"""
Unit tests for CoinbaseConnector.

Tests cover:
- normalize() field mapping for all Coinbase match message fields
- Product ID mapping: btcusdt → BTC-USD (subscription) → BTC-USDT (unified output)
- Side passthrough ("buy"/"sell" — no transformation)
- quote_volume computation
- Timestamp normalization: microsecond ISO → millisecond ISO with Z suffix
- event_id as string (from integer trade_id)
- Non-trade message filtering (subscriptions ACK, heartbeat)
- SYMBOLS env var override
- connect() validation
- health_check() behavior
- shutdown() stop signal
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src/spark-jobs/framework"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src/connectors"))

from coinbase_connector import CoinbaseConnector

SYMBOLS = ["btcusdt", "ethusdt", "solusdt"]

# Canonical Coinbase match message
SAMPLE_MATCH = {
    "type": "match",
    "trade_id": 10,
    "sequence": 50,
    "maker_order_id": "ac928c66-ca53-498f-9c13-a110027a60e8",
    "taker_order_id": "132fb6ae-456b-4654-b4e0-d681ac05cea1",
    "time": "2014-11-07T08:19:27.028459Z",
    "product_id": "BTC-USD",
    "size": "5.23512",
    "price": "400.23",
    "side": "sell",
}

SAMPLE_LAST_MATCH = {**SAMPLE_MATCH, "type": "last_match"}

SAMPLE_SUBSCRIPTIONS_ACK = {
    "type": "subscriptions",
    "channels": [{"name": "matches", "product_ids": ["BTC-USD"]}],
}


class TestCoinbaseNormalize:
    """Test normalize() field mapping."""

    def setup_method(self) -> None:
        self.connector = CoinbaseConnector("coinbase", SYMBOLS)

    def test_all_required_fields_present(self) -> None:
        event = self.connector.normalize(SAMPLE_MATCH)
        assert set(event.keys()) == {
            "event_id",
            "exchange",
            "symbol",
            "price",
            "quantity",
            "quote_volume",
            "side",
            "timestamp",
            "ingestion_timestamp",
        }

    def test_exchange_field(self) -> None:
        assert self.connector.normalize(SAMPLE_MATCH)["exchange"] == "coinbase"

    def test_symbol_btcusd_to_btcusdt(self) -> None:
        """Coinbase BTC-USD → unified BTC-USDT."""
        assert self.connector.normalize(SAMPLE_MATCH)["symbol"] == "BTC-USDT"

    def test_symbol_all_three(self) -> None:
        cases = [
            ("BTC-USD", "BTC-USDT"),
            ("ETH-USD", "ETH-USDT"),
            ("SOL-USD", "SOL-USDT"),
        ]
        for coinbase_sym, expected in cases:
            event = self.connector.normalize({**SAMPLE_MATCH, "product_id": coinbase_sym})
            assert event["symbol"] == expected, f"Expected {expected} for {coinbase_sym}"

    def test_price_cast_from_string(self) -> None:
        event = self.connector.normalize(SAMPLE_MATCH)
        assert event["price"] == 400.23
        assert isinstance(event["price"], float)

    def test_quantity_cast_from_string(self) -> None:
        event = self.connector.normalize(SAMPLE_MATCH)
        assert abs(event["quantity"] - 5.23512) < 1e-6
        assert isinstance(event["quantity"], float)

    def test_quote_volume_computed(self) -> None:
        event = self.connector.normalize(SAMPLE_MATCH)
        expected = 400.23 * 5.23512
        assert abs(event["quote_volume"] - expected) < 0.01

    def test_side_sell_passthrough(self) -> None:
        """Coinbase side is already a string — no boolean conversion."""
        assert self.connector.normalize(SAMPLE_MATCH)["side"] == "sell"

    def test_side_buy_passthrough(self) -> None:
        event = self.connector.normalize({**SAMPLE_MATCH, "side": "buy"})
        assert event["side"] == "buy"

    def test_event_id_is_string(self) -> None:
        event = self.connector.normalize(SAMPLE_MATCH)
        assert event["event_id"] == "10"
        assert isinstance(event["event_id"], str)

    def test_timestamp_ends_with_z(self) -> None:
        ts = self.connector.normalize(SAMPLE_MATCH)["timestamp"]
        assert ts.endswith("Z")

    def test_timestamp_millisecond_precision(self) -> None:
        """Coinbase microseconds (028459) → milliseconds (028)."""
        ts = self.connector.normalize(SAMPLE_MATCH)["timestamp"]
        assert ts.endswith(".028Z")

    def test_timestamp_contains_t_separator(self) -> None:
        ts = self.connector.normalize(SAMPLE_MATCH)["timestamp"]
        assert "T" in ts

    def test_ingestion_timestamp_is_iso_z(self) -> None:
        ts = self.connector.normalize(SAMPLE_MATCH)["ingestion_timestamp"]
        assert ts.endswith("Z")
        assert "T" in ts

    def test_last_match_normalized_same_as_match(self) -> None:
        """last_match type normalizes identically to match."""
        event_match = self.connector.normalize(SAMPLE_MATCH)
        event_last = self.connector.normalize(SAMPLE_LAST_MATCH)
        assert event_match["event_id"] == event_last["event_id"]
        assert event_match["symbol"] == event_last["symbol"]


class TestProductIdMapping:
    """Test config symbol → Coinbase product ID → unified symbol chain."""

    def test_product_ids_for_default_symbols(self) -> None:
        connector = CoinbaseConnector("coinbase", ["btcusdt", "ethusdt", "solusdt"])
        assert connector._product_ids == ["BTC-USD", "ETH-USD", "SOL-USD"]

    def test_symbol_map_btcusd(self) -> None:
        connector = CoinbaseConnector("coinbase", ["btcusdt"])
        assert connector._symbol_map["BTC-USD"] == "BTC-USDT"

    def test_symbol_map_ethusd(self) -> None:
        connector = CoinbaseConnector("coinbase", ["ethusdt"])
        assert connector._symbol_map["ETH-USD"] == "ETH-USDT"

    def test_symbol_map_solusd(self) -> None:
        connector = CoinbaseConnector("coinbase", ["solusdt"])
        assert connector._symbol_map["SOL-USD"] == "SOL-USDT"

    def test_subscription_message_format(self) -> None:
        connector = CoinbaseConnector("coinbase", ["btcusdt"])
        msg = connector._subscribe_message()
        assert msg["type"] == "subscribe"
        assert msg["channels"] == ["matches"]
        assert "BTC-USD" in msg["product_ids"]

    def test_product_ids_uppercase(self) -> None:
        """Input symbols can be lowercase — product_ids must be uppercase."""
        connector = CoinbaseConnector("coinbase", ["btcusdt"])
        assert all(pid == pid.upper() for pid in connector._product_ids)


class TestTimestampNormalization:
    """Test _normalize_timestamp() for various Coinbase timestamp formats."""

    def setup_method(self) -> None:
        self.connector = CoinbaseConnector("coinbase", SYMBOLS)

    def test_microseconds_truncated_to_milliseconds(self) -> None:
        result = self.connector._normalize_timestamp("2014-11-07T08:19:27.028459Z")
        assert result == "2014-11-07T08:19:27.028Z"

    def test_zero_microseconds(self) -> None:
        result = self.connector._normalize_timestamp("2025-01-01T00:00:00.000000Z")
        assert result == "2025-01-01T00:00:00.000Z"

    def test_z_suffix_always_present(self) -> None:
        result = self.connector._normalize_timestamp("2025-01-01T12:30:00.123456Z")
        assert result.endswith("Z")


class TestSymbolsEnvVar:
    """Test SYMBOLS env var override for horizontal partitioning."""

    def test_env_var_overrides_symbols(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SYMBOLS", "solusdt")
        connector = CoinbaseConnector("coinbase", SYMBOLS)
        assert connector.symbols == ["solusdt"]
        assert connector._product_ids == ["SOL-USD"]

    def test_env_var_multi_symbol(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SYMBOLS", "btcusdt,ethusdt")
        connector = CoinbaseConnector("coinbase", SYMBOLS)
        assert connector.symbols == ["btcusdt", "ethusdt"]
        assert connector._product_ids == ["BTC-USD", "ETH-USD"]

    def test_env_var_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SYMBOLS", " btcusdt , solusdt ")
        connector = CoinbaseConnector("coinbase", SYMBOLS)
        assert connector.symbols == ["btcusdt", "solusdt"]

    def test_env_var_empty_falls_back_to_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SYMBOLS", "")
        connector = CoinbaseConnector("coinbase", SYMBOLS)
        assert connector.symbols == SYMBOLS


class TestConnect:
    """Test connect() setup-only behavior."""

    def test_connect_succeeds_with_symbols(self) -> None:
        connector = CoinbaseConnector("coinbase", SYMBOLS)
        connector.connect()  # should not raise

    def test_connect_raises_on_empty_symbols(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SYMBOLS", "")
        connector = CoinbaseConnector("coinbase", [])
        with pytest.raises(ValueError, match="at least one symbol"):
            connector.connect()


class TestHealthCheck:
    """Test health_check() behavior."""

    def test_initially_false(self) -> None:
        """health_check() is False before first message — intentional not-yet-healthy signal."""
        connector = CoinbaseConnector("coinbase", SYMBOLS)
        assert connector.health_check() is False

    def test_true_after_recent_message(self) -> None:
        import time
        connector = CoinbaseConnector("coinbase", SYMBOLS)
        connector._last_message_at = time.monotonic()
        assert connector.health_check() is True

    def test_false_after_stale_message(self) -> None:
        import time
        connector = CoinbaseConnector("coinbase", SYMBOLS)
        connector._last_message_at = time.monotonic() - 31.0  # 31s ago → stale
        assert connector.health_check() is False


class TestShutdown:
    """Test shutdown() sets the stop event."""

    def test_shutdown_sets_stop_event(self) -> None:
        connector = CoinbaseConnector("coinbase", SYMBOLS)
        assert not connector._stop.is_set()
        connector.shutdown()
        assert connector._stop.is_set()


class TestNonTradeMessageFiltering:
    """
    Verify the connector design correctly skips non-match messages.

    Note: actual filtering happens in _listen_once() (async/WS logic not unit-tested here).
    These tests confirm MATCH_TYPES sentinel is correct.
    """

    def test_match_type_is_valid(self) -> None:
        from coinbase_connector import _MATCH_TYPES
        assert "match" in _MATCH_TYPES
        assert "last_match" in _MATCH_TYPES

    def test_subscriptions_ack_not_in_match_types(self) -> None:
        from coinbase_connector import _MATCH_TYPES
        assert SAMPLE_SUBSCRIPTIONS_ACK["type"] not in _MATCH_TYPES
