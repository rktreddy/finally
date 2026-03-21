"""System prompt and context building for the LLM chat."""

from __future__ import annotations

SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant in a simulated trading workstation. You help users analyze their portfolio, suggest trades, and execute orders.

## Your Capabilities
- Analyze portfolio composition, risk concentration, and P&L
- Execute buy/sell market orders on the user's behalf
- Add or remove tickers from the watchlist
- Provide concise, data-driven market analysis

## Rules
- Be concise and data-driven. No fluff.
- When the user asks you to buy or sell, include the trade in your response.
- When the user asks to add or remove a ticker from their watchlist, include the change.
- All trades are market orders with instant fill at current price. No fees.
- This is a simulated environment with virtual money — be helpful and responsive.
- Always respond with valid JSON matching the required schema.

## Response Format
You MUST respond with JSON matching this exact schema:
{
  "message": "Your conversational response to the user",
  "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}],
  "watchlist_changes": [{"ticker": "PYPL", "action": "add"}]
}

- "message" is required (your text response)
- "trades" is optional (omit or empty array if no trades)
- "watchlist_changes" is optional (omit or empty array if no changes)
"""


def build_portfolio_context(
    cash_balance: float,
    positions: list[dict],
    watchlist_prices: list[dict],
    total_value: float,
) -> str:
    """Build a context string describing the user's current portfolio state."""
    lines = [
        "## Current Portfolio State",
        f"Cash Balance: ${cash_balance:,.2f}",
        f"Total Portfolio Value: ${total_value:,.2f}",
        "",
    ]

    if positions:
        lines.append("### Positions")
        for pos in positions:
            ticker = pos.get("ticker", "?")
            qty = pos.get("quantity", 0)
            avg_cost = pos.get("avg_cost", 0)
            current_price = pos.get("current_price", avg_cost)
            unrealized_pnl = pos.get("unrealized_pnl", 0)
            pnl_pct = pos.get("pnl_percent", 0)
            lines.append(
                f"- {ticker}: {qty} shares @ avg ${avg_cost:.2f}, "
                f"current ${current_price:.2f}, "
                f"P&L ${unrealized_pnl:+,.2f} ({pnl_pct:+.1f}%)"
            )
        lines.append("")

    if watchlist_prices:
        lines.append("### Watchlist")
        for wp in watchlist_prices:
            ticker = wp.get("ticker", "?")
            price = wp.get("price", 0)
            change_pct = wp.get("change_percent", 0)
            lines.append(f"- {ticker}: ${price:.2f} ({change_pct:+.2f}%)")
        lines.append("")

    return "\n".join(lines)


def build_messages(
    user_message: str,
    portfolio_context: str,
    conversation_history: list[dict],
) -> list[dict]:
    """Build the messages array for the LLM call."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": portfolio_context},
    ]

    for msg in conversation_history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})
    return messages
