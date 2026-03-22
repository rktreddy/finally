# Phase 1: Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-21
**Phase:** 01-foundation
**Areas discussed:** Database connection, Schema init, App state sharing, Static file fallback
**Mode:** Auto (--auto flag, all recommended defaults selected)

---

## Database Connection Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Single shared connection | aiosqlite connection created at startup, shared via app.state | ✓ |
| Connection per request | New connection for each API call | |
| Connection pool | Pool of connections (overkill for single-user SQLite) | |

**User's choice:** [auto] Single shared connection (recommended default)
**Notes:** Single-user app with SQLite — no concurrency concerns. WAL mode enables concurrent reads.

---

## Schema Initialization

| Option | Description | Selected |
|--------|-------------|----------|
| Raw SQL file + Python init | schema.sql file, Python function reads and executes | ✓ |
| Inline Python strings | SQL embedded in Python code | |
| Migration framework (Alembic) | Full migration support | |

**User's choice:** [auto] Raw SQL file + Python init (recommended default)
**Notes:** Readable, auditable, matches backend conventions. No migration framework needed for lazy init.

---

## App State Sharing

| Option | Description | Selected |
|--------|-------------|----------|
| FastAPI app.state | Store on app.state, access via request.app.state | ✓ |
| Global module singletons | Module-level variables | |
| Dependency injection container | Third-party DI framework | |

**User's choice:** [auto] FastAPI app.state (recommended default)
**Notes:** Standard FastAPI pattern. Simple, testable, no extra dependencies.

---

## Static File Fallback

| Option | Description | Selected |
|--------|-------------|----------|
| Placeholder index.html | Simple HTML page confirming static serving works | ✓ |
| No static files yet | Skip until frontend is built | |
| Redirect to /api/health | API-only until frontend exists | |

**User's choice:** [auto] Placeholder index.html (recommended default)
**Notes:** Validates static serving works in Phase 1. Replaced by Next.js build output in Phase 4.

---

## Claude's Discretion

- Health check response JSON structure
- Logging verbosity at startup
- Exact error messages

## Deferred Ideas

None — auto mode stayed within phase scope.
