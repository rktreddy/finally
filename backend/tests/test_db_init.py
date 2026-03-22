"""Tests for database initialization, schema creation, and seed data."""

from __future__ import annotations

import aiosqlite
import pytest

from app.db import init_db


async def test_schema_creates_tables():
    """init_db on fresh :memory: DB creates all 6 tables."""
    db = await init_db(":memory:")
    try:
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ) as cursor:
            rows = await cursor.fetchall()
            table_names = sorted(row[0] for row in rows)

        expected = sorted([
            "chat_messages",
            "portfolio_snapshots",
            "positions",
            "trades",
            "users_profile",
            "watchlist",
        ])
        assert table_names == expected
    finally:
        await db.close()


async def test_seed_data_inserted():
    """After init_db, users_profile has 1 row with id='default' and cash_balance=10000.0."""
    db = await init_db(":memory:")
    try:
        async with db.execute(
            "SELECT id, cash_balance FROM users_profile"
        ) as cursor:
            rows = await cursor.fetchall()

        assert len(rows) == 1
        assert rows[0][0] == "default"
        assert rows[0][1] == 10000.0
    finally:
        await db.close()


async def test_watchlist_seed():
    """After init_db, watchlist has exactly 10 rows with the correct tickers."""
    db = await init_db(":memory:")
    try:
        async with db.execute(
            "SELECT ticker FROM watchlist WHERE user_id = 'default' ORDER BY ticker"
        ) as cursor:
            rows = await cursor.fetchall()
            tickers = sorted(row[0] for row in rows)

        expected = sorted([
            "AAPL", "AMZN", "GOOGL", "JPM", "META",
            "MSFT", "NFLX", "NVDA", "TSLA", "V",
        ])
        assert tickers == expected
        assert len(tickers) == 10
    finally:
        await db.close()


async def test_init_idempotent():
    """Calling init_db twice on same DB does not error or duplicate rows."""
    db = await init_db(":memory:")
    try:
        # Run init again on the same connection by executing schema + seed manually
        from pathlib import Path

        from app.db.seed import seed_defaults

        schema_path = Path(__file__).parent.parent / "app" / "db" / "schema.sql"
        schema_sql = schema_path.read_text()
        await db.executescript(schema_sql)
        await seed_defaults(db)

        # Verify no duplicates
        async with db.execute("SELECT COUNT(*) FROM users_profile") as cursor:
            row = await cursor.fetchone()
            assert row[0] == 1

        async with db.execute("SELECT COUNT(*) FROM watchlist") as cursor:
            row = await cursor.fetchone()
            assert row[0] == 10
    finally:
        await db.close()


async def test_default_user_balance():
    """users_profile default row has cash_balance=10000.0."""
    db = await init_db(":memory:")
    try:
        async with db.execute(
            "SELECT cash_balance FROM users_profile WHERE id = 'default'"
        ) as cursor:
            row = await cursor.fetchone()

        assert row is not None
        assert row[0] == 10000.0
    finally:
        await db.close()


async def test_wal_mode():
    """After init_db, PRAGMA journal_mode returns 'wal'.

    Note: :memory: databases do not support WAL mode and always return 'memory'.
    We use a temp file to verify WAL is set correctly.
    """
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = await init_db(db_path)
        try:
            async with db.execute("PRAGMA journal_mode") as cursor:
                row = await cursor.fetchone()
            assert row[0] == "wal"
        finally:
            await db.close()


async def test_foreign_keys():
    """After init_db, PRAGMA foreign_keys returns 1."""
    db = await init_db(":memory:")
    try:
        async with db.execute("PRAGMA foreign_keys") as cursor:
            row = await cursor.fetchone()
        assert row[0] == 1
    finally:
        await db.close()
