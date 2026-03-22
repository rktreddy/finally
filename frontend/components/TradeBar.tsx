"use client";

/**
 * Trade execution form for buying and selling shares.
 *
 * Provides ticker and quantity inputs with buy/sell buttons. Submits market
 * orders via the portfolio trade API and displays inline success/error feedback.
 * The ticker field auto-syncs with the currently selected ticker from the watchlist.
 */

import { useEffect, useRef, useState } from "react";
import { executeTrade } from "../lib/api";

interface TradeBarProps {
  selectedTicker: string | null;
  onTradeComplete: () => void;
}

export default function TradeBar({ selectedTicker, onTradeComplete }: TradeBarProps) {
  const [ticker, setTicker] = useState(selectedTicker ?? "");
  const [quantity, setQuantity] = useState("");
  const [feedback, setFeedback] = useState<{
    message: string;
    type: "success" | "error";
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const feedbackTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync ticker state when selectedTicker prop changes
  useEffect(() => {
    if (selectedTicker) {
      setTicker(selectedTicker);
    }
  }, [selectedTicker]);

  const handleTrade = async (side: "buy" | "sell") => {
    const tickerValue = ticker.trim().toUpperCase();
    const qty = parseFloat(quantity);

    if (!tickerValue) {
      setFeedback({ message: "Enter a ticker symbol", type: "error" });
      return;
    }
    if (!quantity || qty <= 0 || isNaN(qty)) {
      setFeedback({ message: "Enter a valid quantity", type: "error" });
      return;
    }

    setLoading(true);
    setFeedback(null);

    try {
      const result = await executeTrade(tickerValue, qty, side);
      const action = side === "buy" ? "Bought" : "Sold";
      setFeedback({
        message: `${action} ${result.trade.quantity} ${result.trade.ticker} at $${result.trade.price.toFixed(2)}`,
        type: "success",
      });
      setQuantity("");
      onTradeComplete();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Trade failed";
      setFeedback({ message, type: "error" });
    } finally {
      setLoading(false);
    }

    // Clear feedback after 3 seconds
    if (feedbackTimeoutRef.current) {
      clearTimeout(feedbackTimeoutRef.current);
    }
    feedbackTimeoutRef.current = setTimeout(() => setFeedback(null), 3000);
  };

  return (
    <div className="bg-[#1a1a2e] border border-[#30363d] rounded-lg p-3">
      <div className="flex items-center gap-3 flex-wrap">
        <input
          type="text"
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          placeholder="TICKER"
          className="bg-[#0d1117] border border-[#30363d] text-[#e6edf3] rounded px-3 py-2 w-24 uppercase placeholder:text-[#484f58] focus:outline-none focus:border-[#209dd7]"
        />

        <input
          type="number"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          placeholder="QTY"
          min="0"
          step="any"
          className="bg-[#0d1117] border border-[#30363d] text-[#e6edf3] rounded px-3 py-2 w-24 placeholder:text-[#484f58] focus:outline-none focus:border-[#209dd7]"
        />

        <button
          type="button"
          onClick={() => handleTrade("buy")}
          disabled={loading}
          className="bg-[#209dd7] hover:bg-[#209dd7]/80 text-white font-bold px-6 py-2 rounded disabled:opacity-50 disabled:cursor-not-allowed"
        >
          BUY
        </button>

        <button
          type="button"
          onClick={() => handleTrade("sell")}
          disabled={loading}
          className="bg-[#753991] hover:bg-[#753991]/80 text-white font-bold px-6 py-2 rounded disabled:opacity-50 disabled:cursor-not-allowed"
        >
          SELL
        </button>

        {/* Inline feedback */}
        {feedback && (
          <span
            className={`text-sm ${
              feedback.type === "success" ? "text-green-400" : "text-red-400"
            }`}
          >
            {feedback.message}
          </span>
        )}
      </div>
    </div>
  );
}
