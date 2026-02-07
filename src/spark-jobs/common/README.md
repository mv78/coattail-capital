# Common Spark Modules

Shared modules used by all PySpark jobs.

## Modules to Create

### schemas.py
Spark StructType definitions for:
- Raw Kinesis record
- Unified trade event
- Windowed volume aggregate
- Anomaly alert
- Whale alert
- Spread record

### quality.py
Data quality validation framework:
- `DataQualityChecker` class
- Completeness checks (nulls)
- Validity checks (ranges, allowed values)
- Timeliness checks (stale data)
- CloudWatch metrics publishing
- DLQ routing for failed records

### writers.py
Output sink helpers:
- DynamoDB batch writer (idempotent)
- Iceberg table writer
- CloudWatch metrics publisher

### config.py
Job configuration:
- SparkConf setup
- Environment variable loading
- Kinesis/S3/DynamoDB endpoints

## Data Quality Checks Required

| Check | Rule | Severity |
|---|---|---|
| completeness_event_id | event_id IS NOT NULL | ERROR |
| completeness_symbol | symbol IS NOT NULL | ERROR |
| completeness_price | price IS NOT NULL | ERROR |
| completeness_quantity | quantity IS NOT NULL | ERROR |
| completeness_timestamp | timestamp IS NOT NULL | ERROR |
| validity_price_positive | price > 0 | ERROR |
| validity_quantity_positive | quantity > 0 | ERROR |
| validity_symbol_allowed | symbol IN allowed_list | ERROR |
| validity_exchange_allowed | exchange IN allowed_list | ERROR |
| timeliness_recent | timestamp > now() - 5 min | WARN |
| consistency_quote_volume | quote_volume ≈ price × quantity | WARN |

## Build Instructions

See `agents/data-engineer-agent.md` for detailed specifications.
