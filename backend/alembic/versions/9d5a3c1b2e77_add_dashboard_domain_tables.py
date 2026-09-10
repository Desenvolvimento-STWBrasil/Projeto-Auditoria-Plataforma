"""add dashboard domain tables

Revision ID: 9d5a3c1b2e77
Revises: 447a4e1de59d
Create Date: 2026-05-22 12:20:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9d5a3c1b2e77"
down_revision: Union[str, None] = "447a4e1de59d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("email", sa.String(length=160), nullable=False),
        sa.Column("phone", sa.String(length=160), nullable=True),
        sa.Column("principal_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["principal_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_companies_name"),
        sa.UniqueConstraint("email", name="uq_companies_email"),
        sa.UniqueConstraint("principal_user_id", name="uq_companies_principal_user_id"),
    )
    op.create_index("ix_companies_name", "companies", ["name"], unique=False)
    op.create_index("ix_companies_email", "companies", ["email"], unique=False)
    op.create_index("ix_companies_principal_user_id", "companies", ["principal_user_id"], unique=False)

    op.create_table(
        "dashboard_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_dashboard_templates_name"),
    )
    op.create_index("ix_dashboard_templates_is_default", "dashboard_templates", ["is_default"], unique=False)

    op.create_table(
        "dashboard_template_cards",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("tag", sa.String(length=60), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["template_id"], ["dashboard_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dashboard_template_cards_template_id", "dashboard_template_cards", ["template_id"], unique=False)
    op.create_index("ix_dashboard_template_cards_tag", "dashboard_template_cards", ["tag"], unique=False)

    op.create_table(
        "dashboards",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", name="uq_dashboards_company_id"),
    )
    op.create_index("ix_dashboards_company_id", "dashboards", ["company_id"], unique=False)

    op.create_table(
        "dashboard_cards",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dashboard_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("tag", sa.String(length=60), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dashboard_id"], ["dashboards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dashboard_cards_dashboard_id", "dashboard_cards", ["dashboard_id"], unique=False)
    op.create_index("ix_dashboard_cards_tag", "dashboard_cards", ["tag"], unique=False)

    op.create_table(
        "dashboard_card_notes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["dashboard_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dashboard_card_notes_card_id", "dashboard_card_notes", ["card_id"], unique=False)
    op.create_index("ix_dashboard_card_notes_created_by_user_id", "dashboard_card_notes", ["created_by_user_id"], unique=False)

    op.create_table(
        "dashboard_card_checklist_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("done", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["dashboard_cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dashboard_card_checklist_items_card_id", "dashboard_card_checklist_items", ["card_id"], unique=False)

    op.create_table(
        "dashboard_card_history_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["dashboard_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dashboard_card_history_entries_card_id", "dashboard_card_history_entries", ["card_id"], unique=False)
    op.create_index("ix_dashboard_card_history_entries_actor_user_id", "dashboard_card_history_entries", ["actor_user_id"], unique=False)

    op.create_table(
        "dashboard_card_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("author_user_id", sa.Integer(), nullable=False),
        sa.Column("message_type", sa.Enum("QUESTION", "ANSWER", name="dashboard_message_type"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["dashboard_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dashboard_card_messages_card_id", "dashboard_card_messages", ["card_id"], unique=False)
    op.create_index("ix_dashboard_card_messages_author_user_id", "dashboard_card_messages", ["author_user_id"], unique=False)
    op.create_index("ix_dashboard_card_messages_message_type", "dashboard_card_messages", ["message_type"], unique=False)


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
    op.drop_table("dashboard_card_messages")

    op.drop_table("dashboard_card_history_entries")

    op.drop_table("dashboard_card_checklist_items")

    op.drop_table("dashboard_card_notes")

    op.drop_table("dashboard_cards")

    op.drop_table("dashboards")

    op.drop_table("dashboard_template_cards")

    op.drop_table("dashboard_templates")

    op.drop_table("companies")
