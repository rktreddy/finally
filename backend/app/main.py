"""
FinAlly backend — FastAPI application entry point.

Mounts:
  /api/stream/*  — SSE streaming (market data)
  /api/health    — Health check

The database, portfolio, watchlist, and chat routers are added by other agents
as they build out those features. Market data is wired up here.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.market_data.base import price_cache
from app.market_data.provider import get_provider
from app.routers.stream import router as stream_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default watchlist tickers (seeded into the provider on startup)
_DEFAULT_TICKERS = [
    "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
    "NVDA", "META", "JPM", "V", "NFLX",
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Start market data provider on startup; stop it on shutdown."""
    provider = get_provider()
    for ticker in _DEFAULT_TICKERS:
        provider.add_ticker(ticker)
    await provider.start()
    logger.info("Market data provider started (%s)", type(provider).__name__)

    yield

    await provider.stop()
    logger.info("Market data provider stopped")


app = FastAPI(title="FinAlly Backend", lifespan=lifespan)

# Market data streaming
app.include_router(stream_router, prefix="/api")


@app.get("/api/health")
async def health() -> dict:
    provider = get_provider()
    return {
        "status": "ok",
        "provider": type(provider).__name__,
        "tickers": sorted(provider.tickers),
        "cached_prices": len(price_cache.get_all()),
    }


# Serve Next.js static export — must be last so /api/* routes take priority.
# The static/ directory is populated by the Docker multi-stage build.
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(_STATIC_DIR):
    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
