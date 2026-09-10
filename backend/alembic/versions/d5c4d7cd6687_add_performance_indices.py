"""add_performance_indices

Revision ID: d5c4d7cd6687
Revises: 5a9233d65599
Create Date: 2026-08-04 17:49:52.229114

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text as _sa_text
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "d5c4d7cd6687"
down_revision: Union[str, None] = "5a9233d65599"
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
    # NOTE: estes índices já podem ter sido criados pela migration
    # 56d322bbd83a_add_performance_indices.py. Checamos a existência
    # antes de criar para manter a migration idempotente.
    if not _index_exists(conn, "ix_audit_controls_status", "audit_controls"):
        op.create_index("ix_audit_controls_status", "audit_controls", ["status"])
    if not _index_exists(conn, "ix_audits_client_user_id", "audits"):
        op.create_index("ix_audits_client_user_id", "audits", ["client_user_id"])
    if not _index_exists(conn, "ix_audits_status", "audits"):
        op.create_index("ix_audits_status", "audits", ["status"])


def _index_exists_fkguard(conn, index_name: str, table_name: str) -> bool:
    return (
        conn.execute(
            _sa_text(
                "SELECT COUNT(*) FROM information_schema.statistics "
                "WHERE table_schema = DATABASE() "
                "AND table_name = :tbl AND index_name = :idx"
            ),
            {"tbl": table_name, "idx": index_name},
        ).scalar()
        or 0
    ) > 0


def _index_backs_foreign_key(conn, index_name: str, table_name: str) -> bool:
    """True se alguma FOREIGN KEY desta tabela depende deste índice."""
    return (
        conn.execute(
            _sa_text(
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
        ).scalar()
        or 0
    ) > 0


def _drop_index_if_safe(index_name: str, table_name: str) -> None:
    """
    Remove o índice só se ele existir e nenhuma FK depender dele.

    O MySQL recusa `DROP INDEX` sobre um índice que sustenta uma FOREIGN
    KEY:

        (1553, "Cannot drop index '...': needed in a foreign key
                constraint")

    Quando a tabela inteira é removida logo em seguida, ou quando a
    coluna é removida, o índice vai junto — não há o que fazer aqui.
    Descoberto na primeira execução real do job `migrations` do CI
    (2026-08-26): a suíte usa `Base.metadata.create_all` e o SQLite não
    impõe a mesma restrição, então nenhum teste local alcançava isto.
    """
    conn = op.get_bind()
    if not _index_exists_fkguard(conn, index_name, table_name):
        return
    if _index_backs_foreign_key(conn, index_name, table_name):
        return
    op.drop_index(index_name, table_name=table_name)


def downgrade() -> None:
    conn = op.get_bind()
    if _index_exists(conn, "ix_audits_status", "audits"):
        _drop_index_if_safe("ix_audits_status", "audits")
    if _index_exists(conn, "ix_audits_client_user_id", "audits"):
        _drop_index_if_safe("ix_audits_client_user_id", "audits")
    if _index_exists(conn, "ix_audit_controls_status", "audit_controls"):
        _drop_index_if_safe("ix_audit_controls_status", "audit_controls")
