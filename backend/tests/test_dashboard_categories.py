from __future__ import annotations

from fastapi.testclient import TestClient


def test_create_and_list_categories(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = client.post(
        "/api/v1/admin/dashboard-categories",
        headers=headers,
        json={"name": "Financeiro", "color": "#2C5A8C", "sort_order": 0},
    )
    assert resp.status_code == 201
    created = resp.json()
    assert created["name"] == "Financeiro"

    resp = client.get("/api/v1/admin/dashboard-categories", headers=headers)
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()]
    assert "Financeiro" in names


def test_create_category_duplicate_name_returns_409(
    client: TestClient, admin_token: str
):
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {"name": "Operacional", "color": "#1F6B4C", "sort_order": 0}

    first = client.post(
        "/api/v1/admin/dashboard-categories", headers=headers, json=payload
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/admin/dashboard-categories", headers=headers, json=payload
    )
    assert second.status_code == 409


def test_update_category(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    created = client.post(
        "/api/v1/admin/dashboard-categories",
        headers=headers,
        json={"name": "Vendas", "color": "#8A6114", "sort_order": 0},
    ).json()

    resp = client.patch(
        f"/api/v1/admin/dashboard-categories/{created['id']}",
        headers=headers,
        json={"name": "Comercial", "color": "#8A6114", "sort_order": 1},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Comercial"


def test_update_unknown_category_returns_404(client: TestClient, admin_token: str):
    resp = client.patch(
        "/api/v1/admin/dashboard-categories/999999",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "X", "color": "#000000", "sort_order": 0},
    )
    assert resp.status_code == 404


def test_delete_category_in_use_returns_409(
    client: TestClient, admin_token: str, db, dashboard_card
):
    headers = {"Authorization": f"Bearer {admin_token}"}
    created = client.post(
        "/api/v1/admin/dashboard-categories",
        headers=headers,
        json={"name": "Compliance", "color": "#96311D", "sort_order": 0},
    ).json()

    dashboard_card.category_id = created["id"]
    db.commit()

    resp = client.delete(
        f"/api/v1/admin/dashboard-categories/{created['id']}", headers=headers
    )
    assert resp.status_code == 409


def test_delete_unused_category_succeeds(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    created = client.post(
        "/api/v1/admin/dashboard-categories",
        headers=headers,
        json={"name": "Categoria Descartável", "color": "#000000", "sort_order": 0},
    ).json()

    resp = client.delete(
        f"/api/v1/admin/dashboard-categories/{created['id']}", headers=headers
    )
    assert resp.status_code == 204


def test_categories_require_admin(client: TestClient, user_token: str):
    resp = client.get(
        "/api/v1/admin/dashboard-categories",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403
