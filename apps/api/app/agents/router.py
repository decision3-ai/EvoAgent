import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.core.auth import get_current_user_id
from app.agents.models import Agent
from app.agents.schemas import AgentCreate, AgentUpdate, AgentResponse

router = APIRouter()


@router.post('/', response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Agent:
    agent = Agent(**payload.model_dump(), owner_id=owner_id)
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.get('/', response_model=List[AgentResponse])
async def list_agents(
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> List[Agent]:
    result = await db.execute(
        select(Agent)
        .where(Agent.owner_id == owner_id)
        .order_by(Agent.created_at.desc())
    )
    return list(result.scalars().all())


@router.get('/{agent_id}', response_model=AgentResponse)
async def get_agent(
    agent_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Agent:
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.owner_id == owner_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail='Agent not found')
    return agent


@router.patch('/{agent_id}', response_model=AgentResponse)
async def update_agent(
    agent_id: uuid.UUID,
    payload: AgentUpdate,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Agent:
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.owner_id == owner_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail='Agent not found')

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(agent, field, value)

    await db.commit()
    await db.refresh(agent)
    return agent


@router.delete('/{agent_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.owner_id == owner_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail='Agent not found')
    await db.delete(agent)
    await db.commit()
