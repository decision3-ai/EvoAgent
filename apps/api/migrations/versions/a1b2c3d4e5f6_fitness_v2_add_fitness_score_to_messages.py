"""fitness_v2_add_fitness_score_to_messages

Revision ID: a1b2c3d4e5f6
Revises: d64050c53ba8
Create Date: 2026-04-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'd64050c53ba8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('messages', sa.Column('fitness_score', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('messages', 'fitness_score')
