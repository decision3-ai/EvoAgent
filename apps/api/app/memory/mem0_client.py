"""
Mem0 memory client — wraps mem0ai for async use.

Vector store : our existing PostgreSQL + pgvector (DATABASE_URL)
LLM          : Claude haiku via OpenRouter (OPENROUTER_API_KEY) — used for fact extraction
Embedder     : Ollama nomic-embed-text (OLLAMA_BASE_URL) — used for vector search,
               accessed through Ollama's OpenAI-compatible /v1 endpoint (768 dims)
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

import openai

from app.core.config import settings

logger = logging.getLogger(__name__)

# Embedding client — Ollama via its OpenAI-compatible /v1 endpoint
_embed_client: Optional[openai.AsyncOpenAI] = None


def _get_embed_client() -> openai.AsyncOpenAI:
    """Lazy singleton for Ollama embedding client (OpenAI-compatible API)."""
    global _embed_client
    if _embed_client is None:
        _embed_client = openai.AsyncOpenAI(
            base_url=f'{settings.OLLAMA_BASE_URL}/v1',
            api_key='ollama',  # required by client, ignored by Ollama
        )
    return _embed_client


async def _embed_text(text: str) -> Optional[List[float]]:
    """
    Generate embedding vector for text using Ollama nomic-embed-text.
    Returns 768-dimensional vector or None on error.
    """
    try:
        client = _get_embed_client()
        response = await client.embeddings.create(
            model='nomic-embed-text',
            input=text,
        )
        return response.data[0].embedding
    except Exception:
        logger.exception('Ollama embedding failed')
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
                'provider': 'openai',  # OpenRouter is OpenAI-compatible
                'config': {
                    'model': 'anthropic/claude-haiku-4.5',
                    'api_key': settings.OPENROUTER_API_KEY,
                    'openai_base_url': 'https://openrouter.ai/api/v1',
                },
            },
            'embedder': {
                'provider': 'openai',  # Ollama is OpenAI-compatible
                'config': {
                    'api_key': 'ollama',
                    'model': 'nomic-embed-text',
                    'openai_base_url': f'{settings.OLLAMA_BASE_URL}/v1',
                },
            },
            'vector_store': {
                'provider': 'pgvector',
                'config': {
                    **db,
                    'collection_name': 'agent_memories',
                    'embedding_model_dims': 768,
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

    Uses Ollama nomic-embed-text to embed the query, then performs
    pgvector cosine similarity search against stored memory embeddings.
    Falls back to importance_score ranking if embeddings unavailable.
    Updates last_used_at for retrieved rows.

    Returns a list of plain-text content strings (empty list on any error).
    """
    try:
        from sqlalchemy import text, bindparam
        from app.core.database import AsyncSessionLocal

        agent_uuid = uuid.UUID(agent_id)
        now = datetime.utcnow()

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
                               1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
                        FROM agent_memories
                        WHERE workspace_id = :agent_id
                          AND embedding IS NOT NULL
                        ORDER BY embedding <=> CAST(:embedding AS vector)
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
    Returns 768-dimensional vector or None on error.
    """
    return await _embed_text(content)
