"""Integration tests for portfolio, trade execution, and snapshot endpoints."""

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


@pytest.fixture
async def client_with_prices(_db_in_temp):
    """Provide an async httpx client with deterministic prices set in PriceCache.

    Stops the market data source to prevent the simulator from overwriting
    our deterministic test prices.
    """
    from app.main import app, lifespan

    async with lifespan(app):
        # Stop the simulator so it doesn't overwrite our test prices
        await app.state.source.stop()

        # Set deterministic prices for testing
        app.state.cache.update("AAPL", 150.0)
        app.state.cache.update("GOOGL", 175.0)

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac, app


async def test_get_portfolio_initial(client):
    """GET /api/portfolio returns initial state with $10k cash, no positions."""
    response = await client.get("/api/portfolio")
    assert response.status_code == 200
    data = response.json()
    assert data["cash"] == 10000.0
    assert data["positions"] == []
    assert data["total_value"] == 10000.0
    assert data["total_pnl"] == 0.0


async def test_buy_trade(client_with_prices):
    """POST buy trade deducts cash and creates position."""
    client, app = client_with_prices

    response = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["trade"]["ticker"] == "AAPL"
    assert data["trade"]["side"] == "buy"
    assert data["trade"]["quantity"] == 10
    assert data["trade"]["price"] == 150.0
    assert data["cash_balance"] == 8500.0

    # Verify via portfolio endpoint
    portfolio = (await client.get("/api/portfolio")).json()
    assert len(portfolio["positions"]) == 1
    pos = portfolio["positions"][0]
    assert pos["ticker"] == "AAPL"
    assert pos["quantity"] == 10
    assert pos["avg_cost"] == 150.0


async def test_sell_trade(client_with_prices):
    """POST sell trade increases cash and reduces position."""
    client, app = client_with_prices

    # Buy first
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )

    # Sell partial
    response = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 5, "side": "sell"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["cash_balance"] == 9250.0

    # Verify remaining position
    portfolio = (await client.get("/api/portfolio")).json()
    assert len(portfolio["positions"]) == 1
    assert portfolio["positions"][0]["quantity"] == 5


async def test_sell_full_position_deletes_row(client_with_prices):
    """Selling full position removes the position row entirely."""
    client, app = client_with_prices

    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "sell"},
    )

    portfolio = (await client.get("/api/portfolio")).json()
    assert portfolio["positions"] == []
    assert portfolio["cash"] == 10000.0


async def test_buy_insufficient_cash(client_with_prices):
    """Buy with insufficient cash returns 400."""
    client, app = client_with_prices

    response = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 1000, "side": "buy"},
    )
    assert response.status_code == 400
    assert "Insufficient cash" in response.json()["detail"]


async def test_sell_insufficient_shares(client_with_prices):
    """Sell more shares than owned returns 400."""
    client, app = client_with_prices

    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )

    response = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 20, "side": "sell"},
    )
    assert response.status_code == 400
    assert "Insufficient shares" in response.json()["detail"]


async def test_sell_no_position(client_with_prices):
    """Sell with no position returns 400."""
    client, app = client_with_prices

    response = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "GOOGL", "quantity": 1, "side": "sell"},
    )
    assert response.status_code == 400
    assert "No position" in response.json()["detail"]


async def test_trade_no_price_in_cache(client):
    """Trade on ticker not in price cache returns 400."""
    response = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "ZZZZ", "quantity": 1, "side": "buy"},
    )
    assert response.status_code == 400
    assert "No price available" in response.json()["detail"]


async def test_buy_updates_avg_cost(client_with_prices):
    """Multiple buys at different prices produce weighted average cost."""
    client, app = client_with_prices

    # Buy 10 at 150
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )

    # Update price and buy 10 more at 200
    app.state.cache.update("AAPL", 200.0)
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )

    portfolio = (await client.get("/api/portfolio")).json()
    pos = portfolio["positions"][0]
    assert pos["quantity"] == 20
    assert pos["avg_cost"] == 175.0  # (10*150 + 10*200) / 20


async def test_portfolio_with_unrealized_pnl(client_with_prices):
    """Portfolio shows correct unrealized P&L when price changes."""
    client, app = client_with_prices

    # Buy 10 at 150
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )

    # Price moves to 160
    app.state.cache.update("AAPL", 160.0)

    portfolio = (await client.get("/api/portfolio")).json()
    pos = portfolio["positions"][0]
    assert pos["current_price"] == 160.0
    assert pos["unrealized_pnl"] == 100.0  # (160-150)*10
    assert abs(pos["pnl_percent"] - 6.67) < 0.01

    # total_value = 8500 cash + 10*160 = 10100
    assert portfolio["total_value"] == 10100.0
    assert portfolio["total_pnl"] == 100.0


async def test_trade_history_recorded(client_with_prices):
    """Trades are recorded and reflected in portfolio state."""
    client, app = client_with_prices

    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 5, "side": "sell"},
    )

    # Verify final state reflects both operations
    portfolio = (await client.get("/api/portfolio")).json()
    assert portfolio["positions"][0]["quantity"] == 5
    assert portfolio["cash"] == 9250.0


async def test_snapshot_after_trade(client_with_prices):
    """Trade execution records a portfolio snapshot."""
    client, app = client_with_prices

    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )

    response = await client.get("/api/portfolio/history")
    assert response.status_code == 200
    data = response.json()
    assert len(data["snapshots"]) >= 1
    # Snapshot value: 8500 cash + 10*150 = 10000
    assert abs(data["snapshots"][0]["total_value"] - 10000.0) < 1.0


async def test_portfolio_history(client_with_prices):
    """GET /api/portfolio/history returns snapshots with required keys."""
    client, app = client_with_prices

    # Trigger a snapshot via trade
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 1, "side": "buy"},
    )

    response = await client.get("/api/portfolio/history")
    assert response.status_code == 200
    data = response.json()
    assert "snapshots" in data
    assert isinstance(data["snapshots"], list)
    assert len(data["snapshots"]) >= 1
    snapshot = data["snapshots"][0]
    assert "total_value" in snapshot
    assert "recorded_at" in snapshot


async def test_ticker_uppercase_normalization(client_with_prices):
    """Trade with lowercase ticker normalizes to uppercase."""
    client, app = client_with_prices

    response = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "aapl", "quantity": 1, "side": "buy"},
    )
    assert response.status_code == 200
    assert response.json()["trade"]["ticker"] == "AAPL"
