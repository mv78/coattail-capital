"""
Alert routing and output sink management.

AlertRouter takes alert DataFrames from detectors and writes them to:
1. DynamoDB — for hot alerts with lineage in details field (24h TTL)
2. Iceberg — for historical analysis with lineage queryable via SQL
"""

import json
from typing import Any

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, from_json, to_json, when
from pyspark.sql.types import StringType, StructType


class AlertRouter:
    """
    Routes detector output to DynamoDB and Iceberg sinks.

    Preserves lineage context in both outputs:
    - DynamoDB: _lineage stored in details JSON field
    - Iceberg: _lineage in a dedicated JSON column
    """

    def __init__(
        self, dynamodb_table: str, glue_database: str, s3_path: str
    ):
        """
        Initialize the alert router.

        Args:
            dynamodb_table: DynamoDB table name for hot alerts
            glue_database: Glue Data Catalog database for Iceberg tables
            s3_path: S3 path prefix for Iceberg data (e.g., "s3://bucket/iceberg/")
        """
        self.dynamodb_table = dynamodb_table
        self.glue_database = glue_database
        self.s3_path = s3_path

    def route(self, alert_df: DataFrame, detector_output_table: str) -> None:
        """
        Route alerts to DynamoDB and Iceberg sinks.

        Input DataFrame should have:
        - All alert fields from the detector
        - _lineage column (JSON string from detect_with_lineage())

        This method:
        1. Merges _lineage into the details JSON field (if details exists)
        2. Writes to DynamoDB with TTL
        3. Writes to Iceberg via Glue Catalog

        Args:
            alert_df: Alert DataFrame from detector
            detector_output_table: Iceberg table name for this detector's output
                                   (e.g., "volume_anomaly_alerts", from detector.output_table())
        """
        # Merge _lineage into details JSON field
        enriched_df = self._merge_lineage_into_details(alert_df)

        # Write to sinks
        self._write_dynamodb(enriched_df)
        self._write_iceberg(enriched_df, detector_output_table)

    def _merge_lineage_into_details(self, df: DataFrame) -> DataFrame:
        """
        Merge _lineage JSON into the details field.

        If details field doesn't exist, create it.
        Parses the _lineage JSON string and merges it into details.

        Args:
            df: DataFrame with _lineage (JSON string) column

        Returns:
            DataFrame with merged details field
        """
        # Parse _lineage JSON string to struct
        from pyspark.sql.functions import col, from_json, get_json_object, lit, struct
        from pyspark.sql.types import StringType

        # Define a loose schema for lineage (all fields as strings)
        lineage_schema = """
        {
            "correlation_id": "string",
            "source_table": "string",
            "source_event_id": "string",
            "module_id": "string",
            "detector_name": "string",
            "config_hash": "string",
            "processed_at": "string",
            "pipeline_version": "string"
        }
        """

        # Parse _lineage JSON string
        lineage_parsed = from_json(col("_lineage"), lineage_schema)

        # Merge: either merge into existing details, or create new details with _lineage
        if "details" in df.columns:
            # Assume details is a JSON string; parse it and merge
            details_merged = struct(
                col("details").alias("original_details"), lineage_parsed
            ).cast("string")
        else:
            # Create details from _lineage
            details_merged = col("_lineage")

        # Return DataFrame with merged details
        return df.withColumn("details", details_merged).drop("_lineage")

    def _write_dynamodb(self, df: DataFrame) -> None:
        """
        Write alert DataFrame to DynamoDB.

        Writes to the hot alerts table with TTL expiration (24 hours).
        Uses correlation_id as the partition key for traceability.

        Args:
            df: Alert DataFrame with merged details field
        """
        # TODO: Implement DynamoDB write via Spark DynamoDB connector
        # Key structure:
        #   - PK: correlation_id
        #   - SK: timestamp
        #   - TTL: expires in 24 hours
        # Reference: docs/PRD.md Section 6.1 Alert Schema
        pass

    def _write_iceberg(self, df: DataFrame, table_name: str) -> None:
        """
        Write alert DataFrame to Iceberg via Glue Catalog.

        Iceberg allows time-travel queries and schema evolution.
        The details field (containing _lineage) is queryable via Athena SQL.

        Args:
            df: Alert DataFrame with merged details field
            table_name: Iceberg table name (e.g., "volume_anomaly_alerts")
        """
        # TODO: Implement Iceberg write via Glue Catalog
        # Format:
        #   - Catalog: Glue
        #   - Database: self.glue_database
        #   - Table: table_name
        #   - Partitioning: by "symbol" and "date(timestamp)"
        # SQL to query lineage:
        #   SELECT json_extract_scalar(details, '$._lineage.correlation_id')
        #   FROM volume_anomaly_alerts
        #   WHERE symbol = 'btcusdt'
        # Reference: docs/ARCHITECTURE.md Section 4 (Iceberg Storage)
        pass
