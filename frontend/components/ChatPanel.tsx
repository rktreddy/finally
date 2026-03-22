"use client";

/**
 * AI chat panel for the trading terminal.
 *
 * Sends messages to the LLM backend, displays responses with loading indicator,
 * and renders inline confirmations for trade executions and watchlist changes.
 */

import { useState, useRef, useEffect } from "react";
import { sendChatMessage } from "../lib/api";
import type { ChatResponse } from "../lib/types";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  actions?: ChatResponse["actions"];
}

interface ChatPanelProps {
  onTradeExecuted: () => void;
}

export default function ChatPanel({ onTradeExecuted }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setLoading(true);

    try {
      const response = await sendChatMessage(text);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.message,
          actions: response.actions,
        },
      ]);

      const hasTradeActions = response.actions?.trades?.length > 0;
      const hasWatchlistActions = response.actions?.watchlist_changes?.length > 0;
      if (hasTradeActions || hasWatchlistActions) {
        onTradeExecuted();
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Something went wrong";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${errorMsg}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-[#1a1a2e] border border-[#30363d] rounded-lg flex flex-col flex-1 min-h-0">
      <h3 className="text-[#8b949e] text-xs uppercase tracking-wider p-3 pb-0">
        AI Assistant
      </h3>

      {/* Messages area */}
      <div ref={scrollRef} className="overflow-y-auto flex-1 p-3 space-y-3">
        {messages.length === 0 && (
          <p className="text-[#8b949e] text-sm">
            Ask your AI assistant about your portfolio, market analysis, or to execute trades.
          </p>
        )}

        {messages.map((msg, i) => (
          <div key={i}>
            <div
              className={`rounded-lg px-3 py-2 text-sm max-w-[90%] ${
                msg.role === "user"
                  ? "bg-[#209dd7]/20 text-[#e6edf3] ml-auto"
                  : "bg-[#0d1117] text-[#e6edf3]"
              }`}
            >
              {msg.content}
            </div>

            {/* Action confirmations */}
            {msg.role === "assistant" && msg.actions && (
              <div className="mt-2 space-y-1">
                {msg.actions.trades?.map((trade, j) => (
                  <div
                    key={`trade-${j}`}
                    className="border-l-2 border-green-500 bg-green-900/20 px-3 py-1 text-sm text-[#e6edf3]"
                  >
                    {trade.side === "buy" ? "Bought" : "Sold"} {trade.quantity}{" "}
                    {trade.ticker} at ${trade.price.toFixed(2)}
                    {trade.status !== "success" && (
                      <span className="text-red-400 ml-2">({trade.status})</span>
                    )}
                  </div>
                ))}
                {msg.actions.watchlist_changes?.map((change, j) => (
                  <div
                    key={`wl-${j}`}
                    className="border-l-2 border-[#209dd7] bg-[#209dd7]/10 px-3 py-1 text-sm text-[#e6edf3]"
                  >
                    {change.action === "add" ? "Added" : "Removed"}{" "}
                    {change.ticker} {change.action === "add" ? "to" : "from"}{" "}
                    watchlist
                    {change.status !== "success" && (
                      <span className="text-red-400 ml-2">({change.status})</span>
                    )}
                  </div>
                ))}
                {msg.actions.errors?.map((error, j) => (
                  <div
                    key={`err-${j}`}
                    className="border-l-2 border-red-500 bg-red-900/20 px-3 py-1 text-sm text-red-400"
                  >
                    {error}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        {/* Loading indicator */}
        {loading && (
          <div className="bg-[#0d1117] rounded-lg px-3 py-2 text-sm text-[#8b949e] animate-pulse">
            Thinking...
          </div>
        )}
      </div>

      {/* Input area */}
      <form onSubmit={handleSubmit} className="p-3 pt-0 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask your AI assistant..."
          disabled={loading}
          className="bg-[#0d1117] border border-[#30363d] text-[#e6edf3] rounded-lg px-3 py-2 flex-1 text-sm placeholder-[#8b949e] focus:outline-none focus:border-[#209dd7] disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="bg-[#753991] hover:bg-[#753991]/80 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Send
        </button>
      </form>
    </div>
  );
}
