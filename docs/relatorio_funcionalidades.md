# Relatório de Funcionalidades — Plataforma de Auditoria

| Campo | Valor |
|---|---|
| **Data da Análise** | 2026-06-24 (criação) · 2026-07-27 (rev. 2.0) · 2026-08-11 (rev. 3.0) · 2026-08-12 (rev. 4.0) · 2026-08-17 (rev. 5.0) · 2026-08-17 (rev. 6.0) · 2026-08-24 (rev. 7.0) · 2026-08-26 (rev. 8.0) · 2026-08-26 (rev. 9.0) · **2026-09-09 (rev. 10.0 — esta revisão)** |
| **Versão** | 10.0 |
| **Branch Analisado** | `feat/dashboard-linhas-modal-e-categorias` (HEAD `2cd57eb`, 7 commits à frente de `main` em `d7c06b3`) |
| **Commits Analisados** | **73 commits** (2026-04-09 → 2026-09-09), confirmado por `git rev-list --count HEAD` |
| **Branches** | `main` · **`feat/dashboard-linhas-modal-e-categorias`** (esta entrega, ainda não mergeada) |
| **Fonte** | `git log`, leitura do código, `pytest -q` (**391 passed**), `npm run test` (**243 passed**), `ruff`/`tsc`/`eslint` limpos, `next build` compilando as 23 rotas |
| **Relatório Base** | `docs/relatorio_geral.md` (rev. 9.0) · `docs/relatorio_bugs.md` (rev. 10.0) |

---

## 1. Resumo Executivo de Funcionalidades

| Categoria | Qtd | Detalhe |
|---|---|---|
| **Concluídas e funcionando** | **90** | F01–F90 (F62–F70 = BLOCO O · F71–F78 = BLOCO P · F79–F83 = BLOCOS R e S · **F84–F90 = BLOCO T**) |
| **Parcialmente implementadas** | 3 | P03 (cadastro público atrás de feature flag — decisão de produto), P04 (conteúdo dos templates vs. ISO 27001 Anexo A), P05 (notificação por e-mail ao mudar status) |
| **Órfãs (código morto, sem consumidor)** | 0 | **3 órfãs fechadas no BLOCO T** (O07, O08, O09) — ver seção 5 |
| **Quebradas** | 0 | Suíte 100% verde: **391 backend + 243 frontend** |
| **Entregues com achado Alta aberto** | **0** | Os 4 achados Alta da rev. 7.0 (B-A23, B-A24, B-A25, B-A26) seguem fechados |
| **Planejadas / não iniciadas** | 7 | N01, N02, N05, N06, N08, N11, N12 |
| **Total mapeado** | **100** | 90 concluídas + 3 parciais + 7 planejadas |

### 1.0 O que mudou desde a rev. 9.0 — BLOCO T

Sete commits numa branch de feature, reorganizando o dashboard da empresa e
fechando o que o quadro Kanban (rev. 9.0) deixou pela metade.

**O achado que define este bloco: três subsistemas estavam prontos no backend
e não tinham consumidor nenhum no frontend.** O pedido original supunha que
Checklist, Histórico e Conversa precisassem ser construídos; a leitura do
código mostrou que existiam desde o BLOCO D.6 — tabelas, endpoints, schemas e
até a renderização. O que faltava era **escrita**: dava para marcar um item de
checklist e nunca criar um; dava para ler a conversa com o cliente e nunca
responder; e o histórico **nunca era gravado por nada** — o que aparecia num
card de demonstração era dado semeado pelo `seed_demo_companies.py`.

| Commit | Natureza |
|---|---|
| `b2c2454` | Quadro em linhas com accordion (F84) |
| `38f8a18` | Modal do card com edição (F85) — primeiro consumidor de `updateCardAction` |
| `cce569c` | Escrita de checklist e conversa (F86) — primeiro consumidor de `POST /cards/{id}/entries` |
| `730ae89` | Histórico automático (F87) — a primeira escrita real em `dashboard_card_history_entries` |
| `41879cc` | Gestão de categorias migra para Templates (F88) |
| `7087d66` | Exclusão de seção e realocação guiada (F89) |
| `2cd57eb` | Datas determinísticas e hidratação (F90) |

**Dois defeitos encontrados durante a implementação, ambos corrigidos aqui:**

| Defeito | Como apareceu | Consequência se não corrigido |
|---|---|---|
| `card.category` obsoleto após atribuir `card.category_id` | Um teste de F87 falhou ao afirmar que trocar categoria gera evento | Trocar a categoria de um card **não apareceria no histórico** — a relação carregada não é reatualizada pela FK |
| Fuso livre em `toLocaleDateString` dentro de `"use client"` | Investigação do erro de hidratação reportado | Divergência servidor/cliente para registro criado entre 00:00 e 03:00 UTC — raro para reproduzir, frequente para acontecer |

**Nenhuma migration.** Todo o esquema necessário já existia. O único endpoint
novo é `DELETE /dashboard/checklist-items/{id}`.

**A suíte cresceu 47%**, de 258+114 para **391+243** casos.

### 1.1 O que mudou desde a rev. 7.0

Três commits, **dois deles com código**:

| Commit | Data | Natureza |
|---|---|---|
| `4fd576f` | 2026-08-25 | **BLOCO P** — o commit de segurança do projeto: 1 Crítico, 4 Altos, 3 Médios e 5 achados Baixos fechados, mais **5 barreiras estruturais** |
| `9e3076f` | 2026-08-25 | Documentação da auditoria adversarial (rev. 8.0) + consolidação dos `Prompt_*.txt` em `INSTRUCTIONS.md` |
| `34f8444` | 2026-08-25 | Correção do CSP — a política uniforme deixava `/docs` e `/redoc` em branco |

**A ressalva mais importante da rev. 7.0 deixou de existir.** Aquela revisão fechou com quatro funcionalidades marcadas como "entregues, porém com achado Alta aberto". As quatro foram corrigidas:

| Achado (rev. 7.0) | Funcionalidade afetada | Como foi fechado |
|---|---|---|
| **B-A23** — cliente declarava a própria conformidade | F37, F38, F39, F40 | `require_admin` em status de card e toggle de checklist; entradas `CHECKLIST`/`HISTORY`/`CHAT_ANSWER` recusadas de não-admin; nova camada `core/policy.py` (**F71**) e matriz de autorização testada (**F72**) |
| **B-A24** — `apply-template` duplicava cards pré-O.3 | **F69** | Migration `a3d81f4c7b02` (backfill de `origin_template_card_id` por título não-ambíguo) + `b7c02e91d4a5` (`UniqueConstraint`) — **F76** |
| **B-A25** — excluir template em uso destruía o vínculo | **F68/F69/F70** | `DELETE` de template e de card de template retorna **409** quando há card em uso — **F76** |
| **B-A26** — evidências sobreviviam à exclusão da empresa | **F58** | `storage.delete_files()` pós-commit com guarda de path traversal (**F73**), `StorageBackend` Protocol (**F74**) e script de varredura de órfãos (**F75**) |

**Oito funcionalidades novas (F71–F78)**, e o que as distingue das anteriores é a natureza: nenhuma delas é uma tela nova. São **garantias** — código cuja finalidade é impedir uma classe de erro de voltar a acontecer.

**A suíte de testes cresceu 58%**, de 128 para **202** casos, e os três arquivos novos não testam funcionalidade: testam a ausência de um defeito.

> ### 📌 Nota sobre o defeito nº 14 (`34f8444`)
>
> O CSP introduzido em P.4.4 tinha teste, o teste passava, e o header estava presente em toda resposta. Mesmo assim `/docs` respondia **200 e renderizava em branco** — o navegador bloqueava o bundle do Swagger, o CSS, o script inline de inicialização e o fetch do `openapi.json`, e nada disso aparecia em log algum do servidor.
>
> O que falhou não foi o código: foi a **pergunta que o teste fazia**. "O header está presente?" passava. "Sob este header, os recursos que a página pede continuam permitidos?" não passava. `tests/test_security_headers.py` (**F78**) agora faz a segunda pergunta: varre o HTML real de `/docs` e `/redoc`, extrai cada origem referenciada e afirma que a diretiva correspondente do CSP a permite. Se o FastAPI trocar de CDN numa atualização, o teste falha em vez de a página parar de renderizar em silêncio.

---

## 2. Linha do Tempo de Evolução

```
2026-04-09 ──────────────────────────────────────────────────────────────
│ 456e10f  first commit — esqueleto FastAPI, config, db session, compose
│ 190045c  Add frontend files as regular directory — Next.js inicial
│
2026-04-28 ──────────────────────────────────────────────────────────────
│ f34c2ad  feat: Criação de funcionalidade Models
│          Audit, AuditControl, ControlCatalog, checklistItem(State),
│          Evidence, Message — ainda sem rotas
│
2026-05-18 ──────────────────────────────────────────────────────────────
│ e9f3c8a  fix(backend): ajuste para executar API
│          Migration consolidada 86f95e525db1; rotas v1 (auth/admin/
│          client/users); core (jwt/security); seeds iniciais
│
2026-05-20 ──────────────────────────────────────────────────────────────
│ f15e294  feat(auth): consolida fluxo de autenticação
│          Design system (globals.css), middleware.ts (versão original),
│          server-backend.ts, rotas proxy de auth/perfil/controles
│
2026-05-21 ──────────────────────────────────────────────────────────────
│ 1fe4a41  feat(backend): fluxo completo de sub-user com aprovação admin
│          SubUserRequest, email_sender.py, deps.require_main_user
│
2026-06-25 ──────────────────────────────────────────────────────────────
│ df83715  feat: documentação técnica, dashboard, onboarding, automações
│          admin_onboarding.py, dashboard_cards.py, company_dashboard.py
│          (9 models novos), 3 migrations novas, seed_dashboard_templates
│
2026-06-26 ──────────────────────────────────────────────────────────────
│ dce4dd3  feat(backend): segurança, upload de evidências, paginação
│          slowapi, SecurityHeadersMiddleware, upload real, chat persistido
│ d0a3266  feat: logging estruturado, repositórios, mixins, admin
│          structlog + RequestIDMiddleware, User/AuditRepository, mixins
│
2026-07-27 ──────────────────────────────────────────────────────────────
│ 8036834  fix(backend): regressões críticas de login, upload, chat, checklist
│ d5c16b5  docs: move @developer/ para docs/ e sincroniza documentação
│
2026-08-04 ──────────────────────────────────────────────────────────────
│ aa9d61b  fix(backend): migration duplicada de índices, upload/paginação
│
2026-08-05 ──────────────────────────────────────────────────────────────
│ 710324a  fix(backend): AuditRepository.create_with_controls, 2 regressões
│ 96f88ce  feat: health check real, mixins ativos, role no middleware
│ 1a69192  docs+fix: reescreve plano de implementação, corrige 4 bugs P0
│ 707e854  feat: implementa JWT refresh token (POST /auth/refresh)
│
2026-08-06 ──────────────────────────────────────────────────────────────
│ 549625d  feat(backend): BLOCO G — suíte de testes automatizados
│
2026-08-07 ──────────────────────────────────────────────────────────────
│ e5de18c  fix(frontend): corrige bugs do BLOCO D
│ 785ef0a  fix(backend): padroniza nomes de campo em SubUserRequest
│
2026-08-10 ──────────────────────────────────────────────────────────────
│ 2964b05  feat(frontend): BLOCO D.6 — Dashboard Admin com dados reais
│ a24bae6  feat(frontend): BLOCO D.7 — Dashboard Cliente com evidência/chat
│ b054c7c  chore(frontend): BLOCO D.8 — remove rotas de API sem consumidor
│ eda82cb  fix(backend): BLOCO B.4 — pendências do chat por controle
│
2026-08-11 ──────────────────────────────────────────────────────────────
│ df7cd65  feat(backend): BLOCO E.2 — mixins em AuditControl
│ 6b4f0a3  docs: revisão e sincronização completa de docs/ (rev. 3.0)
│ 9e14706  docs(plano): verifica BLOCO E.3
│ 2fd729c  feat(backend): E.4-E.9 — 34 → 42 testes
│ 6e02887  feat(infra): BLOCO H (Docker + CI)
│ 8313823  feat(cleanup): I.2, confirma I.1/I.3 — 42 → 43 testes
│
2026-08-12 ──────────────────────────────────────────────────────────────
│ 20efbf9  fix(backend): fecha I.4/I.5/I.7 e E.3 (9/9) — 43 → 55 testes
│ 6595065  fix(backend): sub_user_requests.request_full_name
│ c3d1c6f  docs+fix: K.1 corrigido; L.1 documentada como QUEBRADA
│
2026-08-13 ──────────────────────────────────────────────────────────────
│ d81e980  docs: reverifica L.1 — continua quebrada, regressão em D.7
│ a55f319  fix(fullstack): corrige L.1 (8 bugs backend + 6 frontend)
│          e reverte a regressão em D.7 — 55 → 63 testes
│
2026-08-17 ──────────────────────────────────────────────────────────────
│ 0398570  fix(fullstack): BLOCO L (L.2/L.3/L.4) — 10 bugs reais
│          corrigidos; 63 → 74 testes; BLOCO L 100% concluído
│ bf92636  feat(audit): N.1 — status NAOCONFORME unificado (fecha B-M20)
│          + redesign do cabeçalho privado; 74 → 77 testes
│ 82a46a8  feat(admin): M.1 — CRUD de Empresas + exclusão em cascata
│          transacional; 77 → 89 testes
│ 3ce11a6  feat(admin): N.2 — segmented control + corrige B-B12; 89 testes
│ 04769c7  feat(sub-users): N.3 — empresa no admin + recusa; 89 → 93 testes
│ 73444bd  feat(admin): M.2 — conversa por controle + badges; 93 → 102 testes
│ 94d0223  docs: documenta N.1-N.3 retroativamente, sincroniza docs/ (rev. 6.0)
│
2026-08-24 ──────────────────────────────────────────────────────────────
│ 94873ec  feat(admin): BLOCO O — Home enxuta, Configurações do Cliente,
│          categorias e templates editáveis  ◀── maior entrega de PRODUTO
│          54 arquivos · +15.076 / −834 linhas · 102 → 128 testes
│          · O.1 Home enxuta + GET /dashboard/status-summary + deep-link
│          · O.2 Aba única "Configurações do Cliente" (4 abas) +
│               GET /admin/audits?company_id=
│          · O.3 Categoria como entidade (migration 4f2b8e6a91d3) +
│               hidden + origin_template_card_id
│          · O.4 Editor de templates + apply-template idempotente +
│               edição em massa (bulk)
│          · O.6 12 defeitos corrigidos, encontrados por execução real
│ 66578f0  docs(plano): sincroniza o BLOCO O com o código implementado
│
2026-08-25 ──────────────────────────────────────────────────────────────
│ 4fd576f  fix(security): BLOCO P  ◀── maior entrega de SEGURANÇA
│          128 → 192 testes · 17 → 19 migrations · 2 → 4 jobs de CI
│          · P.1 Autorização: posse ≠ permissão. require_admin em status
│               de card e checklist; core/policy.py como fonte única;
│               tests/test_authorization_matrix.py
│          · P.2 Retenção: storage.delete_files() pós-commit, guarda de
│               path traversal, StorageBackend Protocol,
│               scripts/prune_orphan_uploads.py
│          · P.3 Integridade template↔card: 409 na exclusão em uso,
│               migrations a3d81f4c7b02 (backfill) e b7c02e91d4a5
│               (UniqueConstraint)
│          · P.4 Barreiras: test_migrations_smoke.py, job migrations no
│               CI contra MySQL 8.4 real, gitleaks, pip-audit,
│               .pre-commit-config.yaml movido para a raiz
│          · P.0 Credenciais rotacionadas, db_auditoria.sql removido,
│               .env.example com 21 placeholders
│          · P.7 13 defeitos encontrados na própria verificação do bloco,
│               11 deles pegos pela suíte de testes do BLOCO P
│ 9e3076f  docs: auditoria adversarial rev. 8.0; Prompt_*.txt →
│          INSTRUCTIONS.md
│ 34f8444  fix(api): CSP uniforme deixava o Swagger em branco
│          192 → 202 testes · CSP duplo (API_CSP × DOCS_CSP) +
│          tests/test_security_headers.py (defeito #14)
│
  ESTADO ATUAL (revisão desta análise, 2026-08-26, rev. 8.0) — branch
  fix/audit-repository-refactor-and-regressions, HEAD 34f8444.
  BLOCO P 100% concluído (P.0-P.4 + P.7). Suíte 100% verde
  (202 passed, 0 failed). NENHUM achado Crítico ou Alta ativo.
  Maior gap remanescente: 0% de testes automatizados no frontend
  e ausência de escala horizontal.
```

### Evolução da suíte de testes

```
  34 ─▶ 42 ─▶ 43 ─▶ 55 ─▶ 63 ─▶ 74 ─▶ 77 ─▶ 89 ─▶ 93 ─▶ 102 ─▶ 128 ─▶ 192 ─▶ 202 ─▶ 634
 08-06 08-11 08-11 08-12 08-13 08-17 08-17 08-17 08-17 08-17  08-24  08-25  08-25   09-09
 BLOCO  E.4-  I.2   I.4/  L.1   L.2-  N.1   M.1   N.3   M.2   BLOCO  BLOCO   CSP   BLOCOS
   G    E.9         I.7         L.4                            O      P     (#14)  R–T
                                                             (+26)  (+64)  (+10)  (+432)
```

**Leitura:** o salto de +64 do BLOCO P é o maior salto de um único bloco e não corresponde a funcionalidade nova. São testes de **negativa** — cada papel tentando o que não deveria poder, cada migration verificada quanto a nome × revisão, cada origem do CSP conferida contra o HTML real.

O total de 634 (**391 backend + 243 frontend**) inclui os BLOCOS R e S, que criaram a suíte de frontend do zero, e o BLOCO T. Do T, o arquivo mais denso é `test_dashboard_card_history.py`: metade dos seus casos afirma que uma ação **não** gera evento — status repetido, formulário salvo sem edição, card removido em lote. Um histórico que registra demais esconde o que importa tão bem quanto um histórico vazio, e essa metade da regra não é verificável olhando a tela.

---

## 3. Funcionalidades Concluídas

### 3.1 Infraestrutura e Base

| # | Funcionalidade | Onde | Observação |
|---|---|---|---|
| F01 | Setup do banco MySQL 8.4 via Docker | `backend/docker-compose.yml` | Porta host `3307`, charset `utf8mb4_unicode_ci` |
| F02 | ORM e migrações Alembic | `backend/alembic/` | **19 migrations**, head `b7c02e91d4a5`, cadeia linear verificada |
| F03 | Configuração via variáveis de ambiente | `backend/app/core/config.py` | `pydantic-settings`, `.env`, `AliasChoices` para nomes alternativos |
| F04 | Design system frontend | `frontend/app/globals.css` | CSS vars, Tailwind 4 |
| F05 | Logging estruturado (JSON) | `backend/app/core/logging.py` | `structlog`, nível configurável por `IS_DEBUG` |
| F06 | Request ID por requisição | `backend/app/middleware/request_id.py` | Header `X-Request-ID` + contexto de log |
| F07 | Security headers HTTP | `backend/app/middleware/security_headers.py` | **7 headers** — `nosniff`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`, `Permissions-Policy`, **CSP** e **HSTS** (ver F78) |
| F08 | Health check real | `backend/app/api/health.py` | `GET /health` executa `SELECT 1` no banco |
| F09 | Repository pattern (100% em uso) | `backend/app/repositories/` | `UserRepository`, `AuditRepository`, sem métodos órfãos |

### 3.2 Autenticação e Sessão

| # | Funcionalidade | Onde | Observação |
|---|---|---|---|
| F10 | Login com JWT access token | `auth.py` + `login/route.ts` | `POST /auth/login`, rate limit `5/min` |
| F11 | Refresh token | `core/jwt.py`, `POST /auth/refresh` | 7 dias (`JWT_REFRESH_EXPIRES_DAYS`), rate limit `10/min` |
| F12 | Renovação silenciosa de sessão | `frontend/proxy.ts` | Tenta refresh automaticamente antes de redirecionar a login |
| F13 | Hash seguro de senha | `security.py` | bcrypt com `.encode`/`.decode` explícitos |
| F14 | Logout | `logout/route.ts` + `logout-button.tsx` | Limpa os 2 cookies (`maxAge=0`) e `localStorage` legado, com reload completo |
| F15 | Proteção de rotas privadas | `frontend/proxy.ts` | Substitui `middleware.ts` (renomeação obrigatória no Next.js 16) |
| F16 | Validação de role simétrica | `frontend/proxy.ts` | admin em `/private/client` → redireciona; e vice-versa |
| F17 | DAL de sessão (Server Components) | `frontend/lib/session.ts` | `getCurrentUser`/`getCurrentUserProfile`/`requireAdmin`/`requireClient`, memoizados via `cache()` |
| F18 | Proteção anti open-redirect | `lib/safe-redirect.ts` | `getSafeRedirectPath()` |
| F19 | Limpeza de sessão em rotas públicas | `_components/public-auth-cleanup.tsx` + `proxy.ts` | Limpa cookies ao acessar `/`, `/public/login`, `/public/cadastro` |

### 3.3 Gestão de Usuários

| # | Funcionalidade | Onde | Observação |
|---|---|---|---|
| F20 | Perfil do usuário autenticado | `users.py` (`GET /perfil`) | Usado por `private/layout.tsx` |
| F21 | Criação de usuário | `services/users.py` | Hash de senha + `flush()`, via `UserRepository.create()` |
| F22 | Hierarquia de roles (3 níveis) | `models/user.py` + `deps.py` | admin / user / sub-user |
| F23 | Sub-user: solicitação pelo cliente | `sub_users.py` + `client/actions.ts` | `POST /sub-users/requests`, atrás de `require_main_user` |
| F24 | Sub-user: aprovação pelo admin | `sub_users.py` + `admin/actions.ts` | Lock pessimista (`with_for_update()`), testado contra dupla aprovação |
| F25 | Sub-user: acesso como usuário principal | `client.py`, `dashboard_cards.py` | `_resolve_owner_user_id()` (duplicado nos 2 arquivos — ver `relatorio_melhorias.md`) |

### 3.4 Processo de Auditoria

| # | Funcionalidade | Onde | Observação |
|---|---|---|---|
| F26 | Catálogo de controles | `models/control_catalog.py` + `seed_catalog.py` | Populado via seed; controles do ISO/IEC 27001:2022 Anexo A |
| F27 | Criação de auditoria | `admin.py` + `AuditRepository.create_with_controls` | Instancia 1 `AuditControl` por item do catálogo |
| F28 | Listagem paginada de auditorias | `admin.py` (`GET /audits`) | `PaginatedResponse[AuditOut]` tipado corretamente |
| F29 | Listagem de controles do cliente | `client.py` + `client/page.tsx` | Server Component, dados reais |
| F30 | Upload de evidência (real) | `client.py` + `services/storage.py` | `multipart/form-data`, extensão validada antes de ler bytes, leitura com teto de memória |
| F31 | Chat cliente-auditoria por controle | `client.py` (`GET`/`POST /messages`) | Persistido, listado com dados reais |
| F32 | Checklist por controle (modelo) | `models/checklist.py` | **Removido** em 2026-08-12 (E.10) — substituído por `DashboardCardchecklistItem`, ver seção 5 |

### 3.5 Onboarding e Dashboard Gerencial

| # | Funcionalidade | Onde | Observação |
|---|---|---|---|
| F33 | Onboarding de cliente principal | `admin_onboarding.py` + `admin/actions.ts` | Transação única: User + Company + Dashboard + Cards |
| F34 | Templates de dashboard (modelo) | `models/company_dashboard.py` + `seed_dashboard_templates.py` | `is_default` como fallback quando `template_id` omitido |
| F35 | Dashboard builder (factory) | `services/dashboard_builder.py` | `create_company_dashboard_from_template()` |
| F36 | Listagem de empresas (filtro) | `admin_onboarding.py` | `GET /onboarding/companies` |
| F37 | CRUD de cards do dashboard | `dashboard_cards.py` | Criação, detalhe, atualização de status — **status agora restrito a admin (F71)** |
| F38 | Checklist interno do card | `dashboard_cards.py` (`PATCH /checklist-items/{id}/toggle`) | JOIN de posse + **`require_admin` (F71)** |
| F39 | Histórico de ações por card | `dashboard_cards.py` (`entry_type=HISTORY`) | **Escrita restrita a admin (F71)** |
| F40 | Chat Q&A por card | `dashboard_cards.py` (`CHAT_QUESTION`/`CHAT_ANSWER`) | `CHAT_QUESTION` livre (canal legítimo do cliente); `CHAT_ANSWER` só admin (F71) |
| F41 | Controle de acesso por empresa | `_get_company_with_access` / `_get_card_with_access` | admin vê todas; user/sub-user só a própria |
| F42 | Dashboard Admin com dados reais | `admin-dashboard-client.tsx` + `admin/actions.ts` | Sem mock |
| F43 | Dashboard Cliente com evidência/chat reais | `client-dashboard-client.tsx` + `client/actions.ts` | Sem state local |

### 3.6 Comunicação e Qualidade

| # | Funcionalidade | Onde | Observação |
|---|---|---|---|
| F44 | E-mail de credenciais (onboarding + sub-user) | `services/email_sender.py` | SMTP configurável; fallback log estruturado em dev (sem vazar senha em log) |
| F45 | Suíte de testes automatizados (base) | `backend/tests/` | Ampliada continuamente até **202 casos em 18 arquivos** |
| F46 | Notas internas de card (`DashboardCardNote`) | `dashboard_cards.py` (`POST`/`GET /cards/{id}/notes`) | Restrito a admin — **sem UI própria** |
| F47 | Autor de histórico/chat do card | `dashboard_cards.py::get_card_details` | `actor_user`/`author_user` populados |
| F48 | Testes de `dashboard_cards.py` | `test_dashboard_cards.py` | 8 → 17 (BLOCO O) → **19 funções** |
| F49 | Listagem de usuários por papel (admin) | `admin.py` (`GET /admin/users?role=`) | Usa `UserRepository.list_by_role()` — **sem consumidor no frontend** |
| F50 | Tela "minhas auditorias" (cliente) | `client.py` (`GET /client/audits(/:id)`) | Usa `AuditRepository.get_by_id`/`.list_by_client` |
| F51 | Testes de listagem por papel / minhas auditorias / notas | `test_admin_users.py`, `test_client_audits.py`, `test_onboarding.py` | — |
| F52 | Chat/mensagens gerais entre admin e cliente (L.1) | `company_messages.py` + `admin/mensagens/` + `client/mensagens/` | Canal por empresa; marcação de lido e contagem de não lidas |
| F53 | Encerramento formal de auditoria (L.2) | `admin.py` (`PATCH /admin/audits/{id}/status`) + `admin/auditorias/` | `AuditStatus.CLOSED` com endpoint e UI |
| F54 | Exportação de relatório de auditoria em PDF (L.3) | `admin.py` + `services/audit_reporting.py` + `services/report_generator.py` | `reportlab`; proxy autenticado em `app/api/admin/audits/[auditId]/report/route.ts` |
| F55 | Download de evidência pelo admin (L.4) | `admin.py` + `services/storage.py::get_absolute_path` | Proxy autenticado em `app/api/admin/evidences/[evidenceId]/download/route.ts` |
| F56 | Status `NAOCONFORME` unificado + `PATCH /admin/audit-controls/{id}/status` (N.1) | `admin.py` + `frontend/lib/control-status.ts` | Fonte única de labels/cores nos 3 dashboards; migration `c2a7e6f1b8d3` |
| F57 | Segmented control de status no Dashboard Admin (N.2) | `admin-dashboard-client.tsx` + `control-status.ts` | `CONTROL_STATUS_ORDER`/`controlStatusButtonClass`; atualização otimista |
| F58 | Gestão de Empresas — CRUD + exclusão em cascata (M.1) | `companies.py`/`services/company_admin.py` + `/private/admin/empresas` | Exclusão transacional de usuário, sub-usuários, auditorias, evidências, mensagens e dashboard — **agora inclui os arquivos em disco (F73)** |
| F59 | Recusa de solicitação de sub-usuário + empresa na fila (N.3) | `sub_users.py` (`POST /requests/{id}/reject`) | Mesmo lock de `approve_request`; histórico via `GET /requests/me` |
| F60 | Conversa/dúvidas por controle disponível ao admin (M.2) | `admin.py` (`POST /admin/audit-controls/{id}/messages`, `PATCH .../messages/read`) | Reaproveita `Message`; `read_at` (migration `7e3f9c2b5a1d`) |
| F61 | Badges de mensagens não lidas no menu superior (M.2) | `GET /admin/messages/unread-count` + `GET /companies/unread-count` + `user-menu.tsx` | Polling de 45 s; 2 badges independentes |

### 3.7 BLOCO O — Planta do Dashboard `2026-08-24`

| # | Funcionalidade | Onde | Observação |
|---|---|---|---|
| F62 `O.1` | **KPIs agregados de status em uma query** | `dashboard_cards.py` (`GET /dashboard/status-summary`) + `admin/page.tsx` | `select(status, count(id)).where(hidden == False).group_by(status)`. **Fecha N10.** Substitui a `listAllCardsAction`, que baixava todos os cards de todas as empresas só para somar no navegador |
| F63 `O.1` | **Home enxuta do admin + deep-link de mensagens** | `admin/page.tsx` + `admin-dashboard-client.tsx` | 4 KPIs, fila de sub-usuários pendentes, prévia de mensagens não lidas e lista rápida de empresas. Cada mensagem leva a `/private/admin/mensagens?empresa=<id>&conversa=<id>` |
| F64 `O.2` | **Aba única "Configurações do Cliente"** | `admin/empresas/[id]/` (layout + 4 abas + `company-tabs-nav.tsx`) | *Perfil · Dashboard & Template · Usuários · Auditoria*; a raiz `[id]` redireciona para `./perfil` |
| F65 `O.2` | **Filtro de auditorias por empresa** | `admin.py` (`GET /admin/audits?company_id=`) + aba Auditoria | **Fecha N04.** Resolve os membros da empresa (principal + sub-usuários) via `member_user_ids()` |
| F66 `O.3` | **Categoria de card como entidade + CRUD** | `DashboardCardCategory` + `dashboard_categories.py` (4 endpoints) + migration `4f2b8e6a91d3` | Vocabulário fechado e editável. `DELETE` bloqueia com **409** enquanto houver card usando a categoria. `tag` preservada como campo histórico sincronizado |
| F67 `O.3` | **Cards ocultáveis e rastreáveis até o template** | Colunas `hidden` e `origin_template_card_id` em `dashboard_cards` | `hidden` remove o card da visão e das contagens sem apagá-lo; `origin_template_card_id` sustenta idempotência e detecção de divergência |
| F68 `O.4` | **Editor de templates de dashboard** | `dashboard_templates.py` (8 endpoints) + `services/dashboard_template_admin.py` + `/private/admin/templates` | CRUD completo pela UI. Antes, template só existia via seed |
| F69 `O.4` | **Aplicação idempotente de template + sinalização de card desatualizado** | `POST /dashboard/companies/{id}/apply-template` + `_card_is_outdated` | Segunda chamada não cria nada; nunca sobrescreve card do cliente — apenas sinaliza `is_outdated`. ✅ **A idempotência agora alcança também os cards pré-O.3** (backfill de F76) |
| F70 `O.4` | **Edição em massa de cards** | `PATCH /dashboard/companies/{id}/cards/bulk` | 5 operações: `hide` · `unhide` · `set_category` · `remove` · `restore_from_template`. Filtra por `dashboard_id` — `card_ids` de outra empresa são descartados |

### 3.8 BLOCO P — Segurança, Retenção e Barreiras `🆕 2026-08-25`

> Estas oito não são telas. São **garantias**: código cuja finalidade é impedir que uma classe de erro volte a acontecer. Cada uma nasceu de um achado real da auditoria adversarial e vem pareada com a barreira que a sustenta.

| # | Funcionalidade | Onde | O que garante |
|---|---|---|---|
| F71 `🆕 P.1` | **Camada de política de autorização** | `backend/app/core/policy.py` | Torna explícito o princípio *posse ≠ permissão*. `Action` (13 valores) + `ALLOWED_ROLES` como fonte única de verdade, com `can()` e `assert_can()`. Substitui condições ad-hoc espalhadas por 11 routers — **uma linha nesse mapa é revisável num PR; uma condição escondida num router não é**. Fecha **B-A23** |
| F72 `🆕 P.1` | **Matriz de autorização automatizada** | `backend/tests/test_authorization_matrix.py` | Exercita cada endpoint de escrita com **cada papel que não deveria poder executá-lo**. É o teste que faltava: a suíte anterior confirmava que o admin conseguia, nunca que o cliente não conseguia |
| F73 `🆕 P.2` | **Retenção e exclusão real de arquivo de evidência** | `services/storage.py::delete_files()` + `services/company_admin.py` | Fecha **B-A26** (LGPD). Os `storage_key` são coletados **antes** da cascata; a exclusão em disco acontece **só depois do commit**; qualquer chave que resolva para fora de `uploads/` é recusada; nenhuma falha levanta exceção (a transação já está committada) — cada uma vira log estruturado. `deleted_evidence_files` aparece no `CompanyDeletionSummary` |
| F74 `🆕 P.2` | **Contrato de armazenamento com `delete` obrigatório** | `services/storage_backend.py` (`StorageBackend` Protocol) | A causa estrutural de B-A26 era a ausência de `delete` no módulo de storage. Agora uma implementação nova (S3, Azure Blob) não se completa sem responder "como eu apago?" |
| F75 `🆕 P.2` | **Varredura de evidências órfãs** | `scripts/prune_orphan_uploads.py` | Lista (e com `--apply` remove) arquivos em `uploads/` sem registro correspondente em `evidences.storage_key` — os órfãos deixados por exclusões anteriores à correção |
| F76 `🆕 P.3` | **Integridade do vínculo template ↔ card** | `dashboard_templates.py` + migrations `a3d81f4c7b02` e `b7c02e91d4a5` | Três garantias: (a) `DELETE` de template ou de card de template em uso retorna **409** (fecha **B-A25**); (b) backfill de `origin_template_card_id` por título não-ambíguo alcança os cards pré-O.3 (fecha **B-A24**); (c) `UniqueConstraint(dashboard_id, origin_template_card_id)` move a invariante de idempotência do código para o banco. Restaurada também a rota `POST /admin/templates/{id}/cards`, que havia sido sobrescrita |
| F77 `🆕 P.4` | **Barreiras de integração contínua** | `.github/workflows/ci.yml` + `tests/test_migrations_smoke.py` + `.pre-commit-config.yaml` | De 2 para **4 jobs**: `secrets` (gitleaks sobre todo o histórico) e `migrations` (aplica tudo contra MySQL 8.4 real, faz `downgrade base`, reaplica, confirma head único). Mais `pip-audit` no job backend e `test_migrations_smoke.py` verificando nome de arquivo × `revision` declarado — a divergência que já causou três incidentes. O `.pre-commit-config.yaml` foi movido de `backend/` para a **raiz**, onde o pre-commit de fato o resolve |
| F78 `🆕 #14` | **CSP por rota + HSTS, com teste que olha a página** | `middleware/security_headers.py` + `tests/test_security_headers.py` | `API_CSP` (`default-src 'none'`) nas rotas de dados; `DOCS_CSP` libera exatamente as origens que `/docs` e `/redoc` referenciam, e nada além. HSTS só sob HTTPS. As rotas de documentação são lidas de `app.docs_url`/`app.redoc_url` — se forem desativadas em produção, o middleware acompanha sem edição. O teste varre o HTML real e confere origem por origem |

### 3.9 BLOCO R — Testes de frontend e barreiras de custo `🆕 2026-08-26`

| # | Funcionalidade | Onde | O que garante |
|---|---|---|---|
| F79 `🆕 R.1` | **Suíte de testes do frontend** | `vitest.config.ts` + 12 arquivos de teste | **114 testes** onde havia zero: os 9 grupos de Server Actions, `lib/session.ts`, `lib/safe-redirect.ts` e `proxy.ts`. 81% de statements, **93,5% de funções**. Ambiente padrão `node`, não jsdom — Server Actions e `proxy.ts` são código de servidor, e sob jsdom o `jose` recusa a chave porque o `Uint8Array` é de outro realm. Job `npm run test` no CI |
| F80 `🆕 R.2` | **Orçamento de queries por rota** | `tests/test_query_budget.py` | A suíte tinha 250 testes e **nenhum media custo**. Agora 5 rotas de listagem têm teto, parametrizado por **duas** quantidades — um teto medido com uma quantidade só pode ser satisfeito por acaso. `GET /admin/companies` foi de 7·N+3 para **8 queries constantes** |
| F81 `🆕 R.3` | **Ponto único de checagem de posse** | `app/core/access.py` | De **4 implementações para 1**. O módulo documenta a distinção que o projeto pagou caro para aprender: *posse não é permissão* — quem responde "este recurso é deste usuário?" é este módulo; quem responde "este papel pode executar esta ação?" é `core/policy.py` |

### 3.10 BLOCO S — O CI passa a existir de verdade `🆕 2026-08-26`

| # | Funcionalidade | Onde | O que garante |
|---|---|---|---|
| F82 `🆕 S.3` | **Cadeia de migrations reversível** | 6 migrations + guardas via `information_schema` | O `alembic downgrade` **nunca funcionou** — 6 migrations, 3 causas, mais um `drop_constraint(None, ...)` de 21/05 nunca ajustado. Hoje `upgrade head → downgrade base → upgrade head` está verificado contra MySQL 8.4 real, no CI e localmente. **É o procedimento de emergência para uma migration que dá errado em produção** |
| F83 `🆕 S.2` | **Pipeline de CI executando** | `.github/workflows/ci.yml` | 4 jobs verdes em `main`: `backend` (ruff + pip-audit + pytest), `frontend` (lint + typegen + tsc + vitest + build), `secrets` (gitleaks) e `migrations` (MySQL 8.4 real). Existia desde 2026-08-11 e **nunca havia executado** |

> **Sobre F82 e F83.** Nenhuma das duas é funcionalidade de produto — são a mesma categoria de F71–F78: **garantias**. A diferença é que estas duas só puderam ser escritas depois que a barreira executou. F83 não é "o CI foi configurado" (isso já estava feito havia dois meses e meio); é **"o CI executa e reprova o que deve reprovar"**, que é uma afirmação diferente e só verificável por execução.

---

### 3.11 Quadro Kanban do dashboard da empresa `🆕 2026-08-27`

| Item | Valor |
|---|---|
| **Rotas de admin** | `/private/admin/empresas/[id]/dashboard` · `/private/admin/dashboard-labels` · `/private/admin/templates` |
| **Rota de cliente** | `/private/client/quadro` (somente leitura) |
| **Endpoints** | `GET /dashboard/companies/{id}/board` · `POST /dashboard/companies/{id}/columns` · `PATCH\|DELETE /dashboard/columns/{id}` · `PATCH /dashboard/columns/{id}/move` · `PATCH /dashboard/cards/{id}/move` · `PATCH /dashboard/cards/{id}` · `PUT /dashboard/cards/{id}/labels` · CRUD `/admin/dashboard-labels` · CRUD `/admin/templates/{id}/columns` |
| **Permissões** | `MANAGE_COLUMN`, `MOVE_CARD`, `MANAGE_LABEL` — todas `admin`-only. Leitura do quadro liberada a `admin`, `user` e `sub-user` |

**O que faz.** O dashboard da empresa deixa de ser uma lista agrupada por categoria e
passa a ser um quadro de colunas horizontais. O admin cria, renomeia, reordena e
arquiva colunas; arrasta cards entre e dentro delas; escreve a descrição normativa do
controle; e etiqueta cards por criticidade. O cliente vê o mesmo quadro, na mesma
ordem, em modo leitura.

**O que NÃO faz, e por quê.** Etiqueta não declara conformidade — quem responde "está
conforme?" continua sendo `DashboardCardStatus`, e continua sendo `admin`-only
(B-A23). Colunas do tipo **seção** (`ISO 27001:2022 >>`) são separadores visuais e não
aceitam cards. Excluir uma coluna nunca apaga card: a FK é `SET NULL` e o card cai no
balde "Sem coluna".

---

### 3.12 BLOCO T — Dashboard em linhas, modal do card e vocabulário global `🆕 2026-09-09`

| Item | Valor |
|---|---|
| **Rotas afetadas** | `/private/admin/empresas/[id]/dashboard` · `/private/admin/templates` · `/private/client/quadro` |
| **Endpoint novo** | `DELETE /dashboard/checklist-items/{id}` — único do bloco |
| **Endpoints que ganharam consumidor** | `POST /dashboard/cards/{id}/entries` · `PATCH /dashboard/cards/{id}` · `PATCH\|DELETE /admin/dashboard-categories/{id}` |
| **Permissões novas** | `EDIT_CARD`, `ANSWER_QUESTION` — ambas `admin`-only |
| **Migrations** | **nenhuma** |

| # | Funcionalidade | Onde | O que entrega |
|---|---|---|---|
| F84 `🆕 T.1` | **Quadro em linhas com accordion** | `globals.css` · `_components/board.tsx` · `board-column.tsx` | O quadro girou 90°: cada coluna é uma faixa de largura total, empilhada e **recolhida por padrão**. Com 25 colunas e 215 cards, o layout de colunas de 288 px obrigava varredura horizontal e mantinha todos os cards expostos. O accordion já existia (`collapsedColumns`, `aria-expanded`) e nunca tinha uso real, porque tudo nascia aberto. A rolagem horizontal migrou de `.board-scroller` para `.board-column-body`, mantendo a regra de CA-20 no eixo novo: quem rola é sempre um contêiner interno, nunca o `body` |
| F85 `🆕 T.2` | **Modal de detalhe do card, com edição** | `_components/card-detail-modal.tsx` · `card-edit-form.tsx` | Clique no card abre um diálogo (`role="dialog"`, Esc fecha, foco entra). É **casca** em volta do `CardDetailPanel` existente, não uma segunda implementação — o painel segue compartilhado com `/private/client/quadro`. O botão "Editar" é o **primeiro consumidor de `updateCardAction`**, que existia e era testada desde o quadro Kanban sem nenhum componente chamá-la. `initialCardDetail` deixou de ser pré-carregado nas duas páginas |
| F86 `🆕 T.3` | **Escrita de checklist e conversa** | `admin/actions.ts` · `client/quadro/actions.ts` · `card-detail-panel.tsx` | `POST /cards/{id}/entries` existia desde D.6 e **nunca teve consumidor**. Agora: criar e remover item de checklist, e enviar mensagem na conversa — do lado do auditor (`CHAT_ANSWER`) e do cliente (`CHAT_QUESTION`, que `ASK_QUESTION` já autorizava). O `entry_type` é fixo em cada action, não parâmetro: passá-lo de fora permitiria registrar fala da auditoria como pergunta do cliente. `actor_user`/`author_user` chegavam do backend desde E.7 e eram descartados pelos tipos do frontend — histórico e conversa passam a dizer **o que, quando e quem** |
| F87 `🆕 T.4` | **Histórico automático de movimentações** | `services/dashboard_card_history.py` | **Nada no sistema escrevia em `dashboard_card_history_entries`.** Passam a registrar: criação, status, edição de texto, categoria, coluna, reordenação, etiquetas, ciclo do checklist e ação em lote. Metade do valor está no que **não** registra: status repetido, formulário salvo sem mudança e `remove` em lote (a entrada seria apagada pelo mesmo `CASCADE` que a criou). Trocar de coluna e reordenar dentro dela são eventos distintos — arrastar é a interação mais frequente do quadro, e o mesmo texto tornaria o histórico ilegível |
| F88 `🆕 T.5` | **Gestão de categorias na aba Templates** | `templates/actions.ts` · `templates-client.tsx` | O "+ Nova categoria" vivia embaixo do quadro de **uma** empresa, sugerindo que a categoria pertencia a ela — quando criar uma ali afetava todas as empresas da plataforma. Migrou para Templates com CRUD completo, na mesma estrutura de `dashboard-labels-client.tsx`. Zero linha de backend: o CRUD já existia completo, com 409 `CategoryInUseError`. Exclusão **bloqueada**, não em cascata: a FK é `SET NULL`, e cascata deixaria N cards sem classificação em silêncio |
| F89 `🆕 T.6` | **Excluir seção e realocação guiada de cards** | `_components/delete-column-dialog.tsx` · `board-column.tsx` | A **seção** não tinha ação nenhuma: `board-column.tsx` fazia `return` antecipado e renderizava só o nome, embora o backend aceitasse renomear/mover/arquivar/excluir desde sempre. Ganhou o mesmo menu da faixa, com rótulo acessível de "seção". O `window.confirm` da exclusão de coluna deu lugar a um diálogo que declara a contagem de cards **visíveis** (a mesma que o backend usa para recusar), avisa para onde vão os arquivados, e oferece realocar reaproveitando o `set_column` em lote. A regra não mudou — exclusão bloqueada enquanto houver card visível segue sendo a mais segura das três |
| F90 `🆕 T.7` | **Formatação de data determinística** | `lib/date-format.ts` | Fonte única de data/hora, com o fuso **pinado** em `FUSO_DA_PLATAFORMA`. Fecha um defeito de hidratação real e declara num lugar só a suposição de fuso único que `lang="pt-BR"` e o locale fixo de todas as telas já faziam em silêncio |

**O que este bloco NÃO faz, e por quê.**

- **Renomear item de checklist** não foi implementado. Criar, marcar, desmarcar
  e remover cobrem "atualizar o checklist posteriormente"; renomear entra depois
  sem mexer na arquitetura.
- **Histórico de card removido** não existe. `dashboard_card_history_entries.card_id`
  é `ON DELETE CASCADE`, então a entrada morre com o card. Um histórico que
  sobreviva à remoção teria de viver **fora** do card — outra tabela, outra decisão.
- **Evento agregado de template não é uma linha só.** `card_id` é obrigatório, então
  histórico de quadro seria outra tabela. O que se agrega é a *escrita*: aplicar um
  template de 215 cards custa um `INSERT` em lote, não 215 idas ao banco.
- **Anexo na conversa** segue fora de escopo. A estrutura permite (o `evidence.py`
  existe para auditorias), mas anexo em card seria modelo novo.

> **Validação.** 391 testes de backend e 243 de frontend, `ruff`/`eslint`/`tsc`
> limpos e `next build` compilando as 23 rotas. **Não houve validação em
> navegador com o stack completo rodando** — o arrasto no eixo novo é o ponto
> que mais depende de comportamento real do `dnd-kit` e merece uma passagem
> manual antes do merge.

---

## 4. Funcionalidades Parcialmente Implementadas

### P03 — Cadastro público
- **Backend:** `POST /auth/register` existe e funciona, mas `ALLOW_PUBLIC_REGISTRATION=false` por padrão (`.env.example` e `docker-compose.yml`).
- **Frontend:** `/public/cadastro` completa e funcional, mas inacessível pelo fluxo normal com a flag desligada.
- **Natureza:** decisão de produto, não defeito. Clientes entram por onboarding do admin.

### P04 — Conteúdo dos templates de dashboard vs. ISO 27001 Anexo A
- **Estrutura:** ✅ completa e editável pela UI (F68), com vocabulário de categorias controlado (F66), aplicação idempotente (F69) e integridade garantida no banco (F76).
- **Dados de demonstração:** ✅ `seed_demo_companies.py` / `seed_demo_audits.py` geram 5 empresas fictícias com dashboards, auditorias, evidências em PDF e mensagens.
- **Falta:** o **conteúdo**. Os cards do template padrão ainda não foram auditados item a item contra o Anexo A completo da ISO/IEC 27001:2022. É trabalho de curadoria que o admin já pode fazer sozinho por `/private/admin/templates`.

### P05 — Notificação por e-mail ao mudar status
- **Backend:** `email_sender.py` só envia credenciais (onboarding/sub-user).
- **Falta:** nenhum gatilho de e-mail quando o admin altera o status de `AuditControl`/`DashboardCard`, encerra uma auditoria (L.2), recusa uma solicitação de sub-usuário (N.3) ou envia uma mensagem geral (L.1). Candidato ao próximo ciclo.

---

## 5. Funcionalidades Órfãs — Código Sem Consumidor (histórico, 100% resolvido)

### O01 — ~9 rotas de API do Next.js sem consumidor `✅ Resolvido em 2026-08-11 (I.2)`
A migração para Server Components + Server Actions (BLOCOS D.1–D.7) trocou "Client Component → `/api/...` do Next.js → backend" por "Server Component/Action → `callBackend()` → backend". As ~9 rotas órfãs foram removidas em 2 lotes. Rotas **mantidas** hoje (5, todas com consumidor real): `app/api/auth/{login,logout,register}` + os 2 proxies autenticados de binário do BLOCO L.

### O02 — Subsistema de checklist "clássico" sem API própria `✅ Resolvido em 2026-08-12 (E.10)`
Models, FKs e `UniqueConstraint` existiam e eram populados, mas nenhum endpoint os lia ou escrevia — substituído na prática por `DashboardCardchecklistItem`. Removido por completo. Migration `0ba953b10f8b`.

### O03 — `AuditRepository`/`UserRepository` sem consumidor `✅ Resolvido em 2026-08-12 (E.11)`
Os 4 métodos restantes ganharam consumidor real: `get_current_user()`, `POST /auth/refresh`, `approve_request()` e 2 endpoints novos.

### O04 — `GET /users/admin-only` `✅ Resolvido em 2026-08-11 (E.5)`
Endpoint de exemplo/placeholder, sem consumidor nem propósito em produção — removido.

### O05 — `listAllCardsAction` `✅ Resolvido em 2026-08-24 (O.1)`
Server Action que baixava a lista completa de cards de **todas** as empresas apenas para somar os KPIs no navegador. Substituída por `GET /dashboard/status-summary` (F62).

### O06 — `GET /api/v1/Monitoring` e `DashboardCardListItem` `✅ Resolvido em 2026-08-25 (P.4)` `🆕`
Rota morta sem implementação real (B-B10) e schema Pydantic sem nenhum uso (B-B15), ambos removidos. Verificado nesta revisão: `grep` por qualquer um dos dois em `backend/app/` retorna **zero** ocorrências.

### O07 — `POST /dashboard/cards/{id}/entries` sem consumidor `✅ Resolvido em 2026-09-09 (T.3)` `🆕`
Endpoint completo desde D.6, com os quatro tipos de entrada (`CHECKLIST`,
`HISTORY`, `CHAT_QUESTION`, `CHAT_ANSWER`) e permissão por papel — e **nenhuma
chamada no frontend**. A consequência não era código morto inofensivo: era a
interface saber ler checklist e conversa e não saber escrever em nenhum dos
dois. Fechado por `createCardEntryAction` e `sendCardQuestionAction`.

### O08 — `updateCardAction` sem consumidor `✅ Resolvido em 2026-09-09 (T.2)` `🆕`
Server Action escrita e **testada** (`actions.test.ts:263`) desde o quadro
Kanban, sem nenhum componente chamá-la — não havia onde editar um card na
interface. O teste passando mascarava a lacuna: ele provava que a action
falava certo com o backend, não que alguém falasse com ela. Fechado pelo botão
"Editar" do modal.

### O09 — `Action.WRITE_CARD_HISTORY`, `TOGGLE_CHECKLIST` e `ASK_QUESTION` declaradas e nunca aplicadas `✅ Resolvido em 2026-09-09 (T.4)` `🆕`
As três existiam em `core/policy.py` com papéis declarados em `ALLOWED_ROLES`, e
**nenhum `assert_can` as invocava**. A regra que valia de fato era um
`ADMIN_ONLY_ENTRY_TYPES = frozenset({...})` escrito à mão dentro de
`dashboard_cards.py` — duas fontes de verdade para a mesma pergunta, e a que
valia não era a que se revisa num PR. O `frozenset` foi substituído por
`ENTRY_TYPE_ACTIONS`, mapeando cada tipo à sua `Action`; `ANSWER_QUESTION`
nasceu para fechar o quarto tipo.

> **Padrão comum a O07, O08 e O09, e a lição do BLOCO T:** as três são a mesma
> falha, e nenhuma delas é detectável por teste ou por lint. Cada peça estava
> correta e testada **em isolamento**; o que faltava era alguém chamá-la.
> "Existe e está testado" e "está em uso" são afirmações diferentes, e só a
> segunda entrega valor ao usuário. Vale rodar a varredura de consumidores
> antes de estimar qualquer pedido: neste bloco, três dos sete itens pedidos
> já existiam no backend.

> **Endpoints backend ainda sem UI própria (não são código morto — são API pronta esperando tela):**
> `GET /admin/users?role=` (F49) e `POST`/`GET /dashboard/cards/{id}/notes` (F46). Confirmado por varredura em `frontend/app` e `frontend/lib` nesta revisão.

---

## 6. Funcionalidades Planejadas / Não Iniciadas

| # | Funcionalidade | Evidência do planejamento | Prioridade |
|---|---|---|---|
| N01 | Força de troca de senha no 1º login | Senhas temporárias sem campo `must_change_password` em `User` | Média |
| N02 | Bloqueio de conta por tentativas | Sem `failed_attempts`/`locked_until` em `User` | Média |
| N05 | Rejeição formal de evidência | `AuditControl` sem status "rejeitado"; hoje só o controle muda de status | Média |
| N06 | Notificação por e-mail ao mudar status | Ver P05 | Média |
| N08 | Validação de arquivo por MIME real (magic bytes) | `client.py` valida só a extensão do nome do arquivo | Média |
| N11 | Soft delete funcional (exclusão lógica) | `SoftDeleteMixin` aplicado a `User`/`Audit`/`AuditControl`, mas **zero queries** filtram por `deleted_at` (verificado por `grep` nesta revisão) | Baixa |
| N12 | Testes automatizados no frontend | Nenhum framework de teste configurado em `package.json` | **Alta** |

> **Entregues e removidos desta lista:**
> **N03** (encerramento de auditoria) → L.2/F53 · **N07** (download de evidência) → L.4/F55 · **N09** (relatório PDF) → L.3/F54 · **N04** (filtro de auditorias por cliente) → O.2/F65 · **N10** (KPIs agregados) → O.1/F62.

### 6.1 Lacunas estruturais que não são "funcionalidades", mas bloqueiam produção

| Lacuna | Por quê importa | Esforço |
|---|---|---|
| **Escala horizontal** | Evidências em volume local (F73 apaga do disco local) e rate limit em memória de processo. Duas réplicas quebram os dois. O `StorageBackend` Protocol (F74) já é o ponto de extensão — falta a implementação S3/Azure e o rate limit em Redis | 2–3 dias |
| **Revogação de sessão** | Tokens stateless sem blocklist: logout é client-side e um `refresh_token` vazado vale 7 dias | 1 dia |
| **`audit_log` append-only** | RNF-02 pede trilha de auditoria. O histórico de card agora só o admin escreve (F71), mas continua editável por quem tem acesso ao banco | 1–2 dias |
| **Primeira execução real do CI** | As 4 barreiras de F77 nunca rodaram no ambiente para o qual foram escritas | 1 h |

---

## 7. Matriz de Status por Módulo

```
MÓDULO                              BACKEND  BANCO  FRONTEND  INTEGRADO  TESTADO
────────────────────────────────────────────────────────────────────────────────
Autenticação (login/refresh)          ✅      ✅      ✅        ✅         ✅
Proteção de rotas (proxy.ts)          ✅       —      ✅        ✅         ⚠️ manual
Política de autorização 🆕             ✅       —       —         ✅         ✅
Perfil do usuário                     ✅      ✅      ✅        ✅         ✅
Onboarding de cliente                 ✅      ✅      ✅        ✅         ✅
Sub-user flow (solicita/aprova/recusa) ✅     ✅      ✅        ✅         ✅
Criação/listagem de auditoria         ✅      ✅      ✅        ✅         ✅
Filtro de auditoria por empresa       ✅      ✅      ✅        ✅         ✅
"Minhas auditorias" (cliente)         ✅      ✅      ✅        ✅         ✅
Lista de controles (cliente)          ✅      ✅      ✅        ✅         ⚠️ parcial
Upload de evidências                  ✅      ✅      ✅        ✅         ✅
Download de evidências (admin)        ✅       —      ✅        ✅         ✅
Retenção/exclusão de evidência 🆕      ✅      ✅       —         ✅         ✅
Chat por controle (cliente + admin)   ✅      ✅      ✅        ✅         ✅
Chat geral admin↔cliente              ✅      ✅      ✅        ✅         ✅
Deep-link de mensagem não lida         —       —      ✅        ✅         ❌ (frontend)
Status de card (admin apenas) 🔄       ✅      ✅      ✅        ✅         ✅
Checklist do card (admin apenas) 🔄    ✅      ✅      ✅        ✅         ✅
Histórico do card (com autor)         ✅      ✅      ✅        ✅         ✅
Chat do card (com autor)              ✅      ✅      ✅        ✅         ✅
Notas internas do card                ✅      ✅      ❌ sem UI  ⚠️         ✅ (backend)
KPIs agregados de status              ✅      ✅      ✅        ✅         ✅
Dashboard admin (dados reais)         ✅      ✅      ✅        ✅         ❌ (frontend)
Gestão de empresas (CRUD + cascata)   ✅      ✅      ✅        ✅         ✅
Configurações do Cliente (4 abas)     ✅      ✅      ✅        ✅         ⚠️ backend só
Categorias de card (CRUD)             ✅      ✅      ✅        ✅         ✅
Templates de dashboard (CRUD)         ✅      ✅      ✅        ✅         ✅
Aplicar template (idempotente) 🔄      ✅      ✅      ✅        ✅         ✅
Integridade template↔card 🆕           ✅      ✅       —         ✅         ✅
Edição em massa de cards              ✅      ✅      ✅        ✅         ✅
Listagem de usuários por papel        ✅      ✅      ❌ sem UI  ⚠️         ✅ (backend)
Cadastro público                      ✅      ✅      ✅        ⚠️ flag off ✅
Encerramento de auditoria             ✅      ✅      ✅        ✅         ✅
Exportação/relatório PDF              ✅       —      ✅        ✅         ✅
Cabeçalhos de segurança (CSP/HSTS) 🆕  ✅       —       —         ✅         ✅
Barreiras de CI (4 jobs) 🔄            ✅       —      ✅        ✅         ✅ 4 verdes
Cadeia de migrations reversível 🆕     ✅      ✅       —         ✅         ✅
Testes automatizados backend          ✅ 258/258 —    n/a       n/a        n/a
Testes automatizados frontend 🆕       n/a      —      ✅ 114/114 ✅         ✅

LEGENDA: ✅ Implementado e funcional | ⚠️ Parcial/sem teste | ❌ Não implementado
         🆕 novo nesta revisão | 🔄 alterado nesta revisão
```

---

## 8. Dependências entre Funcionalidades

```
Testes automatizados no frontend (N12)          ◀── maior gap remanescente
  └── Pode ser iniciado a qualquer momento
  └── Desbloqueia: confiança para refatorar os 4 arquivos > 500 LOC
      (company-dashboard-client.tsx 890, empresas-client.tsx 649,
       templates-client.tsx 594, client-dashboard-client.tsx 518)
  └── Justificativa empírica: 5 dos 12 defeitos do BLOCO O eram de
      frontend e só apareceram por execução manual

Primeira execução real do ci.yml (F77)
  └── Não depende de nada — abrir um PR basta
  └── Desbloqueia: confiança em TODAS as demais barreiras do BLOCO P
  └── Enquanto não acontecer, as 4 barreiras são suposições verificadas
      apenas estaticamente

Escala horizontal (storage remoto + rate limit em Redis)
  └── Depende de: implementar StorageBackend (F74) para S3/Azure
  └── O Protocol já força a implementação de delete() — a lacuna que
      causou B-A26 não pode se repetir num backend novo
  └── Bloqueia: qualquer deploy com mais de uma réplica

Remoção de DashboardCard.tag / DashboardTemplateCard.tag
  └── Depende de: category_id preenchido em 100% das linhas
      (backfill de 4f2b8e6a91d3 garante isso)
  └── Exige: migration tornando category_id NOT NULL, depois DROP da tag
  └── Bloqueado por: nada técnico — é decisão de quando pagar a dívida

audit_log append-only (RNF-02)
  └── Parcialmente mitigado por F71: só o admin escreve no histórico
  └── Falta: tabela separada, sem UPDATE/DELETE, com o evento completo
  └── Depende de: decisão sobre retenção e volume

Curadoria do template padrão vs. ISO 27001 Anexo A (P04)
  └── Desbloqueada pelo BLOCO O: a ferramenta de edição existe (F68)
  └── Reforçada pelo BLOCO P: aplicar um template a uma empresa
      existente agora é seguro e idempotente (F76)
  └── Depende de: trabalho de conteúdo, não de código

Notificação por e-mail em mudança de status (N06 / P05)
  └── Gatilhos candidatos já existem: PATCH de status de controle e de
      card, encerramento de auditoria, recusa de sub-usuário, nova
      mensagem geral
  └── Depende de: decisão de produto sobre quais eventos notificam

Soft delete funcional (N11)
  └── Mixins já aplicados a User/Audit/AuditControl — e nunca consultados
  └── Tensão a resolver: M.1 entregou exclusão de empresa em cascata
      FÍSICA e transacional, e o BLOCO P a estendeu ao disco (F73).
      Adotar soft delete exigiria revisitar as duas — e decidir o que
      acontece com o ARQUIVO de uma evidência logicamente excluída
```

---

## 9. Próximos Passos Recomendados

### Alta Prioridade

1. **Abrir um PR real e deixar o `ci.yml` rodar pela primeira vez.** Uma hora de trabalho que muda a natureza de todas as outras recomendações: cinco barreiras foram instaladas no BLOCO P e nenhuma jamais executou no ambiente para o qual foi escrita.
2. **Testes automatizados no frontend (N12).** Maior gap de qualidade do projeto. Entrada sugerida: Vitest + Testing Library nos 9 grupos de Server Actions e nos 4 componentes acima de 500 LOC.
3. **Registrar a decisão sobre o histórico do git.** As credenciais foram rotacionadas (verificado: nenhum valor do `.env` atual aparece em commit algum), então o risco operacional está fechado. O que falta é decidir explicitamente entre purgar o histórico (`git filter-repo` + force-push) e aceitar o risco residual — para que a decisão não fique implícita.

### Média Prioridade

4. **Escala horizontal** — implementar `StorageBackend` para S3/Azure Blob e mover o rate limit para Redis. Até lá, **não rode o backend com mais de um worker/réplica**.
5. **Revogação de sessão** — blocklist de `jti` ou tabela de sessões.
6. **`audit_log` append-only** (RNF-02), separado do histórico de card.
7. **Força de troca de senha no 1º login (N01)** — hoje a senha temporária do onboarding pode viver indefinidamente.
8. **UI para os 2 endpoints sem tela:** `GET /admin/users?role=` (F49) e notas de card (F46).
9. **Curadoria do template padrão** contra o Anexo A da ISO 27001 (P04) — a ferramenta existe, falta o conteúdo.
10. **Decompor os 4 arquivos de frontend acima de 500 LOC.**

### Baixa Prioridade

11. Notificação por e-mail em mudança de status (N06/P05) e rejeição formal de evidência (N05).
12. Bloqueio de conta por tentativas (N02); validação de arquivo por MIME real (N08).
13. Planejar a remoção de `tag` agora que `category_id` é a fonte de verdade.
14. Decidir o destino do soft delete (N11) — hoje os mixins existem sem uso algum.
15. Remover o bloco duplicado de validação de extensão em `client.py:180-194`.
16. Cadastro público (P03) segue atrás de feature flag — decisão de produto, não defeito.

---

*Relatório gerado em 2026-08-26 (rev. 8.0) a partir de `git log` (50 commits), leitura direta do código em `34f8444` e execução real da suíte (`202 passed, 0 failed`). Referência cruzada: `docs/relatorio_geral.md` (rev. 8.0), `docs/relatorio_bugs.md`, `docs/plano_implementacao.md` (BLOCOS O e P).*
