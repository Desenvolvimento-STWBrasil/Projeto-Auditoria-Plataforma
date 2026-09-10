from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.company_dashboard import Company


def test_request_sub_user_success(client: TestClient, user_token: str):
    response = client.post(
        "/api/v1/sub-users/requests",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"requested_full_name": "Sub Usuário", "request_email": "sub@test.com"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "PENDING"
    assert data["request_email"] == "sub@test.com"


def test_request_sub_user_requires_principal_role(client: TestClient, admin_token: str):
    response = client.post(
        "/api/v1/sub-users/requests",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"requested_full_name": "Sub Usuário", "request_email": "sub@test.com"},
    )
    assert response.status_code == 403


def test_approve_sub_user_request(
    client: TestClient, admin_token: str, user_token: str
):
    create_resp = client.post(
        "/api/v1/sub-users/requests",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"requested_full_name": "Sub Usuário", "request_email": "sub2@test.com"},
    )
    request_id = create_resp.json()["id"]

    approve_resp = client.post(
        f"/api/v1/sub-users/requests/{request_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert approve_resp.status_code == 200
    data = approve_resp.json()
    assert data["status"] == "APPROVED"
    assert data["sub_user_email"] == "sub2@test.com"


def test_double_approve_returns_400_not_500(
    client: TestClient,
    admin_token: str,
    user_token: str,
):
    """Reproduz o cenário do item A.12 (race condition corrigida com
    with_for_update): a segunda aprovação da mesma solicitação deve
    retornar 400 'Solicitação já processada', não criar um segundo
    sub-usuário nem estourar 500."""
    create_resp = client.post(
        "/api/v1/sub-users/requests",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"requested_full_name": "Sub Usuário", "request_email": "sub3@test.com"},
    )
    request_id = create_resp.json()["id"]

    first = client.post(
        f"/api/v1/sub-users/requests/{request_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v1/sub-users/requests/{request_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert second.status_code == 400


def test_reject_sub_user_request(
    client: TestClient, admin_token: str, user_token: str
):
    create_resp = client.post(
        "/api/v1/sub-users/requests",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"requested_full_name": "Sub Usuário", "request_email": "sub5@test.com"},
    )
    request_id = create_resp.json()["id"]

    reject_resp = client.post(
        f"/api/v1/sub-users/requests/{request_id}/reject",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reject_resp.status_code == 200
    data = reject_resp.json()
    assert data["status"] == "REJECTED"

    # Não deve ter criado nenhum usuário para o e-mail recusado.
    me_resp = client.get(
        "/api/v1/sub-users/requests/me",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    request = next(
        r for r in me_resp.json() if r["request_email"] == "sub5@test.com"
    )
    assert request["status"] == "REJECTED"


def test_reject_sub_user_request_requires_admin(
    client: TestClient, user_token: str
):
    create_resp = client.post(
        "/api/v1/sub-users/requests",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"requested_full_name": "Sub Usuário", "request_email": "sub6@test.com"},
    )
    request_id = create_resp.json()["id"]

    response = client.post(
        f"/api/v1/sub-users/requests/{request_id}/reject",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403


def test_double_reject_returns_400_not_500(
    client: TestClient, admin_token: str, user_token: str
):
    create_resp = client.post(
        "/api/v1/sub-users/requests",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"requested_full_name": "Sub Usuário", "request_email": "sub7@test.com"},
    )
    request_id = create_resp.json()["id"]

    first = client.post(
        f"/api/v1/sub-users/requests/{request_id}/reject",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v1/sub-users/requests/{request_id}/reject",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert second.status_code == 400


def test_list_pending_requests_requires_admin(client: TestClient, user_token: str):
    response = client.get(
        "/api/v1/sub-users/requests/pending",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403


def test_list_pending_requests_includes_company_name(
    client: TestClient, admin_token: str, user_token: str, company: Company
):
    """O admin precisa ver de qual empresa é cada solicitação pendente de
    sub-usuário, não só nome/e-mail do solicitado (ver plano_implementacao.md)."""
    client.post(
        "/api/v1/sub-users/requests",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"requested_full_name": "Sub Usuário", "request_email": "sub4@test.com"},
    )

    response = client.get(
        "/api/v1/sub-users/requests/pending",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    request = next(r for r in data if r["request_email"] == "sub4@test.com")
    assert request["company_name"] == company.name
