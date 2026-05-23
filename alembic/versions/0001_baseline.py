"""baseline — schema inicial FlowCast v0.9.x

Revision ID: 0001
Revises:
Create Date: 2026-05-22

Revisión vacía que representa el estado del schema antes de que Alembic
fuera introducido. Instalaciones nuevas la reciben via create_all() + stamp;
instalaciones existentes la reciben via stamp al primer arranque post-v1.0.
"""
from typing import Sequence, Union

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
