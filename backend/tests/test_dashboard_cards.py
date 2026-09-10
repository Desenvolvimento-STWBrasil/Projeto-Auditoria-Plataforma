from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.company_dashboard import (
    Dashboard,
    DashboardCard,
    DashboardCardCategory,
    DashboardCardchecklistItem,
    DashboardCardHistoryEntry,
    DashboardCardMessage,
    DashboardCardStatus,
    DashboardMessageType,
)
from app.models.user import User


def test_get_card_details_populates_actor_and_author(
    client: TestClient,
    db,
    admin_token: str,
    admin_user: User,
    dashboard_card: DashboardCard,
):
    """E.7: histórico e chat do card devem trazer quem fez a ação (actor_user/
    author_user), não só o texto — antes desta correção, os dois campos
    sempre vinham nulos mesmo com o autor real gravado no banco."""
    history = DashboardCardHistoryEntry(
        card_id=dashboard_card.id,
        action="Status alterado para PARCIAL",
        actor_user_id=admin_user.id,
    )
    message = DashboardCardMessage(
        card_id=dashboard_card.id,
        author_user_id=admin_user.id,
        message_type=DashboardMessageType.ANSWER,
        content="Evidência aprovada.",
    )
    db.add_all([history, message])
    db.commit()

    resp = client.get(
        f"/api/v1/dashboard/cards/{dashboard_card.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert len(body["history"]) == 1
    assert body["history"][0]["actor_user"] == {
        "id": admin_user.id,
        "full_name": admin_user.full_name,
    }

    assert len(body["chat"]) == 1
    assert body["chat"][0]["author_user"] == {
        "id": admin_user.id,
        "full_name": admin_user.full_name,
    }


def test_get_card_details_traz_a_categoria_viva_e_nao_so_a_tag(
    client: TestClient,
    db,
    admin_token: str,
    dashboard_card: DashboardCard,
):
    """
    O detalhe se anunciava "completo" e devolvia apenas `tag` — o nome que
    a categoria tinha quando o card foi criado, congelado desde O.3.

    Quem precisa disso é o formulário de edição do card: um <select> de
    categoria pré-preenchido por `tag` seleciona a opção errada assim que
    a categoria é renomeada, e gravar de volta trocaria a categoria do
    card sem ninguém ter pedido. Por isso `category_id` (vínculo vivo)
    entrou no payload — e `tag` continua lá, intocada.
    """
    categoria = DashboardCardCategory(name="Tecnológico", color="#788c5d")
    db.add(categoria)
    db.flush()
    dashboard_card.category_id = categoria.id
    db.commit()

    resp = client.get(
        f"/api/v1/dashboard/cards/{dashboard_card.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["category_id"] == categoria.id
    assert body["category_name"] == "Tecnológico"
    # A `tag` histórica não foi tocada por esta mudança.
    assert body["tag"] == "governanca"


def test_get_card_details_categoria_nula_nao_estoura(
    client: TestClient, admin_token: str, dashboard_card: DashboardCard
):
    """Card sem categoria é caso legítimo (`category_id` é nullable, a FK é
    SET NULL): os dois campos vêm nulos em vez de quebrar a serialização."""
    resp = client.get(
        f"/api/v1/dashboard/cards/{dashboard_card.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["category_id"] is None
    assert resp.json()["category_name"] is None


def test_get_card_details_actor_user_none_when_absent(
    client: TestClient,
    db,
    admin_token: str,
    dashboard_card: DashboardCard,
):
    """Histórico com actor_user_id nulo (ex.: usuário removido, SET NULL na FK)
    não deve quebrar a serialização — actor_user deve vir None."""
    history = DashboardCardHistoryEntry(
        card_id=dashboard_card.id,
        action="Card criado automaticamente pelo onboarding",
        actor_user_id=None,
    )
    db.add(history)
    db.commit()

    resp = client.get(
        f"/api/v1/dashboard/cards/{dashboard_card.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["history"][0]["actor_user"] is None


def test_create_card_note_success(
    client: TestClient,
    admin_token: str,
    admin_user: User,
    dashboard_card: DashboardCard,
):
    """E.9: admin consegue criar uma nota interna no card."""
    resp = client.post(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/notes",
        json={"content": "Cliente foi notificado por telefone em 10/08."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["content"] == "Cliente foi notificado por telefone em 10/08."
    assert body["created_by_user_id"] == admin_user.id
    assert body["created_by_name"] == admin_user.full_name
    assert "id" in body and "created_at" in body


def test_create_card_note_requires_admin(
    client: TestClient,
    user_token: str,
    dashboard_card: DashboardCard,
):
    """Notas são um registro interno da auditoria — cliente (role 'user') não
    pode criar, diferente do chat (que é bilateral)."""
    resp = client.post(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/notes",
        json={"content": "Tentativa de nota pelo cliente."},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403


def test_create_card_note_unknown_card_returns_404(
    client: TestClient, admin_token: str
):
    resp = client.post(
        "/api/v1/dashboard/cards/999999/notes",
        json={"content": "Nota para card inexistente."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


def test_create_card_note_rejects_empty_content(
    client: TestClient, admin_token: str, dashboard_card: DashboardCard
):
    resp = client.post(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/notes",
        json={"content": ""},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


def test_list_card_notes_returns_notes_with_author_name(
    client: TestClient,
    admin_token: str,
    admin_user: User,
    dashboard_card: DashboardCard,
):
    for content in ("Primeira nota.", "Segunda nota."):
        resp = client.post(
            f"/api/v1/dashboard/cards/{dashboard_card.id}/notes",
            json={"content": content},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201

    resp = client.get(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/notes",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    notes = resp.json()
    assert len(notes) == 2
    assert [n["content"] for n in notes] == ["Primeira nota.", "Segunda nota."]
    assert all(n["created_by_name"] == admin_user.full_name for n in notes)


def test_list_card_notes_requires_admin(
    client: TestClient, user_token: str, dashboard_card: DashboardCard
):
    resp = client.get(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/notes",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403


def test_status_summary_aggregates_by_status(
    client: TestClient,
    db,
    admin_token: str,
    dashboard,
):
    db.add_all(
        [
            DashboardCard(
                dashboard_id=dashboard.id,
                title="Card 1",
                tag="t1",
                status=DashboardCardStatus.EM_ANALISE,
            ),
            DashboardCard(
                dashboard_id=dashboard.id,
                title="Card 2",
                tag="t1",
                status=DashboardCardStatus.EM_ANALISE,
            ),
            DashboardCard(
                dashboard_id=dashboard.id,
                title="Card 3",
                tag="t1",
                status=DashboardCardStatus.CONFORME,
            ),
        ]
    )
    db.commit()

    resp = client.get(
        "/api/v1/dashboard/status-summary",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "em_analise": 2,
        "parcial": 0,
        "conforme": 1,
        "naoconforme": 0,
    }


def test_status_summary_requires_admin(client: TestClient, user_token: str):
    resp = client.get(
        "/api/v1/dashboard/status-summary",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403


def _create_category(client: TestClient, headers: dict, name: str) -> int:
    resp = client.post(
        "/api/v1/admin/dashboard-categories",
        headers=headers,
        json={"name": name, "color": "#788c5d", "sort_order": 0},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_list_cards_by_company_exposes_category_and_hidden(
    client: TestClient, admin_token: str, dashboard_card
):
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.get(
        f"/api/v1/dashboard/companies/{dashboard_card.dashboard.company_id}/cards",
        headers=headers,
    )
    assert resp.status_code == 200
    item = resp.json()[0]
    assert "category_id" in item
    assert "hidden" in item
    assert "is_outdated" in item
    assert item["hidden"] is False


def test_hidden_cards_excluded_by_default_and_included_with_flag(
    client: TestClient, db, admin_token: str, dashboard
):
    from app.models.company_dashboard import DashboardCard

    card = DashboardCard(
        dashboard_id=dashboard.id, title="Oculto", tag="t", hidden=True
    )
    db.add(card)
    db.commit()

    headers = {"Authorization": f"Bearer {admin_token}"}
    default_resp = client.get(
        f"/api/v1/dashboard/companies/{dashboard.company_id}/cards", headers=headers
    )
    assert all(not c["hidden"] for c in default_resp.json())

    with_hidden_resp = client.get(
        f"/api/v1/dashboard/companies/{dashboard.company_id}/cards"
        "?include_hidden=true",
        headers=headers,
    )
    assert any(c["hidden"] for c in with_hidden_resp.json())


def test_create_card_requires_category(client: TestClient, admin_token: str, dashboard):
    headers = {"Authorization": f"Bearer {admin_token}"}
    category_id = _create_category(client, headers, "Operacional")

    resp = client.post(
        f"/api/v1/dashboard/companies/{dashboard.company_id}/cards",
        headers=headers,
        json={"title": "Novo card manual", "category_id": category_id},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["category_name"] == "Operacional"
    assert body["origin_template_card_id"] is None


def test_apply_template_is_idempotent_and_flags_outdated(
    client: TestClient, admin_token: str, dashboard
):
    headers = {"Authorization": f"Bearer {admin_token}"}
    category_id = _create_category(client, headers, "Financeiro")

    template = client.post(
        "/api/v1/admin/templates",
        headers=headers,
        json={"name": "Template de Teste", "description": None, "is_default": False},
    ).json()
    template_card = client.post(
        f"/api/v1/admin/templates/{template['id']}/cards",
        headers=headers,
        json={
            "title": "Fluxo de caixa",
            "description": None,
            "category_id": category_id,
            "sort_order": 0,
        },
    ).json()

    company_id = dashboard.company_id

    first_apply = client.post(
        f"/api/v1/dashboard/companies/{company_id}/apply-template",
        headers=headers,
        json={"template_id": template["id"]},
    )
    assert first_apply.status_code == 200
    assert first_apply.json()["created_count"] == 1
    assert first_apply.json()["already_applied_count"] == 0

    second_apply = client.post(
        f"/api/v1/dashboard/companies/{company_id}/apply-template",
        headers=headers,
        json={"template_id": template["id"]},
    )
    assert second_apply.json()["created_count"] == 0
    assert second_apply.json()["already_applied_count"] == 1
    assert second_apply.json()["outdated_card_ids"] == []

    # Edita o template — reaplicar deve sinalizar o card como desatualizado,
    # sem sobrescrevê-lo.
    client.patch(
        f"/api/v1/admin/templates/template-cards/{template_card['id']}",
        headers=headers,
        json={
            "title": "Fluxo de caixa (revisado)",
            "description": None,
            "category_id": category_id,
            "sort_order": 0,
        },
    )
    third_apply = client.post(
        f"/api/v1/dashboard/companies/{company_id}/apply-template",
        headers=headers,
        json={"template_id": template["id"]},
    )
    assert third_apply.json()["created_count"] == 0
    assert len(third_apply.json()["outdated_card_ids"]) == 1

    cards = client.get(
        f"/api/v1/dashboard/companies/{company_id}/cards", headers=headers
    ).json()
    assert cards[0]["title"] == "Fluxo de caixa"  # não sobrescrito


def test_bulk_hide_and_unhide(client: TestClient, admin_token: str, dashboard_card):
    headers = {"Authorization": f"Bearer {admin_token}"}
    company_id = dashboard_card.dashboard.company_id

    hide_resp = client.patch(
        f"/api/v1/dashboard/companies/{company_id}/cards/bulk",
        headers=headers,
        json={"card_ids": [dashboard_card.id], "operation": "hide"},
    )
    assert hide_resp.status_code == 200
    assert hide_resp.json()["affected_count"] == 1

    listed = client.get(
        f"/api/v1/dashboard/companies/{company_id}/cards?include_hidden=true",
        headers=headers,
    ).json()
    assert listed[0]["hidden"] is True

    unhide_resp = client.patch(
        f"/api/v1/dashboard/companies/{company_id}/cards/bulk",
        headers=headers,
        json={"card_ids": [dashboard_card.id], "operation": "unhide"},
    )
    assert unhide_resp.json()["affected_count"] == 1


def test_bulk_operation_ignores_cards_from_other_company(
    client: TestClient, db, admin_token: str, dashboard_card
):
    """Um id de card de outra empresa é ignorado, nunca afeta outro cliente."""
    from app.core.security import hash_password
    from app.models.company_dashboard import Company, Dashboard, DashboardCard
    from app.models.user import User

    other_principal = User(
        full_name="Outro Principal",
        email="outroprincipal@test.com",
        password_hash=hash_password("Outro123!"),
        role="user",
    )
    db.add(other_principal)
    db.flush()
    other_company = Company(
        name="Outra Empresa",
        email="outraempresa@test.com",
        principal_user_id=other_principal.id,
    )
    db.add(other_company)
    db.flush()
    other_dashboard = Dashboard(company_id=other_company.id, title="Outro Dashboard")
    db.add(other_dashboard)
    db.flush()
    other_card = DashboardCard(
        dashboard_id=other_dashboard.id, title="Card de outra empresa", tag="t"
    )
    db.add(other_card)
    db.commit()
    db.refresh(other_card)

    headers = {"Authorization": f"Bearer {admin_token}"}
    company_id = dashboard_card.dashboard.company_id

    resp = client.patch(
        f"/api/v1/dashboard/companies/{company_id}/cards/bulk",
        headers=headers,
        json={"card_ids": [dashboard_card.id, other_card.id], "operation": "hide"},
    )
    assert resp.status_code == 200
    assert resp.json()["affected_count"] == 1  # só o card da empresa certa

    db.refresh(other_card)
    assert other_card.hidden is False


def test_status_summary_excludes_hidden_cards(
    client: TestClient, db, admin_token: str, dashboard
):
    from app.models.company_dashboard import DashboardCard, DashboardCardStatus

    db.add_all(
        [
            DashboardCard(
                dashboard_id=dashboard.id,
                title="Visível",
                tag="t",
                status=DashboardCardStatus.EM_ANALISE,
                hidden=False,
            ),
            DashboardCard(
                dashboard_id=dashboard.id,
                title="Oculto",
                tag="t",
                status=DashboardCardStatus.EM_ANALISE,
                hidden=True,
            ),
        ]
    )
    db.commit()

    resp = client.get(
        "/api/v1/dashboard/status-summary",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.json()["em_analise"] == 1


def test_apply_template_adopts_pre_o3_cards_instead_of_duplicating(
    client: TestClient, admin_token: str, db, company, dashboard
):
    """B-A24: cards sem origin_template_card_id (criados antes de O.3)
    devem ser ADOTADOS por título, nunca duplicados."""
    from app.models.company_dashboard import DashboardCard, DashboardCardCategory

    category = DashboardCardCategory(name="Compliance", color="#96311D", sort_order=3)
    db.add(category)
    db.commit()

    titles = ["Política de SI", "Gestão de Acesso", "Backup"]
    for index, title in enumerate(titles):
        db.add(
            DashboardCard(
                dashboard_id=dashboard.id,
                title=title,
                tag=category.name,
                category_id=category.id,
                origin_template_card_id=None,
                sort_order=index,
            )
        )
    db.commit()

    headers = {"Authorization": f"Bearer {admin_token}"}
    template = client.post(
        "/api/v1/admin/templates",
        json={"name": "Template Padrão", "description": None, "is_default": False},
        headers=headers,
    ).json()
    for index, title in enumerate(titles):
        client.post(
            f"/api/v1/admin/templates/{template['id']}/cards",
            json={
                "title": title,
                "description": None,
                "category_id": category.id,
                "sort_order": index,
            },
            headers=headers,
        )

    response = client.post(
        f"/api/v1/dashboard/companies/{company.id}/apply-template",
        json={"template_id": template["id"]},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["created_count"] == 0
    assert body["adopted_count"] == 3

    db.expire_all()
    cards = (
        db.query(DashboardCard).filter(DashboardCard.dashboard_id == dashboard.id).all()
    )
    assert len(cards) == 3
    assert all(card.origin_template_card_id is not None for card in cards)


def test_bulk_restore_reports_zero_for_card_without_origin(
    client: TestClient, admin_token: str, company, dashboard_card
):
    """B-M23: card sem origin_template_card_id não pode ser contado como
    restaurado — reportar sucesso mascara B-A24/B-A25."""
    response = client.patch(
        f"/api/v1/dashboard/companies/{company.id}/cards/bulk",
        json={
            "card_ids": [dashboard_card.id],
            "operation": "restore_from_template",
            "category_id": None,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["affected_count"] == 0


# --------------------------------------------- Quadro Kanban na listagem


def test_listagem_de_cards_traz_os_campos_do_quadro(
    client: TestClient, db, admin_token: str, company, dashboard_card, etiquetas
):
    """
    Os quatro campos novos (`column_id`, `position`, `description`,
    `labels`) são ADIÇÕES ao contrato — nenhum consumidor antigo quebra,
    e quem precisa deles não faz uma segunda chamada.
    """
    dashboard_card.description = "Texto normativo"
    dashboard_card.labels = [etiquetas[0]]
    db.commit()

    resposta = client.get(
        f"/api/v1/dashboard/companies/{company.id}/cards",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resposta.status_code == 200
    card = resposta.json()[0]
    assert card["column_id"] == dashboard_card.column_id
    assert card["position"] == dashboard_card.position
    assert card["description"] == "Texto normativo"
    assert [e["name"] for e in card["labels"]] == ["Item Critico"]


def test_listagem_de_cards_ordena_por_position(
    client: TestClient, db, admin_token: str, company, dashboard, dashboard_column
):
    """
    A ordenação passou de `sort_order` para `position`. Os `sort_order`
    abaixo estão em ordem INVERSA à das posições, de propósito: se a rota
    ainda ordenasse pelo campo antigo, o teste falharia.
    """
    from app.models.company_dashboard import DashboardCard
    from app.services.fractional_index import n_keys_between

    posicoes = n_keys_between(None, None, 3)
    for indice, (titulo, posicao) in enumerate(
        zip(["Primeiro", "Segundo", "Terceiro"], posicoes)
    ):
        db.add(
            DashboardCard(
                dashboard_id=dashboard.id,
                title=titulo,
                tag="t",
                column_id=dashboard_column.id,
                position=posicao,
                sort_order=10 - indice,
            )
        )
    db.commit()

    corpo = client.get(
        f"/api/v1/dashboard/companies/{company.id}/cards",
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()

    assert [c["title"] for c in corpo] == ["Primeiro", "Segundo", "Terceiro"]


def test_criar_card_dentro_de_uma_coluna(
    client: TestClient, admin_token: str, db, company, dashboard, dashboard_column
):
    from app.models.company_dashboard import DashboardCardCategory

    categoria = DashboardCardCategory(name="Governança", color="#000000", sort_order=0)
    db.add(categoria)
    db.commit()

    resposta = client.post(
        f"/api/v1/dashboard/companies/{company.id}/cards",
        json={
            "title": "Card novo",
            "category_id": categoria.id,
            "column_id": dashboard_column.id,
            "description": "Descrição do controle",
            "control_code": "5.2",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["column_id"] == dashboard_column.id
    assert corpo["description"] == "Descrição do controle"
    assert corpo["position"]


def test_criar_card_em_coluna_de_outra_empresa_devolve_404(
    client: TestClient, admin_token: str, db, company, dashboard
):
    from app.core.security import hash_password
    from app.models.company_dashboard import Company, DashboardCardCategory
    from app.models.dashboard_board import DashboardColumn
    from app.models.user import User

    categoria = DashboardCardCategory(name="Governança", color="#000000", sort_order=0)
    outro_usuario = User(
        full_name="Outro",
        email="outro2@test.com",
        password_hash=hash_password("Outro123!"),
        role="user",
    )
    db.add_all([categoria, outro_usuario])
    db.flush()

    outra = Company(
        name="Empresa Alheia",
        email="alheia@test.com",
        principal_user_id=outro_usuario.id,
    )
    db.add(outra)
    db.flush()
    outro_dashboard = Dashboard(company_id=outra.id, title="Dash Alheio")
    db.add(outro_dashboard)
    db.flush()
    coluna_alheia = DashboardColumn(
        dashboard_id=outro_dashboard.id, name="Alheia", position="a0"
    )
    db.add(coluna_alheia)
    db.commit()

    resposta = client.post(
        f"/api/v1/dashboard/companies/{company.id}/cards",
        json={
            "title": "Card",
            "category_id": categoria.id,
            "column_id": coluna_alheia.id,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resposta.status_code == 404


def test_detalhe_do_card_traz_descricao_para_o_cliente(
    client: TestClient, db, user_token: str, dashboard_card, etiquetas
):
    """
    U7: a `description` é o texto normativo do controle — é exatamente o
    que o cliente precisa ler para saber o que entregar. Ao contrário de
    checklist e histórico (B-A28), ela NÃO é registro interno.
    """
    dashboard_card.description = "Convém que a política seja aprovada."
    dashboard_card.labels = [etiquetas[1]]
    db.commit()

    corpo = client.get(
        f"/api/v1/dashboard/cards/{dashboard_card.id}",
        headers={"Authorization": f"Bearer {user_token}"},
    ).json()

    assert corpo["description"] == "Convém que a política seja aprovada."
    assert corpo["column_id"] == dashboard_card.column_id
    assert [e["name"] for e in corpo["labels"]] == ["Alta Criticidade"]
    # B-A28 continua valendo para o registro interno.
    assert corpo["checklist"] == []
    assert corpo["history"] == []


def test_delete_checklist_item_remove_de_verdade(
    client: TestClient,
    db,
    admin_token: str,
    dashboard_card: DashboardCard,
):
    """
    Faltava o par de `POST /entries` com `entry_type=CHECKLIST`: dava para
    criar e marcar item, nunca para desfazer. Um item digitado errado
    ficava para sempre no card, contando no denominador do progresso.
    """
    item = DashboardCardchecklistItem(
        card_id=dashboard_card.id, title="Item digitado errado", done=False
    )
    db.add(item)
    db.commit()
    item_id = item.id

    resp = client.delete(
        f"/api/v1/dashboard/checklist-items/{item_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 204
    assert db.get(DashboardCardchecklistItem, item_id) is None
    # E o item sai do detalhe do card, não só da tabela.
    detalhe = client.get(
        f"/api/v1/dashboard/cards/{dashboard_card.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert detalhe.json()["checklist"] == []


def test_delete_checklist_item_inexistente_da_404(
    client: TestClient, admin_token: str
):
    resp = client.delete(
        "/api/v1/dashboard/checklist-items/999999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


def test_cliente_nao_pode_remover_item_de_checklist(
    client: TestClient,
    db,
    user_token: str,
    dashboard_card: DashboardCard,
):
    """B-A23: o checklist é registro interno da equipe de auditoria. O
    cliente não o lê (B-A28) e, com mais razão, não o apaga."""
    item = DashboardCardchecklistItem(
        card_id=dashboard_card.id, title="Evidência", done=False
    )
    db.add(item)
    db.commit()

    resp = client.delete(
        f"/api/v1/dashboard/checklist-items/{item.id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert resp.status_code == 403
    assert db.get(DashboardCardchecklistItem, item.id) is not None
