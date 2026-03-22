# Requirements: FinAlly

**Defined:** 2026-03-21
**Core Value:** Users can watch live-streaming prices, trade a simulated portfolio, and chat with an AI assistant that executes trades — all in a Bloomberg-inspired terminal interface.

## v1 Requirements

### Database & Foundation

- [x] **DB-01**: SQLite database auto-creates schema and seeds default data on first run (lazy init)
- [x] **DB-02**: User profile with $10,000 default cash balance persists across restarts
- [x] **DB-03**: FastAPI app entry point with lifespan manages startup/shutdown of all subsystems
- [x] **DB-04**: Existing market data (PriceCache, SimulatorDataSource, SSE stream) wired into app lifespan
- [x] **DB-05**: Health check endpoint returns server status at GET /api/health
- [x] **DB-06**: FastAPI serves static Next.js export as catch-all (API routes take priority)

### Watchlist

- [x] **WL-01**: User can view watchlist with current prices from GET /api/watchlist
- [x] **WL-02**: User can add a ticker to watchlist via POST /api/watchlist
- [x] **WL-03**: User can remove a ticker from watchlist via DELETE /api/watchlist/{ticker}
- [x] **WL-04**: Watchlist changes sync with market data source (add_ticker/remove_ticker)
- [x] **WL-05**: Default watchlist seeded with 10 tickers (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX)

### Portfolio & Trading

- [x] **PT-01**: User can view portfolio (positions, cash balance, total value, unrealized P&L) via GET /api/portfolio
- [x] **PT-02**: User can buy shares at current market price via POST /api/portfolio/trade
- [x] **PT-03**: User can sell shares at current market price via POST /api/portfolio/trade
- [x] **PT-04**: Buy validation rejects if insufficient cash
- [x] **PT-05**: Sell validation rejects if insufficient shares
- [x] **PT-06**: Trade history recorded as append-only log
- [x] **PT-07**: Portfolio snapshots recorded every 30 seconds by background task
- [x] **PT-08**: Portfolio snapshot recorded immediately after each trade
- [x] **PT-09**: User can view portfolio value history via GET /api/portfolio/history

### LLM Chat

- [x] **LLM-01**: User can send chat message and receive AI response via POST /api/chat
- [x] **LLM-02**: AI response includes portfolio-aware analysis (cash, positions, P&L, watchlist with prices)
- [x] **LLM-03**: AI can execute trades via structured output (auto-executed, no confirmation)
- [x] **LLM-04**: AI can add/remove watchlist tickers via structured output
- [x] **LLM-05**: Failed trade validations included in chat response so AI can inform user
- [x] **LLM-06**: Chat message history persisted to database
- [x] **LLM-07**: LLM_MOCK=true returns deterministic mock responses (for testing)
- [x] **LLM-08**: LLM uses LiteLLM → OpenRouter with Cerebras inference (openrouter/openai/gpt-oss-120b)

### Frontend — Layout & Theme

- [ ] **UI-01**: Single-page dark terminal aesthetic (backgrounds #0d1117 or #1a1a2e, muted gray borders)
- [ ] **UI-02**: Header shows portfolio total value (live-updating), cash balance, connection status indicator
- [ ] **UI-03**: Accent colors: Yellow #ecad0a, Blue #209dd7, Purple #753991
- [ ] **UI-04**: Desktop-first responsive layout with all panels visible

### Frontend — Watchlist

- [x] **UI-05**: Watchlist panel shows ticker, current price, daily change %, sparkline mini-chart
- [x] **UI-06**: Prices flash green (uptick) or red (downtick) with ~500ms CSS fade animation
- [x] **UI-07**: Sparklines accumulate progressively from SSE data since page load
- [x] **UI-08**: Clicking a ticker selects it for the main chart area
- [x] **UI-09**: User can add/remove tickers from watchlist via UI controls

### Frontend — Charts & Visualization

- [x] **UI-10**: Main chart area shows price-over-time for selected ticker
- [ ] **UI-11**: Portfolio heatmap (treemap) — positions sized by weight, colored by P&L
- [ ] **UI-12**: P&L chart shows total portfolio value over time (line chart from snapshots)
- [ ] **UI-13**: Positions table shows ticker, quantity, avg cost, current price, unrealized P&L, % change

### Frontend — Trading & Chat

- [x] **UI-14**: Trade bar with ticker field, quantity field, buy button, sell button
- [ ] **UI-15**: AI chat panel with message input, scrolling conversation history
- [ ] **UI-16**: Chat shows loading indicator while waiting for LLM response
- [ ] **UI-17**: Trade executions and watchlist changes shown inline in chat as confirmations
- [ ] **UI-18**: SSE connection via EventSource with automatic reconnection

### Infrastructure

- [ ] **INF-01**: Multi-stage Dockerfile (Node 20 → Python 3.12) producing single container on port 8000
- [ ] **INF-02**: Docker volume mount for SQLite persistence (db/finally.db)
- [ ] **INF-03**: Start script for macOS/Linux (scripts/start_mac.sh)
- [ ] **INF-04**: Stop script for macOS/Linux (scripts/stop_mac.sh)
- [ ] **INF-05**: Start/stop scripts for Windows PowerShell
- [ ] **INF-06**: Playwright E2E tests with docker-compose.test.yml
- [ ] **INF-07**: E2E: fresh start shows default watchlist, $10k balance, streaming prices
- [ ] **INF-08**: E2E: add/remove ticker from watchlist
- [ ] **INF-09**: E2E: buy shares — cash decreases, position appears
- [ ] **INF-10**: E2E: sell shares — cash increases, position updates
- [ ] **INF-11**: E2E: AI chat (mocked) — send message, receive response, trade execution inline

## v2 Requirements

### Enhanced Visualization

- **VIZ-01**: Candlestick charts with OHLC data
- **VIZ-02**: Multiple chart timeframes (1m, 5m, 15m, 1h)
- **VIZ-03**: Technical indicators overlay (SMA, EMA, RSI)

### Enhanced AI

- **AI-01**: Chat streaming (token-by-token) for longer responses
- **AI-02**: Trade confirmation dialog option (configurable)
- **AI-03**: AI-generated portfolio reports

### Deployment

- **DEP-01**: Terraform configuration for AWS App Runner
- **DEP-02**: CI/CD pipeline (GitHub Actions)

## Out of Scope

| Feature | Reason |
|---------|--------|
| User authentication | Single-user demo; zero value for capstone |
| Real money / brokerage API | Legal/compliance nightmare, not a demo feature |
| Limit orders / order book | Eliminates massive complexity (matching, partial fills) |
| WebSockets | SSE is sufficient for one-way push |
| Mobile app | Desktop-first terminal; web-only |
| OAuth / social login | No auth at all |
| Dark/light theme toggle | Dark only — it's a terminal |
| Internationalization | English only for demo |
| Multiple user profiles | user_id="default" everywhere |
| Historical data API | Sparklines from SSE since page load |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DB-01 | Phase 1 | Complete |
| DB-02 | Phase 1 | Complete |
| DB-03 | Phase 1 | Complete |
| DB-04 | Phase 1 | Complete |
| DB-05 | Phase 1 | Complete |
| DB-06 | Phase 1 | Complete |
| WL-01 | Phase 2 | Complete |
| WL-02 | Phase 2 | Complete |
| WL-03 | Phase 2 | Complete |
| WL-04 | Phase 2 | Complete |
| WL-05 | Phase 1 | Complete |
| PT-01 | Phase 2 | Complete |
| PT-02 | Phase 2 | Complete |
| PT-03 | Phase 2 | Complete |
| PT-04 | Phase 2 | Complete |
| PT-05 | Phase 2 | Complete |
| PT-06 | Phase 2 | Complete |
| PT-07 | Phase 2 | Complete |
| PT-08 | Phase 2 | Complete |
| PT-09 | Phase 2 | Complete |
| LLM-01 | Phase 3 | Complete |
| LLM-02 | Phase 3 | Complete |
| LLM-03 | Phase 3 | Complete |
| LLM-04 | Phase 3 | Complete |
| LLM-05 | Phase 3 | Complete |
| LLM-06 | Phase 3 | Complete |
| LLM-07 | Phase 3 | Complete |
| LLM-08 | Phase 3 | Complete |
| UI-01 | Phase 4 | Pending |
| UI-02 | Phase 4 | Pending |
| UI-03 | Phase 4 | Pending |
| UI-04 | Phase 4 | Pending |
| UI-05 | Phase 4 | Complete |
| UI-06 | Phase 4 | Complete |
| UI-07 | Phase 4 | Complete |
| UI-08 | Phase 4 | Complete |
| UI-09 | Phase 4 | Complete |
| UI-10 | Phase 4 | Complete |
| UI-11 | Phase 4 | Pending |
| UI-12 | Phase 4 | Pending |
| UI-13 | Phase 4 | Pending |
| UI-14 | Phase 4 | Complete |
| UI-15 | Phase 4 | Pending |
| UI-16 | Phase 4 | Pending |
| UI-17 | Phase 4 | Pending |
| UI-18 | Phase 4 | Pending |
| INF-01 | Phase 5 | Pending |
| INF-02 | Phase 5 | Pending |
| INF-03 | Phase 5 | Pending |
| INF-04 | Phase 5 | Pending |
| INF-05 | Phase 5 | Pending |
| INF-06 | Phase 5 | Pending |
| INF-07 | Phase 5 | Pending |
| INF-08 | Phase 5 | Pending |
| INF-09 | Phase 5 | Pending |
| INF-10 | Phase 5 | Pending |
| INF-11 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 47 total
- Mapped to phases: 47
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-21*
*Last updated: 2026-03-21 after initial definition*
