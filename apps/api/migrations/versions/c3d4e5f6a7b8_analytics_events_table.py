"""analytics_events table

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-04-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'analytics_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('session_id', UUID(as_uuid=True), sa.ForeignKey('sessions.id'), nullable=True),
        sa.Column('message_id', UUID(as_uuid=True), sa.ForeignKey('messages.id'), nullable=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_analytics_events_workspace_id', 'analytics_events', ['workspace_id'])
    op.create_index('ix_analytics_events_session_id', 'analytics_events', ['session_id'])
    op.create_index('ix_analytics_events_message_id', 'analytics_events', ['message_id'])
    op.create_index('ix_analytics_events_event_type', 'analytics_events', ['event_type'])


def downgrade() -> None:
    op.drop_index('ix_analytics_events_event_type', 'analytics_events')
    op.drop_index('ix_analytics_events_message_id', 'analytics_events')
    op.drop_index('ix_analytics_events_session_id', 'analytics_events')
    op.drop_index('ix_analytics_events_workspace_id', 'analytics_events')
    op.drop_table('analytics_events')
