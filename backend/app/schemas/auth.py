from __future__ import annotations

import re

from pydantic import BaseModel, EmailStr, field_validator

from app.core.security import MAX_PASSWORD_BYTES


def _validate_password_length(value: str) -> None:
    """Limite em BYTES (não caracteres) — é o que o bcrypt mede (B-A27)."""
    encoded = value.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Senha não pode ultrapassar {MAX_PASSWORD_BYTES} bytes. "
            "Acentos contam 2 bytes e emojis contam 4, então uma senha "
            "com menos de 72 caracteres ainda pode exceder o limite."
        )


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Senha deve ter ao menos 8 caracteres")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Senha deve ter ao menos uma letra maiúscula")
        if not re.search(r"[0-9]", v):
            raise ValueError("Senha deve ter ao menos um número")
        _validate_password_length(v)
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_within_bcrypt_limit(cls, v: str) -> str:
        """
        No LOGIN o limite não é validado como erro de formulário — uma senha
        longa demais simplesmente não pode estar correta, e `verify_password`
        já devolve False para ela. Este validador existe apenas como corte
        de custo: evita carregar uma string arbitrariamente grande até o
        bcrypt. O corte é generoso de propósito (10x o limite), para não
        virar um oráculo de tamanho.
        """
        if len(v.encode("utf-8")) > MAX_PASSWORD_BYTES * 10:
            raise ValueError("Credenciais inválidas")
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserPublic(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str
