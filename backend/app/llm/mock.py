"""Mock LLM responses for testing (LLM_MOCK=true)."""

from __future__ import annotations

from .models import ChatResponse, TradeAction, WatchlistChange


def mock_response(user_message: str) -> ChatResponse:
    """Return a deterministic mock response based on the user message content."""
    msg_lower = user_message.lower()

    if "buy" in msg_lower:
        # Extract ticker and quantity if possible, otherwise use defaults
        ticker = _extract_ticker(msg_lower) or "AAPL"
        quantity = _extract_quantity(msg_lower) or 10
        return ChatResponse(
            message=f"Mock: Buying {quantity} shares of {ticker}.",
            trades=[TradeAction(ticker=ticker, side="buy", quantity=quantity)],
        )

    if "sell" in msg_lower:
        ticker = _extract_ticker(msg_lower) or "AAPL"
        quantity = _extract_quantity(msg_lower) or 10
        return ChatResponse(
            message=f"Mock: Selling {quantity} shares of {ticker}.",
            trades=[TradeAction(ticker=ticker, side="sell", quantity=quantity)],
        )

    if "add" in msg_lower and ("watch" in msg_lower or "ticker" in msg_lower):
        ticker = _extract_ticker(msg_lower) or "PYPL"
        return ChatResponse(
            message=f"Mock: Adding {ticker} to your watchlist.",
            watchlist_changes=[WatchlistChange(ticker=ticker, action="add")],
        )

    if "remove" in msg_lower and ("watch" in msg_lower or "ticker" in msg_lower):
        ticker = _extract_ticker(msg_lower) or "TSLA"
        return ChatResponse(
            message=f"Mock: Removing {ticker} from your watchlist.",
            watchlist_changes=[WatchlistChange(ticker=ticker, action="remove")],
        )

    return ChatResponse(
        message=(
            "Mock: Your portfolio looks well-diversified. "
            "Consider rebalancing if any single position exceeds 20% of total value."
        ),
    )


# Common tickers for extraction
_KNOWN_TICKERS = {
    "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX",
    "PYPL", "DIS", "BABA", "AMD", "INTC", "CRM", "UBER", "SPOT", "SQ", "COIN",
}


def _extract_ticker(msg: str) -> str | None:
    """Try to extract a ticker symbol from the message."""
    words = msg.upper().split()
    for word in words:
        # Strip punctuation
        clean = "".join(c for c in word if c.isalpha())
        if clean in _KNOWN_TICKERS:
            return clean
    return None


def _extract_quantity(msg: str) -> float | None:
    """Try to extract a numeric quantity from the message."""
    words = msg.split()
    for word in words:
        try:
            val = float(word)
            if val > 0:
                return val
        except ValueError:
            continue
    return None
