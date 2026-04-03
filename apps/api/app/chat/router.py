"""
Chat router — the core of AgentEvo v1.

Calls Anthropic API with full session history.
SSE streaming replaces this in the next sprint.
"""

_VALID_MODELS = {
    'claude-haiku-4-5-20251001',
    'claude-sonnet-4-5-20250929',
    'claude-sonnet-4-6',
    'claude-opus-4-5-20251101',
}
_DEFAULT_MODEL = 'claude-haiku-4-5-20251001'

import json
import time
import uuid
import logging
import anthropic

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db, AsyncSessionLocal
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

    system_prompt = agent.system_prompt or ''

    # Only user/assistant roles go into messages array (Anthropic API requirement)
    chat_messages = [
        {'role': m.role, 'content': m.content}
        for m in history
        if m.role in ('user', 'assistant')
    ]

    # Fallback to default if stored model is not a valid Anthropic model
    model = agent.model if agent.model in _VALID_MODELS else _DEFAULT_MODEL

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    api_response = await client.messages.create(
        model=model,
        max_tokens=agent.max_tokens,
        system=system_prompt,
        messages=chat_messages,
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


@router.post('/{workspace_id}/sessions/{session_id}/chat/stream')
async def chat_stream(
    workspace_id: uuid.UUID,
    session_id: uuid.UUID,
    payload: ChatRequest,
    owner_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    workspace = await _get_owned_workspace(workspace_id, owner_id, db)
    session = await _get_session(session_id, workspace_id, db)

    agent = workspace.agent_profile
    if not agent:
        raise HTTPException(status_code=400, detail='Agent profile not configured')

    # Save user message before streaming starts
    user_msg = Message(session_id=session_id, role='user', content=payload.message)
    db.add(user_msg)

    if session.title == 'New session':
        session.title = _generate_title(payload.message)

    await db.commit()
    await db.refresh(user_msg)

    # Load history after commit (includes the user message just saved)
    history_result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    chat_messages = [
        {'role': m.role, 'content': m.content}
        for m in history_result.scalars().all()
        if m.role in ('user', 'assistant')
    ]

    # Capture all values needed inside the generator (no db session inside)
    model = agent.model if agent.model in _VALID_MODELS else _DEFAULT_MODEL
    system_prompt = agent.system_prompt or ''
    max_tokens = agent.max_tokens
    session_title = session.title
    user_msg_response = MessageResponse.model_validate(user_msg).model_dump(mode='json')

    async def event_stream():
        # Event 1: confirm user message saved
        yield f'data: {json.dumps({"type": "start", "user_message": user_msg_response, "session_title": session_title})}\n\n'

        full_text = ''
        start = time.monotonic()

        try:
            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            async with client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=chat_messages,
            ) as stream:
                async for text in stream.text_stream:
                    full_text += text
                    yield f'data: {json.dumps({"type": "token", "text": text})}\n\n'

                final_msg = await stream.get_final_message()
                tokens_used = (
                    final_msg.usage.input_tokens + final_msg.usage.output_tokens
                )
        except Exception as e:
            logger.error('Stream error: %s', e)
            yield f'data: {json.dumps({"type": "error", "message": "Stream failed"})}\n\n'
            return

        latency_ms = int((time.monotonic() - start) * 1000)

        # Save assistant message using a fresh session (generator outlives request db)
        async with AsyncSessionLocal() as save_db:
            assistant_msg = Message(
                session_id=session_id,
                role='assistant',
                content=full_text,
                latency_ms=latency_ms,
                tokens_used=tokens_used,
                artifacts=[],
            )
            save_db.add(assistant_msg)
            await save_db.commit()
            await save_db.refresh(assistant_msg)
            assistant_response = MessageResponse.model_validate(assistant_msg).model_dump(mode='json')

        # Event 3: done — send full assistant message for frontend state
        yield f'data: {json.dumps({"type": "done", "assistant_message": assistant_response, "session_title": session_title})}\n\n'

    return StreamingResponse(
        event_stream(),
        media_type='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


_LEADING_FILLER = {
    'can', 'could', 'would', 'should', 'please',
    'hi', 'hey', 'hello',
    'how', 'what', 'why', 'when', 'where', 'which',
    'do', 'does', 'is', 'are', 'will', 'i',
    'a', 'an', 'the', 'to',
}


def _generate_title(first_message: str) -> str:
    words = first_message.strip().split()

    # Strip leading filler/question words
    while words and words[0].lower().rstrip('?!,') in _LEADING_FILLER:
        words = words[1:]

    if not words:
        # All words were filler — fall back to raw first 6
        words = first_message.strip().split()

    title = ' '.join(words[:6])
    if len(words) > 6:
        title += '…'

    return (title[:80].capitalize()) or 'New session'
