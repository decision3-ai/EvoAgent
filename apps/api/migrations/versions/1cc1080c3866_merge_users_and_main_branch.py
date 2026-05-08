"""merge_users_and_main_branch

Revision ID: 1cc1080c3866
Revises: b2c3d4e5f6a7, 20260502_evo_points
Create Date: 2026-05-05 11:09:40.892886

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1cc1080c3866'
down_revision: Union[str, None] = ('b2c3d4e5f6a7', '20260502_evo_points')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
