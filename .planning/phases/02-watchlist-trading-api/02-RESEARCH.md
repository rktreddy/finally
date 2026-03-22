# Phase 2: Watchlist & Trading API - Research

**Researched:** 2026-03-21
**Domain:** FastAPI REST endpoints, SQLite repository pattern, portfolio math, background tasks
**Confidence:** HIGH

## Summary

Phase 2 builds 6 REST endpoints (3 watchlist, 3 portfolio) plus a background snapshot task on top of the existing FastAPI app, aiosqlite database, and PriceCache. The codebase already provides all infrastructure: the database schema has all needed tables (watchlist, positions, trades, portfolio_snapshots, users_profile), PriceCache has the exact API methods needed (get_price, get_all, remove), and MarketDataSource exposes add_ticker/remove_ticker. The existing route pattern (health.py) and test pattern (test_app.py) are well-established and should be followed precisely.

The primary technical challenge is trade execution atomicity -- ensuring cash balance, position, and trade log updates happen in a single transaction. The aiosqlite connection is shared via `app.state.db` and uses `aiosqlite.Row` factory. All business logic decisions are locked in CONTEXT.md (weighted average cost, zero-quantity deletion, uppercase normalization, etc.).

**Primary recommendation:** Follow the established patterns exactly. Repository functions in `backend/app/db/` for SQL operations, route handlers in `backend/app/routes/` using Pydantic models, access shared state via `request.app.state`. No new dependencies needed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Price lookup at trade time uses `PriceCache.get_price(ticker)` -- not a database query. If ticker is not in cache, reject the trade with a clear error.
- **D-02:** Trade execution is atomic: cash balance update, position create/update, and trade log insert happen in a single database transaction (`async with db.execute()` + `await db.commit()` once).
- **D-03:** Buy validation: `quantity * current_price <= cash_balance`. Sell validation: `quantity <= position.quantity`. Both reject with 400 and descriptive error message.
- **D-04:** When a position is fully sold (quantity reaches 0), delete the row from the positions table -- don't leave zero-quantity rows.
- **D-05:** Fractional shares are supported (quantity is REAL). No minimum order size.
- **D-06:** Market orders only -- price is always the current PriceCache price at execution time. No slippage simulation.
- **D-07:** Unrealized P&L is computed at request time: `(current_price - avg_cost) * quantity` per position. Not stored in the database.
- **D-08:** Total portfolio value = cash balance + sum of (quantity * current_price) for all positions. Computed live from PriceCache.
- **D-09:** Average cost updated on buy using weighted average: `new_avg = (old_qty * old_avg + buy_qty * buy_price) / (old_qty + buy_qty)`. Sells do not change avg_cost.
- **D-10:** Adding a ticker: normalize to uppercase, insert into database, then call `await source.add_ticker(ticker)` to start receiving prices.
- **D-11:** Removing a ticker: delete from database, then call `await source.remove_ticker(ticker)` to stop receiving prices. Also call `cache.remove(ticker)`.
- **D-12:** Adding a duplicate ticker returns 409 Conflict. Removing a non-existent ticker returns 404.
- **D-13:** GET /api/watchlist returns tickers enriched with live prices from PriceCache (price, change, change_percent, direction).
- **D-14:** An asyncio background task started in lifespan records portfolio snapshots every 30 seconds by computing total portfolio value from cash + positions * live prices.
- **D-15:** A snapshot is also recorded immediately after each successful trade (inline in the trade endpoint, not via the background task).
- **D-16:** The background task uses the same `try/except Exception` + `logger.exception()` pattern as the market data loops -- errors don't kill the task.
- **D-17:** All endpoints return JSON. Errors use FastAPI's HTTPException with appropriate status codes (400, 404, 409).
- **D-18:** POST /api/portfolio/trade returns the executed trade record plus updated cash balance.
- **D-19:** GET /api/portfolio returns: `{cash, positions: [{ticker, quantity, avg_cost, current_price, unrealized_pnl, pnl_percent}], total_value, total_pnl}`.
- **D-20:** Watchlist routes in `backend/app/routes/watchlist.py`, portfolio routes in `backend/app/routes/portfolio.py`.
- **D-21:** Business logic (trade execution, P&L calculation, snapshot recording) lives in service/repository functions, not directly in route handlers. Repository functions in `backend/app/db/` for database operations.
- **D-22:** Pydantic models for request/response validation in route modules (or a shared models file if reuse emerges).

### Claude's Discretion
- Exact Pydantic model field names and nesting structure
- Whether to use a separate `services/` directory or keep logic in route modules
- Snapshot task startup/shutdown coordination details
- Exact error message wording

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WL-01 | User can view watchlist with current prices from GET /api/watchlist | PriceCache.get() returns PriceUpdate with price/change/direction; enrich DB rows with cache data |
| WL-02 | User can add a ticker to watchlist via POST /api/watchlist | DB INSERT with uuid4, then source.add_ticker(); handle UNIQUE constraint for 409 |
| WL-03 | User can remove a ticker from watchlist via DELETE /api/watchlist/{ticker} | DB DELETE, then source.remove_ticker() + cache.remove() |
| WL-04 | Watchlist changes sync with market data source (add_ticker/remove_ticker) | MarketDataSource.add_ticker/remove_ticker are async, no-op for duplicates/missing |
| PT-01 | User can view portfolio (positions, cash, total value, unrealized P&L) via GET /api/portfolio | Compute P&L live from PriceCache; query positions + users_profile |
| PT-02 | User can buy shares at current market price via POST /api/portfolio/trade | PriceCache.get_price() for current price; atomic transaction for cash/position/trade |
| PT-03 | User can sell shares at current market price via POST /api/portfolio/trade | Same atomic transaction pattern; delete position row if quantity reaches 0 |
| PT-04 | Buy validation rejects if insufficient cash | Check quantity * price <= cash_balance before transaction |
| PT-05 | Sell validation rejects if insufficient shares | Check quantity <= position.quantity before transaction |
| PT-06 | Trade history recorded as append-only log | INSERT into trades table within the atomic transaction |
| PT-07 | Portfolio snapshots recorded every 30 seconds by background task | asyncio background task in lifespan; compute total_value from cash + positions * prices |
| PT-08 | Portfolio snapshot recorded immediately after each trade | Inline snapshot insert after successful trade commit |
| PT-09 | User can view portfolio value history via GET /api/portfolio/history | Simple SELECT from portfolio_snapshots ordered by recorded_at |
</phase_requirements>

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.128.7 | REST API framework | Already in project; provides APIRouter, HTTPException, Depends |
| Pydantic | 2.12.5 | Request/response models | Pulled in by FastAPI; use BaseModel for all API schemas |
| aiosqlite | 0.22.1 | Async SQLite access | Already in project; connection shared via app.state.db |
| httpx | 0.28.1+ | Test client | Already in project; ASGITransport for integration tests |

### Supporting (no new installs needed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uuid (stdlib) | - | Generate primary keys | All INSERT operations use `str(uuid.uuid4())` |
| asyncio (stdlib) | - | Background task for snapshots | `asyncio.create_task()` in lifespan |
| logging (stdlib) | - | Module-level loggers | Every new module |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Repository functions | SQLAlchemy ORM | Overkill for simple SQLite; project already uses raw aiosqlite |
| Inline Pydantic models | Separate schemas package | Only separate if significant reuse emerges (Claude's discretion) |

**Installation:** No new packages needed. All dependencies are already in `backend/pyproject.toml`.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── db/
│   ├── __init__.py          # Existing: init_db, get_db_path
│   ├── schema.sql           # Existing: all tables already defined
│   ├── seed.py              # Existing: default user + watchlist
│   └── repository.py        # NEW: all SQL query functions (watchlist, portfolio, trades, snapshots)
├── routes/
│   ├── __init__.py          # Existing: empty
│   ├── health.py            # Existing: health check
│   ├── watchlist.py         # NEW: GET/POST/DELETE /api/watchlist
│   └── portfolio.py         # NEW: GET/POST portfolio, GET history, background snapshot
├── market/
│   └── (existing, unchanged)
└── main.py                  # MODIFY: register new routers, start snapshot task in lifespan
```

### Pattern 1: Route Handler Pattern (established in health.py)
**What:** FastAPI APIRouter with route functions accessing shared state via `request.app.state`
**When to use:** All new endpoints
**Example:**
```python
# Source: backend/app/routes/health.py (existing pattern)
from fastapi import APIRouter, Request
router = APIRouter(tags=["watchlist"])

@router.get("/watchlist")
async def get_watchlist(request: Request) -> list[dict]:
    db = request.app.state.db
    cache = request.app.state.cache
    # ... query db, enrich with cache prices
```

### Pattern 2: Repository Function Pattern (established in seed.py)
**What:** Async functions that take an aiosqlite connection and execute SQL
**When to use:** All database operations -- keeps SQL out of route handlers
**Example:**
```python
# Source: backend/app/db/seed.py (existing pattern)
async def get_watchlist_tickers(db: aiosqlite.Connection, user_id: str = "default") -> list[dict]:
    async with db.execute(
        "SELECT ticker, added_at FROM watchlist WHERE user_id = ? ORDER BY added_at",
        (user_id,),
    ) as cursor:
        rows = await cursor.fetchall()
        return [{"ticker": row["ticker"], "added_at": row["added_at"]} for row in rows]
```

### Pattern 3: Atomic Transaction Pattern
**What:** Multiple SQL statements committed as a single transaction
**When to use:** Trade execution (cash update + position upsert + trade log)
**Example:**
```python
# Trade execution: all three statements in one transaction
await db.execute("UPDATE users_profile SET cash_balance = ? WHERE id = ?", (new_cash, user_id))
await db.execute(
    "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost) VALUES (?, ?, ?, ?, ?) "
    "ON CONFLICT(user_id, ticker) DO UPDATE SET quantity = ?, avg_cost = ?, updated_at = datetime('now')",
    (pos_id, user_id, ticker, new_qty, new_avg, new_qty, new_avg),
)
await db.execute(
    "INSERT INTO trades (id, user_id, ticker, side, quantity, price) VALUES (?, ?, ?, ?, ?, ?)",
    (trade_id, user_id, ticker, side, quantity, price),
)
await db.commit()
```

### Pattern 4: Background Task Pattern (established in market data)
**What:** asyncio task started in lifespan, cancelled on shutdown
**When to use:** Portfolio snapshot recording every 30 seconds
**Example:**
```python
# In lifespan, after market data source starts:
snapshot_task = asyncio.create_task(_snapshot_loop(app))
app.state.snapshot_task = snapshot_task

# In shutdown:
snapshot_task.cancel()
try:
    await snapshot_task
except asyncio.CancelledError:
    pass
```

### Anti-Patterns to Avoid
- **SQL in route handlers:** Move all SQL to repository.py -- routes should call repository functions
- **Forgetting to commit:** aiosqlite does not auto-commit; every write path needs `await db.commit()`
- **Reading stale prices from DB:** Always use PriceCache for current prices, never store "current_price" in the database
- **Blocking the event loop:** aiosqlite is already async; no need for `asyncio.to_thread()` on DB calls
- **Silent duplicate handling on watchlist add:** User expects 409 Conflict, not silent no-op (the MarketDataSource.add_ticker is no-op for duplicates, but the DB UNIQUE constraint must be caught and returned as 409)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UUID generation | Custom ID schemes | `str(uuid.uuid4())` | Established pattern in seed.py; UUIDs as TEXT PKs |
| Request validation | Manual field checks | Pydantic BaseModel | FastAPI auto-validates and returns 422 with details |
| Error responses | Custom error dicts | `raise HTTPException(status_code=400, detail="...")` | FastAPI standard; consistent error format |
| SQL upsert | SELECT-then-INSERT logic | `INSERT ... ON CONFLICT ... DO UPDATE` | SQLite native upsert; atomic, no race conditions |
| Background scheduling | Custom timer/sleep loop | `asyncio.sleep(30)` in a loop with `asyncio.create_task` | Same pattern as market data source |

**Key insight:** The existing codebase has established patterns for every concern in this phase. The risk is deviating from these patterns, not missing some library.

## Common Pitfalls

### Pitfall 1: aiosqlite IntegrityError on Duplicate Watchlist Add
**What goes wrong:** INSERT into watchlist with duplicate (user_id, ticker) raises `aiosqlite.IntegrityError` (wraps sqlite3.IntegrityError) instead of returning a useful error.
**Why it happens:** The UNIQUE(user_id, ticker) constraint fires.
**How to avoid:** Catch `aiosqlite.IntegrityError` (or `sqlite3.IntegrityError`) and raise `HTTPException(status_code=409, detail="Ticker already in watchlist")`.
**Warning signs:** Unhandled 500 errors when adding a ticker that already exists.

### Pitfall 2: Forgetting cache.remove() on Watchlist Delete
**What goes wrong:** Ticker removed from DB and market data source, but PriceCache still holds stale data. GET /api/watchlist enrichment sees no DB row, but other code might still see the cached price.
**Why it happens:** Three systems need updating: DB, source, cache. Easy to forget one.
**How to avoid:** Watchlist delete must do all three: DB delete, `source.remove_ticker()`, `cache.remove()`. The CONTEXT.md D-11 is explicit about this.
**Warning signs:** Stale price data appearing after ticker removal.

### Pitfall 3: Division by Zero in P&L Percentage
**What goes wrong:** `pnl_percent = unrealized_pnl / (avg_cost * quantity) * 100` can divide by zero if avg_cost is 0 (shouldn't happen normally but defensive coding matters).
**Why it happens:** Edge case with cost basis.
**How to avoid:** Guard with `if avg_cost > 0` or compute as `(current_price - avg_cost) / avg_cost * 100`.
**Warning signs:** 500 errors on portfolio endpoint.

### Pitfall 4: Snapshot Task Accessing Closed DB
**What goes wrong:** If the snapshot task fires during shutdown after DB is closed, it crashes.
**Why it happens:** Race between task cancellation and DB close in lifespan shutdown.
**How to avoid:** Cancel the snapshot task BEFORE closing the DB connection. In lifespan shutdown: cancel snapshot task -> await it -> stop market data -> close DB.
**Warning signs:** Errors on shutdown in CI/test runs.

### Pitfall 5: Not Normalizing Ticker to Uppercase
**What goes wrong:** User adds "aapl", DB has "aapl", but PriceCache has "AAPL". Enrichment fails to match.
**Why it happens:** PriceCache uses uppercase tickers (from seed data and simulator). User input might be lowercase.
**How to avoid:** Normalize `ticker = ticker.upper()` at the top of every endpoint that accepts a ticker. D-10 is explicit about this.
**Warning signs:** "Ticker not found" errors for valid tickers in different case.

### Pitfall 6: Floating Point Comparison in Sell Validation
**What goes wrong:** Selling exact quantity fails because `10.0000000001 <= 10.0` is False.
**Why it happens:** Floating point arithmetic accumulation through multiple buys.
**How to avoid:** Use a small epsilon tolerance, or round to a fixed number of decimal places (e.g., 8 decimals) before comparison. Or use `quantity <= position.quantity + 1e-9`.
**Warning signs:** "Insufficient shares" error when selling the full position.

## Code Examples

### Watchlist GET with Price Enrichment
```python
# Pattern: DB query + PriceCache enrichment
async def get_watchlist_tickers(db: aiosqlite.Connection, user_id: str = "default") -> list[dict]:
    async with db.execute(
        "SELECT ticker, added_at FROM watchlist WHERE user_id = ? ORDER BY added_at",
        (user_id,),
    ) as cursor:
        return [dict(row) for row in await cursor.fetchall()]

# In route handler:
@router.get("/watchlist")
async def get_watchlist(request: Request) -> list[dict]:
    db = request.app.state.db
    cache = request.app.state.cache
    tickers = await get_watchlist_tickers(db)
    result = []
    for item in tickers:
        ticker = item["ticker"]
        price_update = cache.get(ticker)
        entry = {"ticker": ticker, "added_at": item["added_at"]}
        if price_update:
            entry.update({
                "price": price_update.price,
                "change": price_update.change,
                "change_percent": price_update.change_percent,
                "direction": price_update.direction,
            })
        result.append(entry)
    return result
```

### Trade Execution with Atomic Transaction
```python
# Pattern: Validate first, then execute atomically
async def execute_trade(
    db: aiosqlite.Connection,
    cache: PriceCache,
    user_id: str,
    ticker: str,
    side: str,
    quantity: float,
) -> dict:
    # 1. Get current price from cache (not DB)
    current_price = cache.get_price(ticker)
    if current_price is None:
        raise HTTPException(status_code=400, detail=f"No price available for {ticker}")

    # 2. Get current cash balance
    async with db.execute(
        "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
    ) as cursor:
        row = await cursor.fetchone()
        cash = row["cash_balance"]

    total_cost = quantity * current_price

    if side == "buy":
        if total_cost > cash:
            raise HTTPException(status_code=400, detail="Insufficient cash")
        new_cash = cash - total_cost
        # ... upsert position with weighted avg cost
    elif side == "sell":
        # ... validate shares, update position, delete if zero
        new_cash = cash + total_cost

    # 3. Atomic: update cash, upsert/delete position, insert trade log
    await db.execute("UPDATE users_profile SET cash_balance = ? WHERE id = ?", (new_cash, user_id))
    # ... position operations ...
    trade_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO trades (id, user_id, ticker, side, quantity, price) VALUES (?, ?, ?, ?, ?, ?)",
        (trade_id, user_id, ticker, side, quantity, current_price),
    )
    await db.commit()
    return {"id": trade_id, "ticker": ticker, "side": side, "quantity": quantity,
            "price": current_price, "cash_balance": new_cash}
```

### Snapshot Background Task
```python
# Pattern: matches market data source background loop
async def _snapshot_loop(app: FastAPI) -> None:
    logger = logging.getLogger(__name__)
    while True:
        try:
            await asyncio.sleep(30)
            await record_snapshot(app.state.db, app.state.cache)
        except asyncio.CancelledError:
            logger.info("Snapshot task cancelled")
            raise
        except Exception:
            logger.exception("Error recording portfolio snapshot")

async def record_snapshot(db: aiosqlite.Connection, cache: PriceCache, user_id: str = "default") -> None:
    async with db.execute("SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)) as cursor:
        row = await cursor.fetchone()
        cash = row["cash_balance"]
    async with db.execute(
        "SELECT ticker, quantity FROM positions WHERE user_id = ?", (user_id,)
    ) as cursor:
        positions = await cursor.fetchall()
    holdings_value = sum(
        row["quantity"] * (cache.get_price(row["ticker"]) or 0.0)
        for row in positions
    )
    total_value = cash + holdings_value
    await db.execute(
        "INSERT INTO portfolio_snapshots (id, user_id, total_value) VALUES (?, ?, ?)",
        (str(uuid.uuid4()), user_id, total_value),
    )
    await db.commit()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| sqlite3 sync | aiosqlite async | Already adopted | All DB ops are async; no blocking |
| Pydantic v1 | Pydantic v2 (2.12.5) | Already adopted | Use `model_validate`, not `from_orm` |
| `@app.on_event` | Lifespan context manager | FastAPI 0.109+ | Already using lifespan in main.py |

**Deprecated/outdated:**
- `@app.on_event("startup")` / `@app.on_event("shutdown")` -- use lifespan instead (already done)
- Pydantic v1 `schema()` / `from_orm()` -- use v2 `model_json_schema()` / `model_validate()`

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.0+ with pytest-asyncio |
| Config file | `backend/pyproject.toml` ([tool.pytest.ini_options]) |
| Quick run command | `cd backend && uv run --extra dev pytest tests/test_watchlist.py tests/test_portfolio.py -x -v` |
| Full suite command | `cd backend && uv run --extra dev pytest -v --cov=app` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WL-01 | GET /api/watchlist returns tickers with prices | integration | `uv run --extra dev pytest tests/test_watchlist.py::test_get_watchlist -x` | Wave 0 |
| WL-02 | POST /api/watchlist adds ticker | integration | `uv run --extra dev pytest tests/test_watchlist.py::test_add_ticker -x` | Wave 0 |
| WL-03 | DELETE /api/watchlist/{ticker} removes ticker | integration | `uv run --extra dev pytest tests/test_watchlist.py::test_remove_ticker -x` | Wave 0 |
| WL-04 | Add/remove syncs with market data source | integration | `uv run --extra dev pytest tests/test_watchlist.py::test_add_syncs_source -x` | Wave 0 |
| PT-01 | GET /api/portfolio returns positions with P&L | integration | `uv run --extra dev pytest tests/test_portfolio.py::test_get_portfolio -x` | Wave 0 |
| PT-02 | POST /api/portfolio/trade buy works | integration | `uv run --extra dev pytest tests/test_portfolio.py::test_buy_trade -x` | Wave 0 |
| PT-03 | POST /api/portfolio/trade sell works | integration | `uv run --extra dev pytest tests/test_portfolio.py::test_sell_trade -x` | Wave 0 |
| PT-04 | Buy rejects insufficient cash | integration | `uv run --extra dev pytest tests/test_portfolio.py::test_buy_insufficient_cash -x` | Wave 0 |
| PT-05 | Sell rejects insufficient shares | integration | `uv run --extra dev pytest tests/test_portfolio.py::test_sell_insufficient_shares -x` | Wave 0 |
| PT-06 | Trade history recorded | integration | `uv run --extra dev pytest tests/test_portfolio.py::test_trade_history -x` | Wave 0 |
| PT-07 | Snapshots recorded every 30s | unit | `uv run --extra dev pytest tests/test_portfolio.py::test_snapshot_background -x` | Wave 0 |
| PT-08 | Snapshot after trade | integration | `uv run --extra dev pytest tests/test_portfolio.py::test_snapshot_after_trade -x` | Wave 0 |
| PT-09 | GET /api/portfolio/history returns snapshots | integration | `uv run --extra dev pytest tests/test_portfolio.py::test_portfolio_history -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && uv run --extra dev pytest tests/test_watchlist.py tests/test_portfolio.py -x -v`
- **Per wave merge:** `cd backend && uv run --extra dev pytest -v --cov=app`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_watchlist.py` -- covers WL-01 through WL-04
- [ ] `tests/test_portfolio.py` -- covers PT-01 through PT-09
- [ ] Shared test fixtures in `tests/conftest.py` -- may need a fixture that seeds a trade/position for sell tests

*(Existing `tests/conftest.py` has minimal fixtures; `tests/test_app.py` has the `client` fixture pattern that should be reused/shared)*

## Open Questions

1. **Concurrent access to aiosqlite connection**
   - What we know: aiosqlite uses a single background thread for all operations. Multiple coroutines can share one connection.
   - What's unclear: Whether concurrent writes (snapshot task + trade endpoint) could conflict.
   - Recommendation: SQLite with WAL mode handles concurrent readers well. Writes are serialized by aiosqlite's background thread. Should work fine for single-user. If issues arise, add a write lock, but this is unlikely to be needed.

2. **Snapshot task timing on startup**
   - What we know: The snapshot task should start in lifespan after market data source starts.
   - What's unclear: Whether to record an initial snapshot immediately or wait 30 seconds.
   - Recommendation: Wait 30 seconds before first snapshot (use `asyncio.sleep(30)` at top of loop). The initial state is just $10k cash with no positions -- not interesting. Trades trigger immediate snapshots anyway (D-15).

## Sources

### Primary (HIGH confidence)
- `backend/app/db/schema.sql` -- exact table definitions, constraints, column types
- `backend/app/db/__init__.py` -- init_db pattern, WAL mode, Row factory
- `backend/app/db/seed.py` -- INSERT OR IGNORE pattern, uuid4 for PKs
- `backend/app/market/cache.py` -- PriceCache API (get_price, get_all, get, remove)
- `backend/app/market/interface.py` -- MarketDataSource.add_ticker/remove_ticker signatures
- `backend/app/routes/health.py` -- route handler pattern (APIRouter, request.app.state)
- `backend/app/main.py` -- lifespan pattern, router registration, app.state usage
- `backend/tests/test_app.py` -- test pattern (client fixture, ASGITransport, lifespan context)
- `backend/pyproject.toml` -- installed versions, pytest config

### Secondary (MEDIUM confidence)
- aiosqlite 0.22.1 documentation -- connection sharing, transaction behavior
- FastAPI 0.128.7 documentation -- HTTPException, APIRouter, Depends

### Tertiary (LOW confidence)
- None -- all findings verified against existing codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed and in use in the codebase
- Architecture: HIGH - all patterns established in Phase 1; this phase extends them
- Pitfalls: HIGH - identified from direct codebase analysis and SQLite/aiosqlite behavior

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (stable -- no external dependencies or fast-moving libraries)
