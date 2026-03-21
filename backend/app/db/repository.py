"""Repository functions for all database CRUD operations."""

from datetime import datetime, timezone
from uuid import uuid4

from .connection import get_connection
from .schema import DEFAULT_USER_ID


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Portfolio ---


async def get_portfolio(user_id: str = DEFAULT_USER_ID) -> dict:
    """Get user's cash balance and all positions."""
    db = await get_connection()
    try:
        cursor = await db.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        cash_balance = row["cash_balance"] if row else 0.0

        cursor = await db.execute(
            "SELECT ticker, quantity, avg_cost, updated_at FROM positions WHERE user_id = ? AND quantity > 0",
            (user_id,),
        )
        positions = [dict(row) for row in await cursor.fetchall()]

        return {"cash_balance": cash_balance, "positions": positions}
    finally:
        await db.close()


async def execute_trade(
    ticker: str, side: str, quantity: float, price: float, user_id: str = DEFAULT_USER_ID
) -> dict:
    """Execute a trade. Returns the trade record or raises ValueError."""
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    if price <= 0:
        raise ValueError("Price must be positive")
    if side not in ("buy", "sell"):
        raise ValueError("Side must be 'buy' or 'sell'")

    db = await get_connection()
    try:
        # Get current cash
        cursor = await db.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError("User not found")
        cash = row["cash_balance"]

        now = _now()
        trade_id = str(uuid4())
        total_cost = quantity * price

        if side == "buy":
            if total_cost > cash:
                raise ValueError(
                    f"Insufficient cash: need ${total_cost:.2f}, have ${cash:.2f}"
                )
            new_cash = cash - total_cost

            # Update or create position
            cursor = await db.execute(
                "SELECT quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
                (user_id, ticker),
            )
            pos = await cursor.fetchone()
            if pos:
                old_qty = pos["quantity"]
                old_cost = pos["avg_cost"]
                new_qty = old_qty + quantity
                new_avg_cost = ((old_qty * old_cost) + total_cost) / new_qty
                await db.execute(
                    "UPDATE positions SET quantity = ?, avg_cost = ?, updated_at = ? "
                    "WHERE user_id = ? AND ticker = ?",
                    (new_qty, new_avg_cost, now, user_id, ticker),
                )
            else:
                await db.execute(
                    "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (str(uuid4()), user_id, ticker, quantity, price, now),
                )

        else:  # sell
            cursor = await db.execute(
                "SELECT quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
                (user_id, ticker),
            )
            pos = await cursor.fetchone()
            if not pos or pos["quantity"] < quantity:
                available = pos["quantity"] if pos else 0
                raise ValueError(
                    f"Insufficient shares: want to sell {quantity}, have {available}"
                )

            new_qty = pos["quantity"] - quantity
            new_cash = cash + total_cost

            if new_qty == 0:
                await db.execute(
                    "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
                    (user_id, ticker),
                )
            else:
                await db.execute(
                    "UPDATE positions SET quantity = ?, updated_at = ? "
                    "WHERE user_id = ? AND ticker = ?",
                    (new_qty, now, user_id, ticker),
                )

        # Update cash
        await db.execute(
            "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
            (new_cash, user_id),
        )

        # Log trade
        await db.execute(
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (trade_id, user_id, ticker, side, quantity, price, now),
        )

        await db.commit()

        return {
            "id": trade_id,
            "ticker": ticker,
            "side": side,
            "quantity": quantity,
            "price": price,
            "executed_at": now,
        }
    finally:
        await db.close()


async def get_trade_history(user_id: str = DEFAULT_USER_ID, limit: int = 50) -> list[dict]:
    """Get recent trades, newest first."""
    db = await get_connection()
    try:
        cursor = await db.execute(
            "SELECT id, ticker, side, quantity, price, executed_at FROM trades "
            "WHERE user_id = ? ORDER BY executed_at DESC LIMIT ?",
            (user_id, limit),
        )
        return [dict(row) for row in await cursor.fetchall()]
    finally:
        await db.close()


# --- Watchlist ---


async def get_watchlist(user_id: str = DEFAULT_USER_ID) -> list[dict]:
    """Get all watched tickers."""
    db = await get_connection()
    try:
        cursor = await db.execute(
            "SELECT id, ticker, added_at FROM watchlist WHERE user_id = ? ORDER BY added_at",
            (user_id,),
        )
        return [dict(row) for row in await cursor.fetchall()]
    finally:
        await db.close()


async def add_ticker(ticker: str, user_id: str = DEFAULT_USER_ID) -> dict:
    """Add a ticker to the watchlist. Returns the entry or raises ValueError if duplicate."""
    ticker = ticker.upper().strip()
    if not ticker:
        raise ValueError("Ticker cannot be empty")

    db = await get_connection()
    try:
        # Check for duplicate
        cursor = await db.execute(
            "SELECT id FROM watchlist WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        )
        if await cursor.fetchone():
            raise ValueError(f"Ticker {ticker} is already in the watchlist")

        entry_id = str(uuid4())
        now = _now()
        await db.execute(
            "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (entry_id, user_id, ticker, now),
        )
        await db.commit()
        return {"id": entry_id, "ticker": ticker, "added_at": now}
    finally:
        await db.close()


async def remove_ticker(ticker: str, user_id: str = DEFAULT_USER_ID) -> bool:
    """Remove a ticker from the watchlist. Returns True if removed, False if not found."""
    ticker = ticker.upper().strip()
    db = await get_connection()
    try:
        cursor = await db.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


# --- Chat Messages ---


async def save_message(
    role: str, content: str, actions: str | None = None, user_id: str = DEFAULT_USER_ID
) -> dict:
    """Save a chat message."""
    if role not in ("user", "assistant"):
        raise ValueError("Role must be 'user' or 'assistant'")

    db = await get_connection()
    try:
        msg_id = str(uuid4())
        now = _now()
        await db.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (msg_id, user_id, role, content, actions, now),
        )
        await db.commit()
        return {"id": msg_id, "role": role, "content": content, "actions": actions, "created_at": now}
    finally:
        await db.close()


async def get_recent_messages(
    user_id: str = DEFAULT_USER_ID, limit: int = 20
) -> list[dict]:
    """Get recent chat messages, oldest first."""
    db = await get_connection()
    try:
        cursor = await db.execute(
            "SELECT id, role, content, actions, created_at FROM chat_messages "
            "WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        rows = [dict(row) for row in await cursor.fetchall()]
        rows.reverse()  # Return in chronological order
        return rows
    finally:
        await db.close()


# --- Portfolio Snapshots ---


async def record_snapshot(total_value: float, user_id: str = DEFAULT_USER_ID) -> dict:
    """Record a portfolio value snapshot."""
    db = await get_connection()
    try:
        snap_id = str(uuid4())
        now = _now()
        await db.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
            "VALUES (?, ?, ?, ?)",
            (snap_id, user_id, total_value, now),
        )
        await db.commit()
        return {"id": snap_id, "total_value": total_value, "recorded_at": now}
    finally:
        await db.close()


async def get_snapshots(user_id: str = DEFAULT_USER_ID, limit: int = 500) -> list[dict]:
    """Get portfolio snapshots, oldest first."""
    db = await get_connection()
    try:
        cursor = await db.execute(
            "SELECT id, total_value, recorded_at FROM portfolio_snapshots "
            "WHERE user_id = ? ORDER BY recorded_at DESC LIMIT ?",
            (user_id, limit),
        )
        rows = [dict(row) for row in await cursor.fetchall()]
        rows.reverse()  # Return in chronological order
        return rows
    finally:
        await db.close()
