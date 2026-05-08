import uuid
import random
from datetime import datetime, timezone, timedelta, UTC
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.core.config import settings
from app.core.celery import celery_client
from app.core.redis import get_redis
from app.core.database import get_db
from app.core.auth import get_current_user_id
from app.workspaces.models import Workspace, AgentProfile, Session, Message, Feedback
from app.workspaces.helpers import _get_owned_workspace, _get_session
from app.analytics.models import AnalyticsEvent
from app.workspaces.schemas import (
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceResponse,
    AgentProfileUpdate,
    AgentProfileResponse,
    SessionCreate,
    SessionUpdate,
    SessionResponse,
    MessageResponse,
    FeedbackCreate,
    FeedbackResponse,
)

router = APIRouter()


# ─── Workspace CRUD ───────────────────────────────────────────────────────────

@router.post('/', response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Workspace:
    # First workspace for this user becomes the default
    existing = await db.execute(
        select(func.count()).select_from(Workspace).where(Workspace.owner_id == owner_id)
    )
    is_first = existing.scalar() == 0

    workspace = Workspace(
        **payload.model_dump(),
        owner_id=owner_id,
        is_default=is_first,
        evo_points=20,
        evo_points_updated_at=datetime.now(UTC),
    )
    db.add(workspace)
    await db.flush()

    # Auto-create the AgentProfile for this workspace
    agent_profile = AgentProfile(workspace_id=workspace.id)
    db.add(agent_profile)

    await db.commit()
    await db.refresh(workspace)
    await db.refresh(agent_profile)
    result = await db.execute(
        select(Workspace)
        .options(selectinload(Workspace.agent_profile))
        .where(Workspace.id == workspace.id)
    )
    return result.scalar_one()


@router.get('/', response_model=List[WorkspaceResponse])
async def list_workspaces(
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> List[Workspace]:
    result = await db.execute(
        select(Workspace)
        .options(selectinload(Workspace.agent_profile))
        .where(Workspace.owner_id == owner_id)
        .order_by(Workspace.created_at.asc())
    )
    return list(result.scalars().all())


@router.get('/{workspace_id}', response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Workspace:
    return await _get_owned_workspace(workspace_id, owner_id, db)


@router.get('/{workspace_id}/status')
async def get_workspace_status(
    workspace_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _get_owned_workspace(workspace_id, owner_id, db)

    r = get_redis()
    value = await r.get(f'maintenance:{workspace_id}')

    now_utc = datetime.now(timezone.utc)

    if value == 'true':
        next_available = now_utc.replace(hour=1, minute=0, second=0, microsecond=0)
        if next_available <= now_utc:
            next_available += timedelta(days=1)
        return {
            'maintenance_mode': True,
            'message': 'evolving',
            'next_available': next_available.isoformat(),
        }

    if value == 'false':
        return {
            'maintenance_mode': False,
            'message': 'evolved',
            'next_available': None,
        }

    return {
        'maintenance_mode': False,
        'message': '',
        'next_available': None,
    }


@router.patch('/{workspace_id}', response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Workspace:
    workspace = await _get_owned_workspace(workspace_id, owner_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(workspace, field, value)
    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.delete('/{workspace_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    workspace = await _get_owned_workspace(workspace_id, owner_id, db)
    await db.delete(workspace)
    await db.commit()


@router.post('/{workspace_id}/evolve')
async def trigger_evolution(
    workspace_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _get_owned_workspace(workspace_id, owner_id, db)

    r = get_redis()
    await r.set(f'evolution_status:{workspace_id}', 'queued', ex=86400)

    celery_client.send_task('tasks.agent_tasks.run_evolution', args=[str(workspace_id)])

    return {'status': 'evolution_queued', 'workspace_id': str(workspace_id)}


# ─── Agent Profile ────────────────────────────────────────────────────────────

@router.get('/{workspace_id}/agent', response_model=AgentProfileResponse)
async def get_agent_profile(
    workspace_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> AgentProfile:
    workspace = await _get_owned_workspace(workspace_id, owner_id, db)
    if not workspace.agent_profile:
        raise HTTPException(status_code=404, detail='Agent profile not found')
    return workspace.agent_profile


@router.patch('/{workspace_id}/agent', response_model=AgentProfileResponse)
async def update_agent_profile(
    workspace_id: uuid.UUID,
    payload: AgentProfileUpdate,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> AgentProfile:
    workspace = await _get_owned_workspace(workspace_id, owner_id, db)
    if not workspace.agent_profile:
        raise HTTPException(status_code=404, detail='Agent profile not found')

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(workspace.agent_profile, field, value)

    await db.commit()
    await db.refresh(workspace.agent_profile)
    return workspace.agent_profile


# ─── Sessions ─────────────────────────────────────────────────────────────────

@router.post('/{workspace_id}/sessions/', response_model=SessionResponse, status_code=201)
async def create_session(
    workspace_id: uuid.UUID,
    payload: SessionCreate,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Session:
    await _get_owned_workspace(workspace_id, owner_id, db)
    session = Session(workspace_id=workspace_id, title=payload.title)
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # 50/50 champion/challenger traffic split — persisted in Redis for 24h
    variant = random.choice(['champion', 'challenger'])
    r = get_redis()
    await r.set(f'session_variant:{session.id}', variant, ex=86400)

    return session


@router.get('/{workspace_id}/sessions/', response_model=List[SessionResponse])
async def list_sessions(
    workspace_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> List[SessionResponse]:
    await _get_owned_workspace(workspace_id, owner_id, db)

    result = await db.execute(
        select(Session)
        .where(Session.workspace_id == workspace_id)
        .order_by(Session.updated_at.desc())
    )
    sessions = result.scalars().all()

    # Add message_count for each session
    responses = []
    for s in sessions:
        count_result = await db.execute(
            select(func.count()).select_from(Message).where(Message.session_id == s.id)
        )
        count = count_result.scalar() or 0
        sr = SessionResponse.model_validate(s)
        sr.message_count = count
        responses.append(sr)

    return responses


@router.get('/{workspace_id}/sessions/{session_id}', response_model=SessionResponse)
async def get_session_endpoint(
    workspace_id: uuid.UUID,
    session_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Session:
    await _get_owned_workspace(workspace_id, owner_id, db)
    return await _get_session(session_id, workspace_id, db)


@router.patch('/{workspace_id}/sessions/{session_id}', response_model=SessionResponse)
async def update_session(
    workspace_id: uuid.UUID,
    session_id: uuid.UUID,
    payload: SessionUpdate,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Session:
    await _get_owned_workspace(workspace_id, owner_id, db)
    session = await _get_session(session_id, workspace_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(session, field, value)
    await db.commit()
    await db.refresh(session)
    return session


@router.delete('/{workspace_id}/sessions/{session_id}', status_code=204)
async def delete_session(
    workspace_id: uuid.UUID,
    session_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_owned_workspace(workspace_id, owner_id, db)
    session = await _get_session(session_id, workspace_id, db)
    await db.delete(session)
    await db.commit()


@router.get(
    '/{workspace_id}/sessions/{session_id}/messages',
    response_model=List[MessageResponse],
)
async def get_messages(
    workspace_id: uuid.UUID,
    session_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> List[Message]:
    await _get_owned_workspace(workspace_id, owner_id, db)
    await _get_session(session_id, workspace_id, db)

    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


# ─── Feedback ─────────────────────────────────────────────────────────────────

@router.post(
    '/{workspace_id}/sessions/{session_id}/messages/{message_id}/feedback',
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_feedback(
    workspace_id: uuid.UUID,
    session_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: FeedbackCreate,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Feedback:
    workspace = await _get_owned_workspace(workspace_id, owner_id, db)
    await _get_session(session_id, workspace_id, db)

    result = await db.execute(
        select(Message).where(
            Message.id == message_id,
            Message.session_id == session_id,
        )
    )
    msg = result.scalar_one_or_none()
    if msg is None:
        raise HTTPException(status_code=404, detail='Message not found')

    feedback = Feedback(
        message_id=message_id,
        session_id=session_id,
        workspace_id=workspace_id,
        score=payload.score,
    )
    db.add(feedback)

    # Fitness V2 phase 1: raw signed score (5=thumbs up → 1.0, 1=thumbs down → -1.0)
    msg.fitness_score = 1.0 if payload.score == 5 else -1.0

    # EvoPoints V3.5: +10 for thumbs up
    if payload.score == 5:
        workspace.evo_points = (workspace.evo_points or 0) + 10
        workspace.evo_points_updated_at = datetime.now(UTC)

    r = get_redis()
    variant = await r.get(f'session_variant:{session_id}')
    variant = variant or 'champion'

    analytics_event = AnalyticsEvent(
        workspace_id=workspace_id,
        session_id=session_id,
        message_id=message_id,
        event_type='feedback',
        event_metadata={'score': payload.score, 'variant': variant},
    )
    db.add(analytics_event)

    await db.commit()
    await db.refresh(feedback)
    return feedback
