"""Integration tests for the chat endpoint covering LLM-01 through LLM-07."""

from __future__ import annotations

import os

import httpx
import pytest
from httpx import ASGITransport


@pytest.fixture
def _mock_llm():
    """Enable mock LLM mode."""
    os.environ["LLM_MOCK"] = "true"
    yield
    os.environ.pop("LLM_MOCK", None)


@pytest.fixture
def _db_in_temp(tmp_path):
    """Set DB_PATH to a temp file so each test gets a fresh database."""
    db_path = str(tmp_path / "test.db")
    os.environ["DB_PATH"] = db_path
    yield db_path
    os.environ.pop("DB_PATH", None)


@pytest.fixture
async def client(_db_in_temp, _mock_llm):
    """Provide an async httpx client with mock LLM and deterministic prices."""
    from app.main import app, lifespan

    async with lifespan(app):
        await app.state.source.stop()
        app.state.cache.update("AAPL", 150.0)
        app.state.cache.update("GOOGL", 175.0)

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac, app


# --- LLM-01: Basic chat ---


async def test_chat_basic(client):
    """POST /api/chat returns 200 with message and actions."""
    ac, app = client
    response = await ac.post("/api/chat", json={"message": "how is my portfolio?"})
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert isinstance(data["message"], str)
    assert len(data["message"]) > 0
    assert "actions" in data


# --- LLM-02: Portfolio-aware context ---


async def test_chat_returns_message_content(client):
    """Chat returns non-empty message text."""
    ac, app = client
    response = await ac.post("/api/chat", json={"message": "analyze my portfolio"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["message"], str)
    assert len(data["message"]) > 0


# --- LLM-03: Auto-execute buy trade ---


async def test_chat_buy_trade(client):
    """Mock buy order auto-executes: cash decreases, position created."""
    ac, app = client
    response = await ac.post("/api/chat", json={"message": "buy some stocks"})
    assert response.status_code == 200
    data = response.json()

    # Mock returns buy 10 AAPL
    trades = data["actions"]["trades"]
    assert len(trades) == 1
    assert trades[0]["ticker"] == "AAPL"
    assert trades[0]["side"] == "buy"
    assert trades[0]["status"] == "executed"
    assert trades[0]["price"] == 150.0

    # Verify portfolio state
    portfolio = (await ac.get("/api/portfolio")).json()
    assert portfolio["cash"] == 8500.0  # 10000 - (10 * 150)
    positions = portfolio["positions"]
    aapl = [p for p in positions if p["ticker"] == "AAPL"]
    assert len(aapl) == 1
    assert aapl[0]["quantity"] == 10


# --- LLM-03: Auto-execute sell trade ---


async def test_chat_sell_trade(client):
    """Mock sell order auto-executes after buying position first."""
    ac, app = client

    # Buy 10 AAPL first via portfolio endpoint
    await ac.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )

    # Mock sell: "sell my shares" triggers sell of 5 AAPL
    response = await ac.post("/api/chat", json={"message": "sell my shares"})
    assert response.status_code == 200
    data = response.json()

    trades = data["actions"]["trades"]
    assert len(trades) == 1
    assert trades[0]["status"] == "executed"
    assert trades[0]["side"] == "sell"

    # Verify remaining position
    portfolio = (await ac.get("/api/portfolio")).json()
    aapl = [p for p in portfolio["positions"] if p["ticker"] == "AAPL"]
    assert len(aapl) == 1
    assert aapl[0]["quantity"] == 5


# --- LLM-04: Auto-execute watchlist add ---


async def test_chat_watchlist_add(client):
    """Mock watchlist add auto-executes."""
    ac, app = client
    response = await ac.post("/api/chat", json={"message": "add PYPL to watchlist"})
    assert response.status_code == 200
    data = response.json()

    wl_changes = data["actions"]["watchlist_changes"]
    assert len(wl_changes) == 1
    assert wl_changes[0]["ticker"] == "PYPL"
    assert wl_changes[0]["action"] == "add"
    assert wl_changes[0]["status"] == "executed"


# --- LLM-04: Auto-execute watchlist remove ---


async def test_chat_watchlist_remove(client):
    """Mock watchlist remove auto-executes after adding ticker."""
    ac, app = client

    # Add PYPL to watchlist first
    await ac.post("/api/watchlist", json={"ticker": "PYPL"})
    app.state.cache.update("PYPL", 80.0)

    # Remove via chat
    response = await ac.post("/api/chat", json={"message": "remove PYPL please"})
    assert response.status_code == 200
    data = response.json()

    wl_changes = data["actions"]["watchlist_changes"]
    assert len(wl_changes) == 1
    assert wl_changes[0]["status"] == "executed"


# --- LLM-05: Failed trade — insufficient cash ---


async def test_chat_trade_failure_insufficient_cash(client):
    """Buy trade fails gracefully when cash insufficient; endpoint returns 200."""
    ac, app = client

    # Set AAPL price high so 10 shares = $20,000 > $10,000 cash
    app.state.cache.update("AAPL", 2000.0)

    response = await ac.post("/api/chat", json={"message": "buy some stocks"})
    assert response.status_code == 200
    data = response.json()

    trades = data["actions"]["trades"]
    assert len(trades) == 1
    assert trades[0]["status"] == "failed"
    assert len(data["actions"]["errors"]) > 0


# --- LLM-05: Failed sell — no position ---


async def test_chat_trade_failure_no_position(client):
    """Sell trade fails gracefully when no position exists."""
    ac, app = client

    response = await ac.post("/api/chat", json={"message": "sell my shares"})
    assert response.status_code == 200
    data = response.json()

    trades = data["actions"]["trades"]
    assert len(trades) == 1
    assert trades[0]["status"] == "failed"


# --- LLM-06: Chat history persistence ---


async def test_chat_history_persisted(client):
    """User and assistant messages are persisted to the database."""
    ac, app = client

    await ac.post("/api/chat", json={"message": "hello"})
    await ac.post("/api/chat", json={"message": "how are you?"})

    # Query database directly
    async with app.state.db.execute(
        "SELECT role, content FROM chat_messages ORDER BY created_at, rowid"
    ) as cursor:
        rows = await cursor.fetchall()

    # Should have at least 4 rows: 2 user + 2 assistant
    assert len(rows) >= 4

    roles = [row[0] for row in rows]
    assert roles.count("user") >= 2
    assert roles.count("assistant") >= 2

    # Check user messages match what was sent
    user_contents = [row[1] for row in rows if row[0] == "user"]
    assert "hello" in user_contents
    assert "how are you?" in user_contents


# --- LLM-07: Mock mode determinism ---


async def test_mock_mode_deterministic(client):
    """Same input produces identical output in mock mode."""
    ac, app = client

    r1 = await ac.post("/api/chat", json={"message": "buy"})
    r2 = await ac.post("/api/chat", json={"message": "buy"})

    assert r1.json()["message"] == r2.json()["message"]


# --- LLM-01: Missing API key returns 503 ---


async def test_chat_no_api_key_returns_503(client):
    """Without LLM_MOCK and OPENROUTER_API_KEY, endpoint returns 503."""
    ac, app = client

    # Temporarily disable mock mode and ensure no API key
    original_mock = os.environ.pop("LLM_MOCK", None)
    original_key = os.environ.pop("OPENROUTER_API_KEY", None)
    try:
        response = await ac.post("/api/chat", json={"message": "hello"})
        assert response.status_code == 503
        assert "LLM not configured" in response.json()["detail"]
    finally:
        if original_mock is not None:
            os.environ["LLM_MOCK"] = original_mock
        if original_key is not None:
            os.environ["OPENROUTER_API_KEY"] = original_key


# --- Regression: existing endpoints unaffected ---


async def test_health_still_works(client):
    """Health endpoint still returns 200 after chat route added."""
    ac, app = client
    response = await ac.get("/api/health")
    assert response.status_code == 200
