"""
Kinesis writer — drains asyncio.Queue and batches trade events to Kinesis.

Uses put_records() (up to 500 records per call, ~10x cheaper than put_record()).
Partition key = symbol, ensuring ordering per symbol within a Kinesis shard.
Failed records in a batch are retried individually with exponential backoff.
Publishes RecordsSent / RecordsFailed metrics to CloudWatch after each batch.
"""

import asyncio
import json
import logging
import time
from typing import Any, Optional

import boto3

logger = logging.getLogger(__name__)


class KinesisWriter:
    """
    Async-compatible Kinesis writer with batching, retry, and CloudWatch metrics.

    drain() is the streaming coroutine consumed by ConnectorManager via asyncio.gather().
    All boto3 calls are synchronous and run in a thread pool executor to avoid
    blocking the event loop.

    Usage (ConnectorManager):
        writer = KinesisWriter(stream_name="coattail-trades", region="us-west-2")
        await asyncio.gather(connector.stream(queue), writer.drain(queue))
    """

    MAX_BATCH_SIZE = 500          # Kinesis put_records hard limit
    FLUSH_INTERVAL_SECONDS = 1.0  # Max time a record waits before batch is flushed
    MAX_RETRIES = 3               # Per-record retry attempts after batch partial failure
    CW_NAMESPACE = "CoatTail/Producer"

    def __init__(self, stream_name: str, region: str) -> None:
        self._stream_name = stream_name
        self._region = region
        self._kinesis = boto3.client("kinesis", region_name=region)
        self._cw = boto3.client("cloudwatch", region_name=region)
        self._stop: asyncio.Event = asyncio.Event()

    def shutdown(self) -> None:
        """Signal drain() to flush remaining records and exit cleanly."""
        self._stop.set()

    async def drain(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """
        Drain events from queue and write to Kinesis in batches.

        Flushes the current batch when:
        - Batch reaches MAX_BATCH_SIZE (500 records), OR
        - FLUSH_INTERVAL_SECONDS has elapsed (prevents records waiting too long)

        Exits when shutdown() is called AND the queue is empty (all records flushed).

        Args:
            queue: Shared asyncio.Queue fed by connector stream() coroutines.
        """
        loop = asyncio.get_event_loop()
        batch: list[dict[str, Any]] = []

        while True:
            deadline = loop.time() + self.FLUSH_INTERVAL_SECONDS

            while len(batch) < self.MAX_BATCH_SIZE:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    break
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=max(remaining, 0.01))
                    batch.append(item)
                except asyncio.TimeoutError:
                    break

            if batch:
                await loop.run_in_executor(None, self._send_batch, batch)
                batch = []

            if self._stop.is_set() and queue.empty():
                break

    def _send_batch(self, events: list[dict[str, Any]]) -> None:
        """
        Format and send a batch of events to Kinesis via put_records().

        Data: JSON-encoded event bytes.
        PartitionKey: event symbol (ordering per symbol per shard).
        On partial failure: retries failed records individually via _retry_failed().
        Always publishes CloudWatch metrics after each batch attempt.
        """
        records = [
            {
                "Data": json.dumps(event).encode("utf-8"),
                "PartitionKey": event.get("symbol", "unknown"),
            }
            for event in events
        ]

        sent = 0
        failed = 0

        try:
            response = self._kinesis.put_records(
                StreamName=self._stream_name,
                Records=records,
            )
            failed_count = response.get("FailedRecordCount", 0)
            sent = len(records) - failed_count

            if failed_count > 0:
                logger.warning(
                    "put_records: %d/%d records failed — retrying individually",
                    failed_count,
                    len(records),
                )
                retried_sent, retried_failed = self._retry_failed(records, response["Records"])
                sent += retried_sent
                failed += retried_failed

        except Exception as exc:
            logger.error("Kinesis put_records batch failed entirely: %s", exc)
            failed = len(records)

        self._publish_metrics(sent, failed)

    def _retry_failed(
        self,
        records: list[dict[str, Any]],
        results: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """
        Retry individually the records that failed in a put_records() batch.

        Uses exponential backoff between retries: 1s, 2s, 4s (MAX_RETRIES=3).

        Args:
            records: Original records list passed to put_records().
            results: Per-record results from Kinesis response["Records"].

        Returns:
            Tuple of (records_sent, records_failed) across all retry attempts.
        """
        sent = 0
        failed = 0

        failed_records = [
            records[i] for i, result in enumerate(results) if result.get("ErrorCode")
        ]

        for record in failed_records:
            success = False
            for attempt in range(self.MAX_RETRIES):
                try:
                    self._kinesis.put_record(
                        StreamName=self._stream_name,
                        Data=record["Data"],
                        PartitionKey=record["PartitionKey"],
                    )
                    sent += 1
                    success = True
                    break
                except Exception as exc:
                    wait = 2**attempt
                    if attempt < self.MAX_RETRIES - 1:
                        logger.warning(
                            "put_record retry %d/%d failed: %s — waiting %ds",
                            attempt + 1,
                            self.MAX_RETRIES,
                            exc,
                            wait,
                        )
                        time.sleep(wait)
                    else:
                        logger.error(
                            "put_record failed after %d retries: %s",
                            self.MAX_RETRIES,
                            exc,
                        )
            if not success:
                failed += 1

        return sent, failed

    def _publish_metrics(self, sent: int, failed: int) -> None:
        """
        Publish per-batch RecordsSent / RecordsFailed metrics to CloudWatch.

        CloudWatch failures are logged as warnings but do not crash the producer.
        """
        try:
            self._cw.put_metric_data(
                Namespace=self.CW_NAMESPACE,
                MetricData=[
                    {
                        "MetricName": "RecordsSent",
                        "Value": float(sent),
                        "Unit": "Count",
                    },
                    {
                        "MetricName": "RecordsFailed",
                        "Value": float(failed),
                        "Unit": "Count",
                    },
                ],
            )
        except Exception as exc:
            logger.warning("CloudWatch put_metric_data failed (non-fatal): %s", exc)
