from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.company_dashboard import DashboardTemplate, DashboardTemplateCard


def _create_template_with_cards(db) -> DashboardTemplate:
    template = DashboardTemplate(name="Template Teste", is_default=True)
    db.add(template)
    db.flush()

    for i in range(3):
        db.add(
            DashboardTemplateCard(
                template_id=template.id,
                title=f"Card {i + 1}",
                tag=f"tag{i + 1}",
                sort_order=i,
            )
        )
    db.commit()
    db.refresh(template)
    return template


def test_onboarding_manual_dashboard_without_phone(
    client: TestClient, admin_token: str
):
    """Reproduz o cenário do item C.2.a: telefone omitido não deve mais
    quebrar com IntegrityError (Company.phone era NOT NULL)."""
    response = client.post(
        "/api/v1/onboarding/principal-user",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "full_name": "Cliente Sem Telefone",
            "company_name": "Empresa Sem Telefone",
            "email": "semtelefone@test.com",
            "phone": None,
            "template_id": None,
            "manual_dashboard": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["dashboard_cards_created"] == 0


def test_onboarding_with_template_creates_cards_without_control_code(
    client: TestClient,
    admin_token: str,
    db,
):
    """Reproduz o cenário do item C.2.b: onboarding com template (cards sem
    control_code) não deve mais quebrar com IntegrityError
    (DashboardCard.control_code era NOT NULL)."""
    template = _create_template_with_cards(db)

    response = client.post(
        "/api/v1/onboarding/principal-user",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "full_name": "Cliente Com Template",
            "company_name": "Empresa Com Template",
            "email": "comtemplate@test.com",
            "phone": "11999999999",
            "template_id": template.id,
            "manual_dashboard": False,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["dashboard_cards_created"] == 3


def test_onboarding_duplicate_email_returns_409(
    client: TestClient, admin_token: str, admin_user
):
    response = client.post(
        "/api/v1/onboarding/principal-user",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "full_name": "Duplicado",
            "company_name": "Empresa Duplicada",
            "email": "admin@test.com",  # mesmo e-mail do admin_user
            "phone": None,
            "template_id": None,
            "manual_dashboard": True,
        },
    )
    assert response.status_code == 409


def test_onboarding_concurrent_duplicate_returns_409_via_integrity_error(
    client: TestClient, admin_token: str, admin_user, monkeypatch,
):
    """Regressão do item I.4: numa condição de corrida real, uma segunda
    requisição concorrente passa pela checagem prévia de get_user_by_email()
    antes do primeiro commit (aqui simulado neutralizando a checagem) e só
    falha no INSERT, por violar a constraint UNIQUE de users.email. Deve
    retornar 409 via `except IntegrityError`, não 500. Sem essa checagem
    neutralizada, a mesma chamada dupla exercita só o pre-check síncrono
    (ver test_onboarding_duplicate_email_returns_409) e nunca chega no
    bloco `except IntegrityError` — motivo pelo qual este teste existe."""
    import app.api.v1.admin_onboarding as onboarding_module

    monkeypatch.setattr(onboarding_module, "get_user_by_email", lambda db, email: None)

    response = client.post(
        "/api/v1/onboarding/principal-user",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "full_name": "Duplicado Corrida",
            "company_name": "Empresa Corrida",
            "email": "admin@test.com",  # já existe (admin_user) — pre-check neutralizado acima
            "phone": None,
            "template_id": None,
            "manual_dashboard": True,
        },
    )
    assert response.status_code == 409
    assert "concorrente" in response.json()["detail"].lower()


def test_onboarding_requires_admin(client: TestClient, user_token: str):
    response = client.post(
        "/api/v1/onboarding/principal-user",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "full_name": "Teste",
            "company_name": "Empresa",
            "email": "teste@test.com",
            "phone": None,
            "template_id": None,
            "manual_dashboard": True,
        },
    )
    assert response.status_code == 403
