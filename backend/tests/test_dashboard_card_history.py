from __future__ import annotations

"""
Histórico automático de movimentações do card.

Até esta entrega NADA no sistema escrevia em
`dashboard_card_history_entries`: a tabela existia desde D.6, o endpoint
de leitura devolvia o histórico e a tela sabia exibi-lo, mas as únicas
escritas eram `POST /cards/{id}/entries` (manual) e o
`seed_demo_companies.py`. O histórico que aparecia num card de
demonstração era dado semeado; num card real ficava vazio para sempre.

O que estes testes fixam é a regra de negócio, não o texto: **o que conta
como movimentação**. As duas metades disso são igualmente importantes —
registrar o que mudou, e NÃO registrar o que não mudou. Um histórico
cheio de "Conforme → Conforme" esconde os eventos que importam tão bem
quanto um histórico vazio.
"""

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.company_dashboard import (
    Dashboard,
    DashboardCard,
    DashboardCardCategory,
    DashboardCardchecklistItem,
    DashboardCardHistoryEntry,
    DashboardCardStatus,
    DashboardTemplate,
    DashboardTemplateCard,
)
from app.models.dashboard_board import DashboardTemplateColumn
from app.models.user import User
from app.services import dashboard_card_history as history
from app.services.fractional_index import n_keys_between


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _historico(db, card_id: int) -> list[DashboardCardHistoryEntry]:
    return list(
        db.scalars(
            select(DashboardCardHistoryEntry)
            .where(DashboardCardHistoryEntry.card_id == card_id)
            .order_by(DashboardCardHistoryEntry.id.asc())
        ).all()
    )


def _acoes(db, card_id: int) -> list[str]:
    return [entrada.action for entrada in _historico(db, card_id)]


# ------------------------------------------------------------- Status


def test_troca_de_status_registra_de_para(
    client: TestClient, db, admin_token: str, admin_user: User, dashboard_card
):
    resposta = client.patch(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/status",
        json={"status": "CONFORME"},
        headers=_headers(admin_token),
    )
    assert resposta.status_code == 200

    entradas = _historico(db, dashboard_card.id)
    assert len(entradas) == 1
    assert entradas[0].action == "Status alterado de Em análise para Conforme"
    # "Quem" é metade do valor de um histórico de auditoria.
    assert entradas[0].actor_user_id == admin_user.id


def test_status_repetido_nao_registra_nada(
    client: TestClient, db, admin_token: str, dashboard_card
):
    """Clicar duas vezes no mesmo status não é movimentação."""
    for _ in range(2):
        client.patch(
            f"/api/v1/dashboard/cards/{dashboard_card.id}/status",
            json={"status": "CONFORME"},
            headers=_headers(admin_token),
        )

    assert len(_historico(db, dashboard_card.id)) == 1


# -------------------------------------------------------------- Edição


def test_edicao_registra_campo_a_campo(
    client: TestClient, db, admin_token: str, dashboard_card
):
    resposta = client.patch(
        f"/api/v1/dashboard/cards/{dashboard_card.id}",
        json={
            "title": "Política de SI revisada",
            "description": "Texto normativo novo",
            "control_code": "5.2",
            "category_id": None,
        },
        headers=_headers(admin_token),
    )
    assert resposta.status_code == 200

    acoes = _acoes(db, dashboard_card.id)
    assert len(acoes) == 1
    # Um evento com os três campos, e não três eventos: foi UMA edição.
    assert "Título" in acoes[0]
    assert "Política de SI revisada" in acoes[0]
    assert "Código do controle" in acoes[0]
    assert "Descrição" in acoes[0]


def test_edicao_registra_categoria_por_nome(
    client: TestClient, db, admin_token: str, dashboard_card
):
    """`category_id` não diz nada a quem audita: "de 7 para 8" é ruído."""
    categoria = DashboardCardCategory(name="Tecnológico", color="#788c5d")
    db.add(categoria)
    db.commit()

    client.patch(
        f"/api/v1/dashboard/cards/{dashboard_card.id}",
        json={
            "title": dashboard_card.title,
            "description": None,
            "control_code": dashboard_card.control_code,
            "category_id": categoria.id,
        },
        headers=_headers(admin_token),
    )

    acoes = _acoes(db, dashboard_card.id)
    assert len(acoes) == 1
    assert "Categoria alterada de (nenhuma) para Tecnológico" in acoes[0]


def test_edicao_sem_mudanca_nao_registra(
    client: TestClient, db, admin_token: str, dashboard_card
):
    """Abrir o formulário e salvar sem editar nada não é movimentação."""
    client.patch(
        f"/api/v1/dashboard/cards/{dashboard_card.id}",
        json={
            "title": dashboard_card.title,
            "description": dashboard_card.description,
            "control_code": dashboard_card.control_code,
            "category_id": dashboard_card.category_id,
        },
        headers=_headers(admin_token),
    )

    assert _historico(db, dashboard_card.id) == []


def test_acao_longa_nao_estoura_a_coluna(
    client: TestClient, db, admin_token: str, dashboard_card
):
    """
    `action` é `String(255)` e o título vai a 160 caracteres: "Título de
    <antigo> para <novo>" passa de 255 com facilidade. Em MySQL isso é
    erro de inserção, e derrubaria a operação de negócio (salvar o card)
    por causa do registro dela.
    """
    titulo_longo = "T" * 160
    resposta = client.patch(
        f"/api/v1/dashboard/cards/{dashboard_card.id}",
        json={
            "title": titulo_longo,
            "description": "D" * 500,
            "control_code": "C" * 40,
            "category_id": None,
        },
        headers=_headers(admin_token),
    )
    assert resposta.status_code == 200

    acoes = _acoes(db, dashboard_card.id)
    assert len(acoes) == 1
    assert len(acoes[0]) <= history.ACTION_MAX_LENGTH


# --------------------------------------------------------------- Mover


def test_mover_entre_colunas_registra_origem_e_destino(
    client: TestClient, db, admin_token: str, dashboard, board_com_3_colunas
):
    a_fazer, _secao, concluido = board_com_3_colunas
    card = DashboardCard(
        dashboard_id=dashboard.id,
        title="Backup",
        tag="t",
        column_id=a_fazer.id,
        position="a0",
    )
    db.add(card)
    db.commit()

    resposta = client.patch(
        f"/api/v1/dashboard/cards/{card.id}/move",
        json={
            "column_id": concluido.id,
            "prev_card_id": None,
            "next_card_id": None,
        },
        headers=_headers(admin_token),
    )
    assert resposta.status_code == 200

    assert _acoes(db, card.id) == ["Movido de A fazer para Concluído"]


def test_reordenar_na_mesma_coluna_nao_se_confunde_com_mudanca_de_coluna(
    client: TestClient, db, admin_token: str, dashboard, board_com_3_colunas
):
    """
    Trocar de coluna muda o andamento do controle; reordenar dentro dela é
    arrumação visual. Registrar as duas com o mesmo texto tornaria o
    histórico ilegível, porque arrastar é a interação mais frequente do
    quadro.
    """
    a_fazer, _secao, _concluido = board_com_3_colunas
    posicoes = n_keys_between(None, None, 2)
    cards = [
        DashboardCard(
            dashboard_id=dashboard.id,
            title=titulo,
            tag="t",
            column_id=a_fazer.id,
            position=posicao,
        )
        for titulo, posicao in zip(["A", "B"], posicoes)
    ]
    db.add_all(cards)
    db.commit()

    client.patch(
        f"/api/v1/dashboard/cards/{cards[0].id}/move",
        json={
            "column_id": a_fazer.id,
            "prev_card_id": cards[1].id,
            "next_card_id": None,
        },
        headers=_headers(admin_token),
    )

    assert _acoes(db, cards[0].id) == ["Reordenado em A fazer"]


# ----------------------------------------------------------- Checklist


def test_ciclo_do_checklist_fica_no_historico(
    client: TestClient, db, admin_token: str, dashboard_card
):
    criacao = client.post(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/entries",
        json={"entry_type": "CHECKLIST", "content": "Evidência documental"},
        headers=_headers(admin_token),
    )
    assert criacao.status_code == 201

    item = db.scalar(
        select(DashboardCardchecklistItem).where(
            DashboardCardchecklistItem.card_id == dashboard_card.id
        )
    )
    client.patch(
        f"/api/v1/dashboard/checklist-items/{item.id}/toggle",
        headers=_headers(admin_token),
    )
    client.delete(
        f"/api/v1/dashboard/checklist-items/{item.id}",
        headers=_headers(admin_token),
    )

    assert _acoes(db, dashboard_card.id) == [
        "Item de checklist adicionado: Evidência documental",
        "Item de checklist concluído: Evidência documental",
        "Item de checklist removido: Evidência documental",
    ]


def test_remocao_de_item_registra_qual_item(
    client: TestClient, db, admin_token: str, dashboard_card
):
    """
    O título é lido ANTES do `db.delete`: depois dele o objeto vira
    transiente e o histórico registraria "removido: " sem dizer qual.
    """
    item = DashboardCardchecklistItem(
        card_id=dashboard_card.id, title="Item específico", done=False
    )
    db.add(item)
    db.commit()

    client.delete(
        f"/api/v1/dashboard/checklist-items/{item.id}",
        headers=_headers(admin_token),
    )

    assert _acoes(db, dashboard_card.id) == [
        "Item de checklist removido: Item específico"
    ]


# --------------------------------------------------------- Ação em lote


def test_ocultar_em_lote_registra_so_os_que_mudaram(
    client: TestClient, db, admin_token: str, company, dashboard, board_com_3_colunas
):
    a_fazer, _secao, _concluido = board_com_3_colunas
    posicoes = n_keys_between(None, None, 2)
    visivel = DashboardCard(
        dashboard_id=dashboard.id,
        title="Visível",
        tag="t",
        column_id=a_fazer.id,
        position=posicoes[0],
        hidden=False,
    )
    ja_oculto = DashboardCard(
        dashboard_id=dashboard.id,
        title="Já oculto",
        tag="t",
        column_id=a_fazer.id,
        position=posicoes[1],
        hidden=True,
    )
    db.add_all([visivel, ja_oculto])
    db.commit()

    client.patch(
        f"/api/v1/dashboard/companies/{company.id}/cards/bulk",
        json={
            "card_ids": [visivel.id, ja_oculto.id],
            "operation": "hide",
            "category_id": None,
        },
        headers=_headers(admin_token),
    )

    assert _acoes(db, visivel.id) == ["Card arquivado"]
    # O que já estava oculto não sofreu movimentação nenhuma.
    assert _acoes(db, ja_oculto.id) == []


def test_remover_em_lote_nao_deixa_historico_orfao(
    client: TestClient, db, admin_token: str, company, dashboard_card
):
    """
    `card_id` é `ON DELETE CASCADE`: uma entrada escrita na remoção seria
    apagada pelo mesmo comando que a criou. Histórico de card removido
    teria de viver fora do card — outra tabela, outra decisão.
    """
    card_id = dashboard_card.id
    client.patch(
        f"/api/v1/dashboard/companies/{company.id}/cards/bulk",
        json={"card_ids": [card_id], "operation": "remove", "category_id": None},
        headers=_headers(admin_token),
    )

    assert db.get(DashboardCard, card_id) is None
    assert _historico(db, card_id) == []


# ------------------------------------------------------ Aplicar template


def test_aplicar_template_registra_criacao_de_cada_card(
    client: TestClient, db, admin_token: str, company, dashboard
):
    """
    Decisão de projeto: evento AGREGADO. Não é uma linha só — `card_id` é
    obrigatório, então histórico de quadro seria outra tabela. O que se
    agrega é a ESCRITA: um `add_all` depois do flush, não 215 idas ao
    banco de dentro do laço.
    """
    template = DashboardTemplate(name="ISO 27001", is_default=False)
    db.add(template)
    db.flush()
    coluna = DashboardTemplateColumn(
        template_id=template.id, name="A fazer", position="a0"
    )
    db.add(coluna)
    db.flush()
    db.add_all(
        [
            DashboardTemplateCard(
                template_id=template.id,
                title=f"Controle {i}",
                tag="t",
                template_column_id=coluna.id,
                position=posicao,
            )
            for i, posicao in enumerate(n_keys_between(None, None, 3))
        ]
    )
    db.commit()

    resposta = client.post(
        f"/api/v1/dashboard/companies/{company.id}/apply-template",
        json={"template_id": template.id},
        headers=_headers(admin_token),
    )
    assert resposta.status_code == 200
    assert resposta.json()["created_count"] == 3

    dashboard = db.scalar(
        select(Dashboard).where(Dashboard.company_id == company.id)
    )
    cards = list(
        db.scalars(
            select(DashboardCard).where(DashboardCard.dashboard_id == dashboard.id)
        ).all()
    )
    assert len(cards) == 3
    for card in cards:
        assert _acoes(db, card.id) == [
            "Card criado pela aplicação do template ISO 27001"
        ]


def test_aplicar_template_duas_vezes_nao_duplica_historico(
    client: TestClient, db, admin_token: str, company, dashboard
):
    """`apply_template_to_company` é idempotente — o histórico acompanha:
    a segunda aplicação não cria card, então não registra criação."""
    template = DashboardTemplate(name="ISO 27001", is_default=False)
    db.add(template)
    db.flush()
    db.add(
        DashboardTemplateCard(
            template_id=template.id, title="Controle 5.1", tag="t", position="a0"
        )
    )
    db.commit()

    for _ in range(2):
        client.post(
            f"/api/v1/dashboard/companies/{company.id}/apply-template",
            json={"template_id": template.id},
            headers=_headers(admin_token),
        )

    dashboard = db.scalar(
        select(Dashboard).where(Dashboard.company_id == company.id)
    )
    card = db.scalar(
        select(DashboardCard).where(DashboardCard.dashboard_id == dashboard.id)
    )
    assert len(_historico(db, card.id)) == 1


# ------------------------------------------------------------- Criação


def test_card_criado_a_mao_registra_criacao(
    client: TestClient, db, admin_token: str, company, dashboard_column
):
    categoria = DashboardCardCategory(name="Governança", color="#788c5d")
    db.add(categoria)
    db.commit()

    resposta = client.post(
        f"/api/v1/dashboard/companies/{company.id}/cards",
        json={
            "title": "Card manual",
            "category_id": categoria.id,
            "control_code": None,
            "column_id": dashboard_column.id,
            "description": None,
        },
        headers=_headers(admin_token),
    )
    assert resposta.status_code == 201

    assert _acoes(db, resposta.json()["id"]) == ["Card criado"]


# ------------------------------------------------------------ Etiquetas


def test_troca_de_etiquetas_registra_o_conjunto(
    client: TestClient, db, admin_token: str, dashboard_card, etiquetas
):
    resposta = client.put(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/labels",
        json={"label_ids": [etiquetas[0].id]},
        headers=_headers(admin_token),
    )
    assert resposta.status_code == 200

    acoes = _acoes(db, dashboard_card.id)
    assert len(acoes) == 1
    assert etiquetas[0].name in acoes[0]


def test_remover_todas_as_etiquetas_registra_a_remocao(
    client: TestClient, db, admin_token: str, dashboard_card, etiquetas
):
    dashboard_card.labels.append(etiquetas[0])
    db.commit()

    client.put(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/labels",
        json={"label_ids": []},
        headers=_headers(admin_token),
    )

    assert _acoes(db, dashboard_card.id) == ["Etiquetas removidas"]


# ------------------------------------------------------------- Leitura


def test_historico_chega_na_api_em_ordem_cronologica(
    client: TestClient, db, admin_token: str, admin_user: User, dashboard_card
):
    """O contrato completo, do ponto de vista da tela: o que mudou, quando
    e quem — em ordem, do mais antigo para o mais recente."""
    client.patch(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/status",
        json={"status": "PARCIAL"},
        headers=_headers(admin_token),
    )
    client.patch(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/status",
        json={"status": "CONFORME"},
        headers=_headers(admin_token),
    )

    corpo = client.get(
        f"/api/v1/dashboard/cards/{dashboard_card.id}",
        headers=_headers(admin_token),
    ).json()

    assert [entrada["action"] for entrada in corpo["history"]] == [
        "Status alterado de Em análise para Parcial",
        "Status alterado de Parcial para Conforme",
    ]
    for entrada in corpo["history"]:
        assert entrada["created_at"]
        assert entrada["actor_user"]["full_name"] == admin_user.full_name


def test_cliente_continua_sem_ver_o_historico(
    client: TestClient, db, admin_token: str, user_token: str, dashboard_card
):
    """B-A28 não afrouxa por o histórico ter passado a ser preenchido: ele
    é registro interno do auditor, e o cliente recebe lista vazia."""
    client.patch(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/status",
        json={"status": "CONFORME"},
        headers=_headers(admin_token),
    )

    corpo = client.get(
        f"/api/v1/dashboard/cards/{dashboard_card.id}",
        headers=_headers(user_token),
    ).json()

    assert corpo["history"] == []
    # E o registro continua existindo no banco — só não é exposto a ele.
    assert len(_historico(db, dashboard_card.id)) == 1


def test_coluna_do_card_sem_coluna_aparece_como_sem_coluna(
    client: TestClient, db, admin_token: str, dashboard, board_com_3_colunas
):
    """Card órfão de coluna excluída é caso real (a FK é SET NULL): o
    histórico precisa dizer algo legível, não "None"."""
    a_fazer, _secao, _concluido = board_com_3_colunas
    card = DashboardCard(
        dashboard_id=dashboard.id,
        title="Órfão",
        tag="t",
        column_id=None,
        position="a0",
    )
    db.add(card)
    db.commit()

    client.patch(
        f"/api/v1/dashboard/cards/{card.id}/move",
        json={
            "column_id": a_fazer.id,
            "prev_card_id": None,
            "next_card_id": None,
        },
        headers=_headers(admin_token),
    )

    assert _acoes(db, card.id) == ["Movido de Sem coluna para A fazer"]


def test_status_label_cobre_todo_o_enum():
    """Um status novo no enum sem rótulo aqui cairia no `.value` cru
    ("NAOCONFORME") no meio de uma frase em português."""
    for status_enum in DashboardCardStatus:
        assert status_enum in history.STATUS_LABELS, (
            f"{status_enum.value} não tem rótulo em pt-BR"
        )


def test_movimentacao_sem_autor_e_permitida(db, dashboard_card):
    """`actor_user_id` é SET NULL e automações não têm usuário: o service
    aceita `actor=None` em vez de exigir um usuário fictício."""
    history.record(db, dashboard_card.id, "Ação automática", None)
    db.commit()

    entradas = _historico(db, dashboard_card.id)
    assert len(entradas) == 1
    assert entradas[0].actor_user_id is None
