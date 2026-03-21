"use client";

import { useState } from "react";
import { executeTrade } from "../lib/api";

interface TradeBarProps {
  onTradeExecuted: () => void;
  defaultTicker?: string;
}

export default function TradeBar({
  onTradeExecuted,
  defaultTicker = "",
}: TradeBarProps) {
  const [ticker, setTicker] = useState(defaultTicker);
  const [quantity, setQuantity] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleTrade = async (side: "buy" | "sell") => {
    const qty = parseFloat(quantity);
    if (!ticker.trim() || isNaN(qty) || qty <= 0) {
      setError("Enter a valid ticker and quantity");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await executeTrade({
        ticker: ticker.toUpperCase().trim(),
        quantity: qty,
        side,
      });
      setQuantity("");
      onTradeExecuted();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Trade failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center gap-2 p-2 border-t border-border bg-surface">
      <input
        type="text"
        value={ticker}
        onChange={(e) => {
          setTicker(e.target.value.toUpperCase());
          setError(null);
        }}
        placeholder="TICKER"
        className="w-20 px-2 py-1 text-xs bg-background border border-border rounded text-foreground placeholder:text-text-muted focus:outline-none focus:border-accent-blue"
      />
      <input
        type="number"
        value={quantity}
        onChange={(e) => {
          setQuantity(e.target.value);
          setError(null);
        }}
        placeholder="QTY"
        min="0"
        step="1"
        className="w-20 px-2 py-1 text-xs bg-background border border-border rounded text-foreground placeholder:text-text-muted focus:outline-none focus:border-accent-blue"
      />
      <button
        onClick={() => handleTrade("buy")}
        disabled={loading}
        className="px-3 py-1 text-xs font-bold bg-profit/20 text-profit border border-profit/30 rounded hover:bg-profit/30 disabled:opacity-50 transition-colors"
      >
        BUY
      </button>
      <button
        onClick={() => handleTrade("sell")}
        disabled={loading}
        className="px-3 py-1 text-xs font-bold bg-loss/20 text-loss border border-loss/30 rounded hover:bg-loss/30 disabled:opacity-50 transition-colors"
      >
        SELL
      </button>
      {error && (
        <span className="text-xs text-loss truncate max-w-48">{error}</span>
      )}
    </div>
  );
}
