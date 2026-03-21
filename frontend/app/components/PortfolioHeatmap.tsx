"use client";

import type { Position } from "../lib/types";
import { formatCurrency, formatPercent } from "../lib/format";

interface PortfolioHeatmapProps {
  positions: Position[];
}

function getColor(pnlPct: number): string {
  if (pnlPct > 5) return "bg-profit/40";
  if (pnlPct > 2) return "bg-profit/30";
  if (pnlPct > 0) return "bg-profit/20";
  if (pnlPct > -2) return "bg-loss/20";
  if (pnlPct > -5) return "bg-loss/30";
  return "bg-loss/40";
}

function getTextColor(pnlPct: number): string {
  return pnlPct >= 0 ? "text-profit" : "text-loss";
}

export default function PortfolioHeatmap({ positions }: PortfolioHeatmapProps) {
  if (positions.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-xs text-text-muted">
        No positions to display
      </div>
    );
  }

  const totalValue = positions.reduce((sum, p) => sum + p.market_value, 0);

  return (
    <div className="flex flex-wrap gap-1 p-2 h-full content-start">
      {positions.map((pos) => {
        const weight = totalValue > 0 ? pos.market_value / totalValue : 0;
        const minWidth = Math.max(60, weight * 400);

        return (
          <div
            key={pos.ticker}
            className={`${getColor(pos.pnl_pct)} rounded p-2 flex flex-col justify-center items-center transition-colors`}
            style={{
              flexBasis: `${Math.max(20, weight * 100)}%`,
              flexGrow: 1,
              minWidth: `${minWidth}px`,
              minHeight: "60px",
            }}
          >
            <span className="text-xs font-bold text-foreground">
              {pos.ticker}
            </span>
            <span className={`text-xs ${getTextColor(pos.pnl_pct)}`}>
              {formatCurrency(pos.unrealized_pnl)}
            </span>
            <span className={`text-xs ${getTextColor(pos.pnl_pct)}`}>
              {formatPercent(pos.pnl_pct)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
