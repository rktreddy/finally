# Coding Conventions

**Analysis Date:** 2026-03-21

## Context

Only the backend (`backend/app/market/`) is currently implemented. The frontend (`frontend/`) is an empty directory not yet scaffolded. All conventions below are derived from the Python backend codebase.

---

## Naming Patterns

**Files:**
- Lowercase snake_case: `cache.py`, `massive_client.py`, `seed_prices.py`, `simulator.py`
- One primary class or concern per file, named to match the file: `cache.py` → `PriceCache`, `simulator.py` → `GBMSimulator` + `SimulatorDataSource`
- Abstract interfaces in a dedicated file: `interface.py`
- Factory functions in a dedicated file: `factory.py`
- `__init__.py` acts as a public API declaration (explicit `__all__`, re-exports only, no logic)

**Classes:**
- PascalCase: `PriceCache`, `PriceUpdate`, `GBMSimulator`, `MarketDataSource`, `SimulatorDataSource`, `MassiveDataSource`

**Functions and methods:**
- snake_case: `create_market_data_source()`, `get_price()`, `add_ticker()`, `remove_ticker()`
- Private methods prefixed with single underscore: `_add_ticker_internal()`, `_rebuild_cholesky()`, `_poll_once()`, `_poll_loop()`, `_run_loop()`, `_generate_events()`
- Factory functions named `create_*`: `create_market_data_source()`, `create_stream_router()`

**Variables and attributes:**
- snake_case: `price_cache`, `api_key`, `update_interval`, `poll_interval`
- Private instance attributes prefixed with underscore: `self._cache`, `self._task`, `self._tickers`, `self._client`, `self._cholesky`

**Constants:**
- UPPER_SNAKE_CASE in module-level dicts and values: `SEED_PRICES`, `TICKER_PARAMS`, `DEFAULT_PARAMS`, `CORRELATION_GROUPS`, `INTRA_TECH_CORR`, `TSLA_CORR`
- Class-level constants in UPPER_SNAKE_CASE: `GBMSimulator.DEFAULT_DT`, `GBMSimulator.TRADING_SECONDS_PER_YEAR`

**Type hints:**
- Used throughout: `list[str]`, `dict[str, float]`, `float | None`, `asyncio.Task | None`, `np.ndarray | None`
- `from __future__ import annotations` used in every module with type hints to enable forward references
- Return types always annotated: `-> None`, `-> PriceUpdate`, `-> dict[str, float]`, `-> list[str]`

---

## Code Style

**Formatter/Linter:**
- `ruff` configured in `backend/pyproject.toml`
- Line length: 100 characters (`line-length = 100`)
- Target Python version: 3.12 (`target-version = "py312"`)
- Rule sets: `E` (pycodestyle errors), `F` (pyflakes), `I` (isort), `N` (naming), `W` (warnings)
- `E501` (line too long) is ignored — ruff formatter handles line wrapping

**Docstrings:**
- Module-level docstrings on every file: `"""Data models for market data."""`
- Class-level docstrings explaining purpose and key design decisions
- Method docstrings for public API; private methods may have inline comments instead
- Docstrings use plain prose, not Sphinx/Google style

---

## Import Organization

**Order (enforced by ruff `I` rules):**
1. Standard library (`__future__`, `asyncio`, `dataclasses`, `logging`, `os`, `math`, `random`, `threading`, `time`)
2. Third-party packages (`fastapi`, `numpy`, `massive`)
3. Local imports using relative paths (`from .cache import PriceCache`, `from .models import PriceUpdate`)

**`from __future__ import annotations`:**
- Placed first in every module that uses type hints, before all other imports

**Relative imports within a package:**
- Always use relative imports inside `app/market/`: `from .cache import PriceCache`, not `from app.market.cache import PriceCache`

**Public API via `__init__.py`:**
- Each package exposes a clean public API through `__init__.py` with explicit `__all__`
- Example: `backend/app/market/__init__.py` re-exports `PriceUpdate`, `PriceCache`, `MarketDataSource`, `create_market_data_source`, `create_stream_router`

---

## Error Handling

**Patterns:**
- Background tasks (asyncio loops) use bare `except Exception` to prevent crashes, log with `logger.exception()` (which captures traceback) or `logger.error()`:
  ```python
  except Exception:
      logger.exception("Simulator step failed")
  ```
- External API calls catch specific exceptions first, fall back to broad `except Exception as e` with `logger.error()` and a comment explaining the non-raise decision:
  ```python
  except (AttributeError, TypeError) as e:
      logger.warning("Skipping snapshot for %s: %s", getattr(snap, "ticker", "???"), e)
  except Exception as e:
      logger.error("Massive poll failed: %s", e)
      # Don't re-raise — the loop will retry on the next interval.
  ```
- Task cancellation is handled explicitly using `asyncio.CancelledError`:
  ```python
  try:
      await self._task
  except asyncio.CancelledError:
      pass
  ```
- Guard clauses check `is None` or truthiness before using optional attributes (`if self._sim:`, `if not self._tickers or not self._client:`)
- No-op behavior for invalid operations (add duplicate ticker, remove nonexistent ticker) is explicit and silent — no exceptions raised

---

## Logging

**Framework:** Python standard library `logging` module

**Pattern:**
- Every module that produces log output creates a module-level logger:
  ```python
  logger = logging.getLogger(__name__)
  ```
- Log levels used:
  - `logger.info()`: lifecycle events (start/stop, ticker add/remove, counts)
  - `logger.debug()`: high-frequency events (per-tick random events, poll counts)
  - `logger.warning()`: recoverable data issues (malformed API snapshots)
  - `logger.error()`: external failures (API poll errors)
  - `logger.exception()`: unexpected exceptions in background tasks (includes traceback)
- Log message format uses `%s` percent-style formatting (not f-strings): `logger.info("Started %d tickers", len(tickers))`

---

## Comments

**Inline comments:**
- Used for non-obvious math: GBM formula explanation, `dt` calculation, rate limit guidance
- Used to explain design decisions: `# Don't re-raise — the loop will retry`, `# Seed the cache immediately`
- Used to mark internal section boundaries: `# --- Public API ---`, `# --- Internals ---`

**Docstrings vs. comments:**
- Docstrings for public API (classes and public methods)
- Inline `#` comments for implementation details within method bodies

---

## Function and Method Design

**Size:** Methods are small and focused. Long methods (e.g., `GBMSimulator.step()`) are the hot path and are commented accordingly.

**Parameters:**
- Use keyword arguments for optional config with sensible defaults: `update_interval: float = 0.5`, `event_probability: float = 0.001`
- Dependency injection over globals — cache and config passed into constructors, never accessed via module-level globals

**Return values:**
- Typed return annotations on all public methods
- Methods that mutate state return `None`; methods that query return typed values
- Convenience accessor methods (e.g., `get_price()` wrapping `get()`) are explicit and documented

---

## Module Design

**Exports:**
- Each package has an explicit public API in `__init__.py` with `__all__`
- Internal implementation details (private classes, helpers) are not re-exported

**Abstract interfaces:**
- Abstract base classes defined in `interface.py` using `abc.ABC` and `@abstractmethod`
- Factory functions (`factory.py`) return the abstract type, hiding the concrete implementation

**Dataclasses:**
- Immutable value objects use `@dataclass(frozen=True, slots=True)`: `PriceUpdate`
- Computed properties implemented as `@property` on frozen dataclasses

**Thread safety:**
- Shared mutable state (the price cache) protected with `threading.Lock`
- Async code uses `asyncio.to_thread()` to run blocking (synchronous) I/O calls without blocking the event loop

---

## Frontend Conventions

The `frontend/` directory is empty — no frontend code exists yet. Conventions will be established when Next.js is scaffolded. Per the project plan (`planning/PLAN.md`), the frontend will use:
- Next.js with TypeScript (`output: 'export'` static mode)
- Tailwind CSS with a custom dark theme
- `EventSource` for SSE connection
- Canvas-based charting (Lightweight Charts or Recharts)
