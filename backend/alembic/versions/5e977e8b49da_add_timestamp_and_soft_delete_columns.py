"""add_timestamp_and_soft_delete_columns

Revision ID: 5e977e8b49da
Revises: 56d322bbd83a
Create Date: 2026-06-26 15:11:36.966647

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = '5e977e8b49da'
down_revision: Union[str, None] = '56d322bbd83a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    for table in ["users", "audits", "audit_controls"]:
        op.add_column(table, sa.Column("updated_at", sa.DateTime(timezone=True),
                                       server_default=sa.text("now()"), nullable=False))
        op.add_column(table, sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for table in ["users", "audits", "audit_controls"]:
        op.drop_column(table, "updated_at")
        op.drop_column(table, "deleted_at")
