"""fix_dashboard_card_checklist_items_pk

Revision ID: 5a9233d65599
Revises: 5e977e8b49da
Create Date: 2026-07-27 00:00:00.000000

Corrige a regressão introduzida pela migration d60f999c1fca, que renomeou a
PK de dashboard_card_checklist_items de `id` para `iid` (via add_column +
drop_column) sem que o model ORM (DashboardCardchecklistItem) ou nenhuma
migration posterior refletisse essa mudança. O model continua declarando
`id` como chave primária, então qualquer query contra essa tabela falha com
"Unknown column 'dashboard_card_checklist_items.id'" em um banco migrado do
zero. Ver docs/relatorio_bugs.md B-C18 e docs/plano_implementacao.md FASE 1B.3.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '5a9233d65599'
down_revision: Union[str, None] = '5e977e8b49da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "dashboard_card_checklist_items"


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    result = conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = DATABASE() "
            "AND table_name = :tbl AND column_name = :col"
        ),
        {"tbl": table_name, "col": column_name},
    )
    return result.scalar() > 0


def _has_primary_key(conn, table_name: str) -> bool:
    result = conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.statistics "
            "WHERE table_schema = DATABASE() "
            "AND table_name = :tbl AND index_name = 'PRIMARY'"
        ),
        {"tbl": table_name},
    )
    return result.scalar() > 0


def upgrade() -> None:
    conn = op.get_bind()

    has_iid = _column_exists(conn, TABLE, "iid")
    has_id = _column_exists(conn, TABLE, "id")
    has_pk = _has_primary_key(conn, TABLE)

    if has_iid and not has_id:
        if has_pk:
            # A tabela já tem uma PRIMARY KEY em outra coluna: renomear é seguro.
            op.alter_column(
                TABLE,
                "iid",
                new_column_name="id",
                existing_type=sa.Integer(),
                existing_nullable=False,
                existing_autoincrement=True,
            )
        else:
            # MySQL exige que uma coluna AUTO_INCREMENT seja definida como
            # chave na MESMA instrução — CHANGE + ADD PRIMARY KEY separados
            # falham com erro 1075 ("there can be only one auto column and
            # it must be defined as a key"). Combinar em um único ALTER TABLE.
            op.execute(
                f"ALTER TABLE {TABLE} "
                f"CHANGE iid id INTEGER NOT NULL AUTO_INCREMENT, "
                f"ADD PRIMARY KEY (id)"
            )
            has_pk = True

    if not has_pk and _column_exists(conn, TABLE, "id"):
        op.execute(f"ALTER TABLE {TABLE} ADD PRIMARY KEY (id)")


def downgrade() -> None:
    conn = op.get_bind()

    has_id = _column_exists(conn, TABLE, "id")
    has_iid = _column_exists(conn, TABLE, "iid")

    if has_id and not has_iid:
        op.alter_column(
            TABLE,
            "id",
            new_column_name="iid",
            existing_type=sa.Integer(),
            existing_nullable=False,
            existing_autoincrement=True,
        )
