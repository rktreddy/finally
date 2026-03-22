"use client";

/**
 * P&L history chart using Recharts LineChart.
 *
 * Displays portfolio total value over time as a line chart,
 * sourced from portfolio_snapshots recorded every 30 seconds.
 */

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { PortfolioSnapshot } from "../lib/types";

interface PnLChartProps {
  snapshots: PortfolioSnapshot[];
}

export default function PnLChart({ snapshots }: PnLChartProps) {
  if (snapshots.length === 0) {
    return (
      <div className="bg-[#1a1a2e] border border-[#30363d] rounded-lg p-3">
        <h3 className="text-[#8b949e] text-xs uppercase tracking-wider mb-2">
          P&L History
        </h3>
        <p className="text-[#8b949e] text-sm">No history data</p>
      </div>
    );
  }

  const chartData = snapshots.map((s) => ({
    time: new Date(s.recorded_at).toLocaleTimeString(),
    value: s.total_value,
  }));

  return (
    <div className="bg-[#1a1a2e] border border-[#30363d] rounded-lg p-3">
      <h3 className="text-[#8b949e] text-xs uppercase tracking-wider mb-2">
        P&L History
      </h3>
      <ResponsiveContainer width="100%" height={150}>
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 5, bottom: 5, left: 5 }}
        >
          <XAxis
            dataKey="time"
            tick={{ fill: "#8b949e", fontSize: 10 }}
            hide={chartData.length > 20}
          />
          <YAxis
            tick={{ fill: "#8b949e", fontSize: 10 }}
            domain={["auto", "auto"]}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1a1a2e",
              border: "1px solid #30363d",
              color: "#e6edf3",
            }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#ecad0a"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
