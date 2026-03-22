# Phase 3: LLM Chat Integration - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can chat with an AI assistant that understands their portfolio and can autonomously execute trades and manage the watchlist through natural language. This phase delivers the POST /api/chat endpoint, LLM client (LiteLLM via OpenRouter with Cerebras inference), structured output parsing, auto-execution of trades and watchlist changes, chat history persistence, and a mock mode for testing. No frontend — pure backend API.

</domain>

<decisions>
## Implementation Decisions

### LLM Client
- **D-01:** Use LiteLLM to call OpenRouter with the model `openrouter/openai/gpt-oss-120b` and Cerebras as the inference provider. Follow the cerebras-inference skill pattern from CLAUDE.md.
- **D-02:** No token-by-token streaming — return the complete response as JSON. Cerebras inference is fast enough that a loading indicator on the frontend is sufficient (per PLAN.md §9).
- **D-03:** The LLM client lives in `backend/app/llm/` directory. Main module: `client.py` for the LiteLLM call, `prompts.py` for system prompt and context assembly, `mock.py` for mock responses, `models.py` for Pydantic output models.
- **D-04:** OPENROUTER_API_KEY read from environment (already in .env). If missing and LLM_MOCK is not true, the chat endpoint returns 503 "LLM not configured".

### Structured Output
- **D-05:** The LLM is instructed to respond with JSON matching this schema: `{"message": str, "trades": [{"ticker": str, "side": str, "quantity": float}], "watchlist_changes": [{"ticker": str, "action": str}]}`. The `trades` and `watchlist_changes` arrays are optional (can be empty or absent).
- **D-06:** Use Pydantic models to validate the structured output. If parsing fails, return the raw LLM text as the message with no actions.
- **D-07:** Pydantic models: `ChatResponse(message, trades, watchlist_changes)`, `TradeAction(ticker, side, quantity)`, `WatchlistAction(ticker, action)`.

### Context Assembly
- **D-08:** System prompt instructs the LLM as "FinAlly, an AI trading assistant" with guidance to analyze portfolio, suggest trades, execute when asked, manage watchlist, be concise and data-driven, always respond with valid JSON.
- **D-09:** Portfolio context includes: current cash balance, all positions with current prices and P&L, watchlist with live prices, total portfolio value. Assembled fresh on each request from DB + PriceCache.
- **D-10:** Recent conversation history loaded from chat_messages table — last 20 messages (10 user + 10 assistant pairs). Included as conversation history in the LLM call.
- **D-11:** Messages sent to LLM as: [system_prompt, ...history_messages, user_message]. The system prompt includes the portfolio context as structured data.

### Auto-Execution
- **D-12:** After receiving the LLM response, auto-execute any trades using the same trade logic as POST /api/portfolio/trade (reuse the existing trade execution function from portfolio.py or repository functions).
- **D-13:** Auto-execute watchlist changes using the same logic as POST/DELETE /api/watchlist (add_ticker/remove_ticker on source, DB persist).
- **D-14:** If a trade fails validation (insufficient cash, insufficient shares, no price), capture the error message — do NOT fail the entire chat request. Include the error in the response's `actions` field.
- **D-15:** All auto-executed actions (successful trades, failed trades, watchlist changes) are stored in the `actions` JSON column of the chat_messages table for the assistant's message.

### Chat Persistence
- **D-16:** Both user messages and assistant messages are stored in the chat_messages table with role="user" or role="assistant".
- **D-17:** User message stored BEFORE the LLM call. Assistant message stored AFTER the LLM response is received and actions are executed.
- **D-18:** The `actions` column stores a JSON object with `{"trades": [...], "watchlist_changes": [...], "errors": [...]}` for assistant messages. Null for user messages.

### Mock Mode
- **D-19:** When `LLM_MOCK=true` environment variable is set, skip the LiteLLM call entirely and return deterministic mock responses.
- **D-20:** Mock responses should vary based on the user's message content — at minimum handle: "buy" triggers a mock buy trade, "sell" triggers a mock sell trade, "add" triggers a mock watchlist add, and a default analytical response for other messages.
- **D-21:** Mock mode uses the same auto-execution path — mock responses go through the same trade/watchlist execution logic as real responses. This tests the full pipeline.

### API Response Shape
- **D-22:** POST /api/chat request body: `{"message": str}`.
- **D-23:** POST /api/chat response: `{"message": str, "actions": {"trades": [{"ticker": str, "side": str, "quantity": float, "price": float, "status": "executed"|"failed", "error": str|null}], "watchlist_changes": [{"ticker": str, "action": "add"|"remove", "status": "executed"|"failed"}]}}`.

### Code Organization
- **D-24:** Chat route in `backend/app/routes/chat.py`, LLM logic in `backend/app/llm/`.
- **D-25:** Repository functions for chat messages added to `backend/app/db/repository.py`: `insert_chat_message(db, role, content, actions=None)` and `get_chat_history(db, limit=20)`.

### Claude's Discretion
- Exact system prompt wording
- How to structure the portfolio context string within the system prompt
- LiteLLM client configuration details (timeout, retries)
- Exact mock response content for different message patterns
- Error handling for LLM API failures (timeouts, rate limits)

</decisions>

<specifics>
## Specific Ideas

- The LLM should feel like a knowledgeable trading assistant — concise, data-driven, no unnecessary disclaimers
- Auto-execution creates an impressive, fluid demo experience — the AI doesn't just talk, it acts
- Mock mode is critical for E2E tests in Phase 5 — must be fully deterministic

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### LLM Integration Spec
- `planning/PLAN.md` §9 — LLM integration: how it works, structured output schema, auto-execution, system prompt guidance, mock mode
- `planning/PLAN.md` §5 — Environment variables: OPENROUTER_API_KEY, LLM_MOCK

### API Specification
- `planning/PLAN.md` §8 — POST /api/chat endpoint definition

### Database Schema
- `planning/PLAN.md` §7 — chat_messages table schema (id, user_id, role, content, actions, created_at)
- `backend/app/db/schema.sql` — Actual SQL for chat_messages table

### Prior Phase Integration
- `.planning/phases/02-watchlist-trading-api/02-CONTEXT.md` — Trade execution decisions (D-01 through D-06) that must be reused for auto-execution
- `backend/app/routes/portfolio.py` — Trade execution logic to reuse
- `backend/app/routes/watchlist.py` — Watchlist add/remove logic to reuse
- `backend/app/db/repository.py` — Existing repository functions

### LLM Skill
- Use the cerebras-inference skill pattern for LiteLLM calls via OpenRouter

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/routes/portfolio.py` — Trade execution logic (buy/sell with validation) in `execute_trade` endpoint; `record_snapshot` helper for post-trade snapshots
- `backend/app/routes/watchlist.py` — Watchlist add/remove with DB persist and source sync
- `backend/app/db/repository.py` — All DB functions (get_user_cash, get_positions, get_watchlist_tickers, insert_trade, etc.)
- `backend/app/market/cache.py` — PriceCache for live price lookups
- `backend/app/db/schema.sql` — chat_messages table already defined

### Established Patterns
- Routes access shared state via `request.app.state.db`, `.cache`, `.source`
- Pydantic models for request/response validation in route modules
- Repository functions for all SQL; transaction-aware commit design
- Module-level `logger = logging.getLogger(__name__)`
- `from __future__ import annotations` in every module
- Background tasks started in lifespan, cancelled on shutdown

### Integration Points
- Chat route needs `app.state.db` (chat history, portfolio context), `app.state.cache` (live prices for context), `app.state.source` (watchlist add/remove)
- Trade auto-execution should reuse repository functions directly (not call HTTP endpoints internally)
- Watchlist auto-execution should reuse repository + source.add_ticker/remove_ticker
- Chat router registered in `main.py` with `/api` prefix

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-llm-chat-integration*
*Context gathered: 2026-03-22*
