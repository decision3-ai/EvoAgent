"""
Mem0 memory client — wraps mem0ai for async use.

Vector store : our existing PostgreSQL + pgvector (DATABASE_URL)
LLM          : Anthropic claude-haiku (ANTHROPIC_API_KEY) — used for fact extraction
Embedder     : OpenAI text-embedding-3-small (OPENAI_API_KEY) — used for vector search
               NOTE: Anthropic does not provide an embeddings API, so OpenAI is required
               for the vector component. Both keys must be set in the environment.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlparse

import openai

from app.core.config import settings

logger = logging.getLogger(__name__)

# OpenAI client for embeddings
_openai_client: Optional[openai.AsyncOpenAI] = None


def _get_openai_client() -> openai.AsyncOpenAI:
    """Lazy singleton for OpenAI async client."""
    global _openai_client
    if _openai_client is None:
        _openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


async def _embed_text(text: str) -> Optional[List[float]]:
    """
    Generate embedding vector for text using OpenAI text-embedding-3-small.
    Returns 1536-dimensional vector or None on error.
    """
    try:
        client = _get_openai_client()
        response = await client.embeddings.create(
            model='text-embedding-3-small',
            input=text,
        )
        return response.data[0].embedding
    except Exception:
        logger.exception('OpenAI embedding failed')
        return None

_memory_client = None


def _parse_db_url(url: str) -> dict:
    """Convert asyncpg DATABASE_URL to plain psycopg2 connection params for mem0."""
    clean = url.replace('postgresql+asyncpg://', 'postgresql://')
    p = urlparse(clean)
    return {
        'host': p.hostname,
        'port': p.port or 5432,
        'dbname': p.path.lstrip('/'),
        'user': p.username,
        'password': p.password,
    }


def _get_client():
    """Lazy singleton — initialised once on first call."""
    global _memory_client
    if _memory_client is None:
        from mem0 import Memory  # imported lazily so startup doesn't fail if not installed
        db = _parse_db_url(settings.DATABASE_URL)
        config = {
            'llm': {
                'provider': 'anthropic',
                'config': {
                    'model': 'claude-haiku-4-5-20251001',
                    'api_key': settings.ANTHROPIC_API_KEY,
                },
            },
            'embedder': {
                'provider': 'openai',
                'config': {
                    'api_key': settings.OPENAI_API_KEY,
                    'model': 'text-embedding-3-small',
                },
            },
            'vector_store': {
                'provider': 'pgvector',
                'config': {
                    **db,
                    'collection_name': 'agent_memories',
                    'embedding_model_dims': 1536,
                },
            },
        }
        _memory_client = Memory.from_config(config)
    return _memory_client


async def save_memory(workspace_id: str, messages: list, agent_id: str) -> None:
    """
    Extract key facts from the latest exchange and persist them.

    messages — list of {"role": "user"|"assistant", "content": "..."} for this turn only.
    Runs in a thread pool so the sync mem0 client doesn't block the event loop.
    """
    try:
        client = _get_client()
        user_id = f'{workspace_id}:{agent_id}'
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: client.add(messages, user_id=user_id))
    except Exception:
        logger.exception('mem0 save_memory failed — skipping')


async def get_relevant_memories(agent_id: str, query: str) -> List[str]:
    """
    Fetch top-5 memories for this agent using multilingual vector search.

    Uses OpenAI text-embedding-3-small to embed the query, then performs
    pgvector cosine similarity search against stored memory embeddings.
    Falls back to importance_score ranking if embeddings unavailable.
    Updates last_used_at for retrieved rows.

    Returns a list of plain-text content strings (empty list on any error).
    """
    try:
        from sqlalchemy import text, bindparam
        from app.core.database import AsyncSessionLocal

        agent_uuid = uuid.UUID(agent_id)
        now = datetime.now(timezone.utc)

        # Generate embedding for the query
        query_embedding = await _embed_text(query)

        async with AsyncSessionLocal() as db:
            rows = []

            # Try vector similarity search if we have a valid embedding
            if query_embedding:
                # Convert to PostgreSQL array literal
                embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'

                result = await db.execute(
                    text(
                        '''
                        SELECT id, content,
                               1 - (embedding <=> :embedding::vector) AS similarity
                        FROM agent_memories
                        WHERE workspace_id = :agent_id
                          AND embedding IS NOT NULL
                        ORDER BY embedding <=> :embedding::vector
                        LIMIT 5
                        '''
                    ),
                    {'agent_id': agent_uuid, 'embedding': embedding_str},
                )
                rows = result.fetchall()

            # Fallback to importance_score ranking if no vector matches
            if not rows:
                result = await db.execute(
                    text(
                        'SELECT id, content FROM agent_memories '
                        'WHERE workspace_id = :agent_id '
                        'ORDER BY importance_score DESC '
                        'LIMIT 5'
                    ),
                    {'agent_id': agent_uuid},
                )
                rows = result.fetchall()

            if not rows:
                return []

            contents = [row.content for row in rows]
            ids = [row.id for row in rows]

            # Update last_used_at for the exact rows we retrieved
            await db.execute(
                text(
                    'UPDATE agent_memories SET last_used_at = :now '
                    'WHERE id IN :ids'
                ).bindparams(bindparam('ids', expanding=True)),
                {'now': now, 'ids': ids},
            )
            await db.commit()

            return contents
    except Exception:
        logger.exception('get_relevant_memories failed — skipping')
        return []


async def embed_memory_content(content: str) -> Optional[List[float]]:
    """
    Generate embedding for memory content before storing.

    Call this when inserting into agent_memories to populate the embedding column.
    Returns 1536-dimensional vector or None on error.
    """
    return await _embed_text(content)
