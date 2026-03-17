"""Unit tests for the GBM market data simulator."""

import asyncio
import math

import pytest

from app.market_data.base import PriceCache, PriceUpdate
from app.market_data.simulator import (
    DEFAULT_SEED_PRICES,
    MarketDataSimulator,
    _TECH_TICKERS,
)


@pytest.fixture
def cache() -> PriceCache:
    return PriceCache()


@pytest.fixture
def sim(cache: PriceCache) -> MarketDataSimulator:
    """A simulator with a fast tick interval and a fixed seed for reproducibility."""
    return MarketDataSimulator(cache=cache, tick_interval=0.01, seed=42)


class TestSimulatorSetup:
    def test_starts_not_running(self, sim):
        assert not sim.is_running

    def test_add_ticker_initialises_price(self, sim):
        sim.add_ticker("AAPL")
        assert "AAPL" in sim.tickers
        assert sim._prices["AAPL"] > 0

    def test_add_ticker_normalises_to_upper(self, sim):
        sim.add_ticker("aapl")
        assert "AAPL" in sim.tickers

    def test_remove_ticker_removes_from_set_and_prices(self, sim, cache):
        sim.add_ticker("AAPL")
        sim.remove_ticker("AAPL")
        assert "AAPL" not in sim.tickers
        assert sim._prices.get("AAPL") is None
        assert cache.get("AAPL") is None

    def test_remove_nonexistent_ticker_is_safe(self, sim):
        sim.remove_ticker("ZZZZZ")  # must not raise

    def test_seed_price_near_default_for_known_ticker(self, sim):
        price = sim._seed_price("AAPL")
        expected = DEFAULT_SEED_PRICES["AAPL"]
        # Within ±3% of the seed value (accounting for jitter)
        assert abs(price - expected) / expected < 0.03

    def test_seed_price_falls_back_for_unknown_ticker(self, sim):
        price = sim._seed_price("ZZZZ")
        assert price > 0


class TestGBMMath:
    def test_next_price_positive(self, sim):
        sim.add_ticker("AAPL")
        for _ in range(50):
            price = sim._next_price("AAPL", 190.0, 0.0)
            assert price > 0

    def test_next_price_stays_near_seed_over_few_ticks(self, sim):
        """Over a small number of ticks the price should stay in a plausible range."""
        sim.add_ticker("TSLA")
        current = 250.0
        for _ in range(100):
            current = sim._next_price("TSLA", current, 0.0)
        # Allow for ±30% drift over 100 fast ticks — very generous
        assert 175.0 < current < 325.0

    def test_unknown_ticker_uses_default_params(self, sim):
        sim.add_ticker("ZZZZ")
        price = sim._next_price("ZZZZ", 100.0, 0.0)
        assert price > 0

    def test_negative_sector_shock_does_not_crash(self, sim):
        sim.add_ticker("NVDA")
        price = sim._next_price("NVDA", 875.0, -3.0)
        assert price > 0

    def test_large_positive_sector_shock_increases_tech_price_on_average(self):
        """With a very large positive sector shock, tech prices should generally rise."""
        cache = PriceCache()
        sim = MarketDataSimulator(cache=cache, tick_interval=0.5, seed=0)
        sim.add_ticker("AAPL")

        gains = 0
        trials = 500
        for _ in range(trials):
            new = sim._next_price("AAPL", 190.0, sector_shock=10.0)
            if new > 190.0:
                gains += 1
        # The positive sector shock should make the majority of moves upward
        assert gains / trials > 0.70


class TestSimulatorTick:
    def test_tick_emits_update_to_cache(self, sim, cache):
        sim.add_ticker("AAPL")
        sim._tick()
        update = cache.get("AAPL")
        assert update is not None
        assert update.ticker == "AAPL"
        assert update.price > 0

    def test_tick_with_no_tickers_does_not_crash(self, sim):
        sim._tick()  # must not raise

    def test_tick_emits_all_tracked_tickers(self, sim, cache):
        for ticker in ["AAPL", "MSFT", "JPM"]:
            sim.add_ticker(ticker)
        sim._tick()
        for ticker in ["AAPL", "MSFT", "JPM"]:
            assert cache.get(ticker) is not None

    def test_tick_does_not_emit_removed_ticker(self, sim, cache):
        sim.add_ticker("AAPL")
        sim.remove_ticker("AAPL")
        sim._tick()
        assert cache.get("AAPL") is None

    def test_tick_update_callback_is_called(self, sim, cache):
        received: list[PriceUpdate] = []
        sim.set_update_callback(received.append)
        sim.add_ticker("AAPL")
        sim._tick()
        assert len(received) == 1
        assert received[0].ticker == "AAPL"

    def test_tick_previous_price_matches_prior_current(self, sim, cache):
        sim.add_ticker("GOOGL")
        sim._tick()
        first_price = cache.get("GOOGL").price
        sim._tick()
        second = cache.get("GOOGL")
        assert second.previous_price == first_price

    def test_tick_change_direction_is_valid(self, sim, cache):
        sim.add_ticker("TSLA")
        for _ in range(10):
            sim._tick()
            update = cache.get("TSLA")
            assert update.change_direction in {"up", "down", "unchanged"}


class TestSimulatorAsync:
    @pytest.mark.asyncio
    async def test_start_sets_running(self, sim):
        sim.add_ticker("AAPL")
        await sim.start()
        assert sim.is_running
        await sim.stop()

    @pytest.mark.asyncio
    async def test_stop_clears_running(self, sim):
        sim.add_ticker("AAPL")
        await sim.start()
        await sim.stop()
        assert not sim.is_running

    @pytest.mark.asyncio
    async def test_double_start_is_idempotent(self, sim):
        sim.add_ticker("AAPL")
        await sim.start()
        await sim.start()  # second call should be a no-op
        assert sim.is_running
        await sim.stop()

    @pytest.mark.asyncio
    async def test_running_simulator_populates_cache(self, sim, cache):
        sim.add_ticker("AAPL")
        await sim.start()
        # Give it a few ticks to fire (tick_interval=0.01 s)
        await asyncio.sleep(0.1)
        await sim.stop()
        assert cache.get("AAPL") is not None

    @pytest.mark.asyncio
    async def test_multiple_tickers_all_populated(self, sim, cache):
        for ticker in ["AAPL", "MSFT", "NVDA"]:
            sim.add_ticker(ticker)
        await sim.start()
        await asyncio.sleep(0.1)
        await sim.stop()
        for ticker in ["AAPL", "MSFT", "NVDA"]:
            assert cache.get(ticker) is not None


class TestSimulatorDefaultPrices:
    def test_all_default_seed_prices_are_positive(self):
        for ticker, price in DEFAULT_SEED_PRICES.items():
            assert price > 0, f"{ticker} seed price must be positive"

    def test_tech_tickers_are_a_subset_of_defaults(self):
        assert _TECH_TICKERS.issubset(DEFAULT_SEED_PRICES.keys())
