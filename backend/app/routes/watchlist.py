"""Watchlist API endpoints."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.db import get_watchlist, add_ticker, remove_ticker

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class AddTickerRequest(BaseModel):
    ticker: str


@router.get("")
async def get_watchlist_endpoint(request: Request) -> dict:
    """Current watchlist tickers with latest prices."""
    price_cache = request.app.state.price_cache
    entries = await get_watchlist()

    tickers = []
    for entry in entries:
        ticker = entry["ticker"]
        price_update = price_cache.get(ticker)
        ticker_data = {
            "ticker": ticker,
            "added_at": entry["added_at"],
        }
        if price_update:
            ticker_data.update(price_update.to_dict())
        tickers.append(ticker_data)

    return {"watchlist": tickers}


@router.post("")
async def add_ticker_endpoint(body: AddTickerRequest, request: Request) -> dict:
    """Add a ticker to the watchlist."""
    market_data = request.app.state.market_data_source

    try:
        entry = await add_ticker(body.ticker)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Start tracking in market data source
    await market_data.add_ticker(entry["ticker"])

    return entry


@router.delete("/{ticker}")
async def remove_ticker_endpoint(ticker: str, request: Request) -> dict:
    """Remove a ticker from the watchlist."""
    market_data = request.app.state.market_data_source

    removed = await remove_ticker(ticker)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} not in watchlist")

    # Stop tracking in market data source
    await market_data.remove_ticker(ticker.upper().strip())

    return {"removed": ticker.upper().strip()}
