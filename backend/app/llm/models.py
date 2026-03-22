"""Pydantic models for LLM structured output."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TradeAction(BaseModel):
    """A trade action for the LLM to execute."""

    ticker: str
    side: str
    quantity: float


class WatchlistAction(BaseModel):
    """A watchlist modification for the LLM to execute."""

    ticker: str
    action: str


class ChatResponse(BaseModel):
    """Structured response from the LLM chat assistant.

    The LLM returns JSON matching this schema. The message field is always present;
    trades and watchlist_changes are optional action arrays that get auto-executed.
    """

    message: str
    trades: list[TradeAction] = Field(default_factory=list)
    watchlist_changes: list[WatchlistAction] = Field(default_factory=list)
