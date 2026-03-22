"use client";

/**
 * Single ticker row in the watchlist panel.
 *
 * Displays ticker symbol, current price, change percentage, and a sparkline.
 * Applies a brief green/red background flash on price changes that fades
 * over ~500ms via CSS transitions.
 */

import { useEffect, useRef, useState } from "react";
import Sparkline from "./Sparkline";

interface WatchlistRowProps {
  ticker: string;
  price: number | null;
  change: number | null;
  changePercent: number | null;
  direction: string | null;
  sparklineData: number[];
  isSelected: boolean;
  onSelect: (ticker: string) => void;
  onRemove: (ticker: string) => void;
}

export default function WatchlistRow({
  ticker,
  price,
  change,
  changePercent,
  direction,
  sparklineData,
  isSelected,
  onSelect,
  onRemove,
}: WatchlistRowProps) {
  const [flash, setFlash] = useState<"up" | "down" | null>(null);
  const prevPriceRef = useRef(price);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (price !== null && prevPriceRef.current !== price) {
      if (direction === "up") {
        setFlash("up");
      } else if (direction === "down") {
        setFlash("down");
      }
      prevPriceRef.current = price;

      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      timeoutRef.current = setTimeout(() => {
        setFlash(null);
      }, 500);
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [price, direction]);

  const flashBg =
    flash === "up"
      ? "bg-[rgba(34,197,94,0.25)]"
      : flash === "down"
        ? "bg-[rgba(239,68,68,0.25)]"
        : "bg-transparent";

  const changeColor =
    change !== null && change > 0
      ? "text-green-400"
      : change !== null && change < 0
        ? "text-red-400"
        : "text-[#8b949e]";

  const formatPercent = (pct: number | null) => {
    if (pct === null) return "--";
    const sign = pct > 0 ? "+" : "";
    return `${sign}${pct.toFixed(2)}%`;
  };

  return (
    <div
      className={`flex items-center gap-3 px-3 py-2 transition-colors duration-500 cursor-pointer ${flashBg} ${
        isSelected ? "border-l-2 border-[#209dd7]" : "border-l-2 border-transparent"
      }`}
      onClick={() => onSelect(ticker)}
    >
      <span className="font-bold text-[#e6edf3] w-16 shrink-0">{ticker}</span>

      <span className="text-[#e6edf3] w-20 text-right tabular-nums shrink-0">
        {price !== null ? price.toFixed(2) : "--"}
      </span>

      <span className={`w-20 text-right text-sm tabular-nums shrink-0 ${changeColor}`}>
        {formatPercent(changePercent)}
      </span>

      <div className="shrink-0">
        <Sparkline data={sparklineData} />
      </div>

      <button
        type="button"
        className="ml-auto text-[#8b949e] hover:text-red-400 text-sm leading-none px-1"
        onClick={(e) => {
          e.stopPropagation();
          onRemove(ticker);
        }}
        aria-label={`Remove ${ticker}`}
      >
        x
      </button>
    </div>
  );
}
