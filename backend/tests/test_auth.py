from __future__ import annotations

from fastapi.testclient import TestClient


def test_login_success(client: TestClient, admin_user, admin_token: str):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "Admin123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient, admin_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "SenhaErrada123!"},
    )
    assert response.status_code == 401


def test_login_unknown_email(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "naoexiste@test.com", "password": "Qualquer123!"},
    )
    assert response.status_code == 401


def test_register_duplicate_email_returns_409(
    client: TestClient, admin_user, monkeypatch
):
    # Este teste é o que teria pego a regressão do item A.6 (get_user_by_email
    # sem `return`) na hora: se o bug voltar, a checagem de duplicidade
    # sempre retorna None e este teste falha com 201 em vez de 409.
    from app.core.config import settings

    monkeypatch.setattr(settings, "ALLOW_PUBLIC_REGISTRATION", True)

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Outro Nome",
            "email": "admin@test.com",  # mesmo e-mail do admin_user
            "password": "OutraSenha123!",
        },
    )
    assert response.status_code == 409


def test_register_success(client: TestClient, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ALLOW_PUBLIC_REGISTRATION", True)

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Novo Usuário",
            "email": "novo@test.com",
            "password": "SenhaForte123!",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "novo@test.com"
    assert data["role"] == "user"


def test_register_weak_password_rejected(client: TestClient, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ALLOW_PUBLIC_REGISTRATION", True)

    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Teste", "email": "fraco@test.com", "password": "123"},
    )
    assert response.status_code == 422


def test_register_returns_403_regardless_of_email_when_disabled(
    client: TestClient, admin_user, monkeypatch
):
    # Item I.1: com o registro público desabilitado, a resposta deve ser
    # sempre 403 (mesma checagem, mesma resposta), independente de o
    # e-mail já existir ou não — a checagem da flag ALLOW_PUBLIC_REGISTRATION
    # precisa vir ANTES da consulta de e-mail duplicado. Se a ordem for
    # invertida de novo, um e-mail já cadastrado voltaria a vazar um 409
    # em vez de 403, permitindo enumerar contas existentes.
    from app.core.config import settings

    monkeypatch.setattr(settings, "ALLOW_PUBLIC_REGISTRATION", False)

    resp_existing = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "X",
            "email": admin_user.email,  # e-mail já cadastrado
            "password": "Senha123",
        },
    )
    assert resp_existing.status_code == 403

    resp_new = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Y",
            "email": "novo-nao-cadastrado@test.com",
            "password": "Senha123",
        },
    )
    assert resp_new.status_code == 403
    assert resp_existing.json() == resp_new.json()


def test_perfil_requires_token(client: TestClient):
    response = client.get("/api/v1/users/perfil")
    assert response.status_code == 401


def test_perfil_with_valid_token(client: TestClient, admin_token: str):
    response = client.get(
        "/api/v1/users/perfil",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"
