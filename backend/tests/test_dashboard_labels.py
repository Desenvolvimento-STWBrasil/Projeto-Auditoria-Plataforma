"""
CA-12: etiqueta é criticidade, status é conformidade — e nunca o
contrário.

A regra que este arquivo protege é a de B-A23. O quadro de referência
tinha uma etiqueta `Concluído com evidência` que responde à MESMA
pergunta que `DashboardCardStatus.CONFORME`. Duas fontes de verdade para
"este controle está conforme?" é o defeito, não a etiqueta: por isso ela
ficou fora do vocabulário semeado, e por isso o teste abaixo verifica
explicitamente que etiquetar um card não mexe no status dele.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.company_dashboard import DashboardCardStatus


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _criar_etiqueta(client: TestClient, token: str, nome: str, cor: str = "#96311D"):
    resposta = client.post(
        "/api/v1/admin/dashboard-labels",
        json={"name": nome, "color": cor, "sort_order": 0},
        headers=_headers(token),
    )
    assert resposta.status_code == 201
    return resposta.json()


def test_crud_de_etiqueta(client: TestClient, admin_token: str):
    criada = _criar_etiqueta(client, admin_token, "Item Critico")
    assert criada["color"] == "#96311D"

    listadas = client.get(
        "/api/v1/admin/dashboard-labels", headers=_headers(admin_token)
    )
    assert listadas.status_code == 200
    assert [e["name"] for e in listadas.json()] == ["Item Critico"]

    editada = client.patch(
        f"/api/v1/admin/dashboard-labels/{criada['id']}",
        json={"name": "Crítico", "color": "#000000", "sort_order": 2},
        headers=_headers(admin_token),
    )
    assert editada.status_code == 200
    assert editada.json()["name"] == "Crítico"

    excluida = client.delete(
        f"/api/v1/admin/dashboard-labels/{criada['id']}",
        headers=_headers(admin_token),
    )
    assert excluida.status_code == 204


def test_nome_duplicado_devolve_409(client: TestClient, admin_token: str):
    _criar_etiqueta(client, admin_token, "Alta Criticidade")

    repetida = client.post(
        "/api/v1/admin/dashboard-labels",
        json={"name": "Alta Criticidade", "color": "#C2410C", "sort_order": 1},
        headers=_headers(admin_token),
    )
    assert repetida.status_code == 409


def test_etiqueta_inexistente_devolve_404(client: TestClient, admin_token: str):
    resposta = client.patch(
        "/api/v1/admin/dashboard-labels/9999",
        json={"name": "X", "color": "#000000", "sort_order": 0},
        headers=_headers(admin_token),
    )
    assert resposta.status_code == 404


def test_excluir_etiqueta_em_uso_devolve_409(
    client: TestClient, admin_token: str, dashboard_card
):
    """Mesma regra de `CategoryInUseError`: exclusão bloqueada, não em
    cascata."""
    etiqueta = _criar_etiqueta(client, admin_token, "Em uso")

    client.put(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/labels",
        json={"label_ids": [etiqueta["id"]]},
        headers=_headers(admin_token),
    )

    resposta = client.delete(
        f"/api/v1/admin/dashboard-labels/{etiqueta['id']}",
        headers=_headers(admin_token),
    )
    assert resposta.status_code == 409
    assert "em uso" in resposta.json()["detail"].lower()


def test_put_substitui_o_conjunto_inteiro_de_etiquetas(
    client: TestClient, admin_token: str, dashboard_card, etiquetas
):
    """Semântica de PUT, não de PATCH: a lista enviada É o conjunto."""
    primeiro, segundo, terceiro = etiquetas

    client.put(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/labels",
        json={"label_ids": [primeiro.id, segundo.id]},
        headers=_headers(admin_token),
    )

    resposta = client.put(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/labels",
        json={"label_ids": [terceiro.id]},
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 200
    assert [e["name"] for e in resposta.json()] == ["Baixa Criticidade"]


def test_lista_vazia_remove_todas_as_etiquetas(
    client: TestClient, admin_token: str, dashboard_card, etiquetas
):
    client.put(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/labels",
        json={"label_ids": [etiquetas[0].id]},
        headers=_headers(admin_token),
    )

    resposta = client.put(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/labels",
        json={"label_ids": []},
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_id_de_etiqueta_inexistente_devolve_404_sem_aplicar_nada(
    client: TestClient, db, admin_token: str, dashboard_card, etiquetas
):
    """
    Todos os ids são validados ANTES de tocar no vínculo: uma lista com um
    id inválido no meio não pode deixar o card com metade das etiquetas.
    """
    resposta = client.put(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/labels",
        json={"label_ids": [etiquetas[0].id, 999999]},
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 404
    db.expire_all()
    assert db.get(type(dashboard_card), dashboard_card.id).labels == []


def test_etiquetar_nao_altera_o_status_do_card(
    client: TestClient, db, admin_token: str, dashboard_card, etiquetas
):
    """
    CA-12. Etiqueta responde "quão crítico é"; status responde "está
    conforme". Misturar os dois recriaria B-A23.
    """
    status_antes = dashboard_card.status

    client.put(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/labels",
        json={"label_ids": [etiquetas[0].id]},
        headers=_headers(admin_token),
    )

    db.expire_all()
    card = db.get(type(dashboard_card), dashboard_card.id)
    assert card.status == status_antes == DashboardCardStatus.EM_ANALISE


def test_cliente_nao_acessa_o_crud_de_etiquetas(client: TestClient, user_token: str):
    resposta = client.get(
        "/api/v1/admin/dashboard-labels", headers=_headers(user_token)
    )
    assert resposta.status_code == 403
