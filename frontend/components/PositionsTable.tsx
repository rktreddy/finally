"use client";

/**
 * Positions table showing all current holdings.
 *
 * Displays ticker, quantity, average cost, current price (live from SSE),
 * unrealized P&L, and percentage change with green/red coloring.
 */

import type { Position, PriceMap } from "../lib/types";

interface PositionsTableProps {
  positions: Position[];
  prices: PriceMap;
}

const fmt = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

export default function PositionsTable({ positions, prices }: PositionsTableProps) {
  return (
    <div className="bg-[#1a1a2e] border border-[#30363d] rounded-lg p-3 overflow-auto">
      <h3 className="text-[#8b949e] text-xs uppercase tracking-wider mb-2">
        Positions
      </h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[#8b949e] text-xs uppercase tracking-wider border-b border-[#30363d]">
            <th className="text-left py-1 pr-2">Ticker</th>
            <th className="text-right py-1 pr-2">Qty</th>
            <th className="text-right py-1 pr-2">Avg Cost</th>
            <th className="text-right py-1 pr-2">Price</th>
            <th className="text-right py-1 pr-2">P&L</th>
            <th className="text-right py-1">%</th>
          </tr>
        </thead>
        <tbody>
          {positions.length === 0 ? (
            <tr>
              <td colSpan={6} className="text-[#8b949e] text-center py-4">
                No positions
              </td>
            </tr>
          ) : (
            positions.map((pos) => {
              const livePrice = prices[pos.ticker]?.price ?? pos.current_price;
              const pnl = (livePrice - pos.avg_cost) * pos.quantity;
              const pnlPct =
                pos.avg_cost > 0
                  ? ((livePrice - pos.avg_cost) / pos.avg_cost) * 100
                  : 0;
              const pnlColor = pnl >= 0 ? "text-green-400" : "text-red-400";

              return (
                <tr
                  key={pos.ticker}
                  className="border-b border-[#30363d]/50"
                >
                  <td className="font-bold text-[#e6edf3] py-1 pr-2">
                    {pos.ticker}
                  </td>
                  <td className="text-right text-[#e6edf3] py-1 pr-2 tabular-nums">
                    {pos.quantity.toFixed(2)}
                  </td>
                  <td className="text-right text-[#e6edf3] py-1 pr-2 tabular-nums">
                    {fmt.format(pos.avg_cost)}
                  </td>
                  <td className="text-right text-[#e6edf3] py-1 pr-2 tabular-nums">
                    {fmt.format(livePrice)}
                  </td>
                  <td className={`text-right py-1 pr-2 tabular-nums ${pnlColor}`}>
                    {pnl >= 0 ? "+" : ""}
                    {fmt.format(pnl)}
                  </td>
                  <td className={`text-right py-1 tabular-nums ${pnlColor}`}>
                    {pnlPct >= 0 ? "+" : ""}
                    {pnlPct.toFixed(2)}%
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
