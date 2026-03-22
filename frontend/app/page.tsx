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
import Watchlist from "../components/Watchlist";
import TickerChart from "../components/TickerChart";
import TradeBar from "../components/TradeBar";
import PortfolioHeatmap from "../components/PortfolioHeatmap";
import PnLChart from "../components/PnLChart";
import PositionsTable from "../components/PositionsTable";
import ChatPanel from "../components/ChatPanel";
import { useSSE } from "../hooks/useSSE";
import {
  fetchPortfolio,
  fetchPortfolioHistory,
  fetchWatchlist,
} from "../lib/api";
import type { Portfolio, PortfolioSnapshot, WatchlistItem } from "../lib/types";

export default function Home() {
  const { prices, status, getHistory } = useSSE();
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [snapshots, setSnapshots] = useState<PortfolioSnapshot[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  const refreshData = useCallback(async () => {
    try {
      const [wl, pf, hist] = await Promise.all([
        fetchWatchlist(),
        fetchPortfolio(),
        fetchPortfolioHistory(),
      ]);
      setWatchlist(wl);
      setPortfolio(pf);
      setSnapshots(hist.snapshots);
    } catch (err) {
      console.error("Failed to refresh data:", err);
    }
  }, []);

  useEffect(() => {
    refreshData();
  }, [refreshData]);

  // Compute live total value from SSE prices when available
  const positions = portfolio?.positions ?? [];
  const liveTotalValue =
    positions.length > 0
      ? (portfolio?.cash ?? 0) +
        positions.reduce((sum, pos) => {
          const livePrice = prices[pos.ticker]?.price ?? pos.current_price;
          return sum + pos.quantity * livePrice;
        }, 0)
      : (portfolio?.total_value ?? 10000);

  return (
    <div className="h-screen flex flex-col bg-[#0d1117]">
      <Header
        totalValue={liveTotalValue}
        cash={portfolio?.cash ?? 0}
        status={status}
      />

      <div className="flex-1 grid grid-cols-[1fr_350px] gap-2 p-2 overflow-hidden">
        {/* Left column */}
        <div className="flex flex-col gap-2 overflow-hidden">
          <Watchlist
            watchlist={watchlist}
            prices={prices}
            getHistory={getHistory}
            selectedTicker={selectedTicker}
            onSelectTicker={setSelectedTicker}
            onRefresh={refreshData}
          />

          <TickerChart
            ticker={selectedTicker}
            data={selectedTicker ? getHistory(selectedTicker) : []}
          />

          <div className="grid grid-cols-2 gap-2">
            <TradeBar
              selectedTicker={selectedTicker}
              onTradeComplete={refreshData}
            />
            <PositionsTable
              positions={positions}
              prices={prices}
            />
          </div>
        </div>

        {/* Right column */}
        <div className="flex flex-col gap-2 overflow-hidden">
          <PortfolioHeatmap positions={positions} />
          <PnLChart snapshots={snapshots} />
          <ChatPanel onTradeExecuted={refreshData} />
        </div>
      </div>
    </div>
  );
}
