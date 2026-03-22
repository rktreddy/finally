"use client";

/**
 * Custom hook for SSE price streaming via EventSource.
 *
 * Manages a single EventSource connection to /api/stream/prices,
 * tracks connection status, and accumulates per-ticker price history
 * for sparklines and charts. History arrays are capped at 200 entries.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { ConnectionStatus, PriceMap } from "../lib/types";

const MAX_HISTORY_POINTS = 200;

export function useSSE() {
  const [prices, setPrices] = useState<PriceMap>({});
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const priceHistoryRef = useRef<Record<string, { time: number; value: number }[]>>({});

  useEffect(() => {
    const es = new EventSource("/api/stream/prices");

    es.onopen = () => setStatus("connected");

    es.onmessage = (event) => {
      const data: PriceMap = JSON.parse(event.data);
      setPrices(data);

      // Accumulate sparkline/chart data per ticker
      for (const [ticker, update] of Object.entries(data)) {
        if (!priceHistoryRef.current[ticker]) {
          priceHistoryRef.current[ticker] = [];
        }
        const history = priceHistoryRef.current[ticker];
        history.push({
          time: update.timestamp,
          value: update.price,
        });
        // Cap at MAX_HISTORY_POINTS to prevent unbounded memory growth
        if (history.length > MAX_HISTORY_POINTS) {
          history.shift();
        }
      }
    };

    es.onerror = () => setStatus("reconnecting");

    return () => {
      es.close();
      setStatus("disconnected");
    };
  }, []);

  const getHistory = useCallback(
    (ticker: string) => priceHistoryRef.current[ticker] || [],
    []
  );

  return { prices, status, getHistory };
}
