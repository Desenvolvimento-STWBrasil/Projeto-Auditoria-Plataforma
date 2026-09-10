"""fix_evidences_and_messages_naming_typos

Revision ID: 83cf1e14efa8
Revises: 0ba953b10f8b
Create Date: 2026-08-12 11:43:01.736995

Corrige os 2 typos de nomenclatura remanescentes do inventário E.3 de
docs/plano_implementacao.md, consolidados desde a migration inicial
(86f95e525db1):
- `evidences.create_at` -> `evidences.created_at` (faltava o "d").
- Tabela `messagens` -> `messages` (nome errado em português/inglês
  misturado; todas as outras tabelas do projeto usam nomes em inglês).

Nenhuma FK de outra tabela aponta para `messagens` (confirmado por grep em
app/models/**), e nenhum código de aplicação lê `Evidence.create_at`/
`.created_at` diretamente hoje — ambas as tabelas estavam vazias em
desenvolvimento no momento desta migration. Risco de dado: zero.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "83cf1e14efa8"
down_revision: Union[str, None] = "0ba953b10f8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "evidences",
        "create_at",
        new_column_name="created_at",
        existing_type=sa.DateTime(timezone=True),
        existing_server_default=sa.text("now()"),
        existing_nullable=False,
    )

    op.rename_table("messagens", "messages")
    op.execute(
        "ALTER TABLE messages RENAME INDEX ix_messagens_audit_control_id "
        "TO ix_messages_audit_control_id"
    )
    op.execute(
        "ALTER TABLE messages RENAME INDEX ix_messagens_author_user_id "
        "TO ix_messages_author_user_id"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE messages RENAME INDEX ix_messages_author_user_id "
        "TO ix_messagens_author_user_id"
    )
    op.execute(
        "ALTER TABLE messages RENAME INDEX ix_messages_audit_control_id "
        "TO ix_messagens_audit_control_id"
    )
    op.rename_table("messages", "messagens")

    op.alter_column(
        "evidences",
        "created_at",
        new_column_name="create_at",
        existing_type=sa.DateTime(timezone=True),
        existing_server_default=sa.text("now()"),
        existing_nullable=False,
    )
