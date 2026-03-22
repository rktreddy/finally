---
phase: 05-docker-e2e-testing
verified: 2026-03-22T17:00:00Z
status: gaps_found
score: 8/10 must-haves verified
gaps:
  - truth: "E2E test infrastructure healthcheck will work when Docker is built"
    status: failed
    reason: "docker-compose.test.yml healthcheck uses curl, but python:3.12-slim does not include curl and the Dockerfile installs no system packages. The healthcheck will always fail/timeout when Docker is actually run."
    artifacts:
      - path: "test/docker-compose.test.yml"
        issue: "healthcheck uses CMD curl but curl is not available in python:3.12-slim"
      - path: "Dockerfile"
        issue: "No apt-get install of curl or wget; python:3.12-slim ships without either"
    missing:
      - "Either install curl in Dockerfile (RUN apt-get update && apt-get install -y --no-install-recommends curl) or change healthcheck to use python: CMD-SHELL python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')\""
  - truth: "chat.spec.ts trade.status === 'success' check renders correctly"
    status: partial
    reason: "The backend returns status='executed' for successful trades, but ChatPanel checks trade.status !== 'success'. This causes a red error indicator to appear alongside every successful auto-executed trade in the chat UI. The test assertion (/Bought 10 AAPL at $/) will still pass because the text renders regardless, but the UI shows a false failure indicator."
    artifacts:
      - path: "frontend/components/ChatPanel.tsx"
        issue: "Line 108: checks trade.status !== 'success' but backend returns 'executed' not 'success' for successful trades"
      - path: "backend/app/routes/chat.py"
        issue: "Lines 149-151: returns status='executed' for successful trades, not 'success'"
    missing:
      - "Either change backend chat.py to return status='success' for successful trades, or change ChatPanel to check trade.status !== 'executed' (i.e., !== the success value)"
human_verification:
  - test: "Run E2E tests against Docker container"
    expected: "All 4 test files pass: fresh-start, watchlist, trading, chat"
    why_human: "Docker daemon not available; tests require a built and running container on port 8000"
  - test: "Verify docker compose up starts app correctly"
    expected: "Container starts, http://localhost:8000 serves the frontend, /api/health returns 200"
    why_human: "Requires Docker daemon; cannot verify build correctness without running it"
---

# Phase 5: Docker & E2E Testing Verification Report

**Phase Goal:** The entire application ships as a single Docker container built from a multi-stage Dockerfile, with start/stop scripts and Playwright E2E tests validating all critical user workflows
**Verified:** 2026-03-22T17:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Running docker compose up builds and starts the container on port 8000 | ? UNCERTAIN | Dockerfile and docker-compose.yml are correct and wired; Docker daemon not available to run |
| 2 | SQLite database persists across container restarts via Docker volume | ✓ VERIFIED | Dockerfile sets `ENV DB_PATH=/app/db/finally.db`; docker-compose.yml maps `finally-data:/app/db`; backend reads DB_PATH at runtime |
| 3 | scripts/start_mac.sh builds image and starts container with correct volume, port, env config | ✓ VERIFIED | Script is executable, uses `-v finally-data:/app/db -p 8000:8000 --env-file .env` |
| 4 | scripts/stop_mac.sh stops the container without destroying persisted data | ✓ VERIFIED | Script calls `docker stop` then `docker rm` — no `docker volume rm`; confirmed |
| 5 | PowerShell scripts provide equivalent functionality on Windows | ✓ VERIFIED | start_windows.ps1 and stop_windows.ps1 are present and contain equivalent docker run/stop logic |
| 6 | E2E tests run against the Dockerized app with LLM_MOCK=true | ✓ VERIFIED | test/docker-compose.test.yml sets `LLM_MOCK=true` as environment variable |
| 7 | Fresh start test confirms default watchlist (10 tickers), $10k balance, and SSE price streaming | ✓ VERIFIED | fresh-start.spec.ts checks all 10 tickers (AAPL…NFLX), '$10,000.00', 'connected' status, span.tabular-nums |
| 8 | Watchlist test adds and removes a ticker, verifying UI updates | ✓ VERIFIED | watchlist.spec.ts adds 'DIS' via input+Add button; removes NFLX via aria-label='Remove NFLX' |
| 9 | Trading test buys shares (cash decreases, position appears) and sells shares (cash increases, position updates) | ✓ VERIFIED | trading.spec.ts uses test.describe.serial(); buy verifies /Bought 5 AAPL at $/ and position in table; sell verifies /Sold 5 AAPL at $/ and qty 5.00 |
| 10 | Chat test sends a message to mocked AI, receives response, and trade execution appears inline | ✓ VERIFIED | chat.spec.ts sends 'How is my portfolio doing?' → expects 'Your portfolio is well-diversified'; sends 'Please buy some AAPL' → expects "I've placed a buy order…" AND /Bought 10 AAPL at $/ |

**Score:** 8/10 truths verified (2 have issues: healthcheck infrastructure flaw, status field mismatch)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `Dockerfile` | Multi-stage build Node 20 + Python 3.12 | ✓ VERIFIED | FROM node:20-slim AS frontend-build; FROM python:3.12-slim AS runtime; EXPOSE 8000; CMD uvicorn app.main:app |
| `.dockerignore` | Excludes dev artifacts | ✓ VERIFIED | Excludes node_modules, __pycache__, .env, .git, .planning, .claude |
| `.env.example` | Documents env vars | ✓ VERIFIED | Contains OPENROUTER_API_KEY, MASSIVE_API_KEY, LLM_MOCK with comments |
| `docker-compose.yml` | Single-service wrapper | ✓ VERIFIED | Service 'app', container_name 'finally', image 'finally', ports 8000:8000, volume finally-data:/app/db, env_file .env |
| `db/.gitkeep` | Volume mount placeholder | ✓ VERIFIED | File exists |
| `scripts/start_mac.sh` | Executable macOS start script | ✓ VERIFIED | Executable; builds image if needed; docker run with -v, -p, --env-file |
| `scripts/stop_mac.sh` | Executable macOS stop script | ✓ VERIFIED | Executable; docker stop + docker rm, preserves volume |
| `scripts/start_windows.ps1` | Windows start script | ✓ VERIFIED | Present; equivalent docker run with volume, port, env-file |
| `scripts/stop_windows.ps1` | Windows stop script | ✓ VERIFIED | Present; stops container, preserves volume |
| `test/docker-compose.test.yml` | Test compose with LLM_MOCK | ✗ PARTIAL | LLM_MOCK=true present; builds from ../Dockerfile; healthcheck uses curl which is not installed in python:3.12-slim |
| `test/playwright.config.ts` | Playwright config targeting :8000 | ✓ VERIFIED | baseURL http://localhost:8000, testDir ./e2e, workers 1, sequential |
| `test/package.json` | Node project with @playwright/test | ✓ VERIFIED | @playwright/test ^1.49.0, typescript ^5 |
| `test/tsconfig.json` | TypeScript config | ✓ VERIFIED | ES2022 target, bundler resolution, strict mode |
| `test/e2e/fresh-start.spec.ts` | Fresh start E2E tests | ✓ VERIFIED | Tests all 10 tickers, $10,000.00 balance, connected status, tabular-nums price span |
| `test/e2e/watchlist.spec.ts` | Watchlist CRUD E2E tests | ✓ VERIFIED | Add DIS via input+button; remove NFLX via aria-label button |
| `test/e2e/trading.spec.ts` | Buy/sell E2E tests | ✓ VERIFIED | Serial execution; buy 5 AAPL, sell 5 AAPL with confirmation text and table assertions |
| `test/e2e/chat.spec.ts` | Chat E2E tests | ✓ VERIFIED | Generic message → diversification response; buy message → trade confirmation inline |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| Dockerfile | backend/app/main.py | `CMD uvicorn app.main:app` | ✓ WIRED | Dockerfile line 47: `CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]` |
| Dockerfile | frontend/out | `COPY --from=frontend-build /app/frontend/out /app/frontend/out` | ✓ WIRED | Path aligns with main.py's `Path(__file__).parent.parent.parent / "frontend" / "out"` = /app/frontend/out |
| Dockerfile | /app/db/finally.db | `ENV DB_PATH=/app/db/finally.db` + `mkdir -p /app/db` | ✓ WIRED | Backend reads DB_PATH env var; volume mounts at /app/db |
| docker-compose.yml | Dockerfile | `build: .` | ✓ WIRED | References project root Dockerfile |
| scripts/start_mac.sh | docker run | docker commands | ✓ WIRED | Calls docker build + docker run with all required flags |
| test/docker-compose.test.yml | Dockerfile | `build: context: .. dockerfile: Dockerfile` | ✓ WIRED | Correct relative path to project root Dockerfile |
| test/playwright.config.ts | test/docker-compose.test.yml | `baseURL: 'http://localhost:8000'` | ✓ WIRED | Tests target app container port mapped to host 8000 |
| test/docker-compose.test.yml | /api/health | healthcheck curl | ✗ NOT_WIRED | curl not available in python:3.12-slim; healthcheck will always fail |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| INF-01 | 05-01-PLAN.md | Multi-stage Dockerfile (Node 20 → Python 3.12) single container port 8000 | ✓ SATISFIED | Dockerfile confirmed: node:20-slim build stage, python:3.12-slim runtime, EXPOSE 8000 |
| INF-02 | 05-01-PLAN.md | Docker volume mount for SQLite persistence (db/finally.db) | ✓ SATISFIED | DB_PATH=/app/db/finally.db; finally-data:/app/db in both docker-compose.yml and start scripts |
| INF-03 | 05-01-PLAN.md | Start script for macOS/Linux (scripts/start_mac.sh) | ✓ SATISFIED | Executable; builds image, runs with volume+port+env-file; idempotent |
| INF-04 | 05-01-PLAN.md | Stop script for macOS/Linux (scripts/stop_mac.sh) | ✓ SATISFIED | Executable; stops and removes container; preserves volume |
| INF-05 | 05-01-PLAN.md | Start/stop scripts for Windows PowerShell | ✓ SATISFIED | scripts/start_windows.ps1 and stop_windows.ps1 present with equivalent logic |
| INF-06 | 05-02-PLAN.md | Playwright E2E tests with docker-compose.test.yml | ✓ SATISFIED | All infrastructure files exist; LLM_MOCK=true set; healthcheck has curl issue (blocker when running) |
| INF-07 | 05-02-PLAN.md | E2E: fresh start shows default watchlist, $10k balance, streaming prices | ✓ SATISFIED | fresh-start.spec.ts verifies all 10 tickers, $10,000.00, 'connected', price span |
| INF-08 | 05-02-PLAN.md | E2E: add/remove ticker from watchlist | ✓ SATISFIED | watchlist.spec.ts adds DIS, removes NFLX via aria-label |
| INF-09 | 05-02-PLAN.md | E2E: buy shares — cash decreases, position appears | ✓ SATISFIED | trading.spec.ts buys 5 AAPL, verifies feedback text and position in table |
| INF-10 | 05-02-PLAN.md | E2E: sell shares — cash increases, position updates | ✓ SATISFIED | trading.spec.ts sells 5 AAPL, verifies feedback text and qty 5.00 in table |
| INF-11 | 05-02-PLAN.md | E2E: AI chat (mocked) — send message, receive response, trade execution inline | ✓ SATISFIED | chat.spec.ts verifies mock response text and 'Bought 10 AAPL at $' inline |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| test/docker-compose.test.yml | 12 | `CMD curl -f http://localhost:8000/api/health` | 🛑 Blocker | curl not installed in python:3.12-slim; healthcheck always fails, `--wait` flag will timeout when E2E tests are started |
| frontend/components/ChatPanel.tsx | 108 | `trade.status !== "success"` but API returns `"executed"` | ⚠️ Warning | False error indicator on every successful AI-executed trade; cosmetic but misleading; E2E chat test still passes |

### Human Verification Required

### 1. Docker Build and Run

**Test:** Run `docker compose up --build` from project root
**Expected:** Container builds (both stages complete), starts on port 8000, `http://localhost:8000` serves the frontend UI, `http://localhost:8000/api/health` returns 200
**Why human:** Docker daemon not available in verification environment; cannot verify build output

### 2. E2E Test Suite Execution

**Test:** `cd test && docker compose -f docker-compose.test.yml up -d --wait && npm test`
**Expected:** All 4 Playwright spec files pass (after curl healthcheck issue is fixed)
**Why human:** Requires Docker daemon and running container; browser automation cannot be verified statically

### 3. Script Idempotency

**Test:** Run `./scripts/start_mac.sh` twice; run `./scripts/stop_mac.sh` twice
**Expected:** No errors on second invocation of either script
**Why human:** Requires Docker daemon to test actual idempotency behavior

### Gaps Summary

Two gaps found:

**Gap 1 (Blocker): Healthcheck uses curl, which is not installed in the runtime image.**

The `test/docker-compose.test.yml` healthcheck specifies `CMD curl -f http://localhost:8000/api/health`. The runtime image is `python:3.12-slim`, which does not include curl. The Dockerfile performs no system package installation (`apt-get`). When E2E tests are run with `docker compose -f docker-compose.test.yml up -d --wait`, the healthcheck will always report unhealthy, causing the `--wait` to timeout and blocking test execution.

Fix option A — install curl in Dockerfile runtime stage:
```
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
```

Fix option B — change healthcheck to use Python (zero additional dependencies):
```yaml
healthcheck:
  test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')\""]
```

**Gap 2 (Warning): Trade status mismatch between backend and frontend.**

`backend/app/routes/chat.py` returns `status="executed"` for successful auto-executed trades. `frontend/components/ChatPanel.tsx` renders a red error indicator when `trade.status !== "success"`. Since "executed" !== "success", every successful AI trade will show a red error badge. The Playwright test for inline trade confirmation (`/Bought 10 AAPL at $/`) will still pass because the confirmation text renders regardless, but the UI presents a false failure state to users.

Fix: change `chat.py` line 151 to `"status": "success"` (and line 197), or change `ChatPanel.tsx` line 108 to check `trade.status === "failed"` instead.

---

_Verified: 2026-03-22T17:00:00Z_
_Verifier: Claude (gsd-verifier)_
