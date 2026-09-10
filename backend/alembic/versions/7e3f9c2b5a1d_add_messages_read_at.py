"""add_messages_read_at

Revision ID: 7e3f9c2b5a1d
Revises: c2a7e6f1b8d3
Create Date: 2026-08-17 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "7e3f9c2b5a1d"
down_revision: Union[str, None] = "c2a7e6f1b8d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages", sa.Column("read_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index("ix_messages_read_at", "messages", ["read_at"])


def downgrade() -> None:
    op.drop_index("ix_messages_read_at", table_name="messages")
    op.drop_column("messages", "read_at")
