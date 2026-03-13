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

## Phase 2 — Multi-Agent Coordination (v0.3.0)

- ❌ Task 21: Task dependencies (DAG-based workflow)
- ❌ Task 22: Agent capability matching
- ❌ Task 23: Quota enforcement middleware
- ❌ Task 24: Rate limiting per agent
- ❌ Task 25: WebSocket notifications for task state changes
- ❌ Task 26: Batch task creation endpoint
- ❌ Task 27: Task priority queue with Redis

## Phase 3 — Production Readiness (v0.4.0)

- ❌ Task 28: Docker Compose (app + postgres + redis)
- ❌ Task 29: OpenAPI docs + Redoc
- ❌ Task 30: Health check deep (db + redis connectivity)
- ❌ Task 31: Structured logging (JSON)
- ❌ Task 32: Metrics endpoint (Prometheus)
- ❌ Task 33: MCP server integration
