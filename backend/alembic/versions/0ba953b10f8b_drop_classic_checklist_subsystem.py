"""drop_classic_checklist_subsystem

Revision ID: 0ba953b10f8b
Revises: eafa65e9df05
Create Date: 2026-08-12 10:44:37.256104

Remove o subsistema de checklist "clássico" (`checklist_items` +
`checklist_item_state`), criado pela migration `86f95e525db1` e nunca
consumido por nenhum endpoint HTTP (achado do inventário E.3 de
`docs/plano_implementacao.md`; substituído em produção pelo domínio
paralelo `dashboard_card_checklist_items`/`DashboardCardchecklistItem`,
que NÃO é afetado por esta migration).

Confirmado antes de escrever esta migration (2026-08-12):
- Nenhuma rota em `app/api/v1/**` referencia `checklistItem`/`checklistItemState`.
- `checklist_item_state` está vazia em produção/dev (0 linhas) — nunca foi
  escrita por nenhum fluxo real.
- `checklist_items` só contém as 7 linhas de seed (`scripts/seed_catalog.py`),
  sem nenhuma escrita fora do seed.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0ba953b10f8b"
down_revision: Union[str, None] = "eafa65e9df05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ordem: tabela filha (FK para checklist_items) antes da tabela pai.
    # Não fazemos DROP INDEX explícito antes do DROP TABLE: no MySQL/InnoDB,
    # um índice que sustenta uma FK constraint (seja ela de saída — a própria
    # tabela referenciando outra — ou o índice exigido pela FK de outra tabela
    # apontando para esta) não pode ser removido isoladamente ("Cannot drop
    # index ...: needed in a foreign key constraint", erro 1553). DROP TABLE
    # remove a tabela inteira — dados, índices e constraints — de uma vez,
    # então o problema não existe nesse caminho.
    op.drop_table("checklist_item_state")
    op.drop_table("checklist_items")


def downgrade() -> None:
    # Recria o schema exatamente como definido em 86f95e525db1 (estado real
    # em produção/dev no momento desta migration), para permitir rollback
    # sem perda de estrutura — os dados de seed removidos não são restaurados
    # automaticamente (rodar `python -m scripts.seed_catalog` não repõe o
    # checklist, que deixou de existir no script após esta remoção).
    op.create_table(
        "checklist_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("control_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["control_id"], ["control_catalog.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_checklist_items_control_id"),
        "checklist_items",
        ["control_id"],
        unique=False,
    )

    op.create_table(
        "checklist_item_state",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("audit_control_id", sa.Integer(), nullable=False),
        sa.Column("checklist_item_id", sa.Integer(), nullable=False),
        sa.Column("done", sa.Boolean(), nullable=False),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["audit_control_id"], ["audit_controls.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["checklist_item_id"], ["checklist_items.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "audit_control_id",
            "checklist_item_id",
            name="uq_checklist_state_one_per_item_per_audit_control",
        ),
    )
    op.create_index(
        op.f("ix_checklist_item_state_audit_control_id"),
        "checklist_item_state",
        ["audit_control_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_checklist_item_state_checklist_item_id"),
        "checklist_item_state",
        ["checklist_item_id"],
        unique=False,
    )
