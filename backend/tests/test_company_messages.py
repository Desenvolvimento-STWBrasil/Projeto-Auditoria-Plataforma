from __future__ import annotations

from fastapi.testclient import TestClient


def test_admin_sends_and_client_reads_message(
    client: TestClient, admin_token: str, user_token: str, company
):
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_client = {"Authorization": f"Bearer {user_token}"}

    send = client.post(
        f"/api/v1/companies/{company.id}/messages",
        headers=headers_admin,
        json={"content": "Olá, tudo pronto para a próxima auditoria?"},
    )
    assert send.status_code == 201
    data = send.json()
    assert data["content"] == "Olá, tudo pronto para a próxima auditoria?"
    assert data["is_from_admin"] is True

    listed = client.get(
        f"/api/v1/companies/{company.id}/messages", headers=headers_client
    )
    assert listed.status_code == 200
    messages = listed.json()
    assert len(messages) == 1
    assert messages[0]["content"] == "Olá, tudo pronto para a próxima auditoria?"


def test_sub_user_can_read_and_send_company_messages(
    client: TestClient, sub_user_token: str, company
):
    headers = {"Authorization": f"Bearer {sub_user_token}"}

    send = client.post(
        f"/api/v1/companies/{company.id}/messages",
        headers=headers,
        json={"content": "Já enviei a evidência do controle 5.1"},
    )
    assert send.status_code == 201
    assert send.json()["is_from_admin"] is False

    listed = client.get(f"/api/v1/companies/{company.id}/messages", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_client_from_other_company_cannot_access_messages(
    client: TestClient, db, company
):
    from app.core.jwt import create_access_token
    from app.core.security import hash_password
    from app.models.user import User

    outro_principal = User(
        full_name="Outro Cliente",
        email="outro-principal@test.com",
        password_hash=hash_password("Outro123!"),
        role="user",
    )
    db.add(outro_principal)
    db.commit()
    db.refresh(outro_principal)
    outro_token = create_access_token(subject=str(outro_principal.id), role="user")

    response = client.get(
        f"/api/v1/companies/{company.id}/messages",
        headers={"Authorization": f"Bearer {outro_token}"},
    )
    # 404, não 403 (B-B23): responder 403 confirmaria que o company_id
    # existe, permitindo enumerar as empresas da plataforma.
    assert response.status_code == 404


def test_send_empty_message_is_rejected(client: TestClient, admin_token: str, company):
    response = client.post(
        f"/api/v1/companies/{company.id}/messages",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"content": ""},
    )
    assert response.status_code == 422


def test_unread_count_and_mark_as_read(
    client: TestClient, admin_token: str, user_token: str, company
):
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_client = {"Authorization": f"Bearer {user_token}"}

    client.post(
        f"/api/v1/companies/{company.id}/messages",
        headers=headers_admin,
        json={"content": "Mensagem 1"},
    )
    client.post(
        f"/api/v1/companies/{company.id}/messages",
        headers=headers_admin,
        json={"content": "Mensagem 2"},
    )

    unread = client.get(
        f"/api/v1/companies/{company.id}/messages/unread-count",
        headers=headers_client,
    )
    assert unread.status_code == 200
    assert unread.json()["unread_count"] == 2

    marked = client.patch(
        f"/api/v1/companies/{company.id}/messages/read", headers=headers_client
    )
    assert marked.status_code == 200
    assert marked.json()["marked_as_read"] == 2

    unread_after = client.get(
        f"/api/v1/companies/{company.id}/messages/unread-count",
        headers=headers_client,
    )
    assert unread_after.json()["unread_count"] == 0


def test_company_messages_require_authentication(client: TestClient, company):
    response = client.get(f"/api/v1/companies/{company.id}/messages")
    assert response.status_code == 401


def test_get_my_company_returns_own_company(
    client: TestClient, user_token: str, company
):
    response = client.get(
        "/api/v1/companies/me",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == company.id


def test_get_my_company_rejects_admin(client: TestClient, admin_token: str):
    response = client.get(
        "/api/v1/companies/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 403


def test_admin_unread_count_aggregates_all_companies(
    client: TestClient, admin_token: str, user_token: str, company
):
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_client = {"Authorization": f"Bearer {user_token}"}

    client.post(
        f"/api/v1/companies/{company.id}/messages",
        headers=headers_client,
        json={"content": "Mensagem não lida 1"},
    )
    client.post(
        f"/api/v1/companies/{company.id}/messages",
        headers=headers_client,
        json={"content": "Mensagem não lida 2"},
    )

    unread = client.get(
        "/api/v1/companies/unread-count", headers=headers_admin
    )
    assert unread.status_code == 200
    assert unread.json()["unread_count"] == 2

    client.patch(
        f"/api/v1/companies/{company.id}/messages/read", headers=headers_admin
    )

    unread_after = client.get(
        "/api/v1/companies/unread-count", headers=headers_admin
    )
    assert unread_after.json()["unread_count"] == 0


def test_admin_unread_count_rejects_non_admin(client: TestClient, user_token: str):
    response = client.get(
        "/api/v1/companies/unread-count",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403
