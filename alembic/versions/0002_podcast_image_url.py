"""podcast image_url column

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("podcasts") as batch_op:
        batch_op.add_column(sa.Column("image_url", sa.String(2048), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("podcasts") as batch_op:
        batch_op.drop_column("image_url")
