import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import settings
from app.core.database import get_db
from app.core.auth import get_current_user_id
from app.core.redis import get_redis
from app.workspaces.models import Workspace
from app.analytics.models import AnalyticsEvent
from app.analytics.schemas import EventCreate, EventResponse

router = APIRouter()


async def _get_session_variant(session_id: uuid.UUID | None) -> str:
    if session_id is None:
        return 'champion'
    r = get_redis()
    variant = await r.get(f'session_variant:{session_id}')
    return variant or 'champion'


@router.post('/', response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def track_event(
    payload: EventCreate,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsEvent:
    # Verify workspace ownership
    ws_result = await db.execute(
        select(Workspace).where(
            Workspace.id == payload.workspace_id,
            Workspace.owner_id == owner_id,
        )
    )
    workspace = ws_result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(status_code=404, detail='Workspace not found')

    if payload.event_type == 'code_copy':
        if payload.message_id is None:
            raise HTTPException(status_code=422, detail='message_id required for code_copy event')
        # 1 code_copy per message_id + workspace_id per calendar day
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        dupe = await db.execute(
            select(func.count()).select_from(AnalyticsEvent).where(
                AnalyticsEvent.event_type == 'code_copy',
                AnalyticsEvent.message_id == payload.message_id,
                AnalyticsEvent.workspace_id == payload.workspace_id,
                AnalyticsEvent.created_at >= today_start,
            )
        )
        if dupe.scalar() > 0:
            raise HTTPException(status_code=409, detail='Duplicate code_copy event for this message today')

    elif payload.event_type == 'completion':
        if payload.session_id is None:
            raise HTTPException(status_code=422, detail='session_id required for completion event')
        # 1 completion per session max
        dupe = await db.execute(
            select(func.count()).select_from(AnalyticsEvent).where(
                AnalyticsEvent.event_type == 'completion',
                AnalyticsEvent.session_id == payload.session_id,
            )
        )
        if dupe.scalar() > 0:
            raise HTTPException(status_code=409, detail='Duplicate completion event for this session')

    # EvoPoints V3.5: +3 for code_copy
    if payload.event_type == 'code_copy':
        workspace.evo_points = (workspace.evo_points or 0) + 3
        workspace.evo_points_updated_at = datetime.utcnow()

    variant = await _get_session_variant(payload.session_id)
    event = AnalyticsEvent(
        workspace_id=payload.workspace_id,
        session_id=payload.session_id,
        message_id=payload.message_id,
        event_type=payload.event_type,
        event_metadata={**payload.event_metadata, 'variant': variant},
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event
