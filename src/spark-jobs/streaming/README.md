# PySpark Streaming Jobs

Real-time streaming jobs running on EMR Serverless.

## Jobs to Create

### volume_anomaly.py
- 60-second tumbling window aggregation
- Rolling 1-hour statistics for z-score calculation
- Anomaly threshold: z > 2.5
- Output: DynamoDB alerts + S3 Iceberg

### whale_detector.py
- Filter trades where quote_volume > $100K
- Enrich with wallet/exchange metadata
- Output: DynamoDB alerts + S3 Iceberg

### spread_calculator.py
- 30-second tumbling window
- VWAP per symbol per exchange
- Spread = (binance_vwap - coinbase_vwap) / coinbase_vwap
- Flag spreads > 0.5%
- Output: DynamoDB alerts + S3 Iceberg

## Common Patterns

All jobs should:
1. Read from Kinesis using `spark.readStream.format("kinesis")`
2. Run data quality checks via `common/quality.py`
3. Apply watermarking (30 seconds)
4. Checkpoint to S3
5. Write to Iceberg via Glue Catalog
6. Write alerts to DynamoDB via foreachBatch

## Build Instructions

See `agents/data-engineer-agent.md` for detailed specifications.
