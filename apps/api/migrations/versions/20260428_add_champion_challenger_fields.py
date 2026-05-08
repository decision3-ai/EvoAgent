"""add champion/challenger fields to agent_profiles

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('agent_profiles', sa.Column('challenger_prompt', sa.Text(), nullable=True))
    op.add_column('agent_profiles', sa.Column('challenger_started_at', sa.DateTime(), nullable=True))
    op.add_column('agent_profiles', sa.Column('active_variant', sa.String(50), nullable=False, server_default='champion'))


def downgrade() -> None:
    op.drop_column('agent_profiles', 'active_variant')
    op.drop_column('agent_profiles', 'challenger_started_at')
    op.drop_column('agent_profiles', 'challenger_prompt')
