# Phase 1: Foundation - Research

**Researched:** 2026-03-21
**Domain:** FastAPI application bootstrap, SQLite async database, static file serving, market data integration
**Confidence:** HIGH

## Summary

Phase 1 establishes the running FastAPI application that all subsequent phases build on. The core work is: (1) creating the SQLite database schema with lazy initialization and seed data using `aiosqlite`, (2) wiring the existing market data subsystem (PriceCache, SimulatorDataSource, SSE streaming) into the FastAPI lifespan, (3) serving a placeholder static frontend, and (4) exposing a health check endpoint.

The existing codebase already has a complete market data subsystem (`backend/app/market/`) with 73 passing tests. The `db/`, `routes/`, and `llm/` directories exist under `backend/app/` but contain no Python files yet -- they are empty placeholders. The `pyproject.toml` has FastAPI 0.128.7, uvicorn, numpy, massive, and rich as dependencies. `aiosqlite` needs to be added.

**Primary recommendation:** Use `aiosqlite` 0.20+ with a single shared connection stored on `app.state.db`, WAL mode enabled, and `CREATE TABLE IF NOT EXISTS` for idempotent lazy init. Mount API routers first, static files last.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use a single shared `aiosqlite` connection created at app startup, stored in `app.state.db`
- **D-02:** Enable WAL mode (`PRAGMA journal_mode=WAL`) on connection open for concurrent reads during SSE streaming
- **D-03:** Connection opened in lifespan startup, closed in lifespan shutdown
- **D-04:** All repository functions receive the db connection as a parameter (dependency injection, not global)
- **D-05:** Schema defined in `backend/app/db/schema.sql` as a raw SQL file
- **D-06:** Python function `init_db()` reads the SQL file and executes it; checks if tables exist first (lazy init)
- **D-07:** Seed data (default user profile + 10 watchlist tickers) applied in the same init function, only if data doesn't exist
- **D-08:** No migration framework -- lazy init only. Tables created with `CREATE TABLE IF NOT EXISTS`
- **D-09:** PriceCache, MarketDataSource, and DB connection stored on `app.state` during lifespan startup
- **D-10:** FastAPI routes access shared state via `request.app.state` (standard FastAPI pattern)
- **D-11:** Background tasks also receive state references from lifespan scope
- **D-12:** FastAPI mounts `StaticFiles(directory="static", html=True)` as the catch-all at `/`
- **D-13:** API routes registered FIRST with `/api` prefix; static mount registered LAST
- **D-14:** Placeholder `static/index.html` created for Phase 1 testing -- replaced by Next.js build output in Phase 4

### Claude's Discretion
- Exact error messages for health check failure modes
- Logging verbosity at startup
- Exact structure of health check response JSON

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DB-01 | SQLite database auto-creates schema and seeds default data on first run (lazy init) | aiosqlite `executescript()` with `CREATE TABLE IF NOT EXISTS`; seed via conditional INSERT; schema.sql file pattern |
| DB-02 | User profile with $10,000 default cash balance persists across restarts | `users_profile` table with `cash_balance REAL DEFAULT 10000.0`; SQLite file at `db/finally.db` persists on disk |
| DB-03 | FastAPI app entry point with lifespan manages startup/shutdown of all subsystems | `@asynccontextmanager` lifespan pattern; `app.state` for shared resources |
| DB-04 | Existing market data (PriceCache, SimulatorDataSource, SSE stream) wired into app lifespan | Import from `app.market`; create PriceCache + source in lifespan; include stream router |
| DB-05 | Health check endpoint returns server status at GET /api/health | Simple APIRouter with GET endpoint returning JSON status |
| DB-06 | FastAPI serves static Next.js export as catch-all (API routes take priority) | `StaticFiles(directory="static", html=True)` mounted LAST at `/` |
| WL-05 | Default watchlist seeded with 10 tickers (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX) | Seed INSERT in `init_db()` after schema creation; tickers match `seed_prices.py` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastapi` | 0.128.7 (installed) | Web framework | Already in pyproject.toml; async-native, lifespan support |
| `uvicorn[standard]` | 0.32.0+ (installed) | ASGI server | Already in pyproject.toml |
| `aiosqlite` | 0.20.0+ (latest: 0.22.1) | Async SQLite wrapper | Thin wrapper over sqlite3 in thread executor; non-blocking for async app |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `starlette` | (bundled with FastAPI) | `StaticFiles` class | Static file serving with `html=True` for SPA catch-all |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `aiosqlite` | SQLAlchemy async | Massive overkill for single-user raw SQL; adds ORM complexity |
| `aiosqlite` | `databases` package | Stale maintenance, unnecessary abstraction |
| Raw SQL schema | Alembic migrations | Unnecessary -- single-user, no schema evolution needed |

**Installation:**
```bash
cd backend
uv add aiosqlite
```

**Version verification:** `aiosqlite` latest on PyPI is 0.22.1 (confirmed via `pip index versions`). FastAPI 0.128.7 already installed in backend venv.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── __init__.py              # "FinAlly backend application."
├── main.py                  # NEW: FastAPI app, lifespan, route/mount wiring
├── market/                  # EXISTING: Complete market data subsystem
│   ├── __init__.py
│   ├── cache.py
│   ├── factory.py
│   ├── interface.py
│   ├── models.py
│   ├── seed_prices.py
│   ├── simulator.py
│   ├── massive_client.py
│   └── stream.py
├── db/                      # NEW: Database layer
│   ├── __init__.py          # Exports: init_db, get_db_path
│   ├── schema.sql           # Raw SQL DDL (all 6 tables)
│   └── seed.py              # Seed data insertion logic
└── routes/                  # NEW (partial): Only health.py in Phase 1
    ├── __init__.py
    └── health.py            # GET /api/health
```

Additionally at project root:
```
static/                      # NEW: Placeholder directory
└── index.html               # Placeholder HTML page
```

### Pattern 1: FastAPI Lifespan with app.state
**What:** Use `@asynccontextmanager` to manage all startup/shutdown resources in one place.
**When to use:** Always -- this is the current FastAPI standard (replaces deprecated `@app.on_event`).
**Example:**
```python
# Source: https://fastapi.tiangolo.com/advanced/events/
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.market import PriceCache, create_market_data_source, create_stream_router
from app.db import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: DB
    db_path = "db/finally.db"
    db = await init_db(db_path)
    app.state.db = db

    # Startup: Market data
    cache = PriceCache()
    source = create_market_data_source(cache)
    tickers = await _get_seed_tickers(db)
    await source.start(tickers)
    app.state.cache = cache
    app.state.source = source

    yield

    # Shutdown
    await source.stop()
    await db.close()

app = FastAPI(lifespan=lifespan)
```

### Pattern 2: aiosqlite Single Shared Connection
**What:** Open one `aiosqlite` connection at startup, share it via `app.state.db`, close on shutdown.
**When to use:** Single-user SQLite apps where write contention is minimal.
**Example:**
```python
# Source: https://aiosqlite.omnilib.dev/en/stable/api.html
import aiosqlite

async def init_db(db_path: str) -> aiosqlite.Connection:
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row  # Access columns by name
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")

    # Read and execute schema
    schema_path = Path(__file__).parent / "schema.sql"
    schema_sql = schema_path.read_text()
    await db.executescript(schema_sql)

    # Seed default data if needed
    await _seed_defaults(db)
    await db.commit()
    return db
```

### Pattern 3: Schema as Raw SQL File
**What:** Define all tables in a single `schema.sql` file using `CREATE TABLE IF NOT EXISTS`.
**When to use:** When schema is stable and no migration framework is needed.
**Example:**
```sql
-- backend/app/db/schema.sql
CREATE TABLE IF NOT EXISTS users_profile (
    id TEXT PRIMARY KEY DEFAULT 'default',
    cash_balance REAL NOT NULL DEFAULT 10000.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS watchlist (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    ticker TEXT NOT NULL,
    added_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, ticker)
);
-- ... remaining 4 tables
```

### Pattern 4: Static File Mount Order
**What:** Register API routers first, mount StaticFiles last as catch-all.
**When to use:** Always when serving SPA + API from same FastAPI app.
**Example:**
```python
from starlette.staticfiles import StaticFiles

# API routes first
app.include_router(health_router, prefix="/api")
app.include_router(stream_router)  # Already has /api/stream prefix

# Static files LAST -- catches everything not matched by API
app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

### Anti-Patterns to Avoid
- **Global database connection module:** Do NOT create a module-level `db` variable. Pass the connection via `app.state` and access it in routes through `request.app.state.db`. This makes testing easier and avoids import-time side effects.
- **Using `@app.on_event("startup")`:** This is deprecated in favor of the lifespan context manager. Do not use it.
- **Mounting StaticFiles before API routes:** FastAPI matches routes in order. If StaticFiles is mounted first at `/`, it will catch `/api/*` requests and return 404 or index.html instead of API responses.
- **Using `executescript()` for seed data with conditional logic:** `executescript` runs raw SQL and auto-commits. For conditional inserts (INSERT OR IGNORE), use individual `execute()` calls within a transaction, then `commit()`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async SQLite access | Thread executor wrapper | `aiosqlite` | Handles thread safety, connection lifecycle, cursor proxying |
| UUID generation for table PKs | Custom ID generators | `uuid.uuid4()` via Python stdlib | Standard, unique, no collision risk for single-user |
| Static file serving | Custom route handlers for files | `StaticFiles(html=True)` from Starlette | Handles MIME types, caching headers, index.html fallback, 404s |
| Schema idempotency | Manual "table exists?" checks | `CREATE TABLE IF NOT EXISTS` | Built into SQLite, atomic, no race conditions |
| ISO timestamps | `strftime` formatting | `datetime('now')` in SQL or `datetime.utcnow().isoformat()` in Python | Consistent format across DB and application |

**Key insight:** Phase 1 is pure wiring and initialization -- every component either already exists (market data) or uses well-established library patterns (aiosqlite, FastAPI lifespan, StaticFiles). There is nothing novel to build.

## Common Pitfalls

### Pitfall 1: executescript Auto-Commits
**What goes wrong:** `aiosqlite`'s `executescript()` issues a `COMMIT` before executing the script, committing any pending transaction. If you mix `executescript()` with transactional seed logic, the transaction boundaries may not be what you expect.
**Why it happens:** This mirrors the stdlib `sqlite3.Cursor.executescript()` behavior.
**How to avoid:** Use `executescript()` only for DDL (CREATE TABLE statements). Use separate `execute()` calls for seed data inserts within an explicit transaction, followed by `commit()`.
**Warning signs:** Seed data partially inserted after a crash/interruption.

### Pitfall 2: StaticFiles Catches API Routes
**What goes wrong:** `/api/health` returns the index.html file instead of JSON.
**Why it happens:** `StaticFiles` mounted at `/` before API routers catches all paths.
**How to avoid:** Always `include_router()` for all API routes BEFORE `app.mount("/", StaticFiles(...))`. Test with `curl localhost:8000/api/health` to verify JSON response.
**Warning signs:** API endpoints returning HTML content-type.

### Pitfall 3: Missing static/ Directory at Startup
**What goes wrong:** FastAPI crashes on startup with `RuntimeError: directory 'static' does not exist`.
**Why it happens:** `StaticFiles` validates the directory exists when mounted.
**How to avoid:** Ensure `static/` directory and at least `static/index.html` exist before the app starts. Create them as part of this phase. In production, the Docker build copies the Next.js export here.
**Warning signs:** Application fails to start with directory not found error.

### Pitfall 4: Forgetting to Start Market Data Source
**What goes wrong:** SSE endpoint returns no data. Prices never update.
**Why it happens:** `PriceCache` and `MarketDataSource` are created but `source.start(tickers)` is never called.
**How to avoid:** In the lifespan, after creating the source, query the watchlist from the database for default tickers, then call `await source.start(tickers)`. The source needs a list of ticker symbols to begin generating/fetching prices.
**Warning signs:** SSE stream connects but never sends data events.

### Pitfall 5: Database File Path Mismatch
**What goes wrong:** Database created in wrong location; data doesn't persist across restarts.
**Why it happens:** Relative paths resolve differently depending on working directory. In Docker, the app runs from `/app` but the volume is mounted at `/app/db/`.
**How to avoid:** Use a configurable path (e.g., environment variable or constant) that defaults to `db/finally.db` relative to the project root. Ensure the `db/` directory exists before connecting (aiosqlite does NOT create parent directories).
**Warning signs:** New database created on every restart; previous data lost.

### Pitfall 6: aiosqlite Row Factory Not Set
**What goes wrong:** Query results return tuples instead of dict-like rows. Code accessing `row["ticker"]` fails with TypeError.
**Why it happens:** Default row factory returns plain tuples.
**How to avoid:** Set `db.row_factory = aiosqlite.Row` immediately after connecting. This allows column access by name (`row["column_name"]`).
**Warning signs:** `TypeError: tuple indices must be integers or slices, not str`.

## Code Examples

Verified patterns from official sources:

### Database Schema (schema.sql)
```sql
-- Source: PLAN.md Section 7 (schema specification)
-- All tables use CREATE TABLE IF NOT EXISTS for idempotent lazy init

CREATE TABLE IF NOT EXISTS users_profile (
    id TEXT PRIMARY KEY DEFAULT 'default',
    cash_balance REAL NOT NULL DEFAULT 10000.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS watchlist (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    ticker TEXT NOT NULL,
    added_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, ticker)
);

CREATE TABLE IF NOT EXISTS positions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    ticker TEXT NOT NULL,
    quantity REAL NOT NULL,
    avg_cost REAL NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, ticker)
);

CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    ticker TEXT NOT NULL,
    side TEXT NOT NULL CHECK(side IN ('buy', 'sell')),
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    executed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    total_value REAL NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    actions TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### Seed Data Insertion
```python
# Source: PLAN.md Section 7 (default seed data)
import uuid

DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]

async def seed_defaults(db: aiosqlite.Connection) -> None:
    """Insert default user profile and watchlist if they don't exist."""
    # Seed user profile (INSERT OR IGNORE for idempotency)
    await db.execute(
        "INSERT OR IGNORE INTO users_profile (id, cash_balance) VALUES (?, ?)",
        ("default", 10000.0),
    )

    # Seed watchlist
    for ticker in DEFAULT_TICKERS:
        await db.execute(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker) VALUES (?, ?, ?)",
            (str(uuid.uuid4()), "default", ticker),
        )

    await db.commit()
```

### Health Check Endpoint
```python
# Source: PLAN.md Section 8 (API endpoints)
from fastapi import APIRouter, Request

router = APIRouter(tags=["system"])

@router.get("/health")
async def health_check(request: Request) -> dict:
    """Health check endpoint for Docker/deployment monitoring."""
    return {
        "status": "healthy",
        "market_data": request.app.state.cache is not None,
        "database": request.app.state.db is not None,
    }
```

### Wiring Market Data into Lifespan
```python
# Source: planning/MARKET_DATA_SUMMARY.md (usage pattern)
from app.market import PriceCache, create_market_data_source, create_stream_router

# In lifespan startup:
cache = PriceCache()
source = create_market_data_source(cache)  # Reads MASSIVE_API_KEY env var
tickers = await _get_watchlist_tickers(db)  # Query default tickers from DB
await source.start(tickers)
app.state.cache = cache
app.state.source = source

# Include SSE router:
stream_router = create_stream_router(cache)
app.include_router(stream_router)

# In lifespan shutdown:
await source.stop()
```

### Querying Watchlist Tickers from DB
```python
async def get_watchlist_tickers(db: aiosqlite.Connection, user_id: str = "default") -> list[str]:
    """Get list of ticker symbols for a user's watchlist."""
    async with db.execute(
        "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at",
        (user_id,),
    ) as cursor:
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup")` | `lifespan` context manager | FastAPI 0.93+ (2023) | Startup/shutdown paired together; cleaner resource management |
| Synchronous sqlite3 in async app | `aiosqlite` async wrapper | Stable since 2020 | Non-blocking DB access on async event loop |
| Module-level global state | `app.state` via lifespan | FastAPI best practice since lifespan | Testable, no import-time side effects |

**Deprecated/outdated:**
- `@app.on_event("startup")` / `@app.on_event("shutdown")` -- use lifespan instead
- `databases` package -- maintenance stalled, prefer `aiosqlite` for SQLite

## Open Questions

1. **Database path configuration**
   - What we know: PLAN.md says `db/finally.db`, Docker volume mounts at `/app/db`
   - What's unclear: Should the path be configurable via env var or hardcoded?
   - Recommendation: Use a constant `DB_PATH = "db/finally.db"` in `main.py`, overridable by env var `DB_PATH` for flexibility. Ensure `db/` directory exists before connecting.

2. **Stream router inclusion timing**
   - What we know: `create_stream_router(cache)` returns an APIRouter that needs `app.include_router()`
   - What's unclear: Whether `include_router` must happen before `yield` in lifespan or can be done at module level
   - Recommendation: Include the router at module level (before `app.mount` for static files) since the router object is created via factory. The `PriceCache` reference is captured in the closure, so it must be created before the router factory is called. This means the stream router should be created and included inside the lifespan or the cache must be created before app construction. The simplest approach: create the stream router inside lifespan startup, but note FastAPI does not support `include_router` inside lifespan. Instead, create PriceCache at module level or use a two-step approach where the cache is pre-created and the router is set up at import time, then the source is started in lifespan. **Recommended:** Follow the existing pattern -- create PriceCache at module level, create the stream router at module level, start the data source in lifespan.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ with pytest-asyncio 0.24+ |
| Config file | `backend/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd backend && uv run --extra dev pytest tests/ -x -q` |
| Full suite command | `cd backend && uv run --extra dev pytest tests/ --cov=app -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DB-01 | Schema auto-creates on first run | unit | `cd backend && uv run --extra dev pytest tests/test_db_init.py::test_schema_creates_tables -x` | Wave 0 |
| DB-01 | Seed data inserted on first run | unit | `cd backend && uv run --extra dev pytest tests/test_db_init.py::test_seed_data_inserted -x` | Wave 0 |
| DB-01 | Idempotent -- second init is no-op | unit | `cd backend && uv run --extra dev pytest tests/test_db_init.py::test_init_idempotent -x` | Wave 0 |
| DB-02 | Default user has $10k balance | unit | `cd backend && uv run --extra dev pytest tests/test_db_init.py::test_default_user_balance -x` | Wave 0 |
| DB-03 | Lifespan starts and stops cleanly | integration | `cd backend && uv run --extra dev pytest tests/test_app.py::test_lifespan -x` | Wave 0 |
| DB-04 | Market data wired and streaming | integration | `cd backend && uv run --extra dev pytest tests/test_app.py::test_sse_stream -x` | Wave 0 |
| DB-05 | Health check returns 200 with JSON | integration | `cd backend && uv run --extra dev pytest tests/test_app.py::test_health_check -x` | Wave 0 |
| DB-06 | Static files served at root | integration | `cd backend && uv run --extra dev pytest tests/test_app.py::test_static_serving -x` | Wave 0 |
| WL-05 | 10 default tickers seeded | unit | `cd backend && uv run --extra dev pytest tests/test_db_init.py::test_watchlist_seed -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && uv run --extra dev pytest tests/ -x -q`
- **Per wave merge:** `cd backend && uv run --extra dev pytest tests/ --cov=app -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_db_init.py` -- covers DB-01, DB-02, WL-05 (schema creation, seed data, idempotency)
- [ ] `backend/tests/test_app.py` -- covers DB-03, DB-04, DB-05, DB-06 (lifespan, SSE, health, static files)
- [ ] Framework install: `cd backend && uv add aiosqlite` -- aiosqlite not yet in pyproject.toml
- [ ] `backend/tests/conftest.py` -- may need shared fixtures for test database (in-memory `:memory:` or temp file)

## Sources

### Primary (HIGH confidence)
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/) -- lifespan pattern, app.state usage
- [aiosqlite API Reference](https://aiosqlite.omnilib.dev/en/stable/api.html) -- connect(), execute(), executescript(), row_factory
- [aiosqlite GitHub](https://github.com/omnilib/aiosqlite) -- latest version 0.22.1, Python 3.9+ compatible
- `planning/PLAN.md` -- database schema (Section 7), API endpoints (Section 8), architecture (Section 3)
- `planning/MARKET_DATA_SUMMARY.md` -- complete market data subsystem API and usage patterns
- `backend/CLAUDE.md` -- existing code conventions and test commands
- Existing code: `backend/app/market/` -- 8 modules, established patterns (strategy, factory, DI)

### Secondary (MEDIUM confidence)
- [FastAPI StaticFiles](https://fastapi.tiangolo.com/tutorial/static-files/) -- StaticFiles mount pattern with html=True
- `.planning/research/PITFALLS.md` -- SQLite async blocking, concurrent write contention, static file mount order
- `.planning/research/STACK.md` -- aiosqlite recommendation
- `.planning/research/ARCHITECTURE.md` -- component boundaries, data flow, build order

### Tertiary (LOW confidence)
- None -- all findings verified against official documentation or existing code.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- aiosqlite is the clear choice; FastAPI already installed; no alternative needed
- Architecture: HIGH -- lifespan pattern is well-documented; market data subsystem already exists with clear API
- Pitfalls: HIGH -- SQLite async, mount order, and executescript behavior are well-documented gotchas

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (stable domain -- SQLite, FastAPI lifespan patterns are mature)
