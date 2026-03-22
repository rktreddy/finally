---
phase: 1
slug: foundation
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-21
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| **Config file** | `backend/pyproject.toml` |
| **Quick run command** | `cd backend && uv run --extra dev pytest tests/test_db_init.py tests/test_app.py -x -v` |
| **Full suite command** | `cd backend && uv run --extra dev pytest -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run --extra dev pytest tests/test_db_init.py tests/test_app.py -x -v`
- **After every plan wave:** Run `cd backend && uv run --extra dev pytest -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | DB-01, DB-02, WL-05 | unit/integration | `pytest tests/test_db_init.py -x -v` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 2 | DB-06 | integration | `test -f static/index.html` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 2 | DB-03, DB-04, DB-05 | integration | `pytest tests/test_app.py -x -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `backend/tests/test_db_init.py` — tests for schema creation, seed data, idempotency (created by Plan 01-01)
- [x] `backend/tests/test_app.py` — tests for lifespan, health check, SSE stream, static serving (created by Plan 01-02)
- [x] `backend/tests/conftest.py` — shared fixtures for temp DB (created by Plan 01-01)

*Test files are created by the same tasks that implement the features (TDD pattern).*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-21
