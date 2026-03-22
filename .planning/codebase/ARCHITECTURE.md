# Architecture

**Analysis Date:** 2026-03-21

## Pattern Overview

**Overall:** Single-container, layered monolith with strategy pattern for market data.

**Key Characteristics:**
- FastAPI backend serves both REST/SSE API and the static Next.js frontend export — single origin, single port (8000)
- Market data subsystem uses the Strategy pattern: `MarketDataSource` ABC with two concrete implementations (`SimulatorDataSource`, `MassiveDataSource`), selected at startup via factory
- Shared in-memory `PriceCache` decouples producers (data sources) from consumers (SSE streaming, portfolio valuation, trade execution)
- SQLite database with lazy initialization — schema + seed data created on first run, no migration step required
- Frontend is a static Next.js export; no SSR. All API calls to same-origin `/api/*`

## Layers

**Market Data Layer:**
- Purpose: Produce live price updates for all tracked tickers
- Location: `backend/app/market/`
- Contains: Abstract interface, GBM simulator, Massive REST client, shared cache, SSE streaming endpoint
- Depends on: Nothing internal (standalone subsystem)
- Used by: SSE route, portfolio valuation, trade execution

**API Routes Layer (planned):**
- Purpose: Handle REST requests for portfolio, watchlist, chat
- Location: `backend/app/routes/` (directory exists, source files not yet implemented)
- Contains: FastAPI routers for portfolio, watchlist, chat, health
- Depends on: Database layer, Market Data layer (for current prices)
- Used by: Frontend via HTTP

**Database Layer (planned):**
- Purpose: Persist user state — profile, watchlist, positions, trades, portfolio snapshots, chat history
- Location: `backend/app/db/` (directory exists, source files not yet implemented)
- Contains: Connection management, schema initialization, repository functions
- Depends on: SQLite (file at `/app/db/finally.db` inside container)
- Used by: API routes layer

**LLM Integration Layer (planned):**
- Purpose: Handle chat messages — context assembly, LLM call, structured output parsing, trade auto-execution
- Location: `backend/app/llm/` (directory exists, source files not yet implemented)
- Contains: LiteLLM client, prompt builder, mock responses, output models
- Depends on: Database layer (history, portfolio context), Market Data layer (live prices), API routes layer (trade execution)
- Used by: Chat route

**Frontend Layer (planned):**
- Purpose: Provide the trading terminal UI
- Location: `frontend/` (directory exists, empty — not yet implemented)
- Contains: Next.js TypeScript SPA with static export
- Depends on: Backend API via `/api/*` (same-origin)
- Used by: End user browser

## Data Flow

**Live Price Updates:**

1. Background task (`SimulatorDataSource._run_loop` or `MassiveDataSource._poll_loop`) runs continuously
2. Task calls `GBMSimulator.step()` (simulator) or `RESTClient.get_snapshot_all()` (Massive) every 500ms / 15s
3. Results written to `PriceCache` via `cache.update(ticker, price)` — increments `cache.version`
4. SSE endpoint (`GET /api/stream/prices`) polls cache version every 500ms
5. On version change, serializes all `PriceUpdate` objects via `to_dict()` and yields SSE event
6. Browser `EventSource` receives event, dispatches to React components for price flash and sparkline update

**Market Data Source Selection:**
1. App starts, reads `MASSIVE_API_KEY` from environment
2. `create_market_data_source(cache)` returns `MassiveDataSource` if key present, else `SimulatorDataSource`
3. Source started with initial tickers from database watchlist seed
4. Same interface (`add_ticker`, `remove_ticker`) used throughout app lifecycle

**Trade Execution (planned):**
1. User submits buy/sell via trade bar OR LLM requests trade
2. Route handler validates: sufficient cash (buy) / sufficient shares (sell)
3. Trade recorded in `trades` table, position updated in `positions` table, cash updated in `users_profile`
4. Portfolio snapshot recorded immediately
5. Response returned to frontend; portfolio views refresh

**Chat Flow (planned):**
1. User message arrives at `POST /api/chat`
2. Backend loads portfolio context (cash, positions + P&L, watchlist with prices)
3. Recent chat history loaded from `chat_messages`
4. LiteLLM call to OpenRouter (`openrouter/openai/gpt-oss-120b` via Cerebras) with structured output
5. Structured JSON response parsed: `{message, trades, watchlist_changes}`
6. Trades and watchlist changes auto-executed
7. Message + actions stored in `chat_messages`
8. Complete response returned to frontend

**State Management:**
- Server-side: SQLite for persistent state, `PriceCache` for ephemeral price state
- Client-side: React component state + EventSource connection for live prices, accumulated sparkline data

## Key Abstractions

**PriceUpdate:**
- Purpose: Immutable snapshot of one ticker's price at a point in time
- Location: `backend/app/market/models.py`
- Pattern: Frozen dataclass with computed properties (`change`, `change_percent`, `direction`) and `to_dict()` for JSON serialization

**PriceCache:**
- Purpose: Thread-safe single source of truth for current prices; decouples producers from consumers
- Location: `backend/app/market/cache.py`
- Pattern: Dict with threading.Lock + monotonic `version` counter for SSE change detection

**MarketDataSource (ABC):**
- Purpose: Common contract for all market data providers
- Location: `backend/app/market/interface.py`
- Pattern: Abstract Base Class with async lifecycle (`start/stop`) and dynamic membership (`add_ticker/remove_ticker`)

**GBMSimulator:**
- Purpose: Realistic price simulation using Geometric Brownian Motion with sector correlations
- Location: `backend/app/market/simulator.py`
- Pattern: Separate from `SimulatorDataSource` — pure simulation math isolated from async/cache concerns; Cholesky decomposition for correlated moves

## Entry Points

**Backend Application:**
- Location: Entry point to be created (planned as `backend/app/main.py` or similar)
- Triggers: `uvicorn` startup command from Dockerfile
- Responsibilities: Create `PriceCache`, call factory to get data source, register FastAPI routers, start background tasks on lifespan event

**SSE Stream Endpoint:**
- Location: `backend/app/market/stream.py` — `create_stream_router(price_cache)`
- Triggers: Browser `EventSource` connecting to `GET /api/stream/prices`
- Responsibilities: Poll cache version, serialize updates, yield SSE events

**Demo Script:**
- Location: `backend/market_data_demo.py`
- Triggers: `uv run market_data_demo.py` (development only)
- Responsibilities: Run the GBM simulator with a Rich terminal dashboard showing live prices

## Error Handling

**Strategy:** Defensive — errors logged and swallowed in background loops to prevent task termination.

**Patterns:**
- Simulator loop: `try/except Exception` with `logger.exception()` — step failures don't kill the loop
- Massive poller: `except Exception as e: logger.error(...)` — poll failures retry on next interval (handles 401, 429, network errors)
- Individual snapshot parse errors: `AttributeError/TypeError` caught per-ticker with `logger.warning()` — bad tickers don't fail the batch
- SSE generator: `asyncio.CancelledError` caught for clean disconnect logging

## Cross-Cutting Concerns

**Logging:** Python `logging` module with `logging.getLogger(__name__)` per module — standard structured logging
**Validation:** Input validation to be handled in API route layer (not yet implemented)
**Authentication:** None — single-user, no auth. All database rows use `user_id="default"` hardcoded, enabling future multi-user migration without schema changes.

---

*Architecture analysis: 2026-03-21*
