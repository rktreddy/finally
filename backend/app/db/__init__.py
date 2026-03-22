"""Database layer for FinAlly.

Public API:
    init_db      - Initialize database connection with schema and seed data
    get_db_path  - Get the database file path from environment or default
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import aiosqlite

from .seed import seed_defaults

logger = logging.getLogger(__name__)

__all__ = ["init_db", "get_db_path"]


def get_db_path() -> str:
    """Return the database file path, configurable via DB_PATH env var."""
    return os.environ.get("DB_PATH", "db/finally.db")


async def init_db(db_path: str) -> aiosqlite.Connection:
    """Initialize and return an aiosqlite connection with schema and seed data.

    Opens a connection, enables WAL mode and foreign keys, creates all tables
    from schema.sql (idempotent via CREATE TABLE IF NOT EXISTS), and seeds
    default data (idempotent via INSERT OR IGNORE).

    The caller is responsible for closing the returned connection.
    """
    # Ensure parent directory exists (skip for :memory: databases)
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row

    # Enable WAL mode for concurrent reads during SSE streaming
    await db.execute("PRAGMA journal_mode=WAL")
    # Enable foreign key enforcement
    await db.execute("PRAGMA foreign_keys=ON")

    # Read and execute schema DDL
    schema_path = Path(__file__).parent / "schema.sql"
    schema_sql = schema_path.read_text()
    await db.executescript(schema_sql)

    # Seed default data (user profile + watchlist tickers)
    await seed_defaults(db)

    logger.info("Database initialized at %s", db_path)
    return db
