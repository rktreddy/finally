"""Portfolio API endpoints."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.db import get_portfolio, execute_trade, get_snapshots, record_snapshot

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class TradeRequest(BaseModel):
    ticker: str
    quantity: float
    side: str  # "buy" or "sell"


@router.get("")
async def get_portfolio_endpoint(request: Request) -> dict:
    """Current positions, cash balance, total value, unrealized P&L."""
    price_cache = request.app.state.price_cache

    portfolio = await get_portfolio()
    cash = portfolio["cash_balance"]
    positions = portfolio["positions"]

    enriched_positions = []
    total_positions_value = 0.0

    for pos in positions:
        ticker = pos["ticker"]
        current_price = price_cache.get_price(ticker)
        if current_price is None:
            current_price = pos["avg_cost"]  # fallback

        market_value = pos["quantity"] * current_price
        cost_basis = pos["quantity"] * pos["avg_cost"]
        unrealized_pnl = market_value - cost_basis
        pnl_percent = (unrealized_pnl / cost_basis * 100) if cost_basis != 0 else 0.0
        total_positions_value += market_value

        enriched_positions.append({
            "ticker": ticker,
            "quantity": pos["quantity"],
            "avg_cost": round(pos["avg_cost"], 2),
            "current_price": round(current_price, 2),
            "market_value": round(market_value, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "pnl_percent": round(pnl_percent, 2),
        })

    total_value = cash + total_positions_value

    return {
        "cash_balance": round(cash, 2),
        "positions": enriched_positions,
        "total_value": round(total_value, 2),
        "total_unrealized_pnl": round(total_positions_value - sum(
            p["quantity"] * p["avg_cost"] for p in positions
        ), 2),
    }


@router.post("/trade")
async def execute_trade_endpoint(trade: TradeRequest, request: Request) -> dict:
    """Execute a market order trade at the current price."""
    price_cache = request.app.state.price_cache
    ticker = trade.ticker.upper().strip()

    current_price = price_cache.get_price(ticker)
    if current_price is None:
        raise HTTPException(status_code=400, detail=f"No price available for {ticker}")

    try:
        result = await execute_trade(
            ticker=ticker,
            side=trade.side,
            quantity=trade.quantity,
            price=current_price,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Record portfolio snapshot after trade
    try:
        portfolio = await get_portfolio()
        total = portfolio["cash_balance"]
        for pos in portfolio["positions"]:
            p = price_cache.get_price(pos["ticker"])
            if p is not None:
                total += pos["quantity"] * p
            else:
                total += pos["quantity"] * pos["avg_cost"]
        await record_snapshot(total)
    except Exception:
        pass  # Non-critical; don't fail the trade response

    return result


@router.get("/history")
async def get_portfolio_history() -> dict:
    """Portfolio value snapshots over time for P&L chart."""
    snapshots = await get_snapshots()
    return {"snapshots": snapshots}
