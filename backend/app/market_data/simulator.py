"""
Market data simulator using Geometric Brownian Motion (GBM).

Generates realistic-looking price movements for a set of tickers without
requiring any external API. Runs as an in-process background task.

Features:
- GBM with configurable per-ticker drift and volatility
- Correlated moves across tickers (e.g., tech stocks move together)
- Occasional random "events" — sudden 2-5% moves for drama
- Realistic seed prices for default tickers
"""

import asyncio
import math
import random
from datetime import datetime, timezone

from .base import MarketDataProvider, PriceCache, PriceUpdate

# Realistic seed prices (approximate)
DEFAULT_SEED_PRICES: dict[str, float] = {
    "AAPL": 190.00,
    "GOOGL": 175.00,
    "MSFT": 420.00,
    "AMZN": 195.00,
    "TSLA": 250.00,
    "NVDA": 875.00,
    "META": 530.00,
    "JPM": 215.00,
    "V": 285.00,
    "NFLX": 680.00,
}

# Annual drift (mu) and volatility (sigma) per ticker.
# These are annualised values; the simulator converts to per-tick values.
_TICKER_PARAMS: dict[str, dict[str, float]] = {
    "AAPL":  {"mu": 0.15, "sigma": 0.22},
    "GOOGL": {"mu": 0.18, "sigma": 0.25},
    "MSFT":  {"mu": 0.16, "sigma": 0.20},
    "AMZN":  {"mu": 0.20, "sigma": 0.28},
    "TSLA":  {"mu": 0.12, "sigma": 0.55},
    "NVDA":  {"mu": 0.25, "sigma": 0.45},
    "META":  {"mu": 0.20, "sigma": 0.30},
    "JPM":   {"mu": 0.12, "sigma": 0.18},
    "V":     {"mu": 0.13, "sigma": 0.17},
    "NFLX":  {"mu": 0.18, "sigma": 0.35},
}

_DEFAULT_PARAMS = {"mu": 0.15, "sigma": 0.25}

# Tickers that share a "tech sector" factor (partial correlation)
_TECH_TICKERS = {"AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "NFLX"}

# How often the simulator ticks, in seconds
_TICK_INTERVAL_SECONDS = 0.5

# Probability of a random "event" on any given tick for a single ticker
_EVENT_PROBABILITY = 0.002


class MarketDataSimulator(MarketDataProvider):
    """
    GBM-based market data simulator.

    Price evolution per tick follows:
        S(t+dt) = S(t) * exp((mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z)
    where Z ~ N(0,1).

    A shared sector factor adds partial correlation between tech tickers.
    """

    def __init__(
        self,
        cache: PriceCache,
        tick_interval: float = _TICK_INTERVAL_SECONDS,
        seed: int | None = None,
    ) -> None:
        super().__init__(cache)
        self._tick_interval = tick_interval
        self._prices: dict[str, float] = {}
        self._task: asyncio.Task | None = None
        if seed is not None:
            random.seed(seed)

    def _seed_price(self, ticker: str) -> float:
        """Return an initial price for a ticker."""
        base = DEFAULT_SEED_PRICES.get(ticker, 100.0)
        # Small random jitter so repeated starts look different
        jitter = random.uniform(-0.02, 0.02)
        return base * (1 + jitter)

    def _on_ticker_added(self, ticker: str) -> None:
        if ticker not in self._prices:
            self._prices[ticker] = self._seed_price(ticker)

    def _on_ticker_removed(self, ticker: str) -> None:
        self._prices.pop(ticker, None)

    def _next_price(self, ticker: str, current_price: float, sector_shock: float) -> float:
        """
        Compute the next price for a ticker using GBM + sector correlation.

        Parameters
        ----------
        ticker:         The ticker symbol.
        current_price:  Current price S(t).
        sector_shock:   Shared sector innovation Z_sector ~ N(0,1).

        Returns
        -------
        Next price S(t+dt), floored at 0.01.
        """
        params = _TICKER_PARAMS.get(ticker, _DEFAULT_PARAMS)
        mu = params["mu"]
        sigma = params["sigma"]
        dt = self._tick_interval / (252 * 6.5 * 3600)  # fraction of a trading year

        # Idiosyncratic shock
        z_idio = random.gauss(0, 1)

        # Mix sector and idiosyncratic shocks (30% sector correlation for tech)
        if ticker in _TECH_TICKERS:
            rho = 0.30
            z = rho * sector_shock + math.sqrt(1 - rho**2) * z_idio
        else:
            z = z_idio

        drift = (mu - 0.5 * sigma**2) * dt
        diffusion = sigma * math.sqrt(dt) * z
        new_price = current_price * math.exp(drift + diffusion)

        # Occasional random event: sudden 2-5% move
        if random.random() < _EVENT_PROBABILITY:
            direction = random.choice([-1, 1])
            magnitude = random.uniform(0.02, 0.05)
            new_price *= 1 + direction * magnitude

        return max(new_price, 0.01)

    async def start(self) -> None:
        """Start the background simulation loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Stop the simulation loop."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        """Main simulation loop — runs until stopped."""
        while self._running:
            await asyncio.sleep(self._tick_interval)
            self._tick()

    def _tick(self) -> None:
        """Advance prices by one tick and emit updates."""
        if not self._tickers:
            return

        # Shared sector shock for tech correlation
        sector_shock = random.gauss(0, 1)

        now = datetime.now(timezone.utc).isoformat()

        for ticker in list(self._tickers):
            current = self._prices.get(ticker, self._seed_price(ticker))
            new_price = self._next_price(ticker, current, sector_shock)
            update = PriceUpdate.from_prices(
                ticker=ticker,
                price=round(new_price, 2),
                previous_price=round(current, 2),
                timestamp=now,
            )
            self._prices[ticker] = new_price
            self._emit(update)
