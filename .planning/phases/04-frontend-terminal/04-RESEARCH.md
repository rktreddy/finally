# Phase 4: Frontend Terminal - Research

**Researched:** 2026-03-22
**Domain:** Next.js static export SPA, real-time SSE, financial data visualization
**Confidence:** HIGH

## Summary

Phase 4 delivers the entire Next.js frontend as a static export (`output: 'export'`) served by the existing FastAPI backend. The frontend is a single-page Bloomberg-inspired trading terminal with live-streaming prices via SSE, interactive charts, portfolio visualizations, a trade bar, and an AI chat panel. All backend APIs are already complete (Phases 1-3); this phase is purely frontend.

The standard stack is Next.js 16 + React 19 + TypeScript + Tailwind CSS 4 for the application shell, Lightweight Charts 5 for the main financial chart, Recharts 3 for the treemap and P&L line chart, and hand-rolled SVG sparklines (zero-dependency, trivial to implement). The SSE connection uses the native browser `EventSource` API -- no library needed.

**Primary recommendation:** Build the frontend as a Next.js 16 static export with App Router, using `useRef`/`useEffect` for Lightweight Charts integration, Recharts `<Treemap>` and `<LineChart>` for portfolio visualizations, and a custom React hook (`useSSE`) wrapping `EventSource` to distribute price updates across all components via React context.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Next.js with TypeScript in `frontend/` directory. Use `output: 'export'` in next.config for static export.
- **D-02:** Tailwind CSS for styling with a custom dark theme configuration matching the project color scheme.
- **D-03:** The static export output goes to `frontend/out/` -- this directory replaces the placeholder `static/` directory. Update `backend/app/main.py` to serve from the correct path or copy the build output.
- **D-04:** No SSR, no API routes in Next.js -- all data fetching via same-origin `/api/*` endpoints using `fetch()`.
- **D-05:** Single-page app with a grid layout. Desktop-first, functional on tablet. All panels visible simultaneously.
- **D-06:** Dark theme: backgrounds `#0d1117` (primary) and `#1a1a2e` (secondary panels), muted gray borders (`#30363d`), no pure black.
- **D-07:** Accent colors: Yellow `#ecad0a` (highlights, active states), Blue `#209dd7` (primary actions, links), Purple `#753991` (submit/trade buttons).
- **D-08:** Header bar spanning full width with: portfolio total value (live-updating), cash balance, connection status indicator (green/yellow/red dot).
- **D-09:** Watchlist table/grid with ticker, price, change %, sparkline.
- **D-10:** Price flash animations: green/red ~500ms CSS fade.
- **D-11:** Sparklines accumulate from SSE since page load.
- **D-12:** Clicking a ticker selects it for main chart.
- **D-13:** Add/remove ticker controls.
- **D-14:** Main chart: Lightweight Charts or Recharts for financial chart.
- **D-15:** Portfolio heatmap: Recharts Treemap.
- **D-16:** P&L chart: Recharts LineChart from portfolio/history snapshots.
- **D-17:** Positions table with P&L.
- **D-18:** Trade bar: ticker, quantity, buy/sell buttons.
- **D-19:** Market orders, POST /api/portfolio/trade, inline feedback.
- **D-20:** AI chat panel: docked sidebar, scrolling history.
- **D-21:** Loading indicator during LLM response.
- **D-22:** Inline trade/watchlist confirmations in chat.
- **D-23:** POST /api/chat for messages.
- **D-24:** Native EventSource to /api/stream/prices.
- **D-25:** Connection status indicator: green/yellow/red.
- **D-26:** SSE updates flow to all UI: watchlist, sparklines, chart, portfolio, header.
- **D-27:** On load: fetch watchlist, portfolio, portfolio/history, then open SSE.
- **D-28:** Re-fetch after trade or watchlist mutation.
- **D-29:** Sparkline/chart data in React state, resets on reload.

### Claude's Discretion
- Exact grid layout proportions and breakpoints
- Component file structure within frontend/
- Choice between Lightweight Charts and Recharts for ticker chart
- Sparkline rendering approach (SVG, canvas, or library)
- Toast/notification library choice
- Exact chat panel width and collapse behavior
- Animation details beyond the 500ms price flash

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-01 | Single-page dark terminal aesthetic (backgrounds #0d1117 or #1a1a2e, muted gray borders) | Tailwind CSS custom theme config with CSS variables for the color palette |
| UI-02 | Header shows portfolio total value (live-updating), cash balance, connection status indicator | React context for SSE data + EventSource readyState mapping |
| UI-03 | Accent colors: Yellow #ecad0a, Blue #209dd7, Purple #753991 | Tailwind `extend.colors` configuration |
| UI-04 | Desktop-first responsive layout with all panels visible | CSS Grid layout with Tailwind grid utilities |
| UI-05 | Watchlist panel shows ticker, current price, daily change %, sparkline mini-chart | SSE data mapped per ticker + SVG sparkline component |
| UI-06 | Prices flash green (uptick) or red (downtick) with ~500ms CSS fade animation | CSS transition on background-color with conditional class toggle |
| UI-07 | Sparklines accumulate progressively from SSE data since page load | React state array per ticker, appended on each SSE update |
| UI-08 | Clicking a ticker selects it for the main chart area | Shared state (context or lifted state) for selectedTicker |
| UI-09 | User can add/remove tickers from watchlist via UI controls | POST/DELETE /api/watchlist + re-fetch pattern |
| UI-10 | Main chart area shows price-over-time for selected ticker | Lightweight Charts `createChart` + `LineSeries` with accumulated SSE data |
| UI-11 | Portfolio heatmap (treemap) -- positions sized by weight, colored by P&L | Recharts `<Treemap>` with custom content renderer for P&L coloring |
| UI-12 | P&L chart shows total portfolio value over time (line chart from snapshots) | Recharts `<LineChart>` consuming GET /api/portfolio/history |
| UI-13 | Positions table shows ticker, quantity, avg cost, current price, unrealized P&L, % change | HTML table styled with Tailwind, data from GET /api/portfolio |
| UI-14 | Trade bar with ticker field, quantity field, buy button, sell button | Form component, POST /api/portfolio/trade on submit |
| UI-15 | AI chat panel with message input, scrolling conversation history | Scrollable div with ref for auto-scroll, POST /api/chat |
| UI-16 | Chat shows loading indicator while waiting for LLM response | Boolean state toggle with animated spinner/dots |
| UI-17 | Trade executions and watchlist changes shown inline in chat as confirmations | Parse `actions` field from chat response, render styled blocks |
| UI-18 | SSE connection via EventSource with automatic reconnection | Native EventSource with onopen/onmessage/onerror handlers in custom hook |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| next | 16.2.1 | App framework with static export | Project decision; `output: 'export'` produces `out/` directory |
| react | 19.2.4 | UI library | Paired with Next.js 16 |
| typescript | 5.9.3 | Type safety | Project decision |
| tailwindcss | 4.2.2 | Utility-first CSS | Project decision; dark theme via config |

### Charting & Visualization
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lightweight-charts | 5.1.0 | Main financial chart (price over time) | Selected ticker detail chart -- canvas-based, high performance |
| recharts | 3.8.0 | Treemap (heatmap) and P&L line chart | Portfolio visualizations -- React-native API, built-in Treemap |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @types/react | 19.2.14 | React type definitions | Development only |
| @types/node | (latest) | Node type definitions | Development only |

### Discretionary Choices (Claude's Recommendation)

| Area | Recommendation | Rationale |
|------|---------------|-----------|
| Ticker detail chart | **Lightweight Charts** (not Recharts) | Purpose-built for financial data, canvas-based performance, proper time axis, crosshair support |
| Sparklines | **Hand-rolled SVG** (no library) | 15 lines of code, zero dependencies, perfect fit for the narrow watchlist rows |
| Toast/notification | **No library -- inline feedback** | Trade bar shows success/error text inline; avoids another dependency for 2 use cases |
| Chat panel width | **~350px fixed, collapsible** | Wide enough for conversation, narrow enough to not crowd charts |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Lightweight Charts | Recharts LineChart | Recharts is simpler but lacks financial chart features (crosshair, time axis, proper OHLC support) |
| Hand-rolled SVG sparklines | react-sparklines | Extra dependency for a trivial component; react-sparklines hasn't been actively maintained |
| Inline feedback | react-hot-toast | Adds a dependency; only 2 feedback points (trade + watchlist) don't justify it |

**Installation:**
```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --app --no-src-dir --no-eslint --no-import-alias
npm install lightweight-charts recharts
```

Note: `create-next-app` with `--tailwind` installs Tailwind CSS automatically. The `--app` flag uses App Router. `--no-src-dir` keeps files in root (simpler for static export).

## Architecture Patterns

### Recommended Project Structure
```
frontend/
├── app/
│   ├── layout.tsx          # Root layout with dark theme, global CSS
│   ├── page.tsx            # Single page -- the entire terminal
│   └── globals.css         # Tailwind directives + custom CSS variables
├── components/
│   ├── Header.tsx          # Portfolio value, cash, connection status
│   ├── Watchlist.tsx       # Ticker grid with sparklines
│   ├── WatchlistRow.tsx    # Single ticker row with price flash
│   ├── Sparkline.tsx       # SVG sparkline mini-chart
│   ├── TickerChart.tsx     # Lightweight Charts wrapper for main chart
│   ├── TradeBar.tsx        # Trade execution form
│   ├── PortfolioHeatmap.tsx # Recharts Treemap
│   ├── PnLChart.tsx        # Recharts LineChart for portfolio history
│   ├── PositionsTable.tsx  # Positions with P&L
│   └── ChatPanel.tsx       # AI chat sidebar
├── hooks/
│   ├── useSSE.ts           # EventSource connection + price state
│   ├── usePortfolio.ts     # Portfolio data fetching + refresh
│   └── useWatchlist.ts     # Watchlist CRUD operations
├── lib/
│   ├── api.ts              # fetch wrappers for /api/* endpoints
│   └── types.ts            # TypeScript interfaces matching API shapes
├── next.config.ts          # output: 'export'
├── tailwind.config.ts      # Custom dark theme colors
├── tsconfig.json
└── package.json
```

### Pattern 1: SSE Data Distribution via Custom Hook
**What:** A single `useSSE` hook manages the EventSource connection and distributes price data to all consumers via React context.
**When to use:** Always -- this is the central data flow pattern for the entire app.
**Example:**
```typescript
// hooks/useSSE.ts
"use client";
import { useEffect, useRef, useState, useCallback } from "react";

type ConnectionStatus = "connected" | "reconnecting" | "disconnected";

interface PriceUpdate {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: number;
  change: number;
  change_percent: number;
  direction: "up" | "down" | "flat";
}

type PriceMap = Record<string, PriceUpdate>;

export function useSSE() {
  const [prices, setPrices] = useState<PriceMap>({});
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const priceHistoryRef = useRef<Record<string, { time: number; value: number }[]>>({});

  useEffect(() => {
    const es = new EventSource("/api/stream/prices");

    es.onopen = () => setStatus("connected");

    es.onmessage = (event) => {
      const data: PriceMap = JSON.parse(event.data);
      setPrices(data);

      // Accumulate sparkline/chart data
      for (const [ticker, update] of Object.entries(data)) {
        if (!priceHistoryRef.current[ticker]) {
          priceHistoryRef.current[ticker] = [];
        }
        priceHistoryRef.current[ticker].push({
          time: update.timestamp,
          value: update.price,
        });
      }
    };

    es.onerror = () => setStatus("reconnecting");

    return () => {
      es.close();
      setStatus("disconnected");
    };
  }, []);

  const getHistory = useCallback(
    (ticker: string) => priceHistoryRef.current[ticker] || [],
    []
  );

  return { prices, status, getHistory };
}
```

### Pattern 2: Price Flash Animation via CSS Transition
**What:** On price change, briefly apply a background class that fades over 500ms.
**When to use:** Every watchlist row, on each SSE update.
**Example:**
```typescript
// components/WatchlistRow.tsx
"use client";
import { useEffect, useRef, useState } from "react";

export function WatchlistRow({ ticker, price, direction, ...rest }) {
  const [flash, setFlash] = useState<"up" | "down" | null>(null);
  const prevPriceRef = useRef(price);

  useEffect(() => {
    if (price !== prevPriceRef.current) {
      setFlash(direction === "up" ? "up" : "down");
      prevPriceRef.current = price;
      const timer = setTimeout(() => setFlash(null), 500);
      return () => clearTimeout(timer);
    }
  }, [price, direction]);

  return (
    <tr className={`transition-colors duration-500 ${
      flash === "up" ? "bg-green-900/40" :
      flash === "down" ? "bg-red-900/40" :
      "bg-transparent"
    }`}>
      {/* ... row content ... */}
    </tr>
  );
}
```

### Pattern 3: Lightweight Charts React Wrapper
**What:** Create chart in useEffect, update data via ref to avoid re-creating chart on every render.
**When to use:** The main ticker detail chart.
**Example:**
```typescript
// components/TickerChart.tsx
"use client";
import { useEffect, useRef } from "react";
import { createChart, LineSeries, type IChartApi, type ISeriesApi } from "lightweight-charts";

interface Props {
  data: { time: number; value: number }[];
}

export function TickerChart({ data }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: "#0d1117" },
        textColor: "#c9d1d9",
      },
      grid: {
        vertLines: { color: "#30363d" },
        horzLines: { color: "#30363d" },
      },
      width: containerRef.current.clientWidth,
      height: 300,
      timeScale: { timeVisible: true, secondsVisible: true },
    });

    const series = chart.addSeries(LineSeries, {
      color: "#209dd7",
      lineWidth: 2,
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, []);

  // Update data without recreating chart
  useEffect(() => {
    if (seriesRef.current && data.length > 0) {
      seriesRef.current.setData(
        data.map((d) => ({ time: d.time as any, value: d.value }))
      );
    }
  }, [data]);

  return <div ref={containerRef} />;
}
```

### Pattern 4: SVG Sparkline (Zero Dependencies)
**What:** Render a simple SVG polyline from accumulated price data.
**When to use:** Watchlist rows, for quick price direction visualization.
**Example:**
```typescript
// components/Sparkline.tsx
interface Props {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
}

export function Sparkline({ data, width = 80, height = 24, color = "#209dd7" }: Props) {
  if (data.length < 2) return <svg width={width} height={height} />;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((v - min) / range) * (height - 4) - 2;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <polyline fill="none" stroke={color} strokeWidth={1.5} points={points} />
    </svg>
  );
}
```

### Anti-Patterns to Avoid
- **Re-creating Lightweight Charts on every render:** Use refs for the chart and series instances; only call `setData()` on data changes.
- **Storing sparkline history in React state:** Use `useRef` for the accumulating array to avoid re-renders on every 500ms SSE tick. Only the displayed slice should trigger renders.
- **Polling for prices:** All price data comes via SSE push. Never set up intervals to fetch prices.
- **Using `getServerSideProps` or `getStaticProps`:** These don't work with `output: 'export'` when there's no build-time data. All data fetching is client-side in `useEffect`.
- **CORS configuration:** Frontend and backend are same-origin. Adding CORS middleware is unnecessary and a maintenance burden.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Financial charting | Custom canvas chart | Lightweight Charts 5 | Time axis handling, crosshair, zoom, resize -- hundreds of edge cases |
| Treemap layout | Custom rectangle packing | Recharts `<Treemap>` | Squarified treemap algorithm is non-trivial; aspect ratio optimization |
| SSE reconnection | Custom reconnection logic | Native `EventSource` | Built-in retry with configurable `retry:` directive from server |
| CSS utility framework | Custom CSS design system | Tailwind CSS | Dark theme consistency, responsive utilities, design tokens |

**Key insight:** The charting libraries handle the hard problems (time axis normalization, responsive canvas, treemap layout algorithm). The SSE and sparkline parts are simple enough that native APIs and SVG are the right choice -- no library needed.

## Common Pitfalls

### Pitfall 1: Lightweight Charts in Next.js Static Export
**What goes wrong:** `createChart` accesses `document` and `window`, which don't exist during build/SSR.
**Why it happens:** Next.js pre-renders pages even with `output: 'export'`.
**How to avoid:** Mark chart components with `"use client"` directive. Use dynamic import with `{ ssr: false }` if needed: `const TickerChart = dynamic(() => import("./TickerChart"), { ssr: false })`.
**Warning signs:** "window is not defined" or "document is not defined" errors during `next build`.

### Pitfall 2: SSE EventSource Memory Leak
**What goes wrong:** EventSource connections left open when component unmounts or re-renders.
**Why it happens:** Missing cleanup in `useEffect`.
**How to avoid:** Always call `es.close()` in the useEffect cleanup function. Create the EventSource in a single top-level component/hook, not in every component that needs price data.
**Warning signs:** Multiple SSE connections visible in browser DevTools Network tab.

### Pitfall 3: Sparkline Data Grows Unbounded
**What goes wrong:** After hours of running, the sparkline data arrays consume excessive memory.
**Why it happens:** Every SSE tick appends to the array with no limit.
**How to avoid:** Cap the array at a reasonable length (e.g., 100-200 data points per ticker). Shift old entries when the limit is reached.
**Warning signs:** Increasing memory usage over time, sluggish UI after prolonged sessions.

### Pitfall 4: Static Export Path Mismatch
**What goes wrong:** FastAPI serves 404 for the frontend because the static directory path doesn't match.
**Why it happens:** `backend/app/main.py` currently resolves to `../../static` relative to `main.py`. The Next.js build outputs to `frontend/out/`.
**How to avoid:** Update `_static_dir` in `main.py` to point to `frontend/out/` (or copy `frontend/out/` to `static/` during build). The Dockerfile will handle this in Phase 5, but for development, update the path or create a symlink.
**Warning signs:** Blank page at `http://localhost:8000/`, 404 errors for `.js` and `.css` files.

### Pitfall 5: Recharts Treemap Custom Coloring
**What goes wrong:** Default Treemap uses a single color; P&L-based green/red coloring requires a custom content component.
**Why it happens:** Recharts Treemap doesn't natively support conditional coloring based on data values.
**How to avoid:** Pass a `content` prop with a custom React component that reads the node's P&L value and computes the fill color.
**Warning signs:** All treemap cells appear the same color.

### Pitfall 6: Tailwind CSS 4 Configuration Changes
**What goes wrong:** Tailwind v4 changed how configuration works -- `tailwind.config.ts` is no longer the primary configuration mechanism.
**Why it happens:** Tailwind v4 uses CSS-based configuration with `@theme` directive instead of JS config.
**How to avoid:** Use `@theme` in `globals.css` or keep using a `tailwind.config.ts` with the `@config` directive. The `create-next-app` template with `--tailwind` handles this correctly for the installed version.
**Warning signs:** Custom colors not applying, theme values not recognized.

## Code Examples

### Next.js Config for Static Export
```typescript
// next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  // Images need unoptimized for static export
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
```

### API Client Wrapper
```typescript
// lib/api.ts
const BASE = "";  // Same origin -- no prefix needed

export async function fetchWatchlist() {
  const res = await fetch(`${BASE}/api/watchlist`);
  if (!res.ok) throw new Error(`Watchlist fetch failed: ${res.status}`);
  return res.json();
}

export async function addTicker(ticker: string) {
  const res = await fetch(`${BASE}/api/watchlist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker }),
  });
  if (!res.ok) throw new Error(`Add ticker failed: ${res.status}`);
  return res.json();
}

export async function removeTicker(ticker: string) {
  const res = await fetch(`${BASE}/api/watchlist/${ticker}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Remove ticker failed: ${res.status}`);
  return res.json();
}

export async function fetchPortfolio() {
  const res = await fetch(`${BASE}/api/portfolio`);
  if (!res.ok) throw new Error(`Portfolio fetch failed: ${res.status}`);
  return res.json();
}

export async function executeTrade(ticker: string, quantity: number, side: "buy" | "sell") {
  const res = await fetch(`${BASE}/api/portfolio/trade`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker, quantity, side }),
  });
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || `Trade failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchPortfolioHistory() {
  const res = await fetch(`${BASE}/api/portfolio/history`);
  if (!res.ok) throw new Error(`History fetch failed: ${res.status}`);
  return res.json();
}

export async function sendChatMessage(content: string) {
  const res = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: content }),
  });
  if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
  return res.json();
}
```

### Recharts Treemap with P&L Coloring
```typescript
// components/PortfolioHeatmap.tsx
"use client";
import { Treemap, ResponsiveContainer } from "recharts";

interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  unrealized_pnl: number;
  pnl_percent: number;
}

function getPnLColor(pnlPercent: number): string {
  if (pnlPercent > 5) return "#22c55e";     // bright green
  if (pnlPercent > 0) return "#16a34a80";   // muted green
  if (pnlPercent === 0) return "#6b7280";   // gray
  if (pnlPercent > -5) return "#dc262680";  // muted red
  return "#dc2626";                          // bright red
}

function CustomContent(props: any) {
  const { x, y, width, height, ticker, pnl_percent } = props;
  if (width < 20 || height < 20) return null;

  return (
    <g>
      <rect
        x={x} y={y} width={width} height={height}
        fill={getPnLColor(pnl_percent)}
        stroke="#30363d" strokeWidth={2}
      />
      {width > 40 && height > 30 && (
        <>
          <text x={x + width / 2} y={y + height / 2 - 6} textAnchor="middle"
            fill="#fff" fontSize={12} fontWeight="bold">
            {ticker}
          </text>
          <text x={x + width / 2} y={y + height / 2 + 10} textAnchor="middle"
            fill="#c9d1d9" fontSize={10}>
            {pnl_percent >= 0 ? "+" : ""}{pnl_percent.toFixed(1)}%
          </text>
        </>
      )}
    </g>
  );
}

export function PortfolioHeatmap({ positions }: { positions: Position[] }) {
  const data = positions.map((p) => ({
    name: p.ticker,
    ticker: p.ticker,
    size: p.quantity * p.current_price, // position value = weight
    pnl_percent: p.pnl_percent,
  }));

  return (
    <ResponsiveContainer width="100%" height={200}>
      <Treemap
        data={data}
        dataKey="size"
        content={<CustomContent />}
      />
    </ResponsiveContainer>
  );
}
```

### TypeScript Interfaces for API Responses
```typescript
// lib/types.ts
export interface PriceUpdate {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: number;
  change: number;
  change_percent: number;
  direction: "up" | "down" | "flat";
}

export interface WatchlistItem {
  ticker: string;
  added_at: string;
  price: number | null;
  change: number | null;
  change_percent: number | null;
  direction: string | null;
}

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  unrealized_pnl: number;
  pnl_percent: number;
}

export interface Portfolio {
  cash: number;
  positions: Position[];
  total_value: number;
  total_pnl: number;
}

export interface TradeResult {
  trade: {
    id: string;
    ticker: string;
    side: "buy" | "sell";
    quantity: number;
    price: number;
    executed_at: string;
  };
  cash_balance: number;
}

export interface PortfolioSnapshot {
  total_value: number;
  recorded_at: string;
}

export interface ChatResponse {
  message: string;
  actions: {
    trades: Array<{ ticker: string; side: string; quantity: number; price: number; status: string }>;
    watchlist_changes: Array<{ ticker: string; action: string; status: string }>;
    errors: string[];
  };
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `next export` CLI command | `output: 'export'` in next.config | Next.js 14+ | Config-based, not a separate command |
| Tailwind CSS JS config only | CSS-first config with `@theme` | Tailwind v4 | May need `@config` directive for JS config |
| Lightweight Charts `addLineSeries()` | `chart.addSeries(LineSeries, opts)` | v5.0 | Modular series imports for tree-shaking |
| Recharts 2.x | Recharts 3.x | 2025 | Improved TypeScript, same component API |

**Deprecated/outdated:**
- `next export` command: removed, use `output: 'export'` in config
- `chart.addLineSeries()`: removed in lightweight-charts v5, use `chart.addSeries(LineSeries, ...)`
- `tailwind.config.js` as sole config: Tailwind v4 prefers CSS `@theme` but JS config still works via `@config`

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Next.js built-in (Jest or Vitest via next config) |
| Config file | none -- see Wave 0 |
| Quick run command | `cd frontend && npm test` |
| Full suite command | `cd frontend && npm test -- --coverage` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-01 | Dark theme renders with correct backgrounds | smoke | Visual inspection during dev | manual-only -- CSS theme |
| UI-02 | Header displays portfolio value, cash, connection dot | unit | `cd frontend && npm test -- Header.test.tsx` | Wave 0 |
| UI-03 | Accent colors applied correctly | smoke | Visual inspection | manual-only -- CSS theme |
| UI-04 | Layout renders all panels | unit | `cd frontend && npm test -- page.test.tsx` | Wave 0 |
| UI-05 | Watchlist renders tickers with prices | unit | `cd frontend && npm test -- Watchlist.test.tsx` | Wave 0 |
| UI-06 | Price flash class applied on price change | unit | `cd frontend && npm test -- WatchlistRow.test.tsx` | Wave 0 |
| UI-07 | Sparkline renders with data points | unit | `cd frontend && npm test -- Sparkline.test.tsx` | Wave 0 |
| UI-08 | Clicking ticker updates selected state | unit | `cd frontend && npm test -- Watchlist.test.tsx` | Wave 0 |
| UI-09 | Add/remove ticker calls API | unit | `cd frontend && npm test -- Watchlist.test.tsx` | Wave 0 |
| UI-10 | Chart component mounts without error | unit | `cd frontend && npm test -- TickerChart.test.tsx` | Wave 0 |
| UI-11 | Treemap renders positions with colors | unit | `cd frontend && npm test -- PortfolioHeatmap.test.tsx` | Wave 0 |
| UI-12 | P&L chart renders snapshot data | unit | `cd frontend && npm test -- PnLChart.test.tsx` | Wave 0 |
| UI-13 | Positions table renders all columns | unit | `cd frontend && npm test -- PositionsTable.test.tsx` | Wave 0 |
| UI-14 | Trade bar submits trade | unit | `cd frontend && npm test -- TradeBar.test.tsx` | Wave 0 |
| UI-15 | Chat panel renders messages | unit | `cd frontend && npm test -- ChatPanel.test.tsx` | Wave 0 |
| UI-16 | Loading indicator shown during chat | unit | `cd frontend && npm test -- ChatPanel.test.tsx` | Wave 0 |
| UI-17 | Action confirmations rendered in chat | unit | `cd frontend && npm test -- ChatPanel.test.tsx` | Wave 0 |
| UI-18 | EventSource connects and handles events | unit | `cd frontend && npm test -- useSSE.test.ts` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd frontend && npm test -- --watchAll=false`
- **Per wave merge:** `cd frontend && npm test -- --coverage --watchAll=false`
- **Phase gate:** Full suite green + visual inspection of running app against backend

### Wave 0 Gaps
- [ ] Test framework setup (Jest or Vitest config for Next.js)
- [ ] `__mocks__/` directory for EventSource mock
- [ ] Test utilities for mocking fetch responses
- [ ] Note: Lightweight Charts tests may need `jest-canvas-mock` or similar since it uses canvas

## Open Questions

1. **Tailwind CSS v4 config approach**
   - What we know: v4 moved to CSS-first configuration with `@theme`. `create-next-app --tailwind` generates the right setup for the installed version.
   - What's unclear: Whether the generated template uses `@theme` or a JS config file.
   - Recommendation: Use whatever `create-next-app` generates. Add custom colors in whichever format is produced. Both approaches work.

2. **Lightweight Charts time format**
   - What we know: The backend sends Unix timestamps (seconds). Lightweight Charts v5 accepts Unix timestamps for time values.
   - What's unclear: Whether the SSE timestamp is seconds or milliseconds.
   - Recommendation: Check the `PriceUpdate.timestamp` field format at implementation time. Lightweight Charts expects seconds -- divide by 1000 if backend sends milliseconds.

3. **Static directory path for development**
   - What we know: `main.py` resolves to `../../static`. Next.js outputs to `frontend/out/`.
   - What's unclear: Whether to update `main.py` now or wait for Dockerfile in Phase 5.
   - Recommendation: Update `_static_dir` in `main.py` to `frontend/out/` in this phase. The Dockerfile (Phase 5) can copy the output wherever needed.

## Sources

### Primary (HIGH confidence)
- npm registry: next@16.2.1, react@19.2.4, lightweight-charts@5.1.0, recharts@3.8.0, tailwindcss@4.2.2 -- verified via `npm view`
- [Next.js static export docs](https://nextjs.org/docs/app/guides/static-exports) -- `output: 'export'` configuration
- [Lightweight Charts React tutorial](https://tradingview.github.io/lightweight-charts/tutorials/react/simple) -- createChart + useRef pattern
- [Recharts Treemap API](https://recharts.github.io/en-US/api/Treemap/) -- custom content component
- Existing `backend/app/main.py` -- current static mount at line 85-89
- Existing `backend/app/market/stream.py` -- SSE event format

### Secondary (MEDIUM confidence)
- [TradingView Lightweight Charts v5 blog](https://www.tradingview.com/blog/en/tradingview-lightweight-charts-version-5-50837/) -- v5 API changes (modular series)
- WebSearch results for Tailwind v4 configuration changes

### Tertiary (LOW confidence)
- Tailwind CSS v4 `@theme` vs JS config -- exact behavior depends on `create-next-app` template version

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all versions verified via npm registry, APIs confirmed via official docs
- Architecture: HIGH - patterns verified from official tutorials and existing codebase
- Pitfalls: HIGH - well-documented Next.js static export limitations, Lightweight Charts SSR issues are widely reported
- Charting integration: MEDIUM - Lightweight Charts v5 API confirmed but React wrapper pattern sourced from tutorial, not production use

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (30 days -- stable ecosystem, no imminent breaking changes)
