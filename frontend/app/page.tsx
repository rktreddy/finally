"use client";

import { useState, useEffect, useCallback } from "react";
import Header from "./components/Header";
import Watchlist from "./components/Watchlist";
import PriceChart from "./components/PriceChart";
import PositionsTable from "./components/PositionsTable";
import PortfolioHeatmap from "./components/PortfolioHeatmap";
import PnLChart from "./components/PnLChart";
import TradeBar from "./components/TradeBar";
import ChatPanel from "./components/ChatPanel";
import { usePriceStream } from "./hooks/usePriceStream";
import { getPortfolio } from "./lib/api";
import type { Portfolio } from "./lib/types";

export default function Home() {
  const { prices, connectionStatus, flashTickers } = usePriceStream();
  const [portfolio, setPortfolio] = useState<Portfolio>({
    positions: [],
    cash_balance: 10000,
    total_value: 10000,
  });
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const loadPortfolio = useCallback(async () => {
    try {
      const data = await getPortfolio();
      setPortfolio(data);
    } catch {
      // retry on next trigger
    }
  }, []);

  useEffect(() => {
    loadPortfolio();
  }, [loadPortfolio]);

  // Refresh portfolio every 10s to get updated prices
  useEffect(() => {
    const interval = setInterval(loadPortfolio, 10000);
    return () => clearInterval(interval);
  }, [loadPortfolio]);

  const handleTradeExecuted = () => {
    loadPortfolio();
    setRefreshTrigger((n) => n + 1);
  };

  // Update positions with live prices from SSE
  const livePositions = portfolio.positions.map((pos) => {
    const livePrice = prices[pos.ticker];
    if (!livePrice) return pos;
    const currentPrice = livePrice.price;
    const marketValue = currentPrice * pos.quantity;
    const unrealizedPnl = (currentPrice - pos.avg_cost) * pos.quantity;
    const pnlPct = pos.avg_cost > 0 ? ((currentPrice - pos.avg_cost) / pos.avg_cost) * 100 : 0;
    return {
      ...pos,
      current_price: currentPrice,
      market_value: marketValue,
      unrealized_pnl: unrealizedPnl,
      pnl_pct: pnlPct,
    };
  });

  const liveTotalValue =
    portfolio.cash_balance +
    livePositions.reduce((sum, p) => sum + p.market_value, 0);

  return (
    <div className="flex flex-col h-full bg-background">
      <Header
        totalValue={liveTotalValue}
        cashBalance={portfolio.cash_balance}
        connectionStatus={connectionStatus}
      />

      <div className="flex flex-1 min-h-0">
        {/* Left sidebar - Watchlist */}
        <div className="w-64 flex-shrink-0 border-r border-border flex flex-col">
          <Watchlist
            prices={prices}
            flashTickers={flashTickers}
            selectedTicker={selectedTicker}
            onSelectTicker={setSelectedTicker}
          />
        </div>

        {/* Main content area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Top row: Chart + Heatmap */}
          <div className="flex flex-1 min-h-0">
            {/* Price chart */}
            <div className="flex-1 border-b border-border border-r border-border p-1">
              <PriceChart
                ticker={selectedTicker}
                priceData={selectedTicker ? prices[selectedTicker] : undefined}
              />
            </div>
            {/* Portfolio heatmap */}
            <div className="w-72 flex-shrink-0 border-b border-border">
              <div className="px-3 py-2 border-b border-border">
                <h2 className="text-xs font-bold text-text-muted uppercase tracking-wider">
                  Portfolio Heatmap
                </h2>
              </div>
              <PortfolioHeatmap positions={livePositions} />
            </div>
          </div>

          {/* Bottom row: Positions + P&L Chart */}
          <div className="flex h-48 flex-shrink-0">
            {/* Positions table */}
            <div className="flex-1 border-r border-border flex flex-col">
              <div className="px-3 py-2 border-b border-border">
                <h2 className="text-xs font-bold text-text-muted uppercase tracking-wider">
                  Positions
                </h2>
              </div>
              <div className="flex-1 overflow-auto">
                <PositionsTable positions={livePositions} />
              </div>
            </div>
            {/* P&L Chart */}
            <div className="w-72 flex-shrink-0 flex flex-col">
              <div className="px-3 py-2 border-b border-border">
                <h2 className="text-xs font-bold text-text-muted uppercase tracking-wider">
                  P&L History
                </h2>
              </div>
              <div className="flex-1">
                <PnLChart refreshTrigger={refreshTrigger} />
              </div>
            </div>
          </div>

          {/* Trade bar */}
          <TradeBar
            onTradeExecuted={handleTradeExecuted}
            defaultTicker={selectedTicker || ""}
          />
        </div>

        {/* Right sidebar - Chat */}
        <div className="w-80 flex-shrink-0">
          <ChatPanel
            onTradeExecuted={handleTradeExecuted}
            onWatchlistChanged={() => setRefreshTrigger((n) => n + 1)}
          />
        </div>
      </div>
    </div>
  );
}
