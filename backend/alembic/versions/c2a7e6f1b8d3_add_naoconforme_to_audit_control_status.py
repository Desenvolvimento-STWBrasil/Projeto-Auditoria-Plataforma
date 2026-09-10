"""add_naoconforme_to_audit_control_status

Revision ID: c2a7e6f1b8d3
Revises: bf7239a52df8
Create Date: 2026-08-17 10:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c2a7e6f1b8d3"
down_revision: Union[str, None] = "bf7239a52df8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Alinha `AuditControlStatus` (domínio Audit/AuditControl, consumido por
    /api/v1/client/controls e pela tela /private/admin/auditorias) com
    `DashboardCardStatus` (domínio DashboardCard), que já tinha 4 valores
    desde 9d5a3c1b2e77 — bug B-M20 do relatorio_bugs.md, agora com decisão
    de produto confirmada: os dois domínios devem expor o mesmo vocabulário
    de status ao cliente.
    """
    op.alter_column(
        "audit_controls",
        "status",
        existing_type=sa.Enum(
            "EM_ANALISE", "PARCIAL", "CONFORME", name="audit_control_status"
        ),
        type_=sa.Enum(
            "EM_ANALISE",
            "PARCIAL",
            "CONFORME",
            "NAOCONFORME",
            name="audit_control_status",
        ),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Reverter exige que nenhuma linha esteja em NAOCONFORME — não migramos
    # dados automaticamente aqui, mesma convenção das demais migrations
    # deste projeto que não fazem downgrade de dados com perda silenciosa.
    op.alter_column(
        "audit_controls",
        "status",
        existing_type=sa.Enum(
            "EM_ANALISE",
            "PARCIAL",
            "CONFORME",
            "NAOCONFORME",
            name="audit_control_status",
        ),
        type_=sa.Enum(
            "EM_ANALISE", "PARCIAL", "CONFORME", name="audit_control_status"
        ),
        existing_nullable=False,
    )
