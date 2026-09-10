"""restore_dashboard_card_indices

Revision ID: eafa65e9df05
Revises: 5457e7377a56
Create Date: 2026-08-12 10:25:25.272124

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "eafa65e9df05"
down_revision: Union[str, None] = "5457e7377a56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_exists(conn, index_name: str, table_name: str) -> bool:
    result = conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.statistics "
            "WHERE table_schema = DATABASE() "
            "AND table_name = :tbl AND index_name = :idx"
        ),
        {"tbl": table_name, "idx": index_name},
    )
    return result.scalar() > 0


def upgrade() -> None:
    conn = op.get_bind()
    if not _index_exists(
        conn,
        "ix_dashboard_card_history_entries_actor_user_id",
        "dashboard_card_history_entries",
    ):
        op.create_index(
            "ix_dashboard_card_history_entries_actor_user_id",
            "dashboard_card_history_entries",
            ["actor_user_id"],
        )
    if not _index_exists(
        conn, "ix_dashboard_card_messages_author_user_id", "dashboard_card_messages"
    ):
        op.create_index(
            "ix_dashboard_card_messages_author_user_id",
            "dashboard_card_messages",
            ["author_user_id"],
        )
    if not _index_exists(
        conn, "ix_dashboard_card_messages_message_type", "dashboard_card_messages"
    ):
        op.create_index(
            "ix_dashboard_card_messages_message_type",
            "dashboard_card_messages",
            ["message_type"],
        )


def _index_backs_foreign_key(conn, index_name: str, table_name: str) -> bool:
    """
    True se alguma FOREIGN KEY desta tabela depende deste índice.

    O MySQL exige um índice para cada FK e **recusa** removê-lo enquanto
    a constraint existir:

        (1553, "Cannot drop index '...': needed in a foreign key
                constraint")

    Esta migration existe justamente para RESTAURAR índices que não
    deviam ter sido removidos; o downgrade dela tentar removê-los de
    novo recria o problema que ela veio consertar — e nem chega lá,
    porque o servidor barra antes.
    """
    result = conn.execute(
        text(
            "SELECT COUNT(*) "
            "FROM information_schema.key_column_usage kcu "
            "JOIN information_schema.statistics s "
            "  ON s.table_schema = kcu.table_schema "
            " AND s.table_name   = kcu.table_name "
            " AND s.column_name  = kcu.column_name "
            "WHERE kcu.table_schema = DATABASE() "
            "  AND kcu.table_name = :tbl "
            "  AND kcu.referenced_table_name IS NOT NULL "
            "  AND s.index_name = :idx"
        ),
        {"tbl": table_name, "idx": index_name},
    )
    return (result.scalar() or 0) > 0


def _drop_index_se_seguro(conn, index_name: str, table_name: str) -> None:
    """Remove o índice só se ele existir E nenhuma FK depender dele."""
    if not _index_exists(conn, index_name, table_name):
        return
    if _index_backs_foreign_key(conn, index_name, table_name):
        return
    op.drop_index(index_name, table_name)


def downgrade() -> None:
    """
    Descoberto na primeira execução real do job `migrations` do CI
    (2026-08-26): `alembic downgrade base` quebrava aqui. A suíte usa
    `Base.metadata.create_all` e o SQLite não impõe a restrição do MySQL,
    então nenhum teste local alcançava este caminho.
    """
    conn = op.get_bind()

    _drop_index_se_seguro(
        conn, "ix_dashboard_card_messages_message_type", "dashboard_card_messages"
    )
    _drop_index_se_seguro(
        conn, "ix_dashboard_card_messages_author_user_id", "dashboard_card_messages"
    )
    _drop_index_se_seguro(
        conn,
        "ix_dashboard_card_history_entries_actor_user_id",
        "dashboard_card_history_entries",
    )
