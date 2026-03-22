"""Integration tests for the FastAPI application entry point."""

from __future__ import annotations

import asyncio
import os

import httpx
import pytest
from httpx import ASGITransport


@pytest.fixture
def _db_in_temp(tmp_path):
    """Set DB_PATH to a temp file so each test gets a fresh database."""
    db_path = str(tmp_path / "test.db")
    os.environ["DB_PATH"] = db_path
    yield db_path
    os.environ.pop("DB_PATH", None)


@pytest.fixture
async def client(_db_in_temp):
    """Provide an async httpx client with lifespan managed."""
    # Import app after DB_PATH is set to avoid path issues
    from app.main import app, lifespan

    # Manually enter the lifespan context so app.state is populated
    async with lifespan(app):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac


async def test_health_check(client):
    """GET /api/health returns 200 with JSON status healthy, market_data true, database true."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["market_data"] is True
    assert data["database"] is True


async def test_static_serving(client):
    """GET / returns 200 with HTML content containing 'FinAlly'."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "FinAlly" in response.text


async def test_api_priority_over_static(client):
    """GET /api/health returns JSON, confirming API routes take priority over static catch-all."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "application/json" in content_type
    assert "text/html" not in content_type


async def test_sse_stream(client):
    """GET /api/stream/prices returns 200 with content-type text/event-stream."""
    # The SSE endpoint is a long-lived stream, so we use a timeout to read
    # just the initial response headers and first chunk, then cancel.
    try:
        async with asyncio.timeout(3):
            async with client.stream("GET", "/api/stream/prices") as response:
                assert response.status_code == 200
                content_type = response.headers.get("content-type", "")
                assert "text/event-stream" in content_type
                # Read first line to confirm stream is active
                async for line in response.aiter_lines():
                    if line.strip():
                        break
    except TimeoutError:
        # Expected -- the stream doesn't end naturally
        pass


async def test_lifespan(_db_in_temp):
    """App starts and stops without errors; app.state has db, cache, source set."""
    from app.main import app, lifespan

    async with lifespan(app):
        # Verify app.state is populated
        assert app.state.db is not None
        assert app.state.cache is not None
        assert app.state.source is not None

        # Verify via health check too
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
            response = await ac.get("/api/health")
            assert response.status_code == 200
            data = response.json()
            assert data["database"] is True
            assert data["market_data"] is True
