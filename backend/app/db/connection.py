"""Database connection management with lazy initialization."""

import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import aiosqlite

from .schema import DEFAULT_CASH_BALANCE, DEFAULT_TICKERS, DEFAULT_USER_ID, SCHEMA_SQL

# Default path: backend/../db/finally.db
_DEFAULT_DB_PATH = str(Path(__file__).resolve().parent.parent.parent.parent / "db" / "finally.db")

_db_path: str | None = None
_initialized: bool = False


def get_db_path() -> str:
    global _db_path
    if _db_path is None:
        _db_path = os.environ.get("FINALLY_DB_PATH", _DEFAULT_DB_PATH)
    return _db_path


def set_db_path(path: str) -> None:
    """Override the database path (useful for testing)."""
    global _db_path, _initialized
    _db_path = path
    _initialized = False


async def get_connection() -> aiosqlite.Connection:
    """Get a database connection, initializing the DB if needed."""
    global _initialized
    db_path = get_db_path()

    # Ensure parent directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")

    if not _initialized:
        await _initialize(db)
        _initialized = True

    return db


async def _initialize(db: aiosqlite.Connection) -> None:
    """Create schema and seed data if tables are empty."""
    await db.executescript(SCHEMA_SQL)

    # Check if user profile already exists
    cursor = await db.execute(
        "SELECT id FROM users_profile WHERE id = ?", (DEFAULT_USER_ID,)
    )
    existing = await cursor.fetchone()
    if existing:
        return

    now = datetime.now(timezone.utc).isoformat()

    # Seed default user
    await db.execute(
        "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
        (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, now),
    )

    # Seed default watchlist
    for ticker in DEFAULT_TICKERS:
        await db.execute(
            "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (str(uuid4()), DEFAULT_USER_ID, ticker, now),
        )

    await db.commit()


def reset_state() -> None:
    """Reset module state (for testing)."""
    global _db_path, _initialized
    _db_path = None
    _initialized = False
