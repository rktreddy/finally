# FinAlly Project - the Finance Ally

All project documentation is in the `planning` directory.

The key document is PLAN.md included in full below; the market data component has been completed and is summarized in the file `planning/MARKET_DATA_SUMMARY.md` with more details in the `planning/archive` folder. Consult these docs only when required. The remainder of the platform is still to be developed.

@planning/PLAN.md

<!-- GSD:project-start source:PROJECT.md -->
## Project

**FinAlly — AI Trading Workstation**

FinAlly (Finance Ally) is a visually stunning AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot. Single Docker container, single port, no auth — immediate experience on launch.

This is the capstone project for an agentic AI coding course, built entirely by coding agents.

**Core Value:** Users can watch live-streaming prices, trade a simulated portfolio, and chat with an AI assistant that can analyze positions and execute trades — all in a single, beautiful, Bloomberg-inspired terminal interface.

### Constraints

- **Single container:** Everything runs in one Docker container on port 8000 — no docker-compose for production
- **Static frontend:** Next.js must use `output: 'export'` — served as static files by FastAPI, no SSR
- **No CORS:** Frontend and API on same origin — no CORS configuration needed
- **Market orders only:** No limit orders, no order book, no partial fills — dramatically simpler portfolio math
- **SQLite only:** No Postgres, no database server — single file, zero config
- **uv for Python:** Not pip, not poetry — uv with lockfile
- **LiteLLM via OpenRouter:** Use cerebras-inference skill pattern for LLM calls
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.12+ - Backend API, market data subsystem, LLM integration (`backend/`)
- TypeScript - Frontend application (`frontend/`) — not yet implemented
- SQL - SQLite schema and seed data (`backend/db/`) — not yet implemented
## Runtime
- Python 3.12 (minimum, enforced in `backend/pyproject.toml` via `requires-python = ">=3.12"`)
- Node.js 20 (planned for frontend build stage in Dockerfile)
- Python: `uv` — lockfile at `backend/uv.lock` (committed, revision 3)
- JavaScript: Not yet present (frontend not yet scaffolded)
- `backend/uv.lock` — present and committed; full reproducible resolution
## Frameworks
- FastAPI 0.128.7 — HTTP API server and SSE streaming (`backend/app/`)
- Starlette 0.52.1 — Underlying ASGI framework (used by FastAPI)
- Uvicorn 0.40.0 with standard extras — ASGI server (uvloop, watchfiles, websockets included)
- Next.js with TypeScript — static export (`output: 'export'`), served by FastAPI
- pytest 9.0.2 — Test runner (`backend/tests/`)
- pytest-asyncio 1.3.0 — Async test support; `asyncio_mode = "auto"` configured
- pytest-cov 7.0.0 — Coverage reporting
- Ruff 0.15.0 — Linting and formatting; `line-length = 100`, targets Python 3.12
- hatchling — Build backend for the Python package
## Key Dependencies
- `fastapi>=0.115.0` (resolved: 0.128.7) — REST API and SSE endpoints
- `uvicorn[standard]>=0.32.0` (resolved: 0.40.0) — Production ASGI server with uvloop
- `numpy>=2.0.0` (resolved: 2.4.2) — GBM simulator: Cholesky decomposition, correlated random normal draws
- `massive>=1.0.0` (resolved: 2.2.0) — Polygon.io REST client for real market data (`backend/app/market/massive_client.py`)
- `rich>=13.0.0` (resolved: 14.3.2) — Terminal demo dashboard (`backend/market_data_demo.py`)
- `pydantic 2.12.5` — Request/response validation (pulled in by FastAPI)
- `python-dotenv 1.2.1` — `.env` file loading
- `anyio 4.12.1` — Async primitives
- LiteLLM — LLM integration via OpenRouter (per PLAN.md section 9; not yet in pyproject.toml)
- SQLite client — Database access (Python stdlib `sqlite3` or `aiosqlite`)
## Configuration
- Configuration via `.env` file at project root (gitignored)
- `MASSIVE_API_KEY` — Optional; selects real market data vs. GBM simulator
- `OPENROUTER_API_KEY` — Required for LLM chat functionality
- `LLM_MOCK` — Set to `"true"` for deterministic mock LLM responses in tests
- Backend reads env vars at runtime; factory in `backend/app/market/factory.py` reads `MASSIVE_API_KEY` via `os.environ`
- `backend/pyproject.toml` — Python project definition, pytest config, ruff config, coverage config
- `backend/uv.lock` — Pinned dependency tree
- Dockerfile (planned, not yet present) — Multi-stage: Node 20 for frontend build → Python 3.12 for runtime
## Platform Requirements
- Python 3.12+
- `uv` package manager
- Run from `backend/`: `uv sync --extra dev`
- Test: `uv run --extra dev pytest -v`
- Lint: `uv run --extra dev ruff check app/ tests/`
- Docker container, port 8000
- Volume mount for SQLite persistence: `docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally`
- Target platforms: AWS App Runner, Render, or any OCI-compatible container platform
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Context
## Naming Patterns
- Lowercase snake_case: `cache.py`, `massive_client.py`, `seed_prices.py`, `simulator.py`
- One primary class or concern per file, named to match the file: `cache.py` → `PriceCache`, `simulator.py` → `GBMSimulator` + `SimulatorDataSource`
- Abstract interfaces in a dedicated file: `interface.py`
- Factory functions in a dedicated file: `factory.py`
- `__init__.py` acts as a public API declaration (explicit `__all__`, re-exports only, no logic)
- PascalCase: `PriceCache`, `PriceUpdate`, `GBMSimulator`, `MarketDataSource`, `SimulatorDataSource`, `MassiveDataSource`
- snake_case: `create_market_data_source()`, `get_price()`, `add_ticker()`, `remove_ticker()`
- Private methods prefixed with single underscore: `_add_ticker_internal()`, `_rebuild_cholesky()`, `_poll_once()`, `_poll_loop()`, `_run_loop()`, `_generate_events()`
- Factory functions named `create_*`: `create_market_data_source()`, `create_stream_router()`
- snake_case: `price_cache`, `api_key`, `update_interval`, `poll_interval`
- Private instance attributes prefixed with underscore: `self._cache`, `self._task`, `self._tickers`, `self._client`, `self._cholesky`
- UPPER_SNAKE_CASE in module-level dicts and values: `SEED_PRICES`, `TICKER_PARAMS`, `DEFAULT_PARAMS`, `CORRELATION_GROUPS`, `INTRA_TECH_CORR`, `TSLA_CORR`
- Class-level constants in UPPER_SNAKE_CASE: `GBMSimulator.DEFAULT_DT`, `GBMSimulator.TRADING_SECONDS_PER_YEAR`
- Used throughout: `list[str]`, `dict[str, float]`, `float | None`, `asyncio.Task | None`, `np.ndarray | None`
- `from __future__ import annotations` used in every module with type hints to enable forward references
- Return types always annotated: `-> None`, `-> PriceUpdate`, `-> dict[str, float]`, `-> list[str]`
## Code Style
- `ruff` configured in `backend/pyproject.toml`
- Line length: 100 characters (`line-length = 100`)
- Target Python version: 3.12 (`target-version = "py312"`)
- Rule sets: `E` (pycodestyle errors), `F` (pyflakes), `I` (isort), `N` (naming), `W` (warnings)
- `E501` (line too long) is ignored — ruff formatter handles line wrapping
- Module-level docstrings on every file: `"""Data models for market data."""`
- Class-level docstrings explaining purpose and key design decisions
- Method docstrings for public API; private methods may have inline comments instead
- Docstrings use plain prose, not Sphinx/Google style
## Import Organization
- Placed first in every module that uses type hints, before all other imports
- Always use relative imports inside `app/market/`: `from .cache import PriceCache`, not `from app.market.cache import PriceCache`
- Each package exposes a clean public API through `__init__.py` with explicit `__all__`
- Example: `backend/app/market/__init__.py` re-exports `PriceUpdate`, `PriceCache`, `MarketDataSource`, `create_market_data_source`, `create_stream_router`
## Error Handling
- Background tasks (asyncio loops) use bare `except Exception` to prevent crashes, log with `logger.exception()` (which captures traceback) or `logger.error()`:
- External API calls catch specific exceptions first, fall back to broad `except Exception as e` with `logger.error()` and a comment explaining the non-raise decision:
- Task cancellation is handled explicitly using `asyncio.CancelledError`:
- Guard clauses check `is None` or truthiness before using optional attributes (`if self._sim:`, `if not self._tickers or not self._client:`)
- No-op behavior for invalid operations (add duplicate ticker, remove nonexistent ticker) is explicit and silent — no exceptions raised
## Logging
- Every module that produces log output creates a module-level logger:
- Log levels used:
- Log message format uses `%s` percent-style formatting (not f-strings): `logger.info("Started %d tickers", len(tickers))`
## Comments
- Used for non-obvious math: GBM formula explanation, `dt` calculation, rate limit guidance
- Used to explain design decisions: `# Don't re-raise — the loop will retry`, `# Seed the cache immediately`
- Used to mark internal section boundaries: `# --- Public API ---`, `# --- Internals ---`
- Docstrings for public API (classes and public methods)
- Inline `#` comments for implementation details within method bodies
## Function and Method Design
- Use keyword arguments for optional config with sensible defaults: `update_interval: float = 0.5`, `event_probability: float = 0.001`
- Dependency injection over globals — cache and config passed into constructors, never accessed via module-level globals
- Typed return annotations on all public methods
- Methods that mutate state return `None`; methods that query return typed values
- Convenience accessor methods (e.g., `get_price()` wrapping `get()`) are explicit and documented
## Module Design
- Each package has an explicit public API in `__init__.py` with `__all__`
- Internal implementation details (private classes, helpers) are not re-exported
- Abstract base classes defined in `interface.py` using `abc.ABC` and `@abstractmethod`
- Factory functions (`factory.py`) return the abstract type, hiding the concrete implementation
- Immutable value objects use `@dataclass(frozen=True, slots=True)`: `PriceUpdate`
- Computed properties implemented as `@property` on frozen dataclasses
- Shared mutable state (the price cache) protected with `threading.Lock`
- Async code uses `asyncio.to_thread()` to run blocking (synchronous) I/O calls without blocking the event loop
## Frontend Conventions
- Next.js with TypeScript (`output: 'export'` static mode)
- Tailwind CSS with a custom dark theme
- `EventSource` for SSE connection
- Canvas-based charting (Lightweight Charts or Recharts)
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- FastAPI backend serves both REST/SSE API and the static Next.js frontend export — single origin, single port (8000)
- Market data subsystem uses the Strategy pattern: `MarketDataSource` ABC with two concrete implementations (`SimulatorDataSource`, `MassiveDataSource`), selected at startup via factory
- Shared in-memory `PriceCache` decouples producers (data sources) from consumers (SSE streaming, portfolio valuation, trade execution)
- SQLite database with lazy initialization — schema + seed data created on first run, no migration step required
- Frontend is a static Next.js export; no SSR. All API calls to same-origin `/api/*`
## Layers
- Purpose: Produce live price updates for all tracked tickers
- Location: `backend/app/market/`
- Contains: Abstract interface, GBM simulator, Massive REST client, shared cache, SSE streaming endpoint
- Depends on: Nothing internal (standalone subsystem)
- Used by: SSE route, portfolio valuation, trade execution
- Purpose: Handle REST requests for portfolio, watchlist, chat
- Location: `backend/app/routes/` (directory exists, source files not yet implemented)
- Contains: FastAPI routers for portfolio, watchlist, chat, health
- Depends on: Database layer, Market Data layer (for current prices)
- Used by: Frontend via HTTP
- Purpose: Persist user state — profile, watchlist, positions, trades, portfolio snapshots, chat history
- Location: `backend/app/db/` (directory exists, source files not yet implemented)
- Contains: Connection management, schema initialization, repository functions
- Depends on: SQLite (file at `/app/db/finally.db` inside container)
- Used by: API routes layer
- Purpose: Handle chat messages — context assembly, LLM call, structured output parsing, trade auto-execution
- Location: `backend/app/llm/` (directory exists, source files not yet implemented)
- Contains: LiteLLM client, prompt builder, mock responses, output models
- Depends on: Database layer (history, portfolio context), Market Data layer (live prices), API routes layer (trade execution)
- Used by: Chat route
- Purpose: Provide the trading terminal UI
- Location: `frontend/` (directory exists, empty — not yet implemented)
- Contains: Next.js TypeScript SPA with static export
- Depends on: Backend API via `/api/*` (same-origin)
- Used by: End user browser
## Data Flow
- Server-side: SQLite for persistent state, `PriceCache` for ephemeral price state
- Client-side: React component state + EventSource connection for live prices, accumulated sparkline data
## Key Abstractions
- Purpose: Immutable snapshot of one ticker's price at a point in time
- Location: `backend/app/market/models.py`
- Pattern: Frozen dataclass with computed properties (`change`, `change_percent`, `direction`) and `to_dict()` for JSON serialization
- Purpose: Thread-safe single source of truth for current prices; decouples producers from consumers
- Location: `backend/app/market/cache.py`
- Pattern: Dict with threading.Lock + monotonic `version` counter for SSE change detection
- Purpose: Common contract for all market data providers
- Location: `backend/app/market/interface.py`
- Pattern: Abstract Base Class with async lifecycle (`start/stop`) and dynamic membership (`add_ticker/remove_ticker`)
- Purpose: Realistic price simulation using Geometric Brownian Motion with sector correlations
- Location: `backend/app/market/simulator.py`
- Pattern: Separate from `SimulatorDataSource` — pure simulation math isolated from async/cache concerns; Cholesky decomposition for correlated moves
## Entry Points
- Location: Entry point to be created (planned as `backend/app/main.py` or similar)
- Triggers: `uvicorn` startup command from Dockerfile
- Responsibilities: Create `PriceCache`, call factory to get data source, register FastAPI routers, start background tasks on lifespan event
- Location: `backend/app/market/stream.py` — `create_stream_router(price_cache)`
- Triggers: Browser `EventSource` connecting to `GET /api/stream/prices`
- Responsibilities: Poll cache version, serialize updates, yield SSE events
- Location: `backend/market_data_demo.py`
- Triggers: `uv run market_data_demo.py` (development only)
- Responsibilities: Run the GBM simulator with a Rich terminal dashboard showing live prices
## Error Handling
- Simulator loop: `try/except Exception` with `logger.exception()` — step failures don't kill the loop
- Massive poller: `except Exception as e: logger.error(...)` — poll failures retry on next interval (handles 401, 429, network errors)
- Individual snapshot parse errors: `AttributeError/TypeError` caught per-ticker with `logger.warning()` — bad tickers don't fail the batch
- SSE generator: `asyncio.CancelledError` caught for clean disconnect logging
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
