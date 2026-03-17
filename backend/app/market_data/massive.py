"""
Massive API client for real market data.

Massive (https://massive.app) provides a unified REST API over multiple market
data sources. This client polls the REST endpoint for the current watchlist at
a configurable interval and feeds prices into the shared price cache.

Usage:
    Set MASSIVE_API_KEY in the environment to enable this provider.
    Omit it (or leave it empty) to use the simulator instead.

Polling interval:
    Free tier  (5 calls/min): poll every 15 s
    Paid tiers:               poll every 2–15 s depending on tier
"""

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from .base import MarketDataProvider, PriceCache, PriceUpdate

logger = logging.getLogger(__name__)

# Massive REST API base URL
_MASSIVE_BASE_URL = "https://api.massive.app"
_QUOTE_ENDPOINT = "/v1/quotes"

# Default poll interval (seconds) — conservative for the free tier
_DEFAULT_POLL_INTERVAL = 15.0


class MassiveAPIClient(MarketDataProvider):
    """
    Polls the Massive REST API for live market quotes.

    Implements the same MarketDataProvider interface as the simulator so all
    downstream code (SSE streaming, price cache) is source-agnostic.
    """

    def __init__(
        self,
        cache: PriceCache,
        api_key: str,
        poll_interval: float = _DEFAULT_POLL_INTERVAL,
        base_url: str = _MASSIVE_BASE_URL,
    ) -> None:
        super().__init__(cache)
        self._api_key = api_key
        self._poll_interval = poll_interval
        self._base_url = base_url.rstrip("/")
        self._task: asyncio.Task | None = None
        # Track last known prices to compute change direction
        self._last_prices: dict[str, float] = {}

    async def start(self) -> None:
        """Start the background polling loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Stop the polling loop."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        """Main polling loop — runs until stopped."""
        async with httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=10.0,
        ) as client:
            while self._running:
                tickers = list(self._tickers)
                if tickers:
                    await self._poll(client, tickers)
                await asyncio.sleep(self._poll_interval)

    async def _poll(self, client: httpx.AsyncClient, tickers: list[str]) -> None:
        """Fetch quotes for the given tickers and update the cache."""
        try:
            response = await client.get(
                _QUOTE_ENDPOINT,
                params={"symbols": ",".join(tickers)},
            )
            response.raise_for_status()
            data = response.json()
            self._process_response(data)
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Massive API returned %s for tickers %s: %s",
                exc.response.status_code,
                tickers,
                exc.response.text,
            )
        except httpx.RequestError as exc:
            logger.warning("Massive API request error: %s", exc)
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error polling Massive API: %s", exc)

    def _process_response(self, data: object) -> None:
        """
        Parse the Massive API response and emit price updates.

        Expected response shape (subject to Massive API spec):
        {
          "quotes": [
            {"symbol": "AAPL", "price": 190.50, ...},
            ...
          ]
        }
        """
        if not isinstance(data, dict):
            logger.warning("Unexpected Massive API response type: %r", type(data))
            return

        quotes = data.get("quotes", [])
        if not isinstance(quotes, list):
            logger.warning("Unexpected 'quotes' field in Massive API response: %r", quotes)
            return

        now = datetime.now(timezone.utc).isoformat()

        for quote in quotes:
            ticker = self._extract_ticker(quote)
            price = self._extract_price(quote)
            if ticker is None or price is None:
                continue

            # Only emit updates for tickers we're still tracking
            if ticker not in self._tickers:
                continue

            previous_price = self._last_prices.get(ticker, price)
            self._last_prices[ticker] = price

            update = PriceUpdate.from_prices(
                ticker=ticker,
                price=price,
                previous_price=previous_price,
                timestamp=now,
            )
            self._emit(update)

    @staticmethod
    def _extract_ticker(quote: object) -> str | None:
        """Extract the ticker symbol from a quote object."""
        if not isinstance(quote, dict):
            return None
        # Massive API may use "symbol" or "ticker"
        symbol = quote.get("symbol") or quote.get("ticker")
        if not isinstance(symbol, str) or not symbol:
            return None
        return symbol.upper()

    @staticmethod
    def _extract_price(quote: object) -> float | None:
        """Extract the price from a quote object."""
        if not isinstance(quote, dict):
            return None
        # Massive API may use "price", "last", or "close"
        raw = quote.get("price") or quote.get("last") or quote.get("close")
        if raw is None:
            return None
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None
        if value <= 0:
            return None
        return round(value, 2)
