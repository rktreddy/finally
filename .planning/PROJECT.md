# FinAlly — AI Trading Workstation

## What This Is

FinAlly (Finance Ally) is a visually stunning AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot. Single Docker container, single port, no auth — immediate experience on launch.

This is the capstone project for an agentic AI coding course, built entirely by coding agents.

## Core Value

Users can watch live-streaming prices, trade a simulated portfolio, and chat with an AI assistant that can analyze positions and execute trades — all in a single, beautiful, Bloomberg-inspired terminal interface.

## Requirements

### Validated

- ✓ Market data simulator (GBM with correlated moves, shock events) — existing
- ✓ Market data real API client (Massive/Polygon.io REST polling) — existing
- ✓ Strategy pattern: both data sources implement same ABC — existing
- ✓ Shared PriceCache (thread-safe, version-based change detection) — existing
- ✓ SSE streaming endpoint for price updates — existing
- ✓ Dynamic ticker add/remove on data sources — existing
- ✓ Backend project structure with uv, FastAPI, pytest, ruff — existing

### Active

- [ ] SQLite database with lazy initialization (schema + seed on first run)
- [ ] User profile management (cash balance tracking)
- [ ] Watchlist CRUD (add/remove tickers, persist to database)
- [ ] Portfolio management (positions, avg cost, P&L calculations)
- [ ] Trade execution (market orders, validation, instant fill)
- [ ] Trade history (append-only log)
- [ ] Portfolio snapshots (periodic + post-trade, for P&L chart)
- [ ] FastAPI app entry point with lifespan (start/stop market data, background tasks)
- [ ] Health check endpoint
- [ ] LLM integration via LiteLLM → OpenRouter (Cerebras inference)
- [ ] Structured output parsing (message + trades + watchlist changes)
- [ ] LLM auto-execution of trades and watchlist changes
- [ ] LLM mock mode for testing (LLM_MOCK=true)
- [ ] Chat message persistence
- [ ] Next.js frontend with static export
- [ ] Dark trading terminal aesthetic (Bloomberg-inspired)
- [ ] Watchlist panel with live prices, flash animations, sparklines
- [ ] Main chart area (selected ticker detail)
- [ ] Portfolio heatmap (treemap by weight, colored by P&L)
- [ ] P&L chart (portfolio value over time)
- [ ] Positions table (ticker, qty, avg cost, current price, P&L)
- [ ] Trade bar (ticker, quantity, buy/sell buttons)
- [ ] AI chat panel (message input, conversation history, inline trade confirmations)
- [ ] Header with portfolio value, cash balance, connection status indicator
- [ ] SSE connection with EventSource and auto-reconnection
- [ ] Multi-stage Dockerfile (Node build → Python runtime)
- [ ] Start/stop scripts (macOS/Linux + Windows PowerShell)
- [ ] Docker volume for SQLite persistence
- [ ] Playwright E2E tests with docker-compose.test.yml

### Out of Scope

- User authentication / multi-user — single user with hardcoded "default" user_id
- Real money trading — simulation only, $10k virtual cash
- Limit orders / order book — market orders only for simplicity
- WebSocket — SSE is sufficient for one-way push
- OAuth / social login — no auth at all
- Mobile app — desktop-first web app
- Real-time chat streaming — full response returned (Cerebras is fast enough)
- Cloud deployment / Terraform — optional stretch goal, not core build

## Context

- **Existing code:** Market data subsystem is complete in `backend/app/market/` (8 modules, ~500 lines, 73 tests passing at 84% coverage). All other layers have empty directory stubs.
- **Tech stack:** Python 3.12 / FastAPI / uv (backend), Next.js / TypeScript (frontend), SQLite, LiteLLM → OpenRouter with Cerebras inference
- **Color scheme:** Accent Yellow `#ecad0a`, Blue Primary `#209dd7`, Purple Secondary `#753991`
- **Background:** `#0d1117` or `#1a1a2e`, muted gray borders, no pure black
- **LLM model:** `openrouter/openai/gpt-oss-120b` via Cerebras inference provider
- **Default tickers:** AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX
- **Reference spec:** `planning/PLAN.md` contains the complete detailed specification

## Constraints

- **Single container:** Everything runs in one Docker container on port 8000 — no docker-compose for production
- **Static frontend:** Next.js must use `output: 'export'` — served as static files by FastAPI, no SSR
- **No CORS:** Frontend and API on same origin — no CORS configuration needed
- **Market orders only:** No limit orders, no order book, no partial fills — dramatically simpler portfolio math
- **SQLite only:** No Postgres, no database server — single file, zero config
- **uv for Python:** Not pip, not poetry — uv with lockfile
- **LiteLLM via OpenRouter:** Use cerebras-inference skill pattern for LLM calls

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SSE over WebSockets | One-way push sufficient; simpler, universal browser support | ✓ Good — market data streaming works well |
| Strategy pattern for market data | Swap simulator/real data transparently | ✓ Good — clean architecture |
| SQLite with lazy init | Zero config, no migration step, self-contained | — Pending |
| Static Next.js export | Single origin, no CORS, one container | — Pending |
| LLM auto-execution (no confirmation) | Simulated environment, zero stakes, impressive demo | — Pending |
| Market orders only | Eliminates order book complexity | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-21 after initialization*
