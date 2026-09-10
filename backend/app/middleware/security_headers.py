from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# B-M21. Política padrão: a API responde JSON/PDF/binário, então nada
# precisa ser carregado a partir dessas respostas.
API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"

# ...com uma exceção: /docs e /redoc SÃO páginas HTML com script, servidas
# pelo próprio FastAPI a partir de CDN. Sob a política acima elas carregam
# com 200 e renderizam em branco — o navegador bloqueia o bundle, o CSS, o
# script inline de inicialização e o fetch do openapi.json, sem nada disso
# aparecer no log do servidor. As origens abaixo são exatamente as que o
# HTML gerado por get_swagger_ui_html/get_redoc_html referencia:
#   - cdn.jsdelivr.net ......... swagger-ui-bundle.js, swagger-ui.css,
#                                redoc.standalone.js
#   - fastapi.tiangolo.com ..... favicon
#   - fonts.googleapis.com ..... folha de estilo de fontes do ReDoc
#   - fonts.gstatic.com ........ arquivos de fonte referenciados por ela
# 'unsafe-inline' é inevitável aqui: as duas páginas inicializam a UI num
# <script> inline sem nonce. Fica restrito às rotas de documentação — as
# rotas de dados seguem com default-src 'none'.
DOCS_CSP = (
    "default-src 'none'; "
    "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com "
    "'unsafe-inline'; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    @staticmethod
    def _is_docs_path(request) -> bool:
        """Lê as rotas de documentação do próprio app em vez de fixá-las:
        se `docs_url`/`redoc_url` mudarem (ou virarem None em produção), o
        middleware acompanha sem precisar de edição."""
        app = request.app
        paths = {
            getattr(app, "docs_url", None),
            getattr(app, "redoc_url", None),
            getattr(app, "swagger_ui_oauth2_redirect_url", None),
        }
        return request.url.path in {p for p in paths if p}

    async def dispatch(self, request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )
        response.headers["Content-Security-Policy"] = (
            DOCS_CSP if self._is_docs_path(request) else API_CSP
        )
        # HSTS só sob HTTPS: enviado em HTTP claro, é ignorado pelos
        # navegadores e ainda induz erro em ambiente local.
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response
