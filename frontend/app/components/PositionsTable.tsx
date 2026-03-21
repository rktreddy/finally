"use client";

import type { Position } from "../lib/types";
import { formatCurrency, formatPercent, formatQuantity } from "../lib/format";

interface PositionsTableProps {
  positions: Position[];
}

export default function PositionsTable({ positions }: PositionsTableProps) {
  if (positions.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-xs text-text-muted">
        No open positions
      </div>
    );
  }

  return (
    <div className="overflow-auto h-full">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-surface">
          <tr className="text-text-muted uppercase tracking-wider border-b border-border">
            <th className="text-left px-3 py-2 font-medium">Ticker</th>
            <th className="text-right px-3 py-2 font-medium">Qty</th>
            <th className="text-right px-3 py-2 font-medium">Avg Cost</th>
            <th className="text-right px-3 py-2 font-medium">Price</th>
            <th className="text-right px-3 py-2 font-medium">P&L</th>
            <th className="text-right px-3 py-2 font-medium">%</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((pos) => (
            <tr
              key={pos.ticker}
              className="border-b border-border-light hover:bg-surface-hover transition-colors"
            >
              <td className="px-3 py-1.5 font-bold text-foreground">
                {pos.ticker}
              </td>
              <td className="px-3 py-1.5 text-right text-text-secondary">
                {formatQuantity(pos.quantity)}
              </td>
              <td className="px-3 py-1.5 text-right text-text-secondary">
                {formatCurrency(pos.avg_cost)}
              </td>
              <td className="px-3 py-1.5 text-right text-foreground">
                {formatCurrency(pos.current_price)}
              </td>
              <td
                className={`px-3 py-1.5 text-right font-medium ${
                  pos.unrealized_pnl >= 0 ? "text-profit" : "text-loss"
                }`}
              >
                {formatCurrency(pos.unrealized_pnl)}
              </td>
              <td
                className={`px-3 py-1.5 text-right ${
                  pos.pnl_pct >= 0 ? "text-profit" : "text-loss"
                }`}
              >
                {formatPercent(pos.pnl_pct)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
