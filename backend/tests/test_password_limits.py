"""B-A27: o limite de 72 bytes do bcrypt é tratado, não herdado."""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.core.security import (
    MAX_PASSWORD_BYTES,
    PasswordTooLongError,
    hash_password,
    verify_password,
)

SENHA_LONGA = "A1" + ("x" * 100)  # 102 bytes
SENHA_LIMITE = "A1" + ("x" * 70)  # exatamente 72 bytes


def test_hash_password_recusa_acima_do_limite():
    with pytest.raises(PasswordTooLongError):
        hash_password(SENHA_LONGA)


def test_hash_password_aceita_exatamente_no_limite():
    assert len(SENHA_LIMITE.encode("utf-8")) == MAX_PASSWORD_BYTES
    assert verify_password(SENHA_LIMITE, hash_password(SENHA_LIMITE))


def test_verify_password_devolve_false_sem_levantar():
    hash_valido = hash_password("Senha1234")
    assert verify_password(SENHA_LONGA, hash_valido) is False


def test_verify_password_nao_confunde_prefixo_de_72_bytes():
    """O modo de falha do truncamento silencioso: duas senhas diferentes
    com o mesmo prefixo de 72 bytes NÃO podem autenticar a mesma conta."""
    hash_valido = hash_password(SENHA_LIMITE)
    assert verify_password(SENHA_LIMITE + "SUFIXO-DIFERENTE", hash_valido) is False


def test_verify_password_com_hash_corrompido_nao_estoura():
    assert verify_password("Senha1234", "isto-nao-e-um-hash-bcrypt") is False


def test_login_com_senha_longa_responde_401_e_nao_500(client, principal_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "cliente@test.com", "password": SENHA_LONGA},
    )
    assert resp.status_code == 401, (
        f"esperado 401 (credencial inválida), veio {resp.status_code} — "
        "o limite do bcrypt voltou a vazar como erro de servidor"
    )


def test_register_com_senha_longa_responde_422_e_nao_500(client, monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_PUBLIC_REGISTRATION", True)
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Teste Longo",
            "email": "longo@test.com",
            "password": SENHA_LONGA,
        },
    )
    assert resp.status_code == 422
    assert "72" in resp.text


def test_acentos_contam_como_dois_bytes(client):
    """36 'ç' = 72 bytes. O limite é de bytes, não de caracteres."""
    senha = "A1" + ("ç" * 36)  # 2 + 72 = 74 bytes
    assert len(senha) < MAX_PASSWORD_BYTES  # 38 caracteres
    assert len(senha.encode("utf-8")) > MAX_PASSWORD_BYTES
    with pytest.raises(PasswordTooLongError):
        hash_password(senha)
