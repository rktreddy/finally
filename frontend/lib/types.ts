/**
 * TypeScript interfaces matching all backend API response shapes.
 *
 * These types are the single source of truth for frontend-backend contracts.
 * Each interface corresponds to a specific API endpoint response format.
 */

export interface PriceUpdate {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: number;
  change: number;
  change_percent: number;
  direction: "up" | "down" | "flat";
}

export type PriceMap = Record<string, PriceUpdate>;

export interface WatchlistItem {
  ticker: string;
  added_at: string;
  price: number | null;
  change: number | null;
  change_percent: number | null;
  direction: string | null;
}

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  unrealized_pnl: number;
  pnl_percent: number;
}

export interface Portfolio {
  cash: number;
  positions: Position[];
  total_value: number;
  total_pnl: number;
}

export interface TradeResult {
  trade: {
    id: string;
    ticker: string;
    side: "buy" | "sell";
    quantity: number;
    price: number;
    executed_at: string;
  };
  cash_balance: number;
}

export interface PortfolioSnapshot {
  total_value: number;
  recorded_at: string;
}

export interface ChatResponse {
  message: string;
  actions: {
    trades: Array<{
      ticker: string;
      side: string;
      quantity: number;
      price: number;
      status: string;
    }>;
    watchlist_changes: Array<{
      ticker: string;
      action: string;
      status: string;
    }>;
    errors: string[];
  };
}

export type ConnectionStatus = "connected" | "reconnecting" | "disconnected";
