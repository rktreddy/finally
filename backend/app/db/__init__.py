"""Database layer for the FinAlly application."""

from .connection import get_connection, get_db_path, reset_state, set_db_path
from .repository import (
    add_ticker,
    execute_trade,
    get_portfolio,
    get_recent_messages,
    get_snapshots,
    get_trade_history,
    get_watchlist,
    record_snapshot,
    remove_ticker,
    save_message,
)
from .schema import DEFAULT_CASH_BALANCE, DEFAULT_TICKERS, DEFAULT_USER_ID

__all__ = [
    "get_connection",
    "get_db_path",
    "set_db_path",
    "reset_state",
    "get_portfolio",
    "execute_trade",
    "get_trade_history",
    "get_watchlist",
    "add_ticker",
    "remove_ticker",
    "save_message",
    "get_recent_messages",
    "record_snapshot",
    "get_snapshots",
    "DEFAULT_USER_ID",
    "DEFAULT_TICKERS",
    "DEFAULT_CASH_BALANCE",
]
