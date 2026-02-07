# Tests

## Structure

```
tests/
├── unit/                    # Fast, isolated tests
│   ├── test_schemas.py
│   ├── test_quality.py
│   ├── test_volume_anomaly.py
│   ├── test_whale_detector.py
│   ├── test_spread_calculator.py
│   └── test_producer.py
├── integration/             # Tests against deployed infra
│   ├── test_kinesis_flow.py
│   ├── test_spark_jobs.py
│   └── test_api_endpoints.py
├── fixtures/                # Test data
│   ├── sample_binance_trades.json
│   ├── sample_coinbase_trades.json
│   ├── anomaly_scenario.json
│   ├── whale_scenario.json
│   └── spread_scenario.json
└── conftest.py              # Shared pytest fixtures
```

## Running Tests

```bash
# All unit tests
pytest tests/unit/ -v

# Specific test
pytest tests/unit/test_quality.py -v

# With coverage
pytest tests/unit/ --cov=src --cov-report=html

# Integration tests (requires deployed infra)
pytest tests/integration/ -v
```

## Build Instructions

See `agents/qa-agent.md` for detailed test specifications.
