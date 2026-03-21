"""FastAPI application for FinAlly — AI Trading Workstation."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db import get_connection, get_portfolio, record_snapshot, get_watchlist
from app.market import PriceCache, create_market_data_source
from app.market.stream import router as stream_router
from app.routes import health, portfolio, watchlist, chat

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


async def _snapshot_loop(app: FastAPI, interval: float = 30.0) -> None:
    """Background task: record portfolio value snapshot every `interval` seconds."""
    while True:
        await asyncio.sleep(interval)
        try:
            price_cache: PriceCache = app.state.price_cache
            port = await get_portfolio()
            total = port["cash_balance"]
            for pos in port["positions"]:
                p = price_cache.get_price(pos["ticker"])
                if p is not None:
                    total += pos["quantity"] * p
                else:
                    total += pos["quantity"] * pos["avg_cost"]
            await record_snapshot(total)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Error recording portfolio snapshot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # --- Startup ---
    # 1. Initialize DB (lazy init on first connection)
    db = await get_connection()
    await db.close()
    logger.info("Database initialized")

    # 2. Create price cache and market data source
    price_cache = PriceCache()
    market_data = create_market_data_source(price_cache)

    # Store on app.state for route access
    app.state.price_cache = price_cache
    app.state.market_data_source = market_data

    # 3. Get watchlist tickers and start market data
    wl = await get_watchlist()
    tickers = [entry["ticker"] for entry in wl]
    await market_data.start(tickers)
    logger.info("Market data source started with %d tickers", len(tickers))

    # 4. Start portfolio snapshot background task
    snapshot_task = asyncio.create_task(_snapshot_loop(app))

    yield

    # --- Shutdown ---
    snapshot_task.cancel()
    try:
        await snapshot_task
    except asyncio.CancelledError:
        pass

    await market_data.stop()
    logger.info("Market data source stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="FinAlly",
        description="AI Trading Workstation",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Include API routers (must be before static mount so they take precedence)
    app.include_router(health.router)
    app.include_router(portfolio.router)
    app.include_router(watchlist.router)
    app.include_router(chat.router)
    app.include_router(stream_router)

    # Serve static frontend files (if directory exists)
    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app


app = create_app()
