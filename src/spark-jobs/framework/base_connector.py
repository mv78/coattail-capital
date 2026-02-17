"""
Base connector abstraction for data source integration.

Every connector (exchange WebSocket, blockchain RPC, etc.) inherits from
BaseConnector and implements the standard interface for:
1. Connecting to the data source
2. Normalizing raw data to TradeEvent schema
3. Injecting correlation IDs for lineage tracking
4. Health checks for operational monitoring
5. Graceful shutdown
"""

from abc import ABC, abstractmethod
from typing import Any

from lineage import generate_correlation_id


class BaseConnector(ABC):
    """
    Abstract base class for data source connectors.

    Subclasses implement specific connectors (BinanceConnector, CoinbaseConnector, etc.).
    """

    def __init__(self, exchange: str, symbols: list[str]):
        """
        Initialize the connector.

        Args:
            exchange: Exchange name (e.g., "binance", "coinbase")
            symbols: List of trading pairs to subscribe to (e.g., ["btcusdt", "ethusdt"])
        """
        self.exchange = exchange
        self.symbols = symbols

    @abstractmethod
    def connect(self) -> None:
        """
        Establish connection to the data source.

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize raw data from the source to standard TradeEvent schema.

        Input: Vendor-specific format (e.g., Binance WebSocket trade message)
        Output: Normalized TradeEvent dict with fields:
            - exchange: str
            - symbol: str
            - timestamp: str (ISO format)
            - event_id: str (unique within exchange)
            - price: float
            - quantity: float
            - side: str ("buy" or "sell")
            - order_id: str (optional, if available)

        Note: This method does NOT inject correlation_id; that's done in
        normalize_with_lineage().

        Args:
            raw: Vendor-specific data dict

        Returns:
            Normalized TradeEvent dict

        Raises:
            ValueError: If raw data doesn't match expected schema
        """
        pass

    def normalize_with_lineage(self, raw: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize raw data and inject correlation ID for lineage tracking.

        This is the public method called by the producer. It:
        1. Calls the vendor-specific normalize()
        2. Generates and injects correlation_id from exchange+symbol+timestamp
        3. Returns the enriched event

        Args:
            raw: Vendor-specific data dict

        Returns:
            Normalized TradeEvent dict with correlation_id field
        """
        event = self.normalize(raw)

        # Generate deterministic correlation ID from event attributes
        event["correlation_id"] = generate_correlation_id(
            event["exchange"], event["symbol"], event["timestamp"]
        )

        return event

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the connector is healthy and able to receive data.

        Returns:
            True if healthy, False otherwise
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """
        Gracefully shutdown the connection.

        Used during teardown to close WebSocket connections, file handles, etc.
        """
        pass
