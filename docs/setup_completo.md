# Guia Completo de Setup — Plataforma de Auditoria

| Campo | Valor |
|---|---|
| **Versão** | **4.1 — 2026-08-26** |
| **Branch / HEAD** | `fix/audit-repository-refactor-and-regressions` · `34f8444` |
| **Validado contra** | Python 3.12/3.14 · Node 20+ · Docker Desktop · MySQL 8.4 · Windows 11 (Git Bash e PowerShell) |
| **Resultado esperado ao fim** | Backend em `:8000`, frontend em `:3000`, MySQL em `:3307`, `pytest -q` → **250 passed** |

> **O que mudou na rev. 4.0:** o passo de verificação de cada seção foi revisto contra o código em `34f8444`. Três correções importantes: o **health check é `GET /health`** (a rota `/api/v1/Monitoring` que o `backend/README.md` ainda indica **foi removida** e responde 404); o **`pre-commit` agora se instala na raiz** do repositório, não em `backend/`; e a **Seção 9.4** cobre o onboarding sem SMTP. **Atualização da rev. 4.1:** o achado B-A29 foi corrigido no mesmo dia — a senha temporária agora é exibida ao admin quando o e-mail não sai, em vez de ser descartada.

---

## Visão Geral

```
                    ┌──────────────────────────────────┐
   http://localhost │  FRONTEND — Next.js 16 (:3000)   │
        :3000  ────▶│  Server Components + Actions      │
                    │  proxy.ts (guarda de sessão)      │
                    └──────────────┬───────────────────┘
                                   │ Bearer token (server-side)
                    ┌──────────────▼───────────────────┐
                    │  BACKEND — FastAPI (:8000)        │
                    │  /api/v1/** · /health · /docs     │
                    └──────────────┬───────────────────┘
                                   │ pymysql
                    ┌──────────────▼───────────────────┐
                    │  MySQL 8.4 (Docker) — host :3307  │
                    │  database: auditoria              │
                    └──────────────────────────────────┘
```

**Tempo estimado do zero ao primeiro login:** 25–40 minutos, sendo ~10 deles esperando o Docker baixar a imagem do MySQL.

---

## Seção 1 — Pré-requisitos

### Ferramentas obrigatórias

| Ferramenta | Versão | Para quê |
|---|---|---|
| **Python** | 3.12 (fixada em `Dockerfile` e CI) · 3.13/3.14 funcionam | Backend |
| **Node.js** | 20 LTS ou superior | Frontend |
| **Docker Desktop** | qualquer versão recente, **em execução** | MySQL 8.4 |
| **Git** | qualquer | Clone e hooks |
| **Terminal** | Git Bash **ou** PowerShell | Os comandos deste guia trazem as duas variantes |

> ⚠️ O `backend/README.md` diz "Python 3.11+". **A 3.11 nunca foi validada** neste projeto (divergência RD-07 em `relatorio_documentacao.md`). Use 3.12 ou superior.

### Verificação rápida

```bash
python --version     # Python 3.12.x ou superior
node --version       # v20.x ou superior
npm --version        # 10.x ou superior
docker --version     # Docker version 2x.x
docker ps            # precisa responder sem erro → Docker Desktop está rodando
git --version
```

Se `docker ps` responder `error during connect` ou `Cannot connect to the Docker daemon`, abra o Docker Desktop e espere o ícone ficar verde antes de continuar.

---

## Seção 2 — Clonar o Repositório

```bash
git clone https://github.com/Rodig0SantOs/Projeto-Auditoria.git
cd Projeto-Auditoria
git checkout fix/audit-repository-refactor-and-regressions
```

### Estrutura relevante para o setup

```
.
├── .pre-commit-config.yaml     ← hook do gitleaks (instale a partir DAQUI)
├── docker-compose.yml          ← stack completa (Seção 10)
├── docs/                       ← esta documentação
├── backend/
│   ├── docker-compose.yml      ← só o MySQL (é o que você usa em dev)
│   ├── .env.example            ← 21 variáveis, todas em placeholder
│   ├── requirements.txt
│   ├── alembic/                ← 19 migrations
│   └── scripts/                ← 8 scripts (seeds + manutenção)
└── frontend/
    ├── package.json
    └── .env.local              ← você vai criar (não é versionado)
```

---

## Seção 3 — Configuração do Backend

### 3.1 — Ambiente virtual Python

```bash
cd backend
python -m venv .venv
```

Ativação, conforme o terminal:

```bash
# Git Bash (Windows)
source .venv/Scripts/activate

# PowerShell (Windows)
.\.venv\Scripts\Activate.ps1

# CMD (Windows)
.venv\Scripts\activate.bat

# Mac / Linux
source .venv/bin/activate
```

O prompt passa a começar com `(.venv)`. **Todos os comandos de backend deste guia assumem o venv ativo.**

> Se o PowerShell recusar o script de ativação, rode uma vez:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

### 3.2 — Instalar dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Verificação:

```bash
pip list | grep -E "fastapi|sqlalchemy|alembic|pytest"
```

### 3.3 — Arquivo `.env`

```bash
cp .env.example .env            # Git Bash / Mac / Linux
# Copy-Item .env.example .env   # PowerShell
```

Abra `backend/.env` e **substitua todos os placeholders**. O arquivo tem 21 variáveis:

```ini
# ===================================================
# BANCO DE DADOS
# Formato: mysql+pymysql://USUARIO:SENHA@HOST:PORTA/BANCO
# Senha com caractere especial? codifique na URL (@ -> %40, # -> %23)
# A porta é 3307 no host — ver backend/docker-compose.yml
# ===================================================
DATABASE_URL=mysql+pymysql://auditoria_app:SUA_SENHA_FORTE@127.0.0.1:3307/auditoria

# Lidas pelo backend/docker-compose.yml ao CRIAR o container do MySQL.
# MYSQL_PASSWORD tem de ser EXATAMENTE a senha usada na DATABASE_URL acima.
MYSQL_ROOT_PASSWORD=OUTRA_SENHA_FORTE_PARA_ROOT
MYSQL_PASSWORD=SUA_SENHA_FORTE

# ===================================================
# JWT — gere com o comando da Seção 3.4
# ===================================================
JWT_SECRET=cole_aqui_a_chave_hex_de_64_caracteres
JWT_ALGORITHM=HS256
JWT_EXPIRES_MINUTES=15
JWT_REFRESH_EXPIRES_DAYS=7

# ===================================================
# APLICAÇÃO
# ===================================================
PROJECT_NAME=Auditoria API
API_PREFIX_V1=/api/v1
IS_DEBUG=false
CORS_ALLOWED_ORIGINS=http://localhost:3000
ALLOW_PUBLIC_REGISTRATION=false

# ===================================================
# ADMIN INICIAL (usado só por scripts/seed_admin.py)
# ===================================================
ADMIN_EMAIL=admin@auditoria.local
ADMIN_FULL_NAME=Administrador
ADMIN_PASSWORD=SENHA_FORTE_DO_ADMIN

# ===================================================
# SMTP (opcional em dev — ver o aviso da Seção 9.4)
# Sem SMTP_HOST, os e-mails de credenciais NÃO são enviados.
# ===================================================
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_USE_TLS=true
```

> 🔒 `backend/.env` está no `.gitignore` e **nunca** deve ser commitado. O `.env.example` **é** versionado — não coloque valores reais nele.

### 3.4 — Gerar o `JWT_SECRET`

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> ⚠️ **Guarde essa chave.** Ela precisa ser **idêntica** em `backend/.env` e em `frontend/.env.local`. Se divergirem, o login funciona (o backend emite o token) mas toda navegação para `/private/**` redireciona de volta para a tela de login — porque o frontend não consegue verificar a assinatura. **É o erro de setup mais comum deste projeto**, e o sintoma engana: sucesso no servidor, porta fechada no cliente.

### 3.5 — Hook de segredo (recomendado)

```bash
cd ..                # RAIZ do repositório — o .pre-commit-config.yaml está aqui
pip install pre-commit
pre-commit install
cd backend
```

> O `pre-commit` resolve a configuração a partir do **topo do repositório**. Até o BLOCO P o arquivo estava em `backend/`, onde o hook nunca rodaria.

---

## Seção 4 — Banco de Dados (Docker)

### 4.1 — Subir o MySQL

```bash
cd backend
docker compose up -d
```

Esse compose sobe **apenas o MySQL**, publicado em **`127.0.0.1:3307`** (o container usa 3306 internamente). Ele lê `MYSQL_PASSWORD` e `MYSQL_ROOT_PASSWORD` do `backend/.env`.

### 4.2 — Verificar

```bash
docker ps
```

Esperado:

```
CONTAINER ID   IMAGE       STATUS         PORTS                               NAMES
xxxxxxxxxxxx   mysql:8.4   Up 2 minutes   0.0.0.0:3307->3306/tcp              auditoria-mysql
```

### 4.3 — Aguardar a inicialização

Na primeira execução, o MySQL leva **30 a 60 segundos** para inicializar o volume de dados. Acompanhe:

```bash
docker logs -f auditoria-mysql
```

Espere a linha `ready for connections` **aparecer duas vezes** (a primeira é da fase de setup interno). `Ctrl+C` sai do `logs -f` sem parar o container.

### 4.4 — Testar a conexão pela aplicação

```bash
python scripts/check_db.py
```

Esperado: mensagem de conexão bem-sucedida. Se falhar, veja a Seção 11.

### Comandos Docker úteis

| Ação | Comando |
|---|---|
| Parar o banco (preserva os dados) | `docker compose down` |
| Parar e **apagar tudo** | `docker compose down -v` |
| Ver logs | `docker logs -f auditoria-mysql` |
| Abrir o cliente MySQL | `docker exec -it auditoria-mysql mysql -uauditoria_app -p -D auditoria` |
| Reiniciar | `docker compose restart` |

---

## Seção 5 — Migrações e Seeds

### 5.1 — Aplicar as migrações

```bash
alembic upgrade head
```

Verificação:

```bash
alembic current    # deve mostrar b7c02e91d4a5 (head)
alembic heads      # deve listar UMA linha só
```

São **19 migrações**. `alembic heads` com mais de uma linha significa branch pendente — não continue.

### 5.2 — Catálogo de controles

```bash
python scripts/seed_catalog.py
```

### 5.3 — Templates de dashboard `⚠️ OBRIGATÓRIO`

```bash
python scripts/seed_dashboard_templates.py
```

> ⚠️ **Não pule este passo.** Sem um template marcado como `is_default`, o onboarding de cliente falha com `"Nenhum template padrão configurado"` (`services/dashboard_builder.py::resolve_template`). O `backend/README.md` lista os seeds como "opcional" — está errado (divergência RD-05).

### 5.4 — Usuário administrador

O script lê `ADMIN_EMAIL`, `ADMIN_FULL_NAME` e `ADMIN_PASSWORD` do `.env`:

```bash
python scripts/seed_admin.py
```

Para sobrescrever pontualmente:

```bash
# Git Bash / Mac / Linux
ADMIN_EMAIL=admin@auditoria.local ADMIN_PASSWORD='SenhaForte123!' python scripts/seed_admin.py

# PowerShell
$env:ADMIN_EMAIL="admin@auditoria.local"; $env:ADMIN_PASSWORD="SenhaForte123!"; python scripts/seed_admin.py
```

O seed é **idempotente**: rodar duas vezes não cria dois admins.

> ⚠️ A senha do admin precisa ter **no máximo 72 bytes**. Acima disso o `bcrypt` levanta `ValueError` e o seed falha (achado **B-A27**). Acentos contam 2 bytes.

### 5.5 — Dados de demonstração (opcional, recomendado em dev)

```bash
python scripts/seed_demo_companies.py
python scripts/seed_demo_audits.py
```

Criam 5 empresas fictícias com dashboards, auditorias, evidências em PDF e mensagens — **com senha conhecida**, ao contrário do onboarding real (ver Seção 9.4). É a forma mais rápida de ter o sistema com conteúdo para explorar.

### Ordem correta (resumo)

```bash
docker compose up -d                          # 1. banco
# aguardar ~30s no primeiro start
alembic upgrade head                          # 2. schema
python scripts/seed_catalog.py                # 3. catálogo de controles
python scripts/seed_dashboard_templates.py    # 4. templates  ← obrigatório
python scripts/seed_admin.py                  # 5. admin
python scripts/seed_demo_companies.py         # 6. demo (opcional)
python scripts/seed_demo_audits.py            # 7. demo (opcional)
```

---

## Seção 6 — Iniciar o Backend

```bash
uvicorn app.main:app --reload
```

### Saída esperada

```
INFO:     Will watch for changes in these directories: ['.../backend']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

### Verificar

```bash
# Health check REAL — executa SELECT 1 no banco
curl http://localhost:8000/health
# {"status":"Ok","db_status":"Ok","timestamp":"..."}

curl http://localhost:8000/
# {"message":"Auditoria API","docs":"/docs"}
```

> ⚠️ **`http://localhost:8000/api/v1/Monitoring` não existe mais.** A rota foi removida no BLOCO P por ser redundante e por não verificar o banco. O `backend/README.md` ainda a indica como health check — está errado (divergência RD-04). **Configure qualquer orquestrador para `GET /health`.**

Abra também, no navegador:

| URL | O que deve aparecer |
|---|---|
| http://localhost:8000/docs | Swagger UI **renderizada** (não uma página em branco) |
| http://localhost:8000/redoc | ReDoc renderizada |

> Se `/docs` responder 200 mas ficar **em branco**, é bloqueio de CSP no navegador — abra o console (F12) e confira. Foi exatamente o defeito nº 14, corrigido em `34f8444`; a barreira que impede a volta é `tests/test_security_headers.py`.

### Rodar a suíte de testes

```bash
python -m pytest -q
# Esperado: 250 passed
```

Os testes usam **SQLite em memória** e não tocam no MySQL nem em `backend/uploads/`. Podem rodar com o Docker parado.

```bash
python -m ruff check app scripts tests
# Esperado: All checks passed!
```

---

## Seção 7 — Configuração do Frontend

### 7.1 — Verificar o Node

```bash
cd ../frontend
node --version    # v20 ou superior
```

### 7.2 — Instalar dependências

```bash
npm install
```

### 7.3 — Arquivo `.env.local`

Crie `frontend/.env.local`:

```ini
# URL do backend, usada em chamadas server-side (Server Components/Actions e proxy.ts)
BACKEND_API_URL=http://127.0.0.1:8000

# DEVE ser IDÊNTICO ao JWT_SECRET de backend/.env — ver o aviso da Seção 3.4
JWT_SECRET=cole_aqui_a_MESMA_chave_do_backend
JWT_ALGORITHM=HS256

# Mesmos valores de backend/.env — usados para o maxAge dos cookies em
# proxy.ts e app/api/auth/login/route.ts. Se divergirem, o cookie sobrevive
# ao JWT que ele carrega e cada navegação dispara um refresh desnecessário
# (achado B-M29).
JWT_EXPIRES_MINUTES=15
JWT_REFRESH_EXPIRES_DAYS=7
```

> `frontend/.env.local` também está no `.gitignore`.

---

## Seção 8 — Iniciar o Frontend

```bash
npm run dev
```

### Saída esperada

```
  ▲ Next.js 16.2.6
  - Local:        http://localhost:3000
  - Environments: .env.local

 ✓ Ready in 2.3s
```

Verificação de tipos e lint (opcionais, mas é o que o CI roda):

```bash
npx tsc --noEmit    # esperado: nenhuma saída
npx eslint          # esperado: nenhuma saída
```

---

## Seção 9 — Fluxo de Desenvolvimento

### 9.1 — Três terminais

```bash
# === TERMINAL 1 — banco (sobe uma vez e fica) ===
cd backend
docker compose up -d
# aguardar ~30s no primeiro start

# === TERMINAL 2 — backend ===
cd backend
source .venv/Scripts/activate
uvicorn app.main:app --reload

# === TERMINAL 3 — frontend ===
cd frontend
npm run dev
```

### 9.2 — Checklist "tudo pronto"

| # | Verificação | Esperado |
|---|---|---|
| 1 | `docker ps` | `auditoria-mysql` **Up**, porta `3307` |
| 2 | `alembic current` | `b7c02e91d4a5 (head)` |
| 3 | `curl localhost:8000/health` | `{"status":"Ok","db_status":"Ok",...}` |
| 4 | http://localhost:8000/docs | Swagger **renderizada** |
| 5 | `python -m pytest -q` | `250 passed` |
| 6 | http://localhost:3000 | Landing page carrega |
| 7 | Login com `ADMIN_EMAIL`/`ADMIN_PASSWORD` | Redireciona para `/private/admin` |
| 8 | `JWT_SECRET` idêntico nos dois `.env` | `diff <(grep JWT_SECRET backend/.env) <(grep JWT_SECRET frontend/.env.local)` |

### 9.3 — Smoke test das telas (3 minutos)

| # | Ação | Resultado esperado |
|---|---|---|
| 1 | Login como admin | Home com 4 KPIs, fila de sub-usuários, prévia de mensagens |
| 2 | **Empresas** → uma empresa → **Perfil** | Dados cadastrais carregam |
| 3 | Aba **Dashboard & Template** | Grade de cards com categoria e status |
| 4 | Aba **Usuários** | Usuário principal + sub-usuários |
| 5 | Aba **Auditoria** | Auditorias daquela empresa |
| 6 | **Templates** | Lista de templates com contagem de cards |
| 7 | **Mensagens** | Conversas por empresa |
| 8 | Logout → login como cliente demo | Dashboard do cliente com cards e upload |

### 9.4 — Onboarding de cliente sem SMTP `✅ corrigido em 2026-08-26`

Ao criar um cliente em **Empresas → Novo**, o backend gera uma senha temporária de 12 caracteres, grava o hash e tenta enviá-la por e-mail.

**Sem `SMTP_HOST` configurado** — o caso padrão em dev — a tela exibe um aviso âmbar com o e-mail e a senha temporária:

> **O e-mail de credenciais não foi enviado.**
> Anote a senha temporária agora — ela não será exibida novamente e não há recuperação de senha na plataforma.

> ⚠️ **Anote a senha quando ela aparecer.** O backend guarda apenas o hash, e a plataforma **não tem recuperação de senha** (Sprint E do `roadmap.md`). Se a senha se perder, as saídas são excluir a empresa e recomeçar, ou alterar o hash direto no banco.

**Alternativas em dev:**
- `python scripts/seed_demo_companies.py` cria 5 empresas com senha conhecida;
- um SMTP local de captura (`python -m aiosmtpd -n -l localhost:1025` com `SMTP_HOST=localhost`, `SMTP_PORT=1025`, `SMTP_USE_TLS=false`) imprime a mensagem completa no terminal.

> **O que mudou (B-A29).** Antes desta correção a senha era gerada, hasheada e **descartada**: não aparecia na resposta da API nem no log, e o cliente nascia inacessível. Pior em produção — o envio acontecia **depois** do commit e **fora** de qualquer `try`, então uma falha de SMTP virava HTTP 500 com o usuário já criado; o admin tentava de novo e recebia 409. Hoje o envio devolve um booleano, nunca propaga falha de SMTP, e a senha só trafega quando o e-mail não saiu.

### 9.5 — Portas

| Serviço | Porta (host) | URL |
|---|---|---|
| Frontend | 3000 | http://localhost:3000 |
| Backend | 8000 | http://localhost:8000 |
| MySQL | **3307** | `127.0.0.1:3307` |
| Swagger | 8000 | http://localhost:8000/docs |
| Health check | 8000 | http://localhost:8000/health |

---

## Seção 10 — Stack completa via Docker Compose

Na **raiz** do repositório existe um `docker-compose.yml` que sobe backend + frontend + MySQL juntos. É o caminho mais próximo de produção.

```bash
cd ..                     # raiz do repositório
cp backend/.env.example .env    # e preencha
docker compose up -d --build
```

Variáveis **obrigatórias** no `.env` da raiz (o compose falha explicitamente sem elas):

```ini
MYSQL_PASSWORD=...
MYSQL_ROOT_PASSWORD=...
JWT_SECRET=...
ADMIN_EMAIL=...
ADMIN_PASSWORD=...
ADMIN_FULL_NAME=Administrador
```

O `docker-entrypoint.sh` do backend aplica `alembic upgrade head` e roda `seed_admin.py` automaticamente ao subir.

**Depois de subir, rode os seeds que o entrypoint não cobre:**

```bash
docker exec -it auditoria-backend python scripts/seed_catalog.py
docker exec -it auditoria-backend python scripts/seed_dashboard_templates.py
```

Verificação:

```bash
curl http://localhost:8000/health
curl http://localhost:3000
```

> ⚠️ **Estado desta rota em 2026-08-26:** os Dockerfiles e o compose foram escritos e revisados, mas **`docker build` e `docker run` nunca foram executados de verdade** neste projeto (Sprint D do `roadmap.md`). Se algo falhar aqui, é o primeiro caminho a suspeitar — e registre o resultado em `docs/deploy_producao.md`.

> ⚠️ **Não rode o backend com mais de uma réplica.** Evidências ficam em volume local e o rate limit vive na memória do processo. Ver Sprint D2 no `roadmap.md`.

---

## Seção 11 — Solução de Problemas

### Erros de setup

| Sintoma | Causa | Solução |
|---|---|---|
| `Can't connect to MySQL server on '127.0.0.1:3307'` | Container não subiu, ainda inicializando, ou porta errada | `docker ps` → `docker logs -f auditoria-mysql`; espere `ready for connections` |
| `Access denied for user 'auditoria_app'` | `MYSQL_PASSWORD` do `.env` diferente da senha usada quando o **volume foi criado** | O MySQL só lê essas variáveis na **primeira** criação. `docker compose down -v` e suba de novo |
| `pydantic_core.ValidationError: DATABASE_URL Field required` | `.env` ausente ou no diretório errado | O arquivo precisa estar em `backend/.env`, e o `uvicorn` precisa rodar a partir de `backend/` |
| Senha com `@`, `#` ou `%` na `DATABASE_URL` não funciona | Caractere especial não codificado | Codifique: `@` → `%40`, `#` → `%23`, `%` → `%25` |
| **Login funciona mas `/private/**` volta ao login** | **`JWT_SECRET` diferente entre backend e frontend** | Compare os dois `.env`. É o erro mais comum |
| `Nenhum template padrão configurado` ao criar cliente | `seed_dashboard_templates.py` não foi executado | Rode o seed (Seção 5.3) |
| `ADMIN_PASSWORD não definido` no seed | Variável ausente no `.env` | Preencha `ADMIN_PASSWORD` |
| `ValueError: password cannot be longer than 72 bytes` | Senha acima do limite do bcrypt | Use uma senha menor. Achado **B-A27** |
| `alembic heads` lista mais de uma linha | Branch de migration pendente | Não continue; investigue antes de aplicar |
| `/docs` responde 200 e fica **em branco** | Bloqueio de CSP no navegador | Abra o console (F12). Corrigido em `34f8444`; se voltar, `pytest tests/test_security_headers.py` |
| `curl /api/v1/Monitoring` → 404 | A rota foi **removida** | Use `GET /health`. O `backend/README.md` está desatualizado |
| `Module not found` no frontend | `npm install` não rodou ou `node_modules` corrompido | `rm -rf node_modules package-lock.json && npm install` |
| Porta 3000 ou 8000 ocupada | Outro processo | `npx kill-port 3000` · `netstat -ano \| findstr :8000` |
| `pre-commit` não roda | Instalado a partir de `backend/` | Instale a partir da **raiz** (Seção 3.5) |

### Comportamentos conhecidos que **não** são erro de setup

| Comportamento | Explicação |
|---|---|
| Cliente novo não consegue entrar | Onboarding sem SMTP — ver **Seção 9.4** (achado B-A29) |
| Nenhum e-mail chega em dev | Sem `SMTP_HOST`, o envio é apenas registrado no log |
| `/public/cadastro` existe mas não cria conta | `ALLOW_PUBLIC_REGISTRATION=false` — decisão de produto |
| Badges de mensagens demoram a atualizar | Polling de 45 s, não é tempo real |
| Checklist e histórico aparecem vazios para o cliente | ✅ **Correto** — são registro interno do auditor (após a correção de B-A28) |
| `docker compose down` não apaga os dados | Correto. Use `-v` para apagar o volume |

### Resetar o banco do zero

```bash
cd backend
docker compose down -v
docker compose up -d
# aguardar ~30s — docker logs -f auditoria-mysql
alembic upgrade head
python scripts/seed_catalog.py
python scripts/seed_dashboard_templates.py
python scripts/seed_admin.py
python scripts/seed_demo_companies.py
python scripts/seed_demo_audits.py
```

> `DELETE FROM users;` **não** funciona como reset — as FKs `ON DELETE RESTRICT` de `companies.principal_user_id` e `audits.client_user_id` bloqueiam. O `backend/README.md` sugere esse comando; está errado (divergência RD-11).

### Limpar evidências órfãs

Arquivos em `backend/uploads/` sem registro correspondente em `evidences` (deixados por exclusões anteriores ao BLOCO P):

```bash
python scripts/prune_orphan_uploads.py           # só relata
python scripts/prune_orphan_uploads.py --apply   # remove de fato
```

---

## Seção 12 — Referências

| Documento | Para quê |
|---|---|
| [`index.md`](index.md) | Central de documentação |
| [`executar_projeto.md`](executar_projeto.md) | Operação diária: banco, backup, logs, Docker |
| [`relatorio_geral.md`](relatorio_geral.md) | Arquitetura, stack, fluxos |
| [`relatorio_bugs.md`](relatorio_bugs.md) | O que está quebrado e como corrigir |
| [`deploy_producao.md`](deploy_producao.md) | Deploy em produção |
| [`roadmap.md`](roadmap.md) | O que vem a seguir |

---

*Guia atualizado em 2026-08-26 (rev. 4.0). Cada comando foi conferido contra o código em `34f8444`; o resultado esperado de `pytest`, `alembic current`, `ruff`, `tsc` e `eslint` vem de execução real, não de memória.*
