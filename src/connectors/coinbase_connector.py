"""
Coinbase WebSocket connector for real-time trade stream ingestion.

Connects to the Coinbase Advanced Trade WebSocket (`wss://ws-feed.exchange.coinbase.com`),
subscribes to the `matches` channel for configured product IDs, normalizes each
executed trade to the unified TradeEvent schema, and puts lineage-enriched events
onto an asyncio.Queue for the ConnectorManager.

Key differences from BinanceConnector:
- Subscribe by sending a JSON message (not URL params); receive async subscription ACK
- Coinbase product IDs use USD ("BTC-USD"), not USDT — mapped to platform format ("BTC-USDT")
- side is already a string ("buy"/"sell") — no boolean conversion needed
- timestamp arrives as ISO 8601 with microseconds — preserved as-is, normalize to Z suffix
- Messages include non-trade types (subscriptions, heartbeat) — filter to type=="match"

Deployment target: ECS Fargate Spot (shared with BinanceConnector via ConnectorManager).
Scaling: Set SYMBOLS env var to a non-overlapping subset per Fargate task.
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../spark-jobs/framework"))

from base_connector import BaseConnector

logger = logging.getLogger(__name__)

_COINBASE_WS_URL = "wss://ws-feed.exchange.coinbase.com"
_MATCH_TYPES = frozenset({"match", "last_match"})


class CoinbaseConnector(BaseConnector):
    """
    Streams real-time executed trades from the Coinbase WebSocket matches channel.

    Subscribes to multiple product IDs in a single WebSocket connection.
    Reconnects automatically with exponential backoff on disconnect.

    Usage (ConnectorManager, Story 2.3):
        connector = CoinbaseConnector("coinbase", ["btcusdt", "ethusdt", "solusdt"])
        connector.connect()
        await asyncio.gather(connector.stream(queue), ...)
    """

    _HEALTH_WINDOW_SECONDS = 30.0
    _MAX_BACKOFF_SECONDS = 60

    def __init__(self, exchange: str, symbols: list[str]) -> None:
        """
        Initialize the connector.

        Symbols in config format ("btcusdt") are converted to Coinbase product IDs
        ("BTC-USD") for subscription and mapped back to unified format ("BTC-USDT")
        in normalize(). SYMBOLS env var overrides config symbols for horizontal
        partitioning across ECS Fargate tasks.

        Args:
            exchange: Exchange identifier, e.g. "coinbase"
            symbols: Default symbol list in config format (e.g. ["btcusdt", "ethusdt"]).
                     Overridden by SYMBOLS env var if set.
        """
        env_symbols = [s.strip() for s in os.getenv("SYMBOLS", "").split(",") if s.strip()]
        effective_symbols = env_symbols if env_symbols else symbols

        super().__init__(exchange=exchange, symbols=effective_symbols)

        # Coinbase product IDs for subscription: ["BTC-USD", "ETH-USD", "SOL-USD"]
        self._product_ids: list[str] = self._build_product_ids()
        # Map Coinbase product ID → unified symbol: {"BTC-USD": "BTC-USDT", ...}
        self._symbol_map: dict[str, str] = self._build_symbol_map()

        self._last_message_at: Optional[float] = None  # None until first trade received
        self._stop: asyncio.Event = asyncio.Event()

    # ------------------------------------------------------------------
    # BaseConnector abstract method implementations
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """
        Setup-only — validates config and logs the product IDs that will be subscribed.

        No network I/O and no threads are started here.
        The actual WebSocket connection and subscription are established inside stream().
        """
        if not self._product_ids:
            raise ValueError("CoinbaseConnector requires at least one symbol")
        logger.info(
            "CoinbaseConnector configured | product_ids=%s | endpoint=%s",
            self._product_ids,
            _COINBASE_WS_URL,
        )

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize a Coinbase match message to the unified TradeEvent schema.

        Coinbase sends price and size as STRINGS — cast to float explicitly.
        Coinbase product_id ("BTC-USD") is mapped to platform format ("BTC-USDT").
        Side is already "buy" or "sell" — no transformation needed.
        Timestamp arrives as ISO 8601 with microseconds; normalized to millisecond Z suffix.

        DO NOT call generate_correlation_id() here — BaseConnector.normalize_with_lineage()
        handles lineage injection automatically after normalize() returns.

        Args:
            raw: Coinbase match message dict (type == "match" or "last_match").

        Returns:
            Normalized TradeEvent dict with 9 fields.
        """
        price = float(raw["price"])
        size = float(raw["size"])
        return {
            "event_id": str(raw["trade_id"]),
            "exchange": self.exchange,
            "symbol": self._symbol_map[raw["product_id"]],
            "price": price,
            "quantity": size,
            "quote_volume": price * size,
            "side": raw["side"],  # already "buy" or "sell"
            "timestamp": self._normalize_timestamp(raw["time"]),
            "ingestion_timestamp": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
        }

    def health_check(self) -> bool:
        """
        Return True if a trade message was received within the last 30 seconds.

        Returns False until the first message arrives — signals "not yet healthy"
        to the ConnectorManager during startup.
        """
        if self._last_message_at is None:
            return False
        return time.monotonic() - self._last_message_at < self._HEALTH_WINDOW_SECONDS

    def shutdown(self) -> None:
        """Signal stream() to exit cleanly on the next loop iteration."""
        self._stop.set()
        logger.info("CoinbaseConnector shutdown requested")

    # ------------------------------------------------------------------
    # Streaming coroutine (called by ConnectorManager via asyncio.gather)
    # ------------------------------------------------------------------

    async def stream(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """
        Streaming coroutine — runs until shutdown() is called.

        Reconnects automatically with exponential backoff (1s → 2s → … → 60s cap)
        on any WebSocket error or disconnect. Delay resets to 1s after a clean run.

        ConnectorManager (Story 2.3) calls this via:
            await asyncio.gather(connector.stream(queue), ...)

        Args:
            queue: Shared asyncio.Queue; lineage-enriched TradeEvent dicts are put here.
        """
        delay = 1
        while not self._stop.is_set():
            try:
                await self._listen_once(queue)
                delay = 1  # reset backoff after clean session
            except Exception as exc:
                if self._stop.is_set():
                    return
                logger.warning(
                    "CoinbaseConnector WebSocket error — reconnecting in %ds | error=%s",
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, self._MAX_BACKOFF_SECONDS)

    async def _listen_once(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """
        Open one WebSocket session, subscribe, and stream match events until disconnect or stop.

        Subscription is sent as a JSON message after connecting. Non-trade messages
        (type "subscriptions", "heartbeat", etc.) are silently skipped.
        Only type=="match" and type=="last_match" are normalized and queued.

        Args:
            queue: asyncio.Queue to put enriched events onto.
        """
        import websockets  # deferred — not available in Spark EMR environment

        async with websockets.connect(_COINBASE_WS_URL) as ws:
            await ws.send(json.dumps(self._subscribe_message()))
            logger.info(
                "CoinbaseConnector connected and subscribed | product_ids=%s",
                self._product_ids,
            )

            async for message in ws:
                if self._stop.is_set():
                    return
                raw = json.loads(message)
                if raw.get("type") not in _MATCH_TYPES:
                    continue  # skip subscriptions ACK, heartbeats, etc.
                self._last_message_at = time.monotonic()
                queue.put_nowait(self.normalize_with_lineage(raw))

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _subscribe_message(self) -> dict[str, Any]:
        """Build the Coinbase WebSocket subscription message for the matches channel."""
        return {
            "type": "subscribe",
            "product_ids": self._product_ids,
            "channels": ["matches"],
        }

    def _build_product_ids(self) -> list[str]:
        """
        Convert config symbols to Coinbase product ID format.

        Config format → Coinbase format:
            btcusdt → BTC-USD
            ethusdt → ETH-USD
            solusdt → SOL-USD

        Coinbase uses USD (not USDT) for spot product IDs. The platform normalizes
        both to "BTC-USDT" in the unified schema so detectors see consistent symbols.
        """
        product_ids = []
        for sym in self.symbols:
            upper = sym.upper()
            if upper.endswith("USDT"):
                # btcusdt → BTC-USD (Coinbase spot uses USD)
                product_ids.append(f"{upper[:-4]}-USD")
            elif upper.endswith("BTC"):
                product_ids.append(f"{upper[:-3]}-BTC")
            elif upper.endswith("ETH"):
                product_ids.append(f"{upper[:-3]}-ETH")
            else:
                product_ids.append(upper)
        return product_ids

    def _build_symbol_map(self) -> dict[str, str]:
        """
        Build mapping from Coinbase product ID → unified platform symbol.

        Coinbase → Unified:
            BTC-USD → BTC-USDT
            ETH-USD → ETH-USDT
            SOL-USD → SOL-USDT

        Both Binance (BTC-USDT) and Coinbase (BTC-USD) normalize to BTC-USDT so
        the spread-calculator detector (MOD-003) can match symbols across exchanges.
        """
        mapping: dict[str, str] = {}
        for sym in self.symbols:
            upper = sym.upper()
            if upper.endswith("USDT"):
                base = upper[:-4]
                mapping[f"{base}-USD"] = f"{base}-USDT"
            elif upper.endswith("BTC"):
                base = upper[:-3]
                mapping[f"{base}-BTC"] = f"{base}-BTC"
            elif upper.endswith("ETH"):
                base = upper[:-3]
                mapping[f"{base}-ETH"] = f"{base}-ETH"
            else:
                mapping[upper] = upper
        return mapping

    def _normalize_timestamp(self, ts: str) -> str:
        """
        Normalize Coinbase ISO 8601 timestamp to millisecond precision with Z suffix.

        Coinbase sends microsecond precision: "2014-11-07T08:19:27.028459Z"
        Unified schema uses millisecond precision: "2014-11-07T08:19:27.028Z"
        """
        # Parse the timestamp and reformat to millisecond precision
        # Strip trailing Z, parse, reformat
        ts_clean = ts.rstrip("Z")
        dt = datetime.fromisoformat(ts_clean).replace(tzinfo=timezone.utc)
        ms = dt.microsecond // 1000
        return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms:03d}Z"
