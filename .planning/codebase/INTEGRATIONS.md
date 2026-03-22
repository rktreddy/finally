# External Integrations

**Analysis Date:** 2026-03-21

## APIs & External Services

**Market Data:**
- Massive (Polygon.io wrapper) — Real-time US stock price snapshots via REST polling
  - SDK/Client: `massive` package v2.2.0 (`backend/app/market/massive_client.py`)
  - Auth: `MASSIVE_API_KEY` environment variable
  - Endpoint used: `GET /v2/snapshot/locale/us/markets/stocks/tickers` (all watched tickers in one call)
  - Rate limits: Free tier 5 req/min → poll every 15s; paid tiers 2-5s
  - Fallback: GBM simulator used automatically when `MASSIVE_API_KEY` is absent or empty
  - Implementation: `MassiveDataSource` in `backend/app/market/massive_client.py`

**LLM / AI:**
- OpenRouter → Cerebras inference → `openrouter/openai/gpt-oss-120b` model
  - SDK/Client: LiteLLM (planned; not yet in `backend/pyproject.toml`)
  - Auth: `OPENROUTER_API_KEY` environment variable
  - Pattern: Structured outputs (JSON schema); no token streaming — full response returned
  - Mock mode: `LLM_MOCK=true` returns deterministic responses without API calls
  - Implementation location: `backend/app/llm/` (directory exists, no Python files yet)

## Data Storage

**Databases:**
- SQLite — Primary and only data store
  - File location: `/app/db/finally.db` inside container; `db/finally.db` at project root
  - Connection: No env var — hardcoded path relative to container layout
  - Client: Python stdlib `sqlite3` (planned; no ORM identified yet)
  - Schema defined in `backend/app/db/` (directory exists, no files yet)
  - Lazy initialization: Backend creates schema and seeds default data on first startup
  - Tables: `users_profile`, `watchlist`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages`
  - All tables include `user_id TEXT DEFAULT "default"` for future multi-user support

**File Storage:**
- Local filesystem only (SQLite file on Docker volume `finally-data`)
- No object storage (S3, GCS, etc.) integrated

**Caching:**
- In-process in-memory only: `PriceCache` class (`backend/app/market/cache.py`)
  - Thread-safe via `threading.Lock`
  - Stores latest `PriceUpdate` per ticker
  - Version counter (`_version`) for SSE change detection
  - No Redis or external cache

## Authentication & Identity

**Auth Provider:**
- None — single-user application with no login/signup
- All database rows use hardcoded `user_id = "default"`
- No session tokens, cookies, or JWT

## Real-Time Data Delivery

**SSE (Server-Sent Events):**
- Endpoint: `GET /api/stream/prices`
  - Implementation: `backend/app/market/stream.py` — `create_stream_router()` factory
  - Protocol: `text/event-stream`, `Content-Type: text/event-stream`
  - Headers: `Cache-Control: no-cache`, `X-Accel-Buffering: no` (nginx-safe)
  - Client retry directive: `retry: 1000` (1 second auto-reconnect)
  - Payload format: `data: {ticker: {ticker, price, previous_price, timestamp, change, change_percent, direction}}\n\n`
  - Update cadence: ~500ms (version-change gated)

## Monitoring & Observability

**Error Tracking:**
- None — no Sentry, Datadog, etc.

**Logs:**
- Python `logging` module throughout `backend/app/market/`
- Log levels: `INFO` for lifecycle events, `DEBUG` for per-tick events, `WARNING` for skipped data, `ERROR` for poll failures
- No structured logging format enforced; output goes to stdout/stderr (container logs)

## CI/CD & Deployment

**Hosting:**
- Docker container, port 8000 (primary deployment model)
- Optional: AWS App Runner, Render, or any OCI-compatible platform

**CI Pipeline:**
- Not detected (no `.github/workflows/`, no CI config files present)

**Container:**
- Dockerfile not yet present (planned multi-stage: Node 20 → Python 3.12)
- `docker-compose.yml` planned (optional convenience wrapper)
- `test/` directory contains `node_modules` — likely Playwright E2E infrastructure in progress

## Environment Configuration

**Required env vars:**
- `OPENROUTER_API_KEY` — LLM chat functionality (required for chat features)

**Optional env vars:**
- `MASSIVE_API_KEY` — Real market data; omit to use GBM simulator
- `LLM_MOCK` — Set to `"true"` to disable real LLM calls (E2E tests / CI)

**Secrets location:**
- `.env` file at project root (gitignored per `.gitignore`)
- Loaded via `python-dotenv` at backend startup
- Passed to Docker container via `--env-file .env`

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- None detected

---

*Integration audit: 2026-03-21*
