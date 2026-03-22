"""Health check endpoint for Docker/deployment monitoring."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])


@router.get("/health")
async def health_check(request: Request) -> dict:
    """Return health status of the application."""
    return {
        "status": "healthy",
        "market_data": request.app.state.cache is not None,
        "database": request.app.state.db is not None,
    }
