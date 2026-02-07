# Kinesis Producer

This directory contains the Python application that:

1. Connects to Binance and Coinbase public WebSocket streams
2. Normalizes trade events to a unified schema
3. Publishes to Kinesis Data Streams

## Files to Create

- `main.py` — Entry point, asyncio event loop
- `config.py` — Environment-based configuration
- `models.py` — Pydantic models for trade events
- `exchanges/binance.py` — Binance WebSocket handler
- `exchanges/coinbase.py` — Coinbase WebSocket handler
- `kinesis_writer.py` — Batched Kinesis put_records
- `requirements.txt` — Dependencies
- `Dockerfile` — For containerized deployment (optional)

## Usage

```bash
export KINESIS_STREAM_NAME=coattail-trades
export AWS_REGION=us-west-2
export SYMBOLS=btcusdt,ethusdt,solusdt

python main.py
```

## Build Instructions

See `agents/data-engineer-agent.md` for detailed specifications.
