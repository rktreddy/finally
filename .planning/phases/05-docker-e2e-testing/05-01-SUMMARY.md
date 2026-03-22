---
phase: 05-docker-e2e-testing
plan: 01
subsystem: infra
tags: [docker, dockerfile, multi-stage-build, docker-compose, shell-scripts, powershell]

# Dependency graph
requires:
  - phase: 04-frontend-terminal
    provides: "Next.js static export in frontend/out/ and FastAPI app serving it"
provides:
  - "Multi-stage Dockerfile building frontend and backend into single container"
  - "docker-compose.yml for single-command startup"
  - "Start/stop scripts for macOS/Linux and Windows"
  - ".env.example documenting all environment variables"
  - ".dockerignore for clean build context"
affects: [05-02-PLAN]

# Tech tracking
tech-stack:
  added: [docker, docker-compose]
  patterns: [multi-stage-build, volume-mount-persistence]

key-files:
  created:
    - Dockerfile
    - .dockerignore
    - .env.example
    - docker-compose.yml
    - db/.gitkeep
    - scripts/start_mac.sh
    - scripts/stop_mac.sh
    - scripts/start_windows.ps1
    - scripts/stop_windows.ps1
  modified: []

key-decisions:
  - "DB_PATH=/app/db/finally.db with volume at /app/db for SQLite persistence across restarts"
  - "Frontend output at /app/frontend/out aligned with main.py Path resolution logic"

patterns-established:
  - "Container naming: container=finally, image=finally, volume=finally-data"
  - "Scripts use docker run directly (not compose) for explicit control over build/run lifecycle"

requirements-completed: [INF-01, INF-02, INF-03, INF-04, INF-05]

# Metrics
duration: 2min
completed: 2026-03-22
---

# Phase 5 Plan 1: Docker Infrastructure Summary

**Multi-stage Dockerfile (Node 20 + Python 3.12), docker-compose.yml, and platform start/stop scripts for single-container deployment on port 8000**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-22T16:06:54Z
- **Completed:** 2026-03-22T16:08:47Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Multi-stage Dockerfile: Node 20 builds frontend static export, Python 3.12 runtime serves everything on port 8000
- docker-compose.yml wraps the container with volume mount and env file for single-command startup
- Cross-platform scripts: bash for macOS/Linux, PowerShell for Windows, all idempotent

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Dockerfile, .dockerignore, and .env.example** - `1c95fd5` (chore)
2. **Task 2: Create docker-compose.yml, start/stop scripts, and db/.gitkeep** - `58428cf` (chore)

## Files Created/Modified
- `Dockerfile` - Multi-stage build: Node 20 frontend, Python 3.12 runtime, uvicorn CMD
- `.dockerignore` - Excludes dev artifacts, planning docs, node_modules from build context
- `.env.example` - Documents OPENROUTER_API_KEY, MASSIVE_API_KEY, LLM_MOCK
- `docker-compose.yml` - Single service with finally-data volume, port 8000, env_file
- `db/.gitkeep` - Placeholder for runtime volume mount directory
- `scripts/start_mac.sh` - Builds image and runs container with volume, port, env config
- `scripts/stop_mac.sh` - Stops container, preserves data volume
- `scripts/start_windows.ps1` - PowerShell equivalent of start_mac.sh
- `scripts/stop_windows.ps1` - PowerShell equivalent of stop_mac.sh

## Decisions Made
- DB_PATH set to /app/db/finally.db with volume mount at /app/db, keeping SQLite data persistent across container restarts
- Frontend build output copied to /app/frontend/out, which aligns exactly with main.py's `Path(__file__).resolve().parent.parent.parent / "frontend" / "out"` resolution
- Used `npm ci` in Dockerfile (lockfile exists) for reproducible frontend builds
- Scripts use `docker run` directly rather than docker-compose for explicit lifecycle control

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Docker infrastructure complete, ready for E2E testing in Plan 05-02
- Container can be built and run with `docker compose up` or `./scripts/start_mac.sh`
- E2E tests will use docker-compose.test.yml to spin up the app container with Playwright

## Self-Check: PASSED

All 9 files verified present. Both task commits (1c95fd5, 58428cf) verified in git log.

---
*Phase: 05-docker-e2e-testing*
*Completed: 2026-03-22*
