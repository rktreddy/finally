# Pitfalls Research: AI Trading Workstation

**Research Date:** 2026-03-21
**Focus:** Common mistakes when building remaining components

## 1. SQLite in Async Python

**Pitfall:** Blocking the event loop with synchronous sqlite3 calls.

**Warning Signs:**
- SSE stream stutters or delays when database writes happen
- Trade execution takes >100ms
- `asyncio` warnings about slow callbacks

**Prevention:**
- Use `aiosqlite` which runs sqlite3 in a thread executor
- Enable WAL mode (`PRAGMA journal_mode=WAL`) for concurrent reads during writes
- Keep transactions short — don't hold connections open across awaits

**Phase:** Database layer (Phase 1)

---

## 2. SQLite Concurrent Write Contention

**Pitfall:** Multiple async tasks trying to write simultaneously causes "database is locked" errors.

**Warning Signs:**
- `sqlite3.OperationalError: database is locked`
- Intermittent failures under load

**Prevention:**
- Single writer pattern — serialize writes through one connection or use a write queue
- WAL mode helps but doesn't eliminate write contention
- For this single-user app: a single shared connection with `aiosqlite` is usually sufficient
- Set `timeout` parameter on connection (e.g., 5 seconds) as safety net

**Phase:** Database layer (Phase 1)

---

## 3. Portfolio P&L Precision

**Pitfall:** Floating-point arithmetic causes penny discrepancies in portfolio calculations.

**Warning Signs:**
- Cash balance doesn't add up after multiple trades
- P&L shows -$0.01 on a position that should be flat

**Prevention:**
- Use Python `float` (not Decimal) — this is a simulation, not accounting software
- Round display values to 2 decimal places on the frontend
- Store raw floats in database; format on output
- Don't try to make cash_balance + sum(positions) exactly equal starting balance — floating point drift is acceptable for a demo

**Phase:** Trade execution (Phase 2)

---

## 4. LiteLLM Structured Output Parsing Failures

**Pitfall:** LLM returns malformed JSON despite `response_format={"type": "json_object"}`.

**Warning Signs:**
- `json.JSONDecodeError` on response parsing
- Missing required fields in structured output
- LLM returns markdown-wrapped JSON (```json ... ```)

**Prevention:**
- Always wrap parse in try/except — return a fallback text response on failure
- Use Pydantic model with `model_validate_json()` for strict parsing
- System prompt must explicitly state "respond with valid JSON only"
- Include the exact schema in the system prompt
- If parsing fails, return `{"message": "I had trouble processing that. Could you rephrase?", "trades": [], "watchlist_changes": []}`

**Phase:** LLM integration (Phase 3)

---

## 5. LLM Context Window Overflow

**Pitfall:** Chat history grows until it exceeds the LLM's context window.

**Warning Signs:**
- LLM responses become truncated or confused
- API returns context length errors

**Prevention:**
- Limit chat history to last N messages (e.g., 20)
- Always include the most recent portfolio context (it changes with every trade)
- System prompt + portfolio context + recent history should fit well within limits
- Cerebras models via OpenRouter have generous context but still finite

**Phase:** LLM integration (Phase 3)

---

## 6. SSE EventSource Reconnection

**Pitfall:** Browser EventSource auto-reconnects but the app doesn't handle the gap gracefully.

**Warning Signs:**
- Prices freeze for a few seconds then jump
- Sparklines show gaps or sudden jumps
- UI shows "connected" but prices aren't updating

**Prevention:**
- Track connection state in React (`connecting`, `open`, `error`)
- Show visual indicator (colored dot in header)
- On reconnect, prices resume from cache — no historical replay needed
- EventSource has built-in retry with `retry:` field in SSE protocol
- Frontend should clear stale price data on reconnect (or just let it catch up)

**Phase:** Frontend (Phase 4)

---

## 7. Next.js Static Export Limitations

**Pitfall:** Using Next.js features that don't work with `output: 'export'`.

**Warning Signs:**
- Build fails with "export doesn't support..."
- Dynamic routes don't work
- API routes in Next.js (they won't exist — API is FastAPI)

**Prevention:**
- No `getServerSideProps` — use `useEffect` + fetch for all data
- No Next.js API routes (`pages/api/`) — all API is FastAPI backend
- No `next/image` optimization (no server) — use regular `<img>` or import images
- No middleware — all routing is client-side
- All pages must be statically exportable
- Use App Router with `'use client'` directive on all components, or Pages Router

**Phase:** Frontend (Phase 4)

---

## 8. Price Flash Animation Performance

**Pitfall:** Applying CSS class on every price update causes layout thrashing.

**Warning Signs:**
- UI becomes janky with 10 tickers updating every 500ms
- Browser DevTools shows excessive paint/layout events

**Prevention:**
- Use CSS transitions, not JavaScript animations
- Apply class briefly then remove (requestAnimationFrame or setTimeout)
- Only flash when price actually changed (compare with previous)
- Use `will-change: background-color` CSS hint
- Batch state updates (React 18 automatic batching helps)

**Phase:** Frontend (Phase 4)

---

## 9. Sparkline Memory Growth

**Pitfall:** Accumulating price data indefinitely for sparklines causes memory growth.

**Warning Signs:**
- Browser memory usage grows steadily over time
- Tab becomes sluggish after running for 30+ minutes

**Prevention:**
- Cap sparkline data to last N points (e.g., 100-200 points)
- Use a ring buffer or array with shift/push
- Each ticker gets its own buffer — 10 tickers × 200 points × 8 bytes = ~16KB (negligible)

**Phase:** Frontend (Phase 4)

---

## 10. Docker Multi-Stage Build Cache Invalidation

**Pitfall:** Changing one backend file triggers full frontend rebuild (or vice versa).

**Warning Signs:**
- Docker builds take 2+ minutes for tiny changes
- `npm install` runs even when package.json didn't change

**Prevention:**
- Copy `package.json` + `package-lock.json` first, run `npm ci`, THEN copy source
- Same pattern: copy `pyproject.toml` + `uv.lock` first, run `uv sync`, THEN copy backend source
- Order COPY statements from least-changed to most-changed
- Use `.dockerignore` to exclude `node_modules/`, `.venv/`, `db/`, `.planning/`

**Phase:** Docker (Phase 5)

---

## 11. Playwright SSE Testing Timing

**Pitfall:** E2E tests are flaky because SSE data arrives at unpredictable times.

**Warning Signs:**
- Tests pass locally, fail in CI
- `expect(price).toBe(...)` fails intermittently

**Prevention:**
- Never assert exact price values — assert that prices exist and update
- Use `page.waitForFunction(() => document.querySelector('.price').textContent !== '$0.00')`
- Set generous timeouts (SSE data arrives within 500ms-2s)
- Test structural assertions: "watchlist has 10 rows" not "AAPL is $191.23"
- Use `LLM_MOCK=true` for deterministic chat responses

**Phase:** E2E Tests (Phase 5)

---

## 12. FastAPI Static File Serving Order

**Pitfall:** Static file mount catches API routes or vice versa.

**Warning Signs:**
- `/api/health` returns HTML instead of JSON
- Frontend routes return 404

**Prevention:**
- Mount API routers FIRST with `/api` prefix
- Mount static files LAST as catch-all on `/`
- Use `StaticFiles(directory="static", html=True)` for SPA — serves `index.html` for all non-file paths
- Test: `curl localhost:8000/api/health` returns JSON, `curl localhost:8000/` returns HTML

**Phase:** App entry point (Phase 1)

---

## Summary: Top 5 Risks

| Rank | Pitfall | Impact | Likelihood |
|------|---------|--------|------------|
| 1 | LLM structured output parsing | Chat breaks entirely | Medium |
| 2 | SQLite async blocking | SSE stutters, poor UX | Medium |
| 3 | Next.js static export limitations | Build failures | Low (well-documented) |
| 4 | Playwright SSE flakiness | CI failures | High |
| 5 | Static file mount order | Routing breaks | Low (easy to fix) |

---
*Pitfalls research: 2026-03-21*
