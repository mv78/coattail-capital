"""
ConnectorManager — reads features.yaml, instantiates connectors, runs the event loop.

This is the core orchestrator for the ECS Fargate producer task:
1. Loads config/features.yaml to determine active exchange_connectors + symbols
2. Instantiates a BaseConnector subclass for each active connector
3. Calls connect() (setup-only) on each
4. Runs asyncio.gather(connector.stream(queue)..., writer.drain(queue))

The event loop is owned here. Connectors expose async stream() coroutines;
KinesisWriter exposes an async drain() coroutine. All run concurrently.
"""

import asyncio
import logging
import os
import sys
from typing import Any

import yaml

# Resolve connector and framework paths relative to this file
_PRODUCER_DIR = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_PRODUCER_DIR, "../connectors"))
sys.path.insert(0, os.path.join(_PRODUCER_DIR, "../spark-jobs/framework"))

from base_connector import BaseConnector  # noqa: E402
from binance_connector import BinanceConnector  # noqa: E402
from coinbase_connector import CoinbaseConnector  # noqa: E402
from kinesis_writer import KinesisWriter  # noqa: E402

logger = logging.getLogger(__name__)

# Registry maps config connector names → (exchange_name, connector_class)
_CONNECTOR_REGISTRY: dict[str, tuple[str, type[BaseConnector]]] = {
    "binance-ws": ("binance", BinanceConnector),
    "coinbase-ws": ("coinbase", CoinbaseConnector),
}


class ConnectorManager:
    """
    Orchestrates the full data ingestion pipeline for the ECS Fargate producer.

    Reads features.yaml, builds connectors, and runs the asyncio event loop
    until shutdown() is called (SIGTERM in production).

    Usage:
        manager = ConnectorManager()
        asyncio.run(manager.run())       # called from main.py
        manager.shutdown()               # called from signal handler
    """

    DEFAULT_CONFIG_PATH = "config/features.yaml"
    DEFAULT_STREAM_NAME = "coattail-trades"
    DEFAULT_REGION = "us-west-2"
    DEFAULT_QUEUE_MAXSIZE = 10_000

    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH) -> None:
        self._config_path = config_path
        self._connectors: list[BaseConnector] = []
        self._writer: KinesisWriter | None = None

    def load_config(self) -> dict[str, Any]:
        """
        Load and parse config/features.yaml.

        Returns:
            Parsed config dict with keys: feature_tier, symbols, exchange_connectors, etc.
        """
        with open(self._config_path) as f:
            config: dict[str, Any] = yaml.safe_load(f)
        return config

    def build_connectors(self, config: dict[str, Any]) -> list[BaseConnector]:
        """
        Instantiate connectors based on the exchange_connectors list in config.

        Unknown connector names are logged as warnings and skipped. Symbols from
        config are passed to each connector and can be overridden at runtime by
        the SYMBOLS environment variable (for horizontal Fargate task partitioning).

        Args:
            config: Parsed features.yaml dict.

        Returns:
            List of instantiated, not-yet-connected BaseConnector subclasses.
        """
        symbols: list[str] = config.get("symbols", [])
        connector_names: list[str] = config.get("exchange_connectors", [])
        connectors: list[BaseConnector] = []

        for name in connector_names:
            entry = _CONNECTOR_REGISTRY.get(name)
            if entry is None:
                logger.warning(
                    "Unknown connector '%s' in exchange_connectors — skipping", name
                )
                continue
            exchange_name, connector_cls = entry
            connector = connector_cls(exchange_name, symbols)
            connectors.append(connector)
            logger.info("Registered connector: %s (%s)", name, connector_cls.__name__)

        return connectors

    async def run(self) -> None:
        """
        Main async entry point — loads config, starts connectors, runs event loop.

        Called by main.py via asyncio.run(manager.run()). Runs until all coroutines
        complete (which happens only when shutdown() is called and queues are drained).
        """
        config = self.load_config()
        self._connectors = self.build_connectors(config)

        if not self._connectors:
            logger.error("No connectors configured in features.yaml — exiting")
            return

        stream_name = os.getenv("KINESIS_STREAM_NAME", self.DEFAULT_STREAM_NAME)
        region = os.getenv("AWS_REGION", self.DEFAULT_REGION)

        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(
            maxsize=self.DEFAULT_QUEUE_MAXSIZE
        )
        self._writer = KinesisWriter(stream_name=stream_name, region=region)

        logger.info(
            "ConnectorManager starting | connectors=%d | stream=%s | region=%s",
            len(self._connectors),
            stream_name,
            region,
        )

        for connector in self._connectors:
            connector.connect()

        await asyncio.gather(
            *[c.stream(queue) for c in self._connectors],
            self._writer.drain(queue),
        )

    def shutdown(self) -> None:
        """
        Signal all connectors and the KinesisWriter to stop gracefully.

        Connectors set their stop event → stream() exits on next iteration.
        KinesisWriter sets its stop event → drain() flushes remaining records and exits.
        asyncio.gather() completes once all coroutines return.
        """
        logger.info("ConnectorManager shutdown initiated")
        for connector in self._connectors:
            connector.shutdown()
        if self._writer is not None:
            self._writer.shutdown()
