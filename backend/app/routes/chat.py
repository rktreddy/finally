"""Chat endpoint for AI trading assistant."""

from __future__ import annotations

import json
import logging
import os
import sqlite3

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.db.repository import (
    add_watchlist_ticker,
    delete_position,
    get_chat_history,
    get_position,
    get_positions,
    get_user_cash,
    get_watchlist_tickers,
    insert_chat_message,
    insert_trade,
    remove_watchlist_ticker,
    update_cash_balance,
    upsert_position,
)
from app.llm.client import call_llm
from app.llm.mock import generate_mock_response
from app.llm.models import ChatResponse
from app.llm.prompts import build_messages, build_system_prompt
from app.routes.portfolio import record_snapshot

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    message: str


async def assemble_portfolio_context(db, cache) -> dict:
    """Gather current portfolio state for LLM context.

    Returns a dict with cash, enriched positions, enriched watchlist, and total_value.
    """
    cash = await get_user_cash(db)
    positions = await get_positions(db)

    enriched_positions = []
    position_value = 0.0
    for pos in positions:
        current_price = cache.get_price(pos["ticker"]) or 0.0
        unrealized_pnl = (current_price - pos["avg_cost"]) * pos["quantity"]
        enriched_positions.append(
            {
                "ticker": pos["ticker"],
                "quantity": pos["quantity"],
                "avg_cost": pos["avg_cost"],
                "current_price": current_price,
                "unrealized_pnl": round(unrealized_pnl, 2),
            }
        )
        position_value += pos["quantity"] * current_price

    watchlist = await get_watchlist_tickers(db)
    enriched_watchlist = []
    for item in watchlist:
        enriched_watchlist.append(
            {
                "ticker": item["ticker"],
                "price": cache.get_price(item["ticker"]),
            }
        )

    total_value = cash + position_value

    return {
        "cash": cash,
        "positions": enriched_positions,
        "watchlist": enriched_watchlist,
        "total_value": round(total_value, 2),
    }


async def execute_actions(chat_response: ChatResponse, db, cache, source) -> dict:
    """Auto-execute trades and watchlist changes from the LLM response.

    Returns a dict with trades, watchlist_changes, and errors lists.
    Each trade/change entry includes a status field ("executed" or "failed").
    """
    results: dict = {"trades": [], "watchlist_changes": [], "errors": []}

    for trade in chat_response.trades:
        ticker = trade.ticker.strip().upper()
        side = trade.side.lower()

        if side not in ("buy", "sell"):
            error_msg = f"Invalid trade side '{trade.side}' for {ticker}"
            results["errors"].append(error_msg)
            results["trades"].append(
                {"ticker": ticker, "side": side, "quantity": trade.quantity, "status": "failed",
                 "error": error_msg}
            )
            continue

        current_price = cache.get_price(ticker)
        if current_price is None:
            error_msg = f"No price available for {ticker}"
            results["errors"].append(error_msg)
            results["trades"].append(
                {"ticker": ticker, "side": side, "quantity": trade.quantity, "status": "failed",
                 "error": error_msg}
            )
            continue

        if side == "buy":
            cash = await get_user_cash(db)
            total_cost = trade.quantity * current_price

            if total_cost > cash:
                error_msg = f"Insufficient cash for {ticker} (need ${total_cost:.2f}, have ${cash:.2f})"
                results["errors"].append(error_msg)
                results["trades"].append(
                    {"ticker": ticker, "side": "buy", "quantity": trade.quantity,
                     "status": "failed", "error": error_msg, "price": current_price}
                )
                continue

            # Compute new average cost
            pos = await get_position(db, ticker)
            if pos:
                new_qty = pos["quantity"] + trade.quantity
                new_avg = (
                    (pos["quantity"] * pos["avg_cost"] + trade.quantity * current_price) / new_qty
                )
            else:
                new_qty = trade.quantity
                new_avg = current_price

            await update_cash_balance(db, cash - total_cost)
            await upsert_position(db, ticker, new_qty, new_avg)
            await insert_trade(db, ticker, "buy", trade.quantity, current_price)
            await db.commit()
            await record_snapshot(db, cache)

            results["trades"].append(
                {"ticker": ticker, "side": "buy", "quantity": trade.quantity,
                 "status": "executed", "price": current_price}
            )
            logger.info("Auto-executed buy: %s x%.2f @ $%.2f", ticker, trade.quantity,
                         current_price)

        else:
            # sell
            cash = await get_user_cash(db)
            pos = await get_position(db, ticker)

            if pos is None:
                error_msg = f"No position in {ticker} to sell"
                results["errors"].append(error_msg)
                results["trades"].append(
                    {"ticker": ticker, "side": "sell", "quantity": trade.quantity,
                     "status": "failed", "error": error_msg}
                )
                continue

            if trade.quantity > pos["quantity"] + 1e-9:
                error_msg = (
                    f"Insufficient shares of {ticker} "
                    f"(want {trade.quantity}, have {pos['quantity']})"
                )
                results["errors"].append(error_msg)
                results["trades"].append(
                    {"ticker": ticker, "side": "sell", "quantity": trade.quantity,
                     "status": "failed", "error": error_msg}
                )
                continue

            sell_qty = min(trade.quantity, pos["quantity"])
            await update_cash_balance(db, cash + sell_qty * current_price)

            remaining = pos["quantity"] - sell_qty
            if remaining < 1e-9:
                await delete_position(db, ticker)
            else:
                await upsert_position(db, ticker, remaining, pos["avg_cost"])

            await insert_trade(db, ticker, "sell", sell_qty, current_price)
            await db.commit()
            await record_snapshot(db, cache)

            results["trades"].append(
                {"ticker": ticker, "side": "sell", "quantity": sell_qty,
                 "status": "executed", "price": current_price}
            )
            logger.info("Auto-executed sell: %s x%.2f @ $%.2f", ticker, sell_qty, current_price)

    for wl_change in chat_response.watchlist_changes:
        ticker = wl_change.ticker.strip().upper()
        action = wl_change.action.lower()

        if action == "add":
            try:
                await add_watchlist_ticker(db, ticker)
                await source.add_ticker(ticker)
                results["watchlist_changes"].append(
                    {"ticker": ticker, "action": "add", "status": "executed"}
                )
                logger.info("Auto-added %s to watchlist", ticker)
            except sqlite3.IntegrityError:
                error_msg = f"{ticker} already in watchlist"
                results["errors"].append(error_msg)
                results["watchlist_changes"].append(
                    {"ticker": ticker, "action": "add", "status": "failed", "error": error_msg}
                )

        elif action == "remove":
            deleted = await remove_watchlist_ticker(db, ticker)
            if deleted == 0:
                error_msg = f"{ticker} not in watchlist"
                results["errors"].append(error_msg)
                results["watchlist_changes"].append(
                    {"ticker": ticker, "action": "remove", "status": "failed", "error": error_msg}
                )
            else:
                await source.remove_ticker(ticker)
                cache.remove(ticker)
                results["watchlist_changes"].append(
                    {"ticker": ticker, "action": "remove", "status": "executed"}
                )
                logger.info("Auto-removed %s from watchlist", ticker)

    return results


@router.post("/chat")
async def chat(request: Request, body: ChatRequest) -> dict:
    """Process a chat message: call LLM (or mock), auto-execute actions, persist history."""
    db = request.app.state.db
    cache = request.app.state.cache
    source = request.app.state.source

    # Persist user message first
    await insert_chat_message(db, "user", body.message)

    # Get LLM response
    if os.environ.get("LLM_MOCK", "").lower() == "true":
        chat_response = generate_mock_response(body.message)
    else:
        if not os.environ.get("OPENROUTER_API_KEY"):
            raise HTTPException(status_code=503, detail="LLM not configured")

        ctx = await assemble_portfolio_context(db, cache)
        system_prompt = build_system_prompt(
            ctx["cash"], ctx["positions"], ctx["watchlist"], ctx["total_value"]
        )
        history = await get_chat_history(db, limit=20)
        messages = build_messages(system_prompt, history, body.message)
        chat_response = await call_llm(messages)

    # Auto-execute any trades or watchlist changes
    actions = await execute_actions(chat_response, db, cache, source)

    # Persist assistant message with actions
    actions_json = json.dumps(actions) if any(actions.values()) else None
    await insert_chat_message(db, "assistant", chat_response.message, actions=actions_json)

    return {"message": chat_response.message, "actions": actions}
