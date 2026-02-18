"""
Unit tests for KinesisWriter.

Tests cover:
- _send_batch(): record format (Data=JSON bytes, PartitionKey=symbol)
- _send_batch(): successful batch sends correct record count
- _send_batch(): partial failure triggers _retry_failed()
- _send_batch(): full batch failure reports all records as failed
- _retry_failed(): retries only failed records
- _retry_failed(): returns correct sent/failed counts
- _publish_metrics(): calls CloudWatch put_metric_data with correct namespace
- _publish_metrics(): CloudWatch failure is non-fatal
- shutdown(): sets stop event
"""

import json
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src/producer"))

SAMPLE_EVENTS = [
    {
        "event_id": "123",
        "exchange": "binance",
        "symbol": "BTC-USDT",
        "price": 67432.50,
        "quantity": 0.5,
        "quote_volume": 33716.25,
        "side": "buy",
        "timestamp": "2025-02-05T10:30:00.123Z",
        "ingestion_timestamp": "2025-02-05T10:30:00.456Z",
        "correlation_id": "a3f8c9e2b1d45f67",
    },
    {
        "event_id": "456",
        "exchange": "coinbase",
        "symbol": "ETH-USDT",
        "price": 3200.00,
        "quantity": 1.0,
        "quote_volume": 3200.00,
        "side": "sell",
        "timestamp": "2025-02-05T10:30:01.000Z",
        "ingestion_timestamp": "2025-02-05T10:30:01.200Z",
        "correlation_id": "b4g9d0f3c2e56g78",
    },
]


class TestSendBatch:
    """Test _send_batch() record formatting and send logic."""

    def setup_method(self) -> None:
        with patch("boto3.client"):
            from kinesis_writer import KinesisWriter
            self.writer = KinesisWriter(stream_name="test-stream", region="us-east-1")

    def test_put_records_called_once(self) -> None:
        self.writer._kinesis.put_records.return_value = {"FailedRecordCount": 0, "Records": []}
        self.writer._cw.put_metric_data.return_value = {}
        self.writer._send_batch(SAMPLE_EVENTS)
        self.writer._kinesis.put_records.assert_called_once()

    def test_records_data_is_json_bytes(self) -> None:
        self.writer._kinesis.put_records.return_value = {"FailedRecordCount": 0, "Records": []}
        self.writer._cw.put_metric_data.return_value = {}
        self.writer._send_batch([SAMPLE_EVENTS[0]])

        call_kwargs = self.writer._kinesis.put_records.call_args.kwargs
        record = call_kwargs["Records"][0]
        data = json.loads(record["Data"].decode("utf-8"))
        assert data["event_id"] == "123"
        assert data["symbol"] == "BTC-USDT"

    def test_partition_key_is_symbol(self) -> None:
        self.writer._kinesis.put_records.return_value = {"FailedRecordCount": 0, "Records": []}
        self.writer._cw.put_metric_data.return_value = {}
        self.writer._send_batch(SAMPLE_EVENTS)

        call_kwargs = self.writer._kinesis.put_records.call_args.kwargs
        assert call_kwargs["Records"][0]["PartitionKey"] == "BTC-USDT"
        assert call_kwargs["Records"][1]["PartitionKey"] == "ETH-USDT"

    def test_stream_name_used(self) -> None:
        self.writer._kinesis.put_records.return_value = {"FailedRecordCount": 0, "Records": []}
        self.writer._cw.put_metric_data.return_value = {}
        self.writer._send_batch([SAMPLE_EVENTS[0]])

        call_kwargs = self.writer._kinesis.put_records.call_args.kwargs
        assert call_kwargs["StreamName"] == "test-stream"

    def test_all_records_sent_on_success(self) -> None:
        self.writer._kinesis.put_records.return_value = {
            "FailedRecordCount": 0,
            "Records": [{"SequenceNumber": "1"}, {"SequenceNumber": "2"}],
        }
        self.writer._cw.put_metric_data.return_value = {}
        self.writer._send_batch(SAMPLE_EVENTS)

        cw_call = self.writer._cw.put_metric_data.call_args.kwargs
        metrics = {m["MetricName"]: m["Value"] for m in cw_call["MetricData"]}
        assert metrics["RecordsSent"] == 2.0
        assert metrics["RecordsFailed"] == 0.0

    def test_partial_failure_triggers_retry(self) -> None:
        self.writer._kinesis.put_records.return_value = {
            "FailedRecordCount": 1,
            "Records": [
                {"SequenceNumber": "1"},
                {"ErrorCode": "ProvisionedThroughputExceededException", "ErrorMessage": "Throttled"},
            ],
        }
        self.writer._kinesis.put_record.return_value = {"SequenceNumber": "3"}
        self.writer._cw.put_metric_data.return_value = {}
        self.writer._send_batch(SAMPLE_EVENTS)

        # put_record should be called for the failed record
        self.writer._kinesis.put_record.assert_called_once()

    def test_full_batch_failure_reports_all_failed(self) -> None:
        self.writer._kinesis.put_records.side_effect = Exception("Connection error")
        self.writer._cw.put_metric_data.return_value = {}
        self.writer._send_batch(SAMPLE_EVENTS)

        cw_call = self.writer._cw.put_metric_data.call_args.kwargs
        metrics = {m["MetricName"]: m["Value"] for m in cw_call["MetricData"]}
        assert metrics["RecordsFailed"] == 2.0

    def test_missing_symbol_uses_unknown_partition_key(self) -> None:
        event_no_symbol = {k: v for k, v in SAMPLE_EVENTS[0].items() if k != "symbol"}
        self.writer._kinesis.put_records.return_value = {"FailedRecordCount": 0, "Records": []}
        self.writer._cw.put_metric_data.return_value = {}
        self.writer._send_batch([event_no_symbol])

        call_kwargs = self.writer._kinesis.put_records.call_args.kwargs
        assert call_kwargs["Records"][0]["PartitionKey"] == "unknown"


class TestRetryFailed:
    """Test _retry_failed() retry logic."""

    def setup_method(self) -> None:
        with patch("boto3.client"):
            from kinesis_writer import KinesisWriter
            self.writer = KinesisWriter(stream_name="test-stream", region="us-east-1")

    def _make_records(self, events: list[dict]) -> list[dict]:
        return [
            {
                "Data": json.dumps(e).encode("utf-8"),
                "PartitionKey": e.get("symbol", "unknown"),
            }
            for e in events
        ]

    def test_only_failed_records_retried(self) -> None:
        records = self._make_records(SAMPLE_EVENTS)
        results = [
            {"SequenceNumber": "1"},  # success
            {"ErrorCode": "InternalFailure", "ErrorMessage": "retry me"},  # failed
        ]
        self.writer._kinesis.put_record.return_value = {"SequenceNumber": "3"}

        sent, failed = self.writer._retry_failed(records, results)

        assert self.writer._kinesis.put_record.call_count == 1
        assert sent == 1
        assert failed == 0

    def test_all_succeed_on_retry(self) -> None:
        records = self._make_records(SAMPLE_EVENTS)
        results = [
            {"ErrorCode": "Throttled"},
            {"ErrorCode": "Throttled"},
        ]
        self.writer._kinesis.put_record.return_value = {"SequenceNumber": "1"}

        sent, failed = self.writer._retry_failed(records, results)

        assert sent == 2
        assert failed == 0

    def test_all_fail_after_max_retries(self) -> None:
        records = self._make_records([SAMPLE_EVENTS[0]])
        results = [{"ErrorCode": "InternalFailure"}]
        self.writer._kinesis.put_record.side_effect = Exception("Still failing")

        with patch("time.sleep"):  # don't actually sleep in tests
            sent, failed = self.writer._retry_failed(records, results)

        assert sent == 0
        assert failed == 1

    def test_no_failed_records_returns_zeros(self) -> None:
        records = self._make_records(SAMPLE_EVENTS)
        results = [{"SequenceNumber": "1"}, {"SequenceNumber": "2"}]

        sent, failed = self.writer._retry_failed(records, results)

        self.writer._kinesis.put_record.assert_not_called()
        assert sent == 0
        assert failed == 0


class TestPublishMetrics:
    """Test _publish_metrics() CloudWatch integration."""

    def setup_method(self) -> None:
        with patch("boto3.client"):
            from kinesis_writer import KinesisWriter
            self.writer = KinesisWriter(stream_name="test-stream", region="us-east-1")

    def test_correct_namespace(self) -> None:
        self.writer._cw.put_metric_data.return_value = {}
        self.writer._publish_metrics(10, 0)

        call_kwargs = self.writer._cw.put_metric_data.call_args.kwargs
        assert call_kwargs["Namespace"] == "CoatTail/Producer"

    def test_records_sent_metric(self) -> None:
        self.writer._cw.put_metric_data.return_value = {}
        self.writer._publish_metrics(42, 3)

        call_kwargs = self.writer._cw.put_metric_data.call_args.kwargs
        metrics = {m["MetricName"]: m["Value"] for m in call_kwargs["MetricData"]}
        assert metrics["RecordsSent"] == 42.0
        assert metrics["RecordsFailed"] == 3.0

    def test_metric_unit_is_count(self) -> None:
        self.writer._cw.put_metric_data.return_value = {}
        self.writer._publish_metrics(1, 0)

        call_kwargs = self.writer._cw.put_metric_data.call_args.kwargs
        for m in call_kwargs["MetricData"]:
            assert m["Unit"] == "Count"

    def test_cloudwatch_failure_is_non_fatal(self) -> None:
        self.writer._cw.put_metric_data.side_effect = Exception("CW unavailable")
        self.writer._publish_metrics(10, 0)  # should not raise


class TestShutdown:
    """Test shutdown() sets the stop event."""

    def test_shutdown_sets_stop(self) -> None:
        with patch("boto3.client"):
            from kinesis_writer import KinesisWriter
            writer = KinesisWriter(stream_name="test-stream", region="us-east-1")
        assert not writer._stop.is_set()
        writer.shutdown()
        assert writer._stop.is_set()
