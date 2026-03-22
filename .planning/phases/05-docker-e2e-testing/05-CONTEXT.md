# Phase 5: Docker & E2E Testing - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

The entire application ships as a single Docker container built from a multi-stage Dockerfile, with start/stop scripts and Playwright E2E tests validating all critical user workflows. This phase delivers the Dockerfile, convenience scripts, docker-compose files, and E2E test suite.

</domain>

<decisions>
## Implementation Decisions

### Dockerfile
- **D-01:** Multi-stage build: Stage 1 is Node 20 slim for frontend build (`npm ci && npm run build`), Stage 2 is Python 3.12 slim for runtime.
- **D-02:** Stage 2 installs `uv`, copies `backend/`, runs `uv sync`, copies frontend build output from Stage 1 into a location FastAPI can serve.
- **D-03:** Expose port 8000. CMD: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- **D-04:** The frontend/out/ static export is copied into the container where `backend/app/main.py` expects it (the static files mount path).
- **D-05:** SQLite database at `/app/db/finally.db` inside the container, persisted via Docker volume mount.

### Start/Stop Scripts
- **D-06:** `scripts/start_mac.sh` builds the Docker image (if not built or `--build` flag), runs the container with volume mount, port mapping, and `.env` file. Prints the URL. Idempotent.
- **D-07:** `scripts/stop_mac.sh` stops and removes the container. Does NOT remove the volume (data persists). Idempotent.
- **D-08:** `scripts/start_windows.ps1` and `scripts/stop_windows.ps1` — PowerShell equivalents.
- **D-09:** Container name: `finally`. Image name: `finally`. Volume name: `finally-data`.

### Docker Compose
- **D-10:** `docker-compose.yml` at project root as convenience wrapper for the single container. Same config as the scripts.
- **D-11:** `test/docker-compose.test.yml` for E2E testing — spins up the app container plus a Playwright container. Uses `LLM_MOCK=true`.

### E2E Tests
- **D-12:** Playwright tests in `test/` directory. All tests run against the Dockerized app with `LLM_MOCK=true`.
- **D-13:** Test scenarios:
  - Fresh start: default watchlist (10 tickers), $10k balance, prices streaming via SSE
  - Watchlist: add and remove a ticker
  - Trading: buy shares (cash decreases, position appears), sell shares (cash increases, position updates)
  - AI chat (mocked): send message, receive response, trade execution appears inline
- **D-14:** Playwright config targets `http://localhost:8000` (the Docker container).

### .env.example
- **D-15:** Commit `.env.example` with all environment variables documented (OPENROUTER_API_KEY, MASSIVE_API_KEY, LLM_MOCK). The actual `.env` is gitignored.

### Claude's Discretion
- Exact Playwright test selectors and assertions
- Docker build optimization (layer caching, .dockerignore)
- Whether to use playwright/docker image or install Playwright locally for tests
- Exact script output formatting

</decisions>

<specifics>
## Specific Ideas

- Scripts should be dead simple — one command to start, one to stop
- E2E tests prove the whole system works end-to-end in the container
- The container should "just work" with `docker run -p 8000:8000 --env-file .env finally`

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Docker & Deployment Spec
- `planning/PLAN.md` §11 — Docker & Deployment: multi-stage Dockerfile, volume mount, start/stop scripts
- `planning/PLAN.md` §4 — Directory structure: scripts/, test/, db/

### Testing Spec
- `planning/PLAN.md` §12 — Testing Strategy: E2E test scenarios, docker-compose.test.yml, LLM_MOCK

### Environment
- `planning/PLAN.md` §5 — Environment variables

### Prior Phase Integration
- `backend/app/main.py` — Static files mount path (needs to match Dockerfile COPY destination)
- `frontend/next.config.ts` — Static export config (`output: 'export'`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/main.py` — Already serves static files; path may need alignment with Docker COPY
- `frontend/` — Complete Next.js project, builds with `npm run build` to `frontend/out/`
- `backend/pyproject.toml` — Python project with uv lockfile

### Established Patterns
- `LLM_MOCK=true` env var for deterministic mock responses (already implemented in Phase 3)
- `DB_PATH` env var for database location (already used in tests)
- `.env` file at project root (already gitignored)

### Integration Points
- Dockerfile must align frontend output path with FastAPI static mount
- Docker volume mount at `/app/db` for SQLite persistence
- E2E tests need the container running with `LLM_MOCK=true`

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-docker-e2e-testing*
*Context gathered: 2026-03-22*
