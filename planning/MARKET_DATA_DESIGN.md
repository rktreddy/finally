# Market Data Backend — Implementation Design

Complete implementation guide for the FinAlly market data subsystem. This document covers the unified API, GBM simulator, Massive (Polygon.io) API client, SSE streaming, and FastAPI lifecycle integration — with full code snippets ready for implementation.

All code lives under `backend/app/market/`.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [File Structure](#2-file-structure)
3. [Data Model — `models.py`](#3-data-model)
4. [Price Cache — `cache.py`](#4-price-cache)
5. [Unified Interface — `interface.py`](#5-unified-interface)
6. [Seed Prices & Ticker Parameters — `seed_prices.py`](#6-seed-prices--ticker-parameters)
7. [GBM Simulator — `simulator.py`](#7-gbm-simulator)
8. [Massive API Client — `massive_client.py`](#8-massive-api-client)
9. [Factory — `factory.py`](#9-factory)
10. [SSE Streaming — `stream.py`](#10-sse-streaming)
11. [FastAPI Lifecycle Integration](#11-fastapi-lifecycle-integration)
12. [Watchlist Coordination](#12-watchlist-coordination)
13. [Testing Strategy](#13-testing-strategy)
14. [Error Handling & Edge Cases](#14-error-handling--edge-cases)
15. [Configuration Summary](#15-configuration-summary)

---

## 1. Architecture Overview

The market data subsystem follows the **Strategy pattern** — two interchangeable data sources (simulator and Massive API) implement the same abstract interface. All downstream code reads from a shared `PriceCache` and is completely agnostic to the data source.

```
MarketDataSource (ABC)
├── SimulatorDataSource  →  GBM simulator (default, no API key needed)
└── MassiveDataSource    →  Polygon.io REST poller (when MASSIVE_API_KEY set)
        │
        ▼
   PriceCache (thread-safe, in-memory)
        │
        ├──→ SSE stream endpoint (/api/stream/prices)  →  Frontend
        ├──→ Portfolio valuation (read current prices)
        └──→ Trade execution (fill at current price)
```

### Data Flow

1. **Producer** (simulator or Massive poller) writes `PriceUpdate` objects to `PriceCache`
2. **SSE endpoint** reads from `PriceCache` every ~500ms, pushes JSON to connected browsers
3. **Portfolio/Trade code** reads from `PriceCache` to value positions and execute trades

### Key Design Decisions

| Decision | Rationale |
|---|---|
| Strategy pattern (ABC) | Swap data sources via env var; downstream code unchanged |
| PriceCache as single truth | Decouples producers from consumers; one writer, many readers |
| Thread-safe cache with Lock | PriceCache may be accessed from async handlers and thread pool |
| Version counter on cache | SSE endpoint skips redundant sends when nothing changed |
| SSE over WebSockets | One-way push is sufficient; simpler, universal browser support |
| Cholesky-correlated GBM | Realistic correlated moves without full order book simulation |

---

## 2. File Structure

```
backend/app/market/
├── __init__.py             # Public API re-exports
├── models.py               # PriceUpdate immutable dataclass
├── cache.py                # PriceCache thread-safe in-memory store
├── interface.py            # MarketDataSource abstract base class
├── seed_prices.py          # Seed prices, GBM params, correlation groups
├── simulator.py            # GBMSimulator engine + SimulatorDataSource
├── massive_client.py       # MassiveDataSource (Polygon.io REST poller)
├── factory.py              # create_market_data_source() factory
└── stream.py               # SSE streaming endpoint factory
```

Total: ~500 lines of production code across 8 modules.

---

## 3. Data Model

**File:** `models.py`

The `PriceUpdate` is the single data type that flows through the entire system — from data source to cache to SSE to frontend.

### Design Choices

- **Frozen dataclass** — immutable once created; safe to share across threads/tasks
- **`slots=True`** — reduces memory footprint (many instances in flight)
- **Computed properties** — `change`, `change_percent`, `direction` derived from price fields
- **`to_dict()`** — JSON serialization for SSE transmission

### Implementation

```python
"""Data models for market data."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PriceUpdate:
    """Immutable snapshot of a single ticker's price at a point in time."""

    ticker: str
    price: float
    previous_price: float
    timestamp: float = field(default_factory=time.time)  # Unix seconds

    @property
    def change(self) -> float:
        """Absolute price change from previous update."""
        return round(self.price - self.previous_price, 4)

    @property
    def change_percent(self) -> float:
        """Percentage change from previous update."""
        if self.previous_price == 0:
            return 0.0
        return round(
            (self.price - self.previous_price) / self.previous_price * 100, 4
        )

    @property
    def direction(self) -> str:
        """'up', 'down', or 'flat'."""
        if self.price > self.previous_price:
            return "up"
        elif self.price < self.previous_price:
            return "down"
        return "flat"

    def to_dict(self) -> dict:
        """Serialize for JSON / SSE transmission."""
        return {
            "ticker": self.ticker,
            "price": self.price,
            "previous_price": self.previous_price,
            "timestamp": self.timestamp,
            "change": self.change,
            "change_percent": self.change_percent,
            "direction": self.direction,
        }
```

### Usage Examples

```python
# Creating a PriceUpdate
update = PriceUpdate(ticker="AAPL", price=191.50, previous_price=190.00)
assert update.direction == "up"
assert update.change == 1.5
assert update.change_percent == 0.7895  # ~0.79%

# Serialization for SSE
import json
json.dumps(update.to_dict())
# {"ticker":"AAPL","price":191.5,"previous_price":190.0,...,"direction":"up"}

# Immutability — this raises FrozenInstanceError:
update.price = 200.0  # TypeError!
```

---

## 4. Price Cache

**File:** `cache.py`

The `PriceCache` is the **single point of truth** for current prices. One data source writes to it; multiple consumers read from it.

### Design Choices

- **`threading.Lock`** — protects the internal dict; necessary because asyncio handlers may read while a thread-pool callback writes (Massive client uses `asyncio.to_thread`)
- **Version counter** — monotonically increasing int, bumped on every `update()`. The SSE endpoint compares `last_version` to `current_version` to skip redundant pushes
- **`previous_price` tracking** — the cache remembers the prior price for each ticker, so the `PriceUpdate` it creates always has correct direction/change data

### Implementation

```python
"""Thread-safe in-memory price cache."""

from __future__ import annotations

import time
from threading import Lock

from .models import PriceUpdate


class PriceCache:
    """Thread-safe in-memory cache of the latest price for each ticker.

    Writers: SimulatorDataSource or MassiveDataSource (one at a time).
    Readers: SSE streaming endpoint, portfolio valuation, trade execution.
    """

    def __init__(self) -> None:
        self._prices: dict[str, PriceUpdate] = {}
        self._lock = Lock()
        self._version: int = 0  # Monotonically increasing; bumped on every update

    def update(self, ticker: str, price: float, timestamp: float | None = None) -> PriceUpdate:
        """Record a new price for a ticker. Returns the created PriceUpdate.

        Automatically computes direction and change from the previous price.
        If this is the first update for the ticker, previous_price == price
        (direction='flat').
        """
        with self._lock:
            ts = timestamp or time.time()
            prev = self._prices.get(ticker)
            previous_price = prev.price if prev else price

            update = PriceUpdate(
                ticker=ticker,
                price=round(price, 2),
                previous_price=round(previous_price, 2),
                timestamp=ts,
            )
            self._prices[ticker] = update
            self._version += 1
            return update

    def get(self, ticker: str) -> PriceUpdate | None:
        """Get the latest price for a single ticker, or None if unknown."""
        with self._lock:
            return self._prices.get(ticker)

    def get_all(self) -> dict[str, PriceUpdate]:
        """Snapshot of all current prices. Returns a shallow copy."""
        with self._lock:
            return dict(self._prices)

    def get_price(self, ticker: str) -> float | None:
        """Convenience: get just the price float, or None."""
        update = self.get(ticker)
        return update.price if update else None

    def remove(self, ticker: str) -> None:
        """Remove a ticker from the cache (e.g., when removed from watchlist)."""
        with self._lock:
            self._prices.pop(ticker, None)

    @property
    def version(self) -> int:
        """Current version counter. Useful for SSE change detection."""
        return self._version

    def __len__(self) -> int:
        with self._lock:
            return len(self._prices)

    def __contains__(self, ticker: str) -> bool:
        with self._lock:
            return ticker in self._prices
```

### Usage Examples

```python
cache = PriceCache()

# First update — previous_price equals price (direction='flat')
update = cache.update("AAPL", 190.50)
assert update.direction == "flat"
assert cache.version == 1

# Second update — direction computed from prior price
update = cache.update("AAPL", 191.00)
assert update.direction == "up"
assert update.previous_price == 190.50
assert cache.version == 2

# Read operations
cache.get_price("AAPL")       # 191.0
cache.get("AAPL")             # PriceUpdate(ticker='AAPL', price=191.0, ...)
cache.get_all()               # {'AAPL': PriceUpdate(...)}
"AAPL" in cache               # True

# Remove
cache.remove("AAPL")
cache.get("AAPL")             # None
```

### Version-Based Change Detection

The version counter enables efficient SSE streaming:

```python
last_version = -1

while True:
    current_version = cache.version
    if current_version != last_version:
        last_version = current_version
        prices = cache.get_all()
        # ... send SSE event ...
    await asyncio.sleep(0.5)
```

This avoids serializing and sending identical data when no prices have changed (e.g., Massive poller with 15s intervals — the SSE loop runs at 500ms but only sends when the version bumps).

---

## 5. Unified Interface

**File:** `interface.py`

The `MarketDataSource` ABC defines the contract that both the simulator and Massive client implement. Downstream code (FastAPI lifecycle, watchlist routes) programs against this interface.

### Design Choices

- **Async methods** — both implementations use `asyncio.Task` for background work
- **Lifecycle model** — `start()` → `add_ticker()`/`remove_ticker()` → `stop()`
- **No price reading** — the interface does NOT expose prices; that's the cache's job. Sources only *write* to the cache.

### Implementation

```python
"""Abstract interface for market data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod


class MarketDataSource(ABC):
    """Contract for market data providers.

    Implementations push price updates into a shared PriceCache on their own
    schedule. Downstream code never calls the data source directly for prices —
    it reads from the cache.

    Lifecycle:
        source = create_market_data_source(cache)
        await source.start(["AAPL", "GOOGL", ...])
        # ... app runs ...
        await source.add_ticker("TSLA")
        await source.remove_ticker("GOOGL")
        # ... app shutting down ...
        await source.stop()
    """

    @abstractmethod
    async def start(self, tickers: list[str]) -> None:
        """Begin producing price updates for the given tickers.

        Starts a background task that periodically writes to the PriceCache.
        Must be called exactly once. Calling start() twice is undefined behavior.
        """

    @abstractmethod
    async def stop(self) -> None:
        """Stop the background task and release resources.

        Safe to call multiple times. After stop(), the source will not write
        to the cache again.
        """

    @abstractmethod
    async def add_ticker(self, ticker: str) -> None:
        """Add a ticker to the active set. No-op if already present.

        The next update cycle will include this ticker.
        """

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Remove a ticker from the active set. No-op if not present.

        Also removes the ticker from the PriceCache.
        """

    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Return the current list of actively tracked tickers."""
```

### How Downstream Code Uses It

```python
# In FastAPI lifespan:
source: MarketDataSource = create_market_data_source(cache)
await source.start(watchlist_tickers)

# In watchlist routes:
@router.post("/api/watchlist")
async def add_to_watchlist(ticker: str):
    # ... save to DB ...
    await source.add_ticker(ticker)

@router.delete("/api/watchlist/{ticker}")
async def remove_from_watchlist(ticker: str):
    # ... delete from DB ...
    await source.remove_ticker(ticker)

# In shutdown:
await source.stop()
```

---

## 6. Seed Prices & Ticker Parameters

**File:** `seed_prices.py`

Constants used by the GBM simulator to create realistic price behavior.

### Implementation

```python
"""Seed prices and per-ticker parameters for the market simulator."""

# Realistic starting prices for the default watchlist
SEED_PRICES: dict[str, float] = {
    "AAPL": 190.00,
    "GOOGL": 175.00,
    "MSFT": 420.00,
    "AMZN": 185.00,
    "TSLA": 250.00,
    "NVDA": 800.00,
    "META": 500.00,
    "JPM": 195.00,
    "V": 280.00,
    "NFLX": 600.00,
}

# Per-ticker GBM parameters
# sigma: annualized volatility (higher = more price movement per tick)
# mu: annualized drift / expected return
TICKER_PARAMS: dict[str, dict[str, float]] = {
    "AAPL": {"sigma": 0.22, "mu": 0.05},
    "GOOGL": {"sigma": 0.25, "mu": 0.05},
    "MSFT": {"sigma": 0.20, "mu": 0.05},
    "AMZN": {"sigma": 0.28, "mu": 0.05},
    "TSLA": {"sigma": 0.50, "mu": 0.03},   # High volatility
    "NVDA": {"sigma": 0.40, "mu": 0.08},   # High volatility, strong drift
    "META": {"sigma": 0.30, "mu": 0.05},
    "JPM": {"sigma": 0.18, "mu": 0.04},    # Low volatility (bank)
    "V": {"sigma": 0.17, "mu": 0.04},      # Low volatility (payments)
    "NFLX": {"sigma": 0.35, "mu": 0.05},
}

# Default parameters for dynamically added tickers (not in the list above)
DEFAULT_PARAMS: dict[str, float] = {"sigma": 0.25, "mu": 0.05}

# Correlation groups for the simulator's Cholesky decomposition
CORRELATION_GROUPS: dict[str, set[str]] = {
    "tech": {"AAPL", "GOOGL", "MSFT", "AMZN", "META", "NVDA", "NFLX"},
    "finance": {"JPM", "V"},
}

# Correlation coefficients
INTRA_TECH_CORR = 0.6       # Tech stocks move together
INTRA_FINANCE_CORR = 0.5    # Finance stocks move together
CROSS_GROUP_CORR = 0.3      # Between sectors / unknown tickers
TSLA_CORR = 0.3             # TSLA does its own thing (despite being in tech set)
```

### How Dynamically Added Tickers Work

When the user adds a new ticker (e.g., "PYPL") via the watchlist or AI chat:

1. Not in `SEED_PRICES` → simulator assigns a random price between $50-$300
2. Not in `TICKER_PARAMS` → simulator uses `DEFAULT_PARAMS` (sigma=0.25, mu=0.05)
3. Not in `CORRELATION_GROUPS` → pairwise correlation falls through to `CROSS_GROUP_CORR` (0.3)
4. Cholesky matrix is rebuilt to incorporate the new ticker

---

## 7. GBM Simulator

**File:** `simulator.py`

The simulator has two classes: `GBMSimulator` (pure math engine) and `SimulatorDataSource` (async lifecycle wrapper that implements `MarketDataSource`).

### GBM Math

For each tick (every 500ms), the simulator applies:

```
S(t+dt) = S(t) * exp((mu - sigma²/2) * dt + sigma * sqrt(dt) * Z)
```

Where:
- `S(t)` = current price
- `mu` = annualized drift
- `sigma` = annualized volatility
- `dt` = time step as fraction of a trading year (500ms ≈ 8.48e-8)
- `Z` = correlated standard normal (via Cholesky decomposition)

The tiny `dt` produces sub-cent moves per tick that accumulate naturally. Over a session, stocks drift realistically based on their volatility parameters.

### Correlated Moves via Cholesky Decomposition

To make tech stocks move together (and separately from finance stocks), we:

1. Build an N×N correlation matrix based on sector groupings
2. Compute its Cholesky decomposition L (where L·L^T = correlation matrix)
3. Each tick: generate N independent standard normals, multiply by L to get correlated normals

```
Z_correlated = L @ Z_independent
```

This means when AAPL goes up, MSFT is likely (ρ=0.6) to go up too, while JPM moves more independently (ρ=0.3).

### Random Shock Events

For visual drama, ~0.1% chance per tick per ticker of a sudden 2-5% shock:
- With 10 tickers at 2 ticks/sec → expect an event roughly every 50 seconds
- Shock direction is random (up or down)
- Creates the kind of sudden moves that make the UI sparklines interesting

### GBMSimulator Implementation

```python
"""GBM-based market simulator."""

from __future__ import annotations

import asyncio
import logging
import math
import random

import numpy as np

from .cache import PriceCache
from .interface import MarketDataSource
from .seed_prices import (
    CORRELATION_GROUPS, CROSS_GROUP_CORR, DEFAULT_PARAMS,
    INTRA_FINANCE_CORR, INTRA_TECH_CORR, SEED_PRICES,
    TICKER_PARAMS, TSLA_CORR,
)

logger = logging.getLogger(__name__)


class GBMSimulator:
    """Geometric Brownian Motion simulator for correlated stock prices."""

    # 500ms as fraction of trading year
    # 252 trading days * 6.5 hours/day * 3600 seconds/hour = 5,896,800 seconds
    TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600  # 5,896,800
    DEFAULT_DT = 0.5 / TRADING_SECONDS_PER_YEAR   # ~8.48e-8

    def __init__(
        self,
        tickers: list[str],
        dt: float = DEFAULT_DT,
        event_probability: float = 0.001,
    ) -> None:
        self._dt = dt
        self._event_prob = event_probability
        self._tickers: list[str] = []
        self._prices: dict[str, float] = {}
        self._params: dict[str, dict[str, float]] = {}
        self._cholesky: np.ndarray | None = None

        for ticker in tickers:
            self._add_ticker_internal(ticker)
        self._rebuild_cholesky()

    def step(self) -> dict[str, float]:
        """Advance all tickers by one time step. Returns {ticker: new_price}.

        This is the hot path — called every 500ms.
        """
        n = len(self._tickers)
        if n == 0:
            return {}

        z_independent = np.random.standard_normal(n)

        if self._cholesky is not None:
            z_correlated = self._cholesky @ z_independent
        else:
            z_correlated = z_independent

        result: dict[str, float] = {}
        for i, ticker in enumerate(self._tickers):
            params = self._params[ticker]
            mu = params["mu"]
            sigma = params["sigma"]

            # GBM formula
            drift = (mu - 0.5 * sigma**2) * self._dt
            diffusion = sigma * math.sqrt(self._dt) * z_correlated[i]
            self._prices[ticker] *= math.exp(drift + diffusion)

            # Random shock event (~0.1% chance per tick)
            if random.random() < self._event_prob:
                shock_magnitude = random.uniform(0.02, 0.05)
                shock_sign = random.choice([-1, 1])
                self._prices[ticker] *= 1 + shock_magnitude * shock_sign
                logger.debug(
                    "Random event on %s: %.1f%% %s",
                    ticker, shock_magnitude * 100,
                    "up" if shock_sign > 0 else "down",
                )

            result[ticker] = round(self._prices[ticker], 2)

        return result

    def add_ticker(self, ticker: str) -> None:
        """Add a ticker. Rebuilds correlation matrix."""
        if ticker in self._prices:
            return
        self._add_ticker_internal(ticker)
        self._rebuild_cholesky()

    def remove_ticker(self, ticker: str) -> None:
        """Remove a ticker. Rebuilds correlation matrix."""
        if ticker not in self._prices:
            return
        self._tickers.remove(ticker)
        del self._prices[ticker]
        del self._params[ticker]
        self._rebuild_cholesky()

    def get_price(self, ticker: str) -> float | None:
        return self._prices.get(ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

    def _add_ticker_internal(self, ticker: str) -> None:
        """Add without rebuilding Cholesky (for batch init)."""
        if ticker in self._prices:
            return
        self._tickers.append(ticker)
        self._prices[ticker] = SEED_PRICES.get(ticker, random.uniform(50.0, 300.0))
        self._params[ticker] = TICKER_PARAMS.get(ticker, dict(DEFAULT_PARAMS))

    def _rebuild_cholesky(self) -> None:
        """Rebuild Cholesky decomposition. O(n^2) but n < 50."""
        n = len(self._tickers)
        if n <= 1:
            self._cholesky = None
            return

        corr = np.eye(n)
        for i in range(n):
            for j in range(i + 1, n):
                rho = self._pairwise_correlation(self._tickers[i], self._tickers[j])
                corr[i, j] = rho
                corr[j, i] = rho

        self._cholesky = np.linalg.cholesky(corr)

    @staticmethod
    def _pairwise_correlation(t1: str, t2: str) -> float:
        """Correlation based on sector grouping."""
        tech = CORRELATION_GROUPS["tech"]
        finance = CORRELATION_GROUPS["finance"]

        if t1 == "TSLA" or t2 == "TSLA":
            return TSLA_CORR
        if t1 in tech and t2 in tech:
            return INTRA_TECH_CORR
        if t1 in finance and t2 in finance:
            return INTRA_FINANCE_CORR
        return CROSS_GROUP_CORR
```

### SimulatorDataSource Implementation

This wraps `GBMSimulator` with the `MarketDataSource` lifecycle:

```python
class SimulatorDataSource(MarketDataSource):
    """MarketDataSource backed by the GBM simulator.

    Runs a background asyncio task that calls GBMSimulator.step() every
    500ms and writes results to the PriceCache.
    """

    def __init__(
        self,
        price_cache: PriceCache,
        update_interval: float = 0.5,
        event_probability: float = 0.001,
    ) -> None:
        self._cache = price_cache
        self._interval = update_interval
        self._event_prob = event_probability
        self._sim: GBMSimulator | None = None
        self._task: asyncio.Task | None = None

    async def start(self, tickers: list[str]) -> None:
        self._sim = GBMSimulator(
            tickers=tickers,
            event_probability=self._event_prob,
        )
        # Seed the cache immediately so SSE has data from the start
        for ticker in tickers:
            price = self._sim.get_price(ticker)
            if price is not None:
                self._cache.update(ticker=ticker, price=price)
        self._task = asyncio.create_task(self._run_loop(), name="simulator-loop")
        logger.info("Simulator started with %d tickers", len(tickers))

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("Simulator stopped")

    async def add_ticker(self, ticker: str) -> None:
        if self._sim:
            self._sim.add_ticker(ticker)
            price = self._sim.get_price(ticker)
            if price is not None:
                self._cache.update(ticker=ticker, price=price)
            logger.info("Simulator: added ticker %s", ticker)

    async def remove_ticker(self, ticker: str) -> None:
        if self._sim:
            self._sim.remove_ticker(ticker)
        self._cache.remove(ticker)
        logger.info("Simulator: removed ticker %s", ticker)

    def get_tickers(self) -> list[str]:
        return self._sim.get_tickers() if self._sim else []

    async def _run_loop(self) -> None:
        """Core loop: step the simulation, write to cache, sleep."""
        while True:
            try:
                if self._sim:
                    prices = self._sim.step()
                    for ticker, price in prices.items():
                        self._cache.update(ticker=ticker, price=price)
            except Exception:
                logger.exception("Simulator step failed")
            await asyncio.sleep(self._interval)
```

### Simulator Behavior Example

```
t=0.0s  AAPL=$190.00  GOOGL=$175.00  TSLA=$250.00  (seed prices)
t=0.5s  AAPL=$190.01  GOOGL=$175.01  TSLA=$249.97  (normal GBM ticks)
t=1.0s  AAPL=$190.03  GOOGL=$175.02  TSLA=$250.05
t=1.5s  AAPL=$190.02  GOOGL=$175.01  TSLA=$250.03
  ...
t=47s   AAPL=$190.15  GOOGL=$175.12  TSLA=$258.50  (shock! +3.4% on TSLA)
t=47.5s AAPL=$190.16  GOOGL=$175.13  TSLA=$258.48  (normal ticks resume)
```

Notice: AAPL and GOOGL move in similar directions (tech correlation 0.6), while TSLA is more independent (0.3).

---

## 8. Massive API Client

**File:** `massive_client.py`

The Massive (Polygon.io) client polls the REST API for real market data and writes to the same `PriceCache`.

### How It Works

1. On `start()`, creates a `RESTClient` with the API key and does an immediate first poll
2. Background task polls at a configurable interval (default 15s for free tier)
3. Each poll: single API call for ALL watched tickers → parse snapshots → update cache
4. The REST client is synchronous, so polls run via `asyncio.to_thread()` to avoid blocking

### Rate Limits

| Tier | Rate Limit | Recommended Interval |
|------|-----------|---------------------|
| Free | 5 req/min | 15 seconds |
| Starter | 100 req/min | 5 seconds |
| Developer+ | 1000+ req/min | 2 seconds |

### API Endpoint Used

```
GET /v2/snapshot/locale/us/markets/stocks/tickers
    ?tickers=AAPL,GOOGL,MSFT,...
```

Returns a snapshot for each ticker including `last_trade.price` and `last_trade.timestamp` (Unix milliseconds).

### Implementation

```python
"""Massive (Polygon.io) API client for real market data."""

from __future__ import annotations

import asyncio
import logging

from massive import RESTClient
from massive.rest.models import SnapshotMarketType

from .cache import PriceCache
from .interface import MarketDataSource

logger = logging.getLogger(__name__)


class MassiveDataSource(MarketDataSource):
    """MarketDataSource backed by the Massive (Polygon.io) REST API.

    Polls snapshot endpoint for all watched tickers in a single API call,
    then writes results to the PriceCache.
    """

    def __init__(
        self,
        api_key: str,
        price_cache: PriceCache,
        poll_interval: float = 15.0,
    ) -> None:
        self._api_key = api_key
        self._cache = price_cache
        self._interval = poll_interval
        self._tickers: list[str] = []
        self._task: asyncio.Task | None = None
        self._client: RESTClient | None = None

    async def start(self, tickers: list[str]) -> None:
        self._client = RESTClient(api_key=self._api_key)
        self._tickers = list(tickers)

        # Immediate first poll so the cache has data right away
        await self._poll_once()

        self._task = asyncio.create_task(self._poll_loop(), name="massive-poller")
        logger.info(
            "Massive poller started: %d tickers, %.1fs interval",
            len(tickers), self._interval,
        )

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self._client = None
        logger.info("Massive poller stopped")

    async def add_ticker(self, ticker: str) -> None:
        ticker = ticker.upper().strip()
        if ticker not in self._tickers:
            self._tickers.append(ticker)
            logger.info("Massive: added ticker %s (will appear on next poll)", ticker)

    async def remove_ticker(self, ticker: str) -> None:
        ticker = ticker.upper().strip()
        self._tickers = [t for t in self._tickers if t != ticker]
        self._cache.remove(ticker)
        logger.info("Massive: removed ticker %s", ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

    # --- Internal ---

    async def _poll_loop(self) -> None:
        """Poll on interval. First poll already happened in start()."""
        while True:
            await asyncio.sleep(self._interval)
            await self._poll_once()

    async def _poll_once(self) -> None:
        """Execute one poll cycle: fetch snapshots, update cache."""
        if not self._tickers or not self._client:
            return

        try:
            # RESTClient is synchronous — run in thread to avoid blocking
            snapshots = await asyncio.to_thread(self._fetch_snapshots)
            processed = 0
            for snap in snapshots:
                try:
                    price = snap.last_trade.price
                    # Massive timestamps are Unix milliseconds → convert to seconds
                    timestamp = snap.last_trade.timestamp / 1000.0
                    self._cache.update(
                        ticker=snap.ticker,
                        price=price,
                        timestamp=timestamp,
                    )
                    processed += 1
                except (AttributeError, TypeError) as e:
                    logger.warning(
                        "Skipping snapshot for %s: %s",
                        getattr(snap, "ticker", "???"), e,
                    )
            logger.debug(
                "Massive poll: updated %d/%d tickers",
                processed, len(self._tickers),
            )

        except Exception as e:
            logger.error("Massive poll failed: %s", e)
            # Don't re-raise — the loop retries on next interval.
            # Common: 401 (bad key), 429 (rate limit), network errors.

    def _fetch_snapshots(self) -> list:
        """Synchronous call to Massive REST API. Runs in a thread."""
        return self._client.get_snapshot_all(
            market_type=SnapshotMarketType.STOCKS,
            tickers=self._tickers,
        )
```

### Key Differences from Simulator

| Aspect | Simulator | Massive |
|--------|-----------|---------|
| Update frequency | 500ms | 15s (free) to 2s (paid) |
| Data source | Math (GBM) | Real Polygon.io API |
| Ticker addition | Immediate (next tick) | Next poll cycle |
| Dependencies | numpy | massive package + API key |
| Offline capable | Yes | No |
| Threading | Pure asyncio | `asyncio.to_thread` for sync REST client |

### Error Handling

The Massive client handles these failure modes gracefully:

- **401 Unauthorized** — bad API key; logged as error, retries (in case key was rotated)
- **429 Rate Limited** — too many requests; logged, waits for next interval
- **Network errors** — connection failures; logged, retries next interval
- **Malformed snapshots** — individual snapshots with missing fields are skipped with a warning
- **All errors are non-fatal** — the poll loop continues; the cache retains the last known prices

---

## 9. Factory

**File:** `factory.py`

Simple factory function that selects the data source based on environment variables.

### Implementation

```python
"""Factory for creating market data sources."""

from __future__ import annotations

import logging
import os

from .cache import PriceCache
from .interface import MarketDataSource
from .massive_client import MassiveDataSource
from .simulator import SimulatorDataSource

logger = logging.getLogger(__name__)


def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    """Create the appropriate market data source based on environment variables.

    - MASSIVE_API_KEY set and non-empty → MassiveDataSource (real market data)
    - Otherwise → SimulatorDataSource (GBM simulation)

    Returns an unstarted source. Caller must await source.start(tickers).
    """
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()

    if api_key:
        logger.info("Market data source: Massive API (real data)")
        return MassiveDataSource(api_key=api_key, price_cache=price_cache)
    else:
        logger.info("Market data source: GBM Simulator")
        return SimulatorDataSource(price_cache=price_cache)
```

### Usage

```python
from app.market import PriceCache, create_market_data_source

cache = PriceCache()
source = create_market_data_source(cache)  # Reads MASSIVE_API_KEY env var

# Returns MassiveDataSource if key exists, SimulatorDataSource otherwise
# Either way, the caller uses the same MarketDataSource interface
await source.start(["AAPL", "GOOGL", "MSFT"])
```

---

## 10. SSE Streaming

**File:** `stream.py`

The SSE endpoint pushes live price data to connected browser clients.

### Design Choices

- **Factory pattern** — `create_stream_router(cache)` injects the `PriceCache` without globals
- **Version-based change detection** — only sends when cache has been updated
- **`retry: 1000` directive** — tells `EventSource` to reconnect after 1 second on disconnect
- **Client disconnect detection** — checks `request.is_disconnected()` to clean up server-side

### SSE Protocol

The SSE format is simple text:

```
retry: 1000\n\n
data: {"AAPL":{"ticker":"AAPL","price":190.50,...},"GOOGL":{...}}\n\n
data: {"AAPL":{"ticker":"AAPL","price":190.51,...},"GOOGL":{...}}\n\n
```

Each `data:` line is followed by two newlines. The browser's `EventSource` API parses this automatically.

### Implementation

```python
"""SSE streaming endpoint for live price updates."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from .cache import PriceCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stream", tags=["streaming"])


def create_stream_router(price_cache: PriceCache) -> APIRouter:
    """Create the SSE streaming router with a reference to the price cache."""

    @router.get("/prices")
    async def stream_prices(request: Request) -> StreamingResponse:
        """SSE endpoint for live price updates.

        Streams all tracked ticker prices every ~500ms. Client connects with
        EventSource and receives:

            data: {"AAPL": {"ticker": "AAPL", "price": 190.50, ...}, ...}
        """
        return StreamingResponse(
            _generate_events(price_cache, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering if proxied
            },
        )

    return router


async def _generate_events(
    price_cache: PriceCache,
    request: Request,
    interval: float = 0.5,
) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE-formatted price events."""
    yield "retry: 1000\n\n"

    last_version = -1
    client_ip = request.client.host if request.client else "unknown"
    logger.info("SSE client connected: %s", client_ip)

    try:
        while True:
            if await request.is_disconnected():
                logger.info("SSE client disconnected: %s", client_ip)
                break

            current_version = price_cache.version
            if current_version != last_version:
                last_version = current_version
                prices = price_cache.get_all()

                if prices:
                    data = {
                        ticker: update.to_dict()
                        for ticker, update in prices.items()
                    }
                    payload = json.dumps(data)
                    yield f"data: {payload}\n\n"

            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logger.info("SSE stream cancelled for: %s", client_ip)
```

### Frontend Integration

```javascript
// Browser-side EventSource usage
const source = new EventSource('/api/stream/prices');

source.onmessage = (event) => {
    const prices = JSON.parse(event.data);
    // prices = {
    //   "AAPL": { ticker: "AAPL", price: 190.50, previous_price: 190.48,
    //             change: 0.02, change_percent: 0.0105, direction: "up", ... },
    //   "GOOGL": { ... },
    //   ...
    // }

    for (const [ticker, update] of Object.entries(prices)) {
        updateTickerUI(ticker, update);
        if (update.direction === 'up') flashGreen(ticker);
        if (update.direction === 'down') flashRed(ticker);
    }
};

source.onerror = () => {
    // EventSource auto-reconnects using the retry: 1000 directive
    setConnectionStatus('reconnecting');
};
```

---

## 11. FastAPI Lifecycle Integration

The market data system integrates with FastAPI's lifespan context manager for clean startup and shutdown.

### Implementation Pattern

```python
# backend/app/main.py (relevant excerpt)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.market import PriceCache, create_market_data_source, create_stream_router

# Module-level singletons (shared across the app)
price_cache = PriceCache()
market_source = create_market_data_source(price_cache)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load watchlist from DB, start market data.
    Shutdown: stop market data cleanly.
    """
    # Load initial watchlist from database
    watchlist_tickers = await get_watchlist_tickers_from_db()
    # e.g., ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]

    # Start the market data source (simulator or Massive)
    await market_source.start(watchlist_tickers)

    yield  # App is running

    # Clean shutdown
    await market_source.stop()


app = FastAPI(lifespan=lifespan)

# Mount the SSE streaming router
stream_router = create_stream_router(price_cache)
app.include_router(stream_router)
```

### Startup Sequence

```
1. FastAPI starts → lifespan enters
2. Load watchlist tickers from SQLite
3. create_market_data_source() → reads MASSIVE_API_KEY
4. source.start(tickers) → starts background task
   - Simulator: seeds cache, starts GBM loop
   - Massive: does first poll, starts poll loop
5. yield → app serves requests
6. SSE clients connect → read from cache every 500ms
```

### Shutdown Sequence

```
1. SIGTERM/SIGINT received
2. lifespan exits yield
3. source.stop() → cancels background task, awaits completion
4. SSE connections close (FastAPI handles this)
5. App exits
```

---

## 12. Watchlist Coordination

When tickers are added or removed from the watchlist, both the database and the market data source must be updated.

### Add Ticker Flow

```python
@router.post("/api/watchlist")
async def add_to_watchlist(body: WatchlistAdd):
    ticker = body.ticker.upper().strip()

    # 1. Save to database
    await db.add_watchlist_ticker(ticker)

    # 2. Tell the data source to start tracking it
    await market_source.add_ticker(ticker)
    # Simulator: adds to GBM, rebuilds Cholesky, seeds cache immediately
    # Massive: adds to poll list, data appears on next poll cycle

    return {"ticker": ticker, "status": "added"}
```

### Remove Ticker Flow

```python
@router.delete("/api/watchlist/{ticker}")
async def remove_from_watchlist(ticker: str):
    ticker = ticker.upper().strip()

    # 1. Delete from database
    await db.remove_watchlist_ticker(ticker)

    # 2. Stop tracking and remove from cache
    await market_source.remove_ticker(ticker)
    # Both sources: remove from active list + cache.remove(ticker)

    return {"ticker": ticker, "status": "removed"}
```

### AI Chat Watchlist Changes

The LLM can also add/remove tickers. The chat handler processes `watchlist_changes` from the structured output:

```python
for change in llm_response.watchlist_changes:
    if change.action == "add":
        await market_source.add_ticker(change.ticker)
        await db.add_watchlist_ticker(change.ticker)
    elif change.action == "remove":
        await market_source.remove_ticker(change.ticker)
        await db.remove_watchlist_ticker(change.ticker)
```

---

## 13. Testing Strategy

### Test Structure

```
backend/tests/market/
├── test_models.py              # 11 tests — PriceUpdate properties, edge cases
├── test_cache.py               # 13 tests — thread safety, version counter
├── test_simulator.py           # 17 tests — GBM math, correlation, shocks
├── test_simulator_source.py    # 10 tests — async lifecycle integration
├── test_factory.py             #  7 tests — env var switching
└── test_massive.py             # 13 tests — API response parsing, error handling
```

**Total: 73 tests, all passing. 84% code coverage.**

### Key Test Examples

#### PriceUpdate Model Tests

```python
def test_direction_up():
    update = PriceUpdate(ticker="AAPL", price=191.0, previous_price=190.0)
    assert update.direction == "up"
    assert update.change == 1.0
    assert update.change_percent == pytest.approx(0.5263, rel=1e-2)

def test_direction_flat():
    update = PriceUpdate(ticker="AAPL", price=190.0, previous_price=190.0)
    assert update.direction == "flat"
    assert update.change == 0.0

def test_immutability():
    update = PriceUpdate(ticker="AAPL", price=190.0, previous_price=189.0)
    with pytest.raises(AttributeError):
        update.price = 200.0

def test_to_dict_serialization():
    update = PriceUpdate(ticker="AAPL", price=191.5, previous_price=190.0, timestamp=1000.0)
    d = update.to_dict()
    assert d["ticker"] == "AAPL"
    assert d["direction"] == "up"
    assert json.dumps(d)  # Must be JSON-serializable
```

#### PriceCache Tests

```python
def test_version_increments():
    cache = PriceCache()
    assert cache.version == 0
    cache.update("AAPL", 190.0)
    assert cache.version == 1
    cache.update("AAPL", 191.0)
    assert cache.version == 2

def test_previous_price_tracking():
    cache = PriceCache()
    u1 = cache.update("AAPL", 190.0)
    assert u1.previous_price == 190.0  # First update: prev == current
    u2 = cache.update("AAPL", 191.0)
    assert u2.previous_price == 190.0  # Second update: prev from u1

def test_thread_safety():
    """Concurrent updates from multiple threads don't corrupt state."""
    cache = PriceCache()
    import threading

    def writer(start):
        for i in range(1000):
            cache.update(f"T{start}", float(i))

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert cache.version == 10000
    assert len(cache) == 10
```

#### GBM Simulator Tests

```python
def test_step_returns_all_tickers():
    sim = GBMSimulator(["AAPL", "GOOGL"])
    result = sim.step()
    assert set(result.keys()) == {"AAPL", "GOOGL"}
    assert all(isinstance(v, float) for v in result.values())

def test_prices_change_over_time():
    sim = GBMSimulator(["AAPL"])
    initial = sim.get_price("AAPL")
    for _ in range(1000):
        sim.step()
    final = sim.get_price("AAPL")
    assert final != initial  # Extremely unlikely to be exact same after 1000 steps

def test_correlation_matrix_is_valid():
    """Cholesky decomposition succeeds (matrix is positive definite)."""
    sim = GBMSimulator(list(SEED_PRICES.keys()))
    assert sim._cholesky is not None
    assert sim._cholesky.shape == (10, 10)

def test_add_ticker_rebuilds_cholesky():
    sim = GBMSimulator(["AAPL", "GOOGL"])
    assert sim._cholesky.shape == (2, 2)
    sim.add_ticker("MSFT")
    assert sim._cholesky.shape == (3, 3)

def test_shock_events_occur():
    """With high probability, at least one shock in many steps."""
    sim = GBMSimulator(["AAPL"], event_probability=0.5)  # 50% for test speed
    prices = [sim.step()["AAPL"] for _ in range(100)]
    # With 50% shock probability, price should vary significantly
    assert max(prices) / min(prices) > 1.01
```

#### Factory Tests

```python
def test_returns_simulator_when_no_key(monkeypatch):
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    cache = PriceCache()
    source = create_market_data_source(cache)
    assert isinstance(source, SimulatorDataSource)

def test_returns_massive_when_key_set(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "test-key-123")
    cache = PriceCache()
    source = create_market_data_source(cache)
    assert isinstance(source, MassiveDataSource)

def test_ignores_empty_key(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "  ")
    cache = PriceCache()
    source = create_market_data_source(cache)
    assert isinstance(source, SimulatorDataSource)
```

#### Massive Client Tests

```python
async def test_poll_updates_cache():
    cache = PriceCache()
    source = MassiveDataSource(api_key="test", price_cache=cache)
    source._client = MagicMock()

    # Mock a snapshot response
    mock_snap = MagicMock()
    mock_snap.ticker = "AAPL"
    mock_snap.last_trade.price = 192.50
    mock_snap.last_trade.timestamp = 1700000000000  # Unix ms
    source._client.get_snapshot_all.return_value = [mock_snap]
    source._tickers = ["AAPL"]

    await source._poll_once()

    update = cache.get("AAPL")
    assert update is not None
    assert update.price == 192.50
    assert update.timestamp == 1700000000.0  # Converted to seconds

async def test_poll_handles_api_error():
    """API errors don't crash the poller — it logs and retries next cycle."""
    cache = PriceCache()
    source = MassiveDataSource(api_key="test", price_cache=cache)
    source._client = MagicMock()
    source._client.get_snapshot_all.side_effect = Exception("Network error")
    source._tickers = ["AAPL"]

    await source._poll_once()  # Should not raise
    assert cache.get("AAPL") is None  # No data written
```

---

## 14. Error Handling & Edge Cases

### Simulator Edge Cases

| Scenario | Behavior |
|---|---|
| Empty ticker list | `step()` returns `{}`, no crash |
| Single ticker | Cholesky is `None`, uses raw standard normal |
| Dynamic ticker not in seed data | Random price $50-$300, default params |
| GBM produces negative price | Mathematically impossible — `exp()` is always positive |
| Simulator step exception | Logged, loop continues on next interval |

### Massive Edge Cases

| Scenario | Behavior |
|---|---|
| Invalid API key | 401 error logged, retries on next interval |
| Rate limited | 429 error logged, backs off to next interval |
| Snapshot missing fields | Individual snapshot skipped with warning |
| Network timeout | Exception caught, logged, retries |
| Market closed (no trades) | Last known price remains in cache |
| Empty ticker list | `_poll_once()` returns early, no API call |

### SSE Edge Cases

| Scenario | Behavior |
|---|---|
| No prices in cache | No `data:` event sent (only `retry:` directive) |
| Client disconnects | Detected via `is_disconnected()`, generator exits |
| Server shutdown | `CancelledError` caught, stream cleaned up |
| Multiple SSE clients | Each gets independent generator; all read same cache |

---

## 15. Configuration Summary

All tunable parameters with their defaults and locations:

| Parameter | Default | Location | Description |
|---|---|---|---|
| `MASSIVE_API_KEY` | (empty) | Environment | Polygon.io API key; if set, uses real data |
| Simulator update interval | 0.5s | `SimulatorDataSource.__init__` | How often GBM ticks |
| Simulator event probability | 0.001 | `GBMSimulator.__init__` | Chance of shock per tick per ticker |
| Massive poll interval | 15.0s | `MassiveDataSource.__init__` | How often to poll the API |
| SSE push interval | 0.5s | `_generate_events()` | How often SSE checks for changes |
| SSE retry directive | 1000ms | `_generate_events()` | Browser reconnect delay |
| GBM dt | ~8.48e-8 | `GBMSimulator.DEFAULT_DT` | Time step as fraction of trading year |
| Seed prices | 10 tickers | `seed_prices.py` | Starting prices for default watchlist |
| Per-ticker sigma/mu | varies | `seed_prices.py` | Volatility and drift per ticker |
| Correlation coefficients | 0.3-0.6 | `seed_prices.py` | Sector-based correlation strengths |

---

## Module Public API (`__init__.py`)

```python
"""Market data subsystem for FinAlly."""

from .cache import PriceCache
from .factory import create_market_data_source
from .interface import MarketDataSource
from .models import PriceUpdate
from .stream import create_stream_router

__all__ = [
    "PriceUpdate",
    "PriceCache",
    "MarketDataSource",
    "create_market_data_source",
    "create_stream_router",
]
```

### Quick Start for Downstream Code

```python
from app.market import PriceCache, create_market_data_source

# Startup
cache = PriceCache()
source = create_market_data_source(cache)  # Reads MASSIVE_API_KEY
await source.start(["AAPL", "GOOGL", "MSFT", ...])

# Read prices (from anywhere in the app)
update = cache.get("AAPL")          # PriceUpdate or None
price = cache.get_price("AAPL")     # float or None
all_prices = cache.get_all()        # dict[str, PriceUpdate]

# Dynamic watchlist
await source.add_ticker("TSLA")
await source.remove_ticker("GOOGL")

# Shutdown
await source.stop()
```

### Dependencies

```toml
# pyproject.toml
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "numpy>=2.0.0",
    "massive>=1.0.0",
]
```
