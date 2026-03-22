# Technology Stack

**Analysis Date:** 2026-03-21

## Languages

**Primary:**
- Python 3.12+ - Backend API, market data subsystem, LLM integration (`backend/`)
- TypeScript - Frontend application (`frontend/`) — not yet implemented

**Secondary:**
- SQL - SQLite schema and seed data (`backend/db/`) — not yet implemented

## Runtime

**Environment:**
- Python 3.12 (minimum, enforced in `backend/pyproject.toml` via `requires-python = ">=3.12"`)
- Node.js 20 (planned for frontend build stage in Dockerfile)

**Package Manager:**
- Python: `uv` — lockfile at `backend/uv.lock` (committed, revision 3)
- JavaScript: Not yet present (frontend not yet scaffolded)

**Lockfile:**
- `backend/uv.lock` — present and committed; full reproducible resolution

## Frameworks

**Core:**
- FastAPI 0.128.7 — HTTP API server and SSE streaming (`backend/app/`)
- Starlette 0.52.1 — Underlying ASGI framework (used by FastAPI)
- Uvicorn 0.40.0 with standard extras — ASGI server (uvloop, watchfiles, websockets included)

**Frontend (planned, not yet implemented):**
- Next.js with TypeScript — static export (`output: 'export'`), served by FastAPI

**Testing:**
- pytest 9.0.2 — Test runner (`backend/tests/`)
- pytest-asyncio 1.3.0 — Async test support; `asyncio_mode = "auto"` configured
- pytest-cov 7.0.0 — Coverage reporting

**Build/Dev:**
- Ruff 0.15.0 — Linting and formatting; `line-length = 100`, targets Python 3.12
- hatchling — Build backend for the Python package

## Key Dependencies

**Critical:**
- `fastapi>=0.115.0` (resolved: 0.128.7) — REST API and SSE endpoints
- `uvicorn[standard]>=0.32.0` (resolved: 0.40.0) — Production ASGI server with uvloop
- `numpy>=2.0.0` (resolved: 2.4.2) — GBM simulator: Cholesky decomposition, correlated random normal draws
- `massive>=1.0.0` (resolved: 2.2.0) — Polygon.io REST client for real market data (`backend/app/market/massive_client.py`)
- `rich>=13.0.0` (resolved: 14.3.2) — Terminal demo dashboard (`backend/market_data_demo.py`)

**Infrastructure:**
- `pydantic 2.12.5` — Request/response validation (pulled in by FastAPI)
- `python-dotenv 1.2.1` — `.env` file loading
- `anyio 4.12.1` — Async primitives

**Planned (not yet installed):**
- LiteLLM — LLM integration via OpenRouter (per PLAN.md section 9; not yet in pyproject.toml)
- SQLite client — Database access (Python stdlib `sqlite3` or `aiosqlite`)

## Configuration

**Environment:**
- Configuration via `.env` file at project root (gitignored)
- `MASSIVE_API_KEY` — Optional; selects real market data vs. GBM simulator
- `OPENROUTER_API_KEY` — Required for LLM chat functionality
- `LLM_MOCK` — Set to `"true"` for deterministic mock LLM responses in tests
- Backend reads env vars at runtime; factory in `backend/app/market/factory.py` reads `MASSIVE_API_KEY` via `os.environ`

**Build:**
- `backend/pyproject.toml` — Python project definition, pytest config, ruff config, coverage config
- `backend/uv.lock` — Pinned dependency tree
- Dockerfile (planned, not yet present) — Multi-stage: Node 20 for frontend build → Python 3.12 for runtime

## Platform Requirements

**Development:**
- Python 3.12+
- `uv` package manager
- Run from `backend/`: `uv sync --extra dev`
- Test: `uv run --extra dev pytest -v`
- Lint: `uv run --extra dev ruff check app/ tests/`

**Production:**
- Docker container, port 8000
- Volume mount for SQLite persistence: `docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally`
- Target platforms: AWS App Runner, Render, or any OCI-compatible container platform

---

*Stack analysis: 2026-03-21*
