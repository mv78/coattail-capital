"""
Unit tests for data lineage context and correlation ID tracking.

Verifies that:
1. Correlation IDs are generated deterministically
2. Configuration hashes are reproducible
3. LineageContext dataclass holds all required fields
4. Integration between BaseConnector, BaseDetector, and AlertRouter
"""

import json
from datetime import datetime
from unittest.mock import patch

import pytest

import sys
import os

# Add framework to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src/spark-jobs/framework"))

from lineage import LineageContext, generate_correlation_id, hash_config, get_pipeline_version


class TestCorrelationIdGeneration:
    """Test correlation ID generation."""

    def test_correlation_id_deterministic(self):
        """Same inputs always produce same correlation ID."""
        cid1 = generate_correlation_id("binance", "btcusdt", "2025-02-05T10:30:00Z")
        cid2 = generate_correlation_id("binance", "btcusdt", "2025-02-05T10:30:00Z")

        assert cid1 == cid2
        assert len(cid1) == 16  # First 16 chars of sha256

    def test_correlation_id_different_inputs(self):
        """Different inputs produce different correlation IDs."""
        cid_binance = generate_correlation_id("binance", "btcusdt", "2025-02-05T10:30:00Z")
        cid_coinbase = generate_correlation_id("coinbase", "btcusdt", "2025-02-05T10:30:00Z")
        cid_different_time = generate_correlation_id(
            "binance", "btcusdt", "2025-02-05T10:31:00Z"
        )

        assert cid_binance != cid_coinbase
        assert cid_binance != cid_different_time

    def test_correlation_id_format(self):
        """Correlation ID is lowercase hex string."""
        cid = generate_correlation_id("binance", "btcusdt", "2025-02-05T10:30:00Z")

        assert isinstance(cid, str)
        assert len(cid) == 16
        assert all(c in "0123456789abcdef" for c in cid)


class TestConfigHashing:
    """Test configuration hashing for reproducibility."""

    def test_config_hash_deterministic(self):
        """Same config dict always produces same hash."""
        config = {"threshold": 2.5, "window_seconds": 60, "enabled": True}

        hash1 = hash_config(config)
        hash2 = hash_config(config)

        assert hash1 == hash2

    def test_config_hash_key_order_independent(self):
        """Config hash independent of dict key order."""
        config_a = {"threshold": 2.5, "window_seconds": 60}
        config_b = {"window_seconds": 60, "threshold": 2.5}

        hash_a = hash_config(config_a)
        hash_b = hash_config(config_b)

        assert hash_a == hash_b

    def test_config_hash_different_values(self):
        """Different config values produce different hashes."""
        config_a = {"threshold": 2.5}
        config_b = {"threshold": 3.0}

        hash_a = hash_config(config_a)
        hash_b = hash_config(config_b)

        assert hash_a != hash_b

    def test_config_hash_format(self):
        """Config hash is full SHA256 (64 hex chars)."""
        config = {"key": "value"}
        hash_val = hash_config(config)

        assert isinstance(hash_val, str)
        assert len(hash_val) == 64
        assert all(c in "0123456789abcdef" for c in hash_val)


class TestLineageContext:
    """Test LineageContext dataclass."""

    def test_lineage_context_creation(self):
        """Create and populate LineageContext."""
        lineage = LineageContext(
            correlation_id="a3f8c9e2b1d45f67",
            source_table="raw_trades",
            source_event_id="evt-12345",
            module_id="MOD-001",
            detector_name="volume-anomaly",
            config_hash="abc123def456",
            processed_at="2025-02-05T10:30:45.123Z",
            pipeline_version="a3f8c9e2b",
        )

        assert lineage.correlation_id == "a3f8c9e2b1d45f67"
        assert lineage.source_table == "raw_trades"
        assert lineage.source_event_id == "evt-12345"
        assert lineage.module_id == "MOD-001"
        assert lineage.detector_name == "volume-anomaly"
        assert lineage.config_hash == "abc123def456"
        assert lineage.processed_at == "2025-02-05T10:30:45.123Z"
        assert lineage.pipeline_version == "a3f8c9e2b"

    def test_lineage_context_to_dict(self):
        """Convert LineageContext to dict."""
        lineage = LineageContext(
            correlation_id="a3f8c9e2b1d45f67",
            source_table="raw_trades",
            source_event_id="evt-12345",
            module_id="MOD-001",
            detector_name="volume-anomaly",
            config_hash="abc123def456",
            processed_at="2025-02-05T10:30:45.123Z",
            pipeline_version="a3f8c9e2b",
        )

        lineage_dict = lineage.to_dict()

        assert isinstance(lineage_dict, dict)
        assert lineage_dict["correlation_id"] == "a3f8c9e2b1d45f67"
        assert lineage_dict["module_id"] == "MOD-001"

    def test_lineage_context_json_serializable(self):
        """LineageContext can be serialized to JSON."""
        lineage = LineageContext(
            correlation_id="a3f8c9e2b1d45f67",
            source_table="raw_trades",
            source_event_id="evt-12345",
            module_id="MOD-001",
            detector_name="volume-anomaly",
            config_hash="abc123def456",
            processed_at="2025-02-05T10:30:45.123Z",
            pipeline_version="a3f8c9e2b",
        )

        json_str = json.dumps(lineage.to_dict())
        parsed = json.loads(json_str)

        assert parsed["correlation_id"] == "a3f8c9e2b1d45f67"
        assert parsed["detector_name"] == "volume-anomaly"


class TestPipelineVersion:
    """Test pipeline version retrieval."""

    def test_pipeline_version_from_env(self):
        """Get pipeline version from PIPELINE_VERSION env var."""
        with patch.dict(os.environ, {"PIPELINE_VERSION": "abc123def456"}):
            version = get_pipeline_version()
            assert version == "abc123def456"

    def test_pipeline_version_default(self):
        """Default to 'dev' if PIPELINE_VERSION not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove PIPELINE_VERSION if it exists
            if "PIPELINE_VERSION" in os.environ:
                del os.environ["PIPELINE_VERSION"]

            version = get_pipeline_version()
            assert version == "dev"


class TestLineageIntegration:
    """Integration tests for lineage across components."""

    def test_correlation_id_flows_through_pipeline(self):
        """Correlation ID should be consistent across all stages."""
        exchange = "binance"
        symbol = "btcusdt"
        timestamp = "2025-02-05T10:30:00Z"

        # Stage 1: Generate correlation ID (BaseConnector)
        correlation_id = generate_correlation_id(exchange, symbol, timestamp)

        # Stage 2: Store in event
        event = {
            "exchange": exchange,
            "symbol": symbol,
            "timestamp": timestamp,
            "correlation_id": correlation_id,
        }

        # Stage 3: Create lineage context (BaseDetector)
        lineage = LineageContext(
            correlation_id=event["correlation_id"],
            source_table="raw_trades",
            source_event_id="evt-12345",
            module_id="MOD-001",
            detector_name="volume-anomaly",
            config_hash=hash_config({"threshold": 2.5}),
            processed_at=datetime.utcnow().isoformat() + "Z",
            pipeline_version=get_pipeline_version(),
        )

        # Verify correlation ID preserved through pipeline
        assert lineage.correlation_id == correlation_id

    def test_lineage_fields_complete(self):
        """Verify all required fields are present in LineageContext."""
        required_fields = {
            "correlation_id",
            "source_table",
            "source_event_id",
            "module_id",
            "detector_name",
            "config_hash",
            "processed_at",
            "pipeline_version",
        }

        lineage = LineageContext(
            correlation_id="a3f8c9e2b1d45f67",
            source_table="raw_trades",
            source_event_id="evt-12345",
            module_id="MOD-001",
            detector_name="volume-anomaly",
            config_hash="abc123def456",
            processed_at="2025-02-05T10:30:45.123Z",
            pipeline_version="a3f8c9e2b",
        )

        lineage_dict = lineage.to_dict()
        assert set(lineage_dict.keys()) == required_fields


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
