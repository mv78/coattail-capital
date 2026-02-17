"""
Data lineage tracking for Coat Tail Capital.

Every alert is tagged with a LineageContext containing:
- correlation_id: Deterministic ID threading from Kinesis ingestion through all detectors
- source details: Original trade event reference
- module details: Which detector produced this alert
- config hash: Reproducibility — same hash means identical detection logic
- pipeline version: Git SHA for audit trail
"""

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass
class LineageContext:
    """
    Embedded in every alert's details._lineage JSON field.
    Zero cost storage — leverages existing details JSON field.
    """

    correlation_id: str  # sha256(exchange+symbol+timestamp)[:16] — threads entire trace
    source_table: str  # "raw_trades" — where this event originated
    source_event_id: str  # Original trade event_id for back-reference
    module_id: str  # "MOD-001" — which module created this alert
    detector_name: str  # "volume-anomaly" — human-readable detector name
    config_hash: str  # sha256(config) — ensures reproducibility
    processed_at: str  # ISO timestamp of detection
    pipeline_version: str  # Git SHA or "dev" — from env var PIPELINE_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)


def generate_correlation_id(exchange: str, symbol: str, timestamp: str) -> str:
    """
    Generate a deterministic correlation ID from trade attributes.

    Same exchange + symbol + timestamp always produces same ID.
    This allows tracing any alert back to its source event.

    Args:
        exchange: Exchange name (e.g., "binance", "coinbase")
        symbol: Trading pair (e.g., "btcusdt", "eth-usd")
        timestamp: ISO timestamp of the trade

    Returns:
        16-character hex string (sha256[:16])
    """
    combined = f"{exchange}:{symbol}:{timestamp}"
    hash_obj = hashlib.sha256(combined.encode("utf-8"))
    return hash_obj.hexdigest()[:16]


def hash_config(config: dict[str, Any]) -> str:
    """
    Hash a configuration dict for reproducibility tracking.

    Same config dict always produces same hash.
    Used to ensure that alerts with the same config_hash
    were generated with identical detection logic.

    Args:
        config: Configuration dict (e.g., {"threshold": 2.5, "window_seconds": 60})

    Returns:
        32-character hex string (full sha256)
    """
    # Sort keys for deterministic serialization
    json_str = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


def get_pipeline_version() -> str:
    """
    Get the pipeline version from environment or default to 'dev'.

    In CI/CD, set PIPELINE_VERSION to git commit SHA.
    """
    return os.getenv("PIPELINE_VERSION", "dev")
