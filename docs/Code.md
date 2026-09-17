# Code — Guia de Implementação (Docker + Nginx + CI/CD) da Plataforma de Auditoria

| Campo | Valor |
|---|---|
| **Data** | 2026-09-10 |
| **Versão** | v1.0 |
| **Autor** | Rodrigo Santos + Claude Code (DevSecOps) |
| **Origem** | Implementa, arquivo por arquivo, o que [`docs/Spec.md`](Spec.md) mapeou e [`docs/prd_deploy_producao.md`](prd_deploy_producao.md) justificou. Este documento não toma nenhuma decisão nova — só entrega o código final e explica cada linha |
| **Audiência** | Quem vai copiar/colar e aplicar os arquivos, e quem vai revisar o PR que os introduz |
| **Convenção didática** | Todo bloco de código vem com 4 blocos de texto ao redor: **Caminho**, **Objetivo**, **Conexões e Integrações** e **Explicação passo a passo** |

---

## Índice

1. [Visão Geral da Implementação](#1-visão-geral-da-implementação)
2. [Implementação do Backend](#2-implementação-do-backend)
3. [Implementação do Frontend](#3-implementação-do-frontend)
4. [Orquestração e Redes (Docker Compose + Nginx)](#4-orquestração-e-redes-docker-compose--nginx)
5. [Automação CI/CD (GitHub Actions)](#5-automação-cicd-github-actions)
6. [Documentação (README.md)](#6-documentação-readmemd)
7. [Guia Prático de Execução](#7-guia-prático-de-execução)

---

## 1. Visão Geral da Implementação

Os 8 arquivos da Spec **não devem ser criados em qualquer ordem**. A ordem abaixo existe para que cada arquivo seja testável isoladamente antes do próximo depender dele — é a mesma lógica de "não construir o segundo andar sem o primeiro estar seco".

| Ordem | Arquivo | Ação | Por que nesta posição |
|---|---|---|---|
| 1 | `backend/Dockerfile` | Reescrever | Não depende de nenhum outro arquivo novo; testável sozinho com `docker build` |
| 2 | `frontend/Dockerfile` | Editar | Idem — testável sozinho |
| 3 | `.env.prod.example` | Criar | Precisa existir antes de qualquer `docker-compose.prod.yml` fazer sentido para quem for aplicá-lo |
| 4 | `.gitignore` | Editar | Deve proteger `.env.prod` **antes** de esse arquivo ser criado de verdade no servidor (passo 6) |
| 5 | `.github/workflows/deploy.yml` | Criar **sem o job `deploy`** | Validado com um Pull Request real, sem risco de acionar SSH contra um servidor que ainda nem existe |
| 6 | Servidor + `docker-compose.prod.yml` + `nginx/nginx.conf` | Provisionar + criar | Primeiro deploy é **manual**, direto por SSH, para provar que a stack sobe antes de automatizar |
| 7 | `.github/workflows/deploy.yml` | Adicionar o job `deploy` + cadastrar Secrets | Só depois do passo 6 confirmado — nunca antes |
| 8 | `README.md` | Editar | Sem dependências; pode ser feito a qualquer momento |

> A partir daqui, cada seção segue essa mesma ordem — backend primeiro, frontend depois, orquestração/rede em seguida, CI/CD por último.

---

## 2. Implementação do Backend

### 2.1 `/backend/Dockerfile`

**Objetivo principal:** empacotar a API FastAPI em uma imagem de produção — pequena, sem ferramentas de compilação, rodando como usuário sem privilégios, e capaz de reportar sozinha se está saudável.

**Conexões e integrações:**
- É referenciado por `docker-compose.prod.yml` em `backend.build.context: ./backend` — o Compose chama exatamente este arquivo para construir a imagem do serviço `backend`.
- O `ENTRYPOINT` chama `./docker-entrypoint.sh`, um arquivo **já existente e que não muda** (mostrado logo abaixo, seção 2.2) — é ele quem aplica as migrations do Alembic e garante o usuário admin toda vez que o container sobe.
- O `HEALTHCHECK` chama `GET /health`, rota definida em `backend/app/api/health.py` — o mesmo endpoint que o Nginx expõe opcionalmente em `/health` (seção 4.2) e que o job `deploy` do GitHub Actions usa como *smoke test* (seção 5).
- Lê `requirements.txt` do próprio diretório `backend/` — nenhuma dependência nova precisa ser adicionada a esse arquivo para este Dockerfile funcionar.

```dockerfile
# /backend/Dockerfile
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
# 1 worker: ver PRD seção 2.4 (uploads em disco local + rate limit em memória
# de processo tornam >1 worker/réplica incorreto com o código atual).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

**Explicação passo a passo:**

| Linha(s) | O que faz | Por que essa abordagem |
|---|---|---|
| `# syntax=docker/dockerfile:1` | Fixa a versão da sintaxe do Dockerfile (BuildKit) | Garante que features modernas de cache do BuildKit funcionem de forma previsível em qualquer versão do Docker instalada no servidor |
| `FROM python:3.12-slim AS builder` | Abre o **primeiro** estágio, nomeado `builder` | `slim` já é uma imagem base pequena; nomear o estágio permite referenciá-lo depois com `COPY --from=builder` |
| `RUN apt-get install ... gcc ...` | Instala compilador C e headers do MySQL client | Algumas dependências Python compilam extensões nativas na instalação; sem isso, `pip install` falharia para essas libs em certas plataformas |
| `COPY requirements.txt .` (antes do `COPY . .`) | Copia **só** o arquivo de dependências primeiro | Técnica central de cache de camadas: o Docker só reexecuta o `RUN pip install` seguinte se `requirements.txt` mudar — um deploy que só altera código Python nunca reinstala dependência nenhuma |
| `pip install --user -r requirements.txt` | Instala os pacotes na pasta do usuário (`~/.local`), não no `site-packages` global | Isso é o que permite copiar **só** essa pasta para o próximo estágio com um único `COPY --from=builder`, sem levar o `pip` nem os `.whl` temporários junto |
| `FROM python:3.12-slim AS runtime` | Abre o **segundo** estágio, do zero | A imagem final não herda `gcc`/`pkg-config` do builder — eles simplesmente não existem aqui, reduzindo tamanho e superfície de ataque |
| `apt-get install ... curl` | Instala só o cliente HTTP `curl` na imagem final | Necessário porque a instrução `HEALTHCHECK` mais abaixo usa `curl` para consultar `/health` — `python:3.12-slim` não vem com nenhum cliente HTTP de linha de comando |
| `groupadd -r appgroup && useradd -r -g appgroup ...` | Cria um usuário e grupo de sistema (`-r`) dedicados | Base para rodar o processo da aplicação sem privilégios de root — se um invasor explorar uma falha na API, ele herda as permissões de `appuser`, não de root |
| `COPY --from=builder /root/.local /home/appuser/.local` | Traz só os pacotes Python já instalados do estágio `builder` | É a "ponte" entre os dois estágios — nenhuma ferramenta de build atravessa, só o resultado final |
| `ENV PATH=/home/appuser/.local/bin:$PATH` | Coloca os executáveis instalados via `--user` (como `alembic`, `uvicorn`) no `PATH` | Sem isso, o shell não encontraria esses comandos, pois eles não foram instalados no local padrão do sistema |
| `COPY --chown=appuser:appgroup . .` | Copia o código da aplicação já com o dono correto | Evita um `chown -R` separado (mais lento, cria uma camada extra); o `.dockerignore` (seção 2.2) garante que segredos e lixo de dev não entrem aqui |
| `chmod +x docker-entrypoint.sh` | Garante que o script seja executável dentro da imagem | O `.dockerignore`/Git podem preservar a permissão do host, mas isso não é garantido em todo ambiente de CI — esta linha remove a dependência dessa garantia |
| `mkdir -p uploads && chown appuser:appgroup uploads` | Cria a pasta de uploads com o dono certo antes do volume ser montado | O volume nomeado `backend_uploads` (seção 4.1) é montado exatamente neste caminho; se a pasta não existisse com o dono certo, `appuser` não teria permissão de escrita |
| `USER appuser` | A partir daqui, tudo roda como `appuser`, nunca mais como root | É a linha que efetivamente aplica o hardening — sem ela, todo o resto acima seria só decoração |
| `HEALTHCHECK ...` | Define como o Docker verifica se o container está "saudável", não só "rodando" | `--start-period=30s` dá tempo para o `docker-entrypoint.sh` terminar as migrations antes da primeira checagem contar como falha; `curl -fsS` falha (código ≠ 0) se a resposta não for 2xx, o que o `|| exit 1` transforma no sinal que o Docker entende |
| `ENTRYPOINT ["./docker-entrypoint.sh"]` | Todo `docker run`/`docker compose up` passa primeiro por este script | Ver conteúdo completo na seção 2.2 — ele aplica migrations e sai (via `exec "$@"`) para o comando real |
| `CMD [..., "--workers", "1"]` | Define o comando padrão executado pelo `ENTRYPOINT` via `exec "$@"` | `--workers 1` explícito documenta em código a limitação arquitetural do PRD (seção 2.4) em vez de depender do default implícito do Uvicorn, que poderia mudar entre versões |

### 2.2 `/backend/docker-entrypoint.sh` (já existe — sem alterações)

**Objetivo principal:** rodar, toda vez que o container do backend inicia, as duas tarefas que precisam acontecer antes da API aceitar requisições: aplicar migrations pendentes e garantir que o usuário admin exista.

**Conexões e integrações:** é chamado pelo `ENTRYPOINT` do Dockerfile (seção 2.1); lê as mesmas variáveis de ambiente que o `docker-compose.prod.yml` injeta no serviço `backend` (`DATABASE_URL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` etc., seção 4.1); o `python -m alembic upgrade head` opera sobre o histórico em `backend/alembic/versions/`.

```sh
#!/bin/sh
set -e

echo "Aplicando migrations (alembic upgrade head)..."
python -m alembic upgrade head

echo "Garantindo usuário admin (idempotente)..."
python scripts/seed_admin.py || true

exec "$@"
```

**Explicação passo a passo:**

| Linha | O que faz | Por que |
|---|---|---|
| `set -e` | Encerra o script imediatamente se qualquer comando falhar | Uma migration que falha não pode ser silenciosamente ignorada — o container deve morrer e o `HEALTHCHECK`/orquestrador devem perceber que algo deu errado, em vez de subir a API contra um schema incompleto |
| `python -m alembic upgrade head` | Aplica todas as migrations pendentes até a mais recente | Roda a cada subida do container — em um deploy de rotina (schema já atualizado) isso é uma operação rápida e sem efeito, o que é o comportamento correto de uma migration idempotente |
| `python scripts/seed_admin.py \|\| true` | Cria o usuário admin definido em `ADMIN_EMAIL`/`ADMIN_PASSWORD`, mas nunca derruba o container se falhar | O `\|\| true` é deliberado: o script já é idempotente (não recria o admin se ele existir) — se ele falhasse por outro motivo, isso não deveria impedir a API de subir, já que o admin normalmente já existe depois do primeiro deploy |
| `exec "$@"` | Substitui o processo do script pelo comando recebido (o `CMD` do Dockerfile) | `exec` (em vez de só chamar o comando) faz o Uvicorn virar o PID 1 do container, recebendo corretamente sinais como `SIGTERM` do Docker — sem isso, um `docker stop` demoraria até o timeout e mataria à força |

### 2.3 `/backend/.dockerignore` (já existe — sem alterações)

**Objetivo principal:** impedir que segredos, ambientes virtuais e artefatos de desenvolvimento entrem no contexto de build — e, por consequência, dentro da imagem — quando o Dockerfile executa `COPY . .`.

**Conexões e integrações:** atua exclusivamente sobre a instrução `COPY --chown=appuser:appgroup . .` do `/backend/Dockerfile` (seção 2.1); nenhuma outra peça do pipeline o lê.

```dockerignore
# /backend/.dockerignore
# Segredos — nunca devem entrar na imagem (Dockerfile faz "COPY . .")
.env
.env.*
!.env.example

# Ambiente virtual e caches — não fazem sentido dentro do container
# (a imagem usa o Python/pip do próprio sistema, ver Dockerfile)
.venv
venv
__pycache__
*.pyc
.pytest_cache
.ruff_cache
.coverage

# Dados locais — em runtime, /app/uploads é um volume Docker nomeado
# (ver docker-compose.yml, backend_uploads:/app/uploads); o conteúdo
# local não precisa (e não deve) ser copiado para dentro da imagem
uploads

# Legado / dev-only, sem uso em runtime
db_auditoria.sql
tests
.git
.gitignore
README.md
```

**Por que nenhuma linha muda:** o multi-stage do item 2.1 não introduz nenhum arquivo novo que precise ser excluído — o estágio `builder` só lê `requirements.txt`, e o estágio `runtime` faz o mesmo `COPY . .` de sempre. O padrão `.env.*` já cobriria um eventual `.env.prod` **se ele existisse dentro de `backend/`** — mas, pelo plano do PRD, `.env.prod` vive na raiz do repositório, não em `backend/`, por isso a proteção equivalente para ele é tratada à parte no `.gitignore` da raiz (seção 4.3 desta spec/`Code.md`).

---

## 3. Implementação do Frontend

### 3.1 `/frontend/Dockerfile`

**Objetivo principal:** empacotar o Next.js 16 em modo `standalone` — um servidor Node mínimo, sem o restante do toolchain de build — também rodando como usuário sem privilégios e com verificação de saúde nativa.

**Conexões e integrações:**
- Referenciado por `docker-compose.prod.yml` em `frontend.build.context: ./frontend`.
- Depende de `next.config.ts` ter `output: "standalone"` (já configurado, **sem alteração necessária** — é o que faz o `next build` gerar a pasta `.next/standalone` com um `server.js` autocontido, copiada no estágio `runner`).
- Em runtime, fala com o backend através da variável `BACKEND_API_URL=http://backend:8000`, injetada pelo `docker-compose.prod.yml` — nunca hardcoded na imagem (ver PRD, seção 2.3: essa chamada acontece só do lado do servidor Next.js, o navegador nunca vê essa URL).

```dockerfile
# /frontend/Dockerfile

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

**Explicação passo a passo:**

| Linha(s) | O que faz | Por que essa abordagem |
|---|---|---|
| `FROM node:20-slim AS deps` | Primeiro estágio, só para instalar dependências | Isolar `npm ci` em seu próprio estágio permite que o Docker o cacheie separadamente da etapa de build do código |
| `COPY package.json package-lock.json ./` (antes do resto do código) | Copia só os arquivos que descrevem dependências | Mesmo princípio do backend: essa camada (e o `npm ci` seguinte) só é invalidada quando o lockfile muda, não a cada alteração de componente React |
| `RUN npm ci` | Instala exatamente as versões travadas no `package-lock.json` | `npm ci` (diferente de `npm install`) é determinístico e mais rápido em CI/build — nunca escreve no lockfile, só o lê |
| `FROM node:20-slim AS builder` + `COPY --from=deps /app/node_modules` | Segundo estágio, reaproveitando os módulos já instalados | Evita rodar `npm ci` de novo; o build (`next build`) só precisa do código-fonte além disso |
| `COPY . .` | Copia o restante do código-fonte (App Router, `lib/`, etc.) | O `.dockerignore` do frontend (seção 3.2) garante que `.env*`, `.git` e `node_modules` locais não entrem aqui |
| `RUN npm run build` | Executa `next build`, que compila, faz type-check e gera `.next/standalone` | É o passo mais caro do Dockerfile — por isso fica isolado em seu próprio estágio, para que uma mudança só de configuração de runtime (estágio seguinte) não force um rebuild dele |
| `FROM node:20-slim AS runner` | Terceiro e último estágio — a imagem que de fato roda em produção | Começa do zero, sem `node_modules` completo nem código-fonte — só o que o `standalone` empacotou |
| `RUN groupadd -r nodejs && useradd -r -g nodejs -d /app nextjs` | Cria usuário/grupo de sistema não-root | Mesmo racional de segurança do backend — o processo Node não roda como root |
| `COPY --from=builder --chown=nextjs:nodejs ...` (3 linhas) | Traz só `public/`, `.next/standalone` e `.next/static` do estágio `builder`, já com o dono certo | São exatamente os 3 artefatos que o modo `standalone` do Next.js define como necessários para rodar — nada de `node_modules` completo, nada de código-fonte TypeScript |
| `USER nextjs` | A partir daqui, tudo roda como `nextjs` | Aplica o hardening definido acima |
| `EXPOSE 3000` / `ENV PORT=3000` | Documenta e fixa a porta que o `server.js` do modo standalone escuta | O `server.js` gerado pelo Next.js lê `process.env.PORT` — declarar explicitamente evita depender do default interno do framework |
| `HEALTHCHECK ... CMD node -e "fetch(...)..."` | Verifica a saúde usando o próprio Node, sem `curl`/`wget` | `node:20-slim` não inclui nenhum cliente HTTP de linha de comando; a API `fetch` já é nativa a partir do Node 18, então não é necessário instalar nenhum pacote extra só para o healthcheck — ao contrário do backend, que precisou instalar `curl` |
| `CMD ["node", "server.js"]` | Comando final: inicia o servidor standalone gerado pelo Next.js | Este `server.js` já inclui o runtime HTTP do Next — não há Nginx, PM2 nem `next start` aqui, é o próprio framework servindo diretamente |

### 3.2 `/frontend/.dockerignore` (já existe — sem alterações)

**Objetivo principal:** o mesmo do lado do backend — impedir que segredos e artefatos locais entrem no contexto de build usado pelos `COPY . .` dos estágios `deps`/`builder`.

**Conexões e integrações:** atua sobre os `COPY` do `/frontend/Dockerfile` (seção 3.1); em particular, a exclusão de `node_modules` e `.next` é o que garante que a imagem nunca reaproveite um build ou uma instalação feita na máquina local de quem faz o build.

```dockerignore
# /frontend/.dockerignore
# Segredos — nunca devem entrar na imagem/no contexto de build
# (Dockerfile faz "COPY . ." no estágio builder)
.env
.env.*

# node_modules já é copiado explicitamente do estágio "deps" via
# "COPY --from=deps" — copiá-lo de novo aqui só desperdiça contexto
# de build (centenas de MB) e pode sobrescrever com uma versão errada
node_modules

# Builds anteriores/caches locais — o build de produção deve ser
# gerado do zero dentro do container, nunca reaproveitar um .next local
.next
out

# Dev-only, sem uso no build de produção
.git
.gitignore
README.md
*.md
tsconfig.tsbuildinfo
```

**Por que nenhuma linha muda:** o Dockerfile modificado (3.1) não passou a copiar nenhum arquivo novo do disco além do que já copiava — a mudança foi inteiramente dentro do estágio `runner`, sobre artefatos que já vêm do estágio `builder` via `COPY --from=builder`, não do disco do host.

---

## 4. Orquestração e Redes (Docker Compose + Nginx)

### 4.1 `/docker-compose.prod.yml`

**Objetivo principal:** subir os 4 serviços de produção (`mysql`, `backend`, `frontend`, `nginx`) em uma única rede isolada, com só o Nginx acessível de fora do servidor.

**Conexões e integrações:**
- `backend.build.context: ./backend` → `/backend/Dockerfile` (seção 2.1).
- `frontend.build.context: ./frontend` → `/frontend/Dockerfile` (seção 3.1).
- Todas as variáveis `${...}` vêm de `.env.prod` no servidor (modelo em `.env.prod.example`, seção 4.3), carregado via `docker compose --env-file .env.prod`.
- `nginx.volumes` monta `./nginx/nginx.conf` (seção 4.2) e os certificados emitidos pelo `certbot` no host (`/etc/letsencrypt`).
- É o arquivo que o job `deploy` do GitHub Actions manda o servidor reconstruir/recriar (seção 5).

```yaml
# /docker-compose.prod.yml
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

**Explicação passo a passo (por serviço):**

| Serviço/chave | O que faz | Por que |
|---|---|---|
| `mysql.environment.MYSQL_*` com `${VAR:?mensagem}` | Exige que a variável exista em `.env.prod`; se faltar, o `docker compose` recusa subir **com uma mensagem clara**, em vez de criar o banco com senha vazia | Fail-fast: um `.env.prod` incompleto nunca deve resultar num banco inseguro por omissão |
| `mysql.healthcheck` (`mysqladmin ping`) | Só marca o container como `healthy` quando o MySQL aceita conexões | É a condição que `backend.depends_on.mysql.condition: service_healthy` espera — o backend não tenta migrar o schema contra um banco ainda inicializando |
| `mysql` sem `ports:` | Não expõe `3306` para fora do container | O único cliente do MySQL é o `backend`, que já está na mesma rede `auditoria-net` — não há motivo para essa porta existir fora do Docker |
| `backend.depends_on.mysql.condition: service_healthy` | Só cria o container do backend depois do MySQL responder saudável | Evita a corrida clássica "app subiu antes do banco aceitar conexões", que faria o `alembic upgrade head` do `docker-entrypoint.sh` falhar na primeira tentativa |
| `backend.environment.DATABASE_URL` | Monta a URL de conexão usando o hostname **do serviço** (`mysql`), não `127.0.0.1` | Dentro da rede Docker, `mysql` resolve para o IP interno do container daquele serviço — é assim que containers se enxergam pelo nome, sem precisar saber IPs |
| `backend.environment.CORS_ALLOWED_ORIGINS: ${CORS_ALLOWED_ORIGINS:?...}` | Obrigatório, sem default | Impede reusar por engano o default de desenvolvimento (`http://localhost:3000`) em produção — se `.env.prod` não declarar o domínio real, o compose recusa subir |
| `backend` sem `ports:` | API não é alcançável diretamente de fora | Reforça o achado do PRD (seção 2.3): o navegador nunca fala com o backend; só o `frontend` (via `BACKEND_API_URL`) e opcionalmente o `nginx` (seção 4.2) o alcançam, ambos dentro da mesma rede |
| `frontend.depends_on.backend.condition: service_healthy` | Só sobe o frontend depois do backend responder saudável | O frontend faz chamadas ao backend em várias rotas server-side logo na primeira requisição — subir antes só adiaria o erro para o primeiro clique do usuário |
| `frontend.environment.BACKEND_API_URL: http://backend:8000` | Mesma lógica do `DATABASE_URL` — hostname pelo nome do serviço | É a única forma de o frontend alcançar o backend nesta topologia (sem porta publicada) |
| `nginx.depends_on: [frontend, backend]` | Só sobe o Nginx depois dos dois serviços de aplicação existirem | Evita que o Nginx comece a responder tráfego para upstreams que ainda não existem (o `depends_on` aqui é sem `condition`, então garante ordem de criação, não que já estejam saudáveis — os `location`s do Nginx toleram uma reconexão se o upstream ainda estiver de pé) |
| `nginx.ports: ["80:80", "443:443"]` | **Único** serviço com porta publicada no host | Materializa a decisão central da topologia: um único ponto de entrada público |
| `nginx.volumes` (3 linhas) | Monta a config (`:ro`) e os certificados do Let's Encrypt (`:ro`) dentro do container | `:ro` (read-only) é intencional — o container do Nginx nunca precisa escrever nesses caminhos, só lê-los |
| `logging.driver: json-file` + `max-size`/`max-file` em cada serviço de app | Limita o log de cada container a 3 arquivos de 10 MB (30 MB no total, por serviço) | Sem isso, o driver padrão do Docker não tem limite — em meses de operação, os logs podem encher o disco do servidor sozinhos |
| `volumes: { mysql_data, backend_uploads }` | Declara os dois volumes nomeados usados acima | Sobrevivem a `docker compose down` (sem `-v`) e a rebuilds de imagem — só um `docker compose down -v` explícito os apagaria |
| `networks.auditoria-net.driver: bridge` | Cria uma rede isolada só para esta stack | Container-a-container por nome de serviço (DNS interno do Docker) funciona só dentro da mesma rede — é o mecanismo que substitui "portas publicadas + `localhost`" usado em dev |

### 4.2 `/nginx/nginx.conf`

**Objetivo principal:** ser o único ponto de entrada público da aplicação — termina TLS, aplica headers de segurança, e decide para qual serviço interno cada requisição vai.

**Conexões e integrações:**
- Montado pelo serviço `nginx` do `docker-compose.prod.yml` (seção 4.1) em `/etc/nginx/nginx.conf`.
- `proxy_pass http://frontend:3000` e `http://backend:8000` resolvem pelo DNS interno da rede `auditoria-net` — só funcionam porque `nginx` está na mesma rede que os outros dois serviços.
- `ssl_certificate`/`ssl_certificate_key` apontam para o caminho onde o `certbot` (rodando no **host**, fora do Docker) grava os certificados — por isso `/etc/letsencrypt` é montado como volume no serviço `nginx` (seção 4.1).

```nginx
# /nginx/nginx.conf
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
        # nunca fala com :8000 diretamente.
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

> ⚠️ **Antes de aplicar**: substituir as 3 ocorrências de `SEU_DOMINIO_AQUI` pelo domínio real, definido antes de emitir o certificado (seção 7.2).

**Explicação passo a passo:**

| Bloco/diretiva | O que faz | Por que |
|---|---|---|
| `events { worker_connections 1024; }` | Define quantas conexões simultâneas cada worker do Nginx aceita | 1024 é suficiente para o volume de tráfego esperado de uma plataforma interna de auditoria; pode ser aumentado depois sem mudar mais nada |
| `client_max_body_size 50M` | Eleva o limite padrão de corpo de requisição (1 MB) para 50 MB | O upload de evidências (`backend/app/services/storage.py`) frequentemente envia PDFs — sem isso, o Nginx rejeitaria o upload antes mesmo de ele chegar ao backend |
| `proxy_connect_timeout`/`proxy_send_timeout`/`proxy_read_timeout: 60s` | Tempo máximo que o Nginx espera pelo backend/frontend antes de desistir | 60s cobre operações mais lentas (ex.: geração do laudo em PDF) sem deixar uma conexão travada indefinidamente em caso de falha real |
| **Server `:80`**, `location /.well-known/acme-challenge/` | Serve os arquivos de desafio do Let's Encrypt | O `certbot` (rodando no host) precisa que uma URL pública `http://dominio/.well-known/...` responda para provar que você controla o domínio — essa location existe só para isso |
| **Server `:80`**, `location / { return 301 https://... }` | Redireciona todo o resto do tráfego HTTP para HTTPS | Garante que ninguém use a aplicação sem TLS, mesmo que digite `http://` manualmente |
| **Server `:443`**, `ssl_certificate`/`ssl_certificate_key` | Aponta para os arquivos gerados pelo `certbot` | `fullchain.pem` inclui o certificado + a cadeia intermediária; `privkey.pem` é a chave privada — os dois são obrigatórios para o TLS funcionar |
| `ssl_protocols TLSv1.2 TLSv1.3` | Desabilita versões antigas e inseguras do protocolo (SSLv3, TLS 1.0/1.1) | Requisito básico de qualquer checklist de segurança atual (também exigido por auditorias PCI-DSS/ISO 27001 — relevante para uma plataforma de auditoria) |
| `add_header Strict-Transport-Security ...` | Instrui o navegador a *nunca mais* tentar `http://` para este domínio, por até 2 anos (`max-age=63072000`) | Protege contra downgrade attacks mesmo que um link antigo aponte para `http://` |
| `add_header X-Content-Type-Options nosniff` | Impede que o navegador tente "adivinhar" o tipo de um arquivo servido | Mitiga uma classe de ataque onde um upload malicioso é interpretado como script pelo navegador da vítima |
| `add_header X-Frame-Options DENY` | Impede que a aplicação seja carregada dentro de um `<iframe>` de outro site | Proteção contra clickjacking |
| `location /` → `proxy_pass http://frontend:3000` | Encaminha toda requisição não capturada pelas locations mais específicas para o Next.js | É a rota que o usuário final realmente usa — o `proxy_set_header Host $host` garante que o Next.js veja o domínio real (usado por ele para gerar links absolutos, cookies, etc.) |
| `proxy_set_header X-Forwarded-Proto $scheme` | Informa ao Next.js que a conexão original era HTTPS, mesmo a conexão interna Nginx→frontend sendo HTTP simples | Sem isso, o framework poderia gerar redirecionamentos ou cookies `Secure` incorretos, achando que a conexão original não era segura |
| `location /health`, `/docs`, `/openapi.json` | Encaminham para o backend, **fora** do fluxo normal da aplicação | Servem só para operação (monitoramento externo, consulta pontual ao Swagger) — comentadas com a recomendação de restringir por IP (`allow`/`deny`) antes de expor publicamente |

### 4.3 `/.env.prod.example`

**Objetivo principal:** ser o template versionado (sem nenhum segredo real) de todas as variáveis que `docker-compose.prod.yml` exige — a referência que quem for aplicar o deploy copia para `.env.prod` no servidor e preenche.

**Conexões e integrações:**
- Cada chave aqui corresponde 1:1 a um `${VAR:?...}`/`${VAR:-default}` lido pelo `backend`/`mysql` em `docker-compose.prod.yml` (seção 4.1) — não sobra nem falta nenhuma variável nos dois arquivos.
- A cópia preenchida (`.env.prod`) é criada manualmente no servidor no primeiro deploy (seção 7.2, passo 2) e nunca é commitada — é justamente esse arquivo real que o `.gitignore` (seção 4.4) passa a proteger.
- É o mesmo arquivo referenciado em `docker compose -f docker-compose.prod.yml --env-file .env.prod` tanto no deploy manual (seção 7.2) quanto no job `deploy` do GitHub Actions (seção 5.1).

```bash
# /.env.prod.example
# Copie para ".env.prod" no servidor e preencha com valores reais.
# Gere segredos com: python -c "import secrets; print(secrets.token_urlsafe(48))"

# ---- MySQL ----
MYSQL_ROOT_PASSWORD=
MYSQL_PASSWORD=

# ---- JWT ----
JWT_SECRET=
JWT_EXPIRES_MINUTES=15
JWT_REFRESH_EXPIRES_DAYS=7

# ---- CORS (domínio real do frontend em produção, sem barra final) ----
CORS_ALLOWED_ORIGINS=https://SEU_DOMINIO_AQUI

# ---- Usuário admin inicial (seed_admin.py, via docker-entrypoint.sh) ----
ADMIN_EMAIL=
ADMIN_FULL_NAME=Administrador
ADMIN_PASSWORD=

# ---- SMTP (opcional — deixe em branco para desabilitar envio de e-mail) ----
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_USE_TLS=true
```

**Explicação passo a passo:**

| Bloco | O que faz | Por que |
|---|---|---|
| `MYSQL_ROOT_PASSWORD` / `MYSQL_PASSWORD` | Senhas do usuário root e do usuário de aplicação (`auditoria_app`) do MySQL | Ambas obrigatórias — o `docker-compose.prod.yml` usa `:?defina no .env.prod` para as duas, então o Compose recusa subir se qualquer uma faltar |
| `JWT_SECRET` | Chave usada para assinar/validar os tokens de acesso e refresh | Sem default por design — um segredo fraco/genérico compartilhado entre ambientes quebraria o isolamento entre dev e produção |
| `JWT_EXPIRES_MINUTES` / `JWT_REFRESH_EXPIRES_DAYS` | Tempo de vida do access token e do refresh token | Já têm default (`:-15`/`:-7`) no compose — aparecem aqui só para tornar explícito o que está em vigor, não para forçar preenchimento |
| `CORS_ALLOWED_ORIGINS` | Domínio(s) autorizados a chamar a API a partir do navegador | Deliberadamente **sem** default de produção no exemplo — obriga quem aplica o deploy a substituir `SEU_DOMINIO_AQUI` pelo domínio real (o mesmo que entra em `nginx/nginx.conf`, seção 4.2) |
| `ADMIN_EMAIL` / `ADMIN_FULL_NAME` / `ADMIN_PASSWORD` | Credenciais do usuário administrador criado pelo `scripts/seed_admin.py` na primeira subida | `ADMIN_EMAIL`/`ADMIN_PASSWORD` são obrigatórios (`:?...`); só `ADMIN_FULL_NAME` tem default, por ser puramente cosmético |
| `SMTP_*` | Configuração de envio de e-mail (notificações) | Todos têm default vazio/`587`/`true` no compose — o backend já trata SMTP não configurado como "recurso desligado", então preencher esses campos é opcional, não um bloqueador de deploy |

### 4.4 `/.gitignore`

**Objetivo principal:** garantir que o `.env.prod` real — criado manualmente no servidor a partir do template acima — nunca seja commitado por engano, mesmo que alguém rode `git add .` dentro de `/opt/auditoria`.

**Conexões e integrações:** protege especificamente o arquivo que `docker-compose.prod.yml` consome via `--env-file .env.prod` (seção 4.1) e que é criado no passo 2 do deploy manual (seção 7.2) — sem outra peça do pipeline lê ou escreve neste arquivo.

```gitignore
# ---- Produção (nunca commitar segredos reais) ----
.env.prod
.env.prod.*
!.env.prod.example
```

> Adicionar ao final do `.gitignore` já existente na raiz do repositório — as regras atuais (`.env`, `.env.*.local`, `!.env.example`) continuam valendo para o `.env` de desenvolvimento e não cobrem `.env.prod`, por isso o bloco é necessário.

**Explicação passo a passo:**

| Linha | O que faz | Por que |
|---|---|---|
| `.env.prod` | Ignora o arquivo real de produção | É exatamente o arquivo criado à mão no servidor (seção 7.2) — nenhuma versão preenchida dele deve existir no histórico do Git |
| `.env.prod.*` | Ignora também variantes (ex.: `.env.prod.local-test`, usado no teste local da seção 7.1) | Sem essa linha, um arquivo de teste criado seguindo o próprio guia desta doc poderia ser commitado sem querer |
| `!.env.prod.example` | Reabre a exceção para o template versionado | Sem esta negação, o padrão `.env.prod.*` acima ignoraria também o próprio `.env.prod.example` (seção 4.3), que **precisa** estar no repositório |

---

## 5. Automação CI/CD (GitHub Actions)

### 5.1 `/.github/workflows/deploy.yml`

**Objetivo principal:** ser o único caminho para código chegar em produção — rodando os testes de backend e frontend em paralelo, e só então (e só em `push` direto na `main`) conectando via SSH ao servidor para atualizar a stack.

**Conexões e integrações:**
- Instala e testa exatamente com as mesmas versões dos Dockerfiles: Python 3.12 (igual ao `FROM python:3.12-slim` do backend) e Node 20 (igual ao `FROM node:20-slim` do frontend) — evita o clássico "passou no CI, falhou na imagem" por divergência de versão.
- O job `deploy` executa, dentro do servidor, exatamente os comandos manuais descritos na seção 7.2 — a automação não inventa nenhum passo novo, só repete o que já foi validado manualmente uma vez.
- Lê os secrets `PROD_HOST`, `PROD_USER`, `PROD_SSH_KEY` (e opcionalmente `PROD_SSH_PORT`), cadastrados em **Settings → Secrets and variables → Actions** do repositório GitHub.
- Chama `docker compose -f docker-compose.prod.yml --env-file .env.prod` — os dois arquivos das seções 4.1 e do servidor (`.env.prod`, nunca versionado).

```yaml
# /.github/workflows/deploy.yml
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
            # próprio servidor — só reinstala pip/npm quando
            # requirements.txt/package-lock.json mudam (ver seções 2.1/3.1).
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

**Explicação passo a passo, job por job:**

#### `backend-tests`

| Step | O que faz | Por que |
|---|---|---|
| `actions/checkout@v4` | Clona o repositório no runner do GitHub | Todo workflow precisa disso como primeiro passo — sem ele não há código para testar |
| `actions/setup-python@v5` com `cache: "pip"` | Instala Python 3.12 e ativa cache do `pip` chaveado por `backend/requirements.txt` | Builds seguintes do CI (não do servidor) reaproveitam pacotes já baixados, mesmo em um runner efêmero — acelera o job sem depender de nada externo |
| `pip install -r requirements.txt` | Instala as mesmas dependências do `backend/Dockerfile`, incluindo `ruff` e `pytest` (já listados no arquivo) | Garante que o CI teste exatamente o que vai para produção, sem lista de dependências paralela |
| `ruff check .` | Roda o linter com a config já existente em `backend/ruff.toml` | Pega erros de código morto/variáveis não usadas (`select = ["F"]`) antes de chegar em produção |
| `pytest -v` com `DATABASE_URL`/`JWT_SECRET` dummy | Roda a suíte de testes (~300+ casos) | `backend/tests/conftest.py` substitui a engine real por SQLite em memória antes de qualquer teste — por isso **não existe** nenhum `services: mysql:` neste job, ao contrário do que um workflow genérico teria |

#### `frontend-tests`

| Step | O que faz | Por que |
|---|---|---|
| `actions/setup-node@v4` com `cache: "npm"` | Instala Node 20 e ativa cache do npm chaveado por `frontend/package-lock.json` | Mesmo racional do cache de pip acima |
| `npm ci` | Instalação determinística a partir do lockfile | Nunca deve divergir do que `frontend/Dockerfile` instala no estágio `deps` |
| `npm run lint` | Roda ESLint 9 com a config já existente (`eslint-config-next`) | Pega problemas de estilo/qualidade antes do build |
| `npm test` | Roda `vitest run` (modo "executa uma vez e sai", não watch) | Cobre os testes de contrato do frontend (Server Actions mockando `callBackend`) |
| `npm run build` (por último) | Roda `next build`, que compila TypeScript e faz bundling | É o passo que mais demora — colocá-lo por último significa que, se o lint ou os testes já falharam, o job para antes de gastar tempo com o build |

#### `deploy`

| Elemento | O que faz | Por que |
|---|---|---|
| `needs: [backend-tests, frontend-tests]` | O job só começa se os dois anteriores tiverem **sucesso** | Se qualquer um falhar, o GitHub Actions nunca inicia este job — não é preciso repetir a checagem de sucesso dentro do próprio job |
| `if: github.event_name == 'push' && github.ref == 'refs/heads/main'` | Segunda barreira, independente da primeira | Um `pull_request` também dispara os dois jobs de teste (por causa do `on: pull_request` no topo), mas nunca chega a satisfazer esta condição — o deploy realmente nunca roda para PR, mesmo que alguém aprove/marque como pronto |
| `uses: appleboy/ssh-action@v1.0.3` | Abre uma sessão SSH usando os 3–4 secrets do repositório e executa o bloco `script:` remotamente | É a ponte entre o runner efêmero do GitHub e o servidor persistente — nenhuma outra parte do workflow toca o servidor diretamente |
| `git fetch origin main && git reset --hard origin/main` | Atualiza o clone local do servidor para o commit exato que acabou de passar nos testes | `reset --hard` (em vez de `pull`) evita conflitos de merge no servidor — o servidor nunca tem commits próprios, só reflete a `main` |
| `docker compose ... build` | Reconstrói as imagens **no próprio servidor** | Decisão registrada no PRD (seção 3.3): o cache de camadas do Docker já persiste no disco do servidor entre deploys, sem precisar de um registry de imagens |
| `docker compose ... up -d` | Recria só os containers cuja configuração/imagem mudou | Um deploy que só mudou o backend recria **apenas** o container `backend` — `mysql` e `frontend`, se inalterados, nem reiniciam |
| Laço `for i in $(seq 1 15); do ... done` | Tenta `curl /health` até 15 vezes, com 2s de espera entre tentativas (até 30s no total) | Dá tempo para o `HEALTHCHECK`/`docker-entrypoint.sh` do backend terminarem migrations antes de declarar sucesso ou falha |
| `if [ "$STATUS" != "200" ]; then ... exit 1; fi` | Se depois de 30s o backend ainda não respondeu 200, o step (e o job) falha | Transforma uma falha silenciosa de subida em um workflow **vermelho** no GitHub — quem fez o push é avisado imediatamente, em vez de descobrir só quando um usuário reportar o sistema fora do ar |
| `docker image prune -f` | Remove imagens Docker antigas, sem tag, que ficaram para trás após o rebuild | Evita que o disco do servidor cresça indefinidamente a cada deploy — mas preserva o cache de camadas (que vive em outra parte do storage driver do Docker, não nas imagens finais soltas) |

> **Nota de honestidade técnica sobre "deploy sem downtime":** `docker compose up -d` recria um container parando o antigo e só então iniciando o novo — para o serviço que mudou, isso é uma janela de poucos segundos de indisponibilidade (não é *blue-green* nem *rolling update* real), e serviços que não mudaram (ex.: `mysql`, ou `frontend` quando só o backend mudou) **não são tocados e não têm downtime algum**. Um deploy verdadeiramente zero-downtime exigiria manter duas instâncias do serviço alterado rodando simultaneamente até a virada de tráfego — o que entra em tensão direta com a restrição de "1 worker/0 réplicas" do PRD (seção 2.4) e está fora do escopo desta primeira versão. Para o perfil de uso descrito (plataforma interna de auditoria, não um serviço de consumo massivo), uma janela de poucos segundos por deploy é um trade-off aceito e documentado, não um problema escondido. Evoluir para *blue-green* de verdade — resolvendo antes as duas causas-raiz do "1 worker" — é um passo futuro, não coberto por este guia.

---

## 6. Documentação (README.md)

### 6.1 `/README.md`

**Objetivo principal:** registrar, no ponto de entrada do repositório, que a stack agora tem um caminho de produção (Docker Compose + Nginx + CI/CD) — sem duplicar aqui o conteúdo operacional, que já vive por inteiro nesta doc (seção 7) e no `prd_deploy_producao.md`.

**Conexões e integrações:** o README já documenta a stack de **desenvolvimento** (`docker-compose.yml` na raiz, seção "Como rodar", linhas ~139–176) — a edição apenas acrescenta uma seção irmã para produção, apontando para `docker-compose.prod.yml` (seção 4.1), `nginx/nginx.conf` (seção 4.2) e `.github/workflows/deploy.yml` (seção 5.1), em vez de repetir os comandos.

```markdown
### Opção C — Deploy em produção (Docker Compose + Nginx + CI/CD)

A stack de produção roda em 4 serviços (`mysql`, `backend`, `frontend`, `nginx`),
com o Nginx como único ponto de entrada público (TLS via Let's Encrypt) e deploy
automatizado por push na `main` via GitHub Actions.

- Arquivos: `docker-compose.prod.yml`, `nginx/nginx.conf`, `.env.prod.example`,
  `.github/workflows/deploy.yml`.
- Guia completo (passo a passo, primeiro deploy manual, troubleshooting):
  [`docs/Code.md`](docs/Code.md#7-guia-prático-de-execução).
- Decisões e justificativas de arquitetura: [`docs/prd_deploy_producao.md`](docs/prd_deploy_producao.md).
```

**Explicação passo a passo:**

| Trecho | O que faz | Por que |
|---|---|---|
| Título "Opção C" | Soma-se à "Opção A" (Compose completo) e "Opção B" (só MySQL, backend local) já existentes no README | Mantém o padrão de nomenclatura do documento em vez de criar uma seção solta com título diferente |
| Lista de arquivos envolvidos | Dá a quem lê o README, sem abrir mais nada, os nomes reais dos arquivos de produção | Responde diretamente ao tipo de lacuna que motivou esta atualização: "qual arquivo real corresponde a isso?" |
| Link para `docs/Code.md#7-...` | Aponta para o guia prático (seção 7 desta doc), não repete os comandos | Uma única fonte de verdade para os comandos de deploy evita os dois textos divergirem com o tempo |
| Link para `docs/prd_deploy_producao.md` | Aponta para o porquê das escolhas (1 worker, sem réplica, Nginx único ponto de entrada, etc.) | Separa "o quê/como" (`Code.md`) de "por quê" (PRD), consistente com a "Origem" declarada no cabeçalho desta doc |

---

## 7. Guia Prático de Execução

### 7.1 Testar localmente antes de qualquer `push`

Reproduza exatamente o que o CI vai rodar, na sua máquina, antes de abrir o PR:

```bash
# ---- Backend: os mesmos 2 comandos do job "backend-tests" ----
cd backend
pip install -r requirements.txt
ruff check .
DATABASE_URL=sqlite:///:memory: JWT_SECRET=local_test CORS_ALLOWED_ORIGINS=http://localhost:3000 pytest -v

# ---- Frontend: os mesmos 3 comandos do job "frontend-tests" ----
cd ../frontend
npm ci
npm run lint
npm test
BACKEND_API_URL=http://backend:8000 JWT_SECRET=local_test JWT_ALGORITHM=HS256 npm run build
```

Depois, valide as **imagens de produção** (não o `docker compose up` de desenvolvimento) de forma isolada:

```bash
# Backend
cd backend
docker build -t auditoria-backend:test .
docker run --rm -e DATABASE_URL=sqlite:////tmp/x.db -e JWT_SECRET=test_only -p 8000:8000 auditoria-backend:test &
sleep 3 && curl -f http://localhost:8000/health   # esperado: {"status":"Ok",...}
docker inspect --format='{{.Config.User}}' auditoria-backend:test   # esperado: "appuser"

# Frontend
cd ../frontend
docker build -t auditoria-frontend:test .
docker run --rm -e BACKEND_API_URL=http://localhost:8000 -e JWT_SECRET=test_only -p 3000:3000 auditoria-frontend:test &
sleep 3 && curl -I http://localhost:3000/         # esperado: HTTP/1.1 200
docker inspect --format='{{.Config.User}}' auditoria-frontend:test   # esperado: "nextjs"
```

Por fim, valide o `docker-compose.prod.yml` (sintaxe e interpolação de variáveis, **sem** precisar de um domínio real ainda):

```bash
cd ..   # raiz do repositório
cp .env.prod.example .env.prod.local-test
# preencha .env.prod.local-test com valores de teste (não use senhas reais)
docker compose -f docker-compose.prod.yml --env-file .env.prod.local-test config
# esperado: nenhum erro de "variable is not set" — se aparecer, falta preencher algo no arquivo
```

### 7.2 Aplicar no servidor (primeiro deploy — manual)

Feito uma única vez, antes de existir qualquer automação. Resumo operacional (comandos completos e comentados: PRD, seções 5.1–5.6):

```bash
# 1. Provisionar: usuário de deploy, Docker, firewall, clone do repositório
adduser --disabled-password --gecos "" deploy && usermod -aG docker deploy
# ... instalar Docker Engine + compose plugin, liberar 22/80/443 no ufw ...
sudo mkdir -p /opt/auditoria && sudo chown deploy:deploy /opt/auditoria
su - deploy -c "git clone <URL-do-repositório> /opt/auditoria"

# 2. Criar .env.prod a partir do modelo versionado (nunca commitar o resultado)
cd /opt/auditoria
cp .env.prod.example .env.prod
nano .env.prod        # preencher com valores reais gerados via `secrets.token_hex`/`token_urlsafe`
chmod 600 .env.prod

# 3. Emitir o certificado TLS (domínio precisa já apontar para o IP do servidor)
sudo apt install -y certbot
sudo certbot certonly --standalone -d SEU_DOMINIO_AQUI \
  --email rodrigo.santos@stwbrasil.com --agree-tos --non-interactive

# 4. Ajustar nginx/nginx.conf: substituir SEU_DOMINIO_AQUI (3 ocorrências) pelo domínio real
sed -i 's/SEU_DOMINIO_AQUI/dominio-real.com.br/g' nginx/nginx.conf

# 5. Primeiro build + subida manual
docker compose -f docker-compose.prod.yml --env-file .env.prod build
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
docker compose -f docker-compose.prod.yml ps    # os 4 serviços devem chegar a "healthy"
```

### 7.3 Validar que o deploy manual funcionou

```bash
curl -I https://SEU_DOMINIO_AQUI/          # esperado: HTTP/2 200 (frontend)
curl https://SEU_DOMINIO_AQUI/health       # esperado: {"status":"Ok","db_status":"Ok",...}
docker compose -f docker-compose.prod.yml exec nginx nginx -t   # esperado: "test is successful"
```

Se tudo respondeu como esperado, popule os dados iniciais (uma vez):

```bash
docker compose -f docker-compose.prod.yml exec backend python scripts/seed_catalog.py
docker compose -f docker-compose.prod.yml exec backend python scripts/seed_dashboard_templates.py
```

### 7.4 Ligar a automação (GitHub Actions) e validar o pipeline

Só depois de 6.2/6.3 confirmados:

1. No repositório GitHub: **Settings → Secrets and variables → Actions** → cadastrar `PROD_HOST`, `PROD_USER` (`deploy`), `PROD_SSH_KEY` (chave privada dedicada, seção 4.2 do `Spec.md`).
2. Adicionar o job `deploy` ao `.github/workflows/deploy.yml` (se ainda não tiver sido incluído desde o início).
3. **Testar o caminho que NÃO deve disparar deploy:** abrir um Pull Request qualquer contra `main` e observar a aba **Actions** — `backend-tests`/`frontend-tests` devem rodar; `deploy` deve aparecer como **skipped**.
4. **Testar o caminho que deve disparar deploy:** fazer merge desse PR (ou um push direto controlado) e acompanhar os 3 jobs — o job `deploy` deve conectar via SSH, reconstruir, e o *smoke test* interno deve encontrar `200` em `/health` antes dos 30s de tentativas.
5. Confirmar de fora do servidor: `curl https://SEU_DOMINIO_AQUI/health` deve continuar respondendo 200 logo após o workflow terminar.

### 7.5 Problemas comuns e como diagnosticar

| Sintoma | Comando de diagnóstico | Causa provável |
|---|---|---|
| `docker compose up` recusa subir com "variable is not set" | `cat .env.prod` — conferir se a variável citada no erro está preenchida | Uma das chaves com `:?mensagem` no `docker-compose.prod.yml` está ausente/vazia em `.env.prod` |
| `docker compose ps` mostra `backend` como `unhealthy` | `docker compose -f docker-compose.prod.yml logs backend` | Geralmente falha de migration (`alembic upgrade head`) ou `DATABASE_URL` incorreta — ver se `mysql` está `healthy` primeiro |
| Nginx retorna `502 Bad Gateway` | `docker compose -f docker-compose.prod.yml logs nginx` + `docker compose ps` | O `frontend`/`backend` não está `running`/`healthy`, ou o nome do serviço no `proxy_pass` não bate com o `container_name`/nome do serviço no compose |
| Workflow do GitHub Actions falha no step SSH | Testar manualmente: `ssh -i <chave> deploy@<PROD_HOST>` da sua máquina | Chave pública não está em `~deploy/.ssh/authorized_keys`, firewall bloqueando a porta SSH, ou secret `PROD_SSH_KEY` colado incompleto |
| Job `deploy` roda mesmo em Pull Request | Ver o YAML do `if:` do job — deve ser exatamente `github.event_name == 'push' && github.ref == 'refs/heads/main'` | Erro de digitação na condição, ou uso de `github.event.pull_request.base.ref` por engano |
| Certificado expira / renovação falha | `sudo certbot renew --dry-run` no host | Cron/timer do certbot não configurado, ou porta 80 bloqueada no momento da renovação (o Nginx em container precisa da location `/.well-known/acme-challenge/` respondendo) |
