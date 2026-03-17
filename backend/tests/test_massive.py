"""Unit tests for the Massive API client."""

import asyncio
import json

import httpx
import pytest
import respx

from app.market_data.base import PriceCache, PriceUpdate
from app.market_data.massive import MassiveAPIClient, _MASSIVE_BASE_URL, _QUOTE_ENDPOINT


@pytest.fixture
def cache() -> PriceCache:
    return PriceCache()


@pytest.fixture
def client(cache: PriceCache) -> MassiveAPIClient:
    return MassiveAPIClient(
        cache=cache,
        api_key="test-key",
        poll_interval=0.01,
        base_url=_MASSIVE_BASE_URL,
    )


def _quote_response(quotes: list[dict]) -> dict:
    return {"quotes": quotes}


class TestMassiveClientSetup:
    def test_starts_not_running(self, client):
        assert not client.is_running

    def test_add_ticker_normalises_upper(self, client):
        client.add_ticker("aapl")
        assert "AAPL" in client.tickers

    def test_remove_ticker(self, client, cache):
        client.add_ticker("AAPL")
        client.remove_ticker("AAPL")
        assert "AAPL" not in client.tickers
        assert cache.get("AAPL") is None


class TestExtractHelpers:
    def test_extract_ticker_from_symbol_field(self):
        assert MassiveAPIClient._extract_ticker({"symbol": "AAPL"}) == "AAPL"

    def test_extract_ticker_from_ticker_field(self):
        assert MassiveAPIClient._extract_ticker({"ticker": "msft"}) == "MSFT"

    def test_extract_ticker_prefers_symbol_over_ticker(self):
        result = MassiveAPIClient._extract_ticker({"symbol": "AAPL", "ticker": "OTHER"})
        assert result == "AAPL"

    def test_extract_ticker_none_on_missing(self):
        assert MassiveAPIClient._extract_ticker({}) is None

    def test_extract_ticker_none_on_non_dict(self):
        assert MassiveAPIClient._extract_ticker("AAPL") is None

    def test_extract_ticker_none_on_empty_string(self):
        assert MassiveAPIClient._extract_ticker({"symbol": ""}) is None

    def test_extract_price_from_price_field(self):
        assert MassiveAPIClient._extract_price({"price": 190.5}) == 190.5

    def test_extract_price_from_last_field(self):
        assert MassiveAPIClient._extract_price({"last": "195.00"}) == 195.0

    def test_extract_price_from_close_field(self):
        assert MassiveAPIClient._extract_price({"close": 200.0}) == 200.0

    def test_extract_price_prefers_price_field(self):
        result = MassiveAPIClient._extract_price({"price": 190.0, "last": 185.0})
        assert result == 190.0

    def test_extract_price_none_on_zero(self):
        assert MassiveAPIClient._extract_price({"price": 0}) is None

    def test_extract_price_none_on_negative(self):
        assert MassiveAPIClient._extract_price({"price": -1.0}) is None

    def test_extract_price_none_on_non_numeric_string(self):
        assert MassiveAPIClient._extract_price({"price": "N/A"}) is None

    def test_extract_price_none_on_missing(self):
        assert MassiveAPIClient._extract_price({}) is None

    def test_extract_price_rounds_to_2dp(self):
        assert MassiveAPIClient._extract_price({"price": 190.123456}) == 190.12


class TestProcessResponse:
    def test_valid_response_updates_cache(self, client, cache):
        client.add_ticker("AAPL")
        client._process_response(
            _quote_response([{"symbol": "AAPL", "price": 190.5}])
        )
        assert cache.get("AAPL") is not None
        assert cache.get("AAPL").price == 190.5

    def test_unknown_ticker_is_skipped(self, client, cache):
        # "ZZZZ" is not in the tracked set
        client._process_response(
            _quote_response([{"symbol": "ZZZZ", "price": 50.0}])
        )
        assert cache.get("ZZZZ") is None

    def test_multiple_tickers_in_one_response(self, client, cache):
        client.add_ticker("AAPL")
        client.add_ticker("MSFT")
        client._process_response(
            _quote_response([
                {"symbol": "AAPL", "price": 190.0},
                {"symbol": "MSFT", "price": 420.0},
            ])
        )
        assert cache.get("AAPL").price == 190.0
        assert cache.get("MSFT").price == 420.0

    def test_malformed_response_does_not_crash(self, client):
        client._process_response("not a dict")  # must not raise
        client._process_response({"quotes": "not a list"})  # must not raise
        client._process_response({"quotes": [None, 42, "bad"]})  # must not raise

    def test_change_direction_computed_correctly(self, client, cache):
        client.add_ticker("AAPL")
        # First update
        client._process_response(_quote_response([{"symbol": "AAPL", "price": 190.0}]))
        # Second update — price went up
        client._process_response(_quote_response([{"symbol": "AAPL", "price": 195.0}]))
        assert cache.get("AAPL").change_direction == "up"

    def test_first_update_marks_unchanged(self, client, cache):
        """On the very first update there is no previous price — should be unchanged."""
        client.add_ticker("AAPL")
        client._process_response(_quote_response([{"symbol": "AAPL", "price": 190.0}]))
        # previous_price equals price on first call, so direction is "unchanged"
        assert cache.get("AAPL").change_direction == "unchanged"

    def test_callback_invoked_on_update(self, client, cache):
        received: list[PriceUpdate] = []
        client.set_update_callback(received.append)
        client.add_ticker("AAPL")
        client._process_response(_quote_response([{"symbol": "AAPL", "price": 190.0}]))
        assert len(received) == 1
        assert received[0].ticker == "AAPL"


class TestMassiveClientHTTP:
    @pytest.mark.asyncio
    async def test_poll_sends_request_with_tickers(self, client, cache):
        with respx.mock(base_url=_MASSIVE_BASE_URL) as mock:
            route = mock.get(_QUOTE_ENDPOINT).mock(
                return_value=httpx.Response(
                    200,
                    json=_quote_response([{"symbol": "AAPL", "price": 190.0}]),
                )
            )
            client.add_ticker("AAPL")
            async with httpx.AsyncClient(base_url=_MASSIVE_BASE_URL) as http:
                await client._poll(http, ["AAPL"])
            assert route.called

    @pytest.mark.asyncio
    async def test_poll_handles_http_error_gracefully(self, client, cache):
        with respx.mock(base_url=_MASSIVE_BASE_URL):
            respx.get(_QUOTE_ENDPOINT).mock(
                return_value=httpx.Response(429, text="Too Many Requests")
            )
            client.add_ticker("AAPL")
            async with httpx.AsyncClient(base_url=_MASSIVE_BASE_URL) as http:
                await client._poll(http, ["AAPL"])  # must not raise
            assert cache.get("AAPL") is None  # no update on error

    @pytest.mark.asyncio
    async def test_poll_handles_network_error_gracefully(self, client, cache):
        with respx.mock(base_url=_MASSIVE_BASE_URL):
            respx.get(_QUOTE_ENDPOINT).mock(side_effect=httpx.ConnectError("timeout"))
            client.add_ticker("AAPL")
            async with httpx.AsyncClient(base_url=_MASSIVE_BASE_URL) as http:
                await client._poll(http, ["AAPL"])  # must not raise


class TestMassiveClientAsync:
    @pytest.mark.asyncio
    async def test_start_sets_running(self, client):
        with respx.mock(base_url=_MASSIVE_BASE_URL):
            respx.get(_QUOTE_ENDPOINT).mock(
                return_value=httpx.Response(200, json={"quotes": []})
            )
            await client.start()
            assert client.is_running
            await client.stop()

    @pytest.mark.asyncio
    async def test_stop_clears_running(self, client):
        with respx.mock(base_url=_MASSIVE_BASE_URL):
            respx.get(_QUOTE_ENDPOINT).mock(
                return_value=httpx.Response(200, json={"quotes": []})
            )
            await client.start()
            await client.stop()
            assert not client.is_running

    @pytest.mark.asyncio
    async def test_double_start_is_idempotent(self, client):
        with respx.mock(base_url=_MASSIVE_BASE_URL):
            respx.get(_QUOTE_ENDPOINT).mock(
                return_value=httpx.Response(200, json={"quotes": []})
            )
            await client.start()
            await client.start()
            assert client.is_running
            await client.stop()

    @pytest.mark.asyncio
    async def test_running_client_polls_and_populates_cache(self, cache):
        client = MassiveAPIClient(
            cache=cache,
            api_key="test-key",
            poll_interval=0.01,
            base_url=_MASSIVE_BASE_URL,
        )
        client.add_ticker("AAPL")

        with respx.mock(base_url=_MASSIVE_BASE_URL):
            respx.get(_QUOTE_ENDPOINT).mock(
                return_value=httpx.Response(
                    200,
                    json=_quote_response([{"symbol": "AAPL", "price": 190.0}]),
                )
            )
            await client.start()
            await asyncio.sleep(0.05)
            await client.stop()

        assert cache.get("AAPL") is not None
        assert cache.get("AAPL").price == 190.0
