"""
CA-05 a CA-08: o quadro, o arrasto e as duas regras que impedem o arrasto
de corromper dados.

Duas classes de defeito justificam este arquivo, e nenhuma delas produz
erro visível na hora:

1. **Chave fora de ordem.** O servidor calcula a `position` a partir das
   âncoras que o cliente manda. Âncoras de outra coluna produziriam uma
   chave "válida" que coloca o card no lugar errado — e a rota
   responderia 200. Por isso `AnchorMismatchError` → 422.

2. **Escrita em cascata.** O índice fracionário existe para que um
   arrasto custe UM UPDATE. Uma regressão que volte a reindexar a coluna
   inteira continua passando em todo teste funcional; só um contador de
   queries a pega (CA-06).

O terceiro eixo é isolamento entre empresas: mover um card para a coluna
de outra empresa responde **404**, não 403 e muito menos 200 (B-B23).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.models.company_dashboard import Company, Dashboard, DashboardCard
from app.models.dashboard_board import DashboardColumn
from app.models.user import User
from app.services.fractional_index import n_keys_between
from tests.test_query_budget import ContadorDeQueries


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _criar_cards(db, dashboard, coluna, titulos: list[str]) -> list[DashboardCard]:
    cards = [
        DashboardCard(
            dashboard_id=dashboard.id,
            title=titulo,
            tag="t",
            column_id=coluna.id if coluna is not None else None,
            position=position,
        )
        for titulo, position in zip(titulos, n_keys_between(None, None, len(titulos)))
    ]
    db.add_all(cards)
    db.commit()
    for card in cards:
        db.refresh(card)
    return cards


def _outra_empresa(db) -> tuple[Company, Dashboard, DashboardColumn]:
    """Empresa completamente separada, para os testes de isolamento."""
    outro_usuario = User(
        full_name="Outro Cliente",
        email="outro@test.com",
        password_hash=hash_password("Outro123!"),
        role="user",
    )
    db.add(outro_usuario)
    db.flush()

    outra = Company(
        name="Outra Empresa",
        email="outra@test.com",
        principal_user_id=outro_usuario.id,
    )
    db.add(outra)
    db.flush()

    outro_dashboard = Dashboard(company_id=outra.id, title="Dash Outra")
    db.add(outro_dashboard)
    db.flush()

    outra_coluna = DashboardColumn(
        dashboard_id=outro_dashboard.id, name="Coluna Alheia", position="a0"
    )
    db.add(outra_coluna)
    db.commit()
    db.refresh(outra_coluna)
    return outra, outro_dashboard, outra_coluna


# ------------------------------------------------------- CA-05: leitura


def test_board_devolve_colunas_e_cards_ordenados_por_position(
    client: TestClient, db, admin_token: str, company, dashboard, board_com_3_colunas
):
    a_fazer, _secao, concluido = board_com_3_colunas
    _criar_cards(db, dashboard, a_fazer, ["Card 1", "Card 2", "Card 3"])
    _criar_cards(db, dashboard, concluido, ["Card 4"])

    resposta = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board",
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["company_id"] == company.id
    assert [c["name"] for c in corpo["columns"]] == [
        "A fazer",
        "ISO 27001:2022 >>",
        "Concluído",
    ]
    assert [c["title"] for c in corpo["columns"][0]["cards"]] == [
        "Card 1",
        "Card 2",
        "Card 3",
    ]
    assert corpo["columns"][0]["card_count"] == 3
    assert corpo["columns"][1]["cards"] == []
    assert [c["title"] for c in corpo["columns"][2]["cards"]] == ["Card 4"]
    assert corpo["uncolumned"] == []


def test_board_embute_as_etiquetas_do_card(
    client: TestClient, db, admin_token: str, company, dashboard_card, etiquetas
):
    dashboard_card.labels = [etiquetas[0], etiquetas[2]]
    db.commit()

    corpo = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board",
        headers=_headers(admin_token),
    ).json()

    card = corpo["columns"][0]["cards"][0]
    assert [etiqueta["name"] for etiqueta in card["labels"]] == [
        "Item Critico",
        "Baixa Criticidade",
    ]
    assert card["labels"][0]["color"] == "#96311D"


def test_card_sem_coluna_cai_no_balde_uncolumned(
    client: TestClient, db, admin_token: str, company, dashboard, dashboard_column
):
    _criar_cards(db, dashboard, None, ["Órfão"])

    corpo = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board",
        headers=_headers(admin_token),
    ).json()

    assert [c["title"] for c in corpo["uncolumned"]] == ["Órfão"]


def test_coluna_arquivada_so_aparece_com_include_hidden(
    client: TestClient, db, admin_token: str, company, dashboard_column
):
    dashboard_column.hidden = True
    db.commit()

    sem_flag = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board",
        headers=_headers(admin_token),
    ).json()
    assert sem_flag["columns"] == []

    com_flag = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board?include_hidden=true",
        headers=_headers(admin_token),
    ).json()
    assert [c["name"] for c in com_flag["columns"]] == ["Controles Organizacionais"]


def test_busca_no_board_filtra_por_titulo_e_codigo(
    client: TestClient, db, admin_token: str, company, dashboard, dashboard_column
):
    _criar_cards(db, dashboard, dashboard_column, ["Backup", "Gestão de Acesso"])

    corpo = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board?search=backup",
        headers=_headers(admin_token),
    ).json()

    assert [c["title"] for c in corpo["columns"][0]["cards"]] == ["Backup"]


def test_cliente_le_o_quadro_da_propria_empresa(
    client: TestClient, user_token: str, company, dashboard_column
):
    """U6/CA-11: leitura é permitida a user e sub-user."""
    resposta = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board",
        headers=_headers(user_token),
    )
    assert resposta.status_code == 200


def test_empresa_sem_dashboard_devolve_quadro_vazio(
    client: TestClient, db, admin_token: str, company
):
    """404 aqui quebraria a tela do cliente em vez de mostrar 'nada ainda'."""
    resposta = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board",
        headers=_headers(admin_token),
    )
    assert resposta.status_code == 200
    assert resposta.json()["columns"] == []


# ------------------------------------------------- CA-06: um UPDATE só


def test_mover_card_executa_exatamente_um_update(
    client: TestClient, db, admin_token: str, dashboard, dashboard_column
):
    """
    CA-06. É o teste que justifica o índice fracionário existir: com
    `sort_order: Integer`, mover o primeiro card para o fim reescreveria
    todos os outros.
    """
    cards = _criar_cards(
        db, dashboard, dashboard_column, [f"Card {i}" for i in range(10)]
    )
    primeiro, ultimo = cards[0], cards[-1]

    with ContadorDeQueries() as contador:
        resposta = client.patch(
            f"/api/v1/dashboard/cards/{primeiro.id}/move",
            json={
                "column_id": dashboard_column.id,
                "prev_card_id": ultimo.id,
                "next_card_id": None,
            },
            headers=_headers(admin_token),
        )

    assert resposta.status_code == 200
    updates = [s for s in contador.statements if s.strip().upper().startswith("UPDATE")]
    assert len(updates) == 1, (
        f"{len(updates)} UPDATEs para mover 1 card — a reindexação em cascata "
        f"voltou:\n" + "\n".join(f"  {s}" for s in updates)
    )

    db.expire_all()
    ordem = [
        c.title
        for c in db.query(DashboardCard)
        .filter(DashboardCard.column_id == dashboard_column.id)
        .order_by(DashboardCard.position.asc())
        .all()
    ]
    assert ordem[-1] == "Card 0"


def test_mover_card_entre_colunas_atualiza_column_id(
    client: TestClient, db, admin_token: str, dashboard, board_com_3_colunas
):
    a_fazer, _secao, concluido = board_com_3_colunas
    card = _criar_cards(db, dashboard, a_fazer, ["Card"])[0]

    resposta = client.patch(
        f"/api/v1/dashboard/cards/{card.id}/move",
        json={"column_id": concluido.id, "prev_card_id": None, "next_card_id": None},
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 200
    assert resposta.json()["column_id"] == concluido.id


# ------------------------------------------- CA-07: isolamento (404)


def test_mover_card_para_coluna_de_outra_empresa_devolve_404(
    client: TestClient, db, admin_token: str, dashboard_card
):
    """
    CA-07. 404, não 403: distinguir "coluna não existe" de "coluna existe
    e não é sua" permitiria enumerar as colunas da plataforma (B-B23).
    """
    _outra, _outro_dashboard, coluna_alheia = _outra_empresa(db)

    resposta = client.patch(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/move",
        json={
            "column_id": coluna_alheia.id,
            "prev_card_id": None,
            "next_card_id": None,
        },
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 404


def test_cliente_de_outra_empresa_nao_ve_o_quadro(
    client: TestClient, db, user_token: str
):
    outra, _outro_dashboard, _coluna = _outra_empresa(db)

    resposta = client.get(
        f"/api/v1/dashboard/companies/{outra.id}/board",
        headers=_headers(user_token),
    )
    assert resposta.status_code == 404


# --------------------------------------- Regras que protegem a ordem


def test_soltar_card_em_coluna_secao_devolve_422(
    client: TestClient, db, admin_token: str, dashboard, board_com_3_colunas
):
    a_fazer, secao, _concluido = board_com_3_colunas
    card = _criar_cards(db, dashboard, a_fazer, ["Card"])[0]

    resposta = client.patch(
        f"/api/v1/dashboard/cards/{card.id}/move",
        json={"column_id": secao.id, "prev_card_id": None, "next_card_id": None},
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 422
    assert "seção" in resposta.json()["detail"]


def test_ancora_de_outra_coluna_devolve_422(
    client: TestClient, db, admin_token: str, dashboard, board_com_3_colunas
):
    """
    A âncora pertence à coluna de ORIGEM, não à de destino. Sem esta
    validação o servidor geraria uma chave a partir de uma posição de
    outra coluna — e o card apareceria em lugar arbitrário, com 200.
    """
    a_fazer, _secao, concluido = board_com_3_colunas
    cards_origem = _criar_cards(db, dashboard, a_fazer, ["A", "B"])
    _criar_cards(db, dashboard, concluido, ["C"])

    resposta = client.patch(
        f"/api/v1/dashboard/cards/{cards_origem[0].id}/move",
        json={
            "column_id": concluido.id,
            "prev_card_id": cards_origem[1].id,  # âncora da coluna errada
            "next_card_id": None,
        },
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 422


def test_ancoras_invertidas_devolvem_422(
    client: TestClient, db, admin_token: str, dashboard, dashboard_column
):
    cards = _criar_cards(db, dashboard, dashboard_column, ["A", "B", "C"])

    resposta = client.patch(
        f"/api/v1/dashboard/cards/{cards[0].id}/move",
        json={
            "column_id": dashboard_column.id,
            # prev depois de next: fora de ordem.
            "prev_card_id": cards[2].id,
            "next_card_id": cards[1].id,
        },
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 422


# ------------------------------------------------ CA-08: CRUD de coluna


def test_criar_coluna_no_fim_do_quadro(
    client: TestClient, admin_token: str, company, dashboard_column
):
    resposta = client.post(
        f"/api/v1/dashboard/companies/{company.id}/columns",
        json={"name": "Em revisão", "kind": "COLUMN", "after_column_id": None},
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 201
    assert resposta.json()["name"] == "Em revisão"
    assert resposta.json()["position"] > dashboard_column.position


def test_criar_coluna_depois_de_outra(
    client: TestClient, admin_token: str, company, board_com_3_colunas
):
    a_fazer, secao, _concluido = board_com_3_colunas

    nova = client.post(
        f"/api/v1/dashboard/companies/{company.id}/columns",
        json={"name": "Meio", "kind": "COLUMN", "after_column_id": a_fazer.id},
        headers=_headers(admin_token),
    ).json()

    assert a_fazer.position < nova["position"] < secao.position


def test_renomear_e_arquivar_coluna(
    client: TestClient, admin_token: str, dashboard_column
):
    resposta = client.patch(
        f"/api/v1/dashboard/columns/{dashboard_column.id}",
        json={"name": "Renomeada", "hidden": True, "wip_limit": 5},
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["name"] == "Renomeada"
    assert corpo["hidden"] is True
    assert corpo["wip_limit"] == 5


def test_mover_coluna_reordena(
    client: TestClient, admin_token: str, board_com_3_colunas
):
    a_fazer, _secao, concluido = board_com_3_colunas

    resposta = client.patch(
        f"/api/v1/dashboard/columns/{a_fazer.id}/move",
        json={"prev_column_id": concluido.id, "next_column_id": None},
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 200
    assert resposta.json()["position"] > concluido.position


def test_excluir_coluna_com_card_visivel_devolve_409(
    client: TestClient, db, admin_token: str, dashboard, dashboard_column
):
    """CA-08, primeira metade. Mensagem em português, com o número de
    cards — o admin precisa saber quantos mover."""
    _criar_cards(db, dashboard, dashboard_column, ["Card"])

    resposta = client.delete(
        f"/api/v1/dashboard/columns/{dashboard_column.id}",
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 409
    assert "card(s)" in resposta.json()["detail"]


def test_excluir_coluna_vazia_devolve_204(
    client: TestClient, admin_token: str, dashboard_column
):
    """CA-08, segunda metade."""
    resposta = client.delete(
        f"/api/v1/dashboard/columns/{dashboard_column.id}",
        headers=_headers(admin_token),
    )
    assert resposta.status_code == 204


def test_card_oculto_nao_impede_excluir_a_coluna(
    client: TestClient, db, admin_token: str, dashboard, dashboard_column
):
    """
    Card oculto já não é trabalho em aberto (decisão de O.4 em
    `get_dashboard_status_summary`). Exigir reexibir 30 cards arquivados
    só para apagar uma coluna seria burocracia sem ganho.
    """
    card = _criar_cards(db, dashboard, dashboard_column, ["Arquivado"])[0]
    card.hidden = True
    db.commit()

    resposta = client.delete(
        f"/api/v1/dashboard/columns/{dashboard_column.id}",
        headers=_headers(admin_token),
    )
    assert resposta.status_code == 204


def test_excluir_coluna_nao_apaga_o_card(
    client: TestClient, db, admin_token: str, dashboard, board_com_3_colunas
):
    """A FK é SET NULL: o card cai em `uncolumned`, nunca some."""
    a_fazer, _secao, concluido = board_com_3_colunas
    card = _criar_cards(db, dashboard, a_fazer, ["Card"])[0]

    client.patch(
        f"/api/v1/dashboard/cards/{card.id}/move",
        json={"column_id": concluido.id, "prev_card_id": None, "next_card_id": None},
        headers=_headers(admin_token),
    )
    resposta = client.delete(
        f"/api/v1/dashboard/columns/{a_fazer.id}", headers=_headers(admin_token)
    )

    assert resposta.status_code == 204
    db.expire_all()
    assert db.get(DashboardCard, card.id) is not None


def test_coluna_de_outra_empresa_devolve_404(
    client: TestClient, db, admin_token: str, user_token: str
):
    _outra, _outro_dashboard, coluna_alheia = _outra_empresa(db)

    resposta = client.patch(
        f"/api/v1/dashboard/columns/{coluna_alheia.id}",
        json={"name": "X", "hidden": False, "wip_limit": None},
        headers=_headers(user_token),
    )
    assert resposta.status_code in (403, 404)


# ---------------------------------------------------- Edição de card


def test_editar_card_grava_descricao(
    client: TestClient, admin_token: str, dashboard_card
):
    resposta = client.patch(
        f"/api/v1/dashboard/cards/{dashboard_card.id}",
        json={
            "title": "Política revisada",
            "description": "**Controle** — Convém que a política seja aprovada.",
            "control_code": "5.1",
            "category_id": None,
        },
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["title"] == "Política revisada"
    assert corpo["description"].startswith("**Controle**")


def test_bulk_set_column_move_varios_cards(
    client: TestClient, db, admin_token: str, company, dashboard, board_com_3_colunas
):
    a_fazer, _secao, concluido = board_com_3_colunas
    cards = _criar_cards(db, dashboard, a_fazer, ["A", "B", "C"])

    resposta = client.patch(
        f"/api/v1/dashboard/companies/{company.id}/cards/bulk",
        json={
            "card_ids": [c.id for c in cards],
            "operation": "set_column",
            "column_id": concluido.id,
        },
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 200
    assert resposta.json()["affected_count"] == 3

    db.expire_all()
    assert all(db.get(DashboardCard, c.id).column_id == concluido.id for c in cards)


def test_bulk_set_column_sem_column_id_devolve_422(
    client: TestClient, db, admin_token: str, company, dashboard, dashboard_column
):
    cards = _criar_cards(db, dashboard, dashboard_column, ["A"])

    resposta = client.patch(
        f"/api/v1/dashboard/companies/{company.id}/cards/bulk",
        json={"card_ids": [cards[0].id], "operation": "set_column"},
        headers=_headers(admin_token),
    )
    assert resposta.status_code == 422


def test_bulk_set_column_para_secao_devolve_422(
    client: TestClient, db, admin_token: str, company, dashboard, board_com_3_colunas
):
    a_fazer, secao, _concluido = board_com_3_colunas
    cards = _criar_cards(db, dashboard, a_fazer, ["A"])

    resposta = client.patch(
        f"/api/v1/dashboard/companies/{company.id}/cards/bulk",
        json={
            "card_ids": [cards[0].id],
            "operation": "set_column",
            "column_id": secao.id,
        },
        headers=_headers(admin_token),
    )
    assert resposta.status_code == 422


@pytest.mark.parametrize(
    "metodo,rota,corpo",
    [
        ("PATCH", "/api/v1/dashboard/cards/{card_id}/move", {"column_id": None}),
        (
            "PATCH",
            "/api/v1/dashboard/cards/{card_id}",
            {
                "title": "x",
                "description": None,
                "control_code": None,
                "category_id": None,
            },
        ),
        ("PUT", "/api/v1/dashboard/cards/{card_id}/labels", {"label_ids": []}),
    ],
)
def test_cliente_nao_pode_escrever_no_quadro(
    client: TestClient, user_token: str, dashboard_card, metodo, rota, corpo
):
    """CA-11: o quadro é leitura para o cliente e escrita só para o auditor."""
    resposta = client.request(
        metodo,
        rota.format(card_id=dashboard_card.id),
        json=corpo,
        headers=_headers(user_token),
    )
    assert resposta.status_code == 403
