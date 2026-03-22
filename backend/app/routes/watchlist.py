"""Watchlist CRUD endpoints for managing tracked tickers."""

from __future__ import annotations

import logging
import sqlite3

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.db.repository import (
    add_watchlist_ticker,
    get_watchlist_tickers,
    remove_watchlist_ticker,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["watchlist"])


class AddTickerRequest(BaseModel):
    """Request body for adding a ticker to the watchlist."""

    ticker: str


@router.get("/watchlist")
async def list_watchlist(request: Request) -> list[dict]:
    """Return all watchlist tickers enriched with live price data from PriceCache."""
    db = request.app.state.db
    cache = request.app.state.cache

    tickers = await get_watchlist_tickers(db)
    result = []
    for item in tickers:
        ticker = item["ticker"]
        price_update = cache.get(ticker)
        entry = {
            "ticker": ticker,
            "added_at": item["added_at"],
            "price": price_update.price if price_update else None,
            "change": price_update.change if price_update else None,
            "change_percent": price_update.change_percent if price_update else None,
            "direction": price_update.direction if price_update else None,
        }
        result.append(entry)
    return result


@router.post("/watchlist", status_code=201)
async def add_ticker(request: Request, body: AddTickerRequest) -> dict:
    """Add a new ticker to the watchlist and register it with the market data source."""
    ticker = body.ticker.strip().upper()
    db = request.app.state.db
    source = request.app.state.source

    try:
        row = await add_watchlist_ticker(db, ticker)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Ticker already in watchlist")

    # Register with market data source so prices start flowing
    await source.add_ticker(ticker)
    logger.info("Added ticker %s to watchlist", ticker)
    return row


@router.delete("/watchlist/{ticker}")
async def remove_ticker(request: Request, ticker: str) -> dict:
    """Remove a ticker from the watchlist, market data source, and price cache."""
    ticker = ticker.upper()
    db = request.app.state.db
    source = request.app.state.source
    cache = request.app.state.cache

    deleted = await remove_watchlist_ticker(db, ticker)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Ticker not in watchlist")

    # Unregister from market data source and clear cached price
    await source.remove_ticker(ticker)
    cache.remove(ticker)
    logger.info("Removed ticker %s from watchlist", ticker)
    return {"status": "removed", "ticker": ticker}
