"use client";

import { useEffect, useRef } from "react";
import type { TickerPrice } from "../lib/types";

interface PriceChartProps {
  ticker: string | null;
  priceData: TickerPrice | undefined;
}

export default function PriceChart({ ticker, priceData }: PriceChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !priceData || priceData.history.length < 2) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    const padding = { top: 20, right: 60, bottom: 30, left: 10 };
    const chartW = w - padding.left - padding.right;
    const chartH = h - padding.top - padding.bottom;

    const data = priceData.history;
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;

    // Clear
    ctx.clearRect(0, 0, w, h);

    // Grid lines
    ctx.strokeStyle = "#30363d";
    ctx.lineWidth = 0.5;
    const gridLines = 5;
    for (let i = 0; i <= gridLines; i++) {
      const y = padding.top + (i / gridLines) * chartH;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(w - padding.right, y);
      ctx.stroke();

      // Price label
      const val = max - (i / gridLines) * range;
      ctx.fillStyle = "#8b949e";
      ctx.font = "10px monospace";
      ctx.textAlign = "left";
      ctx.fillText(`$${val.toFixed(2)}`, w - padding.right + 5, y + 4);
    }

    // Price line
    const isUp = data[data.length - 1] >= data[0];
    ctx.strokeStyle = isUp ? "#3fb950" : "#f85149";
    ctx.lineWidth = 2;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.beginPath();

    for (let i = 0; i < data.length; i++) {
      const x = padding.left + (i / (data.length - 1)) * chartW;
      const y = padding.top + ((max - data[i]) / range) * chartH;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Fill gradient
    const gradient = ctx.createLinearGradient(0, padding.top, 0, h - padding.bottom);
    gradient.addColorStop(0, isUp ? "rgba(63,185,80,0.15)" : "rgba(248,81,73,0.15)");
    gradient.addColorStop(1, "rgba(0,0,0,0)");

    ctx.lineTo(padding.left + chartW, padding.top + chartH);
    ctx.lineTo(padding.left, padding.top + chartH);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // Current price label
    const lastPrice = data[data.length - 1];
    const lastY = padding.top + ((max - lastPrice) / range) * chartH;
    ctx.fillStyle = isUp ? "#3fb950" : "#f85149";
    ctx.font = "bold 11px monospace";
    ctx.textAlign = "right";
    ctx.fillText(`$${lastPrice.toFixed(2)}`, w - padding.right - 5, lastY - 8);

    // Ticker label
    ctx.fillStyle = "#e6edf3";
    ctx.font = "bold 14px monospace";
    ctx.textAlign = "left";
    ctx.fillText(ticker || "", padding.left + 5, padding.top - 5);
  }, [ticker, priceData]);

  if (!ticker) {
    return (
      <div className="flex items-center justify-center h-full text-xs text-text-muted">
        Select a ticker to view chart
      </div>
    );
  }

  if (!priceData || priceData.history.length < 2) {
    return (
      <div className="flex items-center justify-center h-full text-xs text-text-muted">
        Waiting for price data for {ticker}...
      </div>
    );
  }

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full"
      style={{ display: "block" }}
    />
  );
}
