"""Seed data insertion for FinAlly database.

Inserts the default user profile and watchlist tickers. Uses INSERT OR IGNORE
for idempotency — safe to call multiple times without duplicating data.
"""

from __future__ import annotations

import logging
import uuid

import aiosqlite

logger = logging.getLogger(__name__)

DEFAULT_TICKERS = [
    "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
    "NVDA", "META", "JPM", "V", "NFLX",
]


async def seed_defaults(db: aiosqlite.Connection) -> None:
    """Insert default user profile and watchlist if they don't exist."""
    # Seed user profile (INSERT OR IGNORE for idempotency)
    await db.execute(
        "INSERT OR IGNORE INTO users_profile (id, cash_balance) VALUES (?, ?)",
        ("default", 10000.0),
    )

    # Seed watchlist with the 10 default tickers
    for ticker in DEFAULT_TICKERS:
        await db.execute(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker) VALUES (?, ?, ?)",
            (str(uuid.uuid4()), "default", ticker),
        )

    await db.commit()
    logger.info("Seed data applied: default user + %d watchlist tickers", len(DEFAULT_TICKERS))
