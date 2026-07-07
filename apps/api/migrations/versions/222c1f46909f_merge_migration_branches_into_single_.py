"""merge migration branches into single head

Revision ID: 222c1f46909f
Revises: 1cc1080c3866, 20260612_embed_768
Create Date: 2026-07-07 10:54:19.856808

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '222c1f46909f'
down_revision: Union[str, None] = ('1cc1080c3866', '20260612_embed_768')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
