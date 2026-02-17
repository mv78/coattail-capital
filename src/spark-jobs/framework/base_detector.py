"""
Base detector abstraction for processing and detection logic.

Every detector (volume anomaly, whale identifier, etc.) inherits from
BaseDetector and implements the standard interface for:
1. Processing a Spark DataFrame (windowed aggregations, threshold checks, etc.)
2. Producing alerts with lineage context
3. Declaring output tables and alert types
"""

from abc import ABC, abstractmethod
from typing import Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, lit, struct, to_json

from lineage import get_pipeline_version, hash_config


class BaseDetector(ABC):
    """
    Abstract base class for feature detection logic.

    Subclasses implement specific detectors (VolumeAnomalyDetector, WhaleDetector, etc.).
    """

    # Subclasses override these
    module_id: str  # e.g., "MOD-001"
    detector_name: str  # e.g., "volume-anomaly"

    def __init__(self):
        """Initialize the detector. Subclasses may extend this."""
        pass

    @abstractmethod
    def process(
        self, df: DataFrame, config: dict[str, Any], spark: SparkSession
    ) -> DataFrame:
        """
        Run detection logic on a DataFrame.

        Input DataFrame has columns:
            - correlation_id: str (injected by connector)
            - exchange: str
            - symbol: str
            - timestamp: str (ISO)
            - event_id: str
            - price: float
            - quantity: float
            - side: str ("buy" or "sell")
            - ... (connector-specific fields)

        Output DataFrame should have columns:
            - correlation_id: str (preserved from input)
            - all relevant aggregation/detection output fields
            - (lineage will be added by detect_with_lineage())

        Args:
            df: Input DataFrame with trade events
            config: Detector configuration dict (e.g., {"threshold": 2.5, "window_seconds": 60})
            spark: SparkSession for DataFrame operations

        Returns:
            Alert DataFrame with detection results and correlation_id preserved
        """
        pass

    @abstractmethod
    def alert_types(self) -> list[str]:
        """
        Return the list of alert types this detector can produce.

        Example: ["volume_spike", "volume_drop"]

        Returns:
            List of alert type strings
        """
        pass

    @abstractmethod
    def output_table(self) -> str:
        """
        Return the Iceberg table name for this detector's output.

        Example: "volume_anomaly_alerts"

        Returns:
            Table name (no schema prefix)
        """
        pass

    def detect_with_lineage(
        self, df: DataFrame, config: dict[str, Any], spark: SparkSession
    ) -> DataFrame:
        """
        Run detection and inject lineage context into output.

        This is the public method called by PipelineRunner. It:
        1. Calls the vendor-specific process()
        2. Adds a _lineage column with LineageContext JSON
        3. Returns the enriched DataFrame

        The _lineage column contains a JSON object with:
            - correlation_id: From the input row
            - source_table: "raw_trades"
            - source_event_id: From the input row
            - module_id: From self.module_id
            - detector_name: From self.detector_name
            - config_hash: sha256(config)
            - processed_at: Current ISO timestamp
            - pipeline_version: From PIPELINE_VERSION env var or "dev"

        Args:
            df: Input DataFrame with trade events and correlation_id
            config: Detector configuration
            spark: SparkSession

        Returns:
            Alert DataFrame with _lineage column added
        """
        # Run the vendor-specific detection logic
        result_df = self.process(df, config, spark)

        # Build lineage context for each row
        lineage_json = self._build_lineage_udf(config, spark)

        # Add _lineage column to result
        enriched_df = result_df.withColumn("_lineage", lineage_json)

        return enriched_df

    def _build_lineage_udf(
        self, config: dict[str, Any], spark: SparkSession
    ) -> Any:
        """
        Build a Spark SQL expression that creates _lineage JSON for each row.

        Returns a struct<...> expression that can be passed to withColumn().
        The struct includes correlation_id from the row and static fields
        (module_id, detector_name, config_hash, etc.).

        Args:
            config: Detector configuration
            spark: SparkSession

        Returns:
            Spark SQL expression (struct) that produces lineage JSON
        """
        from datetime import datetime as dt

        # Compute static values once
        config_hash = hash_config(config)
        pipeline_version = get_pipeline_version()
        processed_at = dt.utcnow().isoformat() + "Z"
        module_id = self.module_id
        detector_name = self.detector_name

        # Build a struct that includes correlation_id from the row
        lineage_struct = struct(
            col("correlation_id").alias("correlation_id"),
            lit("raw_trades").alias("source_table"),
            col("event_id").alias("source_event_id"),
            lit(module_id).alias("module_id"),
            lit(detector_name).alias("detector_name"),
            lit(config_hash).alias("config_hash"),
            lit(processed_at).alias("processed_at"),
            lit(pipeline_version).alias("pipeline_version"),
        )

        # Convert struct to JSON string
        return to_json(lineage_struct)
