"""FinAlly backend application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from app.db import get_db_path, init_db
from app.market import PriceCache, create_market_data_source, create_stream_router
from app.routes.health import router as health_router
from app.routes.watchlist import router as watchlist_router

logger = logging.getLogger(__name__)

# Create PriceCache at module level so stream router can capture it
price_cache = PriceCache()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of all subsystems."""
    # --- Startup ---

    # Database (D-01, D-03)
    db_path = get_db_path()
    logger.info("Initializing database at %s", db_path)
    db = await init_db(db_path)
    app.state.db = db

    # Market data (D-04, D-09)
    app.state.cache = price_cache
    source = create_market_data_source(price_cache)
    app.state.source = source

    # Get seed tickers from DB and start market data
    async with db.execute(
        "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at",
        ("default",),
    ) as cursor:
        rows = await cursor.fetchall()
        tickers = [row[0] for row in rows]

    logger.info("Starting market data source with %d tickers", len(tickers))
    await source.start(tickers)

    yield

    # --- Shutdown (D-03) ---
    logger.info("Shutting down market data source")
    await source.stop()
    logger.info("Closing database connection")
    await db.close()


app = FastAPI(title="FinAlly", lifespan=lifespan)

# API routes FIRST (D-13)
app.include_router(health_router, prefix="/api")
app.include_router(watchlist_router, prefix="/api")
app.include_router(create_stream_router(price_cache))

# Static files LAST -- catch-all for frontend (D-12, D-13)
# Resolve static directory relative to project root
_static_dir = Path(__file__).resolve().parent.parent.parent / "static"
if _static_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
else:
    logger.warning("Static directory not found at %s -- skipping static file mount", _static_dir)
