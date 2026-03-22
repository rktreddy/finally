/**
 * Fetch wrappers for all backend API endpoints.
 *
 * All functions use same-origin fetch (no base URL prefix needed).
 * Non-ok responses throw errors with status info. Trade errors
 * parse the response body for the `detail` field from FastAPI.
 */

import type {
  ChatResponse,
  Portfolio,
  PortfolioSnapshot,
  TradeResult,
  WatchlistItem,
} from "./types";

export async function fetchWatchlist(): Promise<WatchlistItem[]> {
  const res = await fetch("/api/watchlist");
  if (!res.ok) throw new Error(`Watchlist fetch failed: ${res.status}`);
  return res.json();
}

export async function addTicker(ticker: string): Promise<Record<string, string>> {
  const res = await fetch("/api/watchlist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Add ticker failed: ${res.status}`);
  }
  return res.json();
}

export async function removeTicker(ticker: string): Promise<Record<string, string>> {
  const res = await fetch(`/api/watchlist/${ticker}`, { method: "DELETE" });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Remove ticker failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchPortfolio(): Promise<Portfolio> {
  const res = await fetch("/api/portfolio");
  if (!res.ok) throw new Error(`Portfolio fetch failed: ${res.status}`);
  return res.json();
}

export async function executeTrade(
  ticker: string,
  quantity: number,
  side: "buy" | "sell"
): Promise<TradeResult> {
  const res = await fetch("/api/portfolio/trade", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker, quantity, side }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Trade failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchPortfolioHistory(): Promise<{ snapshots: PortfolioSnapshot[] }> {
  const res = await fetch("/api/portfolio/history");
  if (!res.ok) throw new Error(`History fetch failed: ${res.status}`);
  return res.json();
}

export async function sendChatMessage(message: string): Promise<ChatResponse> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Chat failed: ${res.status}`);
  }
  return res.json();
}
