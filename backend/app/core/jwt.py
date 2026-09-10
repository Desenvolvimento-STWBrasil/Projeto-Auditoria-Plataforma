from __future__ import annotations
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt

from app.core.config import settings


def create_access_token(*, subject: str, role: str) -> str:
    """
    subject: normalmente o user_id (string)
    role: papel do usuário (admin/user)
    """

    expires_delta = timedelta(minutes=settings.JWT_EXPIRES_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta

    payload = {
        "sub": subject,
        "role": role,
        "type": "access",
        "exp": expire,
    }

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(*, subject: str) -> str:
    """
    Token de vida longa (JWT_REFRESH_EXPIRES_DAYS, padrão 7 dias) usado
    apenas em POST /auth/refresh para obter um novo access_token sem
    exigir login (email/senha) de novo.

    Não carrega `role`: o endpoint de refresh sempre relê o usuário no
    banco antes de emitir o novo access_token, então o papel devolvido
    reflete o estado atual do usuário, não o que valia no momento do
    login original.
    """

    expires_delta = timedelta(days=settings.JWT_REFRESH_EXPIRES_DAYS)
    expire = datetime.now(timezone.utc) + expires_delta

    payload = {
        "sub": subject,
        "type": "refresh",
        "exp": expire,
    }

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Valida assinatura + expiração e retorna o payload.
    Lança JWTError se inválido. Decodifica qualquer token (access ou
    refresh) — quem chama decide se o `type` do payload é o esperado
    (ver decode_refresh_token e app/api/deps.py::get_current_user).
    """

    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


def decode_refresh_token(token: str) -> dict:
    """
    Como decode_token, mas recusa qualquer token que não seja
    explicitamente um refresh token (`type == "refresh"`) — evita que um
    access_token (de vida curta, mas eventualmente vazado) seja usado
    para renovar sessão indefinidamente.
    """

    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise JWTError("Token não é um refresh token")
    return payload
