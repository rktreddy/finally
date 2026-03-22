"use client";

/**
 * Portfolio heatmap using a Recharts Treemap.
 *
 * Each rectangle represents a position, sized by portfolio weight
 * (quantity * current_price) and colored by P&L percentage
 * (green for profit, red for loss).
 */

import { Treemap, ResponsiveContainer } from "recharts";
import type { Position } from "../lib/types";

interface PortfolioHeatmapProps {
  positions: Position[];
}

function getColor(pnlPercent: number): string {
  if (pnlPercent > 5) return "#22c55e";
  if (pnlPercent > 0) return "rgba(22,163,74,0.5)";
  if (pnlPercent === 0) return "#6b7280";
  if (pnlPercent > -5) return "rgba(220,38,38,0.5)";
  return "#dc2626";
}

interface CustomContentProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  ticker?: string;
  pnl_percent?: number;
}

function CustomContent(props: CustomContentProps) {
  const { x = 0, y = 0, width = 0, height = 0, ticker, pnl_percent = 0 } = props;

  if (width < 20 || height < 20) return null;

  const fill = getColor(pnl_percent);

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={fill}
        stroke="#30363d"
        strokeWidth={2}
      />
      {width > 40 && height > 30 && (
        <>
          <text
            x={x + width / 2}
            y={y + height / 2 - 6}
            textAnchor="middle"
            fill="white"
            fontSize={12}
            fontWeight="bold"
          >
            {ticker}
          </text>
          <text
            x={x + width / 2}
            y={y + height / 2 + 10}
            textAnchor="middle"
            fill="white"
            fontSize={10}
          >
            {pnl_percent >= 0 ? "+" : ""}
            {pnl_percent.toFixed(1)}%
          </text>
        </>
      )}
    </g>
  );
}

export default function PortfolioHeatmap({ positions }: PortfolioHeatmapProps) {
  if (positions.length === 0) {
    return (
      <div className="bg-[#1a1a2e] border border-[#30363d] rounded-lg p-3">
        <h3 className="text-[#8b949e] text-xs uppercase tracking-wider mb-2">
          Portfolio
        </h3>
        <p className="text-[#8b949e] text-sm">No positions yet</p>
      </div>
    );
  }

  const data = positions.map((p) => ({
    name: p.ticker,
    ticker: p.ticker,
    size: Math.abs(p.quantity * p.current_price),
    pnl_percent: p.pnl_percent,
  }));

  return (
    <div className="bg-[#1a1a2e] border border-[#30363d] rounded-lg p-3">
      <h3 className="text-[#8b949e] text-xs uppercase tracking-wider mb-2">
        Portfolio
      </h3>
      <ResponsiveContainer width="100%" height={200}>
        <Treemap
          data={data}
          dataKey="size"
          content={<CustomContent />}
        />
      </ResponsiveContainer>
    </div>
  );
}
