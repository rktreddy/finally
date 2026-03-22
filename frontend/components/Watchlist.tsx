"use client";

/**
 * Full watchlist panel with add/remove ticker controls.
 *
 * Displays all watched tickers with live prices from the SSE price map,
 * sparkline mini-charts from price history, and controls to add or remove
 * tickers. Clicking a ticker selects it for the main chart view.
 */

import { useState } from "react";
import { addTicker, removeTicker } from "../lib/api";
import type { PriceMap, WatchlistItem } from "../lib/types";
import WatchlistRow from "./WatchlistRow";

interface WatchlistProps {
  watchlist: WatchlistItem[];
  prices: PriceMap;
  getHistory: (ticker: string) => { time: number; value: number }[];
  selectedTicker: string | null;
  onSelectTicker: (ticker: string) => void;
  onRefresh: () => void;
}

export default function Watchlist({
  watchlist,
  prices,
  getHistory,
  selectedTicker,
  onSelectTicker,
  onRefresh,
}: WatchlistProps) {
  const [addInput, setAddInput] = useState("");

  const handleAdd = async () => {
    const ticker = addInput.trim().toUpperCase();
    if (!ticker) return;
    try {
      await addTicker(ticker);
      onRefresh();
      setAddInput("");
    } catch (err) {
      console.error("Failed to add ticker:", err);
    }
  };

  const handleRemove = async (ticker: string) => {
    try {
      await removeTicker(ticker);
      onRefresh();
    } catch (err) {
      console.error("Failed to remove ticker:", err);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleAdd();
    }
  };

  return (
    <div className="bg-[#1a1a2e] border border-[#30363d] rounded-lg flex flex-col">
      {/* Header */}
      <div className="px-3 pt-3 pb-2">
        <h2 className="text-[#8b949e] text-xs uppercase tracking-wider mb-2">
          Watchlist
        </h2>

        {/* Add ticker input */}
        <div className="flex gap-2">
          <input
            type="text"
            value={addInput}
            onChange={(e) => setAddInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="TICKER"
            className="bg-[#0d1117] border border-[#30363d] rounded px-2 py-1 text-sm text-[#e6edf3] uppercase flex-1 placeholder:text-[#484f58] focus:outline-none focus:border-[#209dd7]"
          />
          <button
            type="button"
            onClick={handleAdd}
            className="bg-[#209dd7] text-white px-3 py-1 rounded text-sm hover:bg-[#209dd7]/80 font-medium"
          >
            Add
          </button>
        </div>
      </div>

      {/* Ticker rows */}
      <div className="overflow-y-auto max-h-[400px] divide-y divide-[#30363d]/50">
        {watchlist.map((item) => {
          const livePrice = prices[item.ticker];
          return (
            <WatchlistRow
              key={item.ticker}
              ticker={item.ticker}
              price={livePrice?.price ?? item.price}
              change={livePrice?.change ?? item.change}
              changePercent={livePrice?.change_percent ?? item.change_percent}
              direction={livePrice?.direction ?? item.direction}
              sparklineData={getHistory(item.ticker).map((h) => h.value)}
              isSelected={selectedTicker === item.ticker}
              onSelect={onSelectTicker}
              onRemove={handleRemove}
            />
          );
        })}
        {watchlist.length === 0 && (
          <div className="px-3 py-4 text-[#8b949e] text-sm text-center">
            No tickers in watchlist
          </div>
        )}
      </div>
    </div>
  );
}
