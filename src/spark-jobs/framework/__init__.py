"""
Framework for modular feature detection and alert routing.

Coat Tail Capital uses a plugin architecture where:
- BaseConnector: Standardizes data source integration (exchanges, blockchains)
- BaseDetector: Standardizes detection logic (anomalies, scoring, etc.)
- AlertRouter: Standardizes output routing (DynamoDB, Iceberg)
- ConfigLoader: Reads feature configuration from YAML + SSM
- ModuleRegistry: Dynamically loads active detectors
- PipelineRunner: Orchestrates the full Kinesis → Detector → Alert pipeline

All data flows include a LineageContext to track:
- correlation_id: Deterministic ID threading entire trace from ingestion through all detectors
- source_event_id: Reference to original trade event
- module_id: Which detector produced the alert
- config_hash: Reproducibility — same hash means identical logic
- pipeline_version: Git SHA for audit trail
"""

from alert_router import AlertRouter
from base_connector import BaseConnector
from base_detector import BaseDetector
from config_loader import ConfigLoader
from lineage import LineageContext, generate_correlation_id, get_pipeline_version, hash_config
from module_registry import ModuleRegistry
from pipeline_runner import PipelineRunner

__all__ = [
    "AlertRouter",
    "BaseConnector",
    "BaseDetector",
    "ConfigLoader",
    "LineageContext",
    "ModuleRegistry",
    "PipelineRunner",
    "generate_correlation_id",
    "get_pipeline_version",
    "hash_config",
]
