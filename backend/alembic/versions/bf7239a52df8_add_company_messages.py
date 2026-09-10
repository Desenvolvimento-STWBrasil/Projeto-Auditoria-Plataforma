"""add_company_messages

Revision ID: bf7239a52df8
Revises: f224a87de1a4
Create Date: 2026-08-12 15:29:00.118092

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "bf7239a52df8"
down_revision: Union[str, None] = "f224a87de1a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "company_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_company_messages_company_id", "company_messages", ["company_id"]
    )
    op.create_index(
        "ix_company_messages_author_user_id", "company_messages", ["author_user_id"]
    )
    op.create_index("ix_company_messages_read_at", "company_messages", ["read_at"])


def downgrade() -> None:
    """
    Sem `drop_index` explícito: `op.drop_table` já remove os índices da
    tabela, e no MySQL um índice que sustenta uma FOREIGN KEY **não pode**
    ser removido antes dela:

        (1553, "Cannot drop index '...': needed in a foreign key
                constraint")

    Os `drop_index` que existiam aqui eram redundantes com o `drop_table`
    e quebravam a cadeia. Descoberto na primeira execução real do job
    `migrations` do CI (2026-08-26) — a suíte usa
    `Base.metadata.create_all` e o SQLite não aplica a mesma restrição,
    então nenhum teste local exercitava isto.
    """
    op.drop_table("company_messages")
