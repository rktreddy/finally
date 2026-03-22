# Phase 4: Frontend Terminal - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Users interact with a complete Bloomberg-inspired trading terminal that displays live-streaming prices, charts, portfolio visualizations, a trade bar, and an AI chat panel — all in a dark, data-dense single-page application. This phase delivers the entire Next.js frontend as a static export served by FastAPI. No backend changes except replacing the placeholder static/index.html with the real build output.

</domain>

<decisions>
## Implementation Decisions

### Project Setup
- **D-01:** Next.js with TypeScript in `frontend/` directory. Use `output: 'export'` in next.config for static export.
- **D-02:** Tailwind CSS for styling with a custom dark theme configuration matching the project color scheme.
- **D-03:** The static export output goes to `frontend/out/` — this directory replaces the placeholder `static/` directory. Update `backend/app/main.py` to serve from the correct path or copy the build output.
- **D-04:** No SSR, no API routes in Next.js — all data fetching via same-origin `/api/*` endpoints using `fetch()`.

### Layout & Theme
- **D-05:** Single-page app with a grid layout. Desktop-first, functional on tablet. All panels visible simultaneously.
- **D-06:** Dark theme: backgrounds `#0d1117` (primary) and `#1a1a2e` (secondary panels), muted gray borders (`#30363d`), no pure black.
- **D-07:** Accent colors: Yellow `#ecad0a` (highlights, active states), Blue `#209dd7` (primary actions, links), Purple `#753991` (submit/trade buttons).
- **D-08:** Header bar spanning full width with: portfolio total value (live-updating), cash balance, connection status indicator (green/yellow/red dot).

### Watchlist Panel
- **D-09:** Table/grid of watched tickers. Each row: ticker symbol, current price, daily change %, sparkline mini-chart.
- **D-10:** Price flash animations: on price change from SSE, briefly apply green (uptick) or red (downtick) background highlight, fading over ~500ms via CSS transition.
- **D-11:** Sparklines accumulate data points from the SSE stream since page load — they fill in progressively, not from historical data.
- **D-12:** Clicking a ticker in the watchlist selects it for the main chart area.
- **D-13:** Add/remove ticker controls: a text input + "Add" button to add tickers, and a small "x" or remove icon per row.

### Charts & Visualization
- **D-14:** Main chart area shows price over time for the selected ticker, using accumulated SSE data since page load. Use Lightweight Charts (lightweight-charts npm package) for the financial chart, or Recharts as fallback.
- **D-15:** Portfolio heatmap (treemap): each rectangle is a position, sized by portfolio weight (position_value / total_value), colored by P&L (green gradient for profit, red gradient for loss). Use Recharts Treemap component.
- **D-16:** P&L chart: line chart showing total portfolio value over time from GET /api/portfolio/history snapshots. Use Recharts LineChart.
- **D-17:** Positions table: ticker, quantity, avg cost, current price, unrealized P&L, % change. Green/red text for P&L values.

### Trade Bar
- **D-18:** Simple horizontal bar: ticker input field (auto-populated when clicking watchlist), quantity input field, Buy button (green/blue), Sell button (red/purple).
- **D-19:** Market orders only — instant fill. On submit, POST /api/portfolio/trade, show success/error feedback inline or via toast.

### AI Chat Panel
- **D-20:** Docked sidebar (right side or collapsible). Message input at bottom, scrolling conversation history above.
- **D-21:** Loading indicator (spinner or pulsing dots) while waiting for LLM response.
- **D-22:** Trade executions and watchlist changes from AI responses shown inline as styled confirmation blocks (e.g., "Bought 10 AAPL at $150.00" with green accent).
- **D-23:** POST /api/chat for message submission. Response includes message + actions to display.

### SSE Connection
- **D-24:** Use native `EventSource` API connecting to `/api/stream/prices`.
- **D-25:** Connection status indicator: green = connected, yellow = reconnecting, red = disconnected. EventSource has built-in retry.
- **D-26:** On receiving price updates, update all relevant UI: watchlist prices, sparklines, main chart, portfolio valuations, header total value.

### Data Flow
- **D-27:** On page load: fetch GET /api/watchlist, GET /api/portfolio, GET /api/portfolio/history. Then open SSE connection.
- **D-28:** Watchlist and portfolio data refreshed after trade execution or watchlist mutation (re-fetch from API).
- **D-29:** Sparkline and main chart data accumulated in React state from SSE events — not persisted, resets on page reload.

### Claude's Discretion
- Exact grid layout proportions and breakpoints
- Component file structure within frontend/
- Choice between Lightweight Charts and Recharts for ticker chart
- Sparkline rendering approach (SVG, canvas, or library)
- Toast/notification library choice
- Exact chat panel width and collapse behavior
- Animation details beyond the 500ms price flash

</decisions>

<specifics>
## Specific Ideas

- "Professional, data-dense layout: inspired by Bloomberg/trading terminals — every pixel earns its place"
- Price flash effect should be subtle but noticeable — brief highlight, not garish
- The AI chat panel should feel integrated, not bolted on — docked sidebar that's always accessible
- Sparklines should give a quick sense of price direction without needing to click for the detail chart

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Frontend Design Spec
- `planning/PLAN.md` §10 — Frontend Design: layout elements, technical notes, component descriptions
- `planning/PLAN.md` §2 — User Experience: what the user sees and does, visual design, color scheme

### API Endpoints (consumed by frontend)
- `planning/PLAN.md` §8 — All API endpoints the frontend calls
- `planning/PLAN.md` §6 — SSE streaming: endpoint, event format, reconnection

### Architecture
- `planning/PLAN.md` §3 — Single container, static export served by FastAPI
- `planning/PLAN.md` §4 — Directory structure: frontend/ is self-contained Next.js project

### Prior Phase Integration
- `backend/app/routes/watchlist.py` — GET/POST/DELETE /api/watchlist response shapes
- `backend/app/routes/portfolio.py` — GET /api/portfolio, POST /api/portfolio/trade, GET /api/portfolio/history response shapes
- `backend/app/routes/chat.py` — POST /api/chat request/response shape
- `backend/app/market/stream.py` — SSE event format for /api/stream/prices

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `static/index.html` — Placeholder from Phase 1, will be replaced by Next.js build output
- `backend/app/main.py` — Mounts StaticFiles at "/" as catch-all; may need path update for Next.js export output

### API Response Shapes (from backend routes)
- `GET /api/watchlist` → `[{ticker, added_at, price, change, change_percent, direction}]`
- `GET /api/portfolio` → `{cash, positions: [{ticker, quantity, avg_cost, current_price, unrealized_pnl, pnl_percent}], total_value, total_pnl}`
- `POST /api/portfolio/trade` → `{trade: {id, ticker, side, quantity, price, executed_at}, cash_balance}`
- `GET /api/portfolio/history` → `{snapshots: [{total_value, recorded_at}]}`
- `POST /api/chat` → `{message, actions: {trades: [...], watchlist_changes: [...], errors: [...]}}`
- `GET /api/stream/prices` → SSE events with `data: {TICKER: {ticker, price, previous_price, timestamp, change, change_percent, direction}}`
- `GET /api/health` → `{status, market_data, database}`

### Established Patterns
- Same-origin API calls (no CORS needed)
- SSE via native EventSource with built-in retry
- All prices updated via SSE push, not polling

### Integration Points
- Frontend build output must land where FastAPI's StaticFiles mount expects it
- No backend code changes needed except potentially the static directory path

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-frontend-terminal*
*Context gathered: 2026-03-22*
