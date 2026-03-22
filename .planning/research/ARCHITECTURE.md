# Architecture Research: AI Trading Workstation

**Research Date:** 2026-03-21
**Focus:** How remaining components integrate with existing market data layer

## Current State

```
MarketDataSource (ABC)
├── SimulatorDataSource  →  GBM simulator
└── MassiveDataSource    →  Polygon.io REST poller
        │
        ▼
   PriceCache (thread-safe, in-memory)
        │
        └──→ SSE stream endpoint (/api/stream/prices)
```

## Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  FastAPI Application (main.py)                              │
│                                                             │
│  Lifespan:                                                  │
│  ├── startup: init DB, create PriceCache, start data source │
│  ├── startup: start portfolio snapshot background task      │
│  └── shutdown: stop data source, close DB                   │
│                                                             │
│  Routes:                                                    │
│  ├── /api/stream/prices  → SSE (existing stream.py)        │
│  ├── /api/health         → GET health check                │
│  ├── /api/portfolio      → GET portfolio state             │
│  ├── /api/portfolio/trade → POST execute trade             │
│  ├── /api/portfolio/history → GET snapshots                │
│  ├── /api/watchlist      → GET/POST/DELETE watchlist CRUD  │
│  ├── /api/chat           → POST chat message               │
│  └── /*                  → Static files (Next.js export)   │
│                                                             │
│  Shared State:                                              │
│  ├── PriceCache (in-memory, existing)                      │
│  ├── SQLite DB connection (aiosqlite)                      │
│  └── MarketDataSource (existing)                           │
└─────────────────────────────────────────────────────────────┘
```

## Component Boundaries

### 1. Database Layer (`backend/app/db/`)

**Boundary:** Owns all SQLite interaction. No other module touches the database directly.

**Interface:**
- `init_db(db_path)` → Create tables + seed if needed
- `get_db()` → Async context manager for connection
- Repository functions per domain: `watchlist_repo`, `portfolio_repo`, `trade_repo`, `chat_repo`, `snapshot_repo`

**Key Pattern:** Repository pattern — each domain gets a module with async functions that take a connection parameter.

```python
# backend/app/db/portfolio_repo.py
async def get_portfolio(db) -> dict:
    ...
async def update_position(db, ticker, quantity, avg_cost) -> None:
    ...
```

### 2. API Routes Layer (`backend/app/routes/`)

**Boundary:** HTTP request/response handling. Validates input, calls repositories, returns JSON.

**Modules:**
- `health.py` — `GET /api/health`
- `portfolio.py` — portfolio endpoints (uses portfolio_repo + price_cache for live P&L)
- `watchlist.py` — watchlist CRUD (uses watchlist_repo + market data source for add/remove)
- `trade.py` — trade execution (uses portfolio_repo + trade_repo + price_cache)
- `chat.py` — chat endpoint (uses LLM module + all repos for context)

**Key Pattern:** Routes receive `PriceCache` and `MarketDataSource` via FastAPI dependency injection (app.state).

### 3. LLM Module (`backend/app/llm/`)

**Boundary:** Owns all LLM interaction. Assembles context, calls LiteLLM, parses response.

**Modules:**
- `client.py` — LiteLLM call wrapper (real + mock mode)
- `prompts.py` — System prompt, context assembly
- `models.py` — Pydantic models for structured output schema
- `executor.py` — Auto-execute trades and watchlist changes from LLM response

**Data Flow:**
1. Chat route calls `assemble_context()` → gathers portfolio, positions, watchlist, prices, history
2. Calls `chat_completion()` → LiteLLM to OpenRouter
3. Parses structured JSON into Pydantic model
4. Calls `execute_actions()` → runs trades and watchlist changes
5. Stores message + actions in chat_messages table
6. Returns complete response to frontend

### 4. Frontend (`frontend/`)

**Boundary:** Self-contained Next.js app. Knows nothing about Python. Talks to `/api/*` only.

**Key Components:**
- `WatchlistPanel` — ticker grid with prices, sparklines, flash animations
- `ChartArea` — detail chart for selected ticker (lightweight-charts)
- `PortfolioHeatmap` — treemap visualization
- `PnLChart` — portfolio value over time (recharts)
- `PositionsTable` — tabular position view
- `TradeBar` — ticker/quantity input + buy/sell buttons
- `ChatPanel` — message list + input + inline trade confirmations
- `Header` — portfolio value, cash, connection status

**State Management:** React useState/useReducer + custom hooks for SSE connection, price accumulation, and API calls. No Redux/Zustand needed for single-page terminal.

### 5. App Entry Point (`backend/app/main.py`)

**Responsibility:** Wire everything together.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db = await init_db("db/finally.db")
    cache = PriceCache()
    source = create_market_data_source(cache)
    tickers = await get_watchlist_tickers(db)
    await source.start(tickers)
    # Start snapshot background task
    app.state.db = db
    app.state.cache = cache
    app.state.source = source
    yield
    # Shutdown
    await source.stop()
```

## Data Flow Diagrams

### Trade Execution
```
User clicks Buy → POST /api/portfolio/trade {ticker, qty, side}
  → Validate: enough cash (buy) / enough shares (sell)
  → Get current price from PriceCache
  → Update positions table (insert or update avg_cost)
  → Update cash balance
  → Insert trade record
  → Take portfolio snapshot
  → Return updated portfolio state
```

### Chat with AI
```
User sends message → POST /api/chat {message}
  → Load portfolio context (cash, positions + P&L, watchlist + prices)
  → Load recent chat history
  → Call LiteLLM with system prompt + context + history + message
  → Parse structured JSON response
  → For each trade in response: execute via trade logic
  → For each watchlist change: add/remove ticker
  → Store message + actions in chat_messages
  → Return {message, executed_trades, watchlist_changes}
```

## Suggested Build Order

```
Phase 1: Database + App Foundation
  → SQLite schema, lazy init, seed data
  → FastAPI main.py with lifespan
  → Health endpoint
  → Wire existing market data into app

Phase 2: Core API Routes
  → Watchlist CRUD (integrates with market data source)
  → Portfolio read (positions + live P&L from cache)
  → Trade execution
  → Portfolio snapshots (background task + post-trade)

Phase 3: LLM Integration
  → LiteLLM client (real + mock)
  → Context assembly + system prompt
  → Structured output parsing
  → Auto-execution of trades/watchlist changes
  → Chat message persistence

Phase 4: Frontend
  → Next.js scaffold + Tailwind dark theme
  → Layout shell (header, panels, grid)
  → SSE connection + price state management
  → Watchlist panel with flash animations + sparklines
  → Chart area (lightweight-charts)
  → Trade bar + portfolio views
  → Chat panel

Phase 5: Docker + E2E
  → Multi-stage Dockerfile
  → Start/stop scripts
  → Playwright E2E tests
```

**Rationale:** Each phase builds on the previous. Database first because everything depends on it. API routes before frontend so the frontend has real endpoints. LLM can be parallel with frontend since chat is the last panel wired up.

---
*Architecture research: 2026-03-21*
