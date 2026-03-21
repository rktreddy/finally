"use client";

import { useEffect, useState, useCallback } from "react";
import type { TickerPrice } from "../lib/types";
import { getWatchlist, addToWatchlist, removeFromWatchlist } from "../lib/api";
import { formatPrice, formatPercent } from "../lib/format";
import Sparkline from "./Sparkline";

interface WatchlistProps {
  prices: Record<string, TickerPrice>;
  flashTickers: Record<string, "up" | "down">;
  selectedTicker: string | null;
  onSelectTicker: (ticker: string) => void;
}

export default function Watchlist({
  prices,
  flashTickers,
  selectedTicker,
  onSelectTicker,
}: WatchlistProps) {
  const [tickers, setTickers] = useState<string[]>([]);
  const [newTicker, setNewTicker] = useState("");
  const [showAdd, setShowAdd] = useState(false);

  const loadWatchlist = useCallback(async () => {
    try {
      const items = await getWatchlist();
      setTickers(items.map((i) => i.ticker));
    } catch {
      // Will retry on next load
    }
  }, []);

  useEffect(() => {
    loadWatchlist();
  }, [loadWatchlist]);

  const handleAdd = async () => {
    const t = newTicker.trim().toUpperCase();
    if (!t) return;
    try {
      await addToWatchlist(t);
      setNewTicker("");
      setShowAdd(false);
      loadWatchlist();
    } catch {
      // ignore
    }
  };

  const handleRemove = async (ticker: string) => {
    try {
      await removeFromWatchlist(ticker);
      loadWatchlist();
    } catch {
      // ignore
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border">
        <h2 className="text-xs font-bold text-text-muted uppercase tracking-wider">
          Watchlist
        </h2>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="text-xs text-accent-blue hover:text-accent-yellow transition-colors"
        >
          {showAdd ? "Cancel" : "+ Add"}
        </button>
      </div>

      {showAdd && (
        <div className="flex items-center gap-1 px-3 py-1.5 border-b border-border">
          <input
            type="text"
            value={newTicker}
            onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            placeholder="TICKER"
            className="flex-1 px-2 py-1 text-xs bg-background border border-border rounded text-foreground placeholder:text-text-muted focus:outline-none focus:border-accent-blue"
            autoFocus
          />
          <button
            onClick={handleAdd}
            className="px-2 py-1 text-xs bg-accent-purple text-white rounded hover:opacity-80"
          >
            Add
          </button>
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        {tickers.map((ticker) => {
          const p = prices[ticker];
          const flash = flashTickers[ticker];
          const isSelected = selectedTicker === ticker;

          return (
            <div
              key={ticker}
              onClick={() => onSelectTicker(ticker)}
              className={`flex items-center justify-between px-3 py-1.5 cursor-pointer border-b border-border-light hover:bg-surface-hover transition-colors ${
                isSelected ? "bg-surface-hover border-l-2 border-l-accent-blue" : ""
              } ${flash === "up" ? "flash-green" : flash === "down" ? "flash-red" : ""}`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-xs font-bold text-foreground w-12 flex-shrink-0">
                  {ticker}
                </span>
                {p && p.history.length > 1 && (
                  <Sparkline data={p.history} width={60} height={20} />
                )}
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                {p ? (
                  <>
                    <span className="text-xs font-mono text-foreground w-16 text-right">
                      {formatPrice(p.price)}
                    </span>
                    <span
                      className={`text-xs font-mono w-16 text-right ${
                        p.change_pct >= 0 ? "text-profit" : "text-loss"
                      }`}
                    >
                      {formatPercent(p.change_pct)}
                    </span>
                  </>
                ) : (
                  <span className="text-xs text-text-muted">--</span>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemove(ticker);
                  }}
                  className="text-text-muted hover:text-loss text-xs opacity-0 group-hover:opacity-100 hover:opacity-100 ml-1"
                  title="Remove"
                >
                  x
                </button>
              </div>
            </div>
          );
        })}
        {tickers.length === 0 && (
          <div className="px-3 py-4 text-xs text-text-muted text-center">
            No tickers in watchlist
          </div>
        )}
      </div>
    </div>
  );
}
