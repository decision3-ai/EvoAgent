"""add embedding column to agent_memories

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure pgvector extension exists
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Add embedding column (1536 dims for text-embedding-3-small)
    op.add_column(
        'agent_memories',
        sa.Column('embedding', Vector(1536), nullable=True)
    )

    # Create index for fast cosine similarity search
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
    op.drop_column('agent_memories', 'embedding')
