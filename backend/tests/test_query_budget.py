"""
M-25: o custo em queries de uma rota é medido por teste.

A suíte tinha 250 testes e nenhum media **custo**. Um endpoint que responde
certo em 3 queries e um que responde certo em 300 eram indistinguíveis para
ela — e foi assim que B-M26 (7 queries por empresa na listagem) passou
despercebido, mesmo com `test_admin_companies.py` cobrindo a rota.

O padrão que produz esse defeito é reconhecível: **uma função de detalhe
reusada numa listagem**. `_load_admin_data` está correta para UMA empresa.

Parametrizar por DUAS quantidades é o detalhe que faz o teste funcionar: um
teto absoluto medido com uma quantidade só pode ser satisfeito por acaso;
com 5 e 20 sob o mesmo teto, só passa se o custo for de fato constante.
"""

from __future__ import annotations

import pytest
from sqlalchemy import event, select

from app.core.security import hash_password
from app.models.company_dashboard import Company, Dashboard, DashboardCard
from app.models.company_message import CompanyMessage
from app.models.user import User
from tests.conftest import engine


class ContadorDeQueries:
    """Conta execuções de cursor no engine de teste."""

    def __init__(self) -> None:
        self.count = 0
        self.statements: list[str] = []

    def __enter__(self) -> ContadorDeQueries:
        event.listen(engine, "before_cursor_execute", self._on)
        return self

    def __exit__(self, *exc) -> None:
        event.remove(engine, "before_cursor_execute", self._on)

    def _on(self, conn, cursor, statement, params, context, executemany) -> None:
        self.count += 1
        self.statements.append(statement.split("\n")[0][:90])


def _semear_empresas(db, quantidade: int, *, sub_users: int = 1) -> None:
    for i in range(quantidade):
        principal = User(
            full_name=f"Cliente {i}",
            email=f"cliente{i}@test.com",
            password_hash=hash_password("Cliente123!"),
            role="user",
        )
        db.add(principal)
        db.flush()

        for j in range(sub_users):
            db.add(
                User(
                    full_name=f"Sub {i}-{j}",
                    email=f"sub{i}-{j}@test.com",
                    password_hash=hash_password("SubUser123!"),
                    role="sub-user",
                    parent_user_id=principal.id,
                )
            )

        company = Company(
            name=f"Empresa {i}",
            email=f"empresa{i}@test.com",
            principal_user_id=principal.id,
        )
        db.add(company)
        db.flush()

        dashboard = Dashboard(company_id=company.id, title=f"Dash {i}")
        db.add(dashboard)
        db.flush()

        db.add(DashboardCard(dashboard_id=dashboard.id, title=f"Card {i}", tag="x"))
        db.add(
            CompanyMessage(
                company_id=company.id,
                author_user_id=principal.id,
                content=f"mensagem da empresa {i}",
            )
        )
    db.commit()


# ------------------------------------------------------- GET /admin/companies


@pytest.mark.parametrize("quantidade", [5, 20])
def test_listagem_de_empresas_tem_custo_constante(client, db, admin_token, quantidade):
    _semear_empresas(db, quantidade)

    with ContadorDeQueries() as contador:
        resposta = client.get(
            f"/api/v1/admin/companies?limit={quantidade}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resposta.status_code == 200
    assert len(resposta.json()["items"]) == quantidade
    assert contador.count <= 15, (
        f"{contador.count} queries para {quantidade} empresas — o N+1 de "
        f"B-M26 voltou. O custo tem de ser constante, não linear.\n"
        + "\n".join(f"  {s}" for s in contador.statements[:25])
    )


def test_listagem_devolve_os_mesmos_numeros_do_detalhe(client, db, admin_token):
    """A otimização não pode mudar o resultado."""
    _semear_empresas(db, 3, sub_users=2)

    lista = client.get(
        "/api/v1/admin/companies",
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()["items"]

    assert lista

    for item in lista:
        detalhe = client.get(
            f"/api/v1/admin/companies/{item['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        ).json()

        assert item["principal_full_name"] == detalhe["principal_full_name"]
        assert item["principal_email"] == detalhe["principal_email"]
        assert item["sub_user_count"] == detalhe["sub_user_count"]
        assert item["sub_user_emails"] == detalhe["sub_user_emails"]
        assert item["name"] == detalhe["name"]
        assert item["phone"] == detalhe["phone"]


def test_busca_na_listagem_continua_funcionando(client, db, admin_token):
    _semear_empresas(db, 5)

    resposta = client.get(
        "/api/v1/admin/companies?search=Empresa 3",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["total"] == 1
    assert corpo["items"][0]["name"] == "Empresa 3"


def test_paginacao_na_listagem_continua_funcionando(client, db, admin_token):
    _semear_empresas(db, 5)

    pagina = client.get(
        "/api/v1/admin/companies?skip=2&limit=2",
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()

    assert pagina["total"] == 5
    assert pagina["skip"] == 2
    assert pagina["limit"] == 2
    assert len(pagina["items"]) == 2


def test_listagem_vazia_nao_estoura(client, admin_token):
    resposta = client.get(
        "/api/v1/admin/companies",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resposta.status_code == 200
    assert resposta.json()["items"] == []


# ------------------------------------- outras rotas de listagem sob orçamento


def test_cards_por_empresa_tem_custo_constante(client, db, admin_token, company):
    """Já usa `selectinload`; o orçamento existe para não regredir."""
    dashboard = Dashboard(company_id=company.id, title="Dash")
    db.add(dashboard)
    db.flush()
    for i in range(20):
        db.add(DashboardCard(dashboard_id=dashboard.id, title=f"Card {i}", tag="x"))
    db.commit()

    with ContadorDeQueries() as contador:
        resposta = client.get(
            f"/api/v1/dashboard/companies/{company.id}/cards",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resposta.status_code == 200
    assert len(resposta.json()) == 20
    assert contador.count <= 12, (
        f"{contador.count} queries para 20 cards — N+1 em "
        "list_cards_by_company (o `selectinload` foi removido?).\n"
        "O teto subiu de 8 para 12 quando a rota passou a carregar "
        "`labels` (M:N) e `column` (usada por `_card_is_outdated`): cada "
        "`selectinload` custa UMA query fixa a mais, não uma por card — "
        "é justamente essa diferença que o teto protege."
    )


def test_listagem_de_templates_tem_custo_constante(client, db, admin_token):
    """B-M24 foi corrigido no BLOCO P por leitura; aqui vira barreira."""
    from app.models.company_dashboard import DashboardTemplate, DashboardTemplateCard

    for i in range(10):
        template = DashboardTemplate(name=f"Template {i}", description=None)
        db.add(template)
        db.flush()
        for j in range(3):
            db.add(
                DashboardTemplateCard(
                    template_id=template.id, title=f"T{i} C{j}", tag="x", sort_order=j
                )
            )
    db.commit()

    with ContadorDeQueries() as contador:
        resposta = client.get(
            "/api/v1/admin/templates",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resposta.status_code == 200
    assert len(resposta.json()) == 10
    assert (
        contador.count <= 5
    ), f"{contador.count} queries para 10 templates — o N+1 de B-M24 voltou"


# ------------------------------------------- GET .../board (quadro Kanban)


def _semear_quadro(db, company, colunas: int, cards_por_coluna: int = 5) -> None:
    """
    Um quadro com `colunas` colunas e `colunas * cards_por_coluna` cards.

    Semeado por SQL do ORM direto (e não pela API) de propósito: o que se
    mede aqui é o custo da LEITURA, e criar via API poluiria o contador
    com as queries de escrita.
    """
    from app.models.dashboard_board import DashboardColumn
    from app.services.fractional_index import n_keys_between

    dashboard = Dashboard(company_id=company.id, title="Dash Quadro")
    db.add(dashboard)
    db.flush()

    posicoes_coluna = n_keys_between(None, None, colunas)
    for indice, posicao in enumerate(posicoes_coluna):
        coluna = DashboardColumn(
            dashboard_id=dashboard.id, name=f"Coluna {indice}", position=posicao
        )
        db.add(coluna)
        db.flush()
        for card_posicao in n_keys_between(None, None, cards_por_coluna):
            db.add(
                DashboardCard(
                    dashboard_id=dashboard.id,
                    title=f"Card {indice}-{card_posicao}",
                    tag="x",
                    column_id=coluna.id,
                    position=card_posicao,
                )
            )
    db.commit()


@pytest.mark.parametrize("colunas", [5, 20])
def test_board_tem_custo_constante_em_queries(
    client, db, admin_token, company, colunas
):
    """
    CA-13. Parametrizado com DUAS quantidades sob o MESMO teto, pela razão
    explicada na docstring do módulo: um teto absoluto medido com uma
    quantidade só pode ser satisfeito por acaso; com 5 e 20 colunas sob o
    mesmo teto, só passa se o custo for de fato constante.

    O defeito que isto previne é concreto e fácil de introduzir: uma
    query de cards POR COLUNA dentro do laço de montagem do quadro. Com 5
    colunas ninguém nota; com as 25 do quadro real, a tela trava.
    """
    _semear_quadro(db, company, colunas)

    with ContadorDeQueries() as contador:
        resposta = client.get(
            f"/api/v1/dashboard/companies/{company.id}/board",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo["columns"]) == colunas
    assert sum(len(c["cards"]) for c in corpo["columns"]) == colunas * 5

    assert contador.count <= 15, (
        f"{contador.count} queries para {colunas} colunas — o custo do quadro "
        f"virou linear no número de colunas (CA-13).\n"
        + "\n".join(f"  {s}" for s in contador.statements[:25])
    )


def test_mover_card_nao_reescreve_a_coluna_inteira(client, db, admin_token, company):
    """
    CA-06 medido do lado do orçamento: o índice fracionário existe para
    que um arrasto custe UM UPDATE. Com `sort_order: Integer` seriam até
    100.
    """
    from app.models.dashboard_board import DashboardColumn

    _semear_quadro(db, company, colunas=1, cards_por_coluna=100)
    coluna = db.scalars(select(DashboardColumn)).first()
    cards = (
        db.query(DashboardCard)
        .filter(DashboardCard.column_id == coluna.id)
        .order_by(DashboardCard.position.asc())
        .all()
    )

    with ContadorDeQueries() as contador:
        resposta = client.patch(
            f"/api/v1/dashboard/cards/{cards[0].id}/move",
            json={
                "column_id": coluna.id,
                "prev_card_id": cards[-1].id,
                "next_card_id": None,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resposta.status_code == 200
    updates = [s for s in contador.statements if s.strip().upper().startswith("UPDATE")]
    assert len(updates) == 1, f"{len(updates)} UPDATEs para mover 1 card entre 100"
