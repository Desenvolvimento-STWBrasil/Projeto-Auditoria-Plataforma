"""
M-20: cada endpoint de ESCRITA exercitado por cada papel que NÃO deveria
poder executá-lo.

Complementa os testes de caminho feliz. Os 4 achados de prioridade Alta
da rev. 8.0 de docs/relatorio_bugs.md estavam TODOS fora do caminho que
a UI percorre — e por isso nenhum teste os alcançava.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.policy import ALLOWED_ROLES, Action

ALL_ROLES = ["admin", "user", "sub-user"]

# (método, template de rota, corpo, papéis que DEVEM receber 403)
WRITE_ENDPOINTS = [
    (
        "PATCH",
        "/api/v1/dashboard/cards/{card_id}/status",
        {"status": "CONFORME"},
        ["user", "sub-user"],
    ),
    (
        "POST",
        "/api/v1/dashboard/cards/{card_id}/entries",
        {"entry_type": "HISTORY", "content": "x"},
        ["user", "sub-user"],
    ),
    (
        "POST",
        "/api/v1/dashboard/cards/{card_id}/entries",
        {"entry_type": "CHECKLIST", "content": "x"},
        ["user", "sub-user"],
    ),
    (
        "POST",
        "/api/v1/dashboard/cards/{card_id}/entries",
        {"entry_type": "CHAT_ANSWER", "content": "x"},
        ["user", "sub-user"],
    ),
    (
        "POST",
        "/api/v1/dashboard/cards/{card_id}/notes",
        {"content": "x"},
        ["user", "sub-user"],
    ),
    # ---- Quadro Kanban (PRD §4.4 / CA-11) ----
    (
        "PATCH",
        "/api/v1/dashboard/cards/{card_id}/move",
        {"column_id": None, "prev_card_id": None, "next_card_id": None},
        ["user", "sub-user"],
    ),
    (
        "PATCH",
        "/api/v1/dashboard/cards/{card_id}",
        {
            "title": "x",
            "description": None,
            "control_code": None,
            "category_id": None,
        },
        ["user", "sub-user"],
    ),
    (
        "PUT",
        "/api/v1/dashboard/cards/{card_id}/labels",
        {"label_ids": []},
        ["user", "sub-user"],
    ),
]

# Rotas de escrita do quadro que NÃO são endereçadas por card_id — têm
# template próprio porque a formatação da URL é diferente.
COLUMN_WRITE_ENDPOINTS = [
    (
        "POST",
        "/api/v1/dashboard/companies/{company_id}/columns",
        {"name": "Nova", "kind": "COLUMN", "after_column_id": None},
        ["user", "sub-user"],
    ),
]

# Rotas endereçadas por ITEM DE CHECKLIST. Template próprio pelo mesmo
# motivo das colunas: a URL não leva `card_id`.
#
# O `toggle` já existia e nunca esteve nesta matriz — a decisão "só o
# auditor mexe no checklist" (B-A23) valia na prática, por causa do
# `require_admin` no router, mas não estava fixada em teste nenhum.
CHECKLIST_ITEM_WRITE_ENDPOINTS = [
    (
        "PATCH",
        "/api/v1/dashboard/checklist-items/{item_id}/toggle",
        ["user", "sub-user"],
    ),
    (
        "DELETE",
        "/api/v1/dashboard/checklist-items/{item_id}",
        ["user", "sub-user"],
    ),
]

LABEL_WRITE_ENDPOINTS = [
    (
        "POST",
        "/api/v1/admin/dashboard-labels",
        {"name": "X", "color": "#000000", "sort_order": 0},
        ["user", "sub-user"],
    ),
]


@pytest.mark.parametrize("method,route,body,forbidden_roles", WRITE_ENDPOINTS)
def test_write_endpoint_rejects_forbidden_roles(
    method,
    route,
    body,
    forbidden_roles,
    client: TestClient,
    user_token: str,
    sub_user_token: str,
    dashboard_card,
):
    tokens = {"user": user_token, "sub-user": sub_user_token}
    url = route.format(card_id=dashboard_card.id)

    for role in forbidden_roles:
        response = client.request(
            method,
            url,
            json=body,
            headers={"Authorization": f"Bearer {tokens[role]}"},
        )
        assert response.status_code == 403, (
            f"{method} {url} aceitou escrita do papel '{role}' "
            f"(status {response.status_code}) — ver B-A23"
        )


@pytest.mark.parametrize("method,route,body,forbidden_roles", COLUMN_WRITE_ENDPOINTS)
def test_column_write_endpoint_rejects_forbidden_roles(
    method,
    route,
    body,
    forbidden_roles,
    client: TestClient,
    user_token: str,
    sub_user_token: str,
    company,
    dashboard_column,
):
    tokens = {"user": user_token, "sub-user": sub_user_token}
    url = route.format(company_id=company.id, column_id=dashboard_column.id)

    for role in forbidden_roles:
        response = client.request(
            method,
            url,
            json=body,
            headers={"Authorization": f"Bearer {tokens[role]}"},
        )
        assert response.status_code == 403, (
            f"{method} {url} aceitou escrita do papel '{role}' "
            f"(status {response.status_code}) — ver PRD §4.4"
        )


@pytest.mark.parametrize(
    "method,route,body",
    [
        (
            "PATCH",
            "/api/v1/dashboard/columns/{column_id}",
            {"name": "X", "hidden": False, "wip_limit": None},
        ),
        (
            "PATCH",
            "/api/v1/dashboard/columns/{column_id}/move",
            {"prev_column_id": None, "next_column_id": None},
        ),
        ("DELETE", "/api/v1/dashboard/columns/{column_id}", None),
    ],
)
@pytest.mark.parametrize("role", ["user", "sub-user"])
def test_column_mutations_reject_client_roles(
    method,
    route,
    body,
    role,
    client: TestClient,
    user_token: str,
    sub_user_token: str,
    dashboard_column,
):
    """
    Estas três rotas passam por `require_admin` ANTES do escopo, então o
    cliente recebe 403 — e não 404. É a ordem de `update_card_status`, e
    é o que garante que papel errado e tenant errado tenham respostas
    distintas e corretas.
    """
    tokens = {"user": user_token, "sub-user": sub_user_token}
    url = route.format(column_id=dashboard_column.id)

    response = client.request(
        method, url, json=body, headers={"Authorization": f"Bearer {tokens[role]}"}
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "method,route,forbidden_roles", CHECKLIST_ITEM_WRITE_ENDPOINTS
)
def test_checklist_item_write_rejects_forbidden_roles(
    method,
    route,
    forbidden_roles,
    client: TestClient,
    db,
    user_token: str,
    sub_user_token: str,
    dashboard_card,
):
    """O checklist é registro interno da equipe de auditoria: o cliente não
    o lê (B-A28) e, com mais razão, não o marca nem o apaga (B-A23)."""
    from app.models.company_dashboard import DashboardCardchecklistItem

    item = DashboardCardchecklistItem(
        card_id=dashboard_card.id, title="Evidência", done=False
    )
    db.add(item)
    db.commit()

    tokens = {"user": user_token, "sub-user": sub_user_token}
    url = route.format(item_id=item.id)

    for role in forbidden_roles:
        response = client.request(
            method, url, headers={"Authorization": f"Bearer {tokens[role]}"}
        )
        assert response.status_code == 403, (
            f"{method} {url} aceitou escrita do papel '{role}' "
            f"(status {response.status_code}) — ver B-A23"
        )
    # O item sobreviveu às tentativas.
    assert db.get(DashboardCardchecklistItem, item.id) is not None


@pytest.mark.parametrize("method,route,body,forbidden_roles", LABEL_WRITE_ENDPOINTS)
def test_label_write_endpoint_rejects_forbidden_roles(
    method,
    route,
    body,
    forbidden_roles,
    client: TestClient,
    user_token: str,
    sub_user_token: str,
):
    tokens = {"user": user_token, "sub-user": sub_user_token}

    for role in forbidden_roles:
        response = client.request(
            method,
            route,
            json=body,
            headers={"Authorization": f"Bearer {tokens[role]}"},
        )
        assert response.status_code == 403


def test_client_can_still_ask_question_in_card_chat(
    client: TestClient, user_token: str, dashboard_card
):
    """A restrição de B-A23 não pode fechar o canal legítimo do cliente."""
    response = client.post(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/entries",
        json={"entry_type": "CHAT_QUESTION", "content": "Qual evidência enviar?"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 201


def test_client_cannot_toggle_checklist_item(
    client: TestClient, user_token: str, db, dashboard_card
):
    from app.models.company_dashboard import DashboardCardchecklistItem

    item = DashboardCardchecklistItem(
        card_id=dashboard_card.id, title="Conferir política", done=False
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    response = client.patch(
        f"/api/v1/dashboard/checklist-items/{item.id}/toggle",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------- LEITURA
#
# M-23: leitura sensível também é decisão de política. A matriz nasceu
# cobrindo só escrita — e por isso B-A28 (o cliente lendo o checklist
# interno do auditor) passou por ela sem ser notado.
#
# (rota, papéis que NÃO podem ver, campos que não podem vir preenchidos)
# `campos_vedados = None` significa "a rota inteira é vedada" (403).
# Uma lista de campos significa "a rota é permitida, mas estes campos
# voltam vazios" — o cliente tem direito ao card, não ao trabalho interno
# do auditor sobre ele.
READ_ENDPOINTS = [
    (
        "/api/v1/dashboard/cards/{card_id}",
        ["user", "sub-user"],
        ["checklist", "history"],
    ),
    (
        "/api/v1/dashboard/cards/{card_id}/notes",
        ["user", "sub-user"],
        None,
    ),
]


@pytest.mark.parametrize("route,forbidden_roles,campos_vedados", READ_ENDPOINTS)
def test_read_endpoint_hides_internals_from_forbidden_roles(
    route,
    forbidden_roles,
    campos_vedados,
    client: TestClient,
    db,
    admin_user,
    user_token: str,
    sub_user_token: str,
    dashboard_card,
):
    from app.models.company_dashboard import (
        DashboardCardchecklistItem,
        DashboardCardHistoryEntry,
    )

    db.add(
        DashboardCardchecklistItem(
            card_id=dashboard_card.id, title="INTERNO checklist", done=False
        )
    )
    db.add(
        DashboardCardHistoryEntry(
            card_id=dashboard_card.id,
            action="INTERNO historico",
            actor_user_id=admin_user.id,
        )
    )
    db.commit()

    tokens = {"user": user_token, "sub-user": sub_user_token}
    url = route.format(card_id=dashboard_card.id)

    for role in forbidden_roles:
        response = client.get(url, headers={"Authorization": f"Bearer {tokens[role]}"})
        if campos_vedados is None:
            assert response.status_code == 403, (
                f"GET {url} devolveu {response.status_code} para o papel "
                f"'{role}' — esperado 403"
            )
            continue

        assert response.status_code == 200
        corpo = response.json()
        for campo in campos_vedados:
            assert corpo[campo] == [], (
                f"GET {url} devolveu '{campo}' preenchido para o papel "
                f"'{role}' — ver B-A28"
            )
        assert "INTERNO" not in response.text


@pytest.mark.parametrize("role", ["admin", "user", "sub-user"])
def test_board_read_is_allowed_for_every_role(
    role,
    client: TestClient,
    admin_token: str,
    user_token: str,
    sub_user_token: str,
    company,
    dashboard_column,
):
    """
    M-23 exige que a decisão de leitura seja REGISTRADA, inclusive quando
    ela é "permitido para todos". `GET …/board` é leitura da própria
    empresa: o cliente vê o quadro com as colunas na ordem que o auditor
    montou (U6), e só não consegue rearranjá-lo.

    Sem esta linha explícita, "todos podem ler o quadro" ficaria sendo
    uma propriedade acidental do código em vez de uma decisão.
    """
    tokens = {
        "admin": admin_token,
        "user": user_token,
        "sub-user": sub_user_token,
    }
    response = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board",
        headers={"Authorization": f"Bearer {tokens[role]}"},
    )
    assert response.status_code == 200


@pytest.mark.parametrize("action", list(Action))
def test_every_action_has_an_explicit_decision(action: Action):
    """
    Nenhuma ação pode ficar sem decisão declarada. Um `Action` novo
    acrescentado sem a linha correspondente em ALLOWED_ROLES falha aqui,
    em vez de silenciosamente permitir (ou negar) tudo.
    """
    assert action in ALLOWED_ROLES, f"{action.value} não tem papéis declarados"
    assert isinstance(ALLOWED_ROLES[action], frozenset)
    assert ALLOWED_ROLES[action] <= set(ALL_ROLES), (
        f"{action.value} declara papel desconhecido: "
        f"{ALLOWED_ROLES[action] - set(ALL_ROLES)}"
    )
