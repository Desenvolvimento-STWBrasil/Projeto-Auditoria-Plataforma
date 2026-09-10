# Relatório Geral do Projeto — Plataforma de Auditoria

| Campo | Valor |
|---|---|
| **Data da Análise** | 2026-06-24 (criação) · 2026-07-27 (rev. 2.0) · 2026-08-11 (rev. 3.0) · 2026-08-12 (rev. 4.0) · 2026-08-17 (rev. 5.0) · 2026-08-17 (rev. 6.0) · 2026-08-24 (rev. 7.0) · **2026-08-26 (rev. 8.0 — esta revisão)** |
| **Versão do Relatório** | 9.0 |
| **Analista** | Claude Code (Anthropic) |
| **Branch Analisado** | `main` (HEAD `c769526`) — PRs #1 e #2 mergeados |
| **Commits no branch** | 50 |
| **Escopo** | Leitura integral de `backend/app/**`, `backend/alembic/**`, `backend/scripts/**`, `backend/tests/**`, `frontend/app/**`, `frontend/lib/**`, `frontend/proxy.ts`, `.github/**`, `docker-compose.yml`, `.pre-commit-config.yaml` e toda a pasta `docs/` |
| **Verificação por execução** | `pytest -q` → **250 passed, 0 failed** (68,6 s — eram 202 no levantamento; o BLOCO Q acrescentou 48) · `ruff check app scripts tests` → **All checks passed** · `alembic heads` → **`b7c02e91d4a5` (head único)** · `tsc --noEmit` → **0 erros** · `eslint` → **0 erros** · enumeração de rotas via `app.openapi()` → **64 operações** |

---

> ### ✅ Atualização 2026-08-26 (rev. 8.0) — Leia antes do resto do documento
>
> Desde a rev. 7.0 (2026-08-24, HEAD `66578f0`) entraram **3 commits**, dos quais **2 alteram código**:
>
> | Commit | O quê |
> |---|---|
> | `4fd576f` | **BLOCO P** — o commit de segurança do projeto. Fecha 1 achado Crítico, 4 Altos e 3 Médios da auditoria adversarial, e instala **5 barreiras estruturais** para impedir a reincidência de cada classe de defeito. |
> | `9e3076f` | Documentação da auditoria adversarial (rev. 8.0 de `relatorio_bugs.md`) e consolidação dos dois `Prompt_*.txt` da raiz em `INSTRUCTIONS.md`. |
> | `34f8444` | **Correção do CSP** — a política uniforme `default-src 'none'` introduzida em P.4.4 deixava `/docs` e `/redoc` renderizando em branco (200 no servidor, bloqueio no navegador). |
>
> **O que mudou de fato no código, verificado nesta revisão:**
>
> | Área | Antes (rev. 7.0) | Agora (rev. 8.0) |
> |---|---|---|
> | Testes automatizados (backend) | 128 | **202** (+74) |
> | Arquivos de teste | 15 | **18** (+3: autorização, migrations, security headers) |
> | Migrations Alembic | 17 (head `4f2b8e6a91d3`) | **19** (head `b7c02e91d4a5`) |
> | Camada de política de autorização | não existia | **`app/core/policy.py`** — `Action` + `ALLOWED_ROLES` como fonte única |
> | Exclusão de arquivo de evidência | nunca acontecia | **`storage.delete_files()`** + `scripts/prune_orphan_uploads.py` |
> | Jobs de CI | 2 (backend, frontend) | **4** (+ `secrets`/gitleaks, + `migrations` contra MySQL 8.4 real) |
> | Cabeçalhos de segurança | 5 (sem CSP/HSTS) | **7** — CSP por rota (API × docs) e HSTS sob HTTPS |
> | Credenciais expostas (B-C23) | senha do MySQL e do admin **em uso** e versionadas | **rotacionadas** — verificado: nenhum valor do `.env` atual aparece em commit algum do histórico |
>
> **Conclusão da revisão:** o projeto saiu de "MVP maduro com achados críticos abertos" para **"MVP maduro com dívida técnica conhecida e sob barreira automatizada"**. O maior gap remanescente não é mais de segurança — é **0% de cobertura de testes no frontend** (7.811 LOC) e a **ausência de escala horizontal**.

---

## 1. Resumo Executivo

A **Plataforma de Auditoria** é um sistema web B2B para gestão de processos de auditoria de conformidade (controles no estilo ISO 27001/ISMS). Permite que uma empresa de auditoria gerencie seus clientes, instancie auditorias com controles de conformidade, colete evidências, converse com o cliente (por controle, por card e por empresa), encerre auditorias formalmente, exporte relatórios em PDF e acompanhe o status de conformidade em um dashboard gerencial modelado por templates reutilizáveis.

### Estado Atual do Projeto

| Camada | Maturidade | Observação |
|---|---|---|
| Backend (FastAPI) | 9,5/10 | 62 endpoints em `/api/v1`, 11 routers, 9 serviços, 202 testes verdes, lint limpo, camada de política de autorização explícita |
| Frontend (Next.js 16) | 8,0/10 | 15 páginas, 9 grupos de Server Actions, 5 route handlers; tipa e linta limpo — **sem nenhum teste automatizado** |
| Banco de Dados | 9,0/10 | 18 tabelas de domínio, 19 migrations com head único, downgrades validados no CI, constraints de unicidade que sustentam invariantes de negócio |
| Segurança | 8,5/10 | Autorização por papel centralizada, CSP/HSTS, gitleaks no pre-commit e no CI, pip-audit, rate limiting, credenciais rotacionadas — sem revogação de token e sem trilha append-only |
| Qualidade de Código | 8,5/10 | Bem organizado e coberto; ainda há duplicação pontual e 4 arquivos de frontend acima de 500 LOC |
| Documentação | 10/10 (nesta revisão) | `docs/` sincronizada por leitura direta de código e execução real em 2026-08-26 |
| Testes | 8,0/10 | 202 casos no backend cobrindo os fluxos críticos e a matriz de autorização; **0 no frontend** |
| Observabilidade | 5/10 | Logging estruturado (structlog + X-Request-ID) e health check real; sem métricas, sem tracing, sem alarme |
| DevOps / Infraestrutura | 9,0/10 | Dockerfiles, compose completo, **4 jobs de CI executando e verdes** em `main` — incluindo `downgrade base` contra MySQL 8.4 real. Falta validar os builds Docker |

### Avaliação Geral

**Maturidade técnica global: ~95%** de um MVP pronto para produção controlada.

O que caracteriza esta revisão é a **mudança de natureza da dívida remanescente**. Até a rev. 7.0, os achados abertos eram de *correção* — coisas erradas no código que precisavam ser consertadas. O BLOCO P consertou todas elas e, mais importante, para cada correção entregou também a **barreira** que impede a reincidência:

| Correção | Barreira instalada |
|---|---|
| Cliente auditado declarava a própria conformidade (B-A23) | `app/core/policy.py` — fonte única de verdade — + `tests/test_authorization_matrix.py`, que exercita cada endpoint de escrita com cada papel que **não** deveria poder executá-lo |
| Evidências sobreviviam à exclusão da empresa (B-A26) | `StorageBackend` como `Protocol` com `delete` obrigatório: uma implementação nova (S3, Azure Blob) não compila sem responder "como eu apago?" |
| Cards duplicados ao reaplicar template (B-A24) | `UniqueConstraint(dashboard_id, origin_template_card_id)` no banco — a invariante deixa de depender da disciplina do código |
| Nome de arquivo de migration divergindo do `revision` declarado — a **terceira** ocorrência da mesma classe de incidente | `tests/test_migrations_smoke.py` + job `migrations` no CI contra MySQL 8.4 real, com `downgrade base` e `upgrade head` |
| Credenciais versionadas (B-C23) | `gitleaks` no pre-commit (movido para a **raiz**, onde de fato resolve) e como job próprio no CI |

O defeito nº 14, corrigido em `34f8444`, merece registro à parte porque ilustra o limite dessas barreiras: o CSP de P.4.4 tinha teste, o teste passava, e o header estava presente — mas a página `/docs` renderizava **em branco**. O teste afirmava "o header existe", não "a página funciona sob esse header". A correção veio junto com o teste certo: varrer o HTML real de `/docs` e `/redoc`, extrair cada origem que a página pede e afirmar que a diretiva correspondente do CSP a permite.

**Duas lacunas estruturais permanecem abertas:**

1. **0% de testes no frontend** (7.811 LOC). É o maior gap do projeto, e a justificativa é empírica: os defeitos que escaparam da revisão estática em BLOCO O e BLOCO P foram, em sua maioria, encontrados por execução — não por leitura.
2. **A aplicação não escala horizontalmente.** Evidências vivem em volume local e o rate limit é em memória de processo. Rodar com mais de uma réplica quebra os dois.

---

## 2. Objetivo da Aplicação

A plataforma atende empresas de auditoria que precisam:

1. **Cadastrar clientes** (usuários principais) e suas empresas de forma automatizada (onboarding transacional).
2. **Modelar o trabalho** por meio de **templates de dashboard** reutilizáveis e um **vocabulário de categorias** controlado, ambos editáveis pela própria UI do admin.
3. **Instanciar auditorias** associando um cliente a todos os controles do catálogo mestre.
4. **Coletar evidências** de cada controle (upload pelo cliente, persistido em disco) e **baixá-las** (admin).
5. **Acompanhar status** de conformidade por controle e por card (`EM_ANALISE` · `PARCIAL` · `CONFORME` · `NAOCONFORME`), unificado entre os dois domínios.
6. **Encerrar formalmente uma auditoria** (`AuditStatus.CLOSED`) e **exportar relatório consolidado em PDF**.
7. **Comunicar** dúvidas e respostas em três granularidades: por controle de auditoria, por card de dashboard e por um **canal geral assíncrono** entre admin e cliente.
8. **Gerenciar sub-usuários** delegados pelo cliente principal.
9. **Operar tudo de um cliente em um lugar só** — a aba "Configurações do Cliente" reúne Perfil, Dashboard & Template, Usuários e Auditoria sob a mesma empresa.

A plataforma é **multi-tenant por design**: cada empresa cliente tem seu próprio espaço de dados (`Company` 1:1 com o usuário principal, `Dashboard` 1:1 com a empresa), isolado por checagem de posse em cada endpoint.

**Princípio de domínio explicitado no BLOCO P:** *posse não é permissão*. O cliente é dono dos próprios cards e evidências, mas quem **declara conformidade** é o auditor. Essa distinção deixou de ser uma convenção implícita espalhada por 11 routers e virou código em `app/core/policy.py`.

---

## 3. Tecnologias Utilizadas

### Backend

| Tecnologia | Versão (`requirements.txt`) | Papel |
|---|---|---|
| Python | 3.12 (fixado em `Dockerfile`/CI) — validado também sob 3.14 no ambiente de dev | Linguagem principal |
| FastAPI | >= 0.115.0 | Framework web ASGI |
| Uvicorn[standard] | >= 0.32.0 | Servidor ASGI |
| SQLAlchemy | >= 2.0.0 | ORM declarativo (estilo 2.0, `Mapped[...]`) |
| Alembic | >= 1.13.0 | Migrações de banco |
| Pydantic | >= 2.9.0 (`pydantic[email]`) | Validação de dados/schemas |
| pydantic-settings | >= 2.6.0 | Configuração via `.env` |
| python-dotenv | >= 1.0.0 | Import direto em `scripts/seed_admin.py` (declarado em B-B16) |
| python-jose[cryptography] | >= 3.3.0 | JWT (access + refresh) |
| bcrypt | >= 4.0.0 | Hash de senha |
| pymysql + cryptography | >= 1.1.0 / >= 42.0.0 | Driver MySQL |
| slowapi | 0.1.9 | Rate limiting por IP |
| python-multipart | 0.0.9 | Upload de arquivo |
| aiofiles | 23.2.1 | I/O assíncrono de arquivo |
| structlog | (sem pin) | Logging estruturado JSON |
| reportlab | 4.2.5 | Geração do PDF de relatório |
| pytest + pytest-cov + httpx | 8.2.0 / 5.0.0 / 0.27.0 | Testes automatizados |
| ruff | 0.4.4 | Lint (dev/CI) |
| pip-audit | (instalado no job de CI) | Falha o build em CVE conhecida de dependência declarada |

### Frontend

| Tecnologia | Versão (`package.json`) | Papel |
|---|---|---|
| Next.js | **16.2.6** (App Router) | Framework React full-stack |
| React / React DOM | 19.2.4 | Biblioteca de UI |
| TypeScript | ^5 | Tipagem estática |
| Tailwind CSS | ^4 (via `@tailwindcss/postcss`) | Estilização utilitária |
| jose | ^6.2.8 | Verificação de JWT no servidor/proxy |
| server-only | ^0.0.1 | Barreira de import servidor↔cliente |
| ESLint | ^9 + `eslint-config-next` 16.2.6 | Lint |

> **Nota:** `frontend/AGENTS.md` e `frontend/CLAUDE.md` avisam que esta é uma versão do Next.js com **breaking changes** frente ao conhecimento convencional — confirmado: `middleware.ts` foi descontinuado em favor de `proxy.ts` (ver seção 4), e tipos gerados como `PageProps<"/rota">` / `LayoutProps<"/rota">` são usados nas assinaturas de página.
>
> O nome do pacote, que estava como `"forntend_v"` (typo B-B09), foi corrigido para **`plataforma-auditoria-frontend`** em `4fd576f`.

### Infraestrutura e Automação

| Tecnologia | Versão | Papel |
|---|---|---|
| MySQL | 8.4 (`mysql:8.4`) | Banco relacional, `utf8mb4_unicode_ci` |
| Docker / Docker Compose | — | `backend/docker-compose.yml` (só o banco, dev) **+** `docker-compose.yml` na raiz (stack completa) |
| SMTP (opcional) | — | E-mail de credenciais (fallback: log estruturado em dev) |
| GitHub Actions | — | `ci.yml` (4 jobs) e `commit-report.yml` (gera `docs/relatorio_commit.md`) |
| gitleaks | v8.18.4 | Varredura de segredos — `.pre-commit-config.yaml` **na raiz** + job `secrets` no CI |

---

## 4. Arquitetura Atual

```
┌───────────────────────────────────────────────────────────────────────┐
│                        NAVEGADOR DO USUÁRIO                           │
│               (admin, cliente principal, sub-usuário)                 │
└──────────────────────────────┬────────────────────────────────────────┘
                               │ HTTP / cookies httpOnly (access+refresh)
┌──────────────────────────────▼────────────────────────────────────────┐
│               NEXT.JS 16 FRONTEND (Port 3000, App Router)             │
│  ┌────────────────────┐ ┌────────────────────┐ ┌───────────────────┐  │
│  │ Server Components  │ │ Server Actions     │ │ proxy.ts          │  │
│  │ /private/admin/**  │ │ actions.ts (9)     │ │ (era middleware.  │  │
│  │ /private/client/** │ │ por rota →         │ │  ts — Next 16)    │  │
│  │ chamam callBackend │ │ callBackend direto │ │ Auth guard +      │  │
│  │ (lib/session.ts)   │ │ no FastAPI         │ │ auto-refresh +    │  │
│  │                    │ │                    │ │ validação de role │  │
│  └────────────────────┘ └────────────────────┘ └───────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ Route Handlers (app/api/*) — 5 rotas com consumidor real:       │  │
│  │  /api/auth/{login,logout,register} (setam cookies httpOnly a    │  │
│  │  partir de Client Components) + 2 proxies autenticados de       │  │
│  │  binário: /api/admin/audits/[auditId]/report (PDF) e            │  │
│  │  /api/admin/evidences/[evidenceId]/download (arquivo)           │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬────────────────────────────────────────┘
                               │ HTTP/JSON + Bearer Token (Authorization)
┌──────────────────────────────▼────────────────────────────────────────┐
│                    FASTAPI BACKEND (Port 8000)                        │
│  ┌────────────────────┐ ┌──────────────────┐ ┌────────────────────┐   │
│  │ Routers v1 (11)    │ │ Services (9)     │ │ Core / Middleware  │   │
│  │ auth · users       │ │ users            │ │ config.py          │   │
│  │ admin · client     │ │ dashboard_builder│ │ jwt.py (acc+refr)  │   │
│  │ sub_users          │ │ dashboard_       │ │ security.py bcrypt │   │
│  │ admin_onboarding   │ │  template_admin  │ │ policy.py 🆕 P.1   │   │
│  │ companies          │ │ company_admin    │ │ SecurityHeaders    │   │
│  │ company_messages   │ │ email_sender     │ │ (CSP por rota) 🔄  │   │
│  │ dashboard_cards    │ │ storage 🔄 delete│ │ RequestID+structlog│   │
│  │ dashboard_         │ │ storage_backend🆕│ │ slowapi rate limit │   │
│  │  categories        │ │ audit_reporting  │ └────────────────────┘   │
│  │ dashboard_         │ │ report_generator │ ┌────────────────────┐   │
│  │  templates         │ └──────────────────┘ │ GET /health (fora  │   │
│  └────────────────────┘                      │ do /v1, SELECT 1)  │   │
│  ┌────────────────────┐ ┌──────────────────┐ └────────────────────┘   │
│  │ SQLAlchemy ORM     │ │ Repositories     │                          │
│  │ 18 classes /       │ │ UserRepository   │                          │
│  │ 9 arquivos         │ │ AuditRepository  │                          │
│  └────────────────────┘ └──────────────────┘                          │
└──────────────────────────────┬────────────────────────────────────────┘
                               │ pymysql / SQLAlchemy 2.0
┌──────────────────────────────▼────────────────────────────────────────┐
│                    MySQL 8.4 (Docker — Port 3307 em dev)              │
│   Database: auditoria │ charset utf8mb4_unicode_ci                    │
│   18 tabelas de domínio │ 19 migrations (head b7c02e91d4a5) │ 6 seeds │
└───────────────────────────────────────────────────────────────────────┘
```

### Padrão de Autenticação (access + refresh token)

```
LoginForm (client)      /api/auth/login (route handler)   FastAPI /auth/login
      │── POST email/senha ──────────▶│                          │
      │                               │── POST /api/v1/auth/login ─▶│
      │                               │◀─ {access_token, refresh_token}│
      │                               │  seta 2 cookies httpOnly      │
      │◀── {ok:true, role} ───────────│                               │

Navegação para /private/*  →  proxy.ts (matcher: "/", "/private/:path*", "/public/:path*")
   1. Lê cookie access_token; verifica assinatura/expiração com `jose` (sem round-trip à API).
   2. Se expirado/ausente mas há refresh_token válido: chama POST /api/v1/auth/refresh
      diretamente no backend e re-emite os 2 cookies (renovação silenciosa).
   3. Decodifica `role` do payload e valida simetricamente:
      admin em /private/client → redireciona para /private/admin (e vice-versa).
   4. Sem sessão válida → redireciona para /public/login?redirect=<rota original>.
   5. Em "/", "/public/login" e "/public/cadastro": limpa os cookies (logout forçado).

Dentro de um Server Component/Server Action (checagem AUTORITATIVA, não apenas otimista):
      lib/session.ts::requireUser()/requireAdmin()/requireClient()
        → getCurrentUser() decodifica o JWT do cookie (memoizado por requisição via cache())
        → callBackend() chama o FastAPI com "Authorization: Bearer <token>"
        → o backend valida a assinatura de novo em app/api/deps.py::get_current_user
        → e, para ações de escrita sensíveis, consulta app/core/policy.py::assert_can()
```

> **Defesa em profundidade explícita:** `proxy.ts` documenta no próprio arquivo que sua checagem é **otimista** e que nunca se deve depender só dela para autorização. As camadas (proxy → DAL → endpoint → política) validam de forma independente. A simetria também vale para o **tipo** de token: um `refresh_token` é recusado tanto em `deps.py::get_current_user` quanto em `session.ts::getCurrentUser`.

### Camada de Política de Autorização (`app/core/policy.py` — 🆕 BLOCO P.1)

Antes do BLOCO P, a autorização vivia como condições ad-hoc espalhadas pelos routers, e a checagem dominante era de **posse** (`o card pertence à empresa deste usuário?`). Isso permitia que o próprio auditado marcasse um card como `CONFORME` e escrevesse na trilha de histórico.

Hoje existe um enum `Action` e um mapa `ALLOWED_ROLES` como fonte única:

| Ação | Papéis permitidos |
|---|---|
| `SET_CARD_STATUS`, `SET_CONTROL_STATUS` | `admin` |
| `WRITE_CARD_HISTORY`, `TOGGLE_CHECKLIST`, `WRITE_CARD_NOTE` | `admin` |
| `CLOSE_AUDIT`, `MANAGE_TEMPLATE`, `MANAGE_CATEGORY`, `DELETE_COMPANY` | `admin` |
| `UPLOAD_EVIDENCE` | `user`, `sub-user` |
| `ASK_QUESTION` | `admin`, `user`, `sub-user` |
| `REQUEST_SUB_USER` | `user` |

`can(action, role)` responde a pergunta; `assert_can(action, role)` levanta 403. O ponto de projeto é que **uma linha nesse mapa é mais fácil de revisar num PR do que uma condição escondida no meio de um router**.

### Cabeçalhos de Segurança (`app/middleware/security_headers.py` — 🔄 corrigido em `34f8444`)

Sete cabeçalhos em toda resposta: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`, `Permissions-Policy`, `Content-Security-Policy` e — apenas sob HTTPS — `Strict-Transport-Security`.

O CSP é **duplo, resolvido por rota**:

| Política | Onde se aplica | Conteúdo |
|---|---|---|
| `API_CSP` | todas as rotas de dados e `/openapi.json` | `default-src 'none'; frame-ancestors 'none'; base-uri 'none'` |
| `DOCS_CSP` | `/docs`, `/redoc`, `/docs/oauth2-redirect` | libera exatamente as origens que o HTML do FastAPI referencia: `cdn.jsdelivr.net` (bundle/CSS), `fonts.googleapis.com` + `fonts.gstatic.com` (ReDoc), `fastapi.tiangolo.com` (favicon), `connect-src 'self'` (fetch do `openapi.json`) |

As rotas de documentação são lidas de `app.docs_url` / `app.redoc_url` / `app.swagger_ui_oauth2_redirect_url` em vez de fixadas — se forem desativadas em produção, o middleware acompanha sem edição.

---

## 5. Estrutura de Pastas (estado real em 2026-08-26)

```
Developer/
├── INSTRUCTIONS.md                       ← Diretivas de execução (consolidou os 2 Prompt_*.txt)
├── docs/                                 ← Documentação técnica (17 arquivos)
├── Arquivo/                              ← Requisitos originais (Word/PDF/PPTX)
├── .gitignore, .gitattributes
├── .pre-commit-config.yaml               ← 🔄 movido de backend/ para a RAIZ (gitleaks)
├── docker-compose.yml                    ← Stack completa (backend+frontend+MySQL)
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                        ← 4 jobs: backend · frontend · secrets · migrations
│   │   └── commit-report.yml             ← Gera docs/relatorio_commit.md a cada push em main
│   └── scripts/generate_commit_report.py
│
├── backend/                              ← API FastAPI (5.703 LOC em app/)
│   ├── alembic/
│   │   ├── env.py                        ← importa todos os módulos de model ativos
│   │   └── versions/ (19 migrations, head b7c02e91d4a5)
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py                   ← get_current_user, require_admin, require_main_user
│   │   │   ├── health.py                 ← GET /health (fora do prefixo /api/v1)
│   │   │   └── v1/                       ← 11 routers + router.py (62 operações)
│   │   │       ├── router.py             ← agrega todos os routers
│   │   │       ├── auth.py               ← /register, /login, /refresh
│   │   │       ├── users.py              ← /perfil
│   │   │       ├── admin.py              ← auditorias (CRUD, status, PDF), evidências,
│   │   │       │                            mensagens por controle, /admin/users?role=
│   │   │       ├── client.py             ← /controls, /evidences, /messages, /client/audits
│   │   │       ├── sub_users.py          ← fluxo completo de sub-usuário
│   │   │       ├── admin_onboarding.py   ← /onboarding/{principal-user,companies,templates}
│   │   │       ├── companies.py          ← /admin/companies — CRUD + exclusão em cascata
│   │   │       ├── company_messages.py   ← mensagens gerais admin↔cliente por empresa
│   │   │       ├── dashboard_cards.py    ← runtime do dashboard (610 LOC, maior do backend)
│   │   │       ├── dashboard_categories.py  ← CRUD de categorias de card
│   │   │       └── dashboard_templates.py   ← CRUD de template e card de template
│   │   ├── core/
│   │   │   ├── config.py                 ← Settings (pydantic-settings, AliasChoices)
│   │   │   ├── jwt.py                    ← create_access_token / create_refresh_token /
│   │   │   │                                decode_token / decode_refresh_token
│   │   │   ├── policy.py                 ← 🆕 P.1 — Action + ALLOWED_ROLES + can/assert_can
│   │   │   ├── security.py               ← hash_password / verify_password (bcrypt)
│   │   │   └── logging.py                ← configure_logging (structlog JSON)
│   │   ├── db/
│   │   │   ├── base.py                   ← DeclarativeBase
│   │   │   ├── session.py                ← engine (pool_pre_ping), SessionLocal, get_db()
│   │   │   └── mixins.py                 ← TimestampMixim* / SoftDeleteMixin
│   │   ├── middleware/
│   │   │   ├── security_headers.py       ← 🔄 7 headers, CSP duplo (API_CSP × DOCS_CSP)
│   │   │   └── request_id.py             ← structlog + X-Request-ID por requisição
│   │   ├── models/ (9 arquivos, 18 classes — ver seção 8)
│   │   ├── repositories/
│   │   │   ├── user_repository.py        ← get_by_id/get_by_email/list_by_role/create
│   │   │   └── audit_repository.py       ← get_by_id/list_by_client/create_with_controls
│   │   ├── schemas/ (10 arquivos Pydantic)
│   │   ├── services/ (9 arquivos, 1.421 LOC)
│   │   │   ├── users.py                  ← authenticate_user, create_user, senha temporária
│   │   │   ├── dashboard_builder.py      ← factory empresa+dashboard+cards a partir de template
│   │   │   ├── dashboard_template_admin.py  ← CRUD de template/categoria, aplicação
│   │   │   │                                idempotente e bulk (547 LOC)
│   │   │   ├── company_admin.py          ← CRUD e exclusão em cascata de empresa
│   │   │   ├── email_sender.py           ← SMTP ou log estruturado em dev
│   │   │   ├── storage.py                ← 🔄 save_file + get_absolute_path + delete_files
│   │   │   ├── storage_backend.py        ← 🆕 M-16 — Protocol com delete() obrigatório
│   │   │   ├── audit_reporting.py        ← monta AuditReportData a partir do banco
│   │   │   └── report_generator.py       ← gera o PDF via reportlab
│   │   └── main.py                       ← FastAPI app, CORS, middlewares, routers, lifespan
│   ├── scripts/ (8 arquivos, 1.171 LOC)
│   │   ├── seed_admin.py, seed_catalog.py, seed_dashboard_templates.py
│   │   ├── seed_demo_companies.py, seed_demo_audits.py
│   │   ├── backfill_company_cliente01.py, check_db.py
│   │   └── prune_orphan_uploads.py       ← 🆕 M-16 — varredura de evidências órfãs
│   ├── tests/ (18 arquivos + conftest, 148 funções → 202 casos)
│   ├── uploads/                          ← storage local de evidências
│   ├── docker-compose.yml                ← MySQL 8.4 (só banco, dev)
│   ├── Dockerfile, docker-entrypoint.sh, .dockerignore
│   ├── ruff.toml, pytest.ini, alembic.ini
│   ├── requirements.txt
│   └── README.md                         ← ⚠️ ainda com divergências (ver seção 10)
│
└── frontend/                             ← Next.js 16 (App Router, 7.811 LOC)
    ├── app/
    │   ├── layout.tsx, page.tsx          ← landing; atalhos /private/* só em NODE_ENV=development
    │   ├── globals.css                   ← Tailwind 4 + CSS vars (--color-primary, etc.)
    │   ├── api/
    │   │   ├── auth/{login,logout,register}/route.ts
    │   │   └── admin/
    │   │       ├── audits/[auditId]/report/route.ts        (PDF)
    │   │       └── evidences/[evidenceId]/download/route.ts (arquivo)
    │   ├── public/
    │   │   ├── login/{page.tsx,login-form.tsx}
    │   │   └── cadastro/page.tsx
    │   └── private/
    │       ├── layout.tsx                ← getCurrentUserProfile() + UserMenu
    │       ├── _components/{user-menu.tsx,logout-button.tsx}
    │       ├── admin/
    │       │   ├── page.tsx + admin-dashboard-client.tsx  ← Home enxuta (4 KPIs,
    │       │   │                            fila de sub-usuários, prévia de mensagens,
    │       │   │                            lista rápida de empresas)
    │       │   ├── actions.ts, loading.tsx, error.tsx
    │       │   ├── auditorias/           ← Gestão de Auditorias (status, PDF, conversa)
    │       │   ├── mensagens/            ← Mensagens gerais — visão admin (+ deep-link)
    │       │   ├── templates/            ← editor de templates de dashboard
    │       │   └── empresas/
    │       │       ├── page.tsx, empresas-client.tsx, actions.ts, loading.tsx, error.tsx
    │       │       └── [id]/             ← "Configurações do Cliente"
    │       │           ├── layout.tsx    ← cabeçalho + CompanyTabsNav
    │       │           ├── page.tsx      ← redireciona para ./perfil
    │       │           ├── _components/company-tabs-nav.tsx
    │       │           ├── perfil/       ← dados cadastrais da empresa
    │       │           ├── dashboard/    ← Dashboard & Template (890 LOC — maior do projeto)
    │       │           ├── usuarios/     ← principal + sub-usuários
    │       │           └── auditoria/    ← auditorias da empresa (filtro company_id)
    │       └── client/
    │           ├── page.tsx, client-dashboard-client.tsx, actions.ts
    │           ├── loading.tsx, error.tsx
    │           └── mensagens/
    ├── lib/
    │   ├── session.ts                    ← DAL: getCurrentUser/getCurrentUserProfile/requireX()
    │   ├── server-backend.ts             ← callBackend<T>() — helper genérico de fetch
    │   ├── control-status.ts             ← labels/cores/ordem de status (fonte única)
    │   └── safe-redirect.ts              ← getSafeRedirectPath() (anti open-redirect)
    ├── _components/public-auth-cleanup.tsx
    ├── proxy.ts                          ← substitui middleware.ts (Next.js 16)
    ├── Dockerfile (multi-stage, output standalone), .dockerignore
    ├── next.config.ts, tsconfig.json, eslint.config.mjs, postcss.config.mjs
    ├── package.json                      ← name: "plataforma-auditoria-frontend" ✅ corrigido
    └── .env.local                        (não versionado)
```

### Volumetria de código

| Área | LOC |
|---|---|
| `backend/app/**` | **5.703** |
| `backend/alembic/**` | 1.976 |
| `backend/scripts/**` | 1.171 |
| `backend/tests/**` | 3.270 |
| `frontend/app` + `lib` + `_components` | **7.811** |
| **Total de código de aplicação** | **~13.500** (backend `app/` + frontend) |

**Arquivos acima de 500 LOC** — todos candidatos a decomposição:

| Arquivo | LOC |
|---|---|
| `frontend/app/private/admin/empresas/[id]/dashboard/company-dashboard-client.tsx` | 890 |
| `frontend/app/private/admin/empresas/empresas-client.tsx` | 649 |
| `backend/app/api/v1/dashboard_cards.py` | 610 |
| `frontend/app/private/admin/templates/templates-client.tsx` | 594 |
| `backend/app/services/dashboard_template_admin.py` | 547 |
| `frontend/app/private/client/client-dashboard-client.tsx` | 518 |

---

## 6. Principais Módulos e Funcionalidades

### 6.1 Autenticação e Autorização `🔄 reforçado no BLOCO P.1`

**Tecnologia:** JWT (HS256) access + refresh + bcrypt.
**Papéis:** `admin` (empresa de auditoria) · `user` (cliente principal) · `sub-user` (delegado por um `user`, mesmo acesso via `parent_user_id`).

Login emite `access_token` (`JWT_EXPIRES_MINUTES` — 15 no compose) + `refresh_token` (`JWT_REFRESH_EXPIRES_DAYS`, 7 dias); ambos em cookies `httpOnly` / `sameSite=lax` / `secure` em produção. Registro público existe (`POST /auth/register`) mas fica atrás da flag `ALLOW_PUBLIC_REGISTRATION` (`false` no compose). Rate limiting por IP via `slowapi`: 5/min em `/login`, 10/min em `/refresh`.

A autorização acontece em três degraus independentes:

1. **Papel do endpoint** — `require_admin` / `require_main_user` no `Depends`.
2. **Posse do recurso** — `_resolve_owner_user_id()` / `_get_company_with_access()` resolvem "esta empresa/card/controle pertence a este usuário?".
3. **Política de ação** — `assert_can(Action.X, role)` para escritas cujo direito **não decorre de posse**.

**Limitação conhecida (MVP):** os tokens são stateless, sem blocklist nem tabela de sessões. Um `refresh_token` "rotacionado" continua criptograficamente válido até expirar; logout é client-side (limpeza de cookies).

### 6.2 Onboarding de Clientes (Admin)

`POST /api/v1/onboarding/principal-user` cria, numa única transação: `User` (papel `user`, senha temporária de 12 caracteres), `Company` (1:1), `Dashboard` (1:1) e os `DashboardCard` do template escolhido (ou 0 cards se `manual_dashboard=true`). O e-mail de credenciais é enviado **fora** da transação. Implementado em `admin_onboarding.py` + `services/dashboard_builder.py`; coberto por `tests/test_onboarding.py`.

### 6.3 Auditoria (Controles, Evidências, Encerramento e Relatório)

- `POST /admin/audits` instancia uma auditoria associando um cliente a **todos** os controles do `ControlCatalog` (`AuditRepository.create_with_controls`), com `UniqueConstraint(audit_id, control_id)` garantindo um controle por auditoria.
- `PATCH /admin/audit-controls/{id}/status` — **somente admin**, com os quatro status unificados.
- `POST /client/controls/{id}/evidences` — upload pelo cliente, extensão validada **antes** de ler qualquer byte, leitura com teto de memória (`_read_limited`, B-M22), persistido em `uploads/<uuid><ext>`.
- `GET /admin/evidences/{id}/download` — download autenticado pelo admin, via route handler do Next.js que faz o proxy do binário.
- `PATCH /admin/audits/{id}/status` — encerramento formal (`AuditStatus.CLOSED`).
- `GET /admin/audits/{id}/report.pdf` — `services/audit_reporting.py` monta o `AuditReportData` e `services/report_generator.py` gera o PDF com reportlab.

### 6.4 Dashboard Gerencial (Cards)

Cada empresa tem exatamente um `Dashboard` com N `DashboardCard`. Cada card carrega status, categoria, ordenação, flag `hidden` e o vínculo `origin_template_card_id` com o card de template que o originou. Sob cada card há quatro coleções: notas, itens de checklist, entradas de histórico e mensagens (chat por card).

- `GET /dashboard/status-summary` — os 4 KPIs da Home do admin em **uma única query agrupada**, ignorando cards ocultos.
- `GET /dashboard/companies/{id}/cards` — listagem com busca e `include_hidden`.
- `PATCH /dashboard/cards/{id}/status` — **admin apenas** (B-A23).
- `PATCH /dashboard/checklist-items/{id}/toggle` — **admin apenas** (B-A23).
- `POST /dashboard/cards/{id}/entries` — recusa `CHECKLIST`, `HISTORY` e `CHAT_ANSWER` de papel não-admin; `CHAT_QUESTION` segue livre, por ser o canal legítimo do cliente.
- `PATCH /dashboard/companies/{id}/cards/bulk` — 5 operações em massa (hide/unhide/set_category/remove/restore_from_template).

### 6.5 Templates e Categorias de Dashboard `🔄 integridade fechada em P.3`

`DashboardTemplate` → N `DashboardTemplateCard`; `DashboardCardCategory` é o vocabulário fechado e editável que substituiu a `tag` de texto livre (a `tag` sobrevive como campo histórico sincronizado).

Três invariantes ganharam garantia real no BLOCO P:

| Invariante | Como é garantida hoje |
|---|---|
| Aplicar o mesmo template duas vezes não duplica cards | `UniqueConstraint(dashboard_id, origin_template_card_id)` (migration `b7c02e91d4a5`) — `NULL` não participa da unicidade no MySQL, então cards customizados seguem livres |
| Cards anteriores à entidade "categoria" reconhecem sua origem | Migration `a3d81f4c7b02` faz backfill de `origin_template_card_id` por título não-ambíguo |
| Excluir um template em uso não pode destruir o vínculo em silêncio | `DELETE /admin/templates/{id}` e `DELETE /admin/templates/template-cards/{id}` respondem **409** quando há card em uso |

### 6.6 Mensagens Gerais entre Admin e Cliente

`CompanyMessage` é o canal "solto" — dúvidas que não pertencem a um controle nem a um card. Append-only por design (sem soft delete, sem `updated_at`), com `read_at` para badge de não lidas em `GET /companies/unread-count` e `GET /companies/{id}/messages/unread-count`.

### 6.7 Sub-usuários

`POST /sub-users/requests` (somente usuário principal, via `require_main_user`) → `GET /sub-users/requests/pending` (admin) → `POST /sub-users/requests/{id}/approve` (cria o `User` com `parent_user_id` e envia credenciais) ou `/reject`. `GET /sub-users/requests/me` devolve o histórico do próprio cliente.

### 6.8 Gestão de Empresas e "Configurações do Cliente" (Admin)

`GET/PATCH/DELETE /admin/companies` mais a aba única em `/private/admin/empresas/[id]` — *Perfil · Dashboard & Template · Usuários · Auditoria*.

A **exclusão em cascata** (`services/company_admin.py::delete_company_cascade`) é o fluxo mais delicado do backend e o que mais mudou no BLOCO P. Hoje ele:

1. Coleta os `storage_key` de todas as evidências **antes** da cascata (depois seria tarde: os registros já não existem).
2. Executa a exclusão transacional (usuário principal, sub-usuários, solicitações, auditorias, controles, cards, mensagens).
3. **Só depois do commit** chama `storage.delete_files()`, que recusa qualquer `storage_key` que resolva para fora de `uploads/` e nunca levanta exceção — a transação já está committada e não pode ser desfeita por causa de um arquivo; cada falha vira log estruturado para varredura posterior.
4. Devolve `deleted_evidence_files` no `CompanyDeletionSummary`.

Para os órfãos deixados por exclusões anteriores à correção, existe `scripts/prune_orphan_uploads.py` (relata por padrão; remove com `--apply`).

---

## 7. Fluxo de Funcionamento Completo

### 7.1 Onboarding → Auditoria → Evidência → Relatório

```
ADMIN                          FRONTEND (Next 16)          BACKEND (FastAPI)        MySQL
  │                                  │                            │                   │
  │ 1. Cadastra cliente              │                            │                   │
  ├─────────────────────────────────▶│ Server Action              │                   │
  │                                  ├── POST /onboarding/ ──────▶│                   │
  │                                  │    principal-user          │ TRANSAÇÃO ÚNICA:  │
  │                                  │                            ├─ User (senha tmp)─▶│
  │                                  │                            ├─ Company ────────▶│
  │                                  │                            ├─ Dashboard ──────▶│
  │                                  │                            └─ N DashboardCard ▶│
  │                                  │◀── 201 + senha temporária ─┤ (do template)     │
  │                                  │                            │ e-mail FORA da tx │
  │                                  │                            │                   │
  │ 2. Cria auditoria                │                            │                   │
  ├─────────────────────────────────▶├── POST /admin/audits ─────▶├─ Audit ──────────▶│
  │                                  │                            └─ N AuditControl ─▶│
  │                                  │                              (1 por controle   │
  │                                  │                               do catálogo)     │
CLIENTE                              │                            │                   │
  │ 3. Faz login e vê os controles   │                            │                   │
  ├─────────────────────────────────▶├── GET /client/controls ───▶│◀──── SELECT ──────┤
  │                                  │                            │                   │
  │ 4. Sobe evidência                │                            │                   │
  ├─────────────────────────────────▶├── POST /client/controls/──▶│ valida extensão   │
  │    (PDF/PNG/DOCX…)               │    {id}/evidences          │ lê com teto de mem│
  │                                  │                            │ grava uploads/    │
  │                                  │                            └─ Evidence ───────▶│
  │                                  │                            │                   │
  │ 5. Pergunta no chat do controle  │                            │                   │
  ├─────────────────────────────────▶├── POST …/messages ────────▶├─ Message ────────▶│
ADMIN                                │                            │                   │
  │ 6. Baixa a evidência             │ /api/admin/evidences/[id]/ │                   │
  ├─────────────────────────────────▶├── download (proxy binário)▶│ FileResponse      │
  │                                  │                            │                   │
  │ 7. Classifica o controle         │                            │                   │
  ├─────────────────────────────────▶├── PATCH /admin/audit- ────▶│ require_admin ✋   │
  │    (CONFORME / PARCIAL / …)      │    controls/{id}/status    └─ UPDATE ─────────▶│
  │                                  │                            │                   │
  │ 8. Encerra a auditoria           │                            │                   │
  ├─────────────────────────────────▶├── PATCH /admin/audits/────▶├─ status=CLOSED ──▶│
  │                                  │    {id}/status             │                   │
  │ 9. Exporta o PDF                 │ /api/admin/audits/[id]/    │ audit_reporting + │
  ├─────────────────────────────────▶├── report (proxy binário) ─▶│ report_generator  │
  │◀────────────── PDF ──────────────┤◀───────────────────────────┤ (reportlab)       │
```

### 7.2 Onde cada camada valida

| Camada | O que valida | Falha resulta em |
|---|---|---|
| `proxy.ts` | Existência e assinatura do cookie; papel × prefixo de rota | Redirect (otimista) |
| `lib/session.ts` (DAL) | Assinatura do JWT por requisição, memoizada | `redirect()` para login |
| `deps.py::get_current_user` | Assinatura, `type == access`, usuário existe no banco | 401 |
| `deps.py::require_admin` / `require_main_user` | Papel do chamador | 403 |
| `_get_company_with_access` / `_resolve_owner_user_id` | **Posse** do recurso | 404 (não 403 — não revela existência) |
| `core/policy.py::assert_can` | **Permissão** da ação, independente de posse | 403 |
| Constraints do MySQL | Unicidade e integridade referencial | 409 / erro de integridade |

---

## 8. Banco de Dados

### 8.1 Modelos ORM (9 arquivos, 18 classes, 18 tabelas)

| Arquivo | Classe | Tabela | Papel |
|---|---|---|---|
| `user.py` | `User` | `users` | Papéis `admin`/`user`/`sub-user`; `parent_user_id` auto-referencial |
| `control_catalog.py` | `ControlCatalog` | `control_catalog` | Catálogo mestre de controles (código, título, evidência esperada) |
| `audit.py` | `Audit` | `audits` | Auditoria de um cliente; `DRAFT`/`ACTIVE`/`CLOSED` |
| `audit_control.py` | `AuditControl` | `audit_controls` | Controle instanciado numa auditoria; `UniqueConstraint(audit_id, control_id)` |
| `evidence.py` | `Evidence` | `evidences` | Arquivo anexado a um controle; `storage_key` único |
| `message.py` | `Message` | `messages` | Chat por controle de auditoria, com `read_at` |
| `company_message.py` | `CompanyMessage` | `company_messages` | Canal geral admin↔empresa, append-only, com `read_at` |
| `sub_user_request.py` | `SubUserRequest` | `sub_user_requests` | Fluxo `PENDING`/`APPROVED`/`REJECTED` |
| `company_dashboard.py` | `Company` | `companies` | Empresa cliente, 1:1 com o usuário principal |
| " | `DashboardCardCategory` | `dashboard_card_categories` | Vocabulário fechado de categorias |
| " | `DashboardTemplate` | `dashboard_templates` | Template de dashboard (um pode ser `is_default`) |
| " | `DashboardTemplateCard` | `dashboard_template_cards` | Card modelo dentro de um template |
| " | `Dashboard` | `dashboards` | 1:1 com `Company` |
| " | `DashboardCard` | `dashboard_cards` | Card real; `UniqueConstraint(dashboard_id, origin_template_card_id)` |
| " | `DashboardCardNote` | `dashboard_card_notes` | Nota interna do card |
| " | `DashboardCardchecklistItem` | `dashboard_card_checklist_items` | Item de checklist do card |
| " | `DashboardCardHistoryEntry` | `dashboard_card_history_entries` | Trilha de ações sobre o card |
| " | `DashboardCardMessage` | `dashboard_card_messages` | Chat por card (`QUESTION`/`ANSWER`) |

**Mixins** (`db/mixins.py`): `TimestampMixim` (`created_at`/`updated_at`) e `SoftDeleteMixin` (`deleted_at` + propriedade `is_deleted`), aplicados a `User`, `Audit` e `AuditControl`.

> ⚠️ O nome `TimestampMixim` é um typo de `TimestampMixin`, presente desde o primeiro commit. E o `SoftDeleteMixin` é **declarado mas nunca consultado**: `grep deleted_at` em `backend/app/` fora de `mixins.py` retorna **zero** ocorrências — nenhuma query filtra por ele. Ou o soft delete passa a ser respeitado, ou os mixins deveriam sair.

### 8.2 Enums

| Enum | Valores | Onde |
|---|---|---|
| `AuditStatus` | `DRAFT` · `ACTIVE` · `CLOSED` | `audits.status` |
| `AuditControlStatus` | `EM_ANALISE` · `PARCIAL` · `CONFORME` · `NAOCONFORME` | `audit_controls.status` |
| `DashboardCardStatus` | `EM_ANALISE` · `PARCIAL` · `CONFORME` · `NAOCONFORME` | `dashboard_cards.status` |
| `DashboardMessageType` | `QUESTION` · `ANSWER` | `dashboard_card_messages.message_type` |
| `SubUserRequestStatus` | `PENDING` · `APPROVED` · `REJECTED` | `sub_user_requests.status` |

Os dois enums de status de conformidade são **deliberadamente idênticos** — a unificação foi feita em `bf92636` para que admin e cliente vissem o mesmo vocabulário nos dois domínios. O frontend materializa isso em `lib/control-status.ts` (fonte única de rótulos, cores e ordem).

### 8.3 Histórico de Migrações (Alembic, 19 revisões — head `b7c02e91d4a5`)

| # | Revisão | O quê |
|---|---|---|
| 1 | `86f95e525db1` | Schema v1 — usuários, catálogo, auditorias, controles, evidências, mensagens |
| 2 | `447a4e1de59d` | Fluxo de papel sub-user |
| 3 | `9d5a3c1b2e77` | Tabelas do domínio de dashboard |
| 4 | `d60f999c1fca` | Complemento do fluxo de sub-user |
| 5 | `56d322bbd83a` | Índices de performance |
| 6 | `5e977e8b49da` | Colunas de timestamp e soft delete |
| 7 | `5a9233d65599` | Correção da PK de `dashboard_card_checklist_items` |
| 8 | `d5c4d7cd6687` | Índices de performance (segunda leva) |
| 9 | `5457e7377a56` | Relaxa `companies.phone` e `dashboard_cards.control_code` |
| 10 | `eafa65e9df05` | Restaura índices de `dashboard_cards` |
| 11 | `0ba953b10f8b` | Remove o subsistema de checklist clássico |
| 12 | `83cf1e14efa8` | Corrige typos de nomenclatura em `evidences`/`messages` |
| 13 | `f224a87de1a4` | Corrige `sub_user_requests.request_full_name` |
| 14 | `bf7239a52df8` | Cria `company_messages` |
| 15 | `c2a7e6f1b8d3` | Acrescenta `NAOCONFORME` a `audit_control_status` |
| 16 | `7e3f9c2b5a1d` | `read_at` em mensagens |
| 17 | `4f2b8e6a91d3` | Categoria vira entidade (`dashboard_card_categories`) |
| 18 | `a3d81f4c7b02` | 🆕 **P.3** — backfill de `origin_template_card_id` por título não-ambíguo |
| 19 | `b7c02e91d4a5` | 🆕 **P.3** — `UniqueConstraint(dashboard_id, origin_template_card_id)` |

`alembic heads` confirma **head único** (`b7c02e91d4a5`) — sem branches pendentes. O job `migrations` do CI aplica tudo contra um MySQL 8.4 real, faz `downgrade base`, reaplica e verifica o head único.

### 8.4 Seeds e scripts de manutenção

| Script | Para quê |
|---|---|
| `seed_admin.py` | Cria o usuário administrador a partir de `ADMIN_*` do `.env` |
| `seed_catalog.py` | Popula o `ControlCatalog` mestre |
| `seed_dashboard_templates.py` | Cria os templates e categorias iniciais |
| `seed_demo_companies.py` / `seed_demo_audits.py` | Massa de demonstração |
| `backfill_company_cliente01.py` | Backfill pontual de um cliente legado |
| `check_db.py` | Diagnóstico de conectividade e estado do schema |
| `prune_orphan_uploads.py` | 🆕 Lista (e com `--apply` remove) evidências órfãs em `uploads/` |

---

## 9. Testes Automatizados

**Resultado desta revisão:** `python -m pytest -q` → **250 passed, 0 failed** em 68,6 s, em **24 arquivos**.

O levantamento desta revisão encontrou 202 testes em 18 arquivos; o **BLOCO Q** acrescentou **48**, distribuídos em 6 arquivos novos e uma seção nova na matriz de autorização. Como no BLOCO P, nenhum deles testa funcionalidade — todos testam a **ausência** de uma classe de defeito:

| Arquivo | Testes | Cobre |
|---|---|---|
| `test_storage_path_guard.py` | 12 | Guarda de caminho no ponto único (B-M28) |
| `test_password_limits.py` | 8 | Limite de 72 bytes do bcrypt (B-A27) |
| `test_config_defaults.py` | 8 | Defaults de configuração (B-M25, B-M29) |
| `test_credentials_delivery.py` | 6 | Senha temporária que não se perde (B-A29) |
| `test_email_content.py` | 6 | E-mail por papel (B-M27, B-B22) |
| `test_card_internals_visibility.py` | 5 | Registro interno do auditor (B-A28) |
| `test_authorization_matrix.py` | +2 | Seção de **leitura**, que a matriz não tinha |

| Arquivo | Funções | Cobre |
|---|---|---|
| `test_admin_audit_management.py` | 21 | CRUD de auditoria, status, PDF, mensagens por controle |
| `test_dashboard_cards.py` | 19 | Runtime do dashboard: cards, notas, checklist, histórico, chat, resumo |
| `test_admin_companies.py` | 14 | Listagem, detalhe, atualização e **exclusão em cascata** de empresa |
| `test_company_messages.py` | 10 | Canal geral admin↔cliente e contadores de não lidas |
| `test_auth.py` | 9 | Registro, login, refresh, recusa de token trocado |
| `test_sub_users.py` | 9 | Solicitação, aprovação, recusa, histórico |
| `test_client_audits.py` | 7 | Visão do cliente sobre auditorias e controles |
| `test_client_messages.py` | 7 | Chat por controle no lado do cliente |
| `test_dashboard_categories.py` | 7 | CRUD do vocabulário de categorias |
| `test_dashboard_templates.py` | 7 | CRUD de template, aplicação idempotente, bulk |
| `test_security_headers.py` | 7 | 🆕 **Varre o HTML real de `/docs` e `/redoc`** e afirma que o CSP permite cada origem pedida |
| `test_admin_audits.py` | 6 | Criação de auditoria a partir do catálogo |
| `test_evidence_upload.py` | 6 | Extensão, tamanho, posse, persistência |
| `test_onboarding.py` | 5 | Transação única de onboarding |
| `test_admin_users.py` | 4 | Listagem de usuários por papel |
| `test_authorization_matrix.py` | 4 | 🆕 **Cada endpoint de escrita exercitado por cada papel que NÃO deveria poder executá-lo** |
| `test_migrations_smoke.py` | 4 | 🆕 Importabilidade, nome de arquivo × `revision` declarado, head único |
| `test_dashboard_card_categories_migration.py` | 2 | Backfill de categorias |

**Infraestrutura de teste:** SQLite em memória com `StaticPool`, schema recriado por teste (`Base.metadata.create_all`/`drop_all`), e uma fixture `autouse` que redireciona `uploads/` para `tmp_path` — nenhum teste grava arquivo real no repositório.

**Três observações honestas:**

1. Os três arquivos novos do BLOCO P não testam *funcionalidade* — testam **a ausência de uma classe de defeito**. Essa é a diferença entre corrigir um bug e instalar uma barreira.
2. `test_security_headers.py` existe porque a primeira versão do teste de CSP passava enquanto a página quebrava. O teste certo não pergunta "o header está presente?", e sim "sob este header, os recursos que a página pede continuam permitidos?".
3. **O frontend não tem um único teste.** 7.811 LOC, 15 páginas, 9 grupos de Server Actions, zero cobertura. `tsc --noEmit` e `eslint` passam limpos, mas nenhum dos dois executa lógica.

### Qualidade estática verificada nesta revisão

| Ferramenta | Escopo | Resultado |
|---|---|---|
| `ruff check` | `app scripts tests` | **All checks passed** |
| `tsc --noEmit` | frontend inteiro | **0 erros** |
| `eslint` | frontend inteiro | **0 erros** |
| `alembic heads` | `backend/alembic` | **head único** |

---

## 10. Pontos de Atenção

### 10.1 Resolvido entre 2026-08-24 e 2026-08-26 (BLOCO P + `34f8444`)

| ID | Achado | Como foi fechado | Verificado nesta revisão |
|---|---|---|---|
| 🔴 **B-C23** | Credenciais reais versionadas e publicadas | Valores **rotacionados**; `db_auditoria.sql` removido; `.env.example` com 21 placeholders; gitleaks no pre-commit (raiz) e no CI | ✅ Nenhum valor do `backend/.env` atual aparece em commit algum (`git log --all -S`) |
| 🟠 **B-A23** | Auditado declarava a própria conformidade | `require_admin` em status de card e toggle de checklist; entradas `CHECKLIST`/`HISTORY`/`CHAT_ANSWER` recusadas de não-admin; `core/policy.py` | ✅ `assert_can` importado e usado em `dashboard_cards.py` |
| 🟠 **B-A24** | `apply-template` duplicava o dashboard | Migrations `a3d81f4c7b02` (backfill) + `b7c02e91d4a5` (constraint única) | ✅ `UniqueConstraint` presente no modelo e no head |
| 🟠 **B-A25** | Excluir template em uso destruía o vínculo | `DELETE` de template e de card de template retorna **409** quando há card em uso | ✅ Rota `POST /admin/templates/{id}/cards` restaurada (havia sido sobrescrita) |
| 🟠 **B-A26** | Evidências nunca eram apagadas do disco (LGPD) | `storage.delete_files()` pós-commit, com guarda de path traversal; `StorageBackend` Protocol; `prune_orphan_uploads.py` | ✅ `delete_files` existe e é chamada na cascata |
| 🟡 **B-M21** | CSP/HSTS ausentes | CSP duplo (API × docs) e HSTS sob HTTPS | ✅ 7 headers; `/docs` volta a renderizar |
| 🟡 **B-M15/M18** | `decore_token`, `require_main_user` | Renomeados | ✅ `grep decore_token` → 0 ocorrências |
| 🟢 **B-B09/B10/B11/B15/B16** | Nome do pacote, rota morta `/Monitoring`, atalhos de dev, schema órfão, dependência não declarada | Todos aplicados | ✅ `grep Monitoring` e `grep DashboardCardListItem` → 0; `NODE_ENV === "development"` em `app/page.tsx` |

> **Sobre B-C23:** a rotação fecha o risco **operacional** — as credenciais que estão no histórico já não abrem nada. O que permanece é o histórico em si, publicado em `origin`. Purgá-lo (`git filter-repo` + force-push) é opcional e custoso; a decisão é de política, não de segurança imediata, e deve ser registrada como aceita ou agendada.

### 10.2 Aberto — dívida estrutural

| # | Item | Prioridade | Esforço estimado |
|---|---|---|---|
| 1 | **0% de testes no frontend** (7.811 LOC, 15 páginas, 9 grupos de Server Actions). Justificativa empírica: os defeitos de BLOCO O e P que escaparam da revisão estática apareceram por execução, não por leitura. Entrada sugerida: Vitest + Testing Library nos Server Actions e nos 3 clients maiores. | 🟠 Alta | 2–3 dias |
| ~~2~~ | ~~`ci.yml` nunca executou de verdade~~ ✅ **Resolvido em 2026-08-26.** Executou, **reprovou 3 dos 4 jobs**, e cada reprovação era um defeito real — inclusive a cadeia de `alembic downgrade`, que nunca funcionou. Ver **B-A30/B-A31/B-M30/B-M31** | — | — |
| 3 | **Escala horizontal não funciona.** Evidências em volume local e rate limit em memória de processo — duas réplicas quebram os dois. Exige storage trocável (o `Protocol` já existe) e rate limit em Redis. | 🟡 Média | 2–3 dias |
| 4 | **Sem revogação de token.** Logout é client-side; um `refresh_token` vazado vale 7 dias. Exige blocklist ou tabela de sessões. | 🟡 Média | 1 dia |
| 5 | **`audit_log` append-only inexistente.** RNF-02 pede trilha de auditoria; hoje o histórico vive em `dashboard_card_history_entries`, que agora só o admin escreve — mas ainda é editável por quem tem acesso ao banco. | 🟡 Média | 1–2 dias |
| 6 | **Observabilidade parcial.** structlog + X-Request-ID + `/health` real; sem métricas, tracing ou alarme. | 🟡 Média | 1 dia |

### 10.3 Aberto — dívida pontual

| # | Item | Onde | Prioridade |
|---|---|---|---|
| 7 | Bloco de validação de extensão **duplicado** — o mesmo `if ext not in ALLOWED_EXTENSIONS` aparece duas vezes seguidas | `backend/app/api/v1/client.py:180-194` | 🟢 Baixa |
| 8 | 4 arquivos de frontend acima de 500 LOC (890 / 649 / 594 / 518) | ver seção 5 | 🟡 Média |
| 9 | `SoftDeleteMixin` declarado mas **nunca consultado** — zero queries filtram por `deleted_at` | `backend/app/db/mixins.py` | 🟡 Média |
| 10 | Typo `TimestampMixim` (deveria ser `TimestampMixin`), presente desde o primeiro commit | `backend/app/db/mixins.py` | 🟢 Baixa |
| 11 | `DashboardCard.tag` / `DashboardTemplateCard.tag` coexistem com `category_id`; a remoção exige antes tornar `category_id` NOT NULL | `backend/app/models/company_dashboard.py` | 🟢 Baixa |
| 12 | Divergências entre `backend/README.md` e o código (ver `relatorio_documentacao.md`) | `backend/README.md` (223 linhas) | 🟡 Média |
| 13 | Troca de senha obrigatória no primeiro login não existe — a senha temporária pode viver indefinidamente | `services/users.py` | 🟡 Média |
| 14 | 3 endpoints sem tela consumidora (notas de card, entradas de card, listagem de usuários por papel) | `dashboard_cards.py`, `admin.py` | 🟢 Baixa |
| 15 | `docker build` / `docker run` reais nunca foram validados | `backend/Dockerfile`, `frontend/Dockerfile` | 🟡 Média |
| 16 | `structlog` sem versão fixada em `requirements.txt` — única dependência sem pin nem piso | `backend/requirements.txt` | 🟢 Baixa |

---

## 11. Maturidade Técnica

| Dimensão | Nota | Justificativa |
|---|---|---|
| **Arquitetura** | 9,5/10 | Separação limpa router → service → repository → ORM; política de autorização centralizada; storage atrás de um `Protocol` |
| **Segurança** | 8,5/10 | Autorização por papel explícita e testada, CSP/HSTS, gitleaks, pip-audit, rate limiting, credenciais rotacionadas. Falta revogação de token e trilha append-only |
| **Modelagem de dados** | 9,5/10 | 18 tabelas coerentes, constraints que sustentam invariantes de negócio, 19 migrations com downgrades validados no CI |
| **Cobertura de testes** | 6,5/10 | 202 casos sólidos no backend, incluindo matriz de autorização e smoke de migrations — **zerado no frontend** |
| **Qualidade de código** | 8,5/10 | Lint limpo nos dois lados, tipagem completa; duplicação pontual e arquivos grandes no frontend |
| **Documentação** | 10/10 | 17 documentos em `docs/`, sincronizados por execução real nesta revisão |
| **DevOps** | 8,5/10 | 4 jobs de CI incluindo MySQL real; falta a primeira execução verdadeira e a validação dos builds Docker |
| **Observabilidade** | 5/10 | Logging estruturado e health check; sem métricas, tracing ou alarme |
| **Escalabilidade** | 5/10 | Single-node por construção: uploads locais e rate limit em memória |
| **Média ponderada** | **~8,2/10** | MVP maduro, apto a produção controlada em nó único |

---

## 12. Recomendações Prioritárias

### Alta Prioridade

1. **Abrir um PR real e deixar o `ci.yml` rodar pela primeira vez.** É a recomendação mais barata do documento (1 hora) e a que mais muda a natureza de todas as outras: cinco barreiras foram instaladas no BLOCO P, e nenhuma delas jamais executou no ambiente para o qual foi escrita. Uma barreira não exercitada é uma suposição.
2. **Testes automatizados no frontend.** Vitest + Testing Library, começando pelos 9 grupos de Server Actions e pelos três clients acima de 500 LOC (`company-dashboard-client.tsx`, `templates-client.tsx`, `client-dashboard-client.tsx`). É o único gap que sobrou com justificativa empírica direta.
3. **Decidir e registrar a política sobre o histórico do git** (purgar com `git filter-repo` × aceitar o risco residual). As credenciais já não valem; o que falta é a decisão explícita, para que ela não fique implícita.

### Média Prioridade

4. **Escala horizontal** — implementar o `StorageBackend` para S3/Azure Blob (o `Protocol` já obriga o `delete`) e mover o rate limit para Redis. Enquanto isso não acontece, **não rode o backend com mais de um worker/réplica**.
5. **Revogação de sessão** — blocklist de `jti` ou tabela de sessões, para que logout signifique alguma coisa no servidor.
6. **`audit_log` append-only** — a trilha que RNF-02 pede, separada do histórico de card.
7. **Troca de senha obrigatória no primeiro login.**
8. **Decompor os 4 arquivos de frontend acima de 500 LOC.**
9. **Sincronizar `backend/README.md`** com o código (as divergências estão listadas em `relatorio_documentacao.md`).
10. **Validar `docker build` / `docker run`** dos dois Dockerfiles antes do primeiro deploy.
11. **Decidir o destino do soft delete** — ou as queries passam a respeitar `deleted_at`, ou os mixins saem.

### Baixa Prioridade

12. Remover o bloco duplicado de validação de extensão em `client.py:180-194`.
13. Corrigir o typo `TimestampMixim` → `TimestampMixin` (exige migration? não — é só o nome da classe Python).
14. Planejar a remoção de `tag` agora que `category_id` é a fonte de verdade (exige antes tornar `category_id` NOT NULL).
15. Fixar a versão de `structlog` em `requirements.txt`.
16. Criar UI para os 3 endpoints sem tela, ou removê-los.

---

## 13. Documentos Relacionados

| Documento | Para quê |
|---|---|
| [`index.md`](index.md) | Central de documentação — comece por aqui |
| [`dashboard_projeto.md`](dashboard_projeto.md) | Visão executiva: semáforo por área, riscos, métricas |
| [`relatorio_funcionalidades.md`](relatorio_funcionalidades.md) | Linha do tempo e inventário de funcionalidades |
| [`relatorio_bugs.md`](relatorio_bugs.md) | Achados com localização exata e código de correção |
| [`relatorio_melhorias.md`](relatorio_melhorias.md) | Causas estruturais por trás dos achados |
| [`relatorio_documentacao.md`](relatorio_documentacao.md) | Rastreabilidade requisitos × código |
| [`roadmap.md`](roadmap.md) | Sequenciamento em fases e sprints |
| [`plano_implementacao.md`](plano_implementacao.md) | Passo a passo técnico com código pronto |
| [`setup_completo.md`](setup_completo.md) | Do `git clone` à aplicação rodando |
| [`executar_projeto.md`](executar_projeto.md) | Operação diária: banco, backup, logs, Docker |
| [`deploy_producao.md`](deploy_producao.md) | Deploy em produção |

---

*Relatório gerado em 2026-08-26 (rev. 8.1) a partir de leitura direta do código e verificação por execução — `pytest` (**250 passed**), `ruff` (limpo), `alembic heads` (head único), `tsc --noEmit` (0 erros), `eslint` (0 erros) e enumeração de rotas via `app.openapi()` (64 operações). Nenhum número desta página foi copiado da revisão anterior.*
