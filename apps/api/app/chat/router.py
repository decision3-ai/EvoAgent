"""
Chat router — the core of evoagent.io v1.

All LLM calls go through OpenRouter (fallback chain of models).
"""

import json
import time
import uuid
import logging
import httpx
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db, AsyncSessionLocal
from app.core.auth import get_current_user_id
from app.core.celery import celery_client
from app.core.redis import get_redis
from app.workspaces.models import Workspace, Session, Message
from app.workspaces.schemas import ChatRequest, ChatResponse, MessageResponse
from app.workspaces.helpers import _get_owned_workspace, _get_session
from app.memory.mem0_client import get_relevant_memories
from app.evolution.constitutional import apply_constitutional_rules

logger = logging.getLogger(__name__)
router = APIRouter()

_OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'

# Fallback chain: cheapest first, Claude (via OpenRouter) as last resort
_FALLBACK_CHAIN = [
    'deepseek/deepseek-chat',
    'google/gemini-2.0-flash-001',
    'anthropic/claude-sonnet-4.6',
]


async def _call_with_fallback(
    messages: list[dict],
    system_prompt: str,
    max_tokens: int,
) -> tuple[str, int, str]:
    """Try each provider in order. Returns (text, tokens_used, model_used)."""
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError('OPENROUTER_API_KEY is not set — all LLM calls go through OpenRouter')

    errors: list[str] = []
    for model in _FALLBACK_CHAIN:
        try:
            msgs = (
                [{'role': 'system', 'content': system_prompt}] if system_prompt else []
            ) + messages
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    _OPENROUTER_URL,
                    headers={
                        'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}',
                        'Content-Type': 'application/json',
                    },
                    json={'model': model, 'messages': msgs, 'max_tokens': max_tokens},
                )
                resp.raise_for_status()
                data = resp.json()
                text = data['choices'][0]['message']['content']
                usage = data.get('usage', {})
                tokens_used = (
                    usage.get('prompt_tokens', 0) + usage.get('completion_tokens', 0)
                )

            logger.info('llm_call provider=openrouter model=%s tokens=%d', model, tokens_used)
            return text, tokens_used, model

        except Exception as exc:
            logger.warning('llm_provider_failed provider=openrouter model=%s error=%s', model, exc)
            errors.append(f'{model}: {exc}')

    raise RuntimeError(f'All LLM providers failed: {"; ".join(errors)}')


async def _stream_with_fallback(
    messages: list[dict],
    system_prompt: str,
    max_tokens: int,
) -> AsyncGenerator[tuple[str, str | None, int | None], None]:
    """
    Stream tokens with fallback chain. Yields tuples:
      - ('token', text, None) for each token
      - ('done', model_used, tokens_used) at end
      - ('error', error_msg, None) if all providers fail
    """
    if not settings.OPENROUTER_API_KEY:
        yield ('error', 'OPENROUTER_API_KEY is not set — all LLM calls go through OpenRouter', None)
        return

    errors: list[str] = []

    for model in _FALLBACK_CHAIN:
        try:
            msgs = (
                [{'role': 'system', 'content': system_prompt}] if system_prompt else []
            ) + messages
            headers = {
                'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}',
                'Content-Type': 'application/json',
            }
            body = {'model': model, 'messages': msgs, 'max_tokens': max_tokens, 'stream': True}

            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream('POST', _OPENROUTER_URL, headers=headers, json=body) as resp:
                    resp.raise_for_status()
                    tokens_estimate = 0
                    async for line in resp.aiter_lines():
                        if not line.startswith('data: '):
                            continue
                        payload = line[6:]
                        if payload.strip() == '[DONE]':
                            break
                        chunk = json.loads(payload)
                        content = chunk['choices'][0]['delta'].get('content') or ''
                        if content:
                            tokens_estimate += len(content) // 4  # rough estimate
                            yield ('token', content, None)

            logger.info('llm_stream provider=openrouter model=%s', model)
            yield ('done', model, tokens_estimate)
            return

        except Exception as exc:
            logger.warning('llm_stream_failed provider=openrouter model=%s error=%s', model, exc)
            errors.append(f'{model}: {exc}')

    yield ('error', f'All providers failed: {"; ".join(errors)}', None)


async def _resolve_system_prompt(session_id: uuid.UUID, agent) -> str:
    """Return challenger_prompt if this session was assigned the challenger variant, else champion."""
    r = get_redis()
    variant = await r.get(f'session_variant:{session_id}')
    if variant == 'challenger' and agent.challenger_prompt:
        return agent.challenger_prompt
    return agent.system_prompt or ''


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

    system_prompt = await _resolve_system_prompt(session_id, agent)

    # Retrieve relevant memories and prepend to system prompt
    memories = await get_relevant_memories(str(agent.id), payload.message)
    if memories:
        mem_block = 'What I know about you:\n' + '\n'.join(f'- {m}' for m in memories)
        system_prompt = (mem_block + '\n\n' + system_prompt) if system_prompt else mem_block

    # Append constitutional rules (V3.5)
    system_prompt = apply_constitutional_rules(system_prompt)

    # Only user/assistant roles go into messages array (Anthropic API requirement)
    chat_messages = [
        {'role': m.role, 'content': m.content}
        for m in history
        if m.role in ('user', 'assistant')
    ]

    response_text, tokens_used, model_used = await _call_with_fallback(
        chat_messages, system_prompt, agent.max_tokens,
    )
    latency_ms = int((time.monotonic() - start) * 1000)

    assistant_msg = Message(
        session_id=session_id,
        role='assistant',
        content=response_text,
        latency_ms=latency_ms,
        tokens_used=tokens_used,
        artifacts=[{'model_used': model_used}],
    )
    db.add(assistant_msg)

    # Auto-title the session from its first user message
    if session.title == 'New session':
        session.title = _generate_title(payload.message)

    await db.commit()
    await db.refresh(user_msg)
    await db.refresh(assistant_msg)

    # Extract and persist typed session memories (fire-and-forget Celery task)
    celery_client.send_task(
        'tasks.agent_tasks.write_session_memories',
        args=[str(workspace_id), str(session_id), [
            {'role': 'user', 'content': payload.message},
            {'role': 'assistant', 'content': response_text},
        ]],
    )

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
    system_prompt = await _resolve_system_prompt(session_id, agent)
    max_tokens = agent.max_tokens
    session_title = session.title
    user_msg_response = MessageResponse.model_validate(user_msg).model_dump(mode='json')

    # Retrieve relevant memories and inject into system prompt
    memories = await get_relevant_memories(str(agent.id), payload.message)
    if memories:
        mem_block = 'What I know about you:\n' + '\n'.join(f'- {m}' for m in memories)
        system_prompt = (mem_block + '\n\n' + system_prompt) if system_prompt else mem_block

    # Append constitutional rules (V3.5)
    system_prompt = apply_constitutional_rules(system_prompt)

    # Capture for task dispatch inside generator
    workspace_id_str = str(workspace_id)
    session_id_str = str(session_id)
    user_message_text = payload.message

    async def event_stream():
        # Event 1: confirm user message saved
        yield f'data: {json.dumps({"type": "start", "user_message": user_msg_response, "session_title": session_title})}\n\n'

        full_text = ''
        start = time.monotonic()
        tokens_used = 0
        model_used = 'unknown'

        async for event_type, chunk, extra in _stream_with_fallback(
            chat_messages, system_prompt, max_tokens
        ):
            if event_type == 'token':
                full_text += chunk
                yield f'data: {json.dumps({"type": "token", "text": chunk})}\n\n'
            elif event_type == 'done':
                model_used = chunk
                tokens_used = extra or 0
            elif event_type == 'error':
                logger.error('Stream fallback exhausted: %s', chunk)
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
                artifacts=[{'model_used': model_used}],
            )
            save_db.add(assistant_msg)
            await save_db.commit()
            await save_db.refresh(assistant_msg)
            assistant_response = MessageResponse.model_validate(assistant_msg).model_dump(mode='json')

        # Extract and persist typed session memories (fire-and-forget Celery task)
        celery_client.send_task(
            'tasks.agent_tasks.write_session_memories',
            args=[workspace_id_str, session_id_str, [
                {'role': 'user', 'content': user_message_text},
                {'role': 'assistant', 'content': full_text},
            ]],
        )

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
