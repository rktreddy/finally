# Codebase Concerns

**Analysis Date:** 2026-03-21

---

## Overview

The `main` / `finally-gsd` branch contains only the market data subsystem (`backend/app/market/`). The rest of the platform (database layer, API routes, LLM integration, frontend) exists on the `agent-teams` branch and is the reference implementation used throughout this document. Concerns are evaluated against that fuller codebase.

---

## Tech Debt

**`backend/app/db/` / `backend/app/routes/` / `backend/app/llm/` source files missing from current branch:**
- Issue: The `finally-gsd` and `main` branches contain only `__pycache__` directories for `backend/app/db/`, `backend/app/routes/`, and `backend/app/llm/` — the actual `.py` source files are absent. Only the market data module is committed.
- Files: `backend/app/db/`, `backend/app/routes/`, `backend/app/llm/`
- Impact: The backend does not have a working FastAPI app, database layer, or LLM integration on the default branch. Development must reference `agent-teams` branch.
- Fix approach: Merge `agent-teams` into `main` or cherry-pick the relevant commits.

**`frontend/app/lib/` directory missing from `agent-teams`:**
- Issue: Every frontend component imports from `../lib/api`, `../lib/types`, and `../lib/format` (e.g., `ChatPanel.tsx`, `Watchlist.tsx`, `TradeBar.tsx`, `Header.tsx`, `PnLChart.tsx`, `PortfolioHeatmap.tsx`, `PositionsTable.tsx`, `page.tsx`), but `frontend/app/lib/` is not committed to the `agent-teams` branch.
- Files: `frontend/app/components/ChatPanel.tsx`, `frontend/app/components/Watchlist.tsx`, `frontend/app/components/TradeBar.tsx`, `frontend/app/components/Header.tsx`, `frontend/app/components/PnLChart.tsx`, `frontend/app/components/PortfolioHeatmap.tsx`, `frontend/app/components/PositionsTable.tsx`, `frontend/app/page.tsx`
- Impact: The frontend build fails. `npm run build` will error on missing modules `../lib/api`, `../lib/types`, and `../lib/format`.
- Fix approach: Create `frontend/app/lib/api.ts`, `frontend/app/lib/types.ts`, and `frontend/app/lib/format.ts`. The test file `frontend/__tests__/format.test.ts` documents the required exports for `format.ts` (`formatCurrency`, `formatPercent`, `formatQuantity`).

**`backend/pyproject.toml` missing `aiosqlite`, `litellm`, `pydantic` dependencies:**
- Issue: The `pyproject.toml` on the current branch only lists `fastapi`, `uvicorn`, `numpy`, `massive`, `rich`. The `agent-teams` branch adds `aiosqlite>=0.20.0`, `litellm>=1.40.0`, `pydantic>=2.0.0` which are required by the database layer and LLM client.
- Files: `backend/pyproject.toml`
- Impact: `uv sync` on the current branch will not install these packages; the backend will fail to start.
- Fix approach: Add the three missing dependencies to `backend/pyproject.toml`.

**`scripts/` and `db/` directories absent from repository root:**
- Issue: The plan specifies `scripts/start_mac.sh`, `scripts/stop_mac.sh`, `scripts/start_windows.ps1`, `scripts/stop_windows.ps1`, and a `db/` volume-mount directory. Neither exists in the working tree of the current branch (only present in `agent-teams`).
- Files: `scripts/`, `db/`
- Impact: Users cannot run the documented single-command startup flow. The Dockerfile copies `frontend/` and mounts `/app/db` but there is no `db/` directory to mount.
- Fix approach: Add `scripts/` from `agent-teams`; add `db/.gitkeep` at project root.

**`frontend/` directory absent from repository root on `main`/`finally-gsd`:**
- Issue: There is no `frontend/` directory in the working tree. The Dockerfile stage 1 (`FROM node:20-slim AS frontend-build`) copies `frontend/` and runs `npm run build`, which will fail if the directory does not exist.
- Files: Project root `frontend/` (only in `agent-teams`)
- Impact: `docker build` fails; the app cannot be containerized from the current branch.
- Fix approach: Merge `agent-teams` frontend.

---

## Security Considerations

**No API key validation at startup:**
- Risk: If `OPENROUTER_API_KEY` is absent or empty, the backend starts normally but every `/api/chat` call will fail at the LLM client level with an opaque error. There is no early check or warning.
- Files: `backend/app/llm/client.py` (agent-teams), `backend/app/main.py` (agent-teams)
- Current mitigation: `call_llm()` catches all exceptions and re-raises as `ValueError`; the handler degrades to a generic error message.
- Recommendations: Add a startup check that warns if `OPENROUTER_API_KEY` is unset. Log a clear warning rather than silently degrading.

**No dotenv loading in backend:**
- Risk: The `.env` file at the project root is not loaded by the Python backend. `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, and `LLM_MOCK` are only available if passed via `--env-file` to Docker or set as real environment variables. Developers running the backend directly with `uvicorn` outside Docker will not get the `.env` values.
- Files: `backend/app/main.py`, `backend/pyproject.toml`
- Current mitigation: Docker start scripts use `--env-file .env`. Local dev may silently use wrong config.
- Recommendations: Add `python-dotenv` to dependencies and call `load_dotenv()` in `main.py` before app creation, or document the `uv run --env-file ../.env uvicorn ...` pattern explicitly.

**`TradeRequest.side` is untyped string at the API boundary:**
- Risk: The Pydantic model accepts any string for `side` (e.g., `"hold"`, `"short"`). Validation only happens inside `execute_trade()` in the repository, where it raises `ValueError` caught as HTTP 400. This is correct but the error is less clear than a schema validation error.
- Files: `backend/app/routes/portfolio.py` (agent-teams)
- Current mitigation: Repository-level check raises `ValueError("Side must be 'buy' or 'sell'")`.
- Recommendations: Change `side: str` to `side: Literal["buy", "sell"]` in `TradeRequest` for early Pydantic validation and clearer API docs.

---

## Performance Bottlenecks

**New SQLite connection opened per repository function call:**
- Problem: Every function in `backend/app/db/repository.py` calls `await get_connection()` and `await db.close()` — 21 open/close pairs total. Under concurrent request load (SSE plus API calls), this creates repeated connection setup overhead.
- Files: `backend/app/db/repository.py` (agent-teams), `backend/app/db/connection.py` (agent-teams)
- Cause: There is no connection pool or persistent connection object. Each call creates a fresh `aiosqlite.connect()`.
- Improvement path: Maintain a single long-lived connection as app state (FastAPI lifespan) or use a small connection pool. SQLite WAL mode already mitigates read/write contention but the overhead is per-connection setup.

**Portfolio snapshot loop uses `get_portfolio()` which opens a new DB connection every 30 seconds:**
- Problem: The `_snapshot_loop` in `backend/app/main.py` calls `get_portfolio()` then `record_snapshot()` — two separate connection open/close cycles for each snapshot.
- Files: `backend/app/main.py` (agent-teams)
- Cause: Same per-call connection pattern.
- Improvement path: Consolidate into a single connection for the snapshot operation.

---

## Fragile Areas

**DB initialization race condition:**
- Files: `backend/app/db/connection.py` (agent-teams)
- Why fragile: The module-level `_initialized: bool = False` flag is set after the first `get_connection()` call completes initialization. If two async coroutines call `get_connection()` concurrently before initialization completes (possible during FastAPI startup), both could enter `_initialize()`. The `SCHEMA_SQL` uses `CREATE TABLE IF NOT EXISTS` so schema creation is safe, but the seed data check (`SELECT id FROM users_profile`) could race and attempt two `INSERT` statements for the same `DEFAULT_USER_ID`, causing a constraint violation.
- Safe modification: Wrap initialization in an `asyncio.Lock` at module level, or call `get_connection()` once in the lifespan before registering routes. The existing `lifespan` function in `main.py` does call `await get_connection()` before market data starts, which mitigates this in practice — but it is implicit.
- Test coverage: Not explicitly tested for concurrent initialization.

**LLM watchlist changes do not update the in-memory market data source:**
- Files: `backend/app/llm/handler.py` (agent-teams) — `_execute_watchlist_change()`
- Why fragile: When the LLM requests adding/removing a ticker via `watchlist_changes`, `_execute_watchlist_change()` calls `add_ticker()` / `remove_ticker()` on the database only. It does not call `market_data.add_ticker()` / `market_data.remove_ticker()` on `app.state.market_data_source`. Contrast with the REST watchlist route (`backend/app/routes/watchlist.py`) which correctly calls both.
- Impact: After an LLM-initiated watchlist add, the new ticker appears in the watchlist API response but has no live price in the SSE stream and the `PriceCache`. After an LLM-initiated remove, the ticker stays in the price cache and continues to appear in the SSE stream.
- Safe modification: Pass `price_cache` and `market_data_source` into `handle_chat_message()` and call `await market_data.add_ticker()` / `remove_ticker()` inside `_execute_watchlist_change()`.

**`reasoning_effort="low"` parameter in LLM client may not be supported:**
- Files: `backend/app/llm/client.py` (agent-teams)
- Why fragile: The `completion()` call passes `reasoning_effort="low"` to LiteLLM. This parameter is specific to OpenAI's `o1`/`o3` reasoning models. Passing it to `openrouter/openai/gpt-oss-120b` via Cerebras may cause an API error or be silently ignored depending on how OpenRouter forwards parameters.
- Impact: If the parameter causes a 400 error from OpenRouter, every chat message fails.
- Safe modification: Remove `reasoning_effort="low"` unless confirmed supported by the targeted model.

**SSE disconnect detection via `request.is_disconnected()` is polling-based:**
- Files: `backend/app/market/stream.py`
- Why fragile: The `_generate_events` generator checks `await request.is_disconnected()` on every iteration of its 500ms loop. In Uvicorn/ASGI, disconnect detection is not guaranteed to fire immediately — the connection may have been dropped but `is_disconnected()` returns `False` for up to one full polling interval. Under high SSE client counts, this means ghost generators persist briefly.
- Safe modification: This is an acceptable trade-off for a single-user app. For multi-user, switch to WebSockets or use Starlette's `BackgroundTask` with a connection registry.

---

## Missing Critical Features

**No `Dockerfile` or `docker-compose.yml` in working tree (`main`/`finally-gsd`):**
- Problem: The primary user-facing artifact (single Docker command to run the app) does not exist in the current working branch. The `agent-teams` branch has a complete Dockerfile and `docker-compose.yml`.
- Blocks: User onboarding, E2E test infrastructure, deployment.

**No `frontend/app/lib/` module (api client, types, format utilities):**
- Problem: The entire frontend depends on a `lib/` module that is not committed anywhere. Without it, `npm run build` fails.
- Blocks: All frontend functionality, the Docker build.

**E2E test suite has no playwright specs on `main`/`finally-gsd`:**
- Problem: `test/` contains only `node_modules`. The Playwright test files (`test/e2e/*.spec.ts`) are only in `agent-teams`.
- Blocks: CI/CD test validation.

---

## Test Coverage Gaps

**No tests for `backend/app/db/` (repository, connection, schema):**
- What's not tested: Trade execution edge cases across concurrent requests, connection initialization racing, snapshot recording.
- Files: `backend/app/db/connection.py`, `backend/app/db/repository.py` (agent-teams)
- Risk: Incorrect P&L calculations or phantom trades if the average-cost logic has a bug.
- Priority: High

**No tests for `backend/app/routes/` API endpoints on current branch:**
- What's not tested: HTTP response shapes, error codes, request validation failures for all REST endpoints.
- Files: `backend/app/routes/portfolio.py`, `backend/app/routes/watchlist.py`, `backend/app/routes/chat.py` (agent-teams)
- Risk: Breaking API contract changes go undetected.
- Priority: High

**No tests for LLM watchlist sync bug (market data source not updated):**
- What's not tested: The state after an LLM-requested watchlist change — specifically that `PriceCache` and `MarketDataSource` are updated correctly.
- Files: `backend/app/llm/handler.py` (agent-teams)
- Risk: Silent divergence between DB watchlist and in-memory price stream.
- Priority: Medium

**Frontend `lib/` module (api.ts, types.ts) has no unit tests:**
- What's not tested: API fetch wrappers, TypeScript type contracts for all API response shapes.
- Files: `frontend/app/lib/api.ts`, `frontend/app/lib/types.ts` (missing entirely)
- Risk: API contract drift between frontend and backend goes unnoticed until runtime.
- Priority: Medium

---

## Scaling Limits

**Single-user architecture (hardcoded `DEFAULT_USER_ID = "default"`):**
- Current capacity: One user only.
- Limit: All API endpoints, the LLM handler, and the repository default to `user_id="default"`. There is no authentication, session management, or per-user isolation.
- Scaling path: The schema already includes `user_id` on all tables. Add authentication middleware and pass the authenticated user ID through the request context. This is a deliberate design choice for the course demo.

**In-memory `PriceCache` is process-local:**
- Current capacity: Single process.
- Limit: If the app is scaled to multiple processes (e.g., multiple Uvicorn workers), each process has its own `PriceCache` and market data source. SSE streams from different workers will show different prices.
- Scaling path: Replace `PriceCache` with Redis pub/sub or a shared message queue. Currently mitigated by single-worker Docker deployment.

**SQLite WAL concurrent writer limit:**
- Current capacity: One writer at a time (SQLite constraint).
- Limit: Under high trade volume, write operations serialize. Acceptable for a single-user demo; not for multi-user.
- Scaling path: Migrate to PostgreSQL with connection pooling (pgBouncer) for multi-user.

---

## Dependencies at Risk

**`massive` package (Polygon.io wrapper):**
- Risk: The `massive` package is a third-party wrapper around the Polygon.io REST API. It is listed at `>=1.0.0` with no upper bound. API changes or package abandonment could break the `MassiveDataSource` without warning.
- Impact: Real market data unavailable; fallback to simulator is automatic.
- Migration plan: Implement a direct `httpx`-based Polygon.io client if `massive` becomes unmaintained.

**`litellm` pinned to `>=1.40.0` with no upper bound:**
- Risk: LiteLLM has frequent breaking changes in minor versions. The `>=1.40.0` constraint permits upgrading to any future version that may change the `completion()` API, `response_format` behavior, or `extra_body` handling.
- Impact: LLM calls silently break or return unexpected formats.
- Migration plan: Pin to a specific minor version range in `pyproject.toml` (e.g., `litellm>=1.40.0,<2.0.0`).

**Seed prices are stale (originally set circa 2024):**
- Risk: `backend/app/market/seed_prices.py` uses prices like `NVDA: $800`, `META: $500`. As of early 2026, actual prices are significantly different. The simulator starts from these seeds and drifts from there.
- Files: `backend/app/market/seed_prices.py`
- Impact: Demo looks unrealistic to users familiar with current market prices. Not a functional bug.
- Migration plan: Update seed prices annually or load initial prices from a free API call on simulator startup.

---

*Concerns audit: 2026-03-21*
