"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import type { PriceUpdate, TickerPrice, ConnectionStatus } from "../lib/types";

const MAX_HISTORY = 50;

export function usePriceStream() {
  const [prices, setPrices] = useState<Record<string, TickerPrice>>({});
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>("disconnected");
  const [flashTickers, setFlashTickers] = useState<
    Record<string, "up" | "down">
  >({});
  const flashTimeouts = useRef<Record<string, NodeJS.Timeout>>({});
  const eventSourceRef = useRef<EventSource | null>(null);

  const handlePriceUpdate = useCallback((update: PriceUpdate) => {
    setPrices((prev) => {
      const existing = prev[update.ticker];
      const history = existing ? [...existing.history, update.price] : [update.price];
      if (history.length > MAX_HISTORY) history.shift();

      const change = update.price - update.previous_price;
      const change_pct =
        update.previous_price !== 0
          ? (change / update.previous_price) * 100
          : 0;

      return {
        ...prev,
        [update.ticker]: {
          ticker: update.ticker,
          price: update.price,
          previous_price: update.previous_price,
          change,
          change_pct,
          direction: update.direction,
          timestamp: update.timestamp,
          history,
        },
      };
    });

    if (update.direction === "up" || update.direction === "down") {
      const dir: "up" | "down" = update.direction;
      setFlashTickers((prev) => ({
        ...prev,
        [update.ticker]: dir,
      }));

      // Clear flash after animation
      if (flashTimeouts.current[update.ticker]) {
        clearTimeout(flashTimeouts.current[update.ticker]);
      }
      flashTimeouts.current[update.ticker] = setTimeout(() => {
        setFlashTickers((prev) => {
          const next = { ...prev };
          delete next[update.ticker];
          return next;
        });
      }, 500);
    }
  }, []);

  useEffect(() => {
    const connect = () => {
      const es = new EventSource("/api/stream/prices");
      eventSourceRef.current = es;

      es.onopen = () => setConnectionStatus("connected");

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (Array.isArray(data)) {
            data.forEach(handlePriceUpdate);
          } else if (data && typeof data === "object" && !data.ticker) {
            // SSE sends {AAPL: {...}, AMZN: {...}} — iterate values
            Object.values(data).forEach((update) =>
              handlePriceUpdate(update as PriceUpdate)
            );
          } else {
            handlePriceUpdate(data as PriceUpdate);
          }
        } catch {
          // ignore parse errors
        }
      };

      es.onerror = () => {
        setConnectionStatus("reconnecting");
        // EventSource auto-reconnects
      };
    };

    connect();

    return () => {
      eventSourceRef.current?.close();
      Object.values(flashTimeouts.current).forEach(clearTimeout);
    };
  }, [handlePriceUpdate]);

  return { prices, connectionStatus, flashTickers };
}
