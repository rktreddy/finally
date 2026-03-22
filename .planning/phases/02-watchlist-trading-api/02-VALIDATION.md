---
phase: 02
slug: watchlist-trading-api
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 with pytest-asyncio (asyncio_mode = "auto") |
| **Config file** | `backend/pyproject.toml` |
| **Quick run command** | `cd backend && uv run pytest tests/ -x -q` |
| **Full suite command** | `cd backend && uv run pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/ -x -q`
- **After every plan wave:** Run `cd backend && uv run pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | WL-01, WL-02, WL-03, WL-04 | integration | `cd backend && uv run pytest tests/test_watchlist.py -v` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | PT-01, PT-02, PT-03, PT-04, PT-05, PT-06 | integration | `cd backend && uv run pytest tests/test_portfolio.py -v` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | PT-07, PT-08, PT-09 | integration | `cd backend && uv run pytest tests/test_snapshots.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_watchlist.py` — stubs for WL-01 through WL-04
- [ ] `backend/tests/test_portfolio.py` — stubs for PT-01 through PT-06
- [ ] `backend/tests/test_snapshots.py` — stubs for PT-07 through PT-09

*Existing infrastructure (conftest.py, httpx client fixture, async test config) covers all shared needs.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
