"""
Coat Tail Capital — Kinesis Trade Producer.

ECS Fargate entry point. Reads config/features.yaml, starts Binance + Coinbase
WebSocket connectors, and streams normalized trade events to Kinesis.

Environment variables:
    KINESIS_STREAM_NAME  Kinesis stream name (default: coattail-trades)
    AWS_REGION           AWS region (default: us-west-2)
    SYMBOLS              Override symbol list for horizontal Fargate scaling,
                         e.g. "btcusdt,ethusdt" — must be non-overlapping across tasks

Shutdown:
    SIGTERM / SIGINT  → graceful shutdown: drains queue, closes WebSocket connections
"""

import asyncio
import logging
import signal
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)

from connector_manager import ConnectorManager  # noqa: E402


def main() -> None:
    """Start the producer and run until SIGTERM/SIGINT."""
    manager = ConnectorManager()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _handle_signal(sig: signal.Signals) -> None:
        logger.info("Received %s — initiating graceful shutdown", sig.name)
        manager.shutdown()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handle_signal, sig)

    try:
        logger.info("Coat Tail Capital producer starting")
        loop.run_until_complete(manager.run())
    except Exception as exc:
        logger.exception("Producer exited with error: %s", exc)
        sys.exit(1)
    finally:
        loop.close()
        logger.info("Producer stopped")


if __name__ == "__main__":
    main()
