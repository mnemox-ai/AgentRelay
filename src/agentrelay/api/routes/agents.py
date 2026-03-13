"""Agent registration and lookup routes."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from agentrelay.api.deps import get_db, rate_limit_by_ip
from agentrelay.repositories.agent_repo import AgentRepository
from agentrelay.schemas.agent import AgentRegister, AgentRegisterResponse, AgentResponse
from agentrelay.services.agent_service import AgentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


def _agent_service(db: AsyncSession) -> AgentService:
    return AgentService(AgentRepository(db))


@router.post("", response_model=AgentRegisterResponse, status_code=201, dependencies=[Depends(rate_limit_by_ip)])
async def register_agent(body: AgentRegister, db: AsyncSession = Depends(get_db)):
    try:
        svc = _agent_service(db)
        return await svc.register_agent(body)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception:
        logger.exception("Error registering agent %s", body.name)
        raise


@router.get("/{agent_id}", response_model=AgentResponse, dependencies=[Depends(rate_limit_by_ip)])
async def get_agent(agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        svc = _agent_service(db)
        return await svc.get_agent(agent_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception:
        logger.exception("Error fetching agent %s", agent_id)
        raise
