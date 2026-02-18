"""
Unit tests for BinanceConnector.

Tests cover:
- normalize() field mapping for all 8 Binance @trade fields
- Symbol normalization (BTCUSDT → BTC-USDT, etc.)
- Side derivation from m field
- quote_volume computation
- Timestamp conversion (ms epoch → ISO 8601 Z)
- event_id as string
- Combined stream wrapper unwrapping
- SYMBOLS env var override
- connect() validation
- health_check() behavior
- shutdown() stop signal
"""

import sys
import os
import asyncio

import pytest

# Wire framework and connector paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src/spark-jobs/framework"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src/connectors"))

from binance_connector import BinanceConnector

SYMBOLS = ["btcusdt", "ethusdt", "solusdt"]

# Canonical Binance @trade message (as received from WebSocket, BEFORE unwrapping)
SAMPLE_TRADE = {
    "e": "trade",
    "E": 1672531200123,
    "s": "BTCUSDT",
    "t": 26129417,
    "p": "16500.10",
    "q": "0.001",
    "b": 12345,
    "a": 12346,
    "T": 1672531200123,
    "m": False,
    "M": True,
}

# Same trade wrapped in combined stream envelope
SAMPLE_WRAPPED = {"stream": "btcusdt@trade", "data": SAMPLE_TRADE}


class TestBinanceNormalize:
    """Test normalize() field mapping."""

    def setup_method(self) -> None:
        self.connector = BinanceConnector("binance", SYMBOLS)

    def test_all_required_fields_present(self) -> None:
        event = self.connector.normalize(SAMPLE_TRADE)
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
        assert self.connector.normalize(SAMPLE_TRADE)["exchange"] == "binance"

    def test_symbol_btcusdt(self) -> None:
        assert self.connector.normalize(SAMPLE_TRADE)["symbol"] == "BTC-USDT"

    def test_symbol_all_three(self) -> None:
        cases = [
            ("BTCUSDT", "BTC-USDT"),
            ("ETHUSDT", "ETH-USDT"),
            ("SOLUSDT", "SOL-USDT"),
        ]
        for binance_sym, expected in cases:
            event = self.connector.normalize({**SAMPLE_TRADE, "s": binance_sym})
            assert event["symbol"] == expected, f"Expected {expected} for {binance_sym}"

    def test_price_cast_from_string(self) -> None:
        event = self.connector.normalize(SAMPLE_TRADE)
        assert event["price"] == 16500.10
        assert isinstance(event["price"], float)

    def test_quantity_cast_from_string(self) -> None:
        event = self.connector.normalize(SAMPLE_TRADE)
        assert event["quantity"] == 0.001
        assert isinstance(event["quantity"], float)

    def test_quote_volume_computed(self) -> None:
        event = self.connector.normalize(SAMPLE_TRADE)
        assert abs(event["quote_volume"] - 16.5001) < 0.0001

    def test_side_buyer_taker_is_buy(self) -> None:
        """m=False means buyer is taker → side is buy."""
        event = self.connector.normalize({**SAMPLE_TRADE, "m": False})
        assert event["side"] == "buy"

    def test_side_seller_taker_is_sell(self) -> None:
        """m=True means buyer is market maker → taker is seller → side is sell."""
        event = self.connector.normalize({**SAMPLE_TRADE, "m": True})
        assert event["side"] == "sell"

    def test_event_id_is_string(self) -> None:
        event = self.connector.normalize(SAMPLE_TRADE)
        assert event["event_id"] == "26129417"
        assert isinstance(event["event_id"], str)

    def test_timestamp_ends_with_z(self) -> None:
        ts = self.connector.normalize(SAMPLE_TRADE)["timestamp"]
        assert ts.endswith("Z")

    def test_timestamp_contains_t_separator(self) -> None:
        ts = self.connector.normalize(SAMPLE_TRADE)["timestamp"]
        assert "T" in ts

    def test_timestamp_millisecond_precision(self) -> None:
        """T=1672531200123 → ends in .123Z."""
        ts = self.connector.normalize(SAMPLE_TRADE)["timestamp"]
        assert ts.endswith(".123Z")

    def test_ingestion_timestamp_is_iso_z(self) -> None:
        ts = self.connector.normalize(SAMPLE_TRADE)["ingestion_timestamp"]
        assert ts.endswith("Z")
        assert "T" in ts

    def test_combined_stream_wrapper_unwrap(self) -> None:
        """
        Simulate what _listen_once does: extract outer["data"] before normalizing.
        Calling normalize(SAMPLE_WRAPPED) directly would raise KeyError on raw["p"].
        """
        outer = SAMPLE_WRAPPED
        trade_raw = outer["data"]
        event = self.connector.normalize(trade_raw)
        assert event["symbol"] == "BTC-USDT"
        assert event["event_id"] == "26129417"


class TestSymbolNormalization:
    """Test _build_symbol_map() and symbol normalization edge cases."""

    def test_usdt_pairs(self) -> None:
        connector = BinanceConnector("binance", ["btcusdt", "ethusdt", "solusdt"])
        assert connector._symbol_map["BTCUSDT"] == "BTC-USDT"
        assert connector._symbol_map["ETHUSDT"] == "ETH-USDT"
        assert connector._symbol_map["SOLUSDT"] == "SOL-USDT"

    def test_btc_quote_pair(self) -> None:
        connector = BinanceConnector("binance", ["ethbtc"])
        assert connector._symbol_map["ETHBTC"] == "ETH-BTC"

    def test_eth_quote_pair(self) -> None:
        connector = BinanceConnector("binance", ["solusdt"])
        # ETH-quoted pairs
        connector2 = BinanceConnector("binance", ["soleth"])
        assert connector2._symbol_map["SOLETH"] == "SOL-ETH"

    def test_unknown_pair_falls_back(self) -> None:
        connector = BinanceConnector("binance", ["xrpbnb"])
        assert connector._symbol_map["XRPBNB"] == "XRPBNB"


class TestStreamUrl:
    """Test combined stream URL construction."""

    def test_single_symbol_url(self) -> None:
        connector = BinanceConnector("binance", ["btcusdt"])
        assert connector._stream_url == (
            "wss://stream.binance.com:9443/stream?streams=btcusdt@trade"
        )

    def test_multi_symbol_url(self) -> None:
        connector = BinanceConnector("binance", ["btcusdt", "ethusdt", "solusdt"])
        assert connector._stream_url == (
            "wss://stream.binance.com:9443/stream"
            "?streams=btcusdt@trade/ethusdt@trade/solusdt@trade"
        )

    def test_symbols_lowercased_in_url(self) -> None:
        connector = BinanceConnector("binance", ["BTCUSDT"])
        assert "btcusdt@trade" in connector._stream_url


class TestSymbolsEnvVar:
    """Test SYMBOLS env var override for horizontal partitioning."""

    def test_env_var_overrides_symbols(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SYMBOLS", "solusdt")
        connector = BinanceConnector("binance", SYMBOLS)
        assert connector.symbols == ["solusdt"]

    def test_env_var_multi_symbol(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SYMBOLS", "btcusdt,ethusdt")
        connector = BinanceConnector("binance", SYMBOLS)
        assert connector.symbols == ["btcusdt", "ethusdt"]

    def test_env_var_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SYMBOLS", " btcusdt , solusdt ")
        connector = BinanceConnector("binance", SYMBOLS)
        assert connector.symbols == ["btcusdt", "solusdt"]

    def test_env_var_empty_falls_back_to_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SYMBOLS", "")
        connector = BinanceConnector("binance", SYMBOLS)
        assert connector.symbols == SYMBOLS

    def test_env_var_sets_correct_symbol_map(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SYMBOLS", "solusdt")
        connector = BinanceConnector("binance", SYMBOLS)
        assert "SOL-USDT" in connector._symbol_map.values()
        assert "BTC-USDT" not in connector._symbol_map.values()


class TestConnect:
    """Test connect() setup-only behavior."""

    def test_connect_succeeds_with_symbols(self) -> None:
        connector = BinanceConnector("binance", SYMBOLS)
        connector.connect()  # should not raise

    def test_connect_raises_on_empty_symbols(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SYMBOLS", "")
        connector = BinanceConnector("binance", [])
        with pytest.raises(ValueError, match="at least one symbol"):
            connector.connect()


class TestHealthCheck:
    """Test health_check() behavior."""

    def test_initially_false(self) -> None:
        """health_check() is False before first message — intentional not-yet-healthy signal."""
        connector = BinanceConnector("binance", SYMBOLS)
        assert connector.health_check() is False

    def test_true_after_recent_message(self) -> None:
        import time
        connector = BinanceConnector("binance", SYMBOLS)
        connector._last_message_at = time.monotonic()
        assert connector.health_check() is True

    def test_false_after_stale_message(self) -> None:
        import time
        connector = BinanceConnector("binance", SYMBOLS)
        connector._last_message_at = time.monotonic() - 31.0  # 31s ago → stale
        assert connector.health_check() is False


class TestShutdown:
    """Test shutdown() sets the stop event."""

    def test_shutdown_sets_stop_event(self) -> None:
        connector = BinanceConnector("binance", SYMBOLS)
        assert not connector._stop.is_set()
        connector.shutdown()
        assert connector._stop.is_set()
