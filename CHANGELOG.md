# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2026-03-14

### Added

- Domain layer with core business objects (TaskSpec, TaskType, TaskStatus, TaskDifficulty)
- Validation engine with schema and rule validators
- Security layer with input/output sanitizers and token limiter
- Database models and Alembic migrations
- FastAPI REST API with 16 endpoints (tasks, agents, validation, health)
- API key authentication middleware
- In-memory rate limiting
- Task state machine with lifecycle transitions (claim → submit → validate → reward/reject)
- Automated validation pipeline on task submission
- Reward ledger and automatic reputation updates
- Task expiration worker
- Integration tests covering full task lifecycle and attack simulation
- Docker Compose setup with PostgreSQL and auto-migration
- Seed script with full lifecycle demo
- Agent capability matching for task assignment
- Quota enforcement on task claim
- WebSocket real-time notifications
- Redis priority queue with batch task creation
- MCP Server exposing 7 tools and 1 resource
- Agent auto-discovery via MCP protocol
- SKILL.md template for universal agent onboarding
- MCP E2E tests covering full MCP lifecycle
- CI workflow with lint checks
- PyPI publish workflow
- Traditional Chinese README
- 394 tests

### Changed

- Renamed PyPI package to agentrelay-protocol
- README rewritten with pain-point-driven structure and quick start guide

### Fixed

- Layer violations in dashboard, tasks, agents, and validation routes
- Hardcoded credentials replaced with environment variables
- Enum consistency across codebase (AgentStatus, quota types)
- Concurrent claim protection and unique submission constraint
- Config-driven CORS origins
- Agent name validation and input sanitization
- Consistent zero-token handling and deadline validation

[0.6.0]: https://github.com/mnemox-ai/AgentRelay/releases/tag/v0.6.0
