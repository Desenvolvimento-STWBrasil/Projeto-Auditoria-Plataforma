from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_users_by_role_returns_matching_users(
    client: TestClient, admin_token: str, principal_user, sub_user
):
    response = client.get(
        "/api/v1/admin/users?role=user",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == principal_user.id
    assert data[0]["role"] == "user"
    # sub_user (role="sub-user") não deve aparecer no filtro role=user
    assert all(item["role"] == "user" for item in data)


def test_list_users_by_role_sub_user(
    client: TestClient, admin_token: str, sub_user
):
    response = client.get(
        "/api/v1/admin/users?role=sub-user",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == sub_user.id


def test_list_users_by_role_requires_admin(client: TestClient, user_token: str):
    response = client.get(
        "/api/v1/admin/users?role=user",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403


def test_list_users_by_role_rejects_invalid_role(
    client: TestClient, admin_token: str
):
    response = client.get(
        "/api/v1/admin/users?role=superadmin",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422
