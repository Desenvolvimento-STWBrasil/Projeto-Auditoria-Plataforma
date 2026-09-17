# PRD — Implantação Unificada (Docker + CI/CD) da Plataforma de Auditoria

| Campo | Valor |
|---|---|
| **Data** | 2026-09-10 |
| **Versão** | v1.0 |
| **Autor** | Rodrigo Santos + Claude Code (DevSecOps) |
| **Audiência** | Tech Lead, Desenvolvedor(a) responsável pelo deploy |
| **Status** | 🟡 Proposta — nenhum arquivo de infraestrutura foi criado ainda; este documento especifica o que criar e por quê |
| **Contexto** | Nesta mesma sessão, os documentos antigos de deploy (`docs/deploy_producao.md`, `docs/PRD.md`) foram removidos por estarem desatualizados. Este PRD é uma reconstrução **do zero**, auditando o estado real do repositório em 2026-09-10 (commit `8e9249e`) — não uma cópia dos documentos antigos. Onde a versão antiga acertava algo que ainda é válido, isso é reaproveitado e citado explicitamente; onde ela descrevia algo que nunca foi implementado, isso é tratado como lacuna, não como fato |

---

## Índice

1. [Visão Geral e Objetivos](#1-visão-geral-e-objetivos)
2. [Diagnóstico da Base Atual](#2-diagnóstico-da-base-atual)
3. [Arquitetura da Solução e Desenho do Pipeline](#3-arquitetura-da-solução-e-desenho-do-pipeline)
4. [Especificações Técnicas de Configuração](#4-especificações-técnicas-de-configuração)
5. [Plano de Execução e Preparação do Servidor](#5-plano-de-execução-e-preparação-do-servidor)

---

## 1. Visão Geral e Objetivos

### 1.1 Problema

A Plataforma de Auditoria (API FastAPI + frontend Next.js 16 + MySQL 8.4) hoje só roda de duas formas: localmente via `docker compose up` (stack de desenvolvimento, `CORS_ALLOWED_ORIGINS=http://localhost:3000`, sem TLS) ou com backend/frontend soltos fora de container. **Não existe pipeline de CI/CD no repositório** (`.github/` não existe) e **não existe nenhuma configuração voltada a produção** (sem Nginx, sem HTTPS, sem `docker-compose` de produção, sem processo de deploy). Um guia de deploy detalhado existia em `docs/deploy_producao.md`, mas foi removido nesta mesma sessão por descrever um pipeline (`ci.yml`) que **nunca chegou a ser commitado** — ou seja, era aspiracional, não implementado.

### 1.2 Objetivo

Especificar, de forma pronta para implementação, a infraestrutura de implantação **unificada em um único servidor** (Backend + Frontend + MySQL + Nginx via Docker Compose) e o pipeline de CI/CD no GitHub Actions que:

- roda a cada `push` e `pull_request` na branch `main`;
- executa a suíte de testes do backend (pytest, ~300+ testes, SQLite em memória) e do frontend (Vitest + build Next.js);
- em caso de sucesso **e apenas em `push` direto na `main`** (nunca em PR), faz o deploy em produção via SSH;
- reaproveita o cache de camadas do Docker para que um deploy de rotina rebuilde apenas a camada que mudou (dependências de sistema/npm/pip só quando `requirements.txt`/`package-lock.json` mudam; código da aplicação sempre).

### 1.3 Fora de escopo (não-objetivos)

| Item | Por quê está fora |
|---|---|
| Múltiplos servidores / alta disponibilidade | O requisito explícito é servidor único |
| Escalar o backend horizontalmente (múltiplas réplicas) | **Limitação arquitetural real do código atual**, não de infraestrutura — ver [2.4](#24-limitação-arquitetural-que-a-infraestrutura-precisa-respeitar) |
| Registry de imagens (GHCR/Docker Hub) | Ver decisão em [3.3](#33-decisão-onde-o-build-acontece) — não necessário para servidor único |
| Kubernetes / orquestração multi-nó | Overengineering para o cenário descrito |
| Observabilidade avançada (Prometheus/Grafana/ELK) | Fora do pedido; seção 5 cobre monitoramento básico (logs do Docker + `/health`) |

### 1.4 Critérios de sucesso

- Um `git push` na `main` com testes passando resulta em produção atualizada sem intervenção manual, em poucos minutos.
- Um PR na `main` roda os mesmos testes e **nunca** toca o servidor de produção.
- Um deploy de rotina (só código, sem mudar dependências) não reinstala `pip`/`npm` do zero.
- Nenhum segredo (senha de banco, `JWT_SECRET`, chave SSH) fica versionado no Git — todos vivem em GitHub Secrets ou em `.env.prod` no servidor, nunca commitado (ver `.gitignore`, que já cobre `.env*`).

---

## 2. Diagnóstico da Base Atual

### 2.1 O que já existe e será reaproveitado

| Item | Local | Estado |
|---|---|---|
| `docker-compose.yml` (dev, stack completa) | raiz | Orquestra `mysql` + `backend` + `frontend`; **já não publica a porta do MySQL no host** (bom hábito de isolamento a preservar em produção) |
| `backend/Dockerfile` | `backend/` | Builda com `python:3.12-slim`; **já copia `requirements.txt` antes de `COPY . .`** — layering correto para cache, só falta o multi-stage |
| `frontend/Dockerfile` | `frontend/` | **Já é multi-stage** (`deps` → `builder` → `runner`) e já usa `output: "standalone"` (`next.config.ts:5`) — é o Dockerfile mais próximo do ideal dos dois |
| `backend/docker-entrypoint.sh` | `backend/` | Já roda `alembic upgrade head` e `scripts/seed_admin.py` (idempotente) toda vez que o container do backend sobe — **o pipeline de deploy não precisa reimplementar isso**, só precisa recriar o container |
| `GET /health` | `backend/app/api/health.py` | Já existe, já testa a conexão com o banco (`SELECT 1`) — é o endpoint correto para `HEALTHCHECK` do Docker e para o smoke test do CI |
| `.dockerignore` (backend e frontend) | ambos | Já excluem `.env*`, `node_modules`/`venv`, testes, `.git` — não precisa de mudança |
| Testes 100% isolados do MySQL | `backend/tests/conftest.py` | Usa SQLite em memória (`StaticPool`) — **o job de testes do backend no CI não precisa subir um serviço MySQL**, só variáveis de ambiente dummy |
| `ALLOW_PUBLIC_REGISTRATION` com default seguro | `backend/app/core/config.py:27` | Já é `False` por padrão no código (era um risco citado no guia antigo removido; já foi corrigido) |
| `ruff.toml` / lint do backend | `backend/` | `select = ["F"]`, `target-version = "py312"` — reaproveitar como step de CI |
| `npm run lint` / `npm test` / `npm run build` | `frontend/package.json` | Scripts já existem e são os que o job de CI do frontend deve chamar |

### 2.2 Lacunas (o que falta criar)

| # | Lacuna | Impacto se não resolvida |
|---|---|---|
| G1 | **Nenhum workflow do GitHub Actions** (`.github/workflows/` não existe) | Sem CI, sem gate de testes antes de mergear/deployar; requisito explícito do pedido |
| G2 | `backend/Dockerfile` é single-stage e roda como **root** dentro do container, sem `HEALTHCHECK` | Superfície de ataque maior que o necessário; orquestrador não sabe distinguir container "up" de container "saudável" |
| G3 | Nenhum dos dois Dockerfiles tem `HEALTHCHECK` | Mesma consequência acima também no frontend |
| G4 | **Nenhuma configuração de Nginx no repositório** | Sem TLS, sem domínio único, backend e frontend expostos diretamente em `:8000`/`:3000` |
| G5 | Nenhum `docker-compose` dedicado a produção | O `docker-compose.yml` da raiz é de desenvolvimento (`CORS_ALLOWED_ORIGINS` fixo em `localhost`, portas de app publicadas diretamente no host) |
| G6 | Nenhum processo de deploy documentado ou testado | Cada deploy seria manual e não repetível |
| G7 | Nenhuma rotação de log configurada para os containers | Driver padrão `json-file` do Docker cresce sem limite e pode encher o disco ao longo do tempo |
| G8 | Nenhuma rotina de backup do MySQL | Sem backup, uma falha do volume `mysql_data` é perda total de dados |

### 2.3 Uma decisão de arquitetura que simplifica o desenho (achado desta auditoria)

O frontend **nunca expõe chamadas à API do backend diretamente ao navegador**. Toda comunicação passa por código server-side do Next.js (`frontend/lib/server-backend.ts`, usado pelos Route Handlers em `app/api/**` e pelas Server Actions), que lê `BACKEND_API_URL` como variável de ambiente **apenas do lado do servidor**. O guia de deploy removido assumia que o Nginx precisaria rotear `/api/*` para o backend como parte do funcionamento normal da aplicação — **isso não é verdade neste código**: o Next.js já faz esse proxy internamente, container a container, pela rede Docker (`http://backend:8000`).

Consequência prática: o Nginx só precisa expor **um único upstream para o usuário final** — o frontend (`:3000`). Rotas do backend (`/health`, `/docs`, `/openapi.json`) via Nginx são **opcionais**, só para operação/observabilidade, nunca para o funcionamento da aplicação para o usuário final. Isso reduz a superfície pública e simplifica a configuração do Nginx em relação à tentativa anterior.

### 2.4 Limitação arquitetural que a infraestrutura precisa respeitar

O backend **não pode rodar com mais de 1 processo/réplica** com o código atual, por dois motivos verificáveis no código:

1. **Uploads em disco local**: `backend/app/services/storage.py` grava evidências no volume `backend_uploads`, montado em um único container. Uma segunda réplica não veria os arquivos da primeira.
2. **Rate limiting em memória de processo**: `slowapi` (`app/main.py:18`, `Limiter(key_func=get_remote_address)`) conta requisições no processo Python. Com N réplicas ou N workers do Uvicorn, o limite efetivo de login (5/min) vira `5 × N`.

**Implicação para este PRD**: o `Dockerfile`/`docker-compose` de produção deve rodar o backend com **exatamente 1 worker Uvicorn e 0 réplicas adicionais** (`deploy.replicas` não se aplica aqui pois não se usa Swarm/K8s, mas o compose não deve declarar `--workers N>1` nem múltiplas instâncias do serviço `backend`). Isso não é uma limitação da infraestrutura proposta — é uma restrição real do código de hoje, documentada aqui para não ser "otimizada" incorretamente no futuro sem antes resolver os dois pontos acima.

---

## 3. Arquitetura da Solução e Desenho do Pipeline

### 3.1 Topologia de produção (servidor único)

```
                              Internet
                                 │  HTTPS :443 / HTTP :80 (redirect)
                                 ▼
                     ┌───────────────────────┐
                     │  nginx:alpine          │   único ponto exposto
                     │  (proxy reverso + TLS) │   publicamente no host
                     └──────────┬─────────────┘
                                │ rede Docker interna "auditoria-net"
                 ┌──────────────┼───────────────────┐
                 │                                  │ (opcional: /health,
                 ▼                                  │  /docs, /openapi.json)
        ┌─────────────────┐                         ▼
        │ frontend (Next)  │                ┌──────────────────┐
        │ :3000 standalone │───BACKEND_API──▶│ backend (FastAPI)│
        └──────────────────┘   URL (server-  │ :8000, 1 worker  │
                                side only)    └────────┬─────────┘
                                                        │ SQLAlchemy
                                               ┌────────▼─────────┐
                                               │ mysql:8.4         │
                                               │ :3306 (sem porta  │
                                               │ publicada no host)│
                                               └────────────────────┘
```

Nenhum serviço além do Nginx publica porta diretamente no host — `backend` e `frontend` param de expor `8000:8000`/`3000:3000` (como hoje no `docker-compose.yml` de dev) e passam a ser alcançáveis só pela rede interna do Compose, exatamente como o `mysql` já é hoje.

### 3.2 Desenho do pipeline (GitHub Actions)

```
push / pull_request → branch "main"
            │
            ├──▶ Job "backend-tests"   (sempre, PR ou push)
            │      Python 3.12 + pip cache → ruff check → pytest (SQLite em memória)
            │
            ├──▶ Job "frontend-tests"  (sempre, PR ou push, em paralelo com o acima)
            │      Node 20 + npm cache → eslint → vitest run → next build
            │
            └──▶ Job "deploy"          (só se os dois acima passarem)
                   Condição: github.event_name == 'push' AND github.ref == 'refs/heads/main'
                   → SSH no servidor → git pull → docker compose build → docker compose up -d
                   → curl no /health via rede interna → docker image prune -f
```

Um `pull_request` nunca chega ao job `deploy` — a condição do `if:` do job filtra por `event_name == 'push'`, então mesmo um PR aberto contra `main` (que também dispara o workflow, por causa do `pull_request:` no `on:`) só roda os dois jobs de teste.

### 3.3 Decisão: onde o build acontece

Duas opções válidas para "atualizar rápido, rebuildando só o que mudou":

| Opção | Como funciona | Cache de camadas |
|---|---|---|
| **A — Build no próprio servidor** (recomendada aqui) | O job `deploy` faz SSH, `git pull`, e roda `docker compose build` **no servidor**. O daemon Docker do servidor é persistente entre deploys | **Automático e gratuito**: como o daemon nunca é descartado, as camadas de `pip install`/`npm ci` continuam em cache localmente entre um deploy e outro, desde que `requirements.txt`/`package-lock.json` não mudem. Não precisa de registry nem de `actions/cache` |
| B — Build no runner do GitHub Actions + push para um registry (GHCR) | O CI builda a imagem, publica em `ghcr.io/...`, e o servidor só dá `docker compose pull` | Precisa de `actions/cache` ou `--cache-from` explícito, pois cada execução do runner começa "do zero"; exige configurar autenticação no GHCR e um secret adicional |

**Recomendação: Opção A.** Para um único servidor, ela atende ao requisito de cache de camadas sem infraestrutura extra (sem registry, sem secret adicional de autenticação de imagem) — o próprio filesystem do Docker no servidor já é o cache. A Opção B fica documentada aqui como evolução natural caso o projeto cresça para múltiplos servidores/ambientes (nesse caso o cache do host deixa de ser suficiente porque o servidor de destino nunca fez o build localmente).

---

## 4. Especificações Técnicas de Configuração

### 4.1 `backend/Dockerfile` (multi-stage, substituindo o atual)

```dockerfile
# syntax=docker/dockerfile:1

# ---- builder: instala dependências Python (inclui toolchain de compilação) ----
FROM python:3.12-slim AS builder
WORKDIR /app

# gcc + default-libmysqlclient-dev: necessários para compilar dependências
# nativas de algumas libs (cryptography/pymysql já trazem wheels na maioria
# dos casos, mas o build fica resiliente a plataformas sem wheel pronta).
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copiar só o requirements.txt primeiro: esta camada só é invalidada quando
# uma dependência muda, não a cada alteração de código-fonte.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --user -r requirements.txt

# ---- runtime: imagem final, sem toolchain de build ----
FROM python:3.12-slim AS runtime
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        default-libmysqlclient-dev curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appgroup && useradd -r -g appgroup -d /app appuser

COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

COPY --chown=appuser:appgroup . .
RUN chmod +x docker-entrypoint.sh \
    && mkdir -p uploads && chown appuser:appgroup uploads

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
# 1 worker: ver seção 2.4 (uploads em disco local + rate limit em memória
# de processo tornam >1 worker/réplica incorreto com o código atual).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

**O que muda de fato em relação ao `backend/Dockerfile` atual**: separação builder/runtime (imagem final sem `gcc`), usuário não-root, `HEALTHCHECK` usando o `/health` real do projeto, e `--workers 1` explícito (documentando a limitação, em vez de depender do default implícito do Uvicorn). O `docker-entrypoint.sh` existente **não muda** — continua responsável por `alembic upgrade head` + `seed_admin.py` a cada subida.

### 4.2 `frontend/Dockerfile` (ajustes sobre o já existente)

O Dockerfile atual já está estruturalmente correto (multi-stage, `standalone`, ordem de `COPY` favorável a cache). Os ajustes são hardening, não reestruturação:

```dockerfile
# ---- deps ----
FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# ---- build ----
FROM node:20-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ---- runtime ----
FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN groupadd -r nodejs && useradd -r -g nodejs -d /app nextjs

COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000
ENV PORT=3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD node -e "fetch('http://localhost:3000/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "server.js"]
```

Diferença em relação ao atual: usuário `nextjs` não-root e `HEALTHCHECK` nativo em Node (sem depender de `wget`/`curl`, que não vêm no `node:20-slim` por padrão).

### 4.3 `docker-compose.prod.yml` (novo, na raiz)

Mantém a base do `docker-compose.yml` de desenvolvimento, mas: não publica portas de app no host, adiciona o serviço `nginx`, limita o log driver, e usa variáveis 100% vindas de `.env.prod`.

```yaml
services:
  mysql:
    image: mysql:8.4
    container_name: auditoria-mysql
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:?defina no .env.prod}
      MYSQL_DATABASE: auditoria
      MYSQL_USER: auditoria_app
      MYSQL_PASSWORD: ${MYSQL_PASSWORD:?defina no .env.prod}
    command: >
      --character-set-server=utf8mb4
      --collation-server=utf8mb4_unicode_ci
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-uroot", "-p${MYSQL_ROOT_PASSWORD}"]
      interval: 10s
      timeout: 5s
      retries: 10
    volumes:
      - mysql_data:/var/lib/mysql
    logging:
      driver: json-file
      options: { max-size: "10m", max-file: "3" }
    networks: [auditoria-net]
    # Sem "ports:" — só acessível pela rede interna do Compose.

  backend:
    build:
      context: ./backend
    container_name: auditoria-backend
    restart: unless-stopped
    depends_on:
      mysql:
        condition: service_healthy
    environment:
      DATABASE_URL: mysql+pymysql://auditoria_app:${MYSQL_PASSWORD:?defina no .env.prod}@mysql:3306/auditoria
      JWT_SECRET: ${JWT_SECRET:?defina no .env.prod}
      JWT_ALGORITHM: HS256
      JWT_EXPIRES_MINUTES: ${JWT_EXPIRES_MINUTES:-15}
      JWT_REFRESH_EXPIRES_DAYS: ${JWT_REFRESH_EXPIRES_DAYS:-7}
      CORS_ALLOWED_ORIGINS: ${CORS_ALLOWED_ORIGINS:?defina o domínio real no .env.prod}
      IS_DEBUG: "false"
      ALLOW_PUBLIC_REGISTRATION: "false"
      ADMIN_EMAIL: ${ADMIN_EMAIL:?defina no .env.prod}
      ADMIN_FULL_NAME: ${ADMIN_FULL_NAME:-Administrador}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD:?defina no .env.prod}
      SMTP_HOST: ${SMTP_HOST:-}
      SMTP_PORT: ${SMTP_PORT:-587}
      SMTP_USER: ${SMTP_USER:-}
      SMTP_PASSWORD: ${SMTP_PASSWORD:-}
      SMTP_FROM: ${SMTP_FROM:-}
      SMTP_USE_TLS: ${SMTP_USE_TLS:-true}
    volumes:
      - backend_uploads:/app/uploads
    logging:
      driver: json-file
      options: { max-size: "10m", max-file: "3" }
    networks: [auditoria-net]
    # Sem "ports:" — o Nginx alcança via rede interna ("backend:8000").

  frontend:
    build:
      context: ./frontend
    container_name: auditoria-frontend
    restart: unless-stopped
    depends_on:
      backend:
        condition: service_healthy
    environment:
      BACKEND_API_URL: http://backend:8000
      JWT_SECRET: ${JWT_SECRET:?defina no .env.prod}
      JWT_ALGORITHM: HS256
      JWT_EXPIRES_MINUTES: ${JWT_EXPIRES_MINUTES:-15}
      NODE_ENV: production
    logging:
      driver: json-file
      options: { max-size: "10m", max-file: "3" }
    networks: [auditoria-net]
    # Sem "ports:" — o Nginx alcança via rede interna ("frontend:3000").

  nginx:
    image: nginx:alpine
    container_name: auditoria-nginx
    restart: unless-stopped
    depends_on: [frontend, backend]
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
      - /var/www/certbot:/var/www/certbot:ro
    networks: [auditoria-net]

volumes:
  mysql_data:
  backend_uploads:

networks:
  auditoria-net:
    driver: bridge
```

### 4.4 `nginx/nginx.conf` (novo)

```nginx
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    access_log /var/log/nginx/access.log;
    error_log  /var/log/nginx/error.log warn;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # Uploads de evidências (ver backend/app/services/storage.py)
    client_max_body_size 50M;

    proxy_connect_timeout 60s;
    proxy_send_timeout    60s;
    proxy_read_timeout    60s;

    server {
        listen 80;
        server_name SEU_DOMINIO_AQUI;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://$host$request_uri;
        }
    }

    server {
        listen 443 ssl http2;
        server_name SEU_DOMINIO_AQUI;

        ssl_certificate     /etc/letsencrypt/live/SEU_DOMINIO_AQUI/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/SEU_DOMINIO_AQUI/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_session_cache shared:SSL:10m;

        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
        add_header X-Content-Type-Options nosniff always;
        add_header X-Frame-Options DENY always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;

        # Aplicação (rota obrigatória — é como o usuário final acessa o sistema).
        # O Next.js já faz o proxy para o backend internamente; o navegador
        # nunca fala com :8000 diretamente (ver seção 2.3).
        location / {
            proxy_pass         http://frontend:3000;
            proxy_http_version 1.1;
            proxy_set_header   Host              $host;
            proxy_set_header   X-Real-IP         $remote_addr;
            proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
            proxy_set_header   X-Forwarded-Proto $scheme;
        }

        # Rotas opcionais de operação/observabilidade do backend.
        # Recomendação: restringir por IP (allow/deny) ou remover em produção
        # pública — não são necessárias para o funcionamento da aplicação.
        location /health {
            proxy_pass http://backend:8000/health;
        }

        location /docs {
            # allow 203.0.113.0/24;  # IP do escritório, por exemplo
            # deny all;
            proxy_pass http://backend:8000/docs;
        }

        location /openapi.json {
            proxy_pass http://backend:8000/openapi.json;
        }
    }
}
```

### 4.5 `.github/workflows/deploy.yml` (novo)

```yaml
name: CI/CD — Testes e Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

# Cancela execuções antigas do mesmo PR/branch quando um novo push chega.
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  backend-tests:
    name: Backend — lint + pytest
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
          cache-dependency-path: backend/requirements.txt

      - name: Instalar dependências
        working-directory: backend
        run: pip install -r requirements.txt

      - name: Lint (ruff)
        working-directory: backend
        run: ruff check .

      # Testes usam SQLite em memória (backend/tests/conftest.py) — não
      # precisa de serviço MySQL no runner. As variáveis abaixo só existem
      # para satisfazer app/core/config.py (Settings), que exige
      # DATABASE_URL/JWT_SECRET na importação do app.
      - name: Testes (pytest)
        working-directory: backend
        env:
          DATABASE_URL: sqlite:///:memory:
          JWT_SECRET: ci_only_dummy_secret_not_for_production
          CORS_ALLOWED_ORIGINS: http://localhost:3000
        run: pytest -v

  frontend-tests:
    name: Frontend — lint + testes + build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Instalar dependências
        working-directory: frontend
        run: npm ci

      - name: Lint (eslint)
        working-directory: frontend
        run: npm run lint

      - name: Testes (vitest)
        working-directory: frontend
        run: npm test

      # next build também funciona como verificação de tipos/erros de
      # compilação — falha aqui pega problema que o vitest não cobre.
      - name: Build de produção
        working-directory: frontend
        env:
          BACKEND_API_URL: http://backend:8000
          JWT_SECRET: ci_only_dummy_secret_not_for_production
          JWT_ALGORITHM: HS256
        run: npm run build

  deploy:
    name: Deploy em produção via SSH
    runs-on: ubuntu-latest
    needs: [backend-tests, frontend-tests]
    # Só em push direto na main — nunca em pull_request, mesmo que os
    # testes acima também rodem para PRs.
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.PROD_SSH_KEY }}
          port: ${{ secrets.PROD_SSH_PORT || 22 }}
          script: |
            set -e
            cd /opt/auditoria
            git fetch origin main
            git reset --hard origin/main

            # Build usa o cache de camadas persistido no daemon Docker do
            # próprio servidor (ver seção 3.3) — só reinstala pip/npm
            # quando requirements.txt/package-lock.json mudam.
            docker compose -f docker-compose.prod.yml --env-file .env.prod build

            # Recria só os containers cujo código/config mudou.
            # docker-entrypoint.sh do backend já roda "alembic upgrade head"
            # e o seed do admin sozinho ao subir — não repetir aqui.
            docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

            # Smoke test: espera o backend responder saudável antes de
            # considerar o deploy concluído.
            for i in $(seq 1 15); do
              STATUS=$(docker compose -f docker-compose.prod.yml exec -T backend \
                curl -fsS -o /dev/null -w '%{http_code}' http://localhost:8000/health || echo "000")
              [ "$STATUS" = "200" ] && break
              sleep 2
            done
            if [ "$STATUS" != "200" ]; then
              echo "Deploy falhou: /health não respondeu 200 após rebuild" >&2
              exit 1
            fi

            docker image prune -f
            echo "Deploy concluído: $(date -u +%FT%TZ)"
```

**Secrets necessários no GitHub** (Settings → Secrets and variables → Actions):

| Secret | Conteúdo |
|---|---|
| `PROD_HOST` | IP ou hostname do servidor |
| `PROD_USER` | Usuário SSH de deploy (não-root — ver [5.2](#52-usuário-de-deploy-e-chave-ssh)) |
| `PROD_SSH_KEY` | Chave **privada** SSH dedicada ao deploy (par gerado só para isso) |
| `PROD_SSH_PORT` | Opcional, só se o SSH não estiver na porta 22 |

Nenhum segredo da aplicação (`JWT_SECRET`, senhas do MySQL, `ADMIN_PASSWORD`, credenciais SMTP) passa pelo GitHub Actions — eles vivem exclusivamente em `.env.prod`, criado manualmente no servidor (seção 5) e nunca versionado.

---

## 5. Plano de Execução e Preparação do Servidor Remoto

### 5.1 Requisitos mínimos do servidor

| Recurso | Mínimo | Recomendado |
|---|---|---|
| CPU | 2 vCPUs | 4 vCPUs |
| RAM | 2 GB | 4 GB |
| Disco | 20 GB | 50 GB SSD |
| SO | Ubuntu 22.04 LTS | Ubuntu 22.04/24.04 LTS |
| Software | Docker Engine + plugin `docker compose`, `git`, `nginx`-tools não são necessários no host (Nginx roda em container) | + `certbot` no host para emitir/renovar certificado |

### 5.2 Usuário de deploy e chave SSH

Não usar `root` para o deploy automatizado.

```bash
# No servidor, como root/sudo:
adduser --disabled-password --gecos "" deploy
usermod -aG docker deploy          # permite rodar `docker compose` sem sudo

# Na sua máquina, gerar um par de chaves dedicado só ao CI:
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ./deploy_key -N ""

# Copiar a chave PÚBLICA para o servidor:
ssh-copy-id -i ./deploy_key.pub deploy@SEU_SERVIDOR

# O conteúdo da chave PRIVADA (./deploy_key) vai no secret PROD_SSH_KEY do GitHub.
# Nunca reutilize essa chave para outra finalidade.
```

### 5.3 Instalar Docker, firewall e clonar o repositório

```bash
# Docker Engine + Compose plugin (repositório oficial):
sudo apt update && sudo apt install -y ca-certificates curl gnupg
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Firewall: só SSH, HTTP e HTTPS chegam de fora.
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Clonar o repositório no diretório de deploy:
sudo mkdir -p /opt/auditoria && sudo chown deploy:deploy /opt/auditoria
su - deploy
git clone <URL-do-repositório> /opt/auditoria
cd /opt/auditoria
```

### 5.4 Variáveis de ambiente de produção (`.env.prod`)

Criado **manualmente, uma única vez, no servidor** — nunca no Git (já coberto por `.gitignore`, que ignora todo `.env*`).

```bash
nano /opt/auditoria/.env.prod
```

```dotenv
MYSQL_ROOT_PASSWORD=<gerar: python3 -c "import secrets;print(secrets.token_urlsafe(24))">
MYSQL_PASSWORD=<gerar da mesma forma, valor diferente>

JWT_SECRET=<gerar: python3 -c "import secrets;print(secrets.token_hex(32))">
JWT_EXPIRES_MINUTES=15
JWT_REFRESH_EXPIRES_DAYS=7

CORS_ALLOWED_ORIGINS=https://SEU_DOMINIO_AQUI

ADMIN_EMAIL=admin@stwbrasil.com
ADMIN_FULL_NAME=Administrador
ADMIN_PASSWORD=<senha forte, só para o primeiro acesso>

# Opcional — sem isso, onboarding de cliente não consegue enviar a senha
# temporária por e-mail (vira log estruturado em vez de e-mail real).
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
```

```bash
chmod 600 /opt/auditoria/.env.prod
```

### 5.5 Certificado TLS (Let's Encrypt)

```bash
sudo apt install -y certbot
sudo systemctl stop nginx 2>/dev/null || true   # garantir a porta 80 livre
sudo certbot certonly --standalone -d SEU_DOMINIO_AQUI \
  --email rodrigo.santos@stwbrasil.com --agree-tos --non-interactive

# Renovação automática (o pacote certbot já instala um timer systemd):
sudo certbot renew --dry-run
# Recarregar o Nginx em container após renovar:
echo "0 0,12 * * * root certbot renew --quiet --post-hook 'docker exec auditoria-nginx nginx -s reload'" | \
  sudo tee /etc/cron.d/certbot-renew
```

### 5.6 Primeiro deploy (manual, uma única vez)

Depois disso, todo deploy subsequente é automático via GitHub Actions (seção 4.5).

```bash
cd /opt/auditoria
docker compose -f docker-compose.prod.yml --env-file .env.prod build
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
docker compose -f docker-compose.prod.yml ps    # os 4 serviços devem estar "healthy"

curl -I https://SEU_DOMINIO_AQUI/          # esperado: HTTP/2 200 (frontend)
curl https://SEU_DOMINIO_AQUI/health       # esperado: {"status":"Ok", ...}
```

Popular dados iniciais (catálogo de controles / templates de quadro), se ainda não existirem:

```bash
docker compose -f docker-compose.prod.yml exec backend python scripts/seed_catalog.py
docker compose -f docker-compose.prod.yml exec backend python scripts/seed_dashboard_templates.py
```

### 5.7 Configurar os secrets no GitHub

Repositório → **Settings → Secrets and variables → Actions → New repository secret**: `PROD_HOST`, `PROD_USER` (`deploy`), `PROD_SSH_KEY` (conteúdo de `deploy_key`, a chave privada gerada em 5.2). A partir daqui, todo `git push` na `main` com testes verdes dispara o deploy automaticamente.

### 5.8 Backup do MySQL (rotina mínima)

```bash
sudo mkdir -p /opt/auditoria/backups && sudo chown deploy:deploy /opt/auditoria/backups

cat > /opt/auditoria/backup.sh << 'EOF'
#!/bin/bash
set -e
DIR="/opt/auditoria/backups"
DATE=$(date +%Y%m%d_%H%M%S)
PASS=$(grep MYSQL_PASSWORD /opt/auditoria/.env.prod | cut -d= -f2)
docker exec auditoria-mysql mysqldump -uauditoria_app -p"${PASS}" --single-transaction auditoria \
  | gzip > "${DIR}/backup_${DATE}.sql.gz"
ls -t "${DIR}"/backup_*.sql.gz | tail -n +31 | xargs -r rm   # mantém os últimos 30
EOF
chmod +x /opt/auditoria/backup.sh
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/auditoria/backup.sh >> /var/log/auditoria-backup.log 2>&1") | crontab -
```

> Restaurar: `gunzip < backup_YYYYMMDD.sql.gz | docker exec -i auditoria-mysql mysql -uauditoria_app -p"$SENHA" auditoria`. **Ensaie a restauração pelo menos uma vez contra um banco descartável** antes de confiar na rotina — um backup nunca testado é apenas um arquivo.

### 5.9 Checklist final antes de abrir ao público

- [ ] `.env.prod` criado, com `chmod 600`, e **não** dentro do Git
- [ ] `CORS_ALLOWED_ORIGINS` aponta para o domínio real (sem `localhost`)
- [ ] `JWT_SECRET` gerado só para produção (nunca o mesmo do `.env` de dev)
- [ ] `ALLOW_PUBLIC_REGISTRATION=false` (já é o default no código, mas confirme que ninguém sobrescreveu)
- [ ] HTTPS ativo, HTTP redirecionando para HTTPS, HSTS habilitado
- [ ] Porta do MySQL **não** publicada no host (sem `ports:` no serviço `mysql`)
- [ ] Backend/frontend **sem** `ports:` publicadas — só o Nginx expõe 80/443
- [ ] `/docs` do backend restrito por IP ou removido do Nginx público (é a documentação interativa da API)
- [ ] Backend rodando com `--workers 1` e sem réplicas (seção 2.4)
- [ ] SMTP configurado e testado, se onboarding de clientes reais for usar e-mail de senha temporária
- [ ] Cron de backup ativo e restauração já ensaiada uma vez
- [ ] Secrets `PROD_HOST`/`PROD_USER`/`PROD_SSH_KEY` cadastrados no GitHub

---

## Próximos passos sugeridos

Este documento é a especificação; nenhum arquivo (`Dockerfile`, `docker-compose.prod.yml`, `nginx/nginx.conf`, `.github/workflows/deploy.yml`) foi criado no repositório ainda. Sugestão de ordem de implementação, cada uma verificável isoladamente antes da próxima:

1. Multi-stage do `backend/Dockerfile` + `HEALTHCHECK` nos dois Dockerfiles (seção 4.1/4.2) — testar com `docker compose build` local.
2. `.github/workflows/deploy.yml` **sem** o job `deploy` (só os dois jobs de teste) — validar em um PR real antes de ligar o deploy automático.
3. Provisionar o servidor (seção 5.1–5.5) e fazer o primeiro deploy manual (5.6) — só depois disso ligar o job `deploy` do workflow.
4. `docker-compose.prod.yml` + `nginx/nginx.conf` (seção 4.3/4.4).
5. Cron de backup (5.8) e ensaio de restauração.
