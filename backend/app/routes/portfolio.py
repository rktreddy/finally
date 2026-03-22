"""Portfolio, trade execution, and snapshot endpoints."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.db.repository import (
    delete_position,
    get_position,
    get_positions,
    get_snapshots,
    get_user_cash,
    insert_snapshot,
    insert_trade,
    update_cash_balance,
    upsert_position,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["portfolio"])


class TradeRequest(BaseModel):
    """Request body for executing a trade."""

    ticker: str
    quantity: float
    side: str


async def record_snapshot(db, cache, user_id: str = "default") -> None:
    """Compute current portfolio value and record a snapshot.

    Shared helper used by both the background task and post-trade inline recording.
    """
    cash = await get_user_cash(db, user_id)
    positions = await get_positions(db, user_id)
    total_value = cash + sum(
        pos["quantity"] * (cache.get_price(pos["ticker"]) or 0.0) for pos in positions
    )
    await insert_snapshot(db, total_value, user_id)


async def snapshot_loop(app) -> None:
    """Background task that records portfolio snapshots every 30 seconds."""
    while True:
        await asyncio.sleep(30)
        try:
            db = app.state.db
            cache = app.state.cache
            await record_snapshot(db, cache)
            logger.debug("Recorded periodic portfolio snapshot")
        except asyncio.CancelledError:
            logger.info("Snapshot task cancelled")
            raise
        except Exception:
            logger.exception("Error recording portfolio snapshot")


@router.get("/portfolio")
async def get_portfolio(request: Request) -> dict:
    """Return current portfolio with live-valued positions and unrealized P&L."""
    db = request.app.state.db
    cache = request.app.state.cache

    cash = await get_user_cash(db)
    positions = await get_positions(db)

    enriched = []
    total_pnl = 0.0
    for pos in positions:
        current_price = cache.get_price(pos["ticker"]) or 0.0
        unrealized_pnl = (current_price - pos["avg_cost"]) * pos["quantity"]
        pnl_percent = (
            ((current_price - pos["avg_cost"]) / pos["avg_cost"] * 100)
            if pos["avg_cost"] > 0
            else 0.0
        )
        enriched.append(
            {
                "ticker": pos["ticker"],
                "quantity": pos["quantity"],
                "avg_cost": pos["avg_cost"],
                "current_price": current_price,
                "unrealized_pnl": round(unrealized_pnl, 2),
                "pnl_percent": round(pnl_percent, 2),
            }
        )
        total_pnl += unrealized_pnl

    total_value = cash + sum(p["quantity"] * p["current_price"] for p in enriched)

    return {
        "cash": cash,
        "positions": enriched,
        "total_value": round(total_value, 2),
        "total_pnl": round(total_pnl, 2),
    }


@router.post("/portfolio/trade")
async def execute_trade(request: Request, body: TradeRequest) -> dict:
    """Execute a buy or sell trade at the current market price."""
    ticker = body.ticker.strip().upper()

    if body.side not in ("buy", "sell"):
        raise HTTPException(status_code=400, detail="Side must be 'buy' or 'sell'")
    if body.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    db = request.app.state.db
    cache = request.app.state.cache

    current_price = cache.get_price(ticker)
    if current_price is None:
        raise HTTPException(status_code=400, detail=f"No price available for {ticker}")

    cash = await get_user_cash(db)
    total_cost = body.quantity * current_price

    if body.side == "buy":
        if total_cost > cash:
            raise HTTPException(status_code=400, detail="Insufficient cash")

        new_cash = cash - total_cost
        pos = await get_position(db, ticker)

        if pos:
            new_qty = pos["quantity"] + body.quantity
            new_avg = (pos["quantity"] * pos["avg_cost"] + body.quantity * current_price) / new_qty
        else:
            new_qty = body.quantity
            new_avg = current_price

        await update_cash_balance(db, new_cash)
        await upsert_position(db, ticker, new_qty, new_avg)
        trade = await insert_trade(db, ticker, "buy", body.quantity, current_price)
        await db.commit()

    else:
        # sell
        pos = await get_position(db, ticker)
        if pos is None:
            raise HTTPException(status_code=400, detail=f"No position in {ticker}")

        if body.quantity > pos["quantity"] + 1e-9:
            raise HTTPException(status_code=400, detail="Insufficient shares")

        sell_qty = min(body.quantity, pos["quantity"])
        new_cash = cash + sell_qty * current_price
        remaining = pos["quantity"] - sell_qty

        await update_cash_balance(db, new_cash)

        if remaining < 1e-9:
            await delete_position(db, ticker)
        else:
            await upsert_position(db, ticker, remaining, pos["avg_cost"])

        trade = await insert_trade(db, ticker, "sell", sell_qty, current_price)
        await db.commit()
        total_cost = sell_qty * current_price

    # Record immediate post-trade snapshot
    await record_snapshot(db, cache)

    return {"trade": trade, "cash_balance": new_cash}


@router.get("/portfolio/history")
async def get_portfolio_history(request: Request) -> dict:
    """Return portfolio value snapshots for P&L charting."""
    db = request.app.state.db
    snapshots = await get_snapshots(db)
    return {"snapshots": snapshots}
