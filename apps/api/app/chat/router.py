"""
Chat router — the core of AgentEvo v1.

Calls Claude API (claude-3-5-haiku-20241022) with full session history.
Sprint 3 will replace this with a LangGraph streaming pipeline (SSE).
"""

import time
import uuid
import logging
import anthropic

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.auth import get_current_user_id
from app.workspaces.models import Workspace, Session, Message
from app.workspaces.schemas import ChatRequest, ChatResponse, MessageResponse
from app.workspaces.router import _get_owned_workspace, _get_session

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    '/{workspace_id}/sessions/{session_id}/chat',
    response_model=ChatResponse,
)
async def chat(
    workspace_id: uuid.UUID,
    session_id: uuid.UUID,
    payload: ChatRequest,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    workspace = await _get_owned_workspace(workspace_id, owner_id, db)
    session = await _get_session(session_id, workspace_id, db)

    agent = workspace.agent_profile
    if not agent:
        raise HTTPException(status_code=400, detail='Agent profile not configured')

    start = time.monotonic()

    # Save the user message
    user_msg = Message(
        session_id=session_id,
        role='user',
        content=payload.message,
    )
    db.add(user_msg)
    await db.flush()

    # Load full session history (includes the user message just flushed)
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    history = result.scalars().all()

    system_prompt = agent.system_prompt or (
        'You are an expert AI coding partner. Help the user build, debug, and '
        'understand code. Be concise, precise, and always explain your reasoning.'
    )

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    api_response = await client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=agent.max_tokens,
        system=system_prompt,
        messages=[{'role': m.role, 'content': m.content} for m in history],
    )

    response_text = api_response.content[0].text
    tokens_used = api_response.usage.input_tokens + api_response.usage.output_tokens
    latency_ms = int((time.monotonic() - start) * 1000)

    assistant_msg = Message(
        session_id=session_id,
        role='assistant',
        content=response_text,
        latency_ms=latency_ms,
        tokens_used=tokens_used,
        artifacts=[],
    )
    db.add(assistant_msg)

    # Auto-title the session from its first user message
    if session.title == 'New session':
        session.title = _generate_title(payload.message)

    await db.commit()
    await db.refresh(user_msg)
    await db.refresh(assistant_msg)

    return ChatResponse(
        user_message=MessageResponse.model_validate(user_msg),
        assistant_message=MessageResponse.model_validate(assistant_msg),
        session_title=session.title,
    )


def _generate_title(first_message: str) -> str:
    """Generate a short session title from the first user message."""
    words = first_message.strip().split()
    title = ' '.join(words[:8])
    if len(words) > 8:
        title += '…'
    return title[:100]
