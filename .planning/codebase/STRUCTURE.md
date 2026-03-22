# Codebase Structure

**Analysis Date:** 2026-03-21

## Directory Layout

```
finally/                          # Project root
├── backend/                      # FastAPI uv project (Python 3.12)
│   ├── app/                      # Python package — application code
│   │   ├── __init__.py           # Package marker
│   │   ├── market/               # Market data subsystem (COMPLETE)
│   │   │   ├── __init__.py       # Public API exports
│   │   │   ├── models.py         # PriceUpdate dataclass
│   │   │   ├── interface.py      # MarketDataSource ABC
│   │   │   ├── cache.py          # PriceCache (thread-safe)
│   │   │   ├── factory.py        # create_market_data_source()
│   │   │   ├── simulator.py      # GBMSimulator + SimulatorDataSource
│   │   │   ├── massive_client.py # MassiveDataSource (Polygon.io)
│   │   │   ├── seed_prices.py    # Default tickers, prices, GBM params
│   │   │   └── stream.py         # create_stream_router() SSE factory
│   │   ├── db/                   # Database layer (directory only — NOT YET IMPLEMENTED)
│   │   ├── routes/               # API route handlers (directory only — NOT YET IMPLEMENTED)
│   │   └── llm/                  # LLM integration (directory only — NOT YET IMPLEMENTED)
│   ├── tests/                    # pytest test suite
│   │   ├── __init__.py
│   │   ├── conftest.py           # Shared fixtures
│   │   └── market/               # Market data tests (73 tests, all passing)
│   │       ├── __init__.py
│   │       ├── test_models.py
│   │       ├── test_cache.py
│   │       ├── test_simulator.py
│   │       ├── test_simulator_source.py
│   │       ├── test_factory.py
│   │       └── test_massive.py
│   ├── market_data_demo.py       # Rich terminal demo (development only)
│   ├── pyproject.toml            # uv project config, deps, tool config
│   ├── uv.lock                   # Lockfile (committed)
│   └── CLAUDE.md                 # Backend developer guide
├── frontend/                     # Next.js TypeScript project (EMPTY — NOT YET IMPLEMENTED)
├── planning/                     # Project-wide documentation
│   ├── PLAN.md                   # Full project specification
│   ├── MARKET_DATA_SUMMARY.md    # Summary of completed market data work
│   └── archive/                  # Archived planning documents
├── test/                         # E2E tests (Playwright — NOT YET IMPLEMENTED)
│   └── node_modules/             # Playwright installed but no test files yet
├── db/                           # Runtime volume mount target
│   └── .gitkeep                  # Directory exists; finally.db created at runtime
├── .planning/                    # GSD tooling documents
│   └── codebase/                 # Codebase analysis documents
├── .claude/                      # Claude agent configuration
│   ├── agents/                   # Agent definitions
│   ├── commands/                 # GSD commands
│   └── skills/                   # Skill definitions (cerebras)
├── .github/                      # GitHub Actions workflows
├── CLAUDE.md                     # Root project instructions
└── README.md                     # Project overview
```

## Directory Purposes

**`backend/app/market/`:**
- Purpose: Complete market data subsystem — the only fully implemented backend module
- Contains: Abstract interface, GBM simulator, Massive REST client, price cache, SSE streaming, seed data
- Key files: `interface.py` (the contract), `cache.py` (shared state), `factory.py` (env-driven selection), `stream.py` (SSE endpoint)

**`backend/app/db/`:**
- Purpose: Database connection, schema initialization, repository functions
- Contains: Only `__pycache__` (compiled from previous work) — source files NOT present
- Note: Will house `connection.py`, `schema.py`, `repository.py` based on pycache evidence

**`backend/app/routes/`:**
- Purpose: FastAPI route handlers for portfolio, watchlist, chat, health endpoints
- Contains: Only `__pycache__` — source files NOT present
- Note: Will house `portfolio.py`, `watchlist.py`, `chat.py`, `health.py` based on pycache evidence

**`backend/app/llm/`:**
- Purpose: LLM integration — LiteLLM client, prompt construction, structured output parsing, mock mode
- Contains: Only `__pycache__` — source files NOT present
- Note: Will house `client.py`, `handler.py`, `models.py`, `mock.py`, `prompt.py` based on pycache evidence

**`backend/tests/market/`:**
- Purpose: pytest test suite for the market data subsystem
- Contains: 6 test modules, 73 tests total, 84% overall coverage

**`frontend/`:**
- Purpose: Next.js TypeScript SPA with static export — the trading terminal UI
- Contains: Empty directory — not yet implemented
- Will contain: `package.json`, `tsconfig.json`, `next.config.js`, `app/` or `src/` directory

**`test/`:**
- Purpose: Playwright E2E tests with `docker-compose.test.yml`
- Contains: Only `node_modules/` with Playwright installed — test files not yet written
- Runs with: `LLM_MOCK=true` environment variable

**`db/`:**
- Purpose: Docker volume mount target for SQLite persistence
- Contains: `.gitkeep` only; `finally.db` created at container runtime, gitignored
- Map: Project `db/` → `/app/db/` in container

**`planning/`:**
- Purpose: Shared agent documentation and project specification
- Key files: `PLAN.md` (full spec), `MARKET_DATA_SUMMARY.md` (completed work summary)

## Key File Locations

**Entry Points:**
- `backend/app/market/__init__.py`: Public API for the market data module
- `backend/market_data_demo.py`: Development demo script

**Configuration:**
- `backend/pyproject.toml`: Python deps, pytest config, ruff config, coverage config
- `backend/uv.lock`: Lockfile (committed, do not edit manually)

**Core Market Data Logic:**
- `backend/app/market/interface.py`: `MarketDataSource` ABC — the contract all data sources must satisfy
- `backend/app/market/cache.py`: `PriceCache` — the central hub between producers and consumers
- `backend/app/market/simulator.py`: `GBMSimulator` + `SimulatorDataSource` — default data source
- `backend/app/market/massive_client.py`: `MassiveDataSource` — real market data via Polygon.io

**Testing:**
- `backend/tests/conftest.py`: Shared pytest fixtures
- `backend/tests/market/`: All market data tests

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `massive_client.py`, `seed_prices.py`)
- Test files: `test_<module>.py` (e.g., `test_cache.py`, `test_simulator_source.py`)
- Directories: `snake_case` matching their domain (e.g., `market/`, `routes/`)

**Classes:**
- Data sources: `<Provider>DataSource` (e.g., `SimulatorDataSource`, `MassiveDataSource`)
- Data models: Noun (e.g., `PriceUpdate`, `PriceCache`)
- Abstract interfaces: Domain noun without suffix (e.g., `MarketDataSource`)
- Internal helpers: Prefixed with underscore if module-private (e.g., `GBMSimulator` is public; `_run_loop` is private method)

**Functions:**
- Factory functions: `create_<thing>` (e.g., `create_market_data_source`, `create_stream_router`)
- Private async methods: `_method_name` (e.g., `_run_loop`, `_poll_once`, `_fetch_snapshots`)
- Async lifecycle methods: `start`, `stop`, `add_ticker`, `remove_ticker`

## Where to Add New Code

**New API endpoint:**
- Implement router in: `backend/app/routes/<domain>.py` (e.g., `portfolio.py`, `watchlist.py`)
- Register in main FastAPI app (to be created)
- Tests in: `backend/tests/<domain>/test_<module>.py`

**New database operation:**
- Add to: `backend/app/db/repository.py` (to be created)
- Schema changes: `backend/app/db/schema.py` (to be created)

**New LLM feature:**
- Add to: `backend/app/llm/handler.py` (to be created)
- Add mock support in: `backend/app/llm/mock.py` (to be created)

**Frontend component:**
- Implementation: `frontend/src/components/<ComponentName>.tsx` (or equivalent Next.js structure)
- Tests: Co-located or in `frontend/src/__tests__/`

**New market data source:**
- Implement `MarketDataSource` ABC from `backend/app/market/interface.py`
- Register in `backend/app/market/factory.py`
- Tests in `backend/tests/market/test_<source>.py`

**E2E tests:**
- Add to: `test/` directory
- Infrastructure: `test/docker-compose.test.yml` (to be created)

## Special Directories

**`backend/.venv/`:**
- Purpose: Python virtual environment managed by uv
- Generated: Yes (by `uv sync`)
- Committed: No (gitignored)

**`db/`:**
- Purpose: Runtime SQLite database volume mount
- Generated: Yes (`finally.db` created at runtime)
- Committed: No (`finally.db` is gitignored; `.gitkeep` is committed)

**`test/node_modules/`:**
- Purpose: Playwright and E2E test dependencies
- Generated: Yes (by npm install)
- Committed: No (gitignored)

**`.planning/codebase/`:**
- Purpose: GSD codebase analysis documents consumed by plan and execute commands
- Generated: Yes (by `map-codebase` command)
- Committed: Yes

---

*Structure analysis: 2026-03-21*
