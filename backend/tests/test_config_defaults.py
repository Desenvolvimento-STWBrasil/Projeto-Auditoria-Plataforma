"""
B-M25 / B-M29 / M-24: defaults inseguros ou divergentes não podem voltar.

`Settings` tem 19 campos com default e, até esta correção, nenhum teste
afirmava qual deveria ser. Consequência direta: o default de um campo de
segurança era aquele que a pessoa que escreveu a linha achou conveniente
na hora — `ALLOW_PUBLIC_REGISTRATION` era `True`, contra o que o
`.env.example` e o `docker-compose.yml` mandavam.

Mudar qualquer valor afirmado aqui exige mudar o teste, o que força a
mudança a passar por revisão em vez de escorregar num commit de outra
coisa.
"""

from __future__ import annotations

import pytest

from app.core.config import Settings

# Toda variável que `Settings` lê. O teste precisa limpar as duas fontes —
# o arquivo `.env` E o ambiente do processo —, senão ele mede a máquina
# onde roda, não o default do código.
#
# Isto não é hipotético: a primeira versão deste arquivo isolava só o
# `.env`, passava localmente, e quebrou no CI assim que o job `backend`
# ganhou `DATABASE_URL` e `JWT_SECRET` no ambiente (2026-08-26).
VARIAVEIS_DE_SETTINGS = (
    "PROJECT_NAME",
    "API_PREFIX_V1",
    "API_V1_PREFIX",
    "IS_DEBUG",
    "CORS_ALLOWED_ORIGINS",
    "CORS_ORIGINS",
    "DATABASE_URL",
    "ALLOW_PUBLIC_REGISTRATION",
    "JWT_SECRET",
    "JWT_ALGORITHM",
    "JWT_EXPIRES_MINUTES",
    "JWT_REFRESH_EXPIRES_DAYS",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "SMTP_FROM",
    "SMTP_USE_TLS",
)


@pytest.fixture(autouse=True)
def _ambiente_limpo(monkeypatch):
    """Remove do ambiente tudo que `Settings` consulta."""
    for nome in VARIAVEIS_DE_SETTINGS:
        monkeypatch.delenv(nome, raising=False)


def _settings_sem_env(**obrigatorios) -> Settings:
    """Settings a partir do CÓDIGO: sem `.env` e sem variáveis de ambiente."""
    return Settings(
        DATABASE_URL="sqlite://",
        JWT_SECRET="x" * 32,
        _env_file=None,
        **obrigatorios,
    )


def test_registro_publico_fechado_por_default():
    """B-M25: esquecer a variável não pode abrir o cadastro público."""
    assert _settings_sem_env().ALLOW_PUBLIC_REGISTRATION is False


def test_debug_desligado_por_default():
    assert _settings_sem_env().IS_DEBUG is False


def test_access_token_curto_por_default():
    """
    B-M29: 15 minutos. Se este número mudar, `frontend/proxy.ts` e
    `frontend/app/api/auth/login/route.ts` precisam mudar junto — os dois
    usam `?? 15` como default do `maxAge` do cookie. Divergir faz o cookie
    sobreviver ao token que ele carrega.
    """
    assert _settings_sem_env().JWT_EXPIRES_MINUTES == 15


def test_refresh_token_de_sete_dias_por_default():
    """Mesmo espelhamento de B-M29, para o refresh_token."""
    assert _settings_sem_env().JWT_REFRESH_EXPIRES_DAYS == 7


def test_algoritmo_de_jwt_fixado_por_default():
    assert _settings_sem_env().JWT_ALGORITHM == "HS256"


def test_cors_nao_abre_para_qualquer_origem_por_default():
    configuracao = _settings_sem_env()
    assert "*" not in configuracao.cors_allowed_origins_list
    assert configuracao.cors_allowed_origins_list == ["http://localhost:3000"]


def test_database_url_e_jwt_secret_sao_obrigatorios():
    """
    Nenhum dos dois pode ter default: um banco silenciosamente errado ou
    um segredo previsível são piores que a aplicação recusar-se a subir.

    A fixture `_ambiente_limpo` é o que dá sentido a este teste — sem ela
    ele só afirma que a máquina onde roda tem as variáveis definidas.
    """
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)

    faltando = {e["loc"][0] for e in exc.value.errors()}
    assert faltando == {"DATABASE_URL", "JWT_SECRET"}


def test_register_recusa_quando_a_variavel_nao_esta_definida(client, monkeypatch):
    """
    B-M25 pelo comportamento, não só pelo default: com a configuração que
    o código traz de fábrica, o cadastro público responde 403.
    """
    from app.core.config import settings

    monkeypatch.setattr(
        settings,
        "ALLOW_PUBLIC_REGISTRATION",
        _settings_sem_env().ALLOW_PUBLIC_REGISTRATION,
    )

    resposta = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Intruso",
            "email": "intruso@test.com",
            "password": "Senha1234",
        },
    )

    assert resposta.status_code == 403
