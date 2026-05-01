"""add_detection_time_metrics

Revision ID: c92c1c4b6a82
Revises: 227c5459da7d
Create Date: 2026-05-01 16:37:39.297713

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c92c1c4b6a82'
down_revision: Union[str, None] = '227c5459da7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
