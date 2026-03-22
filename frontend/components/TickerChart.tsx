"use client";

/**
 * Main chart area displaying price-over-time for the selected ticker.
 *
 * Uses Lightweight Charts library with a dark terminal theme. The chart
 * updates reactively as new price data arrives from the SSE stream.
 * Only imports the charting library on the client side to avoid SSR issues.
 */

import { useEffect, useRef } from "react";
import type { IChartApi, ISeriesApi, UTCTimestamp } from "lightweight-charts";

interface TickerChartProps {
  ticker: string | null;
  data: { time: number; value: number }[];
}

export default function TickerChart({ ticker, data }: TickerChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  // Create chart on mount
  useEffect(() => {
    if (!containerRef.current || !ticker) return;

    let chart: IChartApi | null = null;
    let resizeObserver: ResizeObserver | null = null;

    const initChart = async () => {
      const { createChart, LineSeries } = await import("lightweight-charts");

      if (!containerRef.current) return;

      chart = createChart(containerRef.current, {
        layout: {
          background: { color: "#0d1117" },
          textColor: "#c9d1d9",
        },
        grid: {
          vertLines: { color: "#30363d" },
          horzLines: { color: "#30363d" },
        },
        width: containerRef.current.clientWidth,
        height: 300,
        timeScale: {
          timeVisible: true,
          secondsVisible: true,
        },
      });

      const series = chart.addSeries(LineSeries, {
        color: "#209dd7",
        lineWidth: 2,
      });

      chartRef.current = chart;
      seriesRef.current = series;

      // Set initial data
      if (data.length > 0) {
        series.setData(
          data.map((d) => ({ time: d.time as unknown as number, value: d.value }))
        );
      }

      // Resize observer to keep chart width in sync
      resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
          if (chart && entry.contentRect.width > 0) {
            chart.applyOptions({ width: entry.contentRect.width });
          }
        }
      });
      resizeObserver.observe(containerRef.current);
    };

    initChart();

    return () => {
      resizeObserver?.disconnect();
      if (chart) {
        chart.remove();
      }
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [ticker]); // eslint-disable-line react-hooks/exhaustive-deps

  // Update data when it changes
  useEffect(() => {
    if (seriesRef.current && data.length > 0) {
      seriesRef.current.setData(
        data.map((d) => ({ time: d.time as unknown as number, value: d.value }))
      );
    }
  }, [data]);

  if (!ticker) {
    return (
      <div className="bg-[#1a1a2e] border border-[#30363d] rounded-lg p-3 flex items-center justify-center h-[340px]">
        <span className="text-[#8b949e]">Select a ticker from the watchlist</span>
      </div>
    );
  }

  return (
    <div className="bg-[#1a1a2e] border border-[#30363d] rounded-lg p-3">
      <h3 className="text-[#ecad0a] font-bold text-lg mb-2">{ticker}</h3>
      <div ref={containerRef} className="w-full" />
    </div>
  );
}
