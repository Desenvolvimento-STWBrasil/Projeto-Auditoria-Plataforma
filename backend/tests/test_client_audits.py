from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.audit import Audit


def test_list_my_audits_returns_own_audits(
    client: TestClient, user_token: str, audit_with_control
):
    audit, _ = audit_with_control
    response = client.get(
        "/api/v1/client/audits",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == audit.id
    assert data[0]["name"] == audit.name


def test_list_my_audits_does_not_leak_other_clients_audits(
    client: TestClient, user_token: str, db, catalog_control
):
    other_client = Audit(name="Auditoria de Outro Cliente", client_user_id=999)
    db.add(other_client)
    db.commit()

    response = client.get(
        "/api/v1/client/audits",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_list_my_audits_requires_user_or_subuser(
    client: TestClient, admin_token: str
):
    response = client.get(
        "/api/v1/client/audits",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 403


def test_sub_user_lists_principal_audits(
    client: TestClient, sub_user_token: str, audit_with_control
):
    audit, _ = audit_with_control
    response = client.get(
        "/api/v1/client/audits",
        headers={"Authorization": f"Bearer {sub_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == audit.id


def test_get_my_audit_success(
    client: TestClient, user_token: str, audit_with_control
):
    audit, _ = audit_with_control
    response = client.get(
        f"/api/v1/client/audits/{audit.id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == audit.id
    assert data["client_user_id"] == audit.client_user_id


def test_get_my_audit_of_another_client_returns_404(
    client: TestClient, user_token: str, db
):
    other_audit = Audit(name="Auditoria de Outro Cliente", client_user_id=999)
    db.add(other_audit)
    db.commit()
    db.refresh(other_audit)

    response = client.get(
        f"/api/v1/client/audits/{other_audit.id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 404


def test_get_my_audit_unknown_id_returns_404(client: TestClient, user_token: str):
    response = client.get(
        "/api/v1/client/audits/999999",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 404
