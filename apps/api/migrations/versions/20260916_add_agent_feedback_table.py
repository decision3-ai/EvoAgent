"""add agent_feedback table for fine-tuning data collection

Revision ID: 20260916_agent_feedback
Revises: 222c1f46909f
Create Date: 2026-09-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = '20260916_agent_feedback'
down_revision: Union[str, None] = '222c1f46909f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'agent_feedback',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('now()'),
        ),
        sa.Column('session_id', UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('agent_name', sa.String(100), nullable=True),
        sa.Column('task_type', sa.String(100), nullable=True),
        sa.Column('model_used', sa.String(100), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('user_input', sa.Text(), nullable=False),
        sa.Column('agent_output', sa.Text(), nullable=False),
        sa.Column('feedback_type', sa.String(20), nullable=False),
        sa.Column('corrected_output', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
    )
    op.create_index('ix_agent_feedback_session_id', 'agent_feedback', ['session_id'])
    op.create_index('ix_agent_feedback_user_id', 'agent_feedback', ['user_id'])
    op.create_index('ix_agent_feedback_feedback_type', 'agent_feedback', ['feedback_type'])


def downgrade() -> None:
    op.drop_index('ix_agent_feedback_feedback_type', table_name='agent_feedback')
    op.drop_index('ix_agent_feedback_user_id', table_name='agent_feedback')
    op.drop_index('ix_agent_feedback_session_id', table_name='agent_feedback')
    op.drop_table('agent_feedback')
