# Stack Research: AI Trading Workstation

**Research Date:** 2026-03-21
**Focus:** Remaining components (market data already built)

## Existing Stack (Keep As-Is)

- Python 3.12 / FastAPI 0.128.7 / uv / numpy / massive / rich
- pytest + pytest-asyncio + pytest-cov / ruff

## Database Layer

### Recommendation: `aiosqlite` + Python stdlib `sqlite3`

**Confidence:** High

| Library | Version | Purpose |
|---------|---------|---------|
| `aiosqlite` | >=0.20.0 | Async SQLite access — wraps sqlite3 in thread executor |

**Rationale:**
- FastAPI is async; blocking sqlite3 calls would starve the event loop
- `aiosqlite` is thin wrapper, no ORM overhead, direct SQL control
- Single-user app means no write contention — SQLite is perfect
- Schema + seed via raw SQL on startup (lazy init pattern)

**What NOT to use:**
- SQLAlchemy — overkill for single-table CRUD with no relationships; adds complexity
- Tortoise ORM — unnecessary abstraction layer for simple schema
- `databases` package — abandoned/stale maintenance

**Key Pattern:** Use `aiosqlite.connect()` as context manager. Create a single connection factory in app lifespan. WAL mode for concurrent reads during SSE streaming.

## LLM Integration

### Recommendation: `litellm` via OpenRouter with Cerebras

**Confidence:** High

| Library | Version | Purpose |
|---------|---------|---------|
| `litellm` | >=1.40.0 | Unified LLM API — routes to OpenRouter |

**Rationale:**
- LiteLLM provides `response_format` parameter for structured outputs (JSON mode)
- OpenRouter model: `openrouter/openai/gpt-oss-120b` with Cerebras inference
- Structured output via `response_format={"type": "json_object"}` + Pydantic model validation
- Fast inference from Cerebras means no streaming needed — return complete response

**Pattern:**
```python
import litellm
response = litellm.completion(
    model="openrouter/openai/gpt-oss-120b",
    messages=[...],
    response_format={"type": "json_object"},
    api_key=os.environ["OPENROUTER_API_KEY"],
)
```

**Mock Mode:** When `LLM_MOCK=true`, return deterministic JSON responses matching the structured schema. No LiteLLM call.

**What NOT to use:**
- Direct OpenAI SDK — doesn't route to OpenRouter cleanly
- LangChain — massive dependency, unnecessary abstraction for single LLM call
- Raw `httpx` to OpenRouter — reinventing what LiteLLM handles

## Frontend

### Recommendation: Next.js 14+ with TypeScript, static export

**Confidence:** High

| Library | Version | Purpose |
|---------|---------|---------|
| `next` | 14.x or 15.x | React framework with static export |
| `typescript` | 5.x | Type safety |
| `tailwindcss` | 3.x | Utility-first CSS |
| `lightweight-charts` | 4.x | TradingView's canvas charting library |
| `recharts` | 2.x | React charts for P&L line chart |

**Rationale:**
- `output: 'export'` produces static HTML/JS/CSS — served by FastAPI
- No SSR needed; all data comes from API/SSE at runtime
- `lightweight-charts` is purpose-built for financial data — canvas-based, performant, looks professional
- `recharts` for simpler charts (P&L line chart, sparklines)
- Tailwind for rapid dark theme styling

**Heatmap/Treemap:**
- Use `recharts` Treemap component or a lightweight `d3-hierarchy` + custom SVG

**SSE Pattern:**
```typescript
const source = new EventSource('/api/stream/prices');
source.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Update React state
};
```

**What NOT to use:**
- Chart.js — not financial-grade, no candlestick support
- D3 directly — too low-level for this scope
- Socket.io — overkill, SSE is simpler and sufficient
- App Router with server components — static export limits server features; Pages Router or App Router in client-only mode

## Docker

### Recommendation: Multi-stage Dockerfile

**Confidence:** High

```
Stage 1: node:20-slim → build frontend (npm ci && npm run build)
Stage 2: python:3.12-slim → install uv, sync backend, copy frontend build output
```

**Key details:**
- Frontend builds to `frontend/out/` (Next.js static export)
- Copy `out/` contents to a `static/` directory in the Python stage
- FastAPI `StaticFiles` mount serves the frontend
- Single `EXPOSE 8000`
- Volume mount: `-v finally-data:/app/db` for SQLite persistence

## E2E Testing

### Recommendation: Playwright with docker-compose.test.yml

**Confidence:** High

| Library | Version | Purpose |
|---------|---------|---------|
| `@playwright/test` | 1.x | Browser automation and assertions |

**Pattern:**
- `docker-compose.test.yml` spins up app container + Playwright container
- App runs with `LLM_MOCK=true` for deterministic responses
- Tests verify: prices streaming, watchlist CRUD, trade execution, portfolio updates, chat flow
- Use `page.waitForFunction()` to wait for SSE data to arrive

**What NOT to use:**
- Cypress — heavier, less Docker-friendly
- Selenium — outdated patterns
- Testing Library alone — insufficient for full E2E with SSE

---

## Dependency Summary (to add to pyproject.toml)

```toml
# Backend additions
aiosqlite = ">=0.20.0"
litellm = ">=1.40.0"
```

```json
// Frontend package.json (new)
{
  "next": "^14.0.0",
  "react": "^18.0.0",
  "react-dom": "^18.0.0",
  "typescript": "^5.0.0",
  "tailwindcss": "^3.0.0",
  "lightweight-charts": "^4.0.0",
  "recharts": "^2.0.0"
}
```

---
*Stack research: 2026-03-21*
