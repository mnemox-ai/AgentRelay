# Full Codebase Scan Report — AgentRelay Phase 0-5

**Date**: 2026-03-14
**Scope**: `src/agentrelay/` + `tests/`
**Action**: Read-only scan, no files modified

---

## Summary

| Severity | Count | Fixed | Remaining |
|----------|-------|-------|-----------|
| Critical | 3 | 3 | 0 |
| High     | 8 | 7 | 1 |
| Medium   | 13 | 13 | 0 |
| Low      | 4 | 2 | 2 |
| **Total** | **28** | **25** | **3** |

---

## Findings

| # | Severity | File | Line(s) | Category | Description | Status |
|---|----------|------|---------|----------|-------------|--------|
| 1 | Critical | `src/agentrelay/config.py` | 9 | Security | Hardcoded credentials in default `DATABASE_URL` (`user:password@localhost`). Should require env var or use non-credential placeholder. | ✅ Fixed in Batch 2 |
| 2 | Critical | `src/agentrelay/api/routes/dashboard.py` | 36-227 | Layer Violation | Entire dashboard route executes raw SQLAlchemy `select()` / joins directly — completely bypasses Service and Repository layers. No `DashboardService` exists. | ✅ Fixed in Batch 3 |
| 3 | Critical | `src/agentrelay/api/app.py` | 49 | Version Mismatch | FastAPI `version="0.4.0"` — should be `"0.6.0"` per `pyproject.toml`. | ✅ Fixed in Batch 1 |
| 4 | High | `src/agentrelay/api/routes/tasks.py` | 53, 151, 170, 185-189, 223, 243-244 | Layer Violation | Route handlers directly instantiate `TaskRepository`, `SubmissionRepository`, `AgentRepository`, `LedgerRepository`, `ReputationRepository` — bypasses service layer. | ✅ Fixed in Batch 3 |
| 5 | High | `src/agentrelay/api/routes/agents.py` | 24, 46 | Layer Violation | Direct `AgentRepository(db)` instantiation in route handlers. No `AgentService` exists. | ✅ Fixed in Batch 3 |
| 6 | High | `src/agentrelay/api/routes/validation.py` | 27-28 | Layer Violation | Direct `select(ValidationRun)` query without repository. Also no permission check — submission not validated to belong to authenticated agent. | ✅ Fixed in Batch 3 |
| 7 | High | `src/agentrelay/api/routes/tasks.py` | 155, 209, 229, 237, 239 | Type Inconsistency | Status compared with raw strings (`"open"`, `"validating"`, etc.) instead of `TaskStatus` enum values. | ✅ Fixed in Batch 2 |
| 8 | High | `src/agentrelay/services/expiration_service.py` | 36, 57 | Type Inconsistency | Hardcoded status strings `["open", "claimed"]` and `"expired"` instead of enum values. | ✅ Fixed in Batch 2 |
| 9 | High | `src/agentrelay/security/output_sanitizer.py` | 59 | Error Handling | `except Exception: continue` in security-critical base64 decode path — silently swallows all errors without logging. | ✅ Fixed in Batch 2 |
| 10 | High | `tests/test_mcp_server.py` | 224, 279 | Version Mismatch | Test asserts version `"0.5.0"` — should be `"0.6.0"`. Tests will fail against current codebase. | ✅ Fixed in Batch 1 |
| 11 | High | `src/agentrelay/api/routes/tasks.py` | 131 | Security | `list_available_tasks` endpoint rate-limited by IP but allows unauthenticated listing of all available tasks. Potential reconnaissance vector. | ⏳ Deferred — by design for public task discovery |
| 12 | Medium | `src/agentrelay/domain/validation_result.py` | 25 | Type Annotation | `validated_at: datetime = None` — type hint is `datetime` but default is `None`. Should be `datetime \| None = None`. | ✅ Fixed in Batch 1 |
| 13 | Medium | `src/agentrelay/services/quota_service.py` | 33 | Type Annotation | Parameter `task: object` is too generic — uses `getattr(task, "task_spec", None)` expecting a `Task` model. Should be `task: Task`. | ✅ Fixed in Batch 1 |
| 14 | Medium | `src/agentrelay/services/validation_service.py` | 80 | Type Inconsistency | Enum converted to string via `.value` for DB storage, but never converted back to `ValidatorType` enum on retrieval. | ✅ Fixed in Batch 2 |
| 15 | Medium | `src/agentrelay/mcp_server.py` | 101, 121, 153 | Error Handling | Repeated broad `except Exception` with rollback+raise pattern. Should differentiate validation errors from DB errors. | ✅ Fixed in Batch 2 |
| 16 | Medium | `src/agentrelay/services/notification_service.py` | 43 | Error Handling | WebSocket send failure caught with bare `except Exception`, logged only at DEBUG level. Should log at WARNING. | ✅ Fixed in Batch 2 |
| 17 | Medium | `src/agentrelay/api/routes/tasks.py` | 122, 161 | Error Handling | `except Exception: pass` for Redis operations — no logging at all. Silent failures prevent observability. | ✅ Fixed in Batch 2 |
| 18 | Medium | `src/agentrelay/services/task_service.py` | 105-116 | Error Handling | `except ValueError: pass` silently ignores enum parsing errors during capability matching. Invalid `TaskType` values not logged. | ✅ Fixed in Batch 2 |
| 19 | Medium | `src/agentrelay/mcp_server.py` | 62, 68, 109, 118 | Error Handling | `uuid.UUID(task_id)` called without try/except — `ValueError` on invalid UUID format propagates unhandled. | ✅ Fixed in Batch 2 |
| 20 | Medium | `src/agentrelay/api/routes/ws.py` | 15-20 | Error Handling | Only `WebSocketDisconnect` caught — timeout, protocol errors crash handler ungracefully. | ✅ Fixed in Batch 2 |
| 21 | Medium | `tests/test_websocket.py` | 172 | Async Issue | `async def test_broadcast_no_clients` uses sync `TestClient`. Async test with sync client may cause runtime errors. | ✅ Fixed in Batch 4 |
| 22 | Medium | `tests/test_mcp_e2e.py` | 370, 382 | Test Quality | `pytest.raises(Exception)` — too broad, catches any exception including test infrastructure errors. Should use specific exception type. | ✅ Fixed in Batch 4 |
| 23 | Medium | `tests/test_mcp_server.py` | 170, 200 | Test Quality | Same overly broad `pytest.raises(Exception)` pattern. | ✅ Fixed in Batch 4 |
| 24 | Medium | `tests/test_websocket.py` | 151 | Test Quality | `assert status_code in (200, 201, 409)` — too lenient, masks potential bugs. Should assert one specific code. | ✅ Fixed in Batch 4 |
| 25 | Low | `src/agentrelay/repositories/ledger_repo.py` | 5 | Unused Import | `import uuid` imported but never used in the file. | ✅ Fixed in Batch 1 |
| 26 | Low | `src/agentrelay/models/agent.py` | 17 | Type Inconsistency | `Agent.status` is `Mapped[str]` with default `"active"` — no `AgentStatus` enum exists, allows arbitrary string values. | ✅ Fixed in Batch 1 |
| 27 | Low | `tests/test_lifecycle.py` | 121 | Test Quality | Imports private `_TRANSITIONS` dict — testing internal implementation makes tests brittle to refactoring. | ⏳ Deferred — low impact |
| 28 | Low | `tests/test_rate_limit.py` | 105-107 | Test Quality | Imports private helper `_override_rate_limiter` from `tests.conftest` — tight coupling to test infrastructure. | ⏳ Deferred — low impact |

---

## Category Breakdown

### Layer Violations (4 findings)
The architecture rule is **API → Service → Repository → Models**. Four route files violate this by directly instantiating repositories or executing raw SQLAlchemy queries. The `dashboard.py` route is the worst offender — it contains ~200 lines of raw query logic that should live in a `DashboardService`.

### Type Inconsistencies (5 findings)
`TaskStatus` enum exists in `domain/task_spec.py` but database queries and route handlers use raw strings (`"open"`, `"claimed"`, `"expired"`). No `AgentStatus` enum exists at all. `ValidatorType` enum is one-directional (enum→string but not string→enum).

### Error Handling (8 findings)
Most issues are silent `except Exception: pass` or `except Exception: continue` patterns. Two are in security-critical code paths. Redis failures are completely silent with no logging.

### Security (2 findings)
Hardcoded default credentials in `config.py` and unauthenticated task listing endpoint.

### Version Mismatches (2 findings)
`app.py` stuck at v0.4.0, test expects v0.5.0 — both should be v0.6.0.

### Test Quality (5 findings)
Broad `pytest.raises(Exception)`, lenient assertions, sync/async mismatch, and testing private internals.

---

## Not Found (Clean)

| Check | Result |
|-------|--------|
| Circular imports | None detected |
| SQL injection | None — all queries use SQLAlchemy ORM parameterization |
| TODO/FIXME/HACK markers | Zero found in src/ and tests/ |
| Docker/CI outdated | All current (Python 3.12, postgres:16, redis:7, actions v4/v5) |
| Test coverage gaps | All 8 services and 6 routes have corresponding tests |
| Hardcoded API keys/secrets | None (except default DB URL in config.py) |
