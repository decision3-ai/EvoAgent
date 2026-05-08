import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.workspaces.models import Workspace, Session


async def _get_owned_workspace(
    workspace_id: uuid.UUID,
    owner_id: str,
    db: AsyncSession,
) -> Workspace:
    result = await db.execute(
        select(Workspace)
        .options(selectinload(Workspace.agent_profile))
        .where(
            Workspace.id == workspace_id,
            Workspace.owner_id == owner_id,
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail='Workspace not found')
    return workspace


async def _get_session(
    session_id: uuid.UUID,
    workspace_id: uuid.UUID,
    db: AsyncSession,
) -> Session:
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.workspace_id == workspace_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')
    return session
