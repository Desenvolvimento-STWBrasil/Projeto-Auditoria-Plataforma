# Deploy e Configuração de Produção — Guia Completo

| Campo         | Valor                                                              |
|---------------|--------------------------------------------------------------------|
| **Data**      | 2026-06-24 (criação) · 2026-07-27 (rev. 1.1) · 2026-08-11 (rev. 1.2) · 2026-08-12 (rev. 1.3) · 2026-08-17 (rev. 1.4) · 2026-08-24 (rev. 2.0) · **2026-08-26 (rev. 2.1 — esta revisão)** |
| **Versão**    | **v2.2**                                                           |
| **Audiência** | DevOps, Tech Lead, Desenvolvedor Sênior                           |
| **Status**    | 🟡 **Deploy DESBLOQUEADO no código, pendente de validação** — os 3 bloqueadores da rev. 2.0 foram corrigidos em `4fd576f`. Restam pendências de **verificação**, não de código: nem o CI nem `docker build`/`docker run` jamais executaram de verdade |
| **Relacionados** | `executar_projeto.md`, `plano_implementacao.md` (seção H), `roadmap.md` (Fase 3), `relatorio_melhorias.md` |

> **Objetivo deste documento:** guia completo para fazer o deploy em um servidor de produção — dos Dockerfiles à configuração de Nginx, HTTPS, variáveis de ambiente e CI/CD. Para rodar localmente, consulte [`executar_projeto.md`](executar_projeto.md).

---

## ✅ Bloqueadores de deploy — situação em 2026-08-26

A rev. 2.0 listou **três bloqueadores de código**. Os três foram corrigidos no BLOCO P (`4fd576f`) e verificados nesta revisão:

| # | Bloqueador (rev. 2.0) | Estado | Verificação |
|---|---|---|---|
| 1 | **B-C23** — credenciais reais versionadas e publicadas | ✅ **Fechado** | Credenciais **rotacionadas**. `git log --all -S` com os valores atuais do `.env` não retorna commit algum. `db_auditoria.sql` removido; `.env.example` com 21 placeholders; gitleaks no pre-commit e no CI |
| 2 | **B-A23** — o auditado declara a própria conformidade | ✅ **Fechado** | `require_admin` em status de card e toggle de checklist; entradas de histórico recusadas de não-admin; `core/policy.py` como fonte única; matriz de autorização testada |
| 3 | **B-A26** — evidências não são apagadas do disco | ✅ **Fechado** | `storage.delete_files()` executa após o commit, recusa caminho fora de `uploads/` e nunca levanta exceção; `deleted_evidence_files` no resumo; `scripts/prune_orphan_uploads.py` para os órfãos anteriores |

**O deploy deixou de estar bloqueado por código.** O que resta é de outra natureza, e não deve ser confundido com "pronto".

### 🟠 Pendências de verificação — o que fazer antes do primeiro deploy

| # | Pendência | Por quê importa | Esforço |
|---|---|---|---|
| ~~**V1**~~ | ✅ **RESOLVIDO em 2026-08-26.** Os 4 jobs executam e passam em `main` | E a suspeita se confirmou da pior forma: o job `migrations` revelou que **o rollback de schema nunca funcionou** (B-A30, 6 migrations). Hoje `upgrade head → downgrade base → upgrade head` está verificado contra MySQL 8.4 real | — |
| **V2** | **`docker build` / `docker run` nunca executados** | Os Dockerfiles e o `docker-compose.yml` da raiz existem e foram revisados, mas nenhuma imagem foi construída | **3 h** |
| **V3** | **Abrir `GET /docs` dentro do container** | O defeito nº 14 (Swagger em branco por CSP) responde **200** e só aparece no navegador — nunca no log do servidor. Um teste de fumaça que só checa status code não o pega | 15 min |
| **V4** | **Restore de backup nunca ensaiado** | O procedimento da Seção 12 está escrito e nunca foi executado. Backup sem restore testado é arquivo, não backup | **2 h** |

### 🟠 Achados abertos que afetam operação em produção

Nenhum é bloqueador absoluto, mas os três primeiros mudam como o deploy deve ser feito:

| ID | Achado | Consequência em produção | Esforço |
|---|---|---|---|
| **B-A29** | Senha temporária do onboarding não existe sem SMTP, e uma falha de SMTP vira 500 após o commit | **Configure SMTP antes do primeiro cliente real.** Sem ele, cada cliente cadastrado nasce inacessível e não há recuperação de senha | 3 h |
| **B-A27** | Senha acima de 72 bytes derruba `/auth/login` com exceção não tratada | Superfície de erro não autenticada. Vai poluir o log e disparar alarme falso em qualquer monitoramento | 1 h 30 |
| **B-M25** | `ALLOW_PUBLIC_REGISTRATION` tem default `True` | **Defina a variável explicitamente no `.env` de produção.** Esquecê-la abre o cadastro público | 2 min |
| **B-A28** | Cliente lê o checklist interno e o histórico do auditor | Confidencialidade do trabalho interno da auditoria | 2 h |

### ⚠️ Limitação arquitetural — topologia de instância única

> **O backend não roda com mais de 1 worker ou réplica.** Dois motivos independentes:
>
> (a) as evidências vivem num volume local, invisível para as outras réplicas — o `StorageBackend` Protocol já existe (`services/storage_backend.py`) e obriga qualquer implementação nova a responder também "como eu apago?", mas **nenhuma implementação remota foi escrita**;
> (b) o rate limiting do `slowapi` usa contador em memória do processo, então N réplicas multiplicam o limite efetivo por N — o limite de 5 logins/min vira 5×N.
>
> **Consequência prática para este guia:** onde ele sugerir `--workers 4` ou escalar o serviço `backend`, **use 1 worker** até o Sprint D2 do [`roadmap.md`](roadmap.md). Um deploy de instância única é perfeitamente viável hoje; o que não é viável é escalar horizontalmente.

### Checklist mínimo antes do primeiro deploy

- [ ] **V1** — `ci.yml` executou num PR e os 4 jobs foram avaliados
- [ ] **V2** — `docker compose build && docker compose up -d` funcionou localmente
- [ ] **V3** — `GET /docs` **renderiza** dentro do container (não só responde 200)
- [ ] **V4** — restore de backup ensaiado contra um banco descartável
- [ ] **SMTP configurado e testado** (B-A29) — sem isso, não cadastre cliente real
- [ ] `ALLOW_PUBLIC_REGISTRATION=false` **explícito** no `.env` de produção (B-M25)
- [ ] `IS_DEBUG=false` e `JWT_SECRET` novo, gerado só para produção
- [ ] `CORS_ALLOWED_ORIGINS` com o domínio real, sem `localhost`
- [ ] `--workers 1` e **uma** réplica de backend
- [ ] `alembic heads` com um único head antes de aplicar
- [ ] `GET /health` (não `/api/v1/Monitoring`, que foi removida) configurado como health check do orquestrador

---

## Sumário

1. [Arquitetura de Produção](#1-arquitetura-de-produção)
2. [Pré-Requisitos no Servidor](#2-pré-requisitos-no-servidor)
3. [Estrutura de Arquivos de Deploy](#3-estrutura-de-arquivos-de-deploy)
4. [Dockerfile — Backend (FastAPI)](#4-dockerfile--backend-fastapi)
5. [Dockerfile — Frontend (Next.js)](#5-dockerfile--frontend-nextjs)
6. [docker-compose para Produção](#6-docker-compose-para-produção)
7. [Variáveis de Ambiente em Produção](#7-variáveis-de-ambiente-em-produção)
8. [Configuração do Nginx (Reverse Proxy + HTTPS)](#8-configuração-do-nginx-reverse-proxy--https)
9. [Certificado SSL com Let's Encrypt](#9-certificado-ssl-com-lets-encrypt)
10. [Primeiro Deploy Manual](#10-primeiro-deploy-manual)
11. [CI/CD com GitHub Actions](#11-cicd-com-github-actions)
12. [Backup em Produção](#12-backup-em-produção)
13. [Monitoramento e Logs em Produção](#13-monitoramento-e-logs-em-produção)
14. [Atualizações e Rollback](#14-atualizações-e-rollback)
15. [Checklist de Segurança para Produção](#15-checklist-de-segurança-para-produção)
16. [Troubleshooting em Produção](#16-troubleshooting-em-produção)

---

## 1. Arquitetura de Produção

```
Internet
    │ HTTPS :443
    ▼
┌─────────────────────────────────────────────────────────┐
│  Nginx (reverse proxy + TLS termination)                │
│  ├── / → Frontend Next.js :3000                         │
│  └── /api → Backend FastAPI :8000                       │
└────────────────┬────────────────────────────────────────┘
                 │ Rede interna Docker
    ┌────────────┴────────────┐
    │                         │
┌───▼──────┐         ┌───────▼──────┐
│ Next.js  │         │  FastAPI     │
│ :3000    │         │  :8000       │
│ (Docker) │         │  (Docker)    │
└──────────┘         └───────┬──────┘
                             │ SQLAlchemy
                     ┌───────▼──────┐
                     │  MySQL 8.4   │
                     │  :3306       │
                     │  (Docker)    │
                     └──────────────┘
```

### Serviços em Produção

| Serviço     | Imagem / Tecnologia         | Porta interna | Exposta ao Nginx | Volume                |
|-------------|-----------------------------|--------------:|:----------------:|-----------------------|
| MySQL       | `mysql:8.4`                 | `3306`        | ❌               | `mysql_data`          |
| Backend     | Build local (Python 3.12)   | `8000`        | ✅ `/api`        | `uploads_data`        |
| Frontend    | Build local (Node 20)       | `3000`        | ✅ `/`           | —                     |
| Nginx       | `nginx:alpine`              | `80`, `443`   | ✅ (público)     | certificados SSL      |

---

## 2. Pré-Requisitos no Servidor

### Especificações Mínimas Recomendadas

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| CPU     | 2 vCPUs | 4 vCPUs   |
| RAM     | 2 GB    | 4 GB       |
| Disco   | 20 GB   | 50 GB SSD  |
| SO      | Ubuntu 22.04 LTS | Ubuntu 22.04 / Debian 12 |

### Instalar Docker e Docker Compose no Servidor

```bash
# Atualizar pacotes:
sudo apt update && sudo apt upgrade -y

# Instalar dependências:
sudo apt install -y ca-certificates curl gnupg lsb-release

# Adicionar repositório oficial Docker:
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list

# Instalar Docker:
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Adicionar usuário ao grupo docker (evitar uso de sudo):
sudo usermod -aG docker $USER
newgrp docker

# Verificar instalação:
docker --version
docker compose version
```

### Instalar Nginx e Certbot

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
sudo systemctl enable nginx
```

### Configurar Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

---

## 3. Estrutura de Arquivos de Deploy

Organize os arquivos de produção assim:

```
Developer/
├── backend/
│   ├── Dockerfile              ← Criar (Seção 4)
│   ├── docker-compose.yml      ← Apenas MySQL (dev)
│   ├── .env.example
│   └── ...
├── frontend/
│   ├── Dockerfile              ← Criar (Seção 5)
│   └── ...
├── docker-compose.prod.yml     ← Criar na raiz (Seção 6)
├── nginx/
│   └── nginx.conf              ← Criar (Seção 8)
└── .env.prod                   ← Criar no servidor (nunca commitar)
```

---

## 4. Dockerfile — Backend (FastAPI)

Criar o arquivo `backend/Dockerfile`:

```dockerfile
# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Instalar dependências de sistema necessárias para compilação
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.12-slim AS production

WORKDIR /app

# Instalar apenas runtime (não compiladores)
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Usuário não-root por segurança
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Copiar dependências instaladas do builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiar código da aplicação
COPY --chown=appuser:appgroup . .

USER appuser

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# Comando de produção: sem --reload, workers configuráveis
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

**Build e teste local:**

```bash
cd backend
docker build -t auditoria-backend:latest .
docker run --rm -p 8000:8000 --env-file .env auditoria-backend:latest
curl http://localhost:8000/
```

---

## 5. Dockerfile — Frontend (Next.js)

Antes de criar o Dockerfile, habilitar o modo `standalone` no Next.js.

**Editar `frontend/next.config.ts`:**

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",  // ← adicionar esta linha
};

export default nextConfig;
```

Criar o arquivo `frontend/Dockerfile`:

```dockerfile
# Stage 1: Instalar dependências
FROM node:20-alpine AS deps
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --only=production

# Stage 2: Build da aplicação
FROM node:20-alpine AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Variável para a URL do backend (injetada em build time)
ARG BACKEND_API_URL=http://backend:8000
ENV BACKEND_API_URL=$BACKEND_API_URL

RUN npm run build

# Stage 3: Imagem de produção (mínima)
FROM node:20-alpine AS production
WORKDIR /app

ENV NODE_ENV=production

# Usuário não-root
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copiar apenas o necessário do build standalone
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget -qO- http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
```

**Build e teste local:**

```bash
cd frontend
docker build -t auditoria-frontend:latest .
docker run --rm -p 3000:3000 -e BACKEND_API_URL=http://localhost:8000 auditoria-frontend:latest
```

---

## 6. docker-compose para Produção

Criar `docker-compose.prod.yml` na **raiz** do projeto:

```yaml
services:

  mysql:
    image: mysql:8.4
    container_name: auditoria-mysql
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: auditoria
      MYSQL_USER: auditoria_app
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
    command: >
      --character-set-server=utf8mb4
      --collation-server=utf8mb4_unicode_ci
      --max_connections=200
      --innodb_buffer_pool_size=256M
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-uroot", "-p${MYSQL_ROOT_PASSWORD}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks:
      - auditoria-net

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: auditoria-backend
    restart: always
    environment:
      DATABASE_URL: mysql+pymysql://auditoria_app:${MYSQL_PASSWORD}@mysql:3306/auditoria
      JWT_SECRET: ${JWT_SECRET}
      JWT_ALGORITHM: HS256
      JWT_EXPIRES_MINUTES: ${JWT_EXPIRES_MINUTES:-60}
      CORS_ALLOWED_ORIGINS: ${CORS_ALLOWED_ORIGINS}
      IS_DEBUG: "false"
      ALLOW_PUBLIC_REGISTRATION: "false"
      SMTP_HOST: ${SMTP_HOST:-}
      SMTP_PORT: ${SMTP_PORT:-587}
      SMTP_USER: ${SMTP_USER:-}
      SMTP_PASSWORD: ${SMTP_PASSWORD:-}
      SMTP_FROM: ${SMTP_FROM:-}
    volumes:
      - uploads_data:/app/uploads
    depends_on:
      mysql:
        condition: service_healthy
    networks:
      - auditoria-net

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        BACKEND_API_URL: http://backend:8000
    container_name: auditoria-frontend
    restart: always
    environment:
      BACKEND_API_URL: http://backend:8000
      NODE_ENV: production
    depends_on:
      - backend
    networks:
      - auditoria-net

  nginx:
    image: nginx:alpine
    container_name: auditoria-nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
      - /var/www/certbot:/var/www/certbot:ro
    depends_on:
      - frontend
      - backend
    networks:
      - auditoria-net

volumes:
  mysql_data:
    driver: local
  uploads_data:
    driver: local

networks:
  auditoria-net:
    driver: bridge
```

---

## 7. Variáveis de Ambiente em Produção

Criar o arquivo `.env.prod` **diretamente no servidor** (nunca commitar no repositório):

```bash
# No servidor de produção:
nano /opt/auditoria/.env.prod
```

Conteúdo do `.env.prod`:

```dotenv
# ─── Banco de Dados ────────────────────────────────────────────────────────────
MYSQL_ROOT_PASSWORD=<senha-root-forte-e-unica>
MYSQL_PASSWORD=<senha-app-forte-e-unica>

# ─── API ───────────────────────────────────────────────────────────────────────
# Domínio(s) permitidos no CORS (sem barra final):
CORS_ALLOWED_ORIGINS=https://auditoria.seudominio.com.br

# ─── Autenticação JWT ──────────────────────────────────────────────────────────
# Gerar com: python3 -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET=<64-caracteres-hexadecimais-aleatorios>
JWT_EXPIRES_MINUTES=60

# ─── E-mail SMTP (opcional) ────────────────────────────────────────────────────
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@seudominio.com.br
SMTP_PASSWORD=<senha-smtp-ou-app-password>
SMTP_FROM=noreply@seudominio.com.br
```

**Gerar senhas seguras:**

```bash
# Senha do banco (32 chars):
python3 -c "import secrets; print(secrets.token_urlsafe(24))"

# JWT Secret (64 chars hex):
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**Permissões seguras para o arquivo:**

```bash
chmod 600 /opt/auditoria/.env.prod
chown $USER:$USER /opt/auditoria/.env.prod
```

### Diferenças entre Desenvolvimento e Produção

| Variável                    | Desenvolvimento         | Produção                              |
|-----------------------------|-------------------------|---------------------------------------|
| `DATABASE_URL` host         | `127.0.0.1:3307`        | `mysql:3306` (hostname Docker)        |
| `JWT_SECRET`                | Valor fixo no `.env`    | Gerado aleatoriamente, nunca reutilizado |
| `IS_DEBUG`                  | `false` (ou `true`)     | Sempre `false`                        |
| `CORS_ALLOWED_ORIGINS`      | `http://localhost:3000` | `https://auditoria.seudominio.com.br` |
| `MYSQL_PASSWORD`            | `<nunca use um valor real aqui>`    | Senha forte gerada aleatoriamente     |
| `ALLOW_PUBLIC_REGISTRATION` | `false`                 | `false`                               |

---

## 8. Configuração do Nginx (Reverse Proxy + HTTPS)

Criar a pasta e o arquivo de configuração:

```bash
mkdir -p nginx
```

Criar `nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logs
    access_log /var/log/nginx/access.log;
    error_log  /var/log/nginx/error.log warn;

    # Compressão
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 1000;

    # Limites de upload (evidências)
    client_max_body_size 50M;

    # Timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout    60s;
    proxy_read_timeout    60s;

    # Redirecionar HTTP → HTTPS
    server {
        listen 80;
        server_name auditoria.seudominio.com.br;

        # Necessário para renovação Let's Encrypt
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://$host$request_uri;
        }
    }

    # HTTPS — servidor principal
    server {
        listen 443 ssl http2;
        server_name auditoria.seudominio.com.br;

        # Certificados SSL
        ssl_certificate     /etc/letsencrypt/live/auditoria.seudominio.com.br/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/auditoria.seudominio.com.br/privkey.pem;

        # Segurança SSL
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 1d;

        # Headers de segurança
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
        add_header X-Content-Type-Options nosniff always;
        add_header X-Frame-Options DENY always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;

        # ── API Backend (/api e /docs) ───────────────────────────────────────
        location /api/ {
            proxy_pass         http://backend:8000/api/;
            proxy_http_version 1.1;
            proxy_set_header   Host              $host;
            proxy_set_header   X-Real-IP         $remote_addr;
            proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
            proxy_set_header   X-Forwarded-Proto $scheme;
        }

        # Swagger UI (acesso interno recomendado — remover em produção pública)
        location /docs {
            proxy_pass http://backend:8000/docs;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location /openapi.json {
            proxy_pass http://backend:8000/openapi.json;
            proxy_set_header Host $host;
        }

        # ── Frontend Next.js ─────────────────────────────────────────────────
        location / {
            proxy_pass         http://frontend:3000;
            proxy_http_version 1.1;
            proxy_set_header   Upgrade           $http_upgrade;
            proxy_set_header   Connection        "upgrade";
            proxy_set_header   Host              $host;
            proxy_set_header   X-Real-IP         $remote_addr;
            proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
            proxy_set_header   X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
        }
    }
}
```

> **Importante:** substitua `auditoria.seudominio.com.br` pelo seu domínio real em todas as ocorrências.

---

## 9. Certificado SSL com Let's Encrypt

### Obter certificado pela primeira vez

```bash
# Parar nginx temporariamente (se já estiver rodando):
sudo systemctl stop nginx

# Obter certificado:
sudo certbot certonly --standalone \
  -d auditoria.seudominio.com.br \
  --email rodrigo.santos@stwbrasil.com \
  --agree-tos \
  --non-interactive

# Verificar que os certificados foram gerados:
ls /etc/letsencrypt/live/auditoria.seudominio.com.br/
# fullchain.pem  privkey.pem  cert.pem  chain.pem
```

### Renovação automática

```bash
# Testar renovação (dry run):
sudo certbot renew --dry-run

# Configurar renovação automática via cron (certbot já faz isso):
sudo systemctl status certbot.timer
# Se não existir, adicionar manualmente:
echo "0 0,12 * * * root certbot renew --quiet --post-hook 'docker exec auditoria-nginx nginx -s reload'" | sudo tee /etc/cron.d/certbot-renew
```

---

## 10. Primeiro Deploy Manual

Execute estes passos **na primeira vez** no servidor de produção:

### Passo 1 — Clonar o repositório no servidor

```bash
# No servidor:
sudo mkdir -p /opt/auditoria
sudo chown $USER:$USER /opt/auditoria
cd /opt/auditoria

git clone <URL-do-repositório> .
```

### Passo 2 — Criar o arquivo de variáveis de ambiente

```bash
cp backend/.env.example .env.prod
# Editar com os valores de produção:
nano .env.prod
```

### Passo 3 — Obter o certificado SSL

```bash
# (ver Seção 9)
sudo certbot certonly --standalone -d auditoria.seudominio.com.br \
  --email rodrigo.santos@stwbrasil.com --agree-tos --non-interactive
```

### Passo 4 — Build e subida dos containers

```bash
cd /opt/auditoria

# Build das imagens:
docker compose -f docker-compose.prod.yml --env-file .env.prod build

# Subir todos os serviços:
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Verificar status:
docker compose -f docker-compose.prod.yml ps
```

### Passo 5 — Executar migrations

```bash
# Entrar no container do backend:
docker exec -it auditoria-backend bash

# Dentro do container:
alembic upgrade head
exit
```

### Passo 6 — Popular dados iniciais

```bash
# Criar usuário admin de produção:
docker exec -it auditoria-backend bash -c \
  "ADMIN_FULL_NAME='Administrador' ADMIN_EMAIL=admin@seudominio.com.br ADMIN_PASSWORD='SENHA_FORTE_AQUI' python scripts/seed_admin.py"

# Catálogo de controles:
docker exec -it auditoria-backend python scripts/seed_catalog.py

# Templates de dashboard:
docker exec -it auditoria-backend python scripts/seed_dashboard_templates.py
```

### Passo 7 — Verificar que tudo está funcionando

```bash
# Status dos containers:
docker compose -f docker-compose.prod.yml ps

# Testar API:
curl https://auditoria.seudominio.com.br/api/v1/
# Esperado: {"message":"Auditoria API","docs":"/docs"}

# Testar frontend:
curl -I https://auditoria.seudominio.com.br/
# Esperado: HTTP/2 200
```

---

## 11. CI/CD com GitHub Actions

Criar o arquivo `.github/workflows/ci.yml`:

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:

  # ── Testes Backend ────────────────────────────────────────────────────────
  backend-test:
    name: Backend Tests
    runs-on: ubuntu-latest

    services:
      mysql:
        image: mysql:8.4
        env:
          MYSQL_ROOT_PASSWORD: test_root
          MYSQL_DATABASE: auditoria_test
          MYSQL_USER: auditoria_app
          MYSQL_PASSWORD: test_password
        ports:
          - 3306:3306
        options: >-
          --health-cmd="mysqladmin ping -h localhost"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=5

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
          cache-dependency-path: backend/requirements.txt

      - name: Install dependencies
        working-directory: backend
        run: pip install -r requirements.txt

      - name: Run Alembic migrations
        working-directory: backend
        env:
          DATABASE_URL: mysql+pymysql://auditoria_app:test_password@127.0.0.1:3306/auditoria_test
          JWT_SECRET: test_jwt_secret_for_ci_only_not_production
        run: alembic upgrade head

      - name: Run tests
        working-directory: backend
        env:
          DATABASE_URL: mysql+pymysql://auditoria_app:test_password@127.0.0.1:3306/auditoria_test
          JWT_SECRET: test_jwt_secret_for_ci_only_not_production
          CORS_ALLOWED_ORIGINS: http://localhost:3000
        run: |
          pip install pytest pytest-asyncio httpx
          pytest -v --tb=short

  # ── Build Frontend ────────────────────────────────────────────────────────
  frontend-build:
    name: Frontend Build
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js 20
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        working-directory: frontend
        run: npm ci

      - name: Type check
        working-directory: frontend
        run: npm run lint

      - name: Build
        working-directory: frontend
        env:
          BACKEND_API_URL: http://backend:8000
        run: npm run build

  # ── Deploy em Produção (apenas push na main) ──────────────────────────────
  deploy:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: [backend-test, frontend-build]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'

    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.PROD_SSH_KEY }}
          script: |
            cd /opt/auditoria
            git pull origin main
            docker compose -f docker-compose.prod.yml --env-file .env.prod build --no-cache
            docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
            docker exec auditoria-backend alembic upgrade head
            docker image prune -f
            echo "Deploy concluído: $(date)"
```

### Configurar Secrets no GitHub

No repositório GitHub → **Settings → Secrets and variables → Actions**, adicionar:

| Secret          | Valor                                      |
|-----------------|--------------------------------------------|
| `PROD_HOST`     | IP ou hostname do servidor de produção     |
| `PROD_USER`     | Usuário SSH do servidor (ex: `ubuntu`)     |
| `PROD_SSH_KEY`  | Chave privada SSH (conteúdo completo do `.pem`) |

**Gerar par de chaves SSH para o GitHub Actions:**

```bash
# Na sua máquina local:
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/deploy_key -N ""

# Copiar chave pública para o servidor:
ssh-copy-id -i ~/.ssh/deploy_key.pub usuario@IP-DO-SERVIDOR

# O conteúdo da chave PRIVADA vai no secret PROD_SSH_KEY:
cat ~/.ssh/deploy_key
```

---

## 12. Backup em Produção

### Backup Manual

```bash
# Conectar ao servidor:
ssh usuario@IP-DO-SERVIDOR

# Backup do banco:
docker exec auditoria-mysql mysqldump \
  -uauditoria_app -p"${MYSQL_PASSWORD}" \
  --single-transaction \
  --routines \
  --triggers \
  auditoria > /opt/auditoria/backups/backup_$(date +%Y%m%d_%H%M%S).sql

# Compactar e arquivar:
gzip /opt/auditoria/backups/backup_*.sql
```

### Backup Automático via Cron

```bash
# Criar diretório de backups:
sudo mkdir -p /opt/auditoria/backups
sudo chown $USER:$USER /opt/auditoria/backups

# Criar script de backup:
cat > /opt/auditoria/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/auditoria/backups"
DATE=$(date +%Y%m%d_%H%M%S)
MYSQL_PASSWORD=$(grep MYSQL_PASSWORD /opt/auditoria/.env.prod | cut -d= -f2)

docker exec auditoria-mysql mysqldump \
  -uauditoria_app -p"${MYSQL_PASSWORD}" \
  --single-transaction auditoria | gzip > "${BACKUP_DIR}/backup_${DATE}.sql.gz"

# Manter apenas os últimos 30 backups:
ls -t "${BACKUP_DIR}"/backup_*.sql.gz | tail -n +31 | xargs -r rm

echo "Backup concluído: backup_${DATE}.sql.gz"
EOF

chmod +x /opt/auditoria/backup.sh

# Agendar backup diário às 2h da manhã:
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/auditoria/backup.sh >> /var/log/auditoria-backup.log 2>&1") | crontab -
```

### Restaurar Backup em Produção

```bash
# ATENÇÃO: isto sobrescreve todos os dados existentes.
# Sempre faça um backup atual antes de restaurar.

# Restaurar de um arquivo comprimido:
gunzip < /opt/auditoria/backups/backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i auditoria-mysql mysql \
  -uauditoria_app -p"SENHA" auditoria
```

---

## 13. Monitoramento e Logs em Produção

### Ver Logs dos Serviços

```bash
# Todos os serviços juntos (últimas 100 linhas):
docker compose -f docker-compose.prod.yml logs --tail 100

# Backend em tempo real:
docker compose -f docker-compose.prod.yml logs -f backend

# Frontend:
docker compose -f docker-compose.prod.yml logs -f frontend

# MySQL:
docker compose -f docker-compose.prod.yml logs -f mysql

# Nginx:
docker compose -f docker-compose.prod.yml logs -f nginx
# OU diretamente:
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Verificar Saúde dos Containers

```bash
# Status e health de todos os containers:
docker compose -f docker-compose.prod.yml ps

# Inspecionar healthcheck de um container:
docker inspect --format='{{json .State.Health}}' auditoria-backend | python3 -m json.tool

# Uso de recursos (CPU, memória, rede):
docker stats
```

### Alertas Básicos com Script de Monitoramento

```bash
# /opt/auditoria/health_check.sh
cat > /opt/auditoria/health_check.sh << 'EOF'
#!/bin/bash
API_URL="https://auditoria.seudominio.com.br"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/")

if [ "$HTTP_CODE" != "200" ]; then
  echo "ALERTA: API retornou HTTP ${HTTP_CODE} em $(date)"
  # Adicionar aqui: envio de e-mail ou notificação
fi
EOF

chmod +x /opt/auditoria/health_check.sh

# Executar a cada 5 minutos:
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/auditoria/health_check.sh >> /var/log/auditoria-health.log 2>&1") | crontab -
```

---

## 14. Atualizações e Rollback

### Deploy de Nova Versão

```bash
cd /opt/auditoria

# 1. Fazer backup antes de atualizar:
./backup.sh

# 2. Buscar código novo:
git pull origin main

# 3. Rebuild das imagens:
docker compose -f docker-compose.prod.yml --env-file .env.prod build

# 4. Aplicar com downtime mínimo (containers param e sobem):
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# 5. Aplicar migrations (se houver):
docker exec auditoria-backend alembic upgrade head

# 6. Verificar que tudo voltou:
docker compose -f docker-compose.prod.yml ps
curl https://auditoria.seudominio.com.br/
```

### Rollback para Versão Anterior

```bash
# Ver histórico de commits:
git log --oneline -10

# Voltar para um commit específico:
git checkout <hash-do-commit-estável>

# Rebuild e redeploy:
docker compose -f docker-compose.prod.yml --env-file .env.prod build
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Se as migrations precisarem ser revertidas:
docker exec -it auditoria-backend alembic downgrade -1
```

### Reiniciar Serviços sem Rebuild

```bash
# Reiniciar apenas o backend:
docker compose -f docker-compose.prod.yml restart backend

# Reiniciar todos:
docker compose -f docker-compose.prod.yml restart

# Parar e subir novamente:
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

---

## 15. Checklist de Segurança para Produção

Verifique cada item antes de tornar o ambiente acessível ao público:

### Configuração

- [ ] `IS_DEBUG=false` no `.env.prod`
- [ ] `ALLOW_PUBLIC_REGISTRATION=false` no `.env.prod`
- [ ] `JWT_SECRET` gerado aleatoriamente (64 chars hex) — nunca reutilizar o de desenvolvimento
- [ ] Senhas do MySQL fortes e únicas (geradas aleatoriamente)
- [ ] Arquivo `.env.prod` com permissão `600` e dono correto
- [ ] Arquivo `.env.prod` **não** commitado no repositório (verificar `.gitignore`)

### Rede e TLS

- [ ] HTTPS habilitado com certificado válido (Let's Encrypt)
- [ ] Redirecionamento HTTP → HTTPS configurado no Nginx
- [ ] HSTS habilitado (`Strict-Transport-Security`)
- [ ] Porta do MySQL (`3306`) **não** exposta ao exterior (apenas interno Docker)
- [ ] Firewall bloqueando portas não necessárias (apenas 22, 80, 443)

### Headers HTTP

- [ ] `X-Content-Type-Options: nosniff`
- [ ] `X-Frame-Options: DENY`
- [ ] `X-XSS-Protection: 1; mode=block`
- [ ] `Referrer-Policy: strict-origin-when-cross-origin`

### Aplicação

- [ ] `CORS_ALLOWED_ORIGINS` contém apenas o domínio de produção (sem `localhost`)
- [ ] Swagger UI (`/docs`) restrito ou removido em produção pública
- [ ] Usuários com senhas fortes (admin criado com senha única)
- [ ] Logs de acesso habilitados no Nginx
- [ ] Backups automáticos configurados e testados

### Bugs Críticos de Segurança

Antes do deploy, verificar se os seguintes bugs foram corrigidos (ver [`relatorio_bugs.md`](relatorio_bugs.md)):

- [ ] **B-C01** — `bcrypt.hashpw` recebendo `str` em vez de `bytes` (falha silenciosa na criação de usuários)
- [ ] **B-C02** — Senha exposta em logs de debug
- [ ] **B-C05** — Timing attack na autenticação
- [ ] **B-C09** — IDOR no checklist (acesso a dados de outros usuários)
- [ ] **B-C13** — Middleware sem validação de role

---

## 16. Troubleshooting em Produção

### Container não sobe após deploy

```bash
# Ver logs detalhados do container que falhou:
docker compose -f docker-compose.prod.yml logs backend
docker compose -f docker-compose.prod.yml logs mysql

# Ver eventos do Docker:
docker events --since 10m

# Inspecionar container parado:
docker inspect auditoria-backend
```

### Backend não conecta ao MySQL em produção

```bash
# Verificar se o container mysql está saudável:
docker inspect --format='{{json .State.Health.Status}}' auditoria-mysql

# Testar conectividade de dentro do backend:
docker exec -it auditoria-backend bash
python -c "import pymysql; conn=pymysql.connect(host='mysql', port=3306, user='auditoria_app', password='SENHA', db='auditoria'); print('OK')"
```

> Em produção, o host do MySQL é `mysql` (nome do serviço Docker), **não** `127.0.0.1`.

### Nginx retorna 502 Bad Gateway

```bash
# Verificar se o container alvo está rodando:
docker ps | grep auditoria-backend
docker ps | grep auditoria-frontend

# Ver logs do Nginx:
docker logs auditoria-nginx
sudo tail -50 /var/log/nginx/error.log

# Verificar que os nomes dos containers coincidem com o nginx.conf:
# nginx.conf usa: proxy_pass http://backend:8000  → container deve se chamar "backend" na rede Docker
```

### Certificado SSL expirado

```bash
# Renovar manualmente:
sudo certbot renew

# Recarregar Nginx para pegar novo certificado:
docker exec auditoria-nginx nginx -s reload

# Verificar validade do certificado:
echo | openssl s_client -servername auditoria.seudominio.com.br -connect auditoria.seudominio.com.br:443 2>/dev/null | openssl x509 -noout -dates
```

### Erro de permissão nos volumes

```bash
# Ver usuário dentro do container:
docker exec auditoria-backend id

# Ajustar permissões do volume de uploads:
docker exec -u root auditoria-backend chown -R appuser:appgroup /app/uploads
```

### Disco cheio no servidor

```bash
# Verificar uso de disco:
df -h

# Ver o que está ocupando mais espaço:
du -sh /opt/auditoria/*
du -sh /var/lib/docker/

# Limpar imagens Docker não utilizadas:
docker system prune -af

# Limpar logs antigos do Nginx:
sudo find /var/log/nginx/ -name "*.gz" -mtime +30 -delete

# Limpar backups antigos (manter últimos 30):
ls -t /opt/auditoria/backups/backup_*.sql.gz | tail -n +31 | xargs -r rm
```

---

## Referências e Documentação Relacionada

| Documento | Conteúdo |
|-----------|----------|
| [`executar_projeto.md`](executar_projeto.md) | Guia operacional completo para desenvolvimento local |
| [`plano_implementacao.md`](plano_implementacao.md) | Fase 8 — DevOps e infraestrutura com código detalhado |
| [`relatorio_melhorias.md`](relatorio_melhorias.md) | M-10 DevOps — justificativas e estimativa de 3 dias de esforço |
| [`relatorio_bugs.md`](relatorio_bugs.md) | Bugs de segurança críticos que devem ser corrigidos antes do deploy |
| [`setup_completo.md`](setup_completo.md) | Contexto arquitetural e guia de onboarding |

---

*Documento atualizado em 2026-08-26 (v2.2). Os 3 bloqueadores de código da rev. 2.0 estão fechados, e a pendência **V1** também: o CI executou pela primeira vez e revelou que **o rollback de schema nunca funcionara** (B-A30) — hoje `upgrade head → downgrade base → upgrade head` está verificado contra MySQL 8.4 real. Restam **V2** (`docker build`), **V3** (`/docs` dentro do container) e **V4** (restore de backup), que continuam sem execução real.*
