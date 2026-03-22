"""Deterministic mock response generator for LLM_MOCK=true."""

from __future__ import annotations

from .models import ChatResponse, TradeAction, WatchlistAction


def generate_mock_response(user_message: str) -> ChatResponse:
    """Return a deterministic ChatResponse based on keywords in the user message.

    Used when LLM_MOCK=true to enable fast, free, reproducible testing
    without calling OpenRouter.
    """
    msg = user_message.lower()

    if "buy" in msg:
        return ChatResponse(
            message="I've placed a buy order for 10 shares of AAPL.",
            trades=[TradeAction(ticker="AAPL", side="buy", quantity=10)],
        )

    if "sell" in msg:
        return ChatResponse(
            message="I've placed a sell order for 5 shares of AAPL.",
            trades=[TradeAction(ticker="AAPL", side="sell", quantity=5)],
        )

    if "add" in msg:
        return ChatResponse(
            message="I've added PYPL to your watchlist.",
            watchlist_changes=[WatchlistAction(ticker="PYPL", action="add")],
        )

    if "remove" in msg:
        return ChatResponse(
            message="I've removed PYPL from your watchlist.",
            watchlist_changes=[WatchlistAction(ticker="PYPL", action="remove")],
        )

    return ChatResponse(
        message="Your portfolio is well-diversified across tech and finance sectors. "
        "Your total value reflects current market conditions.",
    )
