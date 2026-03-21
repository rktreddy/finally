"use client";

import { useEffect, useState, useCallback } from "react";
import type { PortfolioSnapshot } from "../lib/types";
import { getPortfolioHistory } from "../lib/api";

interface PnLChartProps {
  refreshTrigger: number;
}

export default function PnLChart({ refreshTrigger }: PnLChartProps) {
  const [snapshots, setSnapshots] = useState<PortfolioSnapshot[]>([]);

  const load = useCallback(async () => {
    try {
      const data = await getPortfolioHistory();
      setSnapshots(data);
    } catch {
      // retry on next trigger
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, refreshTrigger]);

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, [load]);

  if (snapshots.length < 2) {
    return (
      <div className="flex items-center justify-center h-full text-xs text-text-muted">
        Portfolio history will appear here
      </div>
    );
  }

  const values = snapshots.map((s) => s.total_value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const isUp = values[values.length - 1] >= values[0];

  const w = 100;
  const h = 100;
  const padding = 5;

  const points = values
    .map((v, i) => {
      const x = padding + (i / (values.length - 1)) * (w - padding * 2);
      const y = h - padding - ((v - min) / range) * (h - padding * 2);
      return `${x},${y}`;
    })
    .join(" ");

  const fillPoints = `${padding},${h - padding} ${points} ${w - padding},${h - padding}`;
  const color = isUp ? "#3fb950" : "#f85149";
  const fillColor = isUp ? "rgba(63,185,80,0.1)" : "rgba(248,81,73,0.1)";

  return (
    <div className="h-full p-2 flex flex-col">
      <div className="flex justify-between text-xs text-text-muted mb-1">
        <span>Portfolio Value</span>
        <span
          className={isUp ? "text-profit" : "text-loss"}
        >
          ${values[values.length - 1].toFixed(2)}
        </span>
      </div>
      <svg viewBox={`0 0 ${w} ${h}`} className="flex-1 w-full" preserveAspectRatio="none">
        <polygon points={fillPoints} fill={fillColor} />
        <polyline
          points={points}
          fill="none"
          stroke={color}
          strokeWidth="1"
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
    </div>
  );
}
