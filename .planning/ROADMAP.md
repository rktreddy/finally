# Roadmap: FinAlly

## Overview

FinAlly is built bottom-up from its data layer through API routes, LLM integration, and frontend, then wrapped in Docker with E2E tests. The market data subsystem already exists, so Phase 1 wires it into a proper FastAPI app with database persistence. Each subsequent phase delivers a complete, verifiable capability: API consumers can trade and manage watchlists (Phase 2), an AI assistant can analyze and act (Phase 3), users see everything in a Bloomberg-inspired terminal (Phase 4), and the whole thing ships as a single Docker container with E2E coverage (Phase 5).

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Database, app lifespan, health check, static file serving, and market data wiring
- [x] **Phase 2: Watchlist & Trading API** - Watchlist CRUD and portfolio/trade endpoints with full validation
- [x] **Phase 3: LLM Chat Integration** - AI assistant with portfolio-aware analysis and auto-trade execution
- [x] **Phase 4: Frontend Terminal** - Bloomberg-inspired single-page trading terminal with all panels
- [ ] **Phase 5: Docker & E2E Testing** - Multi-stage container build, scripts, and Playwright end-to-end tests

## Phase Details

### Phase 1: Foundation
**Goal**: The FastAPI application starts cleanly, initializes a SQLite database with schema and seed data, wires up the existing market data subsystem, serves static files, and responds to health checks
**Depends on**: Nothing (first phase)
**Requirements**: DB-01, DB-02, DB-03, DB-04, DB-05, DB-06, WL-05
**Success Criteria** (what must be TRUE):
  1. Starting the FastAPI app creates the SQLite database with all tables and seeds the default watchlist (10 tickers) and user profile ($10k cash) if they do not already exist
  2. GET /api/health returns a successful status response
  3. The existing market data simulator starts on app startup and stops on shutdown, with prices flowing into PriceCache
  4. The app serves a placeholder index.html (or static files) at the root URL, with API routes taking priority over the catch-all
  5. Restarting the app preserves previously persisted data (no re-seed if data exists)
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — SQLite database layer: schema.sql, init_db(), seed data, and unit tests
- [x] 01-02-PLAN.md — FastAPI app entry point: lifespan, health check, market data wiring, static serving, and integration tests

### Phase 2: Watchlist & Trading API
**Goal**: Users can manage their watchlist and execute trades through REST API endpoints, with all positions, P&L, and trade history properly tracked
**Depends on**: Phase 1
**Requirements**: WL-01, WL-02, WL-03, WL-04, PT-01, PT-02, PT-03, PT-04, PT-05, PT-06, PT-07, PT-08, PT-09
**Success Criteria** (what must be TRUE):
  1. GET /api/watchlist returns all watched tickers with their current live prices from PriceCache
  2. Adding a ticker via POST /api/watchlist persists it to the database and registers it with the market data source; removing via DELETE unregisters it
  3. POST /api/portfolio/trade with side=buy deducts cash, creates/updates the position, and records the trade in history; rejects with error if insufficient cash
  4. POST /api/portfolio/trade with side=sell increases cash, updates/removes the position, and records the trade; rejects with error if insufficient shares
  5. GET /api/portfolio returns current positions with unrealized P&L calculated from live prices, total portfolio value, and cash balance
  6. Portfolio snapshots are recorded every 30 seconds by a background task and immediately after each trade; GET /api/portfolio/history returns the snapshot timeline
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Repository layer + watchlist CRUD endpoints (GET/POST/DELETE) with integration tests
- [x] 02-02-PLAN.md — Portfolio valuation, trade execution, snapshot background task, and portfolio history endpoint with integration tests

### Phase 3: LLM Chat Integration
**Goal**: Users can chat with an AI assistant that understands their portfolio and can autonomously execute trades and manage the watchlist through natural language
**Depends on**: Phase 2
**Requirements**: LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, LLM-06, LLM-07, LLM-08
**Success Criteria** (what must be TRUE):
  1. POST /api/chat accepts a user message and returns a JSON response containing the AI's conversational message, any executed trades, and any watchlist changes
  2. The AI response demonstrates awareness of the user's current portfolio state (cash balance, positions with P&L, watchlist with live prices)
  3. When the AI specifies trades in its structured output, those trades are auto-executed through the same trade logic as manual trades, with failures reported in the response
  4. Chat conversation history persists to the database and is included as context in subsequent LLM calls
  5. Setting LLM_MOCK=true returns deterministic mock responses without calling OpenRouter, enabling test automation
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — LLM module (models, client, prompts, mock), chat repository functions, litellm dependency, and unit tests
- [x] 03-02-PLAN.md — Chat route with auto-execution of trades/watchlist changes, wiring into main.py, and integration tests

### Phase 4: Frontend Terminal
**Goal**: Users interact with a complete Bloomberg-inspired trading terminal that displays live-streaming prices, charts, portfolio visualizations, a trade bar, and an AI chat panel -- all in a dark, data-dense single-page application
**Depends on**: Phase 3
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, UI-08, UI-09, UI-10, UI-11, UI-12, UI-13, UI-14, UI-15, UI-16, UI-17, UI-18
**Success Criteria** (what must be TRUE):
  1. The page loads with a dark terminal aesthetic, header showing live portfolio value, cash balance, and a connection status indicator (green/yellow/red dot)
  2. The watchlist panel shows all tickers with live-updating prices that flash green/red on change, sparkline mini-charts that fill in progressively, and clicking a ticker loads its detail chart
  3. The portfolio section displays a heatmap (treemap) of positions colored by P&L, a line chart of portfolio value over time, and a positions table with unrealized P&L
  4. Users can execute trades via the trade bar (ticker, quantity, buy/sell) and see immediate portfolio updates
  5. The AI chat panel accepts messages, shows a loading indicator during LLM calls, displays responses with inline trade and watchlist change confirmations, and scrolls through conversation history
**Plans**: 3 plans

Plans:
- [x] 04-01-PLAN.md — Next.js scaffold, dark theme, SSE hook, types, API client, Header, and layout shell
- [x] 04-02-PLAN.md — Watchlist panel with sparklines and price flash, main ticker chart, and trade bar
- [x] 04-03-PLAN.md — Portfolio heatmap, P&L chart, positions table, AI chat panel, page wiring, and static serving update

### Phase 5: Docker & E2E Testing
**Goal**: The entire application ships as a single Docker container built from a multi-stage Dockerfile, with start/stop scripts and Playwright E2E tests validating all critical user workflows
**Depends on**: Phase 4
**Requirements**: INF-01, INF-02, INF-03, INF-04, INF-05, INF-06, INF-07, INF-08, INF-09, INF-10, INF-11
**Success Criteria** (what must be TRUE):
  1. Running the start script builds and launches a single Docker container on port 8000 that serves both the frontend and API, with SQLite data persisting across container restarts via a Docker volume
  2. The stop script cleanly stops the container without destroying persisted data
  3. E2E tests confirm: fresh start shows default watchlist with 10 tickers, $10k cash balance, and prices streaming via SSE
  4. E2E tests confirm: watchlist add/remove, buy shares (cash decreases, position appears), sell shares (cash increases, position updates), and AI chat with mocked responses all work end-to-end
**Plans**: 2 plans

Plans:
- [x] 05-01-PLAN.md — Dockerfile, docker-compose.yml, start/stop scripts, .env.example, and .dockerignore
- [ ] 05-02-PLAN.md — E2E test infrastructure (docker-compose.test.yml, Playwright config) and Playwright test suite

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/2 | Complete | 2026-03-22 |
| 2. Watchlist & Trading API | 2/2 | Complete | 2026-03-22 |
| 3. LLM Chat Integration | 2/2 | Complete | 2026-03-22 |
| 4. Frontend Terminal | 3/3 | Complete | 2026-03-22 |
| 5. Docker & E2E Testing | 0/2 | Not started | - |
