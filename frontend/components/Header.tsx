"use client";

/**
 * Header bar for the trading terminal.
 *
 * Displays the FinAlly logo, live portfolio total value, cash balance,
 * and a connection status indicator dot (green/yellow/red) showing
 * the state of the SSE connection to the backend.
 */

import type { ConnectionStatus } from "../lib/types";

interface HeaderProps {
  totalValue: number;
  cash: number;
  status: ConnectionStatus;
}

const currencyFormat = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

export default function Header({ totalValue, cash, status }: HeaderProps) {
  const statusColor =
    status === "connected"
      ? "bg-green-500"
      : status === "reconnecting"
        ? "bg-yellow-500"
        : "bg-red-500";

  return (
    <header className="h-14 bg-[#1a1a2e] border-b border-[#30363d] flex items-center justify-between px-4 shrink-0">
      {/* Left: Logo */}
      <div className="flex items-center gap-2">
        <span className="text-[#ecad0a] font-bold text-xl tracking-tight">
          FinAlly
        </span>
      </div>

      {/* Center: Portfolio value and cash */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="text-[#8b949e] text-xs uppercase tracking-wider">
            Portfolio
          </span>
          <span className="text-[#e6edf3] font-bold tabular-nums">
            {currencyFormat.format(totalValue)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[#8b949e] text-xs uppercase tracking-wider">
            Cash
          </span>
          <span className="text-[#e6edf3] font-bold tabular-nums">
            {currencyFormat.format(cash)}
          </span>
        </div>
      </div>

      {/* Right: Connection status */}
      <div className="flex items-center gap-2">
        <div className={`w-2.5 h-2.5 rounded-full ${statusColor}`} />
        <span className="text-[#8b949e] text-xs capitalize">{status}</span>
      </div>
    </header>
  );
}
