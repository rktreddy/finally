"""Unit tests for the market data base module (PriceUpdate, PriceCache, interface)."""

import pytest

from app.market_data.base import PriceCache, PriceUpdate


class TestPriceUpdate:
    def test_from_prices_up(self):
        u = PriceUpdate.from_prices("AAPL", 191.0, 190.0, "2024-01-01T00:00:00Z")
        assert u.ticker == "AAPL"
        assert u.price == 191.0
        assert u.previous_price == 190.0
        assert u.change_direction == "up"

    def test_from_prices_down(self):
        u = PriceUpdate.from_prices("AAPL", 189.0, 190.0, "2024-01-01T00:00:00Z")
        assert u.change_direction == "down"

    def test_from_prices_unchanged(self):
        u = PriceUpdate.from_prices("AAPL", 190.0, 190.0, "2024-01-01T00:00:00Z")
        assert u.change_direction == "unchanged"

    def test_fields_are_stored(self):
        ts = "2024-06-15T12:30:00Z"
        u = PriceUpdate.from_prices("MSFT", 420.5, 419.0, ts)
        assert u.timestamp == ts
        assert u.ticker == "MSFT"


class TestPriceCache:
    def setup_method(self):
        self.cache = PriceCache()

    def _make_update(self, ticker: str, price: float, prev: float = 0.0) -> PriceUpdate:
        return PriceUpdate.from_prices(ticker, price, prev, "2024-01-01T00:00:00Z")

    def test_update_and_get(self):
        u = self._make_update("AAPL", 190.0, 189.0)
        self.cache.update(u)
        result = self.cache.get("AAPL")
        assert result is u

    def test_get_missing_ticker(self):
        assert self.cache.get("ZZZZZ") is None

    def test_get_all_returns_snapshot(self):
        self.cache.update(self._make_update("AAPL", 190.0))
        self.cache.update(self._make_update("GOOGL", 175.0))
        snap = self.cache.get_all()
        assert set(snap.keys()) == {"AAPL", "GOOGL"}

    def test_get_all_is_a_copy(self):
        self.cache.update(self._make_update("AAPL", 190.0))
        snap = self.cache.get_all()
        snap["AAPL"] = None  # mutate the copy
        assert self.cache.get("AAPL") is not None  # original unaffected

    def test_get_tickers(self):
        self.cache.update(self._make_update("AAPL", 190.0))
        self.cache.update(self._make_update("MSFT", 420.0))
        assert set(self.cache.get_tickers()) == {"AAPL", "MSFT"}

    def test_remove(self):
        self.cache.update(self._make_update("AAPL", 190.0))
        self.cache.remove("AAPL")
        assert self.cache.get("AAPL") is None

    def test_remove_nonexistent_is_safe(self):
        self.cache.remove("ZZZZZ")  # should not raise

    def test_clear(self):
        self.cache.update(self._make_update("AAPL", 190.0))
        self.cache.update(self._make_update("MSFT", 420.0))
        self.cache.clear()
        assert self.cache.get_all() == {}

    def test_update_overwrites_previous(self):
        self.cache.update(self._make_update("AAPL", 190.0))
        newer = self._make_update("AAPL", 192.0, 190.0)
        self.cache.update(newer)
        assert self.cache.get("AAPL").price == 192.0
