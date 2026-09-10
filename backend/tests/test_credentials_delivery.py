"""
B-A29 / M-22: a senha temporária nunca pode se perder, e uma falha de
SMTP nunca pode derrubar uma transação já committada.

O modo de falha que estes testes cobrem é silencioso: sem SMTP, a senha
era gerada, hasheada e descartada. A empresa e o dashboard existiam, e
ninguém conseguia entrar na conta — sem erro, sem log, sem sintoma.
"""

from __future__ import annotations

import smtplib

import pytest

from app.core.config import settings
from app.models.company_dashboard import DashboardTemplate
from app.models.sub_user_request import SubUserRequest, SubUserRequestStatus
from app.services import email_sender

ONBOARDING_PAYLOAD = {
    "full_name": "Novo Cliente",
    "email": "novo@test.com",
    "company_name": "Nova Empresa",
}


@pytest.fixture
def template_padrao(db) -> DashboardTemplate:
    template = DashboardTemplate(name="Padrao", description=None, is_default=True)
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def _onboard(client, admin_token: str):
    return client.post(
        "/api/v1/onboarding/principal-user",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=ONBOARDING_PAYLOAD,
    )


# ------------------------------------------------------------- onboarding


def test_sem_smtp_a_senha_volta_na_resposta(
    client, admin_token, template_padrao, monkeypatch
):
    monkeypatch.setattr(settings, "SMTP_HOST", None)

    resposta = _onboard(client, admin_token)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["email_delivered"] is False
    assert corpo["temporary_password"], (
        "senha perdida: o cliente foi criado e ninguém consegue acessar a "
        "conta — ver B-A29"
    )
    assert len(corpo["temporary_password"]) == 12


def test_a_senha_devolvida_realmente_autentica(
    client, admin_token, template_padrao, monkeypatch
):
    """Não basta o campo vir preenchido — tem de ser a senha certa."""
    monkeypatch.setattr(settings, "SMTP_HOST", None)

    corpo = _onboard(client, admin_token).json()

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": ONBOARDING_PAYLOAD["email"],
            "password": corpo["temporary_password"],
        },
    )
    assert login.status_code == 200
    assert login.json()["access_token"]


def test_com_smtp_ok_a_senha_nao_trafega(
    client, admin_token, template_padrao, monkeypatch
):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.exemplo.local")
    monkeypatch.setattr(email_sender, "_enviar", lambda msg: True)

    corpo = _onboard(client, admin_token).json()

    assert corpo["email_delivered"] is True
    assert corpo["temporary_password"] is None


def test_falha_de_smtp_nao_derruba_o_onboarding(
    client, admin_token, template_padrao, monkeypatch
):
    """O usuário já foi committado — uma falha de SMTP não pode virar 500."""
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.inexistente.local")

    def _explode(*args, **kwargs):
        raise smtplib.SMTPException("servidor indisponível")

    monkeypatch.setattr(smtplib, "SMTP", _explode)

    resposta = _onboard(client, admin_token)

    assert resposta.status_code == 201, (
        "falha de SMTP virou erro de servidor, com o usuário já criado — "
        "o admin tentaria de novo e receberia 409"
    )
    corpo = resposta.json()
    assert corpo["email_delivered"] is False
    assert corpo["temporary_password"]


# ---------------------------------------------------- aprovação de sub-user


def _solicitacao_pendente(db, principal_user) -> SubUserRequest:
    pedido = SubUserRequest(
        principal_user_id=principal_user.id,
        requested_full_name="Sub Usuario Teste",
        request_email="sub.novo@test.com",
        status=SubUserRequestStatus.PENDING,
    )
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    return pedido


def test_aprovacao_sem_smtp_devolve_a_senha(
    client, db, admin_token, principal_user, monkeypatch
):
    monkeypatch.setattr(settings, "SMTP_HOST", None)
    pedido = _solicitacao_pendente(db, principal_user)

    resposta = client.post(
        f"/api/v1/sub-users/requests/{pedido.id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["email_delivered"] is False
    assert corpo["temporary_password"]
    assert corpo["status"] == "APPROVED"

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "sub.novo@test.com",
            "password": corpo["temporary_password"],
        },
    )
    assert login.status_code == 200


def test_aprovacao_com_smtp_ok_nao_devolve_a_senha(
    client, db, admin_token, principal_user, monkeypatch
):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.exemplo.local")
    monkeypatch.setattr(email_sender, "_enviar", lambda msg: True)
    pedido = _solicitacao_pendente(db, principal_user)

    corpo = client.post(
        f"/api/v1/sub-users/requests/{pedido.id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()

    assert corpo["email_delivered"] is True
    assert corpo["temporary_password"] is None
