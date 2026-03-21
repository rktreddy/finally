"""Unit tests for FastAPI API endpoints."""

import tempfile
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.db import set_db_path, reset_state
from app.market import PriceCache


@pytest.fixture(autouse=True)
def _temp_db(tmp_path):
    """Use a temporary database for each test."""
    db_path = str(tmp_path / "test.db")
    set_db_path(db_path)
    yield
    reset_state()


@pytest.fixture
def price_cache():
    cache = PriceCache()
    # Seed some prices
    cache.update("AAPL", 190.0)
    cache.update("GOOGL", 175.0)
    cache.update("MSFT", 420.0)
    cache.update("AMZN", 185.0)
    cache.update("TSLA", 250.0)
    cache.update("NVDA", 800.0)
    cache.update("META", 500.0)
    cache.update("JPM", 195.0)
    cache.update("V", 280.0)
    cache.update("NFLX", 600.0)
    return cache


@pytest.fixture
def mock_market_data():
    md = AsyncMock()
    md.start = AsyncMock()
    md.stop = AsyncMock()
    md.add_ticker = AsyncMock()
    md.remove_ticker = AsyncMock()
    md.get_tickers = MagicMock(return_value=["AAPL", "GOOGL"])
    return md


@pytest.fixture
def client(price_cache, mock_market_data):
    """Create a test client with mocked market data and no lifespan."""
    from app.routes import health, portfolio, watchlist, chat
    from fastapi import FastAPI

    test_app = FastAPI()
    test_app.include_router(health.router)
    test_app.include_router(portfolio.router)
    test_app.include_router(watchlist.router)
    test_app.include_router(chat.router)

    test_app.state.price_cache = price_cache
    test_app.state.market_data_source = mock_market_data

    return TestClient(test_app)


# --- Health ---

def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# --- Portfolio ---

def test_get_portfolio_empty(client):
    resp = client.get("/api/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cash_balance"] == 10000.0
    assert data["positions"] == []
    assert data["total_value"] == 10000.0


def test_buy_trade(client):
    resp = client.post("/api/portfolio/trade", json={
        "ticker": "AAPL",
        "quantity": 10,
        "side": "buy",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "AAPL"
    assert data["side"] == "buy"
    assert data["quantity"] == 10
    assert data["price"] == 190.0

    # Check portfolio
    resp = client.get("/api/portfolio")
    data = resp.json()
    assert data["cash_balance"] == 10000.0 - 1900.0
    assert len(data["positions"]) == 1
    assert data["positions"][0]["ticker"] == "AAPL"
    assert data["positions"][0]["quantity"] == 10


def test_sell_trade(client):
    # Buy first
    client.post("/api/portfolio/trade", json={
        "ticker": "AAPL", "quantity": 10, "side": "buy",
    })
    # Sell some
    resp = client.post("/api/portfolio/trade", json={
        "ticker": "AAPL", "quantity": 5, "side": "sell",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["side"] == "sell"
    assert data["quantity"] == 5

    # Check remaining
    resp = client.get("/api/portfolio")
    data = resp.json()
    assert data["positions"][0]["quantity"] == 5


def test_buy_insufficient_cash(client):
    resp = client.post("/api/portfolio/trade", json={
        "ticker": "NVDA", "quantity": 100, "side": "buy",
    })
    assert resp.status_code == 400
    assert "Insufficient cash" in resp.json()["detail"]


def test_sell_insufficient_shares(client):
    resp = client.post("/api/portfolio/trade", json={
        "ticker": "AAPL", "quantity": 10, "side": "sell",
    })
    assert resp.status_code == 400
    assert "Insufficient shares" in resp.json()["detail"]


def test_trade_no_price(client):
    resp = client.post("/api/portfolio/trade", json={
        "ticker": "UNKNOWN", "quantity": 1, "side": "buy",
    })
    assert resp.status_code == 400
    assert "No price available" in resp.json()["detail"]


def test_portfolio_history(client):
    resp = client.get("/api/portfolio/history")
    assert resp.status_code == 200
    data = resp.json()
    assert "snapshots" in data
    assert isinstance(data["snapshots"], list)


# --- Watchlist ---

def test_get_watchlist(client):
    resp = client.get("/api/watchlist")
    assert resp.status_code == 200
    data = resp.json()
    assert "watchlist" in data
    # Default seed has 10 tickers
    assert len(data["watchlist"]) == 10


def test_add_ticker(client, mock_market_data):
    resp = client.post("/api/watchlist", json={"ticker": "PYPL"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "PYPL"
    mock_market_data.add_ticker.assert_called_once_with("PYPL")


def test_add_duplicate_ticker(client):
    resp = client.post("/api/watchlist", json={"ticker": "AAPL"})
    assert resp.status_code == 400
    assert "already in the watchlist" in resp.json()["detail"]


def test_remove_ticker(client, mock_market_data):
    resp = client.delete("/api/watchlist/AAPL")
    assert resp.status_code == 200
    assert resp.json()["removed"] == "AAPL"
    mock_market_data.remove_ticker.assert_called_once_with("AAPL")


def test_remove_nonexistent_ticker(client):
    resp = client.delete("/api/watchlist/ZZZZ")
    assert resp.status_code == 404


# --- Chat ---

def test_chat_placeholder(client):
    resp = client.post("/api/chat", json={"message": "Hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert "trades" in data
    assert "watchlist_changes" in data
