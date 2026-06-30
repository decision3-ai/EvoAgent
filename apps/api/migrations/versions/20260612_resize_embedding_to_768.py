"""resize agent_memories.embedding to 768 dims (Ollama nomic-embed-text)

Revision ID: 20260612_embed_768
Revises: 20260502_evo_points
Create Date: 2026-06-12 00:00:00.000000

WARNING: destructive for embedding data — existing 1536-dim OpenAI embeddings
are incompatible with 768-dim nomic-embed-text vectors, so the column is
NULLed before the type change. Memories themselves are kept; embeddings are
regenerated as memories are written/retrieved going forward.
"""
from typing import Sequence, Union

from alembic import op


revision: str = '20260612_embed_768'
down_revision: Union[str, None] = '20260502_evo_points'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index('ix_agent_memories_embedding', table_name='agent_memories')
    op.execute('UPDATE agent_memories SET embedding = NULL')
    op.execute('ALTER TABLE agent_memories ALTER COLUMN embedding TYPE vector(768)')
    op.create_index(
        'ix_agent_memories_embedding',
        'agent_memories',
        ['embedding'],
        postgresql_using='ivfflat',
        postgresql_with={'lists': 100},
        postgresql_ops={'embedding': 'vector_cosine_ops'},
    )


def downgrade() -> None:
    op.drop_index('ix_agent_memories_embedding', table_name='agent_memories')
    op.execute('UPDATE agent_memories SET embedding = NULL')
    op.execute('ALTER TABLE agent_memories ALTER COLUMN embedding TYPE vector(1536)')
    op.create_index(
        'ix_agent_memories_embedding',
        'agent_memories',
        ['embedding'],
        postgresql_using='ivfflat',
        postgresql_with={'lists': 100},
        postgresql_ops={'embedding': 'vector_cosine_ops'},
    )
