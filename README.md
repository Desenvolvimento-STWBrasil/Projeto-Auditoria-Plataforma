# Plataforma de Auditoria

![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)
![Python](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-%3E%3D0.115-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![MySQL](https://img.shields.io/badge/MySQL-8.4-4479A1?logo=mysql&logoColor=white)
![Testes](https://img.shields.io/badge/testes-300%2B%20backend%20%7C%20240%2B%20frontend-brightgreen)
![Licença](https://img.shields.io/badge/licença-uso%20interno-lightgrey)

Plataforma web para gestão de processos de auditoria/compliance entre uma equipe auditora (admin) e as empresas auditadas (clientes). Combina um fluxo formal de auditoria (controles, evidências, laudo em PDF) com um quadro Kanban por empresa para acompanhamento contínuo do trabalho.

---

## Índice

- [Visão Geral](#visão-geral)
- [Tecnologias Utilizadas](#tecnologias-utilizadas)
- [Histórico de Desenvolvimento / Changelog](#histórico-de-desenvolvimento--changelog)
- [Como Executar](#como-executar)
- [Como Usar](#como-usar)
- [Estrutura de Arquivos](#estrutura-de-arquivos)
- [Testes](#testes)
- [Licença](#licença)

---

## Visão Geral

A **Plataforma de Auditoria** é um sistema full-stack (API em FastAPI + frontend em Next.js) que digitaliza o relacionamento entre uma equipe de auditoria/compliance e as empresas que ela audita. O objetivo principal é dar visibilidade e rastreabilidade ao processo de conformidade, evitando o vaivém de planilhas e e-mails.

O sistema tem dois portais, com o mesmo login mas telas e permissões diferentes por papel (`admin`, `user`/principal, `sub-user`):

- **Portal do Auditor (admin)** — `/private/admin`
  - Cadastro e gestão de empresas clientes (onboarding cria empresa + usuário principal + quadro em uma única operação).
  - Módulo de **Auditorias formais**: ciclo de vida `DRAFT → ACTIVE → CLOSED`, catálogo fixo de controles (ISO/IEC 27001), status por controle (`EM_ANALISE`, `PARCIAL`, `CONFORME`, `NAOCONFORME`), revisão de evidências enviadas pelo cliente, chat por controle e geração de **laudo em PDF**.
  - **Quadro Kanban por empresa ("quadro")**: colunas/seções, cartões com categoria, etiquetas coloridas, checklist, histórico de alterações e chat por cartão, com drag-and-drop (arquivar/mover colunas e cartões).
  - **Templates de quadro**: blueprints reaproveitáveis (colunas + cartões) aplicados automaticamente ao integrar uma nova empresa.
  - Vocabulários administráveis: categorias de cartão e etiquetas.
  - Aprovação/rejeição de solicitações de sub-usuário feitas pelas empresas.
  - Central de mensagens (chat geral admin ↔ empresa, com contagem de não lidas).
- **Portal do Cliente (empresa auditada)** — `/private/client`
  - Lista dos próprios controles de auditoria, com envio de evidências e status.
  - Visualização **somente leitura** do quadro Kanban da própria empresa (cartões arquivados/ocultos não aparecem).
  - Chat com a equipe auditora (por controle e canal geral da empresa).
  - Usuário principal pode solicitar novos sub-usuários (login adicional) para sua equipe.

Autenticação é feita via **JWT em cookies httpOnly**, com três camadas de verificação (proxy de borda no Next.js, checagem autoritativa no servidor, e validação final na API) e renovação silenciosa via refresh token.

---

## Tecnologias Utilizadas

### Backend (`backend/`)

| Categoria | Tecnologia |
|---|---|
| Linguagem | Python 3.12 |
| Framework web | FastAPI (`>=0.115`) + Uvicorn (ASGI) |
| ORM / Migrations | SQLAlchemy 2.0 (estilo `Mapped`) + Alembic |
| Banco de dados | MySQL 8.4 (via `pymysql`) |
| Autenticação | JWT (`python-jose`), hashing de senha com `bcrypt` |
| Validação/config | Pydantic v2 + `pydantic-settings` |
| Rate limiting | `slowapi` |
| Upload de arquivos | `python-multipart`, `aiofiles` (evidências) |
| Geração de PDF | `reportlab` (laudo de auditoria) |
| Logging | `structlog` (logs estruturados) |
| Testes | `pytest`, `pytest-cov`, `httpx` (client de testes) |
| Lint | `ruff` |

### Frontend (`frontend/`)

| Categoria | Tecnologia |
|---|---|
| Framework | Next.js 16 (App Router, Server Components/Actions) |
| UI | React 19, Tailwind CSS 4 |
| Linguagem | TypeScript (modo estrito) |
| Drag-and-drop | `@dnd-kit` (core/sortable/modifiers) — quadro Kanban |
| Autenticação | `jose` (verificação de JWT), cookies httpOnly |
| Testes | Vitest + Testing Library (`jsdom` sob demanda) |
| Lint | ESLint 9 (`eslint-config-next`) |

### Infraestrutura

- **Docker Compose** (raiz) orquestrando 3 serviços: `mysql` (8.4, utf8mb4), `backend` (FastAPI) e `frontend` (Next.js em modo `standalone`), com volumes nomeados para dados do MySQL e uploads de evidências.
- Compose auxiliar em `backend/docker-compose.yml` para subir apenas o MySQL localmente durante o desenvolvimento do backend fora de containers.
- Dockerfiles dedicados para backend (`python:3.12-slim`) e frontend (build multi-stage `node:20-slim` → runtime standalone).

---

## Histórico de Desenvolvimento / Changelog

> **Nota sobre a fonte destes dados:** este diretório de trabalho não é um repositório Git (não há histórico de commits para extrair datas reais de cada tarefa). O changelog abaixo foi reconstruído a partir da **cadeia de migrações do Alembic** (`backend/alembic/versions/`), que preserva a ordem exata em que o esquema do banco — e, por consequência, as funcionalidades — evoluiu, do primeiro `down_revision = None` até a revisão mais recente (`head`). Datas exatas só são indicadas quando há evidência concreta no próprio código (comentários com data ou timestamp de arquivo claramente distinto); os demais itens são apresentados em ordem cronológica relativa, sem data fixa.

### Fase 1 — Fundação do domínio de auditoria formal
- `86f95e525db1` **Criação do schema inicial (v1)**: tabelas `control_catalog`, `users`, `audits`, `audit_controls`, `evidences`, `messages`.
- `447a4e1de59d` **Fluxo de sub-usuários**: tabela `sub_user_requests` (solicitação → aprovação/rejeição pelo admin).
- `9d5a3c1b2e77` **Domínio de dashboard/empresas**: tabelas `companies` e primeira versão das tabelas de quadro por empresa.
- `d60f999c1fca` Ajustes de `created_at`/defaults em várias tabelas (parte do fluxo de sub-usuários).
- `56d322bbd83a` Índices de performance (1ª rodada) em `audit_controls`.

### Fase 2 — Hardening, auditoria de dados e correções
- `5e977e8b49da` *(2026-06-26)* Colunas de `updated_at`/soft delete (`deleted_at`) em `users`, `audits`, `audit_controls`.
- `5a9233d65599` *(2026-07-27)* Correção da chave primária de `dashboard_card_checklist_items` (regressão introduzida em `d60f999c1fca`).
- `d5c4d7cd6687` Índices de performance (2ª rodada), idempotentes em relação à fase 1.
- `5457e7377a56` Flexibilização de `companies.phone` e `dashboard_cards.control_code` para aceitar nulo, alinhando o banco à realidade da API/UI (onboarding sem telefone, cartões vindos de template sem código de controle).
- `eafa65e9df05` Restauração de índices em `dashboard_card_history_entries` e `dashboard_card_messages`.
- `0ba953b10f8b` Remoção do subsistema de checklist "clássico" (`checklist_items`/`checklist_item_state`), nunca consumido por nenhum endpoint.
- `83cf1e14efa8` Correção de nomes: `evidences.create_at` → `created_at`; tabela `messagens` → `messages`.
- `f224a87de1a4` Correção de nome de coluna em `sub_user_requests` (`request_full_name` → `requested_full_name`), migração condicional/segura para bancos antigos.

### Fase 3 — Mensageria e alinhamento de domínio
- `bf7239a52df8` **Canal de mensagens geral admin ↔ empresa** (`company_messages`), independente do chat por controle.
- `c2a7e6f1b8d3` Adição do status `NAOCONFORME` a `audit_control_status`, unificando o vocabulário de status entre o domínio de auditoria formal e o de dashboard.
- `7e3f9c2b5a1d` Rastreio de leitura (`read_at`) nas mensagens por controle.

### Fase 4 — Categorização e integridade do quadro Kanban
- `4f2b8e6a91d3` **Categorias de cartão** (`dashboard_card_categories`): criação, seed de 4 categorias canônicas, backfill a partir do campo livre `tag`, e novo campo `origin_template_card_id`/`hidden` nos cartões.
- `a3d81f4c7b02` Backfill de `origin_template_card_id` em cartões pré-existentes que ficaram sem essa referência.
- `b7c02e91d4a5` Restrição de unicidade `uq_dashboard_card_origin_per_dashboard`, movendo para o banco a garantia de idempotência ao aplicar um template (antes controlada só em memória).

### Fase 5 — Quadro Kanban completo (colunas, etiquetas, drag-and-drop)
- `c8f1a3e57b90` *(2026-09-08)* **Introdução de colunas de quadro e etiquetas**: `dashboard_template_columns`, `dashboard_columns`, `dashboard_labels`, `dashboard_card_labels` (M:N), posicionamento por índice fracionário (`fractional_index.py`), com backfill de dados para que nenhum quadro existente ficasse vazio.
- Em paralelo, no frontend: implementação do quadro drag-and-drop com `@dnd-kit` (`board.tsx`, `board-column.tsx`, `board-card.tsx`), painel de detalhe de cartão (checklist, histórico, chat), visão somente leitura para o cliente (`/private/client/quadro`) e gestão de templates/categorias/etiquetas no portal admin.

### Fase 6 — Endurecimento de segurança e qualidade (mais recente)
- *(2026-08-26)* Auditoria de dependências com `pip-audit` no CI identifica 7 CVEs em `slowapi`/`python-multipart` (parser de multipart usado exatamente no upload de evidências); dependência atualizada para `python-multipart>=0.0.31`.
- Fixação de versões por CVE: `pytest>=9.0.3` (PYSEC-2026-1845).
- Consolidação de regras de acesso (`app/core/access.py` + `app/core/policy.py`): distinção explícita entre "dono do dado" e "permissão de ação" (ex.: só o auditor pode declarar conformidade, mover cartões ou ler notas internas do auditor).
- Guard contra path traversal no armazenamento de evidências (`storage.py` / `test_storage_path_guard.py`).
- Suíte de testes ampla dos dois lados: **mais de 300 testes no backend** (auth, autorização, cada módulo de domínio, migrações — rodando contra SQLite em memória, sem depender do MySQL) e testes de contrato no frontend (Server Actions mockando `callBackend`, sem duplicar a cobertura do backend).
- Scripts de manutenção: `prune_orphan_uploads.py` (evidências órfãs no disco) e `backfill_company_cliente01.py` (correção pontual de dado de produção).

---

## Como Executar

### Opção A — Stack completa via Docker Compose (recomendado)

Pré-requisitos: Docker Desktop.

1. Gere um segredo para o JWT:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   Na raiz do projeto, crie um arquivo `.env` com as variáveis exigidas pelo `docker-compose.yml`, usando o valor gerado acima em `JWT_SECRET`:
   ```
   MYSQL_ROOT_PASSWORD=defina_uma_senha
   MYSQL_PASSWORD=defina_uma_senha
   JWT_SECRET=<valor_gerado_acima>
   ADMIN_EMAIL=admin@exemplo.local
   ADMIN_FULL_NAME=Administrador
   ADMIN_PASSWORD=defina_uma_senha_forte
   ```
2. Suba os três serviços:
   ```bash
   docker compose up -d --build
   ```
   O `docker-entrypoint.sh` do backend já roda `alembic upgrade head` e garante o usuário admin (via `scripts/seed_admin.py`) automaticamente na subida do container — não é preciso fazer isso manualmente.
3. (Opcional) Popule o catálogo de controles e/ou os templates de quadro:
   ```bash
   docker compose exec backend python scripts/seed_catalog.py
   docker compose exec backend python scripts/seed_dashboard_templates.py
   ```
4. Acesse:
   - Frontend: http://localhost:3000
   - API / Swagger: http://localhost:8000/docs

### Opção B — Desenvolvimento local (backend e frontend separados)

#### Backend

```bash
cd backend
docker compose up -d              # sobe só o MySQL (porta 3307)
cp .env.example .env               # ajuste DATABASE_URL, JWT_SECRET, etc.
python -m venv venv
source venv/Scripts/activate       # Git Bash (ou venv\Scripts\activate no PowerShell)
pip install -r requirements.txt
alembic upgrade head
python scripts/seed_admin.py       # cria o usuário admin inicial
python scripts/seed_catalog.py     # popula o catálogo de controles
uvicorn app.main:app --reload      # API em http://localhost:8000/docs
```

Detalhes adicionais (consultas SQL manuais, reset de dados) estão em [`backend/README.md`](backend/README.md).

#### Frontend

```bash
cd frontend
npm install
npm run dev                        # http://localhost:3000
```

Antes de rodar, crie `frontend/.env.local` (não versionado) com as variáveis abaixo.

`frontend/.env.local` precisa conter, **com os mesmos valores usados no backend**:
```
BACKEND_API_URL=http://127.0.0.1:8000
JWT_SECRET=<idêntico ao JWT_SECRET do backend>
JWT_ALGORITHM=HS256
JWT_EXPIRES_MINUTES=15
```
> Divergência entre esses valores e os do backend faz o cookie de sessão expirar de forma inconsistente com o token.

### Testes

```bash
# Backend (usa SQLite em memória — não depende do MySQL rodando)
cd backend && pytest

# Frontend
cd frontend && npm test
```

### Opção C — Deploy em produção (Docker Compose + Nginx + CI/CD)

A stack de produção roda em 4 serviços (`mysql`, `backend`, `frontend`, `nginx`),
com o Nginx como único ponto de entrada público (TLS via Let's Encrypt) e deploy
automatizado por push na `main` via GitHub Actions.

- Arquivos: `docker-compose.prod.yml`, `nginx/nginx.conf`, `.env.prod.example`,
  `.github/workflows/deploy.yml`.
- Guia completo (passo a passo, primeiro deploy manual, troubleshooting):
  [`docs/Code.md`](docs/Code.md#7-guia-prático-de-execução).
- Decisões e justificativas de arquitetura: [`docs/prd_deploy_producao.md`](docs/prd_deploy_producao.md).

---

## Como Usar

Com a stack no ar (veja [Como Executar](#como-executar)), o fluxo típico é:

### 1. Login

O usuário admin inicial é criado pelo `seed_admin.py` (ou automaticamente pelo container, via `docker-entrypoint.sh`) com o e-mail/senha definidos em `ADMIN_EMAIL`/`ADMIN_PASSWORD`. Acesse **http://localhost:3000** e entre com essas credenciais para cair no **Portal do Auditor** (`/private/admin`).

Também é possível autenticar diretamente na API (útil para testar/integrar), o que devolve um par de tokens JWT e seta os cookies httpOnly de sessão:

```bash
curl -i -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@exemplo.local", "password": "sua_senha"}'
```

A API interativa (Swagger) fica em **http://localhost:8000/docs** — todos os endpoints podem ser explorados e testados por lá, incluindo o fluxo de `refresh` token (`POST /api/v1/auth/refresh`).

### 2. Cadastrar uma empresa (onboarding)

No Portal do Auditor, em **Empresas → Nova empresa**, o onboarding cria em uma única operação: a empresa, o usuário principal (que recebe a senha temporária por e-mail, se SMTP estiver configurado) e o quadro Kanban já populado a partir de um template padrão.

### 3. Acompanhar pelo quadro Kanban

Em **Empresas → [empresa] → Quadro**, o admin organiza o trabalho em colunas com cartões (categoria, etiquetas, checklist, histórico e chat por cartão), reordenando por arrastar-e-soltar. O cliente enxerga o mesmo quadro em modo somente leitura no seu portal (`/private/client/quadro`).

### 4. Conduzir uma auditoria formal

Em **Empresas → [empresa] → Auditoria**, o admin abre uma auditoria (`DRAFT → ACTIVE → CLOSED`), avalia cada controle do catálogo ISO/IEC 27001 (`EM_ANALISE`, `PARCIAL`, `CONFORME`, `NAOCONFORME`), troca mensagens com o cliente por controle e, ao fechar o ciclo, gera o **laudo em PDF** com um clique.

O cliente, do seu lado, acessa **Meus Controles** para enviar evidências (upload) e acompanhar o status de cada item.

> Para rodar a suíte de testes ao alterar código, veja [Testes](#testes) em "Como Executar".

---

## Estrutura de Arquivos

```
Developer/
├── docker-compose.yml        # Orquestra mysql + backend + frontend (stack completa)
├── backend/                  # API — FastAPI + SQLAlchemy + MySQL
│   ├── app/
│   │   ├── api/v1/           # Rotas HTTP (auth, admin, client, dashboard, empresas, mensagens...)
│   │   ├── core/             # Config, JWT, segurança, política de acesso (access.py/policy.py)
│   │   ├── db/                # Session e Base do SQLAlchemy
│   │   ├── middleware/        # Security headers, request-id
│   │   ├── models/            # Entidades ORM (User, Audit, Company, DashboardCard...)
│   │   ├── repositories/      # Acesso a dados (audit_repository, user_repository)
│   │   ├── schemas/           # Schemas Pydantic (request/response)
│   │   └── services/          # Regras de negócio (relatórios PDF, storage, templates, e-mail...)
│   ├── alembic/versions/      # Histórico de migrações do banco (ver Changelog acima)
│   ├── scripts/               # Seeds e utilitários de manutenção
│   ├── tests/                 # 300+ testes (pytest, SQLite em memória)
│   └── docker-compose.yml     # MySQL isolado para desenvolvimento local
├── frontend/                  # Next.js 16 (App Router)
│   ├── app/
│   │   ├── public/            # Login e cadastro (rotas públicas)
│   │   ├── private/
│   │   │   ├── admin/         # Portal do auditor (empresas, auditorias, quadro, templates, mensagens)
│   │   │   └── client/        # Portal do cliente (controles, quadro somente leitura, mensagens)
│   │   └── api/                # Route handlers (proxy de auth, download de evidências/laudo)
│   ├── lib/                    # Sessão/JWT, formatação de data, proteção de redirect, cliente da API
│   ├── proxy.ts                 # Substituto do middleware.ts (Next 16) — checagem otimista de sessão
│   └── test/                   # Helpers e stubs compartilhados pelos testes
├── docs/                      # Documentação de processo/produto (PRD, specs, backlog, roadmap,
│                               #   relatórios de bugs/melhorias/commits, guia de deploy...)
└── .vscode/                    # Configurações do editor (interpretador Python do venv)
```

---

## Licença

Projeto interno da **STW Brasil** — uso restrito. Todo o código, dados e documentação deste repositório são de propriedade da STW Brasil; não há licença de código aberto associada, e a redistribuição, cópia ou uso fora do contexto da equipe autorizada não é permitida sem consentimento prévio.
