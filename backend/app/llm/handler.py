"""Chat handler — orchestrates LLM calls, trade execution, and persistence."""

from __future__ import annotations

import json
import logging
import os

from app.db import (
    add_ticker,
    execute_trade,
    get_portfolio,
    get_recent_messages,
    get_watchlist,
    record_snapshot,
    remove_ticker,
    save_message,
)
from app.db.schema import DEFAULT_USER_ID
from app.market.cache import PriceCache

from .client import call_llm
from .mock import mock_response
from .models import ChatResponse
from .prompt import build_messages, build_portfolio_context

logger = logging.getLogger(__name__)


async def handle_chat_message(
    user_message: str,
    price_cache: PriceCache,
    user_id: str = DEFAULT_USER_ID,
) -> dict:
    """Process a user chat message end-to-end.

    Returns a dict with: message, trades (with results), watchlist_changes (with results).
    """
    # 1. Save the user message
    await save_message("user", user_message, user_id=user_id)

    # 2. Load portfolio context
    portfolio_context = await _build_context(price_cache, user_id)

    # 3. Load conversation history (last 20 messages)
    history_rows = await get_recent_messages(user_id=user_id, limit=20)
    history = [{"role": r["role"], "content": r["content"]} for r in history_rows]

    # 4. Get LLM response (mock or real)
    if os.environ.get("LLM_MOCK", "").lower() == "true":
        chat_response = mock_response(user_message)
    else:
        messages = build_messages(user_message, portfolio_context, history)
        try:
            chat_response = call_llm(messages)
        except ValueError:
            chat_response = ChatResponse(
                message="I'm having trouble processing your request right now. Please try again."
            )

    # 5. Auto-execute trades
    trade_results = []
    for trade in chat_response.trades:
        result = await _execute_trade(price_cache, trade, user_id)
        trade_results.append(result)

    # 6. Auto-execute watchlist changes
    watchlist_results = []
    for change in chat_response.watchlist_changes:
        result = await _execute_watchlist_change(change, user_id)
        watchlist_results.append(result)

    # 7. Save assistant message with actions
    actions = None
    if trade_results or watchlist_results:
        actions = json.dumps({"trades": trade_results, "watchlist_changes": watchlist_results})

    await save_message("assistant", chat_response.message, actions=actions, user_id=user_id)

    return {
        "message": chat_response.message,
        "trades": trade_results,
        "watchlist_changes": watchlist_results,
    }


async def _build_context(price_cache: PriceCache, user_id: str) -> str:
    """Build portfolio context string for the LLM prompt."""
    port = await get_portfolio(user_id=user_id)
    cash_balance = port["cash_balance"]

    positions = []
    total_position_value = 0.0
    for pos in port["positions"]:
        ticker = pos["ticker"]
        qty = pos["quantity"]
        avg_cost = pos["avg_cost"]
        current_price = price_cache.get_price(ticker) or avg_cost
        market_value = qty * current_price
        cost_basis = qty * avg_cost
        unrealized_pnl = market_value - cost_basis
        pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis != 0 else 0
        total_position_value += market_value
        positions.append({
            "ticker": ticker,
            "quantity": qty,
            "avg_cost": avg_cost,
            "current_price": current_price,
            "unrealized_pnl": unrealized_pnl,
            "pnl_percent": pnl_pct,
        })

    wl = await get_watchlist(user_id=user_id)
    watchlist_prices = []
    for entry in wl:
        ticker = entry["ticker"]
        update = price_cache.get(ticker)
        if update:
            watchlist_prices.append({
                "ticker": ticker,
                "price": update.price,
                "change_percent": update.change_percent,
            })
        else:
            watchlist_prices.append({"ticker": ticker, "price": 0, "change_percent": 0})

    total_value = cash_balance + total_position_value

    return build_portfolio_context(cash_balance, positions, watchlist_prices, total_value)


async def _execute_trade(price_cache: PriceCache, trade, user_id: str) -> dict:
    """Execute a single trade action. Returns a result dict."""
    ticker = trade.ticker.upper()
    side = trade.side
    quantity = trade.quantity

    current_price = price_cache.get_price(ticker)
    if current_price is None:
        return {
            "ticker": ticker, "side": side, "quantity": quantity,
            "status": "failed", "error": f"No price available for {ticker}",
        }

    try:
        result = await execute_trade(ticker, side, quantity, current_price, user_id=user_id)
        # Record portfolio snapshot after trade
        port = await get_portfolio(user_id=user_id)
        total = port["cash_balance"]
        for pos in port["positions"]:
            p = price_cache.get_price(pos["ticker"])
            total += pos["quantity"] * (p if p is not None else pos["avg_cost"])
        await record_snapshot(total, user_id=user_id)

        return {
            "ticker": ticker, "side": side, "quantity": quantity,
            "price": current_price, "total": quantity * current_price,
            "status": "executed",
        }
    except ValueError as e:
        return {
            "ticker": ticker, "side": side, "quantity": quantity,
            "status": "failed", "error": str(e),
        }


async def _execute_watchlist_change(change, user_id: str) -> dict:
    """Execute a single watchlist change. Returns a result dict."""
    ticker = change.ticker.upper()
    action = change.action

    if action == "add":
        try:
            await add_ticker(ticker, user_id=user_id)
            return {"ticker": ticker, "action": action, "status": "added"}
        except ValueError:
            return {"ticker": ticker, "action": action, "status": "already_exists"}

    elif action == "remove":
        removed = await remove_ticker(ticker, user_id=user_id)
        if removed:
            return {"ticker": ticker, "action": action, "status": "removed"}
        return {"ticker": ticker, "action": action, "status": "not_found"}

    return {"ticker": ticker, "action": action, "status": "unknown_action"}
