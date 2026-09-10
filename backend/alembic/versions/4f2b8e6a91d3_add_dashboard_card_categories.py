"""add_dashboard_card_categories

Revision ID: 4f2b8e6a91d3
Revises: 7e3f9c2b5a1d
Create Date: 2026-08-19 17:30:13.459224

Fase O.3 do plano de implementação ("Planta do Dashboard"): substitui a
tag de texto livre (`dashboard_cards.tag` / `dashboard_template_cards.tag`)
por uma entidade de categoria (`dashboard_card_categories`), no mesmo
padrão catálogo -> instância que `ControlCatalog`/`AuditControl` já usam
no módulo de Auditorias. Adiciona também rastreio de origem
(`dashboard_cards.origin_template_card_id`, liga o card à definição de
template da qual nasceu) e ocultação sem apagar
(`dashboard_cards.hidden`).

Estratégia de migração de dados, para não perder nem inventar
informação:
1. Cria `dashboard_card_categories` e semeia as 4 categorias canônicas
   do documento de origem (Financeiro/Operacional/Vendas/Compliance).
2. Para cada valor DISTINTO de `tag` já presente em `dashboard_cards`
   OU `dashboard_template_cards` que não bata (case-insensitive) com
   nenhuma das 4 categorias canônicas, cria uma categoria própria com
   esse texto como nome -- preserva os dados exatamente como estavam,
   sem tentar adivinhar agrupamentos. Duplicatas reais (ex.: "Financeiro"
   e "financeiro" coexistindo) viram categorias distintas e óbvias,
   consolidadas manualmente pelo admin via o CRUD de categorias
   entregue em O.4 -- mesma decisão consciente já tomada em E.12.
3. Preenche `category_id` em ambas as tabelas por igualdade
   case-insensitive com `dashboard_card_categories.name`.
4. `tag` NÃO é removida nesta migration -- vira um campo histórico,
   mantido até uma limpeza futura confirmada em produção (mesmo padrão
   conservador de E.10, que só removeu um subsistema inteiro depois de
   confirmar ausência de uso real).
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "4f2b8e6a91d3"
down_revision: Union[str, None] = "7e3f9c2b5a1d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CANONICAL_CATEGORIES = [
    ("Financeiro", "#2C5A8C", 0),
    ("Operacional", "#1F6B4C", 1),
    ("Vendas", "#8A6114", 2),
    ("Compliance", "#96311D", 3),
]


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "dashboard_card_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column(
            "color", sa.String(length=20), nullable=False, server_default="#788c5d"
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_dashboard_card_categories_name"),
    )

    categories_table = sa.table(
        "dashboard_card_categories",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("color", sa.String),
        sa.column("sort_order", sa.Integer),
    )

    for name, color, order in CANONICAL_CATEGORIES:
        bind.execute(
            categories_table.insert().values(name=name, color=color, sort_order=order)
        )

    op.add_column(
        "dashboard_template_cards",
        sa.Column("category_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "dashboard_template_cards",
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_dashboard_template_cards_category_id",
        "dashboard_template_cards",
        "dashboard_card_categories",
        ["category_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_dashboard_template_cards_category_id",
        "dashboard_template_cards",
        ["category_id"],
    )

    op.add_column(
        "dashboard_cards",
        sa.Column("category_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "dashboard_cards",
        sa.Column("origin_template_card_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "dashboard_cards",
        sa.Column("hidden", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )
    op.create_foreign_key(
        "fk_dashboard_cards_category_id",
        "dashboard_cards",
        "dashboard_card_categories",
        ["category_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_dashboard_cards_origin_template_card_id",
        "dashboard_cards",
        "dashboard_template_cards",
        ["origin_template_card_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_dashboard_cards_category_id", "dashboard_cards", ["category_id"]
    )
    op.create_index(
        "ix_dashboard_cards_origin_template_card_id",
        "dashboard_cards",
        ["origin_template_card_id"],
    )

    # --- Backfill: 1 categoria por valor distinto de `tag` ainda não
    # coberto pelas 4 canônicas (comparação case-insensitive) ---
    distinct_tags: set[str] = set()
    for table_name in ("dashboard_cards", "dashboard_template_cards"):
        rows = bind.execute(
            sa.text(
                f"SELECT DISTINCT tag FROM {table_name} "
                "WHERE tag IS NOT NULL AND tag <> ''"
            )
        ).fetchall()
        distinct_tags.update(row[0] for row in rows)

    canonical_names_lower = {name.lower() for name, _, _ in CANONICAL_CATEGORIES}
    next_sort_order = len(CANONICAL_CATEGORIES)
    for tag_value in sorted(distinct_tags):
        if tag_value.lower() in canonical_names_lower:
            continue
        bind.execute(
            categories_table.insert().values(
                name=tag_value, color="#788c5d", sort_order=next_sort_order
            )
        )
        next_sort_order += 1

    # --- Backfill de category_id por igualdade case-insensitive com tag ---
    for table_name in ("dashboard_cards", "dashboard_template_cards"):
        bind.execute(sa.text(f"""
                UPDATE {table_name}
                SET category_id = (
                    SELECT id FROM dashboard_card_categories
                    WHERE LOWER(dashboard_card_categories.name) = LOWER({table_name}.tag)
                )
                WHERE tag IS NOT NULL AND tag <> ''
                """))


def downgrade() -> None:
    """
    A ordem aqui não é estilística: no MySQL, uma FOREIGN KEY precisa de
    um índice, e o servidor **recusa** removê-lo enquanto a constraint
    existir:

        (1553, "Cannot drop index
                'ix_dashboard_cards_origin_template_card_id':
                needed in a foreign key constraint")

    A ordem correta é sempre **constraint → índice → coluna**.

    Isto passou despercebido por dois meses porque a suíte usa
    `Base.metadata.create_all` e o SQLite não aplica a mesma restrição —
    nenhum teste local exercitava `alembic downgrade`. O defeito só
    apareceu na PRIMEIRA execução real do job `migrations` do CI
    (2026-08-26), que roda `downgrade base` contra um MySQL 8.4 de
    verdade. Ver Sprint A5 em docs/roadmap.md.
    """
    # --- dashboard_cards: constraints primeiro ---
    op.drop_constraint(
        "fk_dashboard_cards_origin_template_card_id",
        "dashboard_cards",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_dashboard_cards_category_id", "dashboard_cards", type_="foreignkey"
    )
    op.drop_index(
        "ix_dashboard_cards_origin_template_card_id", table_name="dashboard_cards"
    )
    op.drop_index("ix_dashboard_cards_category_id", table_name="dashboard_cards")
    op.drop_column("dashboard_cards", "hidden")
    op.drop_column("dashboard_cards", "origin_template_card_id")
    op.drop_column("dashboard_cards", "category_id")

    # --- dashboard_template_cards: mesma ordem ---
    op.drop_constraint(
        "fk_dashboard_template_cards_category_id",
        "dashboard_template_cards",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_dashboard_template_cards_category_id", table_name="dashboard_template_cards"
    )
    op.drop_column("dashboard_template_cards", "description")
    op.drop_column("dashboard_template_cards", "category_id")

    op.drop_table("dashboard_card_categories")
