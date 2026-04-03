"""fix_agent_model_default_and_data

Revision ID: d64050c53ba8
Revises: 606fa47daa6a
Create Date: 2026-03-28 10:15:58.671021

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd64050c53ba8'
down_revision: Union[str, None] = '606fa47daa6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VALID_MODELS = (
    'claude-haiku-4-5-20251001',
    'claude-sonnet-4-5-20250929',
    'claude-sonnet-4-6',
    'claude-opus-4-5-20251101',
)
DEFAULT_MODEL = 'claude-haiku-4-5-20251001'


def upgrade() -> None:
    # 1. Update server default for new rows
    op.alter_column(
        'agent_profiles',
        'model',
        server_default=DEFAULT_MODEL,
        existing_type=sa.String(100),
        existing_nullable=False,
    )

    # 2. Data migration — replace all invalid/null models in existing rows
    valid_list = ', '.join(f"'{m}'" for m in VALID_MODELS)
    op.execute(
        f"""
        UPDATE agent_profiles
        SET model = '{DEFAULT_MODEL}'
        WHERE model IS NULL
           OR model NOT IN ({valid_list})
        """
    )


def downgrade() -> None:
    op.alter_column(
        'agent_profiles',
        'model',
        server_default='gpt-4o',
        existing_type=sa.String(100),
        existing_nullable=False,
    )
