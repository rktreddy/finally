"""Unit tests for the LLM module: models, mock, prompts, client, and chat repository."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.models import ChatResponse, TradeAction, WatchlistAction
from app.llm.mock import generate_mock_response
from app.llm.prompts import build_system_prompt, build_messages


# --- Model Tests ---


def test_chat_response_minimal():
    """ChatResponse with just a message defaults to empty trades/watchlist_changes."""
    resp = ChatResponse(message="hello")
    assert resp.message == "hello"
    assert resp.trades == []
    assert resp.watchlist_changes == []


def test_chat_response_with_trades():
    """ChatResponse with trades list works correctly."""
    resp = ChatResponse(
        message="ok",
        trades=[TradeAction(ticker="AAPL", side="buy", quantity=10)],
    )
    assert len(resp.trades) == 1
    assert resp.trades[0].ticker == "AAPL"
    assert resp.trades[0].side == "buy"
    assert resp.trades[0].quantity == 10


def test_chat_response_from_json():
    """ChatResponse can be parsed from minimal JSON."""
    resp = ChatResponse.model_validate_json('{"message": "hi"}')
    assert resp.message == "hi"
    assert resp.trades == []
    assert resp.watchlist_changes == []


def test_chat_response_full_json():
    """ChatResponse can be parsed from full JSON with trades and watchlist changes."""
    data = json.dumps({
        "message": "Done!",
        "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 5}],
        "watchlist_changes": [{"ticker": "PYPL", "action": "add"}],
    })
    resp = ChatResponse.model_validate_json(data)
    assert resp.message == "Done!"
    assert len(resp.trades) == 1
    assert resp.trades[0].ticker == "AAPL"
    assert len(resp.watchlist_changes) == 1
    assert resp.watchlist_changes[0].action == "add"


# --- Mock Tests ---


def test_mock_buy():
    """Mock response for buy keyword returns a buy trade."""
    resp = generate_mock_response("please buy some shares")
    assert isinstance(resp, ChatResponse)
    assert len(resp.trades) == 1
    assert resp.trades[0].side == "buy"


def test_mock_sell():
    """Mock response for sell keyword returns a sell trade."""
    resp = generate_mock_response("sell my AAPL")
    assert isinstance(resp, ChatResponse)
    assert len(resp.trades) == 1
    assert resp.trades[0].side == "sell"


def test_mock_add_watchlist():
    """Mock response for add keyword returns a watchlist add action."""
    resp = generate_mock_response("add PYPL")
    assert isinstance(resp, ChatResponse)
    assert len(resp.watchlist_changes) == 1
    assert resp.watchlist_changes[0].action == "add"
    assert resp.watchlist_changes[0].ticker == "PYPL"


def test_mock_remove_watchlist():
    """Mock response for remove keyword returns a watchlist remove action."""
    resp = generate_mock_response("remove PYPL")
    assert isinstance(resp, ChatResponse)
    assert len(resp.watchlist_changes) == 1
    assert resp.watchlist_changes[0].action == "remove"


def test_mock_default():
    """Mock response for generic message returns analysis with no actions."""
    resp = generate_mock_response("how is my portfolio?")
    assert isinstance(resp, ChatResponse)
    assert len(resp.message) > 0
    assert resp.trades == []
    assert resp.watchlist_changes == []


# --- Prompt Tests ---


def test_build_system_prompt_contains_context():
    """System prompt includes portfolio context and role description."""
    prompt = build_system_prompt(
        cash=10000.0,
        positions=[{
            "ticker": "AAPL",
            "quantity": 10,
            "avg_cost": 150.0,
            "current_price": 155.0,
            "unrealized_pnl": 50.0,
        }],
        watchlist=[{"ticker": "AAPL", "price": 155.0}],
        total_value=11550.0,
    )
    assert "FinAlly" in prompt
    assert "10,000" in prompt or "10000" in prompt
    assert "AAPL" in prompt
    assert "11,550" in prompt or "11550" in prompt


def test_build_messages_structure():
    """build_messages assembles system, history, and user message correctly."""
    messages = build_messages(
        system_prompt="You are a bot",
        history=[
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ],
        user_message="what's up",
    )
    assert len(messages) == 4
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "You are a bot"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "hi"
    assert messages[2]["role"] == "assistant"
    assert messages[3]["role"] == "user"
    assert messages[3]["content"] == "what's up"


# --- Client Tests ---


@pytest.fixture
def mock_llm_response():
    """Create a mock LLM response object."""
    mock_choice = MagicMock()
    mock_choice.message.content = '{"message": "test response"}'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


async def test_call_llm_success(mock_llm_response):
    """call_llm returns a parsed ChatResponse on success."""
    from app.llm.client import call_llm

    with patch("app.llm.client.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.return_value = mock_llm_response
        result = await call_llm([{"role": "user", "content": "hi"}])

    assert isinstance(result, ChatResponse)
    assert result.message == "test response"
    assert result.trades == []
    assert result.watchlist_changes == []

    # Verify the call was made with correct parameters
    call_kwargs = mock_acompletion.call_args
    assert call_kwargs.kwargs["model"] == "openrouter/openai/gpt-oss-120b"
    assert call_kwargs.kwargs["extra_body"] == {"provider": {"order": ["cerebras"]}}
    assert call_kwargs.kwargs["response_format"] == ChatResponse


async def test_call_llm_invalid_json():
    """call_llm returns raw text as message when JSON parsing fails."""
    from app.llm.client import call_llm

    mock_choice = MagicMock()
    mock_choice.message.content = "not json at all"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch("app.llm.client.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.return_value = mock_response
        result = await call_llm([{"role": "user", "content": "hi"}])

    assert isinstance(result, ChatResponse)
    assert result.message == "not json at all"
    assert result.trades == []
    assert result.watchlist_changes == []


async def test_call_llm_api_error():
    """call_llm returns user-friendly error when API call fails."""
    from app.llm.client import call_llm

    with patch("app.llm.client.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.side_effect = Exception("API down")
        result = await call_llm([{"role": "user", "content": "hi"}])

    assert isinstance(result, ChatResponse)
    assert "error" in result.message.lower() or "sorry" in result.message.lower()
    assert result.trades == []
    assert result.watchlist_changes == []


# --- Chat Repository Tests ---


@pytest.fixture
async def db(tmp_path):
    """Initialize a fresh test database."""
    from app.db import init_db

    db_conn = await init_db(str(tmp_path / "test.db"))
    yield db_conn
    await db_conn.close()


async def test_insert_chat_message(db):
    """insert_chat_message persists and returns a chat message."""
    from app.db.repository import insert_chat_message

    result = await insert_chat_message(db, role="user", content="hello")
    assert "id" in result
    assert result["role"] == "user"
    assert result["content"] == "hello"
    assert result["actions"] is None


async def test_insert_chat_message_with_actions(db):
    """insert_chat_message persists actions JSON."""
    from app.db.repository import insert_chat_message

    actions = json.dumps({"trades": [{"ticker": "AAPL", "side": "buy"}]})
    result = await insert_chat_message(db, role="assistant", content="Done!", actions=actions)
    assert result["actions"] is not None
    parsed = json.loads(result["actions"])
    assert parsed["trades"][0]["ticker"] == "AAPL"


async def test_get_chat_history_chronological(db):
    """get_chat_history returns messages in chronological order."""
    from app.db.repository import insert_chat_message, get_chat_history

    await insert_chat_message(db, role="user", content="first")
    await insert_chat_message(db, role="assistant", content="second")
    await insert_chat_message(db, role="user", content="third")

    history = await get_chat_history(db, limit=20)
    assert len(history) == 3
    assert history[0]["content"] == "first"
    assert history[1]["content"] == "second"
    assert history[2]["content"] == "third"


async def test_get_chat_history_limit(db):
    """get_chat_history respects the limit parameter, returning most recent N."""
    from app.db.repository import insert_chat_message, get_chat_history

    for i in range(5):
        await insert_chat_message(db, role="user", content=f"message {i}")

    history = await get_chat_history(db, limit=3)
    assert len(history) == 3
    # Should be the 3 most recent, in chronological order
    assert history[0]["content"] == "message 2"
    assert history[1]["content"] == "message 3"
    assert history[2]["content"] == "message 4"
