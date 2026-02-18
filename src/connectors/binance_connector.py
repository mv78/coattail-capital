"""
Binance WebSocket connector for real-time trade stream ingestion.

Streams the Binance combined @trade stream for configured symbols,
normalizes each trade to the unified TradeEvent schema, and puts
lineage-enriched events onto an asyncio.Queue for the ConnectorManager.

Deployment target: ECS Fargate Spot (NOT Lambda — 15-min timeout disqualifies Lambda).
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

# BaseConnector lives in src/spark-jobs/framework/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../spark-jobs/framework"))

from base_connector import BaseConnector

logger = logging.getLogger(__name__)


class BinanceConnector(BaseConnector):
    """
    Streams real-time trades from the Binance combined WebSocket trade stream.

    Uses a single combined stream connection for all symbols (PRD §6.2: max 5 WS per IP).
    Reconnects automatically with exponential backoff on disconnect.

    Usage (ConnectorManager, Story 2.3):
        connector = BinanceConnector("binance", ["btcusdt", "ethusdt", "solusdt"])
        connector.connect()
        await asyncio.gather(connector.stream(queue), ...)
    """

    _BINANCE_WS_BASE = "wss://stream.binance.com:9443/stream"
    _HEALTH_WINDOW_SECONDS = 30.0
    _MAX_BACKOFF_SECONDS = 60

    def __init__(self, exchange: str, symbols: list[str]) -> None:
        """
        Initialize the connector.

        Symbols are overridable via the SYMBOLS environment variable for horizontal
        partitioning across multiple ECS Fargate tasks. Non-overlapping assignment
        is an operational constraint — duplicate symbols produce duplicate Kinesis records.

        Args:
            exchange: Exchange identifier, e.g. "binance"
            symbols: Default symbol list from config (e.g. ["btcusdt", "ethusdt", "solusdt"]).
                     Overridden by SYMBOLS env var if set.
        """
        env_symbols = [s.strip() for s in os.getenv("SYMBOLS", "").split(",") if s.strip()]
        effective_symbols = env_symbols if env_symbols else symbols

        super().__init__(exchange=exchange, symbols=effective_symbols)

        self._symbol_map: dict[str, str] = self._build_symbol_map()
        self._stream_url: str = self._build_stream_url()
        self._last_message_at: Optional[float] = None  # None until first message received
        self._stop: asyncio.Event = asyncio.Event()

    # ------------------------------------------------------------------
    # BaseConnector abstract method implementations
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """
        Setup-only — validates config and logs the stream URL.

        No network I/O and no threads are started here.
        The actual WebSocket connection is established inside stream().
        """
        if not self.symbols:
            raise ValueError("BinanceConnector requires at least one symbol")
        logger.info(
            "BinanceConnector configured | symbols=%s | stream_url=%s",
            self.symbols,
            self._stream_url,
        )

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize a Binance @trade message to the unified TradeEvent schema.

        Binance sends price and quantity as STRINGS — cast to float explicitly.
        Timestamp field T is milliseconds epoch — converted to ISO 8601 UTC with Z suffix.
        Side is derived from the m (buyer is market maker) boolean:
            m=True  → taker is seller → "sell"
            m=False → taker is buyer  → "buy"

        DO NOT call generate_correlation_id() here — BaseConnector.normalize_with_lineage()
        handles lineage injection automatically after normalize() returns.

        Args:
            raw: Binance @trade message dict (already unwrapped from combined stream wrapper).

        Returns:
            Normalized TradeEvent dict with 9 fields.
        """
        price = float(raw["p"])
        quantity = float(raw["q"])
        return {
            "event_id": str(raw["t"]),
            "exchange": self.exchange,
            "symbol": self._symbol_map[raw["s"]],
            "price": price,
            "quantity": quantity,
            "quote_volume": price * quantity,
            "side": "sell" if raw["m"] else "buy",
            "timestamp": self._ms_to_iso(raw["T"]),
            "ingestion_timestamp": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
        }

    def health_check(self) -> bool:
        """
        Return True if a trade message was received within the last 30 seconds.

        Returns False until the first message arrives — this is intentional and signals
        "not yet healthy" to the ConnectorManager during startup.
        """
        if self._last_message_at is None:
            return False
        return time.monotonic() - self._last_message_at < self._HEALTH_WINDOW_SECONDS

    def shutdown(self) -> None:
        """Signal stream() to exit cleanly on the next loop iteration."""
        self._stop.set()
        logger.info("BinanceConnector shutdown requested")

    # ------------------------------------------------------------------
    # Streaming coroutine (called by ConnectorManager via asyncio.gather)
    # ------------------------------------------------------------------

    async def stream(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """
        Streaming coroutine — runs until shutdown() is called.

        Reconnects automatically with exponential backoff (1s → 2s → 4s → … → 60s cap)
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
                    "BinanceConnector WebSocket error — reconnecting in %ds | error=%s",
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, self._MAX_BACKOFF_SECONDS)

    async def _listen_once(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """
        Open one WebSocket session and stream messages until disconnect or stop.

        Each message from the combined stream is wrapped:
            {"stream": "btcusdt@trade", "data": {...actual trade...}}
        The outer wrapper MUST be unwrapped before calling normalize_with_lineage().

        Args:
            queue: asyncio.Queue to put enriched events onto.
        """
        import websockets  # deferred — not available in Spark EMR environment

        async with websockets.connect(self._stream_url) as ws:
            logger.info("BinanceConnector connected | url=%s", self._stream_url)
            async for message in ws:
                if self._stop.is_set():
                    return
                outer = json.loads(message)
                trade_raw = outer["data"]  # unwrap combined stream wrapper — REQUIRED
                self._last_message_at = time.monotonic()
                queue.put_nowait(self.normalize_with_lineage(trade_raw))

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_stream_url(self) -> str:
        """
        Build the Binance combined stream URL for all configured symbols.

        Single connection for all symbols — required to stay within the 5 WS/IP limit.
        Result: wss://stream.binance.com:9443/stream?streams=btcusdt@trade/ethusdt@trade/...
        """
        streams = "/".join(f"{sym.lower()}@trade" for sym in self.symbols)
        return f"{self._BINANCE_WS_BASE}?streams={streams}"

    def _build_symbol_map(self) -> dict[str, str]:
        """
        Build mapping from Binance uppercase symbol to platform hyphenated format.

        Examples:
            BTCUSDT → BTC-USDT
            ETHUSDT → ETH-USDT
            SOLUSDT → SOL-USDT
            ETHBTC  → ETH-BTC  (quote asset detection)
        """
        mapping: dict[str, str] = {}
        for sym in self.symbols:
            upper = sym.upper()
            if upper.endswith("USDT"):
                mapping[upper] = f"{upper[:-4]}-USDT"
            elif upper.endswith("BTC"):
                mapping[upper] = f"{upper[:-3]}-BTC"
            elif upper.endswith("ETH"):
                mapping[upper] = f"{upper[:-3]}-ETH"
            else:
                mapping[upper] = upper  # fallback: no transformation
        return mapping

    def _ms_to_iso(self, ms: int) -> str:
        """
        Convert milliseconds epoch to ISO 8601 UTC string with Z suffix.

        Preserves millisecond precision: 1672531200123 → "2023-01-01T00:00:00.123Z"
        """
        dt = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms % 1000:03d}Z"
