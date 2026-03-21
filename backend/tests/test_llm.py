"""Tests for the LLM chat integration."""

import json
import os
import tempfile

import pytest

from app.db.connection import get_connection, set_db_path, reset_state
from app.db.schema import DEFAULT_USER_ID
from app.llm.models import ChatResponse, TradeAction, WatchlistChange
from app.llm.mock import mock_response
from app.llm.prompt import build_portfolio_context, build_messages
from app.llm.handler import handle_chat_message
from app.market.cache import PriceCache


# ── Model tests ──────────────────────────────────────────────────────────────


class TestModels:
    def test_chat_response_minimal(self):
        r = ChatResponse(message="Hello")
        assert r.message == "Hello"
        assert r.trades == []
        assert r.watchlist_changes == []

    def test_chat_response_with_trades(self):
        r = ChatResponse(
            message="Buying AAPL",
            trades=[TradeAction(ticker="AAPL", side="buy", quantity=10)],
        )
        assert len(r.trades) == 1
        assert r.trades[0].ticker == "AAPL"
        assert r.trades[0].side == "buy"

    def test_chat_response_with_watchlist_changes(self):
        r = ChatResponse(
            message="Adding PYPL",
            watchlist_changes=[WatchlistChange(ticker="PYPL", action="add")],
        )
        assert len(r.watchlist_changes) == 1
        assert r.watchlist_changes[0].action == "add"

    def test_chat_response_from_json(self):
        raw = '{"message": "test", "trades": [{"ticker": "MSFT", "side": "sell", "quantity": 5}]}'
        r = ChatResponse.model_validate_json(raw)
        assert r.message == "test"
        assert r.trades[0].ticker == "MSFT"

    def test_chat_response_from_json_missing_optional(self):
        raw = '{"message": "just a message"}'
        r = ChatResponse.model_validate_json(raw)
        assert r.trades == []
        assert r.watchlist_changes == []

    def test_trade_action_invalid_side(self):
        with pytest.raises(Exception):
            TradeAction(ticker="AAPL", side="hold", quantity=10)

    def test_watchlist_change_invalid_action(self):
        with pytest.raises(Exception):
            WatchlistChange(ticker="AAPL", action="update")


# ── Mock tests ───────────────────────────────────────────────────────────────


class TestMock:
    def test_mock_buy(self):
        r = mock_response("buy 5 AAPL")
        assert len(r.trades) == 1
        assert r.trades[0].side == "buy"
        assert r.trades[0].ticker == "AAPL"
        assert r.trades[0].quantity == 5

    def test_mock_sell(self):
        r = mock_response("sell 3 MSFT")
        assert len(r.trades) == 1
        assert r.trades[0].side == "sell"
        assert r.trades[0].ticker == "MSFT"

    def test_mock_add_watchlist(self):
        r = mock_response("add PYPL to watchlist")
        assert len(r.watchlist_changes) == 1
        assert r.watchlist_changes[0].action == "add"
        assert r.watchlist_changes[0].ticker == "PYPL"

    def test_mock_remove_watchlist(self):
        r = mock_response("remove TSLA from watchlist")
        assert len(r.watchlist_changes) == 1
        assert r.watchlist_changes[0].action == "remove"

    def test_mock_generic(self):
        r = mock_response("how is my portfolio doing?")
        assert r.trades == []
        assert r.watchlist_changes == []
        assert "portfolio" in r.message.lower() or "diversified" in r.message.lower()

    def test_mock_default_ticker_buy(self):
        r = mock_response("buy some stock")
        assert r.trades[0].ticker == "AAPL"  # default

    def test_mock_default_quantity(self):
        r = mock_response("buy NVDA")
        assert r.trades[0].quantity == 10  # default


# ── Prompt tests ─────────────────────────────────────────────────────────────


class TestPrompt:
    def test_build_portfolio_context_empty(self):
        ctx = build_portfolio_context(10000.0, [], [], 10000.0)
        assert "Cash Balance: $10,000.00" in ctx
        assert "Total Portfolio Value: $10,000.00" in ctx

    def test_build_portfolio_context_with_positions(self):
        positions = [
            {
                "ticker": "AAPL",
                "quantity": 10,
                "avg_cost": 150.0,
                "current_price": 160.0,
                "unrealized_pnl": 100.0,
                "pnl_percent": 6.67,
            }
        ]
        ctx = build_portfolio_context(8500.0, positions, [], 10100.0)
        assert "AAPL" in ctx
        assert "10 shares" in ctx

    def test_build_messages(self):
        history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
        msgs = build_messages("what should I buy?", "## Context", history)
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "system"
        assert msgs[2]["role"] == "user"
        assert msgs[2]["content"] == "hi"
        assert msgs[3]["role"] == "assistant"
        assert msgs[-1]["role"] == "user"
        assert msgs[-1]["content"] == "what should I buy?"


# ── Handler integration tests ────────────────────────────────────────────────


@pytest.fixture
async def test_db():
    """Set up a temporary database for handler tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    reset_state()
    set_db_path(db_path)

    # Initialize by getting a connection (triggers lazy init)
    db = await get_connection()
    await db.close()

    yield db_path

    reset_state()
    os.unlink(db_path)


@pytest.fixture
def price_cache():
    """Create a price cache with some test prices."""
    cache = PriceCache()
    cache.update("AAPL", 190.0)
    cache.update("GOOGL", 175.0)
    cache.update("MSFT", 420.0)
    cache.update("TSLA", 250.0)
    cache.update("NVDA", 900.0)
    return cache


class TestHandler:
    @pytest.mark.asyncio
    async def test_mock_chat_generic(self, test_db, price_cache):
        os.environ["LLM_MOCK"] = "true"
        try:
            result = await handle_chat_message("how is my portfolio?", price_cache)
            assert "message" in result
            assert isinstance(result["trades"], list)
            assert isinstance(result["watchlist_changes"], list)
        finally:
            os.environ.pop("LLM_MOCK", None)

    @pytest.mark.asyncio
    async def test_mock_chat_buy(self, test_db, price_cache):
        os.environ["LLM_MOCK"] = "true"
        try:
            result = await handle_chat_message("buy 5 AAPL", price_cache)
            assert len(result["trades"]) == 1
            trade = result["trades"][0]
            assert trade["ticker"] == "AAPL"
            assert trade["side"] == "buy"
            assert trade["status"] == "executed"
            assert trade["quantity"] == 5
            assert trade["price"] == 190.0

            # Verify cash was deducted
            db = await get_connection()
            cursor = await db.execute(
                "SELECT cash_balance FROM users_profile WHERE id = ?",
                (DEFAULT_USER_ID,),
            )
            row = await cursor.fetchone()
            assert row["cash_balance"] == 10000.0 - (5 * 190.0)
            await db.close()
        finally:
            os.environ.pop("LLM_MOCK", None)

    @pytest.mark.asyncio
    async def test_mock_chat_sell_insufficient_shares(self, test_db, price_cache):
        os.environ["LLM_MOCK"] = "true"
        try:
            result = await handle_chat_message("sell 10 AAPL", price_cache)
            assert len(result["trades"]) == 1
            assert result["trades"][0]["status"] == "failed"
            assert "Insufficient shares" in result["trades"][0]["error"]
        finally:
            os.environ.pop("LLM_MOCK", None)

    @pytest.mark.asyncio
    async def test_mock_chat_buy_insufficient_cash(self, test_db, price_cache):
        os.environ["LLM_MOCK"] = "true"
        try:
            # Try to buy way more than cash allows
            result = await handle_chat_message("buy 1000 NVDA", price_cache)
            assert result["trades"][0]["status"] == "failed"
            assert "Insufficient cash" in result["trades"][0]["error"]
        finally:
            os.environ.pop("LLM_MOCK", None)

    @pytest.mark.asyncio
    async def test_mock_chat_add_watchlist(self, test_db, price_cache):
        os.environ["LLM_MOCK"] = "true"
        try:
            result = await handle_chat_message("add PYPL to watchlist", price_cache)
            assert len(result["watchlist_changes"]) == 1
            assert result["watchlist_changes"][0]["status"] == "added"
        finally:
            os.environ.pop("LLM_MOCK", None)

    @pytest.mark.asyncio
    async def test_chat_messages_saved(self, test_db, price_cache):
        os.environ["LLM_MOCK"] = "true"
        try:
            await handle_chat_message("hello", price_cache)

            db = await get_connection()
            cursor = await db.execute(
                "SELECT role, content FROM chat_messages WHERE user_id = ? ORDER BY created_at",
                (DEFAULT_USER_ID,),
            )
            rows = await cursor.fetchall()
            await db.close()

            assert len(rows) == 2
            assert rows[0]["role"] == "user"
            assert rows[0]["content"] == "hello"
            assert rows[1]["role"] == "assistant"
        finally:
            os.environ.pop("LLM_MOCK", None)

    @pytest.mark.asyncio
    async def test_buy_then_sell(self, test_db, price_cache):
        os.environ["LLM_MOCK"] = "true"
        try:
            # Buy first
            result = await handle_chat_message("buy 5 AAPL", price_cache)
            assert result["trades"][0]["status"] == "executed"

            # Now sell
            result = await handle_chat_message("sell 3 AAPL", price_cache)
            assert result["trades"][0]["status"] == "executed"

            # Check remaining position
            db = await get_connection()
            cursor = await db.execute(
                "SELECT quantity FROM positions WHERE user_id = ? AND ticker = 'AAPL'",
                (DEFAULT_USER_ID,),
            )
            row = await cursor.fetchone()
            assert row["quantity"] == 2
            await db.close()
        finally:
            os.environ.pop("LLM_MOCK", None)

    @pytest.mark.asyncio
    async def test_portfolio_snapshot_after_trade(self, test_db, price_cache):
        os.environ["LLM_MOCK"] = "true"
        try:
            await handle_chat_message("buy 5 AAPL", price_cache)

            db = await get_connection()
            cursor = await db.execute(
                "SELECT total_value FROM portfolio_snapshots WHERE user_id = ? "
                "ORDER BY recorded_at DESC LIMIT 1",
                (DEFAULT_USER_ID,),
            )
            row = await cursor.fetchone()
            assert row is not None
            # Should be close to $10,000 (cash minus purchase + position value)
            assert row["total_value"] == pytest.approx(10000.0, abs=1.0)
            await db.close()
        finally:
            os.environ.pop("LLM_MOCK", None)
