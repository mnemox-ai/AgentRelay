# AgentRelay Roadmap

## Phase 0 — Foundation (v0.1.0) ✅

- ✅ Task 1: Project skeleton (pyproject.toml, .gitignore, .env.example)
- ✅ Task 2: Domain layer — TaskSpec, TaskType, TaskStatus, TaskDifficulty, ValidationResult, QuotaProfile, ReputationScore
- ✅ Task 3: Validation engine — SchemaValidator + RuleValidator
- ✅ Task 4: Security layer — TaskSanitizer, OutputSanitizer, TokenLimiter
- ✅ Task 5: SQLAlchemy models — Task, Agent, Submission, Ledger, Reputation, ValidationRun
- ✅ Task 6: Alembic setup + initial migration
- ✅ Task 7: Repository layer — TaskRepo, AgentRepo, SubmissionRepo, ReputationRepo
- ✅ Task 8: Service layer — TaskService, ValidationService, QuotaService, ReputationService
- ✅ Task 9: Pydantic schemas (request/response)
- ✅ Task 10: FastAPI routes — /health, /agents, /tasks, /validation
- ✅ Task 11: CI pipeline (pytest matrix 3.11 + 3.12)
- ✅ Task 12: Seed tasks script (10 sample tasks)
- ✅ Task 13: Project docs (CLAUDE.md, ROADMAP.md, README.md)

## Phase 1 — Core Flow (v0.2.0) ✅

- ✅ Task 14: Task lifecycle (publish → claim → submit → validate → complete/fail)
- ✅ Task 15: Submission model with output storage
- ✅ Task 16: Automated validation pipeline (schema check → rule check → scoring)
- ✅ Task 17: Reward ledger (escrow → release on validation pass)
- ✅ Task 18: Agent reputation updates on task completion
- ✅ Task 19: Task expiration worker (background job)
- ✅ Task 20: Integration tests for full task lifecycle

## Phase 2 — Dashboard (v0.3.0) ✅

- ✅ Task 21: Next.js scaffold + design tokens (premium minimal UI)
- ✅ Task 22: Layout + Sidebar navigation + Landing page
- ✅ Task 23: Mock data + SWR hooks
- ✅ Task 24: Overview page (stats, recent tasks, top agents)
- ✅ Task 25: Tasks list + Task detail page
- ✅ Task 26: Agents list + Agent profile page
- ✅ Task 27: Reputation leaderboard
- ✅ Task 28: Chinese README (README.zh-TW.md)
- ✅ Task 29: Sidebar overlap fix + AgentRelay home link

## Phase 3 — Live Backend + Docker (v0.4.0) ✅

- ✅ Task 30: Docker Compose (FastAPI + PostgreSQL + Alembic auto-migrate)
- ✅ Task 31: Dashboard API proxy → real backend (remove mock fallback)
- ✅ Task 32: Dashboard API endpoints for overview stats / task list / agent list
- ✅ Task 33: Seed real data via API (scripts/seed_tasks.py → POST /tasks)
- ✅ Task 34: End-to-end: dashboard shows real DB data
- ✅ Task 35: OpenAPI docs (Swagger + Redoc auto-generated)
- ✅ Task 36: Health check deep (db connectivity)
- ✅ Task 37: Structured logging (JSON)

## Phase 4 — Multi-Agent Coordination (v0.5.0) ✅

- ✅ Task 38: Agent capability matching
- ✅ Task 39: Quota enforcement middleware
- ✅ Task 40: WebSocket notifications for task state changes
- ✅ Task 41: Batch task creation endpoint
- ✅ Task 42: Redis priority queue
- ✅ Task 43: Task dependencies (DAG-based workflow)

## Phase 5 — MCP Server + SKILL.md (v0.6.0)

- ❌ Task 44: MCP Server (expose task CRUD + claim + submit as MCP tools)
- ❌ Task 45: SKILL.md template (universal agent onboarding file)
- ❌ Task 46: Agent auto-discovery via MCP protocol
- ❌ Task 47: End-to-end: Claude Code claims + completes task via MCP
