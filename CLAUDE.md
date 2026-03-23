# AgentRelay — Claude Code 指令

## 專案概述

AgentRelay = Verifiable Microtask Protocol for AI Agents。多 agent 協作平台，讓 AI agent 發布、認領、執行微任務，並透過驗證引擎確保產出品質。

- GitHub: mnemox-ai/AgentRelay
- 版本: v0.6.0
- License: Apache-2.0
- Default branch: `main`

## 架構（分層）

```
src/agentrelay/
├── api/              # FastAPI routes (app.py, routes/)
│   └── routes/       # health, agents, tasks, validation
├── schemas/          # Pydantic request/response models
├── services/         # Business logic (task_service, validation_service, quota_service, reputation_service)
├── repositories/     # DB access layer (task_repo, agent_repo, submission_repo, reputation_repo)
├── models/           # SQLAlchemy ORM models (task, agent, submission, ledger, reputation, validation_run)
├── domain/           # Core business objects (task_spec, validation_result, quota_profile, reputation_score)
├── validation/       # Validation engine (schema_validator, rule_validator)
├── security/         # Input/output sanitizers, token limiter
├── config.py         # pydantic-settings (.env)
└── db.py             # Async SQLAlchemy engine + session
```

分層規則：**API → Service → Repository → Models**，禁止跨層呼叫。

## 開發規範

- Python 3.11+
- 測試：`python -m pytest tests/ -v`（每個任務完成後必跑）
- Linting：`ruff check src/ tests/`
- Commit message 格式：`type: description`（feat/fix/docs/chore/test）
- DB：PostgreSQL + asyncpg，Redis for quota/cache
- 所有 timestamps 用 UTC

## ToS 紅線

- **不碰 auth / API key 管理** — agent 身分驗證由外部 IdP 負責
- **不代理 API call** — AgentRelay 只轉發任務規格和結果，絕不代替 agent 呼叫第三方 API
- **不存放模型權重或推論結果** — 只存結構化驗證結果

## 重要檔案位置

- FastAPI app：`src/agentrelay/api/app.py`
- Routes：`src/agentrelay/api/routes/`（tasks, agents, validation, health）
- Domain objects：`src/agentrelay/domain/`（TaskSpec, TaskType, TaskStatus, TaskDifficulty）
- Validation engine：`src/agentrelay/validation/`
- Security：`src/agentrelay/security/`（auth.py, rate_limiter.py, task_sanitizer, output_sanitizer, token_limiter）
- DB models：`src/agentrelay/models/`
- Alembic migrations：`alembic/`
- Tests：`tests/`
- Integration tests：`tests/test_integration.py`（full lifecycle）、`tests/test_security_integration.py`（attack simulation）
- Seed script：`scripts/seed_tasks.py`
- CI：`.github/workflows/ci.yml`
- Phase 1 services：`src/agentrelay/services/`（task_service, validation_service, ledger_service, reputation_service, expiration_service, quota_service）
- Phase 1 domain：`src/agentrelay/domain/task_lifecycle.py`（TaskStateMachine）
- API deps：`src/agentrelay/api/deps.py`（auth, rate limiting dependency injection）
- Phase 4 capability：`src/agentrelay/domain/capability.py`（AgentCapability matching）
- Phase 4 notification：`src/agentrelay/services/notification_service.py`（WebSocket broadcast）
- Phase 4 queue：`src/agentrelay/services/queue_service.py`（Redis priority queue）
- Phase 4 WebSocket：`src/agentrelay/api/routes/ws.py`（/ws endpoint）
- Phase 5 MCP server：`src/agentrelay/mcp_server.py`（7 MCP tools + 1 resource）
- Phase 5 MCP E2E tests：`tests/test_mcp_e2e.py`（full MCP lifecycle tests）
- Phase 5 MCP unit tests：`tests/test_mcp_server.py`（per-tool unit tests）
- Phase 5 SKILL.md：`.skills/agentrelay/SKILL.md`（universal agent onboarding）

## Rules

1. 每個任務完成前必須跑 pytest 確認沒壞東西
2. commit 前用 `git diff` 檢查改動範圍是否合理
3. 分層架構嚴格遵守：API 不直接碰 Repository，Service 不直接碰 ORM session
4. NEVER hardcode credentials — 所有 secrets 走 `.env` 或環境變數
5. 不要修改 security/ 下的 sanitizer，除非任務明確要求
6. 簡單方案優先，不要 over-engineer
7. 寫文件用開發者語調，不要行銷語調

## Recent Changes
- [2026-03-18] 策略決策：AgentRelay 暫停新開發，精力轉 TradeMemory。保持維護狀態。
- [2026-03-18] Worker executor 修復：prompt injection fix + claude path auto-resolve + 三層隔離。E2E FULL LIFECYCLE PASS。CI green (481 tests)。
- [2026-03-17] CI green: lint fix (5 unused imports) + all 3 CI jobs pass
- [2026-03-17] Worker executor 三層隔離：--system-prompt + --setting-sources "" + cwd=tempdir
- [2026-03-17] Worker executor fix: prompt injection 防誤判（system-prompt 隔離）、claude path 自動解析、E2E lifecycle PASS
- [2026-03-15] Worker MVP 上線：runner.py + cli.py + executor.py + 20 task templates + regenerator
- [2026-03-15] Render 部署成功：API + PostgreSQL + Redis (Key Value) + Dashboard
- [2026-03-15] Seed 20 tasks + 5 agents 到 production
- [2026-03-15] Fix: Windows cp950 emoji crash, missing files from auto-claude
- [2026-03-15] README 加 Worker Quickstart section（EN + zh-TW）
- [2026-03-15] Jarvis 系統建立，加入 /morning 掃描範圍

## Current Status
- v0.6.0, 481 tests passing, CI green, worker E2E verified
- Production: https://agentrelay-api.onrender.com (API) + Dashboard
- Worker CLI: `agentrelay worker --server https://agentrelay-api.onrender.com`
- 20 tasks seeded, regenerator 每小時補充到 20 個
- Render 月成本：~$21（PostgreSQL $7 + Redis $7 + API starter $7）
- 狀態：可推廣，等 Sean 在自己電腦測試 worker 完整流程
