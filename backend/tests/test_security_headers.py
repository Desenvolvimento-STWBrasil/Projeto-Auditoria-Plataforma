"""
B-M21: os cabeçalhos de segurança, e em particular o CSP.

O defeito que estes testes existem para impedir: o CSP foi aplicado de
forma uniforme a todas as respostas, com a premissa de que "a API só
devolve JSON/PDF/binário". A premissa era falsa — /docs e /redoc são
páginas HTML que carregam script e CSS de CDN. Sob `default-src 'none'`
elas respondem **200** e renderizam **em branco**: tudo é bloqueado no
navegador, e nada disso aparece no log do servidor.

Conferir a presença do header não pega isso. É preciso conferir se o
header permite os recursos que a página realmente pede.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

DOCS_PATHS = ["/docs", "/redoc"]


def _csp(response) -> dict[str, list[str]]:
    header = response.headers["content-security-policy"]
    directives: dict[str, list[str]] = {}
    for part in header.split(";"):
        tokens = part.split()
        if tokens:
            directives[tokens[0]] = tokens[1:]
    return directives


def test_security_headers_present_on_data_route(client: TestClient):
    response = client.get("/health")
    headers = response.headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "geolocation=()" in headers["permissions-policy"]


def test_data_route_keeps_the_restrictive_csp(client: TestClient):
    """O valor do B-M21 está aqui: nas rotas que servem dados, nada pode
    ser carregado. A exceção das rotas de doc não pode vazar para cá."""
    directives = _csp(client.get("/health"))
    assert directives["default-src"] == ["'none'"]
    assert directives["frame-ancestors"] == ["'none'"]
    assert directives["base-uri"] == ["'none'"]
    assert "script-src" not in directives


def test_hsts_absent_over_plain_http(client: TestClient):
    """HSTS em HTTP claro é ignorado pelo navegador e atrapalha em local."""
    assert "strict-transport-security" not in client.get("/health").headers


@pytest.mark.parametrize("path", DOCS_PATHS)
def test_docs_page_is_served(client: TestClient, path: str):
    response = client.get(path)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@pytest.mark.parametrize("path", DOCS_PATHS)
def test_docs_csp_allows_every_resource_the_page_requests(
    client: TestClient, path: str
):
    """
    Varre o HTML de verdade e confere, origem por origem, que o CSP a
    permite. Se o FastAPI trocar de CDN numa atualização, este teste
    falha em vez de a página silenciosamente parar de renderizar.
    """
    response = client.get(path)
    directives = _csp(response)

    def allows(directive: str, origin: str) -> bool:
        sources = directives.get(directive, directives.get("default-src", []))
        return origin in sources

    for url in sorted(set(re.findall(r'https?://[^"\'\s>)]+', response.text))):
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        extension = url.rsplit(".", 1)[-1].split("?")[0]
        if extension == "js":
            directive = "script-src"
        elif extension == "css" or "fonts.googleapis" in url:
            directive = "style-src"
        else:
            directive = "img-src"
        assert allows(directive, origin), (
            f"{path}: {directive} bloqueia {origin} — a página carrega "
            f"com 200 e renderiza em branco"
        )

    # As duas páginas inicializam a UI num <script> inline sem nonce.
    assert "'unsafe-inline'" in directives["script-src"]
    # E buscam o /openapi.json a partir da própria origem.
    assert "'self'" in directives["connect-src"]


@pytest.mark.parametrize("path", DOCS_PATHS)
def test_docs_csp_still_blocks_framing_and_base_uri(client: TestClient, path: str):
    """A exceção das rotas de doc afrouxa script/style/img — não o resto."""
    directives = _csp(client.get(path))
    assert directives["default-src"] == ["'none'"]
    assert directives["frame-ancestors"] == ["'none'"]
    assert directives["base-uri"] == ["'none'"]


def test_openapi_json_keeps_the_restrictive_csp(client: TestClient):
    """O schema é dado, não página: o fetch é autorizado pelo connect-src
    da página que o pede, não pelo CSP da própria resposta."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert _csp(response)["default-src"] == ["'none'"]
