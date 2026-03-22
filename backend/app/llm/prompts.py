"""System prompt builder and context assembly for LLM calls."""

from __future__ import annotations


def build_system_prompt(
    cash: float,
    positions: list[dict],
    watchlist: list[dict],
    total_value: float,
) -> str:
    """Build the system prompt with portfolio context for the LLM.

    The prompt includes the assistant's role, portfolio state, and response format instructions.
    """
    # Format positions table
    if positions:
        pos_lines = []
        for p in positions:
            ticker = p.get("ticker", "???")
            qty = p.get("quantity", 0)
            avg_cost = p.get("avg_cost", 0.0)
            current_price = p.get("current_price", 0.0)
            pnl = p.get("unrealized_pnl", 0.0)
            pos_lines.append(
                f"  {ticker}: {qty} shares, avg cost ${avg_cost:.2f}, "
                f"current ${current_price:.2f}, P&L ${pnl:.2f}"
            )
        positions_text = "\n".join(pos_lines)
    else:
        positions_text = "  No positions"

    # Format watchlist
    if watchlist:
        wl_lines = []
        for w in watchlist:
            ticker = w.get("ticker", "???")
            price = w.get("price")
            if price is not None:
                wl_lines.append(f"  {ticker}: ${price:.2f}")
            else:
                wl_lines.append(f"  {ticker}: price unavailable")
        watchlist_text = "\n".join(wl_lines)
    else:
        watchlist_text = "  Empty watchlist"

    return f"""You are FinAlly, an AI trading assistant for a simulated trading platform.

Your capabilities:
- Analyze portfolio composition, risk concentration, and P&L
- Suggest trades with clear reasoning
- Execute trades when the user asks or agrees
- Manage the watchlist proactively (add/remove tickers)
- Be concise and data-driven in responses

Current Portfolio State:
- Cash: ${cash:,.2f}
- Total Portfolio Value: ${total_value:,.2f}

Positions:
{positions_text}

Watchlist:
{watchlist_text}

Response Format:
You must respond with valid JSON matching this schema:
- "message" (required): Your conversational response to the user
- "trades" (optional): Array of trades to execute, each with "ticker", "side" (buy/sell), "quantity"
- "watchlist_changes" (optional): Array of watchlist changes, each with "ticker", "action" (add/remove)

Example response:
{{"message": "I recommend buying 5 shares of AAPL.", "trades": [{{"ticker": "AAPL", "side": "buy", "quantity": 5}}], "watchlist_changes": []}}"""


def build_messages(
    system_prompt: str, history: list[dict], user_message: str
) -> list[dict]:
    """Assemble the full message list for an LLM call.

    Returns a list with the system prompt, conversation history, and the new user message.
    """
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend({"role": msg["role"], "content": msg["content"]} for msg in history)
    messages.append({"role": "user", "content": user_message})
    return messages
