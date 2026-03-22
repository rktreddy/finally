---
phase: 03-llm-chat-integration
plan: 01
subsystem: llm
tags: [litellm, openrouter, cerebras, pydantic, structured-output, mock]

# Dependency graph
requires:
  - phase: 02-trading-api
    provides: "Repository pattern, database layer, PriceCache"
provides:
  - "ChatResponse, TradeAction, WatchlistAction Pydantic models for structured LLM output"
  - "call_llm() async client via LiteLLM/OpenRouter/Cerebras"
  - "build_system_prompt() with portfolio context assembly"
  - "generate_mock_response() for deterministic LLM_MOCK mode"
  - "insert_chat_message() and get_chat_history() repository functions"
affects: [03-02-chat-route]

# Tech tracking
tech-stack:
  added: [litellm]
  patterns: [structured-output-parsing, mock-response-generator, system-prompt-builder]

key-files:
  created:
    - backend/app/llm/__init__.py
    - backend/app/llm/models.py
    - backend/app/llm/client.py
    - backend/app/llm/prompts.py
    - backend/app/llm/mock.py
    - backend/tests/test_llm.py
  modified:
    - backend/pyproject.toml
    - backend/uv.lock
    - backend/app/db/repository.py

key-decisions:
  - "Used rowid tiebreaker in chat history ORDER BY for correct chronological ordering within same second"

patterns-established:
  - "LLM module pattern: models.py for schemas, client.py for API call, prompts.py for context, mock.py for testing"
  - "Structured output via response_format=PydanticModel with fallback to raw text on validation error"

requirements-completed: [LLM-06, LLM-07, LLM-08]

# Metrics
duration: 3min
completed: 2026-03-22
---

# Phase 03 Plan 01: LLM Module Summary

**LiteLLM client with Pydantic structured output, system prompt builder with portfolio context, and deterministic mock mode for testing**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-22T14:49:03Z
- **Completed:** 2026-03-22T14:52:22Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Complete backend/app/llm/ package with models, client, prompts, and mock modules
- Chat repository functions (insert_chat_message, get_chat_history) added to repository.py
- 18 unit tests covering all LLM components, 124 total tests passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Add litellm dependency and create LLM module** - `f736f05` (feat)
2. **Task 2: Add chat repository functions and unit tests** - `8934ee8` (feat)

## Files Created/Modified
- `backend/app/llm/models.py` - ChatResponse, TradeAction, WatchlistAction Pydantic models
- `backend/app/llm/client.py` - Async call_llm() using LiteLLM via OpenRouter/Cerebras
- `backend/app/llm/prompts.py` - build_system_prompt() and build_messages() for context assembly
- `backend/app/llm/mock.py` - generate_mock_response() for deterministic testing
- `backend/app/llm/__init__.py` - Public API re-exports with __all__
- `backend/app/db/repository.py` - Added insert_chat_message() and get_chat_history()
- `backend/tests/test_llm.py` - 18 unit tests for models, mock, prompts, client, repository
- `backend/pyproject.toml` - Added litellm dependency
- `backend/uv.lock` - Updated lockfile

## Decisions Made
- Used rowid as secondary sort key in get_chat_history() ORDER BY clause to ensure correct chronological ordering when multiple messages share the same created_at timestamp (SQLite second-level resolution)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed chat history chronological ordering**
- **Found during:** Task 2 (unit tests)
- **Issue:** Messages inserted within the same second got the same created_at timestamp, causing ORDER BY created_at DESC to return them in arbitrary order
- **Fix:** Added `rowid DESC` as tiebreaker in the ORDER BY clause
- **Files modified:** backend/app/db/repository.py
- **Verification:** test_get_chat_history_chronological passes
- **Committed in:** 8934ee8 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential for correctness of chat history ordering. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All LLM building blocks ready for Plan 02 (chat route)
- call_llm(), build_system_prompt(), build_messages(), generate_mock_response() all independently tested
- Chat persistence functions ready for the chat endpoint to use

---
*Phase: 03-llm-chat-integration*
*Completed: 2026-03-22*
