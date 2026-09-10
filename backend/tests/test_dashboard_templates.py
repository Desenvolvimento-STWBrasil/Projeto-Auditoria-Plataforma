from __future__ import annotations

from fastapi.testclient import TestClient


def _create_category(client: TestClient, headers: dict, name: str) -> int:
    resp = client.post(
        "/api/v1/admin/dashboard-categories",
        headers=headers,
        json={"name": name, "color": "#788c5d", "sort_order": 0},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_create_template_and_list_with_card_count(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    created = client.post(
        "/api/v1/admin/templates",
        headers=headers,
        json={"name": "Financeiro Padrão", "description": "Base", "is_default": False},
    )
    assert created.status_code == 201
    template_id = created.json()["id"]
    assert created.json()["card_count"] == 0

    listed = client.get("/api/v1/admin/templates", headers=headers)
    assert listed.status_code == 200
    assert any(t["id"] == template_id for t in listed.json())


def test_create_template_duplicate_name_returns_409(
    client: TestClient, admin_token: str
):
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {"name": "Template Único", "description": None, "is_default": False}

    first = client.post("/api/v1/admin/templates", headers=headers, json=payload)
    assert first.status_code == 201

    second = client.post("/api/v1/admin/templates", headers=headers, json=payload)
    assert second.status_code == 409


def test_setting_new_default_clears_previous_default(
    client: TestClient, admin_token: str
):
    headers = {"Authorization": f"Bearer {admin_token}"}

    first = client.post(
        "/api/v1/admin/templates",
        headers=headers,
        json={"name": "Template A", "description": None, "is_default": True},
    ).json()
    second = client.post(
        "/api/v1/admin/templates",
        headers=headers,
        json={"name": "Template B", "description": None, "is_default": True},
    ).json()

    detail_first = client.get(
        f"/api/v1/admin/templates/{first['id']}", headers=headers
    ).json()
    detail_second = client.get(
        f"/api/v1/admin/templates/{second['id']}", headers=headers
    ).json()

    assert detail_first["is_default"] is False
    assert detail_second["is_default"] is True


def test_cannot_delete_default_template(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    template = client.post(
        "/api/v1/admin/templates",
        headers=headers,
        json={"name": "Template Padrão", "description": None, "is_default": True},
    ).json()

    resp = client.delete(f"/api/v1/admin/templates/{template['id']}", headers=headers)
    assert resp.status_code == 409


def test_add_update_and_remove_template_card(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    category_id = _create_category(client, headers, "Financeiro")
    template = client.post(
        "/api/v1/admin/templates",
        headers=headers,
        json={"name": "Template com cards", "description": None, "is_default": False},
    ).json()

    card = client.post(
        f"/api/v1/admin/templates/{template['id']}/cards",
        headers=headers,
        json={
            "title": "Fluxo de caixa mensal",
            "description": "Relatório mensal de fluxo de caixa",
            "category_id": category_id,
            "sort_order": 0,
        },
    )
    assert card.status_code == 201
    card_id = card.json()["id"]
    assert card.json()["category_name"] == "Financeiro"

    detail = client.get(
        f"/api/v1/admin/templates/{template['id']}", headers=headers
    ).json()
    assert detail["card_count"] == 1

    updated = client.patch(
        f"/api/v1/admin/templates/template-cards/{card_id}",
        headers=headers,
        json={
            "title": "Fluxo de caixa mensal (revisado)",
            "description": "Atualizado",
            "category_id": category_id,
            "sort_order": 0,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Fluxo de caixa mensal (revisado)"

    deleted = client.delete(
        f"/api/v1/admin/templates/template-cards/{card_id}", headers=headers
    )
    assert deleted.status_code == 204

    detail_after = client.get(
        f"/api/v1/admin/templates/{template['id']}", headers=headers
    ).json()
    assert detail_after["card_count"] == 0


def test_templates_require_admin(client: TestClient, user_token: str):
    resp = client.get(
        "/api/v1/admin/templates",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403


def test_delete_template_in_use_returns_409(
    client: TestClient, admin_token: str, db, company, dashboard
):
    """B-A25: excluir um template já aplicado apagaria (ON DELETE SET NULL)
    o vínculo de origem de todos os cards derivados."""
    from app.models.company_dashboard import DashboardCardCategory

    category = DashboardCardCategory(name="Probe", color="#000000", sort_order=0)
    db.add(category)
    db.commit()

    headers = {"Authorization": f"Bearer {admin_token}"}
    template = client.post(
        "/api/v1/admin/templates",
        json={"name": "Template Em Uso", "description": None, "is_default": False},
        headers=headers,
    ).json()
    client.post(
        f"/api/v1/admin/templates/{template['id']}/cards",
        json={
            "title": "Card A",
            "description": None,
            "category_id": category.id,
            "sort_order": 0,
        },
        headers=headers,
    )
    client.post(
        f"/api/v1/dashboard/companies/{company.id}/apply-template",
        json={"template_id": template["id"]},
        headers=headers,
    )

    response = client.delete(
        f"/api/v1/admin/templates/{template['id']}", headers=headers
    )
    assert response.status_code == 409
    assert "em uso" in response.json()["detail"]


# ------------------------------------------- Quadro Kanban: CA-09 e CA-10


def _criar_template_com_coluna(client: TestClient, headers: dict) -> tuple[int, int]:
    template = client.post(
        "/api/v1/admin/templates",
        headers=headers,
        json={"name": "Due Diligence", "description": None, "is_default": False},
    ).json()

    coluna = client.post(
        f"/api/v1/admin/templates/{template['id']}/columns",
        headers=headers,
        json={"name": "Controle 5 - Organizacionais", "kind": "COLUMN"},
    )
    assert coluna.status_code == 201
    return template["id"], coluna.json()["id"]


def test_coluna_de_template_aparece_no_detalhe(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    template_id, coluna_id = _criar_template_com_coluna(client, headers)

    detalhe = client.get(f"/api/v1/admin/templates/{template_id}", headers=headers)

    assert detalhe.status_code == 200
    colunas = detalhe.json()["columns"]
    assert [c["id"] for c in colunas] == [coluna_id]
    assert colunas[0]["kind"] == "COLUMN"


def test_nome_de_coluna_duplicado_no_mesmo_template_devolve_409(
    client: TestClient, admin_token: str
):
    headers = {"Authorization": f"Bearer {admin_token}"}
    template_id, _coluna_id = _criar_template_com_coluna(client, headers)

    repetida = client.post(
        f"/api/v1/admin/templates/{template_id}/columns",
        headers=headers,
        json={"name": "Controle 5 - Organizacionais", "kind": "COLUMN"},
    )
    assert repetida.status_code == 409


def test_excluir_coluna_de_template_com_card_devolve_409(
    client: TestClient, admin_token: str
):
    headers = {"Authorization": f"Bearer {admin_token}"}
    template_id, coluna_id = _criar_template_com_coluna(client, headers)

    client.post(
        f"/api/v1/admin/templates/{template_id}/cards",
        headers=headers,
        json={
            "title": "Política de SI",
            "description": None,
            "category_id": None,
            "template_column_id": coluna_id,
            "sort_order": 0,
        },
    )

    resposta = client.delete(
        f"/api/v1/admin/templates/{template_id}/columns/{coluna_id}", headers=headers
    )
    assert resposta.status_code == 409


def test_card_nao_pode_apontar_para_coluna_de_outro_template(
    client: TestClient, admin_token: str
):
    headers = {"Authorization": f"Bearer {admin_token}"}
    _template_a, coluna_a = _criar_template_com_coluna(client, headers)

    template_b = client.post(
        "/api/v1/admin/templates",
        headers=headers,
        json={"name": "Outro Template", "description": None, "is_default": False},
    ).json()

    resposta = client.post(
        f"/api/v1/admin/templates/{template_b['id']}/cards",
        headers=headers,
        json={
            "title": "Card do B",
            "description": None,
            "category_id": None,
            "template_column_id": coluna_a,
            "sort_order": 0,
        },
    )
    assert resposta.status_code == 404


def test_aplicar_template_com_colunas_duas_vezes_e_idempotente(
    client: TestClient, admin_token: str, company, dashboard
):
    """
    CA-09. A idempotência de coluna repousa na MESMA `UniqueConstraint`
    que a de card — `uq_dashboard_column_origin_per_dashboard`. Sem ela, a
    segunda aplicação duplicaria as 25 colunas do quadro real (R2).
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    template_id, coluna_id = _criar_template_com_coluna(client, headers)

    for titulo in ("Política de SI", "Inventário de Ativos"):
        client.post(
            f"/api/v1/admin/templates/{template_id}/cards",
            headers=headers,
            json={
                "title": titulo,
                "description": None,
                "category_id": None,
                "template_column_id": coluna_id,
                "sort_order": 0,
            },
        )

    primeira = client.post(
        f"/api/v1/dashboard/companies/{company.id}/apply-template",
        headers=headers,
        json={"template_id": template_id},
    ).json()
    assert primeira["created_count"] == 2
    assert primeira["columns_created_count"] == 1

    segunda = client.post(
        f"/api/v1/dashboard/companies/{company.id}/apply-template",
        headers=headers,
        json={"template_id": template_id},
    ).json()
    assert segunda["created_count"] == 0
    assert segunda["columns_created_count"] == 0

    quadro = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board", headers=headers
    ).json()
    assert len(quadro["columns"]) == 1
    assert len(quadro["columns"][0]["cards"]) == 2


def test_aplicar_template_copia_a_descricao_para_o_card_da_empresa(
    client: TestClient, admin_token: str, company, dashboard
):
    """
    CA-10. Até esta entrega, `apply_template_to_company` copiava
    título/tag/categoria e DESCARTAVA a descrição em silêncio — 68 % dos
    cards do quadro real perderiam o texto normativo do controle.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    template_id, coluna_id = _criar_template_com_coluna(client, headers)

    texto = "**Controle** — Convém que a política de segurança seja aprovada."
    client.post(
        f"/api/v1/admin/templates/{template_id}/cards",
        headers=headers,
        json={
            "title": "Política de SI",
            "description": texto,
            "category_id": None,
            "template_column_id": coluna_id,
            "sort_order": 0,
        },
    )

    client.post(
        f"/api/v1/dashboard/companies/{company.id}/apply-template",
        headers=headers,
        json={"template_id": template_id},
    )

    quadro = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board", headers=headers
    ).json()
    assert quadro["columns"][0]["cards"][0]["description"] == texto


def test_aplicar_template_posiciona_o_card_na_coluna_correspondente(
    client: TestClient, admin_token: str, company, dashboard
):
    headers = {"Authorization": f"Bearer {admin_token}"}
    template_id, coluna_id = _criar_template_com_coluna(client, headers)

    client.post(
        f"/api/v1/admin/templates/{template_id}/cards",
        headers=headers,
        json={
            "title": "Card com coluna",
            "description": None,
            "category_id": None,
            "template_column_id": coluna_id,
            "sort_order": 0,
        },
    )
    client.post(
        f"/api/v1/admin/templates/{template_id}/cards",
        headers=headers,
        json={
            "title": "Card sem coluna",
            "description": None,
            "category_id": None,
            "template_column_id": None,
            "sort_order": 1,
        },
    )

    client.post(
        f"/api/v1/dashboard/companies/{company.id}/apply-template",
        headers=headers,
        json={"template_id": template_id},
    )

    quadro = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board", headers=headers
    ).json()
    assert [c["title"] for c in quadro["columns"][0]["cards"]] == ["Card com coluna"]
    assert [c["title"] for c in quadro["uncolumned"]] == ["Card sem coluna"]
