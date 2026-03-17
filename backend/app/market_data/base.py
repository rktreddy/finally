"""
Abstract base interface for market data providers.

Both the simulator and the Massive API client implement this interface.
All downstream code (SSE streaming, price cache) is agnostic to the source.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class PriceUpdate:
    """A single price update event for a ticker."""

    ticker: str
    price: float
    previous_price: float
    timestamp: str  # ISO 8601 timestamp
    change_direction: str  # "up", "down", or "unchanged"

    @classmethod
    def from_prices(cls, ticker: str, price: float, previous_price: float, timestamp: str) -> "PriceUpdate":
        if price > previous_price:
            direction = "up"
        elif price < previous_price:
            direction = "down"
        else:
            direction = "unchanged"
        return cls(
            ticker=ticker,
            price=price,
            previous_price=previous_price,
            timestamp=timestamp,
            change_direction=direction,
        )


@dataclass
class PriceCache:
    """
    Shared in-memory price cache.

    A single background task (simulator or Massive poller) writes to this cache.
    SSE streams read from this cache to push updates to connected clients.
    Holds the latest price, previous price, and timestamp for each ticker.
    """

    _data: dict[str, PriceUpdate] = field(default_factory=dict)

    def update(self, update: PriceUpdate) -> None:
        """Store the latest price update for a ticker."""
        self._data[update.ticker] = update

    def get(self, ticker: str) -> PriceUpdate | None:
        """Return the latest price update for a ticker, or None if not cached."""
        return self._data.get(ticker)

    def get_all(self) -> dict[str, PriceUpdate]:
        """Return a snapshot of all current prices."""
        return dict(self._data)

    def get_tickers(self) -> list[str]:
        """Return list of tickers currently in the cache."""
        return list(self._data.keys())

    def remove(self, ticker: str) -> None:
        """Remove a ticker from the cache."""
        self._data.pop(ticker, None)

    def clear(self) -> None:
        """Clear all cached prices."""
        self._data.clear()


# Module-level singleton shared across the application
price_cache = PriceCache()


class MarketDataProvider(ABC):
    """
    Abstract base class for market data providers.

    Implementations:
    - MarketDataSimulator: GBM-based simulator (default, no API key needed)
    - MassiveAPIClient: Real market data via Massive REST API
    """

    def __init__(self, cache: PriceCache) -> None:
        self._cache = cache
        self._running = False
        self._tickers: set[str] = set()
        self._on_update: Callable[[PriceUpdate], None] | None = None

    @property
    def tickers(self) -> set[str]:
        """Return the set of tickers currently being tracked."""
        return set(self._tickers)

    def set_update_callback(self, callback: Callable[[PriceUpdate], None]) -> None:
        """Optional callback invoked whenever a price update is written to cache."""
        self._on_update = callback

    def add_ticker(self, ticker: str) -> None:
        """
        Begin tracking a ticker.
        The provider starts generating/polling prices for it immediately.
        """
        ticker = ticker.upper()
        self._tickers.add(ticker)
        self._on_ticker_added(ticker)

    def remove_ticker(self, ticker: str) -> None:
        """
        Stop tracking a ticker.
        Drops it from subsequent price updates.
        """
        ticker = ticker.upper()
        self._tickers.discard(ticker)
        self._cache.remove(ticker)
        self._on_ticker_removed(ticker)

    def _on_ticker_added(self, ticker: str) -> None:
        """Hook called after a ticker is added. Subclasses may override."""

    def _on_ticker_removed(self, ticker: str) -> None:
        """Hook called after a ticker is removed. Subclasses may override."""

    def _emit(self, update: PriceUpdate) -> None:
        """Write an update to the cache and invoke the callback if set."""
        self._cache.update(update)
        if self._on_update is not None:
            self._on_update(update)

    @abstractmethod
    async def start(self) -> None:
        """Start the background data generation/polling loop."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the background loop cleanly."""

    @property
    def is_running(self) -> bool:
        return self._running
