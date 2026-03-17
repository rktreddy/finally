"""
SSE streaming router — GET /api/stream/prices

Streams live price updates to connected clients using Server-Sent Events.
Clients use the native EventSource API; reconnection is handled automatically.

Each event payload is a JSON object:
{
  "ticker": "AAPL",
  "price": 190.50,
  "previous_price": 189.80,
  "timestamp": "2024-01-15T10:30:00.000Z",
  "change_direction": "up"
}
"""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.market_data.base import price_cache
from app.market_data.provider import get_provider

logger = logging.getLogger(__name__)

router = APIRouter()

# How often to push a snapshot of all current prices to the client (seconds)
_PUSH_INTERVAL = 0.5


@router.get("/stream/prices")
async def stream_prices() -> StreamingResponse:
    """
    Long-lived SSE endpoint that pushes price updates for all watched tickers.

    The server pushes a batch of price updates every ~500ms. Each event
    contains data for one ticker. When the client disconnects, the generator
    exits cleanly.
    """
    return StreamingResponse(
        _price_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
            "Connection": "keep-alive",
        },
    )


async def _price_event_generator() -> AsyncGenerator[str, None]:
    """Async generator that yields SSE-formatted price events."""
    # Send an initial comment to establish the connection immediately
    yield ": connected\n\n"

    while True:
        try:
            await asyncio.sleep(_PUSH_INTERVAL)

            provider = get_provider()
            tracked = provider.tickers

            all_prices = price_cache.get_all()
            if not all_prices and not tracked:
                # Nothing to stream yet — keep connection alive with a comment
                yield ": heartbeat\n\n"
                continue

            for ticker, update in all_prices.items():
                if ticker not in tracked:
                    continue
                payload = {
                    "ticker": update.ticker,
                    "price": update.price,
                    "previous_price": update.previous_price,
                    "timestamp": update.timestamp,
                    "change_direction": update.change_direction,
                }
                yield f"data: {json.dumps(payload)}\n\n"

        except asyncio.CancelledError:
            # Client disconnected
            logger.debug("SSE client disconnected")
            break
        except Exception as exc:  # noqa: BLE001
            logger.error("Error in SSE generator: %s", exc)
            break
