"""Unit tests for the market data provider factory."""

import os

import pytest

from app.market_data.base import PriceCache
from app.market_data.massive import MassiveAPIClient
from app.market_data.provider import _create_provider, get_provider, reset_provider
from app.market_data.simulator import MarketDataSimulator


class TestCreateProvider:
    def test_no_api_key_returns_simulator(self, monkeypatch):
        monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
        provider = _create_provider()
        assert isinstance(provider, MarketDataSimulator)

    def test_empty_api_key_returns_simulator(self, monkeypatch):
        monkeypatch.setenv("MASSIVE_API_KEY", "")
        provider = _create_provider()
        assert isinstance(provider, MarketDataSimulator)

    def test_whitespace_api_key_returns_simulator(self, monkeypatch):
        monkeypatch.setenv("MASSIVE_API_KEY", "   ")
        provider = _create_provider()
        assert isinstance(provider, MarketDataSimulator)

    def test_valid_api_key_returns_massive_client(self, monkeypatch):
        monkeypatch.setenv("MASSIVE_API_KEY", "sk-test-12345")
        provider = _create_provider()
        assert isinstance(provider, MassiveAPIClient)


class TestGetProvider:
    def setup_method(self):
        reset_provider(None)

    def teardown_method(self):
        reset_provider(None)

    def test_get_provider_returns_singleton(self, monkeypatch):
        monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
        p1 = get_provider()
        p2 = get_provider()
        assert p1 is p2

    def test_reset_none_triggers_re_creation(self, monkeypatch):
        monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
        p1 = get_provider()
        reset_provider(None)
        p2 = get_provider()
        # They're different instances after reset
        assert p1 is not p2

    def test_reset_with_instance_uses_that_instance(self):
        cache = PriceCache()
        custom = MarketDataSimulator(cache=cache)
        reset_provider(custom)
        assert get_provider() is custom
