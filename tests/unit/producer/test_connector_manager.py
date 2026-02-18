"""
Unit tests for ConnectorManager.

Tests cover:
- build_connectors() instantiates correct connector types for known names
- build_connectors() skips unknown connector names with a warning
- build_connectors() passes symbols from config to each connector
- build_connectors() returns empty list for empty exchange_connectors
- load_config() reads and parses features.yaml correctly
- shutdown() delegates to all connectors and writer
"""

import sys
import os
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src/spark-jobs/framework"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src/connectors"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src/producer"))

from connector_manager import ConnectorManager
from binance_connector import BinanceConnector
from coinbase_connector import CoinbaseConnector


SAMPLE_CONFIG = {
    "feature_tier": "small",
    "symbols": ["btcusdt", "ethusdt", "solusdt"],
    "exchange_connectors": ["binance-ws", "coinbase-ws"],
}


class TestBuildConnectors:
    """Test connector factory logic."""

    def setup_method(self) -> None:
        self.manager = ConnectorManager()

    def test_binance_ws_creates_binance_connector(self) -> None:
        config = {**SAMPLE_CONFIG, "exchange_connectors": ["binance-ws"]}
        connectors = self.manager.build_connectors(config)
        assert len(connectors) == 1
        assert isinstance(connectors[0], BinanceConnector)

    def test_coinbase_ws_creates_coinbase_connector(self) -> None:
        config = {**SAMPLE_CONFIG, "exchange_connectors": ["coinbase-ws"]}
        connectors = self.manager.build_connectors(config)
        assert len(connectors) == 1
        assert isinstance(connectors[0], CoinbaseConnector)

    def test_both_connectors_created(self) -> None:
        connectors = self.manager.build_connectors(SAMPLE_CONFIG)
        assert len(connectors) == 2
        types = {type(c) for c in connectors}
        assert BinanceConnector in types
        assert CoinbaseConnector in types

    def test_order_preserved(self) -> None:
        connectors = self.manager.build_connectors(SAMPLE_CONFIG)
        assert isinstance(connectors[0], BinanceConnector)
        assert isinstance(connectors[1], CoinbaseConnector)

    def test_symbols_passed_to_binance_connector(self) -> None:
        config = {**SAMPLE_CONFIG, "exchange_connectors": ["binance-ws"]}
        connectors = self.manager.build_connectors(config)
        assert connectors[0].symbols == ["btcusdt", "ethusdt", "solusdt"]

    def test_symbols_passed_to_coinbase_connector(self) -> None:
        config = {**SAMPLE_CONFIG, "exchange_connectors": ["coinbase-ws"]}
        connectors = self.manager.build_connectors(config)
        assert connectors[0].symbols == ["btcusdt", "ethusdt", "solusdt"]

    def test_exchange_name_binance(self) -> None:
        config = {**SAMPLE_CONFIG, "exchange_connectors": ["binance-ws"]}
        connectors = self.manager.build_connectors(config)
        assert connectors[0].exchange == "binance"

    def test_exchange_name_coinbase(self) -> None:
        config = {**SAMPLE_CONFIG, "exchange_connectors": ["coinbase-ws"]}
        connectors = self.manager.build_connectors(config)
        assert connectors[0].exchange == "coinbase"

    def test_unknown_connector_skipped(self) -> None:
        config = {**SAMPLE_CONFIG, "exchange_connectors": ["kraken-ws"]}
        connectors = self.manager.build_connectors(config)
        assert connectors == []

    def test_unknown_connector_does_not_block_known(self) -> None:
        config = {
            **SAMPLE_CONFIG,
            "exchange_connectors": ["binance-ws", "kraken-ws", "coinbase-ws"],
        }
        connectors = self.manager.build_connectors(config)
        assert len(connectors) == 2
        assert isinstance(connectors[0], BinanceConnector)
        assert isinstance(connectors[1], CoinbaseConnector)

    def test_empty_exchange_connectors(self) -> None:
        config = {**SAMPLE_CONFIG, "exchange_connectors": []}
        connectors = self.manager.build_connectors(config)
        assert connectors == []

    def test_missing_exchange_connectors_key(self) -> None:
        config = {"symbols": ["btcusdt"]}
        connectors = self.manager.build_connectors(config)
        assert connectors == []

    def test_empty_symbols_passed_through(self) -> None:
        config = {"symbols": [], "exchange_connectors": ["binance-ws"]}
        connectors = self.manager.build_connectors(config)
        assert connectors[0].symbols == []


class TestLoadConfig:
    """Test load_config() reads and parses features.yaml."""

    def test_load_actual_features_yaml(self) -> None:
        """Load the real config/features.yaml from the project root."""
        # Path relative to repo root (tests run from project root)
        manager = ConnectorManager(config_path="config/features.yaml")
        config = manager.load_config()
        assert "symbols" in config
        assert "exchange_connectors" in config
        assert "feature_tier" in config

    def test_load_config_symbols(self) -> None:
        manager = ConnectorManager(config_path="config/features.yaml")
        config = manager.load_config()
        assert "btcusdt" in config["symbols"]
        assert "ethusdt" in config["symbols"]
        assert "solusdt" in config["symbols"]

    def test_load_config_connectors(self) -> None:
        manager = ConnectorManager(config_path="config/features.yaml")
        config = manager.load_config()
        assert "binance-ws" in config["exchange_connectors"]
        assert "coinbase-ws" in config["exchange_connectors"]


class TestShutdown:
    """Test shutdown() delegates stop signals correctly."""

    def test_shutdown_calls_connector_shutdown(self) -> None:
        manager = ConnectorManager()
        mock_connector = MagicMock()
        manager._connectors = [mock_connector]
        manager.shutdown()
        mock_connector.shutdown.assert_called_once()

    def test_shutdown_calls_writer_shutdown(self) -> None:
        manager = ConnectorManager()
        mock_writer = MagicMock()
        manager._connectors = []
        manager._writer = mock_writer
        manager.shutdown()
        mock_writer.shutdown.assert_called_once()

    def test_shutdown_all_connectors(self) -> None:
        manager = ConnectorManager()
        mock_a = MagicMock()
        mock_b = MagicMock()
        manager._connectors = [mock_a, mock_b]
        manager.shutdown()
        mock_a.shutdown.assert_called_once()
        mock_b.shutdown.assert_called_once()

    def test_shutdown_with_no_writer_does_not_raise(self) -> None:
        manager = ConnectorManager()
        manager._connectors = []
        manager._writer = None
        manager.shutdown()  # should not raise
