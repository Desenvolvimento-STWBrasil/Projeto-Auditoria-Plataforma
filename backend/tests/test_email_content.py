"""
B-M27 / B-B22: cada papel recebe o e-mail que corresponde ao seu papel.

O onboarding reusava a função do sub-usuário, então todo cliente principal
recebia, como primeiro contato com a plataforma:

    Assunto: Acesso de sub-usuário - Plataforma de Auditoria
    OláMaria Silva,
    Você foi adicionado como sub-usuário de Construtora Alfa Ltda.

Três erros em quatro frases. Reuso de INFRAESTRUTURA (SMTP, TLS, erro) é
correto; reuso de CONTEÚDO endereçado a um papel é o destinatário errado
recebendo a mensagem de outro.
"""

from __future__ import annotations

from email.message import EmailMessage

import pytest

from app.core.config import settings
from app.services import email_sender


@pytest.fixture
def capturar_emails(monkeypatch) -> list[EmailMessage]:
    enviados: list[EmailMessage] = []
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.exemplo.local")
    monkeypatch.setattr(settings, "SMTP_FROM", "nao-responda@exemplo.local")
    monkeypatch.setattr(
        email_sender, "_enviar", lambda msg: (enviados.append(msg), True)[1]
    )
    return enviados


def test_email_do_principal_nao_diz_sub_usuario(capturar_emails):
    entregue = email_sender.send_principal_user_credentials_email(
        to_email="maria@cliente.com",
        full_name="Maria Silva",
        company_name="Construtora Alfa Ltda",
        temporary_password="Senha-Temp-12",
    )

    assert entregue is True
    msg = capturar_emails[0]
    corpo = msg.get_content()

    assert "sub-usuário" not in msg["Subject"].lower()
    assert "sub-usuário" not in corpo.lower()
    assert "Construtora Alfa Ltda" in corpo
    assert "Olá, Maria Silva" in corpo  # B-B22: com espaço e vírgula
    assert "Senha-Temp-12" in corpo
    assert msg["To"] == "maria@cliente.com"


def test_email_do_sub_usuario_continua_dizendo_sub_usuario(capturar_emails):
    """A correção de B-M27 não pode ter trocado os dois papéis de lugar."""
    entregue = email_sender.send_sub_user_credentials_email(
        to_email="joao@cliente.com",
        sub_user_name="João Souza",
        principal_name="Maria Silva",
        temporary_password="Senha-Temp-34",
    )

    assert entregue is True
    corpo = capturar_emails[0].get_content()

    assert "colaborador de Maria Silva" in corpo
    assert "Olá, João Souza" in corpo
    assert "Senha-Temp-34" in corpo


def test_as_duas_funcoes_sao_distintas():
    """
    A aplicação inicial de Q.2 renomeou a função do sub-usuário para o nome
    da função do principal, deixando DUAS definições com o mesmo nome no
    módulo — a segunda sobrescrevia a primeira e
    `send_sub_user_credentials_email` deixava de existir, quebrando o
    import de sub_users.py. Este teste torna isso impossível de repetir.
    """
    assert (
        email_sender.send_sub_user_credentials_email
        is not email_sender.send_principal_user_credentials_email
    )

    import inspect

    assert set(
        inspect.signature(email_sender.send_sub_user_credentials_email).parameters
    ) == {"to_email", "sub_user_name", "principal_name", "temporary_password"}
    assert set(
        inspect.signature(
            email_sender.send_principal_user_credentials_email
        ).parameters
    ) == {"to_email", "full_name", "company_name", "temporary_password"}


def test_sem_smtp_nenhuma_senha_vai_para_o_log(monkeypatch, capsys):
    monkeypatch.setattr(settings, "SMTP_HOST", None)

    entregue = email_sender.send_principal_user_credentials_email(
        to_email="maria@cliente.com",
        full_name="Maria Silva",
        company_name="Alfa",
        temporary_password="SENHA-SECRETA-99",
    )

    assert entregue is False
    saida = capsys.readouterr()
    assert "SENHA-SECRETA-99" not in saida.out
    assert "SENHA-SECRETA-99" not in saida.err


def test_falha_de_smtp_devolve_false_sem_propagar(monkeypatch):
    import smtplib

    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.exemplo.local")

    def _explode(*args, **kwargs):
        raise smtplib.SMTPException("conexão recusada")

    monkeypatch.setattr(smtplib, "SMTP", _explode)

    assert (
        email_sender.send_sub_user_credentials_email(
            to_email="joao@cliente.com",
            sub_user_name="João",
            principal_name="Maria",
            temporary_password="x",
        )
        is False
    )


def test_falha_de_rede_tambem_devolve_false(monkeypatch):
    """OSError (DNS, timeout, recusa de conexão) não é SMTPException."""
    import smtplib

    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.exemplo.local")

    def _explode(*args, **kwargs):
        raise OSError("Name or service not known")

    monkeypatch.setattr(smtplib, "SMTP", _explode)

    assert (
        email_sender.send_principal_user_credentials_email(
            to_email="maria@cliente.com",
            full_name="Maria",
            company_name="Alfa",
            temporary_password="x",
        )
        is False
    )
