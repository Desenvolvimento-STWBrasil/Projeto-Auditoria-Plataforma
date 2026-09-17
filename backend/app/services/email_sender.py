from __future__ import annotations

import smtplib
from email.message import EmailMessage

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


def _enviar(msg: EmailMessage) -> bool:
    """Entrega via SMTP. Devolve False (em vez de propagar) se falhar:
    quem chama já committou a transação e não pode desfazê-la por causa
    de um servidor de e-mail — mesmo princípio de storage.delete_files()
    (B-A26). A falha vira log estruturado e um sinal de retorno."""
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        logger.warning("credentials_email_failed", to_email=msg["To"], error=str(exc))
        return False

    logger.info("credentials_email_sent", to_email=msg["To"])
    return True


def send_sub_user_credentials_email(
    *, to_email: str, sub_user_name: str, principal_name: str, temporary_password: str
) -> bool:
    """
    Credenciais de um SUB-USUÁRIO, criado a pedido do usuário principal.

    Devolve True se o e-mail foi entregue, False caso contrário (SMTP não
    configurado ou falha de entrega). Quem chama usa esse retorno para
    decidir se precisa devolver a senha ao admin (B-A29). A senha NUNCA
    entra em log, com ou sem SMTP.
    """
    if not settings.SMTP_HOST:
        logger.info(
            "credentials_email_skipped_no_smtp",
            to_email=to_email,
            recipient_kind="sub-user",
        )
        return False

    msg = EmailMessage()
    msg["Subject"] = "Acesso de colaborador — Plataforma de Auditoria"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.set_content(
        f"Olá, {sub_user_name}.\n\n"
        f"Você foi adicionado como colaborador de {principal_name}.\n\n"
        f"Use as seguintes credenciais para acessar o sistema:\n\n"
        f"E-mail: {to_email}\n"
        f"Senha temporária: {temporary_password}\n\n"
        f"Recomendamos alterar sua senha no primeiro acesso.\n\n"
        f"Atenciosamente,\nEquipe de Auditoria"
    )
    return _enviar(msg)


def send_principal_user_credentials_email(
    *, to_email: str, full_name: str, company_name: str, temporary_password: str
) -> bool:
    """
    Credenciais do USUÁRIO PRINCIPAL de uma empresa recém-onboardada.

    Função própria, e não reuso de `send_sub_user_credentials_email`
    (B-M27): reusar fazia todo cliente principal receber um e-mail com o
    assunto "Acesso de sub-usuário" dizendo que ele fora "adicionado como
    sub-usuário" da própria empresa.
    """
    if not settings.SMTP_HOST:
        logger.info(
            "credentials_email_skipped_no_smtp",
            to_email=to_email,
            recipient_kind="principal-user",
        )
        return False

    msg = EmailMessage()
    msg["Subject"] = "Seu acesso — Plataforma de Auditoria"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.set_content(
        f"Olá, {full_name}.\n\n"
        f"A conta da empresa {company_name} foi criada na Plataforma de "
        f"Auditoria e você é o usuário responsável.\n\n"
        f"Use as seguintes credenciais para o primeiro acesso:\n\n"
        f"E-mail: {to_email}\n"
        f"Senha temporária: {temporary_password}\n\n"
        f"Altere sua senha no primeiro acesso.\n\n"
        f"Atenciosamente,\nEquipe de Auditoria"
    )
    return _enviar(msg)
