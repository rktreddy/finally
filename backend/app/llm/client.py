"""LLM client — calls OpenRouter with Cerebras inference via LiteLLM."""

from __future__ import annotations

import logging

from litellm import completion

from .models import ChatResponse

logger = logging.getLogger(__name__)

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}


def call_llm(messages: list[dict]) -> ChatResponse:
    """Call the LLM and return a structured ChatResponse.

    Raises ValueError if the response cannot be parsed.
    """
    try:
        response = completion(
            model=MODEL,
            messages=messages,
            response_format=ChatResponse,
            reasoning_effort="low",
            extra_body=EXTRA_BODY,
        )
        content = response.choices[0].message.content
        return ChatResponse.model_validate_json(content)
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        raise ValueError(f"LLM call failed: {e}") from e
