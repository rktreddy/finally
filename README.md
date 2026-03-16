# FinAlly — AI Trading Workstation

A visually stunning AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades. Think Bloomberg terminal meets AI copilot.

Built entirely by coding agents as the capstone project for an agentic AI coding course.

## Features

- **Live price streaming** via SSE with green/red flash animations
- **Simulated trading** — $10k virtual cash, market orders, fractional shares
- **Portfolio visualization** — heatmap, P&L chart, positions table
- **AI chat assistant** — analyzes positions, executes trades, manages watchlist via natural language
- **Dark terminal aesthetic** — data-dense, professional layout

## Quick Start

```bash
# 1. Copy and configure environment variables
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY

# 2. Start the app
./scripts/start_mac.sh        # macOS/Linux
# ./scripts/start_windows.ps1  # Windows

# 3. Open http://localhost:8000
```

## Architecture

Single Docker container, single port (`8000`).

| Layer | Tech |
|-------|------|
| Frontend | Next.js (static export), TypeScript, Tailwind CSS |
| Backend | FastAPI, Python, uv |
| Database | SQLite (volume-mounted) |
| Real-time | Server-Sent Events (SSE) |
| AI | LiteLLM → OpenRouter (Cerebras inference) |
| Market Data | Built-in simulator (default) or Massive API |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key for LLM chat |
| `MASSIVE_API_KEY` | No | Massive API key for real market data (simulator used if absent) |
| `LLM_MOCK` | No | Set `true` for deterministic mock LLM responses (testing) |
| `DB_PATH` | No | Custom SQLite database path |

## Project Structure

```
finally/
├── frontend/          # Next.js static app
├── backend/           # FastAPI + uv project
├── planning/          # Project documentation & agent specs
├── scripts/           # Start/stop scripts
├── test/              # Playwright E2E tests
├── db/                # SQLite volume mount point
└── Dockerfile         # Multi-stage build (Node → Python)
```

## Development

**Backend:**
```bash
cd backend && uv sync && uv run uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend && npm install && npm run dev
```

## Testing

```bash
# Backend unit tests
cd backend && uv run pytest

# Frontend unit tests
cd frontend && npm test

# E2E tests (requires Docker)
cd test && docker compose -f docker-compose.test.yml up --abort-on-container-exit
```

## License

Educational project — built for the AI Coder course.
