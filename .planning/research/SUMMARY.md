# Research Summary: FinAlly AI Trading Workstation

**Date:** 2026-03-21

## Stack Recommendations

| Component | Choice | Confidence |
|-----------|--------|------------|
| Database | `aiosqlite` (async SQLite wrapper) | High |
| LLM | `litellm` → OpenRouter (`openrouter/openai/gpt-oss-120b` via Cerebras) | High |
| Frontend Framework | Next.js 14+ with TypeScript, static export | High |
| Styling | Tailwind CSS 3.x with custom dark theme | High |
| Financial Charts | `lightweight-charts` 4.x (TradingView's canvas lib) | High |
| General Charts | `recharts` 2.x (P&L chart, sparklines, treemap) | High |
| E2E Testing | Playwright with docker-compose.test.yml | High |
| Docker | Multi-stage: Node 20 slim → Python 3.12 slim | High |

**Backend additions:** `aiosqlite>=0.20.0`, `litellm>=1.40.0`

## Table Stakes Features

1. **Database:** Persistent watchlist, portfolio, trades, chat history — SQLite with lazy init
2. **Portfolio:** Cash balance, positions with avg cost, unrealized P&L, total value
3. **Trading:** Market order execution with validation (cash/shares sufficiency)
4. **Visualization:** Live prices with flash animations, sparklines, detail chart, P&L chart, positions table
5. **Infrastructure:** Single Docker container, health check, connection status indicator

## Key Differentiators

1. **AI auto-execution** — LLM executes trades without confirmation dialog (zero stakes, max demo impact)
2. **Portfolio heatmap** — Treemap visualization sized by weight, colored by P&L
3. **AI watchlist management** — Natural language add/remove tickers
4. **Inline trade confirmations** — Trade executions shown in chat thread
5. **Progressive sparklines** — Fill in from SSE stream since page load

## Build Order (Critical Path)

```
Phase 1: Database + App Foundation → Phase 2: API Routes → Phase 3: LLM Integration
                                                                        ↓
                                              Phase 4: Frontend ←←←←←←←←
                                                        ↓
                                              Phase 5: Docker + E2E
```

Database → API → LLM → Frontend → Docker is the dependency chain. LLM and early frontend work can overlap.

## Top Pitfalls to Avoid

1. **LLM structured output failures** → Always wrap parse in try/except with fallback response
2. **SQLite async blocking** → Use `aiosqlite` + WAL mode, never raw `sqlite3`
3. **Next.js static export limits** → No SSR, no API routes, no `next/image` optimization, all `'use client'`
4. **Playwright SSE flakiness** → Assert structure not values, generous timeouts, `waitForFunction`
5. **FastAPI static mount order** → API routes first, static files last as catch-all

## Anti-Features (Do NOT Build)

- Authentication, limit orders, real money, WebSockets, chat streaming, mobile layout
- Trade confirmation dialogs, historical data API, candlestick charts, dark/light toggle
- These are all explicitly out of scope per PROJECT.md

---
*Research synthesis: 2026-03-21*
