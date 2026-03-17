"""
Factory for selecting the active market data provider based on environment variables.

If MASSIVE_API_KEY is set and non-empty → MassiveAPIClient
Otherwise                               → MarketDataSimulator
"""

import os

from .base import MarketDataProvider, price_cache
from .massive import MassiveAPIClient
from .simulator import MarketDataSimulator

# Module-level singleton — created once on import, shared across the app
_provider: MarketDataProvider | None = None


def get_provider() -> MarketDataProvider:
    """Return (or create) the active market data provider singleton."""
    global _provider  # noqa: PLW0603
    if _provider is None:
        _provider = _create_provider()
    return _provider


def _create_provider() -> MarketDataProvider:
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()
    if api_key:
        return MassiveAPIClient(cache=price_cache, api_key=api_key)
    return MarketDataSimulator(cache=price_cache)


def reset_provider(provider: MarketDataProvider | None = None) -> None:
    """
    Replace the global provider singleton.

    Passing None forces re-creation from environment on the next call to
    get_provider(). Passing a concrete instance is useful for testing.
    """
    global _provider  # noqa: PLW0603
    _provider = provider
