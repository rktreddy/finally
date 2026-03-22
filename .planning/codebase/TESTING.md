# Testing Patterns

**Analysis Date:** 2026-03-21

## Context

Only the backend (`backend/`) has tests. The frontend (`frontend/`) is not yet scaffolded. All patterns below are derived from `backend/tests/`. The plan specifies E2E tests will live in `test/` using Playwright, but that directory contains only `node_modules` — no test files yet.

---

## Test Framework

**Runner:**
- pytest `>=8.3.0`
- Config: `backend/pyproject.toml` under `[tool.pytest.ini_options]`

**Async support:**
- `pytest-asyncio >= 0.24.0`
- `asyncio_mode = "auto"` — all async test methods run automatically without `@pytest.mark.asyncio` on each method (class-level `@pytest.mark.asyncio` is used instead)
- `asyncio_default_fixture_loop_scope = "function"` — each test gets a fresh event loop

**Coverage:**
- `pytest-cov >= 5.0.0`
- Source: `app/` (the entire backend package)
- Config: `backend/pyproject.toml` under `[tool.coverage.run]` and `[tool.coverage.report]`

**Assertion Library:**
- pytest built-in `assert` statements (no separate assertion library)

**Run Commands:**
```bash
cd backend
uv run --extra dev pytest -v              # All tests, verbose
uv run --extra dev pytest --cov=app       # With coverage report
uv run --extra dev ruff check app/ tests/ # Lint check
```

---

## Test File Organization

**Location:**
- Separate `tests/` directory at `backend/tests/`, mirroring the `app/` package structure
- `backend/tests/market/` mirrors `backend/app/market/`

**Naming:**
- Test files: `test_<module>.py` matching the source module name
  - `app/market/models.py` → `tests/market/test_models.py`
  - `app/market/cache.py` → `tests/market/test_cache.py`
  - `app/market/simulator.py` → `tests/market/test_simulator.py` (GBMSimulator) and `tests/market/test_simulator_source.py` (SimulatorDataSource)
  - `app/market/massive_client.py` → `tests/market/test_massive.py`
  - `app/market/factory.py` → `tests/market/test_factory.py`
- Test classes: `Test<ClassName>` matching the class under test
- Test methods: `test_<what_is_being_tested>` — descriptive, behavior-focused names

**Structure:**
```
backend/
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Shared fixtures (minimal — event loop policy only)
│   └── market/
│       ├── __init__.py      # Module docstring only
│       ├── test_cache.py
│       ├── test_factory.py
│       ├── test_massive.py
│       ├── test_models.py
│       ├── test_simulator.py
│       └── test_simulator_source.py
```

---

## Test Structure

**Suite Organization:**
```python
"""Tests for PriceCache."""

from app.market.cache import PriceCache


class TestPriceCache:
    """Unit tests for the PriceCache."""

    def test_update_and_get(self):
        """Test updating and getting a price."""
        cache = PriceCache()
        update = cache.update("AAPL", 190.50)
        assert update.ticker == "AAPL"
        assert update.price == 190.50
        assert cache.get("AAPL") == update
```

**Async suite organization:**
```python
@pytest.mark.asyncio
class TestSimulatorDataSource:
    """Integration tests for the SimulatorDataSource."""

    async def test_start_populates_cache(self):
        """Test that start() immediately populates the cache."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
        await source.start(["AAPL", "GOOGL"])
        assert cache.get("AAPL") is not None
        await source.stop()
```

**Patterns:**
- All tests in a class that wraps a single unit under test
- Each test method has a docstring explaining what is being verified
- No shared fixtures within test classes — each test creates its own instances (no `setup_method`)
- Tests are stateless: each creates fresh instances of dependencies

---

## Mocking

**Framework:** `unittest.mock` from the standard library (`MagicMock`, `patch`, `patch.object`)

**Patterns:**

Environment variable mocking:
```python
from unittest.mock import patch
import os

with patch.dict(os.environ, {"MASSIVE_API_KEY": "test-key"}, clear=True):
    source = create_market_data_source(cache)
```

Method mocking with `patch.object`:
```python
with patch.object(source, "_fetch_snapshots", return_value=mock_snapshots):
    await source._poll_once()
```

Error injection:
```python
with patch.object(source, "_fetch_snapshots", side_effect=Exception("network error")):
    await source._poll_once()  # Should not raise
```

External SDK mocking with `MagicMock`:
```python
from unittest.mock import MagicMock

def _make_snapshot(ticker: str, price: float, timestamp_ms: int) -> MagicMock:
    """Create a mock Massive snapshot object."""
    snap = MagicMock()
    snap.ticker = ticker
    snap.last_trade = MagicMock()
    snap.last_trade.price = price
    snap.last_trade.timestamp = timestamp_ms
    return snap
```

Module-level patching:
```python
with patch("app.market.massive_client.RESTClient"):
    with patch.object(source, "_fetch_snapshots", return_value=[]):
        await source.start(["AAPL"])
```

**What to Mock:**
- External API clients (`RESTClient` from the `massive` SDK)
- Environment variables via `patch.dict(os.environ, ...)`
- Individual methods on a class under test when testing the surrounding logic in isolation (`patch.object`)

**What NOT to Mock:**
- The classes under test themselves
- `PriceCache` — use the real implementation; it has no external dependencies
- Standard library modules (threading, asyncio, math)
- numpy operations

---

## Fixtures and Factories

**Test Data:**
```python
# Inline fixture helper (not a pytest fixture) in test_massive.py
def _make_snapshot(ticker: str, price: float, timestamp_ms: int) -> MagicMock:
    """Create a mock Massive snapshot object."""
    snap = MagicMock()
    snap.ticker = ticker
    snap.last_trade = MagicMock()
    snap.last_trade.price = price
    snap.last_trade.timestamp = timestamp_ms
    return snap
```

**Shared fixtures:**
- Minimal global fixtures in `backend/tests/conftest.py` — currently only `event_loop_policy`
- Prefer inline instantiation within each test over shared fixtures for clarity

---

## Coverage

**Requirements:** Not explicitly enforced (no minimum threshold in config)

**Excluded from coverage:**
- `tests/*`
- Standard boilerplate: `__repr__`, `raise AssertionError`, `raise NotImplementedError`, `if __name__ == "__main__":`, `if TYPE_CHECKING:`

**View Coverage:**
```bash
cd backend
uv run --extra dev pytest --cov=app --cov-report=term-missing
```

---

## Test Types

**Unit Tests** (`TestPriceCache`, `TestPriceUpdate`, `TestGBMSimulator`, `TestFactory`):
- Scope: A single class or function, no async I/O
- Location: `tests/market/test_models.py`, `tests/market/test_cache.py`, `tests/market/test_simulator.py`, `tests/market/test_factory.py`
- Pattern: Instantiate class, call method, assert on return value or state
- Sync methods only — no `asyncio`

**Integration Tests** (`TestSimulatorDataSource`, `TestMassiveDataSource`):
- Scope: A component that manages async lifecycle (background tasks), tested with real asyncio
- Location: `tests/market/test_simulator_source.py`, `tests/market/test_massive.py`
- Pattern: `await source.start()`, allow time to pass with `asyncio.sleep()`, assert on side effects in the shared `PriceCache`, `await source.stop()`
- Use fast `update_interval` values (0.01–0.1s) to make async tests complete quickly
- External APIs are mocked; real `PriceCache` is used

**E2E Tests:**
- Framework: Playwright (specified in plan, `test/` directory exists but contains no test files yet)
- Infrastructure: `test/docker-compose.test.yml` (not yet created)
- Run with `LLM_MOCK=true` for determinism

---

## Common Patterns

**Async Testing:**
```python
@pytest.mark.asyncio
class TestSimulatorDataSource:
    async def test_prices_update_over_time(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.05)
        await source.start(["AAPL"])
        initial_version = cache.version
        await asyncio.sleep(0.3)  # Allow several update cycles
        assert cache.version > initial_version
        await source.stop()
```

**Error/Exception Testing:**
```python
def test_immutability(self):
    """Test that PriceUpdate is immutable."""
    update = PriceUpdate(ticker="AAPL", price=190.50, previous_price=190.00, timestamp=1234567890.0)
    with pytest.raises(AttributeError):
        update.price = 200.00
```

**Idempotent operation testing:**
```python
async def test_stop_is_clean(self):
    """Test that stop() is clean and idempotent."""
    cache = PriceCache()
    source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
    await source.start(["AAPL"])
    await source.stop()
    await source.stop()  # Double stop should not raise
```

**Edge case naming:**
- `test_<operation>_nonexistent_is_noop` — for silent no-op behaviors
- `test_<operation>_does_not_crash` — for resilience tests
- `test_<operation>_is_idempotent` — for safe-to-repeat operations

---

## Future Test Areas (Not Yet Implemented)

Per `planning/PLAN.md`, the following test areas still need to be built:

- **Backend portfolio tests** (`tests/portfolio/`): trade execution logic, P&L calculations, edge cases (sell more than owned, insufficient cash)
- **Backend LLM tests** (`tests/llm/`): structured output parsing, malformed response handling, trade validation in chat flow
- **Backend API route tests** (`tests/routes/`): status codes, response shapes, error handling
- **Frontend unit tests** (`frontend/`): component rendering, price flash animation, watchlist CRUD, chat display
- **E2E tests** (`test/`): full user flow via Playwright with `LLM_MOCK=true`
