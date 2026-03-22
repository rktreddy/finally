"use client";

/**
 * Main trading terminal page.
 *
 * Single-page layout with CSS grid containing all panels:
 * watchlist, chart, trade bar, positions, portfolio heatmap,
 * P&L chart, and AI chat. Fetches initial data on mount and
 * connects to the SSE price stream.
 */

import { useCallback, useEffect, useState } from "react";
import Header from "../components/Header";
import { useSSE } from "../hooks/useSSE";
import { fetchPortfolio, fetchWatchlist } from "../lib/api";
import type { Portfolio, WatchlistItem } from "../lib/types";

export default function Home() {
  const { prices, status } = useSSE();
  const [portfolio, setPortfolio] = useState<Portfolio>({
    cash: 10000,
    positions: [],
    total_value: 10000,
    total_pnl: 0,
  });
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);

  const refreshData = useCallback(async () => {
    try {
      const [portfolioData, watchlistData] = await Promise.all([
        fetchPortfolio(),
        fetchWatchlist(),
      ]);
      setPortfolio(portfolioData);
      setWatchlist(watchlistData);
    } catch (err) {
      console.error("Failed to refresh data:", err);
    }
  }, []);

  // Fetch initial data on mount
  useEffect(() => {
    refreshData();
  }, [refreshData]);

  // Compute live total value from SSE prices when available
  const liveTotalValue =
    portfolio.positions.length > 0
      ? portfolio.cash +
        portfolio.positions.reduce((sum, pos) => {
          const livePrice = prices[pos.ticker]?.price ?? pos.current_price;
          return sum + pos.quantity * livePrice;
        }, 0)
      : portfolio.total_value;

  return (
    <div className="flex flex-col h-screen">
      <Header
        totalValue={liveTotalValue}
        cash={portfolio.cash}
        status={status}
      />

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[1fr_350px] gap-2 p-2 overflow-hidden">
        {/* Left column */}
        <div className="flex flex-col gap-2 min-h-0">
          {/* Watchlist panel */}
          <div className="bg-[#1a1a2e] border border-[#30363d] rounded-lg p-3 overflow-y-auto max-h-[280px]">
            <h2 className="text-[#8b949e] text-xs uppercase tracking-wider mb-2">
              Watchlist
            </h2>
            <div className="text-[#8b949e] text-sm">
              {watchlist.length} tickers loaded
            </div>
          </div>

          {/* Main chart area */}
          <div className="bg-[#1a1a2e] border border-[#30363d] rounded-lg p-3 flex-1 min-h-[200px]">
            <h2 className="text-[#8b949e] text-xs uppercase tracking-wider mb-2">
              Chart
            </h2>
            <div className="text-[#8b949e] text-sm">
              Select a ticker to view chart
            </div>
          </div>

          {/* Trade bar + Positions */}
          <div className="flex flex-col gap-2">
            <div className="bg-[#1a1a2e] border border-[#30363d] rounded-lg p-3">
              <h2 className="text-[#8b949e] text-xs uppercase tracking-wider mb-2">
                Trade
              </h2>
              <div className="text-[#8b949e] text-sm">
                Trade bar placeholder
              </div>
            </div>

            <div className="bg-[#1a1a2e] border border-[#30363d] rounded-lg p-3 overflow-y-auto max-h-[200px]">
              <h2 className="text-[#8b949e] text-xs uppercase tracking-wider mb-2">
                Positions
              </h2>
              <div className="text-[#8b949e] text-sm">
                {portfolio.positions.length} positions
              </div>
            </div>
          </div>
        </div>

        {/* Right column */}
        <div className="flex flex-col gap-2 min-h-0">
          {/* Portfolio heatmap */}
          <div className="bg-[#1a1a2e] border border-[#30363d] rounded-lg p-3">
            <h2 className="text-[#8b949e] text-xs uppercase tracking-wider mb-2">
              Portfolio
            </h2>
            <div className="text-[#8b949e] text-sm">
              Heatmap placeholder
            </div>
          </div>

          {/* P&L Chart */}
          <div className="bg-[#1a1a2e] border border-[#30363d] rounded-lg p-3">
            <h2 className="text-[#8b949e] text-xs uppercase tracking-wider mb-2">
              P&L
            </h2>
            <div className="text-[#8b949e] text-sm">
              P&L chart placeholder
            </div>
          </div>

          {/* Chat panel */}
          <div className="bg-[#1a1a2e] border border-[#30363d] rounded-lg p-3 flex-1 min-h-[200px]">
            <h2 className="text-[#8b949e] text-xs uppercase tracking-wider mb-2">
              Chat
            </h2>
            <div className="text-[#8b949e] text-sm">
              AI assistant placeholder
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
