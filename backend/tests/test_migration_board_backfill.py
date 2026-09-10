"""
CA-02 e CA-03: o backfill da migration c8f1a3e57b90.

O defeito que este arquivo previne é o pior desta entrega inteira (R3):
um `upgrade` que roda sem erro, o CI fica verde, e o quadro de todas as
empresas de produção aparece VAZIO — porque `column_id` ficou NULL — ou
com os cards em ordem trocada, porque `position` foi gerada na ordem
errada. Nenhum teste de rota pega isso: as rotas passariam a responder
200 com uma lista vazia legítima.

`test_migrations_smoke.py` cobre a CADEIA (importável, revision bate com o
nome do arquivo, head único) e o job `migrations` do CI cobre o
`upgrade`/`downgrade` real contra MySQL 8.4. O que faltava era verificar
o CONTEÚDO do backfill, e é o que se faz aqui: montamos em SQLite o
schema exatamente como ele fica depois do DDL e antes do backfill,
populamos com dados de ordem conhecida e chamamos as três funções.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = (
    BACKEND_ROOT
    / "alembic"
    / "versions"
    / "c8f1a3e57b90_add_dashboard_columns_and_labels.py"
)

# Schema no estado "depois do DDL, antes do backfill": as colunas novas
# existem e `position` ainda é NULLABLE. Só as tabelas que os backfills
# tocam — montar o schema inteiro aqui seria duplicar os models.
SCHEMA_POS_DDL = [
    """
    CREATE TABLE dashboard_card_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(60) NOT NULL UNIQUE,
        color VARCHAR(20) NOT NULL DEFAULT '#788c5d',
        sort_order INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE dashboards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        title VARCHAR(200) NOT NULL
    )
    """,
    """
    CREATE TABLE dashboard_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(120) NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE dashboard_template_columns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_id INTEGER NOT NULL,
        name VARCHAR(160) NOT NULL,
        kind VARCHAR(20) NOT NULL DEFAULT 'COLUMN',
        position VARCHAR(64)
    )
    """,
    """
    CREATE TABLE dashboard_template_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_id INTEGER NOT NULL,
        title VARCHAR(160) NOT NULL,
        description TEXT,
        tag VARCHAR(60) NOT NULL DEFAULT '',
        category_id INTEGER,
        template_column_id INTEGER,
        sort_order INTEGER NOT NULL DEFAULT 0,
        position VARCHAR(64)
    )
    """,
    """
    CREATE TABLE dashboard_columns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dashboard_id INTEGER NOT NULL,
        name VARCHAR(160) NOT NULL,
        kind VARCHAR(20) NOT NULL DEFAULT 'COLUMN',
        position VARCHAR(64) NOT NULL,
        hidden BOOLEAN NOT NULL DEFAULT 0,
        wip_limit INTEGER,
        origin_template_column_id INTEGER,
        created_at DATETIME
    )
    """,
    """
    CREATE TABLE dashboard_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dashboard_id INTEGER NOT NULL,
        control_code VARCHAR(40),
        title VARCHAR(160) NOT NULL,
        tag VARCHAR(60) NOT NULL DEFAULT '',
        category_id INTEGER,
        origin_template_card_id INTEGER,
        hidden BOOLEAN NOT NULL DEFAULT 0,
        status VARCHAR(20) NOT NULL DEFAULT 'EM_ANALISE',
        column_id INTEGER,
        position VARCHAR(64),
        description TEXT,
        due_date DATETIME,
        sort_order INTEGER NOT NULL DEFAULT 0
    )
    """,
]


def _carregar_migration():
    """Importa o módulo da migration pelo caminho, como test_migrations_smoke."""
    spec = importlib.util.spec_from_file_location(MIGRATION_PATH.stem, MIGRATION_PATH)
    assert spec and spec.loader, f"não foi possível carregar {MIGRATION_PATH}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def conexao():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        for ddl in SCHEMA_POS_DDL:
            conn.execute(text(ddl))
        yield conn


@pytest.fixture
def migration():
    return _carregar_migration()


def _semear(conn) -> None:
    """
    Dois quadros, três categorias, cards com `sort_order` conhecido e um
    card sem categoria — a forma de dado que o backfill precisa tratar.
    """
    conn.execute(
        text(
            "INSERT INTO dashboard_card_categories (id, name, color, sort_order) "
            "VALUES (1, 'Compliance', '#96311D', 3), "
            "       (2, 'Financeiro', '#2C5A8C', 0), "
            "       (3, 'Vendas', '#8A6114', 2)"
        )
    )
    conn.execute(
        text(
            "INSERT INTO dashboards (id, company_id, title) "
            "VALUES (1, 10, 'Dash A'), (2, 20, 'Dash B')"
        )
    )
    conn.execute(text("INSERT INTO dashboard_templates (id, name) VALUES (1, 'T1')"))
    conn.execute(
        text(
            "INSERT INTO dashboard_template_cards "
            "(id, template_id, title, description, sort_order) "
            "VALUES (100, 1, 'Política de SI', 'Texto normativo do controle 5.1', 0), "
            "       (101, 1, 'Inventário', NULL, 1)"
        )
    )
    # Quadro 1: 4 cards, um deles sem categoria, sort_order fora de ordem
    # de id de propósito — é a ordem por sort_order que tem de sobreviver.
    conn.execute(
        text(
            "INSERT INTO dashboard_cards "
            "(id, dashboard_id, title, category_id, origin_template_card_id, sort_order) "
            "VALUES (1, 1, 'Card Financeiro B', 2, NULL, 3), "
            "       (2, 1, 'Card Compliance',   1, 100,  1), "
            "       (3, 1, 'Card sem categoria', NULL, NULL, 2), "
            "       (4, 1, 'Card Financeiro A', 2, 101,  0)"
        )
    )
    # Quadro 2: 1 card, categoria Vendas.
    conn.execute(
        text(
            "INSERT INTO dashboard_cards "
            "(id, dashboard_id, title, category_id, sort_order) "
            "VALUES (5, 2, 'Card Vendas', 3, 0)"
        )
    )


def test_nenhum_card_fica_sem_coluna(conexao, migration):
    """CA-02, primeira metade: quadro que tinha cards não pode ficar vazio."""
    _semear(conexao)

    migration.backfill_columns(conexao)

    orfaos = conexao.execute(
        text("SELECT COUNT(*) FROM dashboard_cards WHERE column_id IS NULL")
    ).scalar_one()
    assert orfaos == 0, "há card sem coluna depois do backfill — ver R3 do PRD"


def test_colunas_nascem_por_categoria_em_uso_e_na_ordem_da_categoria(
    conexao, migration
):
    _semear(conexao)

    migration.backfill_columns(conexao)

    nomes_quadro_1 = [
        linha[0]
        for linha in conexao.execute(
            text(
                "SELECT name FROM dashboard_columns "
                "WHERE dashboard_id = 1 ORDER BY position ASC"
            )
        ).fetchall()
    ]
    # Financeiro (sort_order 0) < Vendas (2) < Compliance (3); Vendas não
    # é usada no quadro 1, então não vira coluna. "Sem categoria" por último.
    assert nomes_quadro_1 == ["Financeiro", "Compliance", "Sem categoria"]

    nomes_quadro_2 = [
        linha[0]
        for linha in conexao.execute(
            text("SELECT name FROM dashboard_columns WHERE dashboard_id = 2")
        ).fetchall()
    ]
    assert nomes_quadro_2 == ["Vendas"]


def test_quadro_sem_cards_nao_ganha_colunas(conexao, migration):
    """Criar colunas vazias num quadro vazio seria inventar informação."""
    conexao.execute(
        text("INSERT INTO dashboards (id, company_id, title) VALUES (9, 90, 'Vazio')")
    )

    migration.backfill_columns(conexao)

    total = conexao.execute(
        text("SELECT COUNT(*) FROM dashboard_columns WHERE dashboard_id = 9")
    ).scalar_one()
    assert total == 0


def test_ordem_por_position_reproduz_a_ordem_por_sort_order(conexao, migration):
    """
    CA-02, segunda metade: a ordem que o usuário vê hoje (`sort_order ASC,
    id ASC`) tem de ser exatamente a ordem depois do upgrade
    (`position ASC`).
    """
    _semear(conexao)

    migration.backfill_positions(conexao)

    antes = [
        linha[0]
        for linha in conexao.execute(
            text(
                "SELECT id FROM dashboard_cards WHERE dashboard_id = 1 "
                "ORDER BY sort_order ASC, id ASC"
            )
        ).fetchall()
    ]
    depois = [
        linha[0]
        for linha in conexao.execute(
            text(
                "SELECT id FROM dashboard_cards WHERE dashboard_id = 1 "
                "ORDER BY position ASC"
            )
        ).fetchall()
    ]
    assert antes == [4, 2, 3, 1]
    assert depois == antes


def test_position_e_preenchida_em_todos_os_cards_e_cards_de_template(
    conexao, migration
):
    _semear(conexao)

    migration.backfill_positions(conexao)

    for tabela in ("dashboard_cards", "dashboard_template_cards"):
        nulos = conexao.execute(
            text(f"SELECT COUNT(*) FROM {tabela} WHERE position IS NULL")
        ).scalar_one()
        assert (
            nulos == 0
        ), f"{tabela} ficou com position NULL — o ALTER NOT NULL falharia"


def test_position_cabe_na_coluna_de_64_caracteres(conexao, migration):
    _semear(conexao)

    migration.backfill_positions(conexao)

    maior = conexao.execute(
        text("SELECT MAX(LENGTH(position)) FROM dashboard_cards")
    ).scalar_one()
    assert maior <= 64


def test_descricao_e_propagada_do_card_de_template_de_origem(conexao, migration):
    """
    CA-03: recupera o dado que `apply_template_to_company` descartava
    desde O.3.
    """
    _semear(conexao)

    migration.backfill_descriptions(conexao)

    descricao = conexao.execute(
        text("SELECT description FROM dashboard_cards WHERE id = 2")
    ).scalar_one()
    assert descricao == "Texto normativo do controle 5.1"


def test_descricao_nao_e_inventada_para_card_sem_origem(conexao, migration):
    _semear(conexao)

    migration.backfill_descriptions(conexao)

    # Card 4 tem origem (101), mas o template card 101 tem description NULL.
    assert (
        conexao.execute(
            text("SELECT description FROM dashboard_cards WHERE id = 4")
        ).scalar_one()
        is None
    )
    # Card 3 não tem origem nenhuma.
    assert (
        conexao.execute(
            text("SELECT description FROM dashboard_cards WHERE id = 3")
        ).scalar_one()
        is None
    )


def test_descricao_escrita_a_mao_nao_e_sobrescrita(conexao, migration):
    """Mesma regra de 'nunca sobrescrever card existente' que sustenta a
    idempotência de apply_template_to_company."""
    _semear(conexao)
    conexao.execute(
        text(
            "UPDATE dashboard_cards SET description = 'Escrita pelo auditor' WHERE id = 2"
        )
    )

    migration.backfill_descriptions(conexao)

    assert (
        conexao.execute(
            text("SELECT description FROM dashboard_cards WHERE id = 2")
        ).scalar_one()
        == "Escrita pelo auditor"
    )


def test_as_oito_etiquetas_aprovadas_estao_declaradas(migration):
    """
    CA-12/§2.1: `Concluído com evidência` NÃO pode entrar — ela criaria
    uma segunda fonte de verdade para "está conforme?", que é exatamente
    o que B-A23 proíbe. `Não Aplicável` também fica fora (é status, não
    etiqueta — decisão D-2).
    """
    nomes = {nome for nome, _cor, _ordem in migration.APPROVED_LABELS}

    assert len(migration.APPROVED_LABELS) == 8
    assert "Item Critico" in nomes
    assert "Concluído com evidência" not in nomes
    assert "Entregue - Inove Educação" not in nomes
    assert "Não Aplicável" not in nomes
