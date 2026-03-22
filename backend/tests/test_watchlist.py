"""Integration tests for watchlist CRUD endpoints."""

from __future__ import annotations

import os

import httpx
import pytest
from httpx import ASGITransport


@pytest.fixture
def _db_in_temp(tmp_path):
    """Set DB_PATH to a temp file so each test gets a fresh database."""
    db_path = str(tmp_path / "test.db")
    os.environ["DB_PATH"] = db_path
    yield db_path
    os.environ.pop("DB_PATH", None)


@pytest.fixture
async def client(_db_in_temp):
    """Provide an async httpx client with lifespan managed."""
    from app.main import app, lifespan

    async with lifespan(app):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac


async def test_get_watchlist(client):
    """GET /api/watchlist returns 200 with 10 seeded tickers enriched with price data."""
    response = await client.get("/api/watchlist")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 10

    # Check required keys on each item
    for item in data:
        assert "ticker" in item
        assert "added_at" in item
        assert "price" in item
        assert "change" in item
        assert "change_percent" in item
        assert "direction" in item

    # AAPL should be in the seeded watchlist
    tickers = [item["ticker"] for item in data]
    assert "AAPL" in tickers


async def test_add_ticker(client):
    """POST /api/watchlist with new ticker returns 201 and adds to watchlist."""
    response = await client.post("/api/watchlist", json={"ticker": "PYPL"})
    assert response.status_code == 201
    data = response.json()
    assert data["ticker"] == "PYPL"

    # Verify watchlist now has 11 items
    list_response = await client.get("/api/watchlist")
    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 11
    tickers = [item["ticker"] for item in items]
    assert "PYPL" in tickers


async def test_add_ticker_uppercase_normalization(client):
    """POST /api/watchlist normalizes ticker to uppercase."""
    response = await client.post("/api/watchlist", json={"ticker": "pypl"})
    assert response.status_code == 201
    data = response.json()
    assert data["ticker"] == "PYPL"


async def test_add_duplicate_ticker(client):
    """POST /api/watchlist with already-seeded ticker returns 409."""
    response = await client.post("/api/watchlist", json={"ticker": "AAPL"})
    assert response.status_code == 409
    data = response.json()
    assert "already in watchlist" in data["detail"].lower()


async def test_remove_ticker(client):
    """DELETE /api/watchlist/AAPL returns 200 and removes from watchlist."""
    response = await client.delete("/api/watchlist/AAPL")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "removed"
    assert data["ticker"] == "AAPL"

    # Verify watchlist now has 9 items and AAPL is gone
    list_response = await client.get("/api/watchlist")
    items = list_response.json()
    assert len(items) == 9
    tickers = [item["ticker"] for item in items]
    assert "AAPL" not in tickers


async def test_remove_nonexistent_ticker(client):
    """DELETE /api/watchlist/ZZZZ returns 404."""
    response = await client.delete("/api/watchlist/ZZZZ")
    assert response.status_code == 404
    data = response.json()
    assert "not in watchlist" in data["detail"].lower()


async def test_remove_ticker_case_insensitive(client):
    """DELETE /api/watchlist/aapl (lowercase) normalizes and removes AAPL."""
    response = await client.delete("/api/watchlist/aapl")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
