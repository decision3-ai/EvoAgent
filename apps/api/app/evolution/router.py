import time
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.auth import get_current_user_id
from app.agents.models import Agent, Interaction
from app.agents.schemas import InteractionCreate, FeedbackPayload, InteractionResponse

router = APIRouter()


@router.post('/{agent_id}/interact', response_model=InteractionResponse)
async def interact_with_agent(
    agent_id: uuid.UUID,
    payload: InteractionCreate,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Interaction:
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.owner_id == owner_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail='Agent not found')

    start = time.monotonic()

    # Placeholder response — real LangGraph pipeline goes here in the next sprint
    output = (
        f'[evoagent Gen-{agent.generation} | {agent.model}] '
        f'Echo: {payload.input}'
    )

    latency_ms = int((time.monotonic() - start) * 1000)

    interaction = Interaction(
        agent_id=agent_id,
        input=payload.input,
        output=output,
        latency_ms=latency_ms,
        meta=payload.meta,
    )
    agent.total_interactions += 1

    db.add(interaction)
    await db.commit()
    await db.refresh(interaction)
    return interaction


@router.post('/{agent_id}/feedback')
async def submit_feedback(
    agent_id: uuid.UUID,
    payload: FeedbackPayload,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Interaction).where(
            Interaction.id == payload.interaction_id,
            Interaction.agent_id == agent_id,
        )
    )
    interaction = result.scalar_one_or_none()
    if not interaction:
        raise HTTPException(status_code=404, detail='Interaction not found')

    interaction.feedback_score = payload.score

    agent_result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = agent_result.scalar_one()

    # Exponential moving average for fitness score
    alpha = 0.2
    agent.fitness_score = alpha * payload.score + (1 - alpha) * agent.fitness_score

    await db.commit()

    return {
        'status': 'feedback_recorded',
        'interaction_id': str(payload.interaction_id),
        'new_fitness_score': round(agent.fitness_score, 4),
    }


@router.get('/{agent_id}/history', response_model=list[InteractionResponse])
async def get_interaction_history(
    agent_id: uuid.UUID,
    limit: int = 50,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[Interaction]:
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.owner_id == owner_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail='Agent not found')

    history_result = await db.execute(
        select(Interaction)
        .where(Interaction.agent_id == agent_id)
        .order_by(Interaction.created_at.desc())
        .limit(limit)
    )
    return list(history_result.scalars().all())
