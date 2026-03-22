# Phase 1: Foundation - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

The FastAPI application starts cleanly, initializes a SQLite database with schema and seed data, wires up the existing market data subsystem (PriceCache, SimulatorDataSource, SSE streaming), serves static files at the root, and responds to health checks. This phase delivers a running backend that downstream phases (API routes, LLM, frontend) build on.

</domain>

<decisions>
## Implementation Decisions

### Database Connection Strategy
- **D-01:** Use a single shared `aiosqlite` connection created at app startup, stored in `app.state.db`
- **D-02:** Enable WAL mode (`PRAGMA journal_mode=WAL`) on connection open for concurrent reads during SSE streaming
- **D-03:** Connection opened in lifespan startup, closed in lifespan shutdown
- **D-04:** All repository functions receive the db connection as a parameter (dependency injection, not global)

### Schema Initialization
- **D-05:** Schema defined in `backend/app/db/schema.sql` as a raw SQL file — readable, auditable, source of truth
- **D-06:** Python function `init_db()` reads the SQL file and executes it; checks if tables exist first (lazy init)
- **D-07:** Seed data (default user profile + 10 watchlist tickers) applied in the same init function, only if data doesn't exist
- **D-08:** No migration framework — lazy init only. Tables created with `CREATE TABLE IF NOT EXISTS`

### App State Sharing
- **D-09:** PriceCache, MarketDataSource, and DB connection stored on `app.state` during lifespan startup
- **D-10:** FastAPI routes access shared state via `request.app.state` (standard FastAPI pattern)
- **D-11:** Background tasks (snapshot recording) also receive state references from lifespan scope

### Static File Serving
- **D-12:** FastAPI mounts `StaticFiles(directory="static", html=True)` as the catch-all at `/`
- **D-13:** API routes registered FIRST with `/api` prefix; static mount registered LAST
- **D-14:** Placeholder `static/index.html` created for Phase 1 testing — replaced by Next.js build output in Phase 4

### Claude's Discretion
- Exact error messages for health check failure modes
- Logging verbosity at startup
- Exact structure of health check response JSON

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specification
- `planning/PLAN.md` §7 — Database schema (all 6 tables with column definitions, types, defaults)
- `planning/PLAN.md` §3 — Architecture overview (single container, FastAPI serving static files)
- `planning/PLAN.md` §5 — Environment variables (MASSIVE_API_KEY, OPENROUTER_API_KEY, LLM_MOCK)
- `planning/PLAN.md` §8 — API endpoints (health check at GET /api/health)
- `planning/PLAN.md` §4 — Directory structure (backend/, db/, frontend/ boundaries)

### Existing Market Data
- `planning/MARKET_DATA_SUMMARY.md` — Complete market data subsystem summary (usage patterns for downstream code)
- `backend/app/market/__init__.py` — Public API: PriceCache, create_market_data_source, create_stream_router

### Research
- `.planning/research/PITFALLS.md` §1-2 — SQLite async blocking and concurrent write contention pitfalls
- `.planning/research/STACK.md` — aiosqlite recommendation with rationale
- `.planning/research/ARCHITECTURE.md` — Component boundaries and data flow diagrams

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/market/` — Complete market data subsystem (PriceCache, SimulatorDataSource, MassiveDataSource, SSE stream router)
- `backend/app/market/factory.py` — `create_market_data_source(cache)` selects simulator vs Massive based on env var
- `backend/app/market/stream.py` — `create_stream_router(price_cache)` creates SSE endpoint router
- `backend/app/market/seed_prices.py` — SEED_PRICES dict with initial prices for all 10 default tickers

### Established Patterns
- Strategy pattern for data sources (ABC + concrete implementations)
- Factory functions returning abstract types (`create_market_data_source`)
- Dependency injection (PriceCache passed to constructors, not global)
- Module-level `__all__` exports in `__init__.py`
- `from __future__ import annotations` in all modules
- Frozen dataclasses for value objects (PriceUpdate)
- `logging.getLogger(__name__)` per module

### Integration Points
- `app.state.cache` — PriceCache instance created in lifespan, used by SSE router and future portfolio/trade routes
- `app.state.source` — MarketDataSource instance, needs `start()` on startup and `stop()` on shutdown
- SSE stream router needs to be included in the FastAPI app via `app.include_router()`
- Default tickers from database watchlist seed need to be passed to `source.start(tickers)`

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. The PLAN.md spec is comprehensive and prescriptive for this phase.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-03-21*
