"""LLM client for calling OpenRouter via LiteLLM."""

from __future__ import annotations

import logging

from litellm import acompletion
from pydantic import ValidationError

from .models import ChatResponse

logger = logging.getLogger(__name__)

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}


async def call_llm(messages: list[dict]) -> ChatResponse:
    """Call the LLM via LiteLLM and return a structured ChatResponse.

    Handles validation errors by returning the raw message text with empty actions.
    Handles API errors by returning a user-friendly error message.
    """
    try:
        response = await acompletion(
            model=MODEL,
            messages=messages,
            response_format=ChatResponse,
            reasoning_effort="low",
            extra_body=EXTRA_BODY,
            timeout=30,
            num_retries=1,
        )
        content = response.choices[0].message.content
    except Exception:
        logger.exception("LLM API call failed")
        return ChatResponse(
            message="I'm sorry, I encountered an error processing your request. Please try again."
        )

    try:
        return ChatResponse.model_validate_json(content)
    except ValidationError:
        logger.exception("Failed to parse LLM response as structured output: %s", content)
        return ChatResponse(message=content)
