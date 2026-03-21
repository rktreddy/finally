"""Unit tests for the database layer."""

import os

import pytest

from app.db import (
    DEFAULT_CASH_BALANCE,
    DEFAULT_TICKERS,
    add_ticker,
    execute_trade,
    get_portfolio,
    get_recent_messages,
    get_snapshots,
    get_trade_history,
    get_watchlist,
    record_snapshot,
    remove_ticker,
    reset_state,
    save_message,
    set_db_path,
)


@pytest.fixture(autouse=True)
def temp_db(tmp_path):
    """Use a temporary database for every test."""
    db_path = str(tmp_path / "test.db")
    reset_state()
    set_db_path(db_path)
    yield db_path
    reset_state()


# --- Initialization ---


class TestInitialization:
    async def test_lazy_init_creates_db(self, temp_db):
        """DB file is created on first access."""
        assert not os.path.exists(temp_db)
        await get_portfolio()
        assert os.path.exists(temp_db)

    async def test_seed_data_default_user(self, temp_db):
        """Default user starts with correct cash balance."""
        portfolio = await get_portfolio()
        assert portfolio["cash_balance"] == DEFAULT_CASH_BALANCE

    async def test_seed_data_watchlist(self, temp_db):
        """Default watchlist has 10 tickers."""
        watchlist = await get_watchlist()
        tickers = [w["ticker"] for w in watchlist]
        assert len(tickers) == 10
        for t in DEFAULT_TICKERS:
            assert t in tickers

    async def test_idempotent_init(self, temp_db):
        """Calling get_portfolio twice doesn't duplicate seed data."""
        await get_portfolio()
        await get_portfolio()
        watchlist = await get_watchlist()
        assert len(watchlist) == 10


# --- Portfolio & Trading ---


class TestTrading:
    async def test_buy_shares(self, temp_db):
        """Buying reduces cash and creates a position."""
        trade = await execute_trade("AAPL", "buy", 10, 150.0)
        assert trade["ticker"] == "AAPL"
        assert trade["side"] == "buy"
        assert trade["quantity"] == 10
        assert trade["price"] == 150.0

        portfolio = await get_portfolio()
        assert portfolio["cash_balance"] == pytest.approx(DEFAULT_CASH_BALANCE - 1500.0)
        assert len(portfolio["positions"]) == 1
        assert portfolio["positions"][0]["ticker"] == "AAPL"
        assert portfolio["positions"][0]["quantity"] == 10
        assert portfolio["positions"][0]["avg_cost"] == 150.0

    async def test_buy_insufficient_cash(self, temp_db):
        """Cannot buy more than cash allows."""
        with pytest.raises(ValueError, match="Insufficient cash"):
            await execute_trade("AAPL", "buy", 1000, 100.0)  # $100k > $10k

    async def test_sell_shares(self, temp_db):
        """Selling increases cash and reduces position."""
        await execute_trade("AAPL", "buy", 10, 150.0)
        trade = await execute_trade("AAPL", "sell", 5, 160.0)
        assert trade["side"] == "sell"

        portfolio = await get_portfolio()
        assert portfolio["cash_balance"] == pytest.approx(DEFAULT_CASH_BALANCE - 1500.0 + 800.0)
        assert portfolio["positions"][0]["quantity"] == 5

    async def test_sell_all_removes_position(self, temp_db):
        """Selling all shares removes the position entirely."""
        await execute_trade("AAPL", "buy", 10, 150.0)
        await execute_trade("AAPL", "sell", 10, 160.0)

        portfolio = await get_portfolio()
        assert len(portfolio["positions"]) == 0

    async def test_sell_more_than_owned(self, temp_db):
        """Cannot sell more shares than held."""
        await execute_trade("AAPL", "buy", 5, 100.0)
        with pytest.raises(ValueError, match="Insufficient shares"):
            await execute_trade("AAPL", "sell", 10, 100.0)

    async def test_sell_without_position(self, temp_db):
        """Cannot sell a ticker with no position."""
        with pytest.raises(ValueError, match="Insufficient shares"):
            await execute_trade("AAPL", "sell", 1, 100.0)

    async def test_buy_averages_cost(self, temp_db):
        """Multiple buys calculate weighted average cost."""
        await execute_trade("AAPL", "buy", 10, 100.0)  # $1000
        await execute_trade("AAPL", "buy", 10, 200.0)  # $2000

        portfolio = await get_portfolio()
        pos = portfolio["positions"][0]
        assert pos["quantity"] == 20
        assert pos["avg_cost"] == pytest.approx(150.0)  # $3000 / 20

    async def test_invalid_quantity(self, temp_db):
        with pytest.raises(ValueError, match="Quantity must be positive"):
            await execute_trade("AAPL", "buy", 0, 100.0)

    async def test_invalid_side(self, temp_db):
        with pytest.raises(ValueError, match="Side must be"):
            await execute_trade("AAPL", "short", 1, 100.0)

    async def test_trade_history(self, temp_db):
        """Trades are logged and retrievable."""
        await execute_trade("AAPL", "buy", 10, 150.0)
        await execute_trade("GOOGL", "buy", 5, 175.0)

        history = await get_trade_history()
        assert len(history) == 2
        # Newest first
        assert history[0]["ticker"] == "GOOGL"
        assert history[1]["ticker"] == "AAPL"


# --- Watchlist ---


class TestWatchlist:
    async def test_add_ticker(self, temp_db):
        """Can add a new ticker to watchlist."""
        entry = await add_ticker("PYPL")
        assert entry["ticker"] == "PYPL"

        watchlist = await get_watchlist()
        tickers = [w["ticker"] for w in watchlist]
        assert "PYPL" in tickers
        assert len(watchlist) == 11

    async def test_add_duplicate(self, temp_db):
        """Cannot add a ticker that's already in watchlist."""
        # AAPL is in the seed data
        await get_watchlist()  # trigger init
        with pytest.raises(ValueError, match="already in the watchlist"):
            await add_ticker("AAPL")

    async def test_add_ticker_normalizes(self, temp_db):
        """Ticker is uppercased and trimmed."""
        entry = await add_ticker("  pypl  ")
        assert entry["ticker"] == "PYPL"

    async def test_add_empty_ticker(self, temp_db):
        with pytest.raises(ValueError, match="cannot be empty"):
            await add_ticker("   ")

    async def test_remove_ticker(self, temp_db):
        """Can remove a ticker from watchlist."""
        await get_watchlist()  # trigger init
        removed = await remove_ticker("AAPL")
        assert removed is True

        watchlist = await get_watchlist()
        tickers = [w["ticker"] for w in watchlist]
        assert "AAPL" not in tickers
        assert len(watchlist) == 9

    async def test_remove_nonexistent(self, temp_db):
        """Removing a ticker not in watchlist returns False."""
        await get_watchlist()  # trigger init
        removed = await remove_ticker("ZZZZZ")
        assert removed is False


# --- Chat Messages ---


class TestChatMessages:
    async def test_save_and_retrieve(self, temp_db):
        """Messages are saved and returned in chronological order."""
        await save_message("user", "Hello")
        await save_message("assistant", "Hi there!", '{"trades": []}')

        messages = await get_recent_messages()
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"
        assert messages[0]["actions"] is None
        assert messages[1]["role"] == "assistant"
        assert messages[1]["actions"] == '{"trades": []}'

    async def test_invalid_role(self, temp_db):
        with pytest.raises(ValueError, match="Role must be"):
            await save_message("system", "test")

    async def test_limit(self, temp_db):
        """Limit parameter caps returned messages."""
        for i in range(5):
            await save_message("user", f"msg {i}")
        messages = await get_recent_messages(limit=3)
        assert len(messages) == 3
        # Should be the 3 most recent in chronological order
        assert messages[0]["content"] == "msg 2"
        assert messages[2]["content"] == "msg 4"


# --- Portfolio Snapshots ---


class TestSnapshots:
    async def test_record_and_get(self, temp_db):
        """Snapshots are recorded and returned in chronological order."""
        await record_snapshot(10000.0)
        await record_snapshot(10500.0)

        snaps = await get_snapshots()
        assert len(snaps) == 2
        assert snaps[0]["total_value"] == 10000.0
        assert snaps[1]["total_value"] == 10500.0

    async def test_limit(self, temp_db):
        for i in range(5):
            await record_snapshot(10000.0 + i * 100)
        snaps = await get_snapshots(limit=3)
        assert len(snaps) == 3
