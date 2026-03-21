"use client";

import { useState, useRef, useEffect } from "react";
import type { ChatMessage } from "../lib/types";
import { sendChatMessage } from "../lib/api";

interface ChatPanelProps {
  onTradeExecuted: () => void;
  onWatchlistChanged: () => void;
}

export default function ChatPanel({
  onTradeExecuted,
  onWatchlistChanged,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const msg = input.trim();
    if (!msg || loading) return;

    const userMsg: ChatMessage = { role: "user", content: msg };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const response = await sendChatMessage(msg);

      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: response.message,
        actions: {
          trades: response.trades,
          watchlist_changes: response.watchlist_changes,
        },
      };
      setMessages((prev) => [...prev, assistantMsg]);

      if (response.trades && response.trades.length > 0) {
        onTradeExecuted();
      }
      if (response.watchlist_changes && response.watchlist_changes.length > 0) {
        onWatchlistChanged();
      }
    } catch (e) {
      const errorMsg: ChatMessage = {
        role: "assistant",
        content: `Error: ${e instanceof Error ? e.message : "Failed to get response"}`,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 px-4 py-2 bg-accent-purple text-white text-sm rounded-lg shadow-lg hover:opacity-90 transition-opacity z-50"
      >
        AI Chat
      </button>
    );
  }

  return (
    <div className="flex flex-col h-full border-l border-border bg-surface">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border">
        <h2 className="text-xs font-bold text-text-muted uppercase tracking-wider">
          AI Assistant
        </h2>
        <button
          onClick={() => setIsOpen(false)}
          className="text-text-muted hover:text-foreground text-xs"
        >
          Minimize
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.length === 0 && (
          <div className="text-xs text-text-muted text-center py-8">
            Ask about your portfolio, request trades, or get market analysis.
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}>
            <div
              className={`max-w-[90%] px-3 py-2 rounded-lg text-xs leading-relaxed ${
                msg.role === "user"
                  ? "bg-accent-purple/20 text-foreground"
                  : "bg-background text-text-secondary"
              }`}
            >
              {msg.content}
            </div>
            {msg.actions?.trades && msg.actions.trades.length > 0 && (
              <div className="mt-1 max-w-[90%]">
                {msg.actions.trades.map((t, j) => (
                  <div
                    key={j}
                    className={`text-xs px-2 py-1 rounded mt-0.5 ${
                      t.success !== false
                        ? "bg-profit/10 text-profit"
                        : "bg-loss/10 text-loss"
                    }`}
                  >
                    {t.success !== false ? "Executed" : "Failed"}:{" "}
                    {t.side?.toUpperCase()} {t.quantity} {t.ticker}{" "}
                    {t.price ? `@ $${t.price.toFixed(2)}` : ""}
                    {t.error && ` - ${t.error}`}
                  </div>
                ))}
              </div>
            )}
            {msg.actions?.watchlist_changes &&
              msg.actions.watchlist_changes.length > 0 && (
                <div className="mt-1 max-w-[90%]">
                  {msg.actions.watchlist_changes.map((w, j) => (
                    <div
                      key={j}
                      className="text-xs px-2 py-1 rounded bg-accent-blue/10 text-accent-blue mt-0.5"
                    >
                      {w.action === "add" ? "Added" : "Removed"} {w.ticker}{" "}
                      {w.action === "add" ? "to" : "from"} watchlist
                    </div>
                  ))}
                </div>
              )}
          </div>
        ))}
        {loading && (
          <div className="flex items-start">
            <div className="px-3 py-2 rounded-lg bg-background text-text-muted text-xs">
              <span className="animate-pulse">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-2 border-t border-border">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder="Ask about your portfolio..."
            disabled={loading}
            className="flex-1 px-3 py-1.5 text-xs bg-background border border-border rounded text-foreground placeholder:text-text-muted focus:outline-none focus:border-accent-blue disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="px-3 py-1.5 text-xs font-bold bg-accent-purple text-white rounded hover:opacity-80 disabled:opacity-50 transition-opacity"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
