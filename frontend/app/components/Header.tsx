"use client";

import type { ConnectionStatus } from "../lib/types";
import { formatCurrency } from "../lib/format";

interface HeaderProps {
  totalValue: number;
  cashBalance: number;
  connectionStatus: ConnectionStatus;
}

const statusColors: Record<ConnectionStatus, string> = {
  connected: "bg-profit",
  reconnecting: "bg-accent-yellow",
  disconnected: "bg-loss",
};

const statusLabels: Record<ConnectionStatus, string> = {
  connected: "Live",
  reconnecting: "Reconnecting...",
  disconnected: "Disconnected",
};

export default function Header({
  totalValue,
  cashBalance,
  connectionStatus,
}: HeaderProps) {
  return (
    <header className="flex items-center justify-between px-4 py-2 border-b border-border bg-surface">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-bold text-accent-yellow tracking-wide">
          FinAlly
        </h1>
        <span className="text-xs text-text-muted hidden sm:inline">
          AI Trading Workstation
        </span>
      </div>

      <div className="flex items-center gap-6">
        <div className="text-right">
          <div className="text-xs text-text-muted">Portfolio</div>
          <div className="text-sm font-bold text-foreground">
            {formatCurrency(totalValue)}
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs text-text-muted">Cash</div>
          <div className="text-sm font-medium text-text-secondary">
            {formatCurrency(cashBalance)}
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <div
            className={`w-2 h-2 rounded-full ${statusColors[connectionStatus]}`}
          />
          <span className="text-xs text-text-muted">
            {statusLabels[connectionStatus]}
          </span>
        </div>
      </div>
    </header>
  );
}
