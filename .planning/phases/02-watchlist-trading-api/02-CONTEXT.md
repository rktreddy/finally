# Phase 2: Watchlist & Trading API - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can manage their watchlist and execute trades through REST API endpoints, with all positions, P&L, and trade history properly tracked. This phase delivers 6 REST endpoints (3 watchlist, 3 portfolio) plus a background snapshot task. No frontend, no LLM — pure API layer with database persistence and live price integration.

</domain>

<decisions>
## Implementation Decisions

### Trade Execution
- **D-01:** Price lookup at trade time uses `PriceCache.get_price(ticker)` — not a database query. If ticker is not in cache, reject the trade with a clear error.
- **D-02:** Trade execution is atomic: cash balance update, position create/update, and trade log insert happen in a single database transaction (`async with db.execute()` + `await db.commit()` once).
- **D-03:** Buy validation: `quantity * current_price <= cash_balance`. Sell validation: `quantity <= position.quantity`. Both reject with 400 and descriptive error message.
- **D-04:** When a position is fully sold (quantity reaches 0), delete the row from the positions table — don't leave zero-quantity rows.
- **D-05:** Fractional shares are supported (quantity is REAL). No minimum order size.
- **D-06:** Market orders only — price is always the current PriceCache price at execution time. No slippage simulation.

### Portfolio Valuation
- **D-07:** Unrealized P&L is computed at request time: `(current_price - avg_cost) * quantity` per position. Not stored in the database.
- **D-08:** Total portfolio value = cash balance + sum of (quantity * current_price) for all positions. Computed live from PriceCache.
- **D-09:** Average cost updated on buy using weighted average: `new_avg = (old_qty * old_avg + buy_qty * buy_price) / (old_qty + buy_qty)`. Sells do not change avg_cost.

### Watchlist Management
- **D-10:** Adding a ticker: normalize to uppercase, insert into database, then call `await source.add_ticker(ticker)` to start receiving prices.
- **D-11:** Removing a ticker: delete from database, then call `await source.remove_ticker(ticker)` to stop receiving prices. Also call `cache.remove(ticker)`.
- **D-12:** Adding a duplicate ticker returns 409 Conflict. Removing a non-existent ticker returns 404.
- **D-13:** GET /api/watchlist returns tickers enriched with live prices from PriceCache (price, change, change_percent, direction).

### Snapshot Background Task
- **D-14:** An asyncio background task started in lifespan records portfolio snapshots every 30 seconds by computing total portfolio value from cash + positions * live prices.
- **D-15:** A snapshot is also recorded immediately after each successful trade (inline in the trade endpoint, not via the background task).
- **D-16:** The background task uses the same `try/except Exception` + `logger.exception()` pattern as the market data loops — errors don't kill the task.

### API Response Shapes
- **D-17:** All endpoints return JSON. Errors use FastAPI's HTTPException with appropriate status codes (400, 404, 409).
- **D-18:** POST /api/portfolio/trade returns the executed trade record plus updated cash balance.
- **D-19:** GET /api/portfolio returns: `{cash, positions: [{ticker, quantity, avg_cost, current_price, unrealized_pnl, pnl_percent}], total_value, total_pnl}`.

### Code Organization
- **D-20:** Watchlist routes in `backend/app/routes/watchlist.py`, portfolio routes in `backend/app/routes/portfolio.py`.
- **D-21:** Business logic (trade execution, P&L calculation, snapshot recording) lives in service/repository functions, not directly in route handlers. Repository functions in `backend/app/db/` for database operations, service logic can be in route modules or a thin service layer.
- **D-22:** Pydantic models for request/response validation in route modules (or a shared models file if reuse emerges).

### Claude's Discretion
- Exact Pydantic model field names and nesting structure
- Whether to use a separate `services/` directory or keep logic in route modules
- Snapshot task startup/shutdown coordination details
- Exact error message wording

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. The PLAN.md spec is comprehensive and prescriptive for this phase.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### API Specification
- `planning/PLAN.md` §8 — API endpoint definitions (paths, methods, request/response shapes)
- `planning/PLAN.md` §7 — Database schema (positions, trades, portfolio_snapshots, watchlist tables with exact columns)

### Architecture & Patterns
- `planning/PLAN.md` §3 — Single-container architecture, FastAPI serving everything
- `planning/PLAN.md` §6 — Market data: PriceCache as shared state, SSE streaming, dynamic ticker management

### Prior Phase Context
- `.planning/phases/01-foundation/01-CONTEXT.md` — Database connection strategy (D-01 through D-04), app state sharing (D-09 through D-11)

### Existing Market Data
- `planning/MARKET_DATA_SUMMARY.md` — PriceCache API, MarketDataSource add_ticker/remove_ticker behavior

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/db/__init__.py` — `init_db()` returns aiosqlite connection; schema already defines all Phase 2 tables
- `backend/app/db/seed.py` — Seed data pattern (INSERT OR IGNORE) for reference
- `backend/app/market/cache.py` — `PriceCache.get_price(ticker)`, `get_all()`, `get(ticker)`, `remove(ticker)` — all needed for portfolio valuation and watchlist enrichment
- `backend/app/market/interface.py` — `MarketDataSource.add_ticker()`, `remove_ticker()` — for watchlist sync
- `backend/app/routes/health.py` — Route pattern: `APIRouter()`, access `request.app.state`

### Established Patterns
- Routes access shared state via `request.app.state.db`, `request.app.state.cache`, `request.app.state.source`
- Database operations use `async with db.execute(sql, params)` with `aiosqlite.Row` results
- Background tasks started in lifespan, stored on app.state, cancelled on shutdown
- Factory functions return abstract types; dependency injection over globals
- `from __future__ import annotations` in every module; typed returns on all public methods

### Integration Points
- `app.state.db` — aiosqlite connection for all database reads/writes
- `app.state.cache` — PriceCache for live price lookups in portfolio valuation and trade execution
- `app.state.source` — MarketDataSource for add_ticker/remove_ticker on watchlist changes
- `app.include_router()` in `main.py` — new routers need to be registered with `/api` prefix
- Lifespan — snapshot background task needs to be started/stopped alongside market data source

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-watchlist-trading-api*
*Context gathered: 2026-03-21*
