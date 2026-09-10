"""add_dashboard_columns_and_labels

Revision ID: c8f1a3e57b90
Revises: b7c02e91d4a5
Create Date: 2026-08-27 10:14:22.108431

Quadro Kanban de colunas e cards. Acrescenta ao domínio de card três
eixos que ele não tinha: ONDE o card está no quadro (`dashboard_columns`),
EM QUE ORDEM ele está dentro da coluna (`position`, índice fracionário) e
QUÃO CRÍTICO ele é (`dashboard_labels`, M:N).

Estratégia de dados — a regra que governa tudo aqui é **nenhum quadro
existente pode ficar vazio depois do upgrade**:

1. As 4 tabelas novas são criadas antes de qualquer ALTER, e nesta ordem:
   `dashboard_template_columns` antes de `dashboard_columns` (que a
   referencia) e `dashboard_labels` antes de `dashboard_card_labels`.

2. As 6 colunas novas entram com `position` **NULLABLE**. Não é
   preferência de estilo: `ADD COLUMN ... NOT NULL` sem default falha em
   tabela populada no MySQL. A coluna vira `NOT NULL` no passo 5, depois
   do backfill.

3. **Backfill de coluna** (`backfill_columns`): para cada quadro, uma
   `dashboard_columns` por `category_id` EFETIVAMENTE em uso naquele
   quadro, nomeada com o nome da categoria, na ordem de
   `dashboard_card_categories.sort_order`; cards sem categoria vão para
   um balde `Sem categoria`. Não criamos uma coluna por categoria
   existente — só pelas usadas: um quadro de 12 cards não deve nascer com
   40 colunas vazias.

4. **Backfill de `position`** (`backfill_positions`): chaves fracionárias
   geradas em Python na ordem `sort_order ASC, id ASC` — ou seja, a ordem
   que o usuário JÁ VÊ hoje é preservada exatamente. A migration importa
   `app.services.fractional_index`; o precedente de migration que importa
   do app é `a3d81f4c7b02`, e o módulo é puro (sem Session, sem I/O), o
   que torna o import barato e seguro.

5. **Backfill de `description`** (`backfill_descriptions`): copia a
   descrição do `DashboardTemplateCard` de origem para o card da empresa.
   Recupera o dado que `apply_template_to_company` vinha DESCARTANDO
   silenciosamente desde O.3 — 68 % dos cards do quadro real têm
   descrição, e ela é o texto normativo do controle.

6. **Seed de 8 etiquetas** (§2.1 do PRD). Ficam de fora, de propósito:
   `Concluído com evidência` (redundante com o status `CONFORME` — duas
   fontes de verdade para "está conforme?" é exatamente o que B-A23
   proíbe), `Entregue - Inove Educação` (específica de um cliente) e
   `Não Aplicável` (é status, não etiqueta — decisão D-2, registrada no
   backlog).

As três funções de backfill são de módulo, e não código inline dentro de
`upgrade()`, porque é o que permite testá-las sem MySQL — ver
`tests/test_migration_board_backfill.py`. `test_migrations_smoke.py` faz
só análise estática e nunca abre conexão; não teria como verificar
CA-02/CA-03.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.services.fractional_index import n_keys_between

# revision identifiers, used by Alembic.
revision: str = "c8f1a3e57b90"
down_revision: Union[str, None] = "b7c02e91d4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


#: As 8 etiquetas aprovadas em §2.1 do PRD: (nome, cor, ordem).
#: A cor é o hex do tema correspondente à cor do Trello de origem — o mapa
#: completo vive em `frontend/lib/board-labels.ts::TRELLO_COLOR_MAP`.
APPROVED_LABELS = [
    ("Item Critico", "#96311D", 0),
    ("Alta Criticidade", "#C2410C", 1),
    ("Média Criticidade", "#A16207", 2),
    ("Baixa Criticidade", "#2C5A8C", 3),
    ("Aguardando empresa", "#0E7490", 4),
    ("Check-list", "#6D28D9", 5),
    ("Inserir doc atualizado no final do projeto", "#854D0E", 6),
    ("Final do projeto", "#1E3A8A", 7),
]

UNCATEGORIZED_COLUMN_NAME = "Sem categoria"


# ------------------------------------------------------------ backfills


def backfill_columns(bind) -> None:
    """
    Cria uma `dashboard_columns` por categoria em uso em cada quadro e
    liga os cards a ela.

    Chamada por `upgrade()` e, diretamente, por
    `tests/test_migration_board_backfill.py` — é por isso que recebe o
    `bind` em vez de chamar `op.get_bind()` por dentro.
    """
    categorias = bind.execute(
        sa.text(
            "SELECT id, name FROM dashboard_card_categories "
            "ORDER BY sort_order ASC, name ASC"
        )
    ).fetchall()
    ordem_da_categoria = {linha[0]: indice for indice, linha in enumerate(categorias)}
    nome_da_categoria = {linha[0]: linha[1] for linha in categorias}

    quadros = bind.execute(
        sa.text("SELECT id FROM dashboards ORDER BY id ASC")
    ).fetchall()

    for (dashboard_id,) in quadros:
        usadas = [
            linha[0]
            for linha in bind.execute(
                sa.text(
                    "SELECT DISTINCT category_id FROM dashboard_cards "
                    "WHERE dashboard_id = :dashboard_id"
                ),
                {"dashboard_id": dashboard_id},
            ).fetchall()
        ]
        if not usadas:
            # Quadro sem card nenhum: nada a preservar, e criar colunas
            # vazias aqui seria inventar informação.
            continue

        com_categoria = sorted(
            [cid for cid in usadas if cid is not None],
            # Categoria referenciada por card mas ausente da tabela (FK
            # SET NULL de uma exclusão antiga) vai para o fim, nunca some.
            key=lambda cid: ordem_da_categoria.get(cid, 10**6),
        )
        alvos: list[tuple[int | None, str]] = [
            (cid, nome_da_categoria.get(cid, UNCATEGORIZED_COLUMN_NAME))
            for cid in com_categoria
        ]
        if any(cid is None for cid in usadas):
            alvos.append((None, UNCATEGORIZED_COLUMN_NAME))

        for (category_id, nome), position in zip(
            alvos, n_keys_between(None, None, len(alvos))
        ):
            bind.execute(
                sa.text(
                    "INSERT INTO dashboard_columns "
                    "(dashboard_id, name, kind, position, hidden) "
                    "VALUES (:dashboard_id, :nome, 'COLUMN', :position, 0)"
                ),
                {"dashboard_id": dashboard_id, "nome": nome, "position": position},
            )
            column_id = bind.execute(
                sa.text(
                    "SELECT id FROM dashboard_columns "
                    "WHERE dashboard_id = :dashboard_id AND position = :position"
                ),
                {"dashboard_id": dashboard_id, "position": position},
            ).scalar_one()

            if category_id is None:
                bind.execute(
                    sa.text(
                        "UPDATE dashboard_cards SET column_id = :column_id "
                        "WHERE dashboard_id = :dashboard_id AND category_id IS NULL"
                    ),
                    {"column_id": column_id, "dashboard_id": dashboard_id},
                )
            else:
                bind.execute(
                    sa.text(
                        "UPDATE dashboard_cards SET column_id = :column_id "
                        "WHERE dashboard_id = :dashboard_id "
                        "AND category_id = :category_id"
                    ),
                    {
                        "column_id": column_id,
                        "dashboard_id": dashboard_id,
                        "category_id": category_id,
                    },
                )


def backfill_positions(bind) -> None:
    """
    Gera `position` para cards de empresa e de template, na ordem
    `sort_order ASC, id ASC` — a mesma ordem que as duas telas usam hoje.

    `n_keys_between` divide o intervalo binariamente, então 213 cards
    saem com chaves de 3 caracteres, não de 213.
    """
    for tabela, escopo in (
        ("dashboard_cards", "dashboard_id"),
        ("dashboard_template_cards", "template_id"),
    ):
        grupos = bind.execute(
            sa.text(f"SELECT DISTINCT {escopo} FROM {tabela}")
        ).fetchall()
        for (grupo,) in grupos:
            ids = [
                linha[0]
                for linha in bind.execute(
                    sa.text(
                        f"SELECT id FROM {tabela} WHERE {escopo} = :grupo "
                        "ORDER BY sort_order ASC, id ASC"
                    ),
                    {"grupo": grupo},
                ).fetchall()
            ]
            if not ids:
                continue
            for registro_id, position in zip(ids, n_keys_between(None, None, len(ids))):
                bind.execute(
                    sa.text(f"UPDATE {tabela} SET position = :position WHERE id = :id"),
                    {"position": position, "id": registro_id},
                )


def backfill_descriptions(bind) -> None:
    """
    Recupera a descrição descartada por `apply_template_to_company` desde
    O.3, a partir do card de template de origem.

    Só preenche onde ainda está NULL: um card cuja descrição já tenha sido
    escrita à mão não pode ser sobrescrito pelo template — é a mesma regra
    de "nunca sobrescrever card existente" que sustenta a idempotência.
    """
    bind.execute(sa.text("""
            UPDATE dashboard_cards
               SET description = (
                   SELECT t.description
                     FROM dashboard_template_cards t
                    WHERE t.id = dashboard_cards.origin_template_card_id
               )
             WHERE origin_template_card_id IS NOT NULL
               AND description IS NULL
            """))


# ------------------------------------------------------------- upgrade


def upgrade() -> None:
    bind = op.get_bind()

    # --- 1. Tabelas novas (ordem de dependência) ---
    op.create_table(
        "dashboard_template_columns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("COLUMN", "SECTION", name="dashboard_column_kind"),
            nullable=False,
            server_default="COLUMN",
        ),
        sa.Column("position", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["template_id"], ["dashboard_templates.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "template_id", "name", name="uq_dashboard_template_column_name"
        ),
    )
    op.create_index(
        "ix_dashboard_template_columns_template_id",
        "dashboard_template_columns",
        ["template_id"],
    )

    op.create_table(
        "dashboard_columns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dashboard_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("COLUMN", "SECTION", name="dashboard_column_kind"),
            nullable=False,
            server_default="COLUMN",
        ),
        sa.Column("position", sa.String(length=64), nullable=False),
        sa.Column("hidden", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("wip_limit", sa.Integer(), nullable=True),
        sa.Column("origin_template_column_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["dashboard_id"], ["dashboards.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["origin_template_column_id"],
            ["dashboard_template_columns.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dashboard_id",
            "origin_template_column_id",
            name="uq_dashboard_column_origin_per_dashboard",
        ),
    )
    op.create_index(
        "ix_dashboard_columns_dashboard_id", "dashboard_columns", ["dashboard_id"]
    )
    op.create_index(
        "ix_dashboard_columns_origin_template_column_id",
        "dashboard_columns",
        ["origin_template_column_id"],
    )

    op.create_table(
        "dashboard_labels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column(
            "color", sa.String(length=20), nullable=False, server_default="#788c5d"
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_dashboard_labels_name"),
    )

    op.create_table(
        "dashboard_card_labels",
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("label_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["card_id"], ["dashboard_cards.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["label_id"], ["dashboard_labels.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("card_id", "label_id"),
    )

    # --- 2. Colunas novas (position entra NULLABLE, ver docstring) ---
    op.add_column(
        "dashboard_cards", sa.Column("column_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "dashboard_cards", sa.Column("position", sa.String(length=64), nullable=True)
    )
    op.add_column("dashboard_cards", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "dashboard_cards",
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_dashboard_cards_column_id",
        "dashboard_cards",
        "dashboard_columns",
        ["column_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_dashboard_cards_column_id", "dashboard_cards", ["column_id"])

    op.add_column(
        "dashboard_template_cards",
        sa.Column("template_column_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "dashboard_template_cards",
        sa.Column("position", sa.String(length=64), nullable=True),
    )
    op.create_foreign_key(
        "fk_dashboard_template_cards_template_column_id",
        "dashboard_template_cards",
        "dashboard_template_columns",
        ["template_column_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_dashboard_template_cards_template_column_id",
        "dashboard_template_cards",
        ["template_column_id"],
    )

    # --- 3, 4 e 5. Backfills ---
    backfill_columns(bind)
    backfill_positions(bind)
    backfill_descriptions(bind)

    # --- 6. Só agora `position` pode ser NOT NULL ---
    op.alter_column(
        "dashboard_cards",
        "position",
        existing_type=sa.String(length=64),
        nullable=False,
    )
    op.alter_column(
        "dashboard_template_cards",
        "position",
        existing_type=sa.String(length=64),
        nullable=False,
    )

    # --- 7. Vocabulário de etiquetas ---
    labels_table = sa.table(
        "dashboard_labels",
        sa.column("name", sa.String),
        sa.column("color", sa.String),
        sa.column("sort_order", sa.Integer),
    )
    op.bulk_insert(
        labels_table,
        [
            {"name": name, "color": color, "sort_order": sort_order}
            for name, color, sort_order in APPROVED_LABELS
        ],
    )

    # --- 8. Índices compostos que cobrem o ORDER BY do quadro (CA-13) ---
    op.create_index(
        "ix_dashboard_columns_board_position",
        "dashboard_columns",
        ["dashboard_id", "position"],
    )
    op.create_index(
        "ix_dashboard_cards_column_position",
        "dashboard_cards",
        ["column_id", "position"],
    )


# ----------------------------------------------------------- downgrade


def downgrade() -> None:
    """
    A ordem aqui não é estilística — é a lição de B-A30, que só apareceu
    na PRIMEIRA execução real do job `migrations` contra MySQL 8.4:

        (1553, "Cannot drop index '...': needed in a foreign key constraint")

    No MySQL, uma FOREIGN KEY exige um índice, e o servidor RECUSA remover
    esse índice enquanto a constraint existir. A ordem correta é sempre
    **constraint → índice → coluna**, e as tabelas caem na ordem inversa
    da criação.

    Nada de `pass` (B13): o job `migrations` do CI reverte até `base` e
    reaplica a cada PR — um downgrade incompleto reprova o build.
    """
    # --- dashboard_cards: constraint, depois índices, depois colunas ---
    op.drop_constraint(
        "fk_dashboard_cards_column_id", "dashboard_cards", type_="foreignkey"
    )
    op.drop_index("ix_dashboard_cards_column_position", table_name="dashboard_cards")
    op.drop_index("ix_dashboard_cards_column_id", table_name="dashboard_cards")
    op.drop_column("dashboard_cards", "due_date")
    op.drop_column("dashboard_cards", "description")
    op.drop_column("dashboard_cards", "position")
    op.drop_column("dashboard_cards", "column_id")

    # --- dashboard_template_cards: mesma ordem ---
    op.drop_constraint(
        "fk_dashboard_template_cards_template_column_id",
        "dashboard_template_cards",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_dashboard_template_cards_template_column_id",
        table_name="dashboard_template_cards",
    )
    op.drop_column("dashboard_template_cards", "position")
    op.drop_column("dashboard_template_cards", "template_column_id")

    # --- Tabelas, na ordem inversa da criação ---
    #
    # Sem `drop_index` aqui, de propósito. A regra "constraint → índice →
    # coluna" acima vale para tabela que SOBREVIVE ao downgrade; para tabela
    # que vai inteira embora, `DROP TABLE` já leva junto os índices dela — e
    # tentar removê-los antes reencena o próprio B-A30 pelo outro lado:
    # `dashboard_columns` tem FK para `dashboards` e para
    # `dashboard_template_columns`, e o MySQL recusa remover o índice que
    # sustenta uma FK ainda viva:
    #
    #     (1553, "Cannot drop index
    #      'ix_dashboard_columns_origin_template_column_id':
    #      needed in a foreign key constraint")
    #
    # A ordem entre as tabelas continua importando: a que referencia cai
    # antes da referenciada.
    op.drop_table("dashboard_card_labels")
    op.drop_table("dashboard_labels")
    op.drop_table("dashboard_columns")
    op.drop_table("dashboard_template_columns")
