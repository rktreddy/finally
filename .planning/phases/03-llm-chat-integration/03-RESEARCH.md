# Phase 3: LLM Chat Integration - Research

**Researched:** 2026-03-22
**Domain:** LLM integration (LiteLLM, OpenRouter, Cerebras inference, structured outputs)
**Confidence:** HIGH

## Summary

Phase 3 adds an AI chat assistant to the FinAlly backend. The user sends messages via POST /api/chat, and the backend assembles portfolio context, calls an LLM via LiteLLM through OpenRouter (Cerebras inference provider), parses the structured JSON response, auto-executes any trades or watchlist changes, persists the conversation, and returns the result. A mock mode (LLM_MOCK=true) provides deterministic responses for testing.

The existing codebase provides all the building blocks: trade execution logic in `portfolio.py`, watchlist management in `watchlist.py`, repository functions in `repository.py`, and the `chat_messages` table already defined in `schema.sql`. The primary new work is the LLM client module (`backend/app/llm/`), chat repository functions, the chat route, and wiring it into `main.py`.

**Primary recommendation:** Use LiteLLM's `acompletion` (async) with `response_format=ChatResponse` (Pydantic model) for structured outputs. Reuse existing repository functions directly for auto-execution (not HTTP calls). Keep the LLM client thin and testable by extracting it behind a simple async function interface.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use LiteLLM to call OpenRouter with the model `openrouter/openai/gpt-oss-120b` and Cerebras as the inference provider. Follow the cerebras-inference skill pattern from CLAUDE.md.
- **D-02:** No token-by-token streaming -- return the complete response as JSON. Cerebras inference is fast enough that a loading indicator on the frontend is sufficient.
- **D-03:** The LLM client lives in `backend/app/llm/` directory. Main module: `client.py` for the LiteLLM call, `prompts.py` for system prompt and context assembly, `mock.py` for mock responses, `models.py` for Pydantic output models.
- **D-04:** OPENROUTER_API_KEY read from environment. If missing and LLM_MOCK is not true, the chat endpoint returns 503 "LLM not configured".
- **D-05:** Structured JSON schema: `{"message": str, "trades": [...], "watchlist_changes": [...]}`.
- **D-06:** Use Pydantic models to validate the structured output. If parsing fails, return the raw LLM text as the message with no actions.
- **D-07:** Pydantic models: `ChatResponse(message, trades, watchlist_changes)`, `TradeAction(ticker, side, quantity)`, `WatchlistAction(ticker, action)`.
- **D-08:** System prompt instructs the LLM as "FinAlly, an AI trading assistant".
- **D-09:** Portfolio context includes: current cash balance, all positions with current prices and P&L, watchlist with live prices, total portfolio value.
- **D-10:** Last 20 messages from chat_messages table included as conversation history.
- **D-11:** Messages sent as: [system_prompt, ...history_messages, user_message].
- **D-12:** Auto-execute trades using existing repository functions directly (not HTTP endpoints).
- **D-13:** Auto-execute watchlist changes using repository + source.add_ticker/remove_ticker.
- **D-14:** Failed trade validations captured as error messages, not exceptions. Do NOT fail the entire chat request.
- **D-15:** All auto-executed actions stored in the `actions` JSON column of chat_messages.
- **D-16:** Both user and assistant messages stored in chat_messages table.
- **D-17:** User message stored BEFORE the LLM call. Assistant message stored AFTER response + execution.
- **D-18:** Actions column: `{"trades": [...], "watchlist_changes": [...], "errors": [...]}`. Null for user messages.
- **D-19:** LLM_MOCK=true skips LiteLLM call, returns deterministic mock responses.
- **D-20:** Mock responses vary by message content: "buy" -> mock buy, "sell" -> mock sell, "add" -> mock watchlist add, default -> analytical response.
- **D-21:** Mock mode uses same auto-execution path as real responses.
- **D-22:** POST /api/chat request body: `{"message": str}`.
- **D-23:** POST /api/chat response shape with actions containing status and error fields.
- **D-24:** Chat route in `backend/app/routes/chat.py`, LLM logic in `backend/app/llm/`.
- **D-25:** Repository functions: `insert_chat_message(db, role, content, actions=None)` and `get_chat_history(db, limit=20)`.

### Claude's Discretion
- Exact system prompt wording
- How to structure the portfolio context string within the system prompt
- LiteLLM client configuration details (timeout, retries)
- Exact mock response content for different message patterns
- Error handling for LLM API failures (timeouts, rate limits)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LLM-01 | User can send chat message and receive AI response via POST /api/chat | Chat route (D-22, D-23, D-24); LiteLLM acompletion with structured output |
| LLM-02 | AI response includes portfolio-aware analysis (cash, positions, P&L, watchlist with prices) | Context assembly in prompts.py (D-08, D-09, D-11); existing repository functions for portfolio data |
| LLM-03 | AI can execute trades via structured output (auto-executed, no confirmation) | Structured output models (D-05, D-06, D-07); auto-execution reusing repository functions (D-12, D-14) |
| LLM-04 | AI can add/remove watchlist tickers via structured output | WatchlistAction model (D-07); auto-execution via repository + source (D-13) |
| LLM-05 | Failed trade validations included in chat response so AI can inform user | Error capture pattern (D-14, D-18); actions JSON with errors array |
| LLM-06 | Chat message history persisted to database | chat_messages table exists in schema.sql; repository functions (D-25); storage order (D-16, D-17) |
| LLM-07 | LLM_MOCK=true returns deterministic mock responses (for testing) | Mock module (D-19, D-20, D-21); same execution pipeline |
| LLM-08 | LLM uses LiteLLM -> OpenRouter with Cerebras inference | cerebras-inference skill pattern; LiteLLM 1.82.4 installed; acompletion async API verified |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| litellm | 1.82.4 (installed, latest: 1.82.6) | LLM API client | Project requirement; supports OpenRouter + Cerebras + structured outputs |
| pydantic | 2.12.5 (already installed via FastAPI) | Structured output models, request/response validation | Already in stack; LiteLLM accepts Pydantic models for response_format |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | 1.2.1 (already installed) | Load OPENROUTER_API_KEY from .env | Already used by the project |

### No New Dependencies Needed
LiteLLM is already installed in the virtualenv but **must be added to pyproject.toml** via `uv add litellm`. Pydantic and python-dotenv are already declared dependencies.

**Installation:**
```bash
cd backend && uv add litellm
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/llm/
  __init__.py       # Public API: __all__ re-exports
  models.py         # Pydantic models: ChatResponse, TradeAction, WatchlistAction
  client.py         # LLM client: call_llm(messages) -> ChatResponse
  prompts.py        # System prompt builder, portfolio context assembly
  mock.py           # Mock response generator for LLM_MOCK=true

backend/app/routes/
  chat.py           # POST /api/chat route + auto-execution orchestration

backend/app/db/
  repository.py     # Add: insert_chat_message(), get_chat_history()
```

### Pattern 1: Thin LLM Client with Async Call
**What:** A single async function that takes messages, calls LiteLLM, and returns a parsed Pydantic model. No business logic in the client itself.
**When to use:** Always -- keeps LLM call testable and mockable.
**Example:**
```python
# backend/app/llm/client.py
from litellm import acompletion
from .models import ChatResponse

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}

async def call_llm(messages: list[dict]) -> ChatResponse:
    """Call LLM via LiteLLM and return parsed structured response."""
    response = await acompletion(
        model=MODEL,
        messages=messages,
        response_format=ChatResponse,
        reasoning_effort="low",
        extra_body=EXTRA_BODY,
        timeout=30,
    )
    content = response.choices[0].message.content
    return ChatResponse.model_validate_json(content)
```

### Pattern 2: Context Assembly as Pure Function
**What:** Build the system prompt with embedded portfolio data as a pure function that takes DB/cache data and returns a string.
**When to use:** Always -- makes the prompt testable without any I/O.
**Example:**
```python
# backend/app/llm/prompts.py
def build_system_prompt(cash: float, positions: list[dict], watchlist: list[dict],
                        total_value: float) -> str:
    """Build system prompt with portfolio context."""
    # ... format portfolio data into structured text ...
    return system_prompt_text
```

### Pattern 3: Auto-Execution with Error Capture
**What:** Execute trades/watchlist changes from LLM response, capturing errors per-action rather than failing the whole request.
**When to use:** After receiving LLM (or mock) response, before storing assistant message.
**Example:**
```python
# In chat route or a helper function
async def execute_actions(response: ChatResponse, db, cache, source) -> dict:
    """Execute trades and watchlist changes, return actions summary with status."""
    results = {"trades": [], "watchlist_changes": [], "errors": []}
    for trade in response.trades or []:
        try:
            # Reuse the same validation + execution logic from portfolio.py
            # ... validate cash/shares, update position, record trade ...
            results["trades"].append({...trade details..., "status": "executed"})
        except Exception as e:
            results["trades"].append({...trade details..., "status": "failed", "error": str(e)})
            results["errors"].append(str(e))
    # Similar for watchlist_changes
    return results
```

### Pattern 4: Mock Mode via Environment Variable
**What:** Check `LLM_MOCK` env var early in the chat route to decide between real LLM call and mock response.
**When to use:** Controls the code path in chat route.
**Example:**
```python
import os
if os.environ.get("LLM_MOCK", "").lower() == "true":
    chat_response = generate_mock_response(user_message)
else:
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise HTTPException(status_code=503, detail="LLM not configured")
    chat_response = await call_llm(messages)
```

### Anti-Patterns to Avoid
- **Calling HTTP endpoints internally for auto-execution:** Do NOT call POST /api/portfolio/trade from the chat route. Reuse the repository functions directly. HTTP self-calls add latency, error handling complexity, and circular dependency risk.
- **Putting business logic in the LLM client:** The client should only call the LLM and parse the response. Trade execution, context assembly, and persistence belong in the route or helper functions.
- **Raising exceptions on trade failures during auto-execution:** Trade failures should be captured and reported, not raised. The chat response must always succeed even if individual trades fail.
- **Storing chat messages with db.commit() inside repository functions for trade-related operations:** Trade auto-execution involves multiple DB writes (cash, position, trade record) that must be atomic. Chat message storage (standalone) should commit, but trade execution should follow the existing transaction-aware pattern (caller commits).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM API calls | Custom HTTP client for OpenRouter | LiteLLM `acompletion` | Handles auth, retries, provider routing, structured output conversion |
| JSON schema enforcement | Manual JSON parsing + validation | Pydantic `response_format` + `model_validate_json` | Type-safe, handles optional fields, validation errors |
| Trade execution logic | New trade execution code | Existing repository functions from Phase 2 | Already tested, handles edge cases (cash validation, position upsert) |
| Watchlist management | New watchlist code | Existing repository + source.add_ticker/remove_ticker | Already tested, handles DB + market data source sync |

## Common Pitfalls

### Pitfall 1: LiteLLM Not in pyproject.toml
**What goes wrong:** LiteLLM is installed in the virtualenv but not declared in `pyproject.toml`. Docker builds will fail.
**Why it happens:** Someone ran `uv pip install litellm` instead of `uv add litellm`.
**How to avoid:** Run `uv add litellm` to add it to pyproject.toml and update uv.lock.
**Warning signs:** `uv sync` in a fresh environment or Docker build fails to install litellm.

### Pitfall 2: Structured Output Parsing Failures
**What goes wrong:** The LLM returns invalid JSON or JSON that doesn't match the Pydantic schema, causing a crash.
**Why it happens:** LLMs occasionally produce malformed output, especially with complex schemas.
**How to avoid:** Wrap `ChatResponse.model_validate_json(content)` in a try/except. On failure, return a ChatResponse with the raw text as the message and empty action arrays (per D-06).
**Warning signs:** Unhandled `ValidationError` in logs.

### Pitfall 3: Forgetting to Commit After Trade Auto-Execution
**What goes wrong:** Trades appear to execute but are rolled back because no commit was issued.
**Why it happens:** The existing repository functions for trades (update_cash_balance, upsert_position, insert_trade) do NOT commit -- they expect the caller to commit.
**How to avoid:** After all trade operations for a single trade, call `await db.commit()`. Follow the same pattern as `execute_trade` in portfolio.py.
**Warning signs:** Trades disappear on page refresh.

### Pitfall 4: Chat History Growing Without Bound
**What goes wrong:** Including all chat history in the LLM prompt causes token limit issues.
**Why it happens:** No limit on the number of messages loaded.
**How to avoid:** Limit to last 20 messages (D-10). The `get_chat_history` repository function should have a `LIMIT` clause.
**Warning signs:** LLM API errors about exceeding context length.

### Pitfall 5: Mock Mode Not Testing Full Pipeline
**What goes wrong:** Mock mode returns responses without going through auto-execution, so mock tests don't cover the trade/watchlist execution path.
**Why it happens:** Taking a shortcut by returning the final response directly from mock.
**How to avoid:** Mock mode generates a `ChatResponse` object that goes through the same auto-execution pipeline as real responses (D-21).
**Warning signs:** E2E tests with LLM_MOCK=true pass but real LLM calls fail on execution.

### Pitfall 6: Synchronous LiteLLM Call Blocking the Event Loop
**What goes wrong:** Using `completion()` (sync) instead of `acompletion()` (async) blocks the FastAPI event loop during the LLM call.
**Why it happens:** The cerebras-inference skill examples show synchronous `completion()`.
**How to avoid:** Use `acompletion()` which has the same signature but returns an awaitable. Verified: `acompletion` supports `response_format`, `reasoning_effort`, and `**kwargs` (for `extra_body`).
**Warning signs:** All SSE streams and other requests freeze during LLM calls.

## Code Examples

### Pydantic Structured Output Models
```python
# backend/app/llm/models.py
from __future__ import annotations
from pydantic import BaseModel, Field

class TradeAction(BaseModel):
    """A trade the AI wants to execute."""
    ticker: str
    side: str  # "buy" or "sell"
    quantity: float

class WatchlistAction(BaseModel):
    """A watchlist change the AI wants to make."""
    ticker: str
    action: str  # "add" or "remove"

class ChatResponse(BaseModel):
    """Structured response from the LLM."""
    message: str
    trades: list[TradeAction] = Field(default_factory=list)
    watchlist_changes: list[WatchlistAction] = Field(default_factory=list)
```

### Async LiteLLM Call (cerebras-inference skill pattern, adapted for async)
```python
# backend/app/llm/client.py
from litellm import acompletion
from .models import ChatResponse

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}

async def call_llm(messages: list[dict]) -> ChatResponse:
    response = await acompletion(
        model=MODEL,
        messages=messages,
        response_format=ChatResponse,
        reasoning_effort="low",
        extra_body=EXTRA_BODY,
        timeout=30,
    )
    content = response.choices[0].message.content
    return ChatResponse.model_validate_json(content)
```

### Chat Repository Functions
```python
# Added to backend/app/db/repository.py
async def insert_chat_message(
    db: aiosqlite.Connection,
    role: str,
    content: str,
    actions: str | None = None,
    user_id: str = "default",
) -> dict:
    msg_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO chat_messages (id, user_id, role, content, actions) VALUES (?, ?, ?, ?, ?)",
        (msg_id, user_id, role, content, actions),
    )
    await db.commit()
    async with db.execute(
        "SELECT id, role, content, actions, created_at FROM chat_messages WHERE id = ?",
        (msg_id,),
    ) as cursor:
        row = await cursor.fetchone()
        return dict(row)

async def get_chat_history(
    db: aiosqlite.Connection, user_id: str = "default", limit: int = 20
) -> list[dict]:
    async with db.execute(
        "SELECT role, content, actions, created_at FROM chat_messages "
        "WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    ) as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in reversed(rows)]  # Chronological order
```

### Mock Response Generator
```python
# backend/app/llm/mock.py
from .models import ChatResponse, TradeAction, WatchlistAction

def generate_mock_response(user_message: str) -> ChatResponse:
    msg_lower = user_message.lower()
    if "buy" in msg_lower:
        return ChatResponse(
            message="I've placed a buy order for 10 shares of AAPL.",
            trades=[TradeAction(ticker="AAPL", side="buy", quantity=10)],
        )
    elif "sell" in msg_lower:
        return ChatResponse(
            message="I've placed a sell order for 5 shares of AAPL.",
            trades=[TradeAction(ticker="AAPL", side="sell", quantity=5)],
        )
    elif "add" in msg_lower:
        return ChatResponse(
            message="I've added PYPL to your watchlist.",
            watchlist_changes=[WatchlistAction(ticker="PYPL", action="add")],
        )
    else:
        return ChatResponse(
            message="Your portfolio is well-diversified across tech and finance sectors. "
            "Your total value reflects current market conditions.",
        )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual JSON schema in prompt | `response_format` with Pydantic model | LiteLLM 1.40+ (2024) | Reliable structured output; no manual JSON parsing |
| Sync `completion()` | Async `acompletion()` | LiteLLM 1.0+ | Non-blocking in async frameworks |
| `openai` client directly | LiteLLM as unified interface | Project decision | Supports OpenRouter + Cerebras routing with minimal code |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio |
| Config file | `backend/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd backend && uv run --extra dev pytest tests/test_chat.py -x -v` |
| Full suite command | `cd backend && uv run --extra dev pytest -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LLM-01 | POST /api/chat returns AI response | integration | `cd backend && uv run --extra dev pytest tests/test_chat.py::test_chat_basic -x` | Wave 0 |
| LLM-02 | Response demonstrates portfolio awareness | integration | `cd backend && uv run --extra dev pytest tests/test_chat.py::test_chat_portfolio_context -x` | Wave 0 |
| LLM-03 | AI trades auto-executed via structured output | integration | `cd backend && uv run --extra dev pytest tests/test_chat.py::test_chat_buy_trade -x` | Wave 0 |
| LLM-04 | AI watchlist changes auto-executed | integration | `cd backend && uv run --extra dev pytest tests/test_chat.py::test_chat_watchlist_add -x` | Wave 0 |
| LLM-05 | Failed trades included in response | integration | `cd backend && uv run --extra dev pytest tests/test_chat.py::test_chat_trade_failure -x` | Wave 0 |
| LLM-06 | Chat history persisted to DB | integration | `cd backend && uv run --extra dev pytest tests/test_chat.py::test_chat_history_persisted -x` | Wave 0 |
| LLM-07 | LLM_MOCK=true returns deterministic responses | integration | `cd backend && uv run --extra dev pytest tests/test_chat.py::test_mock_mode -x` | Wave 0 |
| LLM-08 | LiteLLM -> OpenRouter with Cerebras | unit | `cd backend && uv run --extra dev pytest tests/test_llm_client.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && uv run --extra dev pytest tests/test_chat.py -x -v`
- **Per wave merge:** `cd backend && uv run --extra dev pytest -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_chat.py` -- integration tests for chat endpoint (all tests use LLM_MOCK=true)
- [ ] `tests/test_llm_client.py` -- unit tests for LLM client module (mock the acompletion call)

## Open Questions

1. **LiteLLM timeout and retry behavior with Cerebras**
   - What we know: LiteLLM supports `timeout` parameter; Cerebras is fast (sub-second inference)
   - What's unclear: Optimal timeout value; whether LiteLLM auto-retries on 429/5xx from OpenRouter
   - Recommendation: Set timeout=30s, add explicit try/except for API errors with a user-friendly message. LiteLLM has built-in retry logic (num_retries parameter) -- use `num_retries=1` for a single retry.

2. **Portfolio context token budget**
   - What we know: System prompt + portfolio context + 20 messages of history could be large
   - What's unclear: Exact token limits for gpt-oss-120b via Cerebras on OpenRouter
   - Recommendation: Keep portfolio context concise (summary format, not raw JSON). If 10 positions + 10 watchlist tickers + 20 messages, this should be well under typical context limits.

## Sources

### Primary (HIGH confidence)
- cerebras-inference skill (`/.claude/skills/cerebras/SKILL.md`) -- LiteLLM + OpenRouter + Cerebras pattern
- LiteLLM structured output docs (https://docs.litellm.ai/docs/completion/json_mode) -- Pydantic response_format usage
- Existing codebase: `backend/app/routes/portfolio.py`, `watchlist.py`, `db/repository.py`, `db/schema.sql`, `main.py`
- LiteLLM version 1.82.4 verified installed; `acompletion` async API verified with `response_format`, `reasoning_effort`, and `**kwargs` support

### Secondary (MEDIUM confidence)
- LiteLLM GitHub issues on structured output reliability -- suggests using Pydantic models directly is generally reliable for OpenAI-compatible providers

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- LiteLLM already installed, cerebras skill provides exact pattern, async API verified
- Architecture: HIGH -- follows established project patterns (routes + repository + module organization)
- Pitfalls: HIGH -- derived from direct code inspection and verified API behavior

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (LiteLLM updates frequently but core API is stable)
