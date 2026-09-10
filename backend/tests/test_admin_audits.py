from __future__ import annotations

from fastapi.testclient import TestClient


def test_create_audit_success(
    client: TestClient,
    admin_token: str,
    principal_user,
    catalog_control,
):
    response = client.post(
        "/api/v1/admin/audits",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"client_user_id": principal_user.id, "name": "Auditoria ISO 2026"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Auditoria ISO 2026"
    assert data["client_user_id"] == principal_user.id
    assert data["status"] == "DRAFT"


def test_create_audit_requires_admin(
    client: TestClient, user_token: str, principal_user
):
    response = client.post(
        "/api/v1/admin/audits",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"client_user_id": principal_user.id, "name": "Auditoria Teste"},
    )
    assert response.status_code == 403


def test_list_audits_paginated_and_serializable(
    client: TestClient,
    admin_token: str,
    principal_user,
    catalog_control,
):
    # Este é o teste que teria pego o item B.6 nas duas vezes em que
    # regrediu: sem PaginatedResponse[AuditOut] devidamente parametrizado
    # (e items convertidos via AuditOut.model_validate), esta chamada
    # falha com 500 assim que existe ao menos uma auditoria no banco — o
    # caso "banco vazio" não expõe o bug, por isso o teste cria 2 antes.
    headers = {"Authorization": f"Bearer {admin_token}"}

    for name in ("Auditoria A", "Auditoria B"):
        create_resp = client.post(
            "/api/v1/admin/audits",
            headers=headers,
            json={"client_user_id": principal_user.id, "name": name},
        )
        assert create_resp.status_code == 201

    response = client.get("/api/v1/admin/audits?skip=0&limit=10", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["total"] >= 2
    assert data["skip"] == 0
    assert data["limit"] == 10
    assert len(data["items"]) >= 2
    for item in data["items"]:
        assert "id" in item
        assert "name" in item
        assert "client_user_id" in item
        assert "status" in item
        assert "created_at" in item


def test_list_audits_requires_admin(client: TestClient, user_token: str):
    response = client.get(
        "/api/v1/admin/audits", headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403


def test_list_audits_filters_by_company_id(
    client: TestClient,
    db,
    admin_token: str,
    principal_user,
    company,
):
    """O.2: GET /admin/audits?company_id= só retorna auditorias dos membros
    (principal + sub-usuários) daquela empresa."""
    from app.models.user import User
    from app.core.security import hash_password

    other_principal = User(
        full_name="Outro Cliente",
        email="outro@test.com",
        password_hash=hash_password("Outro123!"),
        role="user",
    )
    db.add(other_principal)
    db.commit()
    db.refresh(other_principal)

    headers = {"Authorization": f"Bearer {admin_token}"}

    resp_a = client.post(
        "/api/v1/admin/audits",
        headers=headers,
        json={"client_user_id": principal_user.id, "name": "Auditoria da Empresa"},
    )
    assert resp_a.status_code == 201

    resp_b = client.post(
        "/api/v1/admin/audits",
        headers=headers,
        json={
            "client_user_id": other_principal.id,
            "name": "Auditoria de Outra Empresa",
        },
    )
    assert resp_b.status_code == 201

    resp = client.get(
        f"/api/v1/admin/audits?company_id={company.id}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Auditoria da Empresa"


def test_list_audits_unknown_company_id_returns_404(
    client: TestClient, admin_token: str
):
    resp = client.get(
        "/api/v1/admin/audits?company_id=999999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404
