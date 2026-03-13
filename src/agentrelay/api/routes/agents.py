"""Agent registration and lookup routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from agentrelay.api.deps import get_db, rate_limit_by_ip
from agentrelay.repositories.agent_repo import AgentRepository
from agentrelay.schemas.agent import AgentRegister, AgentRegisterResponse, AgentResponse
from agentrelay.security.auth import generate_api_key

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=AgentRegisterResponse, status_code=201, dependencies=[Depends(rate_limit_by_ip)])
async def register_agent(body: AgentRegister, db: AsyncSession = Depends(get_db)):
    repo = AgentRepository(db)
    existing = await repo.get_by_name(body.name)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Agent name already registered")
    api_key = generate_api_key()
    agent = await repo.create(
        name=body.name,
        api_key=api_key,
        quota_profile=body.quota_profile,
        capabilities=body.capabilities,
    )
    return agent


@router.get("/{agent_id}", response_model=AgentResponse, dependencies=[Depends(rate_limit_by_ip)])
async def get_agent(agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    repo = AgentRepository(db)
    agent = await repo.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
