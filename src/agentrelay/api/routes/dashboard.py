"""Dashboard API routes — aggregated stats for the frontend."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from agentrelay.api.deps import get_db, rate_limit_by_ip
from agentrelay.repositories.dashboard_repo import DashboardRepository
from agentrelay.schemas.dashboard import (
    DashboardStats,
    LedgerEntryResponse,
    RecentTask,
    TopAgent,
    ValidationRate,
)
from agentrelay.schemas.reputation import ReputationResponse
from agentrelay.services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _dashboard_service(db: AsyncSession) -> DashboardService:
    return DashboardService(DashboardRepository(db))


@router.get("/stats", response_model=DashboardStats, dependencies=[Depends(rate_limit_by_ip)])
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Aggregated dashboard statistics."""
    try:
        svc = _dashboard_service(db)
        return await svc.get_stats()
    except Exception:
        logger.exception("Error fetching dashboard stats")
        raise


@router.get("/tasks/recent", response_model=list[RecentTask], dependencies=[Depends(rate_limit_by_ip)])
async def get_recent_tasks(db: AsyncSession = Depends(get_db)):
    """Latest 10 tasks with agent name and validation score."""
    try:
        svc = _dashboard_service(db)
        return await svc.get_recent_tasks()
    except Exception:
        logger.exception("Error fetching recent tasks")
        raise


@router.get("/agents/top", response_model=list[TopAgent], dependencies=[Depends(rate_limit_by_ip)])
async def get_top_agents(db: AsyncSession = Depends(get_db)):
    """Top 5 agents by quality_score from their latest reputation snapshot."""
    try:
        svc = _dashboard_service(db)
        return await svc.get_top_agents()
    except Exception:
        logger.exception("Error fetching top agents")
        raise


@router.get("/validation-rate", response_model=ValidationRate, dependencies=[Depends(rate_limit_by_ip)])
async def get_validation_rate(db: AsyncSession = Depends(get_db)):
    """Overall validation pass rate."""
    try:
        svc = _dashboard_service(db)
        return await svc.get_validation_rate()
    except Exception:
        logger.exception("Error fetching validation rate")
        raise


# ---------------------------------------------------------------------------
# Agent-scoped endpoints (mounted under /dashboard for grouping)
# ---------------------------------------------------------------------------


@router.get(
    "/agents/{agent_id}/ledger",
    response_model=list[LedgerEntryResponse],
    dependencies=[Depends(rate_limit_by_ip)],
)
async def get_agent_ledger(agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """All ledger entries for a specific agent."""
    try:
        svc = _dashboard_service(db)
        return await svc.get_agent_ledger(agent_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception:
        logger.exception("Error fetching agent ledger for %s", agent_id)
        raise


@router.get(
    "/agents/{agent_id}/reputation",
    response_model=ReputationResponse,
    dependencies=[Depends(rate_limit_by_ip)],
)
async def get_agent_reputation(agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Latest reputation snapshot for a specific agent."""
    try:
        svc = _dashboard_service(db)
        return await svc.get_agent_reputation(agent_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception:
        logger.exception("Error fetching agent reputation for %s", agent_id)
        raise
