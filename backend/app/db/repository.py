"""Database repository functions for FinAlly.

All SQL query functions for watchlist, portfolio, trades, and snapshots.
Each function receives an aiosqlite.Connection and operates on it directly.

Functions that are used within a transaction (update_cash_balance, upsert_position,
delete_position, insert_trade) do NOT commit — the caller manages the transaction.
Standalone functions (add_watchlist_ticker, remove_watchlist_ticker, insert_snapshot)
commit after their operation.
"""

from __future__ import annotations

import logging
import uuid

import aiosqlite

logger = logging.getLogger(__name__)

__all__ = [
    "get_watchlist_tickers",
    "add_watchlist_ticker",
    "remove_watchlist_ticker",
    "get_user_cash",
    "get_positions",
    "get_position",
    "update_cash_balance",
    "upsert_position",
    "delete_position",
    "insert_trade",
    "insert_snapshot",
    "get_snapshots",
]


# --- Watchlist ---


async def get_watchlist_tickers(
    db: aiosqlite.Connection, user_id: str = "default"
) -> list[dict]:
    """Return all watchlist tickers for the given user, ordered by add time."""
    async with db.execute(
        "SELECT ticker, added_at FROM watchlist WHERE user_id = ? ORDER BY added_at",
        (user_id,),
    ) as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def add_watchlist_ticker(
    db: aiosqlite.Connection, ticker: str, user_id: str = "default"
) -> dict:
    """Insert a new watchlist entry and return it as a dict.

    Raises sqlite3.IntegrityError if the (user_id, ticker) pair already exists.
    """
    row_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO watchlist (id, user_id, ticker) VALUES (?, ?, ?)",
        (row_id, user_id, ticker),
    )
    await db.commit()

    # Read back the inserted row to get the server-generated added_at
    async with db.execute(
        "SELECT id, ticker, added_at FROM watchlist WHERE id = ?",
        (row_id,),
    ) as cursor:
        row = await cursor.fetchone()
        return dict(row)


async def remove_watchlist_ticker(
    db: aiosqlite.Connection, ticker: str, user_id: str = "default"
) -> int:
    """Delete a ticker from the watchlist. Returns number of rows deleted (0 or 1)."""
    cursor = await db.execute(
        "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    )
    await db.commit()
    return cursor.rowcount


# --- Portfolio ---


async def get_user_cash(
    db: aiosqlite.Connection, user_id: str = "default"
) -> float:
    """Return the cash balance for the given user."""
    async with db.execute(
        "SELECT cash_balance FROM users_profile WHERE id = ?",
        (user_id,),
    ) as cursor:
        row = await cursor.fetchone()
        return float(row["cash_balance"])


async def get_positions(
    db: aiosqlite.Connection, user_id: str = "default"
) -> list[dict]:
    """Return all positions for the given user."""
    async with db.execute(
        "SELECT id, ticker, quantity, avg_cost, updated_at FROM positions WHERE user_id = ?",
        (user_id,),
    ) as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_position(
    db: aiosqlite.Connection, ticker: str, user_id: str = "default"
) -> dict | None:
    """Return a single position or None if not found."""
    async with db.execute(
        "SELECT id, ticker, quantity, avg_cost, updated_at FROM positions "
        "WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    ) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_cash_balance(
    db: aiosqlite.Connection, new_balance: float, user_id: str = "default"
) -> None:
    """Update the cash balance. Does NOT commit — caller manages transaction."""
    await db.execute(
        "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
        (new_balance, user_id),
    )


async def upsert_position(
    db: aiosqlite.Connection,
    ticker: str,
    quantity: float,
    avg_cost: float,
    user_id: str = "default",
) -> None:
    """Insert or update a position. Does NOT commit — caller manages transaction."""
    await db.execute(
        "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(user_id, ticker) DO UPDATE SET "
        "quantity = ?, avg_cost = ?, updated_at = datetime('now')",
        (str(uuid.uuid4()), user_id, ticker, quantity, avg_cost, quantity, avg_cost),
    )


async def delete_position(
    db: aiosqlite.Connection, ticker: str, user_id: str = "default"
) -> None:
    """Delete a position. Does NOT commit — caller manages transaction."""
    await db.execute(
        "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    )


# --- Trades ---


async def insert_trade(
    db: aiosqlite.Connection,
    ticker: str,
    side: str,
    quantity: float,
    price: float,
    user_id: str = "default",
) -> dict:
    """Record a trade. Does NOT commit — caller manages transaction.

    Returns a dict with the trade details including the generated id and executed_at.
    """
    trade_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO trades (id, user_id, ticker, side, quantity, price) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (trade_id, user_id, ticker, side, quantity, price),
    )

    # Read back to get the server-generated executed_at
    async with db.execute(
        "SELECT id, ticker, side, quantity, price, executed_at FROM trades WHERE id = ?",
        (trade_id,),
    ) as cursor:
        row = await cursor.fetchone()
        return dict(row)


# --- Portfolio Snapshots ---


async def insert_snapshot(
    db: aiosqlite.Connection, total_value: float, user_id: str = "default"
) -> None:
    """Record a portfolio value snapshot. Commits after insert."""
    await db.execute(
        "INSERT INTO portfolio_snapshots (id, user_id, total_value) VALUES (?, ?, ?)",
        (str(uuid.uuid4()), user_id, total_value),
    )
    await db.commit()


async def get_snapshots(
    db: aiosqlite.Connection, user_id: str = "default", limit: int = 500
) -> list[dict]:
    """Return portfolio snapshots ordered by time, up to the given limit."""
    async with db.execute(
        "SELECT total_value, recorded_at FROM portfolio_snapshots "
        "WHERE user_id = ? ORDER BY recorded_at ASC LIMIT ?",
        (user_id, limit),
    ) as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
