# Relatório de Commits — Plataforma de Auditoria ISO 27001

> Arquivo gerado e mantido automaticamente pelo GitHub Actions.
> Atualizado a cada push na branch `main`.
> **Não edite manualmente** — suas alterações serão sobrescritas pelo próximo push.
> Para detalhes da automação, consulte `docs/automacao_commits.md`.

---

<!-- ENTRIES GERADOS AUTOMATICAMENTE ABAIXO -->

---

## Commit `03c0fba` — 2026-09-08 20:43:44

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `main` |
| **Tipo** | 🐛 Correção de Bug (`fix`) |
| **Hash Completo** | `03c0fbac40d804d16bd2826a164963e153450635` |
| **Arquivos Alterados** | 4 arquivo(s) |
| **Linhas** | +25 / −22 |

### Título do Commit

```
fix(ci): corrige os 2 defeitos que o CI da main revelou no merge do Kanban
```

### Descrição

O merge 79a0983 reprovou em `frontend` e `migrations`. Nenhum dos dois
aparecia localmente: um só existe sob `npm ci`, o outro só contra MySQL.

## `frontend` — `npm ci` não resolvia as dependências

`251f9e1` subiu `vitest` e `@vitest/coverage-v8` de `^2.1.9` para `^5.0.0`
sem mexer em duas coisas que esse salto arrasta junto:

- `vitest@5` declara `engines: node ^22.12.0 || ^24.0.0 || >=26.0.0`, e o
  job rodava `node-version: "20"` — versão que o vitest 5 não suporta.
- `vitest@5` pede `peerOptional @types/node@"^22.0.0 || >=24.0.0"`, e o
  projeto continuava em `@types/node@^20`. Daí o `ERESOLVE` que derrubava
  o job em 9 segundos, antes de lint, tipos, testes ou build.

Passou despercebido porque `npm ci` instala do zero e valida peers; a
máquina de desenvolvimento já tinha `node_modules` resolvido de antes e
roda Node 24, então lint/tsc/vitest/build ficavam todos verdes.

Correção: `node-version: "24"` no job e `@types/node` para `^24` (a mesma
major do Node da máquina de desenvolvimento), com o `package-lock.json`
regenerado. Verificado com `npm ci` de verdade, seguido de `npm run lint`,
`tsc --noEmit`, `vitest` (182 testes) e `npm run build` — todos limpos.

## `migrations` — o downgrade de `c8f1a3e57b90` batia no B-A30 de novo

    (1553, "Cannot drop index
     'ix_dashboard_columns_origin_template_column_id':
     needed in a foreign key constraint")

O `downgrade()` já aplicava a ordem "constraint → índice → coluna" em
`dashboard_cards` e `dashboard_template_cards`, que sobrevivem ao
downgrade. Mas em `dashboard_columns` e `dashboard_template_columns`, que
são derrubadas inteiras, ele removia os índices antes do `DROP TABLE` — e
`dashboard_columns` tem FK viva para `dashboards` e para
`dashboard_template_columns`, cujos índices o MySQL se recusa a soltar.

Correção: os `drop_index` dessas duas tabelas saem. `DROP TABLE` já leva
junto os índices da tabela, e a ordem entre as tabelas (quem referencia cai
antes de quem é referenciado) continua preservada. O motivo está comentado
no próprio `downgrade()`, ao lado da regra que ele parecia contradizer.

Não dá para validar este lado localmente: a máquina de desenvolvimento não
tem MySQL. Quem valida é o job `migrations`, que reverte até `base` e
reaplica.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>

### Arquivos Modificados (4 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `.github/workflows/ci.yml` | CI/CD e Automação |
| Modificado | `backend/alembic/versions/c8f1a3e57b90_add_dashboard_columns_and_labels.py` | Banco de Dados / Migrações |
| Modificado | `frontend/package-lock.json` | Outro / Não Categorizado |
| Modificado | `frontend/package.json` | Dependências Node.js |

### Funcionalidades Impactadas

- Banco de Dados / Migrações
- CI/CD e Automação
- Dependências Node.js
- Outro / Não Categorizado

### Correções Realizadas

- Referências detectadas: **B-A30**
  - Consulte `docs/relatorio_bugs.md` para o detalhamento de cada item.

### Verificações Recomendadas

- ⚠️ **Migration alterada.** A suíte usa `Base.metadata.create_all` e **não** executa migrations (ver M-18 em `docs/relatorio_melhorias.md`) — uma suíte verde não prova que a migration roda. Execute `alembic upgrade head` contra o MySQL real e confirme `alembic heads` com um único head.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Verificar se o mesmo bug ocorre em contextos similares no código.
- Adicionar teste de regressão para garantir que o problema não retorne.
- Atualizar `docs/relatorio_bugs.md` marcando o achado como corrigido.

---

## Commit `79a0983` — 2026-09-08 20:34:33

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `main` |
| **Tipo** | 📌 Alteração Geral (`other`) |
| **Hash Completo** | `79a09834cc80dd32f96615f83c7593ac707a4d72` |
| **Arquivos Alterados** | 72 arquivo(s) |
| **Linhas** | +11275 / −1823 |

### Título do Commit

```
Merge branch 'feat/quadro-kanban-colunas-e-cards' — Quadro Kanban completo
```

### Descrição

Traz para a main a Sprint A6 inteira, em dois commits:

- 251f9e1 feat: implementa quadro kanban, colunas, cards e etiquetas
  Migration c8f1a3e57b90, DashboardColumn com position fracionária,
  DashboardLabel, quadro arrastável do admin, quadro do cliente em
  leitura, tela de etiquetas e as permissões MANAGE_COLUMN / MOVE_CARD /
  MANAGE_LABEL.

- d09a3c7 fix(kanban): corrige 8 defeitos do quadro, conclui a Fase 10 e
  importa o Trello
  Campos trocados em BoardColumnOut, três rotas com path digitado errado,
  duas chamadas de função com argumentos errados, o AttributeError na
  exclusão de empresa, as colunas de template (Fase 10) no frontend e o
  importador do export do Trello.

Verificação: tsc, eslint, build e vitest (182 testes) limpos; ruff limpo;
alembic com um único head. A suíte pytest roda no CI (Python 3.12) — o
ambiente local, em Python 3.14, não importa o app por incompatibilidade
com FastAPI 0.115.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>

### Arquivos Modificados (72 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `backend/alembic/env.py` | Banco de Dados / Migrações |
| Adicionado | `backend/alembic/versions/c8f1a3e57b90_add_dashboard_columns_and_labels.py` | Banco de Dados / Migrações |
| Modificado | `backend/app/api/v1/companies.py` | Gestão de Empresas (Admin) |
| Adicionado | `backend/app/api/v1/dashboard_board.py` | Outro / Não Categorizado |
| Modificado | `backend/app/api/v1/dashboard_cards.py` | Dashboard Gerencial / Cards |
| Adicionado | `backend/app/api/v1/dashboard_labels.py` | Outro / Não Categorizado |
| Modificado | `backend/app/api/v1/dashboard_templates.py` | Templates de Dashboard |
| Modificado | `backend/app/api/v1/router.py` | Roteamento da API |
| Modificado | `backend/app/core/access.py` | Configuração e Segurança |
| Modificado | `backend/app/core/policy.py` | Configuração e Segurança |
| Modificado | `backend/app/models/__init__.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/company_dashboard.py` | Modelos de Dados (ORM) |
| Adicionado | `backend/app/models/dashboard_board.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/schemas/company_admin.py` | Schemas / Validação de Dados |
| Adicionado | `backend/app/schemas/dashboard_board.py` | Schemas / Validação de Dados |
| Adicionado | `backend/app/schemas/dashboard_labels.py` | Schemas / Validação de Dados |
| Modificado | `backend/app/schemas/dashboard_runtime.py` | Schemas / Validação de Dados |
| Modificado | `backend/app/schemas/dashboard_templates.py` | Schemas / Validação de Dados |
| Modificado | `backend/app/services/company_admin.py` | Serviços / Lógica de Negócio |
| Adicionado | `backend/app/services/dashboard_board.py` | Serviços / Lógica de Negócio |
| Modificado | `backend/app/services/dashboard_builder.py` | Serviços / Lógica de Negócio |
| Modificado | `backend/app/services/dashboard_template_admin.py` | Serviços / Lógica de Negócio |
| Adicionado | `backend/app/services/fractional_index.py` | Serviços / Lógica de Negócio |
| Adicionado | `backend/scripts/import_trello_board.py` | Scripts de Inicialização / Seeds |
| Modificado | `backend/scripts/seed_dashboard_templates.py` | Scripts de Inicialização / Seeds |
| Modificado | `backend/tests/conftest.py` | Testes Automatizados (pytest) |
| Modificado | `backend/tests/test_authorization_matrix.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_dashboard_board.py` | Testes Automatizados (pytest) |
| Modificado | `backend/tests/test_dashboard_cards.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_dashboard_labels.py` | Testes Automatizados (pytest) |
| Modificado | `backend/tests/test_dashboard_templates.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_fractional_index.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_migration_board_backfill.py` | Testes Automatizados (pytest) |
| Modificado | `backend/tests/test_query_budget.py` | Testes Automatizados (pytest) |
| Modificado | `docs/backlog.md` | Documentação Técnica |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |
| Modificado | `docs/relatorio_funcionalidades.md` | Documentação Técnica |
| Modificado | `docs/roadmap.md` | Documentação Técnica |
| Modificado | `frontend/app/globals.css` | Design System (Frontend) |
| Modificado | `frontend/app/page.tsx` | Homepage / Página Inicial |
| Modificado | `frontend/app/private/admin/actions.ts` | Home do Admin (Frontend) |
| Adicionado | `frontend/app/private/admin/dashboard-labels/actions.test.ts` | Home do Admin (Frontend) |
| Adicionado | `frontend/app/private/admin/dashboard-labels/actions.ts` | Home do Admin (Frontend) |
| Adicionado | `frontend/app/private/admin/dashboard-labels/dashboard-labels-client.tsx` | Home do Admin (Frontend) |
| Adicionado | `frontend/app/private/admin/dashboard-labels/error.tsx` | Home do Admin (Frontend) |
| Adicionado | `frontend/app/private/admin/dashboard-labels/loading.tsx` | Home do Admin (Frontend) |
| Adicionado | `frontend/app/private/admin/dashboard-labels/page.tsx` | Home do Admin (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/dashboard/_components/board-card.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/dashboard/_components/board-column.test.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/dashboard/_components/board-column.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/dashboard/_components/board.test.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/dashboard/_components/board.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/dashboard/_components/card-detail-panel.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/dashboard/_components/move-card-menu.test.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/dashboard/_components/move-card-menu.tsx` | Gestão de Empresas (Frontend) |
| Modificado | `frontend/app/private/admin/empresas/[id]/dashboard/actions.test.ts` | Gestão de Empresas (Frontend) |
| Modificado | `frontend/app/private/admin/empresas/[id]/dashboard/actions.ts` | Gestão de Empresas (Frontend) |
| Modificado | `frontend/app/private/admin/empresas/[id]/dashboard/company-dashboard-client.tsx` | Gestão de Empresas (Frontend) |
| Modificado | `frontend/app/private/admin/empresas/[id]/dashboard/page.tsx` | Gestão de Empresas (Frontend) |
| Modificado | `frontend/app/private/admin/templates/actions.test.ts` | Editor de Templates (Frontend) |
| Modificado | `frontend/app/private/admin/templates/actions.ts` | Editor de Templates (Frontend) |
| Modificado | `frontend/app/private/admin/templates/templates-client.tsx` | Editor de Templates (Frontend) |
| Adicionado | `frontend/app/private/client/quadro/actions.test.ts` | Dashboard Cliente (Frontend) |
| Adicionado | `frontend/app/private/client/quadro/actions.ts` | Dashboard Cliente (Frontend) |
| Adicionado | `frontend/app/private/client/quadro/client-board-client.tsx` | Dashboard Cliente (Frontend) |
| Adicionado | `frontend/app/private/client/quadro/error.tsx` | Dashboard Cliente (Frontend) |
| Adicionado | `frontend/app/private/client/quadro/loading.tsx` | Dashboard Cliente (Frontend) |
| Adicionado | `frontend/app/private/client/quadro/page.tsx` | Dashboard Cliente (Frontend) |
| Adicionado | `frontend/lib/board-labels.test.ts` | Utilitários do Frontend |
| Adicionado | `frontend/lib/board-labels.ts` | Utilitários do Frontend |
| Modificado | `frontend/package-lock.json` | Outro / Não Categorizado |
| Modificado | `frontend/package.json` | Dependências Node.js |

### Funcionalidades Impactadas

- Banco de Dados / Migrações
- Configuração e Segurança
- Dashboard Cliente (Frontend)
- Dashboard Gerencial / Cards
- Dependências Node.js
- Design System (Frontend)
- Documentação Técnica
- Editor de Templates (Frontend)
- Gestão de Empresas (Admin)
- Gestão de Empresas (Frontend)
- Home do Admin (Frontend)
- Homepage / Página Inicial
- Modelos de Dados (ORM)
- Outro / Não Categorizado
- Roteamento da API
- Schemas / Validação de Dados
- Scripts de Inicialização / Seeds
- Serviços / Lógica de Negócio
- Templates de Dashboard
- Testes Automatizados (pytest)
- Utilitários do Frontend

### Correções Realizadas

- Nenhuma referência a achado (`B-X00` / `RD-00`) identificada neste commit.

### Verificações Recomendadas

- ⚠️ **Migration alterada.** A suíte usa `Base.metadata.create_all` e **não** executa migrations (ver M-18 em `docs/relatorio_melhorias.md`) — uma suíte verde não prova que a migration roda. Execute `alembic upgrade head` contra o MySQL real e confirme `alembic heads` com um único head.
- ⚠️ **Endpoint alterado.** Confirme a dependência de autorização: posse (`_get_*_with_access`) não é permissão. Ver **B-A23** em `docs/relatorio_bugs.md`.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Revisar os arquivos modificados em contexto com `docs/relatorio_bugs.md`.
- Consultar `docs/roadmap.md` para verificar alinhamento com o plano.

---

## Commit `b0d26bb` — 2026-08-27 16:36:29

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `main` |
| **Tipo** | 📝 Documentação (`docs`) |
| **Hash Completo** | `b0d26bb38ef5159381d71c9c200691bf79ed99a6` |
| **Arquivos Alterados** | 5 arquivo(s) |
| **Linhas** | +17920 / −0 |

### Título do Commit

```
docs(kanban): PRD, Spec e guia de implementacao do Quadro Kanban + CA-30 no .gitignore
```

### Descrição

Acrescenta a trilha completa de documentacao da proxima entrega — o quadro de
colunas e cards arrastaveis (estilo Trello) sobre o dominio de DashboardCard que
ja existe — e executa desde ja a Fase 0 dessa entrega, que e a unica com risco
de vazamento de dado pessoal.

Documentos novos (docs/)
------------------------
- PRD.md  (v1.0, 774 linhas) — o problema, as personas, os requisitos funcionais
  e os 30 criterios de aceite. Parte do achado central: hoje o agrupamento visual
  e derivado de DashboardCardCategory, um vocabulario GLOBAL compartilhado por
  todas as empresas, e por isso incapaz de expressar "este quadro tem estas
  colunas" — o quadro-modelo real da STW tem 31 listas nomeadas por norma e por
  controle. Registra tambem os riscos, entre eles R6 (o export do Trello ser
  commitado por engano, expondo 12 nomes de membros).
- Spec.md (v1.0, 551 linhas) — a traducao tecnica do PRD: arvore de arquivos
  (20 novos, 24 modificados, 3 dependencias npm), contratos de API, modelo de
  dados e migration. Corrige duas divergencias do PRD descobertas na leitura do
  codigo: (1) client-dashboard-client.tsx renderiza AuditControl vindo de
  GET /api/v1/client/controls, nao DashboardCard — a visao de quadro do cliente
  e rota nova, nao modificacao; (2) test_migrations_smoke.py e analise estatica
  e roda sem banco, logo nao pode verificar CA-02/CA-03 — o backfill precisa de
  arquivo de teste proprio.
- Code.md (v1.0, 16.584 linhas) — o guia de implementacao 100% manual, em 13
  fases ordenadas por dependencia, com o codigo-fonte integral de cada arquivo
  (arquivo inteiro depois da modificacao, sem "resto do codigo"). Cobre indice
  fracionario, DashboardColumn, DashboardCard.position/description,
  DashboardLabel + M:N, rotas, testes de backend, quadro do admin, quadro do
  cliente, tela de etiquetas, colunas de template, importador do Trello e seed.
  Head de migrations: b7c02e91d4a5 -> c8f1a3e57b90.

Higiene de repositorio — CA-30 / R6 executado agora
---------------------------------------------------
- .gitignore: passam a ser ignorados `trello*.json` e `Trello*.json`.
  O arquivo "trello exemplo para ser implementado.json" (1,2 MB) esta hoje
  untracked na raiz e contem 12 nomes completos de membros e o ID da organizacao
  do Trello — dado pessoal sob LGPD, num repositorio que ja teve incidente de
  segredos no historico. Ele NAO entra no indice: o importador
  (backend/scripts/import_trello_board.py, Fase 11) le o arquivo do disco local
  do operador. Esta e a primeira fase da entrega justamente por ser a que se
  esquece — nada mais depende dela.

Indice
------
- docs/index.md: PRD.md, Spec.md e Code.md registrados na secao
  "Planejamento & Execucao", para a central de documentacao continuar sendo a
  lista completa dos documentos do projeto.

Sem alteracao de codigo, de migration ou de teste nesta entrega — a base
permanece no HEAD 754ed58, com os 4 jobs de CI verdes.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>

### Arquivos Modificados (5 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `.gitignore` | Outro / Não Categorizado |
| Adicionado | `docs/Code.md` | Documentação Técnica |
| Adicionado | `docs/PRD.md` | Documentação Técnica |
| Adicionado | `docs/Spec.md` | Documentação Técnica |
| Modificado | `docs/index.md` | Documentação Técnica |

### Funcionalidades Impactadas

- Documentação Técnica
- Outro / Não Categorizado

### Correções Realizadas

- Nenhuma referência a achado (`B-X00` / `RD-00`) identificada neste commit.

### Verificações Recomendadas

- Nenhuma verificação manual específica disparada pelos caminhos tocados.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Revisar consistência com os outros documentos de `docs/`.
- Verificar cada afirmação de estado contra o código, não contra a revisão anterior.

---

## Commit `d4482e1` — 2026-08-26 15:04:55

| Campo | Valor |
|---|---|
| **Autor** | Rodig0SantOs (163863169+Rodig0SantOs@users.noreply.github.com) |
| **Branch** | `main` |
| **Tipo** | 📌 Alteração Geral (`other`) |
| **Hash Completo** | `d4482e1c50a1b3d6bc630a397d85e6d35c195823` |
| **Arquivos Alterados** | 13 arquivo(s) |
| **Linhas** | +620 / −98 |

### Título do Commit

```
Merge PR #2 — correcao dos 4 defeitos revelados pela primeira execucao do CI
```

### Descrição

Cadeia de downgrade do Alembic, 9 CVEs (7 no parser de upload), tipos gerados do Next e variaveis de ambiente do job backend. Detalhes em docs/plano_implementacao.md.

### Arquivos Modificados (13 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `.github/workflows/ci.yml` | CI/CD e Automação |
| Modificado | `backend/alembic/versions/447a4e1de59d_add_sub_user_role_flow.py` | Banco de Dados / Migrações |
| Modificado | `backend/alembic/versions/4f2b8e6a91d3_add_dashboard_card_categories.py` | Banco de Dados / Migrações |
| Modificado | `backend/alembic/versions/56d322bbd83a_add_performance_indices.py` | Banco de Dados / Migrações |
| Modificado | `backend/alembic/versions/86f95e525db1_create_audit_schema_v1.py` | Banco de Dados / Migrações |
| Modificado | `backend/alembic/versions/9d5a3c1b2e77_add_dashboard_domain_tables.py` | Banco de Dados / Migrações |
| Modificado | `backend/alembic/versions/bf7239a52df8_add_company_messages.py` | Banco de Dados / Migrações |
| Modificado | `backend/alembic/versions/d5c4d7cd6687_add_performance_indices.py` | Banco de Dados / Migrações |
| Modificado | `backend/alembic/versions/d60f999c1fca_add_sub_user_role_flow.py` | Banco de Dados / Migrações |
| Modificado | `backend/alembic/versions/eafa65e9df05_restore_dashboard_card_indices.py` | Banco de Dados / Migrações |
| Modificado | `backend/requirements.txt` | Dependências Python |
| Modificado | `backend/tests/test_config_defaults.py` | Testes Automatizados (pytest) |
| Modificado | `docs/relatorio_commit.md` | Documentação Técnica |

### Funcionalidades Impactadas

- Banco de Dados / Migrações
- CI/CD e Automação
- Dependências Python
- Documentação Técnica
- Testes Automatizados (pytest)

### Correções Realizadas

- Nenhuma referência a achado (`B-X00` / `RD-00`) identificada neste commit.

### Verificações Recomendadas

- ⚠️ **Migration alterada.** A suíte usa `Base.metadata.create_all` e **não** executa migrations (ver M-18 em `docs/relatorio_melhorias.md`) — uma suíte verde não prova que a migration roda. Execute `alembic upgrade head` contra o MySQL real e confirme `alembic heads` com um único head.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Revisar os arquivos modificados em contexto com `docs/relatorio_bugs.md`.
- Consultar `docs/roadmap.md` para verificar alinhamento com o plano.

---

## Commit `a90e3f1` — 2026-08-26 14:20:37

| Campo | Valor |
|---|---|
| **Autor** | Rodig0SantOs (163863169+Rodig0SantOs@users.noreply.github.com) |
| **Branch** | `main` |
| **Tipo** | 📌 Alteração Geral (`other`) |
| **Hash Completo** | `a90e3f14cb374aad3d6e598ef503c1437b7b0c64` |
| **Arquivos Alterados** | 239 arquivo(s) |
| **Linhas** | +61620 / −13820 |

### Título do Commit

```
Merge PR #1 — BLOCOS P, Q e R: segurança, achados de borda e testes de frontend
```

### Descrição

Traz o ci.yml para o branch padrão, onde o GitHub Actions o registra e passa a executá-lo. Ver docs/plano_implementacao.md (BLOCOS P, Q, R) e docs/relatorio_bugs.md (rev. 9.2).

### Arquivos Modificados (239 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Adicionado | `.gitattributes` | Outro / Não Categorizado |
| Modificado | `.github/scripts/generate_commit_report.py` | CI/CD e Automação |
| Adicionado | `.github/workflows/ci.yml` | CI/CD e Automação |
| Modificado | `.github/workflows/commit-report.yml` | CI/CD e Automação |
| Adicionado | `.gitignore` | Outro / Não Categorizado |
| Adicionado | `.pre-commit-config.yaml` | Outro / Não Categorizado |
| Adicionado | `INSTRUCTIONS.md` | Documentação Técnica |
| Adicionado | `backend/.dockerignore` | Outro / Não Categorizado |
| Modificado | `backend/.env.example` | Configuração e Segurança |
| Modificado | `backend/.gitignore` | Outro / Não Categorizado |
| Adicionado | `backend/Dockerfile` | Infraestrutura / Docker |
| Modificado | `backend/README.md` | Documentação Técnica |
| Modificado | `backend/alembic/env.py` | Banco de Dados / Migrações |
| Adicionado | `backend/alembic/versions/0ba953b10f8b_drop_classic_checklist_subsystem.py` | Banco de Dados / Migrações |
| Modificado | `backend/alembic/versions/447a4e1de59d_add_sub_user_role_flow.py` | Banco de Dados / Migrações |
| Adicionado | `backend/alembic/versions/4f2b8e6a91d3_add_dashboard_card_categories.py` | Banco de Dados / Migrações |
| Adicionado | `backend/alembic/versions/5457e7377a56_relax_company_phone_and_card_control_.py` | Banco de Dados / Migrações |
| Adicionado | `backend/alembic/versions/7e3f9c2b5a1d_add_messages_read_at.py` | Banco de Dados / Migrações |
| Adicionado | `backend/alembic/versions/83cf1e14efa8_fix_evidences_and_messages_naming_typos.py` | Banco de Dados / Migrações |
| Adicionado | `backend/alembic/versions/a3d81f4c7b02_backfill_card_origin_template.py` | Banco de Dados / Migrações |
| Adicionado | `backend/alembic/versions/b7c02e91d4a5_unique_card_origin.py` | Banco de Dados / Migrações |
| Adicionado | `backend/alembic/versions/bf7239a52df8_add_company_messages.py` | Banco de Dados / Migrações |
| Adicionado | `backend/alembic/versions/c2a7e6f1b8d3_add_naoconforme_to_audit_control_status.py` | Banco de Dados / Migrações |
| Adicionado | `backend/alembic/versions/eafa65e9df05_restore_dashboard_card_indices.py` | Banco de Dados / Migrações |
| Adicionado | `backend/alembic/versions/f224a87de1a4_fix_sub_user_requests_full_name_typo.py` | Banco de Dados / Migrações |
| Modificado | `backend/app/api/deps.py` | Autenticação / Autorização |
| Adicionado | `backend/app/api/health.py` | Health Check / Observabilidade |
| Modificado | `backend/app/api/v1/admin.py` | Auditorias (Admin) |
| Modificado | `backend/app/api/v1/admin_onboarding.py` | Onboarding de Clientes |
| Modificado | `backend/app/api/v1/auth.py` | Autenticação / Login |
| Modificado | `backend/app/api/v1/client.py` | Interface do Cliente |
| Adicionado | `backend/app/api/v1/companies.py` | Gestão de Empresas (Admin) |
| Adicionado | `backend/app/api/v1/company_messages.py` | Mensagens Gerais (Admin↔Cliente) |
| Modificado | `backend/app/api/v1/dashboard_cards.py` | Dashboard Gerencial / Cards |
| Adicionado | `backend/app/api/v1/dashboard_categories.py` | Categorias de Card |
| Adicionado | `backend/app/api/v1/dashboard_templates.py` | Templates de Dashboard |
| Modificado | `backend/app/api/v1/router.py` | Roteamento da API |
| Modificado | `backend/app/api/v1/sub_users.py` | Sub-usuários |
| Modificado | `backend/app/api/v1/users.py` | Perfil do Usuário |
| Adicionado | `backend/app/core/access.py` | Configuração e Segurança |
| Modificado | `backend/app/core/config.py` | Configuração e Segurança |
| Modificado | `backend/app/core/jwt.py` | Configuração e Segurança |
| Adicionado | `backend/app/core/policy.py` | Configuração e Segurança |
| Modificado | `backend/app/core/security.py` | Configuração e Segurança |
| Removido | `backend/app/db/create_with_controls.py` | Conexão com Banco de Dados |
| Adicionado | `backend/app/db/mixins.py` | Conexão com Banco de Dados |
| Modificado | `backend/app/db/session.py` | Conexão com Banco de Dados |
| Modificado | `backend/app/main.py` | Bootstrap da Aplicação |
| Modificado | `backend/app/middleware/request_id.py` | Middleware / Observabilidade |
| Modificado | `backend/app/middleware/security_headers.py` | Middleware / Observabilidade |
| Modificado | `backend/app/models/__init__.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/audit.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/audit_control.py` | Modelos de Dados (ORM) |
| Removido | `backend/app/models/checklist.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/company_dashboard.py` | Modelos de Dados (ORM) |
| Adicionado | `backend/app/models/company_message.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/control_catalog.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/evidence.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/message.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/sub_user_request.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/user.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/repositories/audit_repository.py` | Repository Pattern (ORM) |
| Modificado | `backend/app/schemas/admin.py` | Schemas / Validação de Dados |
| Modificado | `backend/app/schemas/admin_onboarding.py` | Schemas / Validação de Dados |
| Modificado | `backend/app/schemas/audit.py` | Schemas / Validação de Dados |
| Modificado | `backend/app/schemas/auth.py` | Schemas / Validação de Dados |
| Adicionado | `backend/app/schemas/company_admin.py` | Schemas / Validação de Dados |
| Adicionado | `backend/app/schemas/company_message.py` | Schemas / Validação de Dados |
| Modificado | `backend/app/schemas/dashboard_runtime.py` | Schemas / Validação de Dados |
| Adicionado | `backend/app/schemas/dashboard_templates.py` | Schemas / Validação de Dados |
| Modificado | `backend/app/schemas/sub_user.py` | Schemas / Validação de Dados |
| Adicionado | `backend/app/services/audit_reporting.py` | Serviços / Lógica de Negócio |
| Adicionado | `backend/app/services/company_admin.py` | Serviços / Lógica de Negócio |
| Modificado | `backend/app/services/dashboard_builder.py` | Serviços / Lógica de Negócio |
| Adicionado | `backend/app/services/dashboard_template_admin.py` | Serviços / Lógica de Negócio |
| Modificado | `backend/app/services/email_sender.py` | Serviços / Lógica de Negócio |
| Adicionado | `backend/app/services/report_generator.py` | Serviços / Lógica de Negócio |
| Modificado | `backend/app/services/storage.py` | Serviços / Lógica de Negócio |
| Adicionado | `backend/app/services/storage_backend.py` | Serviços / Lógica de Negócio |
| Modificado | `backend/app/services/users.py` | Serviços / Lógica de Negócio |
| Removido | `backend/db_auditoria.sql` | Outro / Não Categorizado |
| Adicionado | `backend/docker-entrypoint.sh` | Infraestrutura / Docker |
| Adicionado | `backend/pytest.ini` | Testes Automatizados (pytest) |
| Modificado | `backend/requirements.txt` | Dependências Python |
| Adicionado | `backend/ruff.toml` | Lint / Qualidade de Código |
| Adicionado | `backend/scripts/backfill_company_cliente01.py` | Scripts de Inicialização / Seeds |
| Adicionado | `backend/scripts/prune_orphan_uploads.py` | Scripts de Inicialização / Seeds |
| Modificado | `backend/scripts/seed_catalog.py` | Scripts de Inicialização / Seeds |
| Modificado | `backend/scripts/seed_dashboard_templates.py` | Scripts de Inicialização / Seeds |
| Adicionado | `backend/scripts/seed_demo_audits.py` | Scripts de Inicialização / Seeds |
| Adicionado | `backend/scripts/seed_demo_companies.py` | Scripts de Inicialização / Seeds |
| Adicionado | `backend/tests/__init__.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/conftest.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_admin_audit_management.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_admin_audits.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_admin_companies.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_admin_users.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_auth.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_authorization_matrix.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_card_internals_visibility.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_client_audits.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_client_messages.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_company_messages.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_config_defaults.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_credentials_delivery.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_dashboard_card_categories_migration.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_dashboard_cards.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_dashboard_categories.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_dashboard_templates.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_email_content.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_evidence_upload.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_migrations_smoke.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_onboarding.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_password_limits.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_query_budget.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_security_headers.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_storage_path_guard.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_sub_users.py` | Testes Automatizados (pytest) |
| Adicionado | `docker-compose.yml` | Infraestrutura / Docker |
| Modificado | `docs/automacao_commits.md` | Documentação Técnica |
| Adicionado | `docs/backlog.md` | Documentação Técnica |
| Modificado | `docs/dashboard_projeto.md` | Documentação Técnica |
| Modificado | `docs/deploy_producao.md` | Documentação Técnica |
| Modificado | `docs/executar_projeto.md` | Documentação Técnica |
| Modificado | `docs/index.md` | Documentação Técnica |
| Modificado | `docs/mindmeister_automacao.md` | Documentação Técnica |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |
| Modificado | `docs/relatorio_bugs.md` | Documentação Técnica |
| Modificado | `docs/relatorio_commit.md` | Documentação Técnica |
| Modificado | `docs/relatorio_documentacao.md` | Documentação Técnica |
| Modificado | `docs/relatorio_funcionalidades.md` | Documentação Técnica |
| Modificado | `docs/relatorio_geral.md` | Documentação Técnica |
| Modificado | `docs/relatorio_melhorias.md` | Documentação Técnica |
| Modificado | `docs/roadmap.md` | Documentação Técnica |
| Modificado | `docs/setup_completo.md` | Documentação Técnica |
| Modificado | `docs/trello_automacao.md` | Documentação Técnica |
| Adicionado | `frontend/.dockerignore` | Outro / Não Categorizado |
| Adicionado | `frontend/Dockerfile` | Infraestrutura / Docker |
| Adicionado | `frontend/app/api/admin/audits/[auditId]/report/route.ts` | Proxy de Binário (PDF/Evidência) |
| Removido | `frontend/app/api/admin/audits/route.ts` | Proxy de Binário (PDF/Evidência) |
| Adicionado | `frontend/app/api/admin/evidences/[evidenceId]/download/route.ts` | Proxy de Binário (PDF/Evidência) |
| Removido | `frontend/app/api/admin/onboarding/companies/route.ts` | Proxy de Binário (PDF/Evidência) |
| Removido | `frontend/app/api/admin/onboarding/principal-users/route.ts` | Proxy de Binário (PDF/Evidência) |
| Removido | `frontend/app/api/admin/onboarding/templates/route.ts` | Proxy de Binário (PDF/Evidência) |
| Modificado | `frontend/app/api/auth/login/route.ts` | Proxy Auth (Next.js → FastAPI) |
| Modificado | `frontend/app/api/auth/logout/route.ts` | Proxy Auth (Next.js → FastAPI) |
| Removido | `frontend/app/api/client/controls/route.ts` | Outro / Não Categorizado |
| Removido | `frontend/app/api/me/route.ts` | Outro / Não Categorizado |
| Removido | `frontend/app/api/profile/route.ts` | Outro / Não Categorizado |
| Removido | `frontend/app/api/sub-users/requests/[id]/approve/route.ts` | Outro / Não Categorizado |
| Removido | `frontend/app/api/sub-users/requests/pending/route.ts` | Outro / Não Categorizado |
| Removido | `frontend/app/api/sub-users/requests/route.ts` | Outro / Não Categorizado |
| Modificado | `frontend/app/globals.css` | Design System (Frontend) |
| Modificado | `frontend/app/page.tsx` | Homepage / Página Inicial |
| Modificado | `frontend/app/private/_components/logout-button.tsx` | Componentes Privados (Frontend) |
| Modificado | `frontend/app/private/_components/user-menu.tsx` | Componentes Privados (Frontend) |
| Adicionado | `frontend/app/private/admin/actions.test.ts` | Home do Admin (Frontend) |
| Adicionado | `frontend/app/private/admin/actions.ts` | Home do Admin (Frontend) |
| Adicionado | `frontend/app/private/admin/admin-dashboard-client.tsx` | Home do Admin (Frontend) |
| Adicionado | `frontend/app/private/admin/auditorias/actions.test.ts` | Gestão de Auditorias (Frontend) |
| Adicionado | `frontend/app/private/admin/auditorias/actions.ts` | Gestão de Auditorias (Frontend) |
| Adicionado | `frontend/app/private/admin/auditorias/auditorias-client.tsx` | Gestão de Auditorias (Frontend) |
| Adicionado | `frontend/app/private/admin/auditorias/error.tsx` | Gestão de Auditorias (Frontend) |
| Adicionado | `frontend/app/private/admin/auditorias/loading.tsx` | Gestão de Auditorias (Frontend) |
| Adicionado | `frontend/app/private/admin/auditorias/page.tsx` | Gestão de Auditorias (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/_components/company-tabs-nav.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/auditoria/actions.test.ts` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/auditoria/actions.ts` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/auditoria/error.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/auditoria/loading.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/auditoria/page.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/dashboard/actions.test.ts` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/dashboard/actions.ts` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/dashboard/company-dashboard-client.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/dashboard/error.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/dashboard/loading.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/dashboard/page.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/layout.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/page.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/perfil/error.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/perfil/loading.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/perfil/page.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/perfil/perfil-client.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/usuarios/error.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/usuarios/loading.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/usuarios/page.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/usuarios/usuarios-client.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/actions.test.ts` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/actions.ts` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/empresas-client.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/error.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/loading.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/page.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/error.tsx` | Home do Admin (Frontend) |
| Adicionado | `frontend/app/private/admin/loading.tsx` | Home do Admin (Frontend) |
| Adicionado | `frontend/app/private/admin/mensagens/actions.test.ts` | Mensagens Gerais (Frontend Admin) |
| Adicionado | `frontend/app/private/admin/mensagens/actions.ts` | Mensagens Gerais (Frontend Admin) |
| Adicionado | `frontend/app/private/admin/mensagens/error.tsx` | Mensagens Gerais (Frontend Admin) |
| Adicionado | `frontend/app/private/admin/mensagens/loading.tsx` | Mensagens Gerais (Frontend Admin) |
| Adicionado | `frontend/app/private/admin/mensagens/mensagens-client.tsx` | Mensagens Gerais (Frontend Admin) |
| Adicionado | `frontend/app/private/admin/mensagens/page.tsx` | Mensagens Gerais (Frontend Admin) |
| Modificado | `frontend/app/private/admin/page.tsx` | Home do Admin (Frontend) |
| Adicionado | `frontend/app/private/admin/templates/actions.test.ts` | Editor de Templates (Frontend) |
| Adicionado | `frontend/app/private/admin/templates/actions.ts` | Editor de Templates (Frontend) |
| Adicionado | `frontend/app/private/admin/templates/error.tsx` | Editor de Templates (Frontend) |
| Adicionado | `frontend/app/private/admin/templates/loading.tsx` | Editor de Templates (Frontend) |
| Adicionado | `frontend/app/private/admin/templates/page.tsx` | Editor de Templates (Frontend) |
| Adicionado | `frontend/app/private/admin/templates/templates-client.tsx` | Editor de Templates (Frontend) |
| Removido | `frontend/app/private/admin_components/sub-user-requests-panel.tsx` | Outro / Não Categorizado |
| Adicionado | `frontend/app/private/client/actions.test.ts` | Dashboard Cliente (Frontend) |
| Adicionado | `frontend/app/private/client/actions.ts` | Dashboard Cliente (Frontend) |
| Adicionado | `frontend/app/private/client/client-dashboard-client.tsx` | Dashboard Cliente (Frontend) |
| Adicionado | `frontend/app/private/client/error.tsx` | Dashboard Cliente (Frontend) |
| Adicionado | `frontend/app/private/client/loading.tsx` | Dashboard Cliente (Frontend) |
| Adicionado | `frontend/app/private/client/mensagens/actions.test.ts` | Mensagens Gerais (Frontend Cliente) |
| Adicionado | `frontend/app/private/client/mensagens/actions.ts` | Mensagens Gerais (Frontend Cliente) |
| Adicionado | `frontend/app/private/client/mensagens/error.tsx` | Mensagens Gerais (Frontend Cliente) |
| Adicionado | `frontend/app/private/client/mensagens/loading.tsx` | Mensagens Gerais (Frontend Cliente) |
| Adicionado | `frontend/app/private/client/mensagens/mensagens-client.tsx` | Mensagens Gerais (Frontend Cliente) |
| Adicionado | `frontend/app/private/client/mensagens/page.tsx` | Mensagens Gerais (Frontend Cliente) |
| Modificado | `frontend/app/private/client/page.tsx` | Dashboard Cliente (Frontend) |
| Modificado | `frontend/app/private/layout.tsx` | Layout Privado (Frontend) |
| Modificado | `frontend/app/public/login/login-form.tsx` | Página de Login |
| Removido | `frontend/lib/auth-context.tsx` | Utilitários do Frontend |
| Adicionado | `frontend/lib/control-status.ts` | Status de Controle (Frontend) |
| Adicionado | `frontend/lib/safe-redirect.test.ts` | Utilitários do Frontend |
| Modificado | `frontend/lib/server-backend.ts` | Utilitários do Frontend |
| Adicionado | `frontend/lib/session.test.ts` | Utilitários do Frontend |
| Adicionado | `frontend/lib/session.ts` | DAL de Sessão (Frontend) |
| Removido | `frontend/middleware.ts` | Outro / Não Categorizado |
| Modificado | `frontend/next.config.ts` | Configuração Next.js |
| Modificado | `frontend/package-lock.json` | Outro / Não Categorizado |
| Modificado | `frontend/package.json` | Dependências Node.js |
| Adicionado | `frontend/proxy.test.ts` | Outro / Não Categorizado |
| Adicionado | `frontend/proxy.ts` | Proxy/Guarda de Autenticação |
| Adicionado | `frontend/test/helpers/action-mocks.ts` | Outro / Não Categorizado |
| Adicionado | `frontend/test/stubs/server-only.ts` | Outro / Não Categorizado |
| Adicionado | `frontend/vitest.config.ts` | Outro / Não Categorizado |
| Adicionado | `frontend/vitest.setup.ts` | Outro / Não Categorizado |

### Funcionalidades Impactadas

- Auditorias (Admin)
- Autenticação / Autorização
- Autenticação / Login
- Banco de Dados / Migrações
- Bootstrap da Aplicação
- CI/CD e Automação
- Categorias de Card
- Componentes Privados (Frontend)
- Conexão com Banco de Dados
- Configuração Next.js
- Configuração e Segurança
- DAL de Sessão (Frontend)
- Dashboard Cliente (Frontend)
- Dashboard Gerencial / Cards
- Dependências Node.js
- Dependências Python
- Design System (Frontend)
- Documentação Técnica
- Editor de Templates (Frontend)
- Gestão de Auditorias (Frontend)
- Gestão de Empresas (Admin)
- Gestão de Empresas (Frontend)
- Health Check / Observabilidade
- Home do Admin (Frontend)
- Homepage / Página Inicial
- Infraestrutura / Docker
- Interface do Cliente
- Layout Privado (Frontend)
- Lint / Qualidade de Código
- Mensagens Gerais (Admin↔Cliente)
- Mensagens Gerais (Frontend Admin)
- Mensagens Gerais (Frontend Cliente)
- Middleware / Observabilidade
- Modelos de Dados (ORM)
- Onboarding de Clientes
- Outro / Não Categorizado
- Perfil do Usuário
- Proxy Auth (Next.js → FastAPI)
- Proxy de Binário (PDF/Evidência)
- Proxy/Guarda de Autenticação
- Página de Login
- Repository Pattern (ORM)
- Roteamento da API
- Schemas / Validação de Dados
- Scripts de Inicialização / Seeds
- Serviços / Lógica de Negócio
- Status de Controle (Frontend)
- Sub-usuários
- Templates de Dashboard
- Testes Automatizados (pytest)
- Utilitários do Frontend

### Correções Realizadas

- Nenhuma referência a achado (`B-X00` / `RD-00`) identificada neste commit.

### Verificações Recomendadas

- ⚠️ **Migration alterada.** A suíte usa `Base.metadata.create_all` e **não** executa migrations (ver M-18 em `docs/relatorio_melhorias.md`) — uma suíte verde não prova que a migration roda. Execute `alembic upgrade head` contra o MySQL real e confirme `alembic heads` com um único head.
- ⚠️ **Endpoint alterado.** Confirme a dependência de autorização: posse (`_get_*_with_access`) não é permissão. Ver **B-A23** em `docs/relatorio_bugs.md`.
- 🔴 **Arquivo de configuração versionado.** Nenhum valor real pode entrar aqui — ver **B-C23** em `docs/relatorio_bugs.md`.
- 🔴 **Documentação versionada.** Nenhuma credencial em texto claro — ver **B-C23**.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Revisar os arquivos modificados em contexto com `docs/relatorio_bugs.md`.
- Consultar `docs/roadmap.md` para verificar alinhamento com o plano.

---

## Commit `34f8444` — 2026-08-25 19:06:57

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🐛 Correção de Bug (`fix`) |
| **Hash Completo** | `34f8444196790b85dbdd00916e1e70d8ec8412e1` |
| **Arquivos Alterados** | 3 arquivo(s) |
| **Linhas** | +232 / −14 |

### Título do Commit

```
fix(api): CSP uniforme deixava o Swagger em branco (B-M21, defeito #14)
```

### Descrição

O CSP de P.4.4 era aplicado a todas as respostas com `default-src 'none'`,
justificado pela premissa de que "a API so devolve JSON/PDF/binario — nenhuma
pagina HTML com script". A premissa e falsa: /docs e /redoc sao paginas HTML
servidas pelo proprio FastAPI, que carregam bundle e CSS de cdn.jsdelivr.net,
favicon de fastapi.tiangolo.com, fontes do Google (ReDoc) e inicializam a UI
num <script> inline.

Sintoma: GET /docs responde 200 e a pagina renderiza em branco. O bloqueio e
do navegador, entao nao aparece em log nenhum do servidor — mesma assinatura
do problema anterior de JWT_SECRET: sucesso no servidor, porta fechada no
cliente.

## Correcao

- API_CSP (default-src 'none') continua nas rotas de dados, que e onde esta o
  valor do B-M21.
- DOCS_CSP libera exatamente as origens que o HTML gerado por
  get_swagger_ui_html/get_redoc_html referencia, e nada alem: script-src e
  style-src para cdn.jsdelivr.net, style-src para fonts.googleapis.com,
  font-src para fonts.gstatic.com, img-src para fastapi.tiangolo.com,
  connect-src 'self' para o fetch do /openapi.json.
- 'unsafe-inline' em script-src e inevitavel (as duas paginas inicializam a UI
  num script inline sem nonce) e fica restrito as rotas de documentacao.
- frame-ancestors e base-uri seguem 'none' tambem nas paginas de doc.
- As rotas de doc sao resolvidas a partir de app.docs_url / app.redoc_url /
  app.swagger_ui_oauth2_redirect_url, nao fixadas: se forem desativadas em
  producao, o middleware acompanha sem edicao.

## Barreira

Novo tests/test_security_headers.py (10 testes). O teste que faltava nao e
"o header esta presente" — era exatamente isso que dava a falsa seguranca.
E: varrer o HTML real de /docs e /redoc, extrair cada origem que a pagina
pede e afirmar que a diretiva correspondente do CSP a permite. Se o FastAPI
trocar de CDN numa atualizacao, o teste falha em vez de a pagina parar de
renderizar em silencio. Mais os testes que garantem que a excecao nao vazou:
rotas de dados e /openapi.json seguem com default-src 'none'.

## Testes

- python -m pytest -q -> 202 passed, 0 failed (192 + 10 novos)
- python -m ruff check app scripts tests -> limpo
- Barreira verificada por reversao: com o CSP uniforme de volta, falha com
  "/docs: script-src bloqueia https://cdn.jsdelivr.net — a pagina carrega com
  200 e renderiza em branco"; com a correcao, 10 passed.
- Cada recurso de /docs e /redoc conferido origem por origem contra o CSP.

## Documento

P.4.4 reescrito com a versao correta e um aviso sobre a premissa falsa, para
que a versao antiga nao seja reintroduzida a partir do proprio plano. O item
"CSP presente" da checklist de P.4 tinha sido marcado como validado conferindo
so a existencia do header — corrigido, com a ressalva registrada. Defeito #14
acrescentado a P.7.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>

### Arquivos Modificados (3 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `backend/app/middleware/security_headers.py` | Middleware / Observabilidade |
| Adicionado | `backend/tests/test_security_headers.py` | Testes Automatizados (pytest) |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |

### Funcionalidades Impactadas

- Documentação Técnica
- Middleware / Observabilidade
- Testes Automatizados (pytest)

### Correções Realizadas

- Referências detectadas: **B-M21**
  - Consulte `docs/relatorio_bugs.md` para o detalhamento de cada item.

### Verificações Recomendadas

- Nenhuma verificação manual específica disparada pelos caminhos tocados.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Verificar se o mesmo bug ocorre em contextos similares no código.
- Adicionar teste de regressão para garantir que o problema não retorne.
- Atualizar `docs/relatorio_bugs.md` marcando o achado como corrigido.

---

## Commit `9e3076f` — 2026-08-25 18:27:22

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 📝 Documentação (`docs`) |
| **Hash Completo** | `9e3076fffd483ed72c67587d4ccc36b6e8ff435a` |
| **Arquivos Alterados** | 21 arquivo(s) |
| **Linhas** | +9150 / −2499 |

### Título do Commit

```
docs: auditoria adversarial rev. 8.0 e sincronizacao da pasta docs/
```

### Descrição

Registra a auditoria que deu origem ao BLOCO P (implementado no commit
anterior) e sincroniza os demais documentos com o estado atual do codigo.

- relatorio_bugs.md sobe para a rev. 8.0: auditoria adversarial que exercita
  a API fora do caminho que a UI percorre. 1 achado Critico (B-C23,
  credenciais em arquivo versionado), 4 Altos (B-A23 posse tratada como
  permissao, B-A24 origin_template_card_id nunca preenchido, B-A25 exclusao
  de template em uso, B-A26 evidencias sobrevivendo a exclusao da empresa) e
  3 Medios, todos confirmados por sonda executavel, nao por leitura.
- relatorio_melhorias.md sobe para a rev. 6.0, com as 5 barreiras estruturais
  (M-15 camada de politica, M-16 Protocol de storage, M-18 migrations no CI,
  M-19 constraint de unicidade, M-20 matriz de autorizacao) — cada correcao
  do BLOCO P vem pareada com a barreira que impede a reincidencia.
- relatorio_geral.md, relatorio_funcionalidades.md, relatorio_documentacao.md,
  roadmap.md, backlog.md, dashboard_projeto.md, index.md, setup_completo.md,
  executar_projeto.md, deploy_producao.md e os documentos de automacao
  (commits, trello, mindmeister) atualizados para o mesmo recorte.
- deploy_producao.md: senha de exemplo redigida (parte de B-C23).
- .github/scripts/generate_commit_report.py e commit-report.yml revisados
  junto, por serem a fonte de relatorio_commit.md.
- Os dois Prompt_*.txt na raiz foram consolidados em INSTRUCTIONS.md, que
  passa a ser o unico arquivo de diretivas de execucao do projeto.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>

### Arquivos Modificados (21 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `.github/scripts/generate_commit_report.py` | CI/CD e Automação |
| Modificado | `.github/workflows/commit-report.yml` | CI/CD e Automação |
| Adicionado | `INSTRUCTIONS.md` | Documentação Técnica |
| Removido | `Prompt_Analise_de_projeto.txt` | Outro / Não Categorizado |
| Removido | `Prompt_Atualizar_Plano_Implemetacao.txt` | Outro / Não Categorizado |
| Modificado | `docs/automacao_commits.md` | Documentação Técnica |
| Modificado | `docs/backlog.md` | Documentação Técnica |
| Modificado | `docs/dashboard_projeto.md` | Documentação Técnica |
| Modificado | `docs/deploy_producao.md` | Documentação Técnica |
| Modificado | `docs/executar_projeto.md` | Documentação Técnica |
| Modificado | `docs/index.md` | Documentação Técnica |
| Modificado | `docs/mindmeister_automacao.md` | Documentação Técnica |
| Modificado | `docs/relatorio_bugs.md` | Documentação Técnica |
| Modificado | `docs/relatorio_commit.md` | Documentação Técnica |
| Modificado | `docs/relatorio_documentacao.md` | Documentação Técnica |
| Modificado | `docs/relatorio_funcionalidades.md` | Documentação Técnica |
| Modificado | `docs/relatorio_geral.md` | Documentação Técnica |
| Modificado | `docs/relatorio_melhorias.md` | Documentação Técnica |
| Modificado | `docs/roadmap.md` | Documentação Técnica |
| Modificado | `docs/setup_completo.md` | Documentação Técnica |
| Modificado | `docs/trello_automacao.md` | Documentação Técnica |

### Funcionalidades Impactadas

- CI/CD e Automação
- Documentação Técnica
- Outro / Não Categorizado

### Correções Realizadas

- Referências detectadas: **B-A23, B-A24, B-A25, B-A26, B-C23**
  - Consulte `docs/relatorio_bugs.md` para o detalhamento de cada item.

### Verificações Recomendadas

- Nenhuma verificação manual específica disparada pelos caminhos tocados.

### Pendências Identificadas

**Novos TODOs/FIXMEs introduzidos neste commit:**
- `.github/scripts/generate_commit_report.py`: Linhas +TODO/+FIXME/+HACK/+XXX adicionadas neste commit.
- `.github/scripts/generate_commit_report.py`: if re.search(r"\b(TODO|FIXME|HACK|XXX)\b", content):
- `docs/automacao_commits.md`: Uma mensagem de commit descreve **o que o autor pretendia**. O relatório descreve **o que o commit efetivamente tocou** ...
- `docs/automacao_commits.md`: Linhas +TODO/+FIXME/+HACK/+XXX adicionadas neste commit.
- `docs/automacao_commits.md`: | **Pendências Identificadas** | Linhas `+TODO/FIXME/HACK/XXX` do diff + seção `Pendências:` do corpo do commit |

### Próximos Passos Recomendados

- Revisar consistência com os outros documentos de `docs/`.
- Verificar cada afirmação de estado contra o código, não contra a revisão anterior.

---

## Commit `4fd576f` — 2026-08-25 18:27:01

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🐛 Correção de Bug (`fix`) |
| **Hash Completo** | `4fd576fe3e5e88c2a3be3fb83667bbda5e5eff57` |
| **Arquivos Alterados** | 36 arquivo(s) |
| **Linhas** | +3357 / −167 |

### Título do Commit

```
fix(security): BLOCO P — autorizacao, retencao de arquivo, vinculo template e barreiras de CI
```

### Descrição

Implementa e conclui as fases P.1-P.4 do BLOCO P (docs/plano_implementacao.md),
que nasceram da auditoria adversarial da rev. 8.0 de docs/relatorio_bugs.md:
1 achado Critico, 4 Altos, 3 Medios e 5 barreiras estruturais.

O bloco ja tinha sido parcialmente aplicado. Esta revisao verificou cada
arquivo contra o spec e encontrou 13 defeitos, 11 deles pegos pela propria
suite de testes do bloco. O padrao dominante foi codigo correto colocado no
lugar errado — nao erro de digitacao. O relatorio completo esta em P.7.

## P.1 — Autorizacao: posse nao e permissao (B-A23, M-15, M-20)

- PATCH /dashboard/cards/{id}/status e PATCH /dashboard/checklist-items/
  {id}/toggle passam a exigir require_admin. O cliente auditado nao declara
  mais a propria conformidade nem escreve na trilha de auditoria.
- POST /dashboard/cards/{id}/entries recusa CHECKLIST/HISTORY/CHAT_ANSWER de
  papel nao-admin; CHAT_QUESTION segue livre, e o canal legitimo do cliente.
- Novo app/core/policy.py (M-15): Action + ALLOWED_ROLES como fonte unica de
  verdade, com can()/assert_can(). Corrigidos os nomes MANEGE_* -> MANAGE_* e
  o valor "WHITE_CARD_HISTORY" -> "WRITE_CARD_HISTORY".
- Novo tests/test_authorization_matrix.py (M-20): cada endpoint de escrita
  exercitado por cada papel que NAO deveria poder executa-lo.

## P.2 — Retencao de arquivo: o storage nunca destruia (B-A26, M-16)

- storage.delete_files() apaga do disco apos o commit, recusa storage_key
  que resolva para fora de uploads/ e nunca levanta excecao.
- Corrigido: o bloco que le evidence_storage_keys estava ANTES da definicao
  de audits/audit_ids (UnboundLocalError em toda exclusao de empresa), com um
  laco de delete duplicado; o campo faltava no return do dataclass; e o router
  fazia `delete_files = delete_files(...)`, sombreando a funcao importada.
- deleted_evidence_files acrescentado a CompanyDeletionSummary.
- Novos: scripts/prune_orphan_uploads.py e services/storage_backend.py (M-16).

## P.3 — Integridade do vinculo template<->card (B-A24, B-A25, B-M23, M-19)

- B-A25: excluir template ou card de template em uso agora retorna 409. O
  bloco de P.3.1 tinha sido apendado aninhado dentro do corpo de
  TemplateInUseError, entao as funcoes reais seguiam sem guarda e o DELETE
  respondia 204 apagando o vinculo em silencio.
- Restaurada a rota POST /admin/templates/{id}/cards, que havia sido
  sobrescrita pela rota nova de DELETE (criar card de template dava 404), e
  removida a definicao duplicada de delete_dashboard_template_card.
- B-A24: migrations a3d81f4c7b02 (backfill de origin_template_card_id por
  titulo nao-ambiguo) e b7c02e91d4a5 (constraint unica, M-19). As duas
  estavam com nome de arquivo divergindo do revision declarado — a terceira
  ocorrencia da classe de incidente de I.5/O.5, desta vez pega pela barreira.
- P.3.6: adopted_count passa a aparecer na mensagem do admin; sem isso,
  aplicar template em empresa pre-O.3 exibia "0 card(s) criado(s)".

## P.4 — Barreiras de CI e limpeza

- M-18: tests/test_migrations_smoke.py (importabilidade, nome x revision,
  head unico) e job `migrations` no CI contra MySQL 8.4 real.
- B-B13: pip-audit acrescentado ao job backend.
- .pre-commit-config.yaml movido de backend/ para a raiz — pre-commit resolve
  a configuracao a partir do topo do repo, entao o hook do gitleaks nunca
  teria rodado onde estava.
- B-M15 decore_token -> decode_token; B-M18 require_main_user; B-B09 nome do
  pacote do frontend; B-B10 rota morta GET /Monitoring; B-B11 atalhos de dev
  so em NODE_ENV=development (e href relativo corrigido); B-B15
  DashboardCardListItem orfa removida; B-B16 python-dotenv declarado.
- P.0 (parte versionada): db_auditoria.sql removido, README.md sem a senha em
  linha de comando, .env.example com as 21 variaveis em placeholder.

## Testes

- python -m pytest -q -> 192 passed, 0 failed (era 9 failed, 183 passed)
- python -m ruff check app scripts tests -> limpo
- python -m alembic heads -> 1 head, b7c02e91d4a5; cadeia conferida por
  alembic history (4f2b8e6a91d3 -> a3d81f4c7b02 -> b7c02e91d4a5)
- Barreira M-18 exercitada de verdade: SyntaxError proposital numa migration
  fez test_migration_module_is_importable falhar; arquivo revertido em seguida
- npx tsc --noEmit, npm run lint e npm run build -> limpos
- Varredura por padroes de credencial nos arquivos rastreados -> nada

Pendente e registrado em P.7: a rotacao das credenciais (P.0.1-P.0.3) e a
decisao sobre o historico (P.0.8) sao operacoes sobre o ambiente em execucao,
nao sobre o repositorio, e a rotacao do JWT_SECRET derruba todas as sessoes.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>

### Arquivos Modificados (36 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `.github/workflows/ci.yml` | CI/CD e Automação |
| Adicionado | `.pre-commit-config.yaml` | Outro / Não Categorizado |
| Modificado | `backend/.env.example` | Configuração e Segurança |
| Modificado | `backend/README.md` | Documentação Técnica |
| Adicionado | `backend/alembic/versions/a3d81f4c7b02_backfill_card_origin_template.py` | Banco de Dados / Migrações |
| Adicionado | `backend/alembic/versions/b7c02e91d4a5_unique_card_origin.py` | Banco de Dados / Migrações |
| Modificado | `backend/app/api/deps.py` | Autenticação / Autorização |
| Modificado | `backend/app/api/v1/client.py` | Interface do Cliente |
| Modificado | `backend/app/api/v1/companies.py` | Gestão de Empresas (Admin) |
| Modificado | `backend/app/api/v1/dashboard_cards.py` | Dashboard Gerencial / Cards |
| Modificado | `backend/app/api/v1/dashboard_templates.py` | Templates de Dashboard |
| Modificado | `backend/app/api/v1/router.py` | Roteamento da API |
| Modificado | `backend/app/core/jwt.py` | Configuração e Segurança |
| Adicionado | `backend/app/core/policy.py` | Configuração e Segurança |
| Modificado | `backend/app/middleware/security_headers.py` | Middleware / Observabilidade |
| Modificado | `backend/app/models/company_dashboard.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/schemas/company_admin.py` | Schemas / Validação de Dados |
| Modificado | `backend/app/schemas/dashboard_runtime.py` | Schemas / Validação de Dados |
| Modificado | `backend/app/schemas/dashboard_templates.py` | Schemas / Validação de Dados |
| Modificado | `backend/app/services/company_admin.py` | Serviços / Lógica de Negócio |
| Modificado | `backend/app/services/dashboard_template_admin.py` | Serviços / Lógica de Negócio |
| Modificado | `backend/app/services/storage.py` | Serviços / Lógica de Negócio |
| Adicionado | `backend/app/services/storage_backend.py` | Serviços / Lógica de Negócio |
| Removido | `backend/db_auditoria.sql` | Outro / Não Categorizado |
| Modificado | `backend/requirements.txt` | Dependências Python |
| Adicionado | `backend/scripts/prune_orphan_uploads.py` | Scripts de Inicialização / Seeds |
| Modificado | `backend/tests/test_admin_companies.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_authorization_matrix.py` | Testes Automatizados (pytest) |
| Modificado | `backend/tests/test_dashboard_cards.py` | Testes Automatizados (pytest) |
| Modificado | `backend/tests/test_dashboard_templates.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_migrations_smoke.py` | Testes Automatizados (pytest) |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |
| Modificado | `frontend/app/page.tsx` | Homepage / Página Inicial |
| Modificado | `frontend/app/private/admin/empresas/[id]/dashboard/actions.ts` | Gestão de Empresas (Frontend) |
| Modificado | `frontend/app/private/admin/empresas/[id]/dashboard/company-dashboard-client.tsx` | Gestão de Empresas (Frontend) |
| Modificado | `frontend/package.json` | Dependências Node.js |

### Funcionalidades Impactadas

- Autenticação / Autorização
- Banco de Dados / Migrações
- CI/CD e Automação
- Configuração e Segurança
- Dashboard Gerencial / Cards
- Dependências Node.js
- Dependências Python
- Documentação Técnica
- Gestão de Empresas (Admin)
- Gestão de Empresas (Frontend)
- Homepage / Página Inicial
- Interface do Cliente
- Middleware / Observabilidade
- Modelos de Dados (ORM)
- Outro / Não Categorizado
- Roteamento da API
- Schemas / Validação de Dados
- Scripts de Inicialização / Seeds
- Serviços / Lógica de Negócio
- Templates de Dashboard
- Testes Automatizados (pytest)

### Correções Realizadas

- Referências detectadas: **B-A23, B-A24, B-A25, B-A26, B-B09, B-B10, B-B11, B-B13, B-B15, B-B16, B-M15, B-M18, B-M23**
  - Consulte `docs/relatorio_bugs.md` para o detalhamento de cada item.

### Verificações Recomendadas

- ⚠️ **Migration alterada.** A suíte usa `Base.metadata.create_all` e **não** executa migrations (ver M-18 em `docs/relatorio_melhorias.md`) — uma suíte verde não prova que a migration roda. Execute `alembic upgrade head` contra o MySQL real e confirme `alembic heads` com um único head.
- ⚠️ **Endpoint alterado.** Confirme a dependência de autorização: posse (`_get_*_with_access`) não é permissão. Ver **B-A23** em `docs/relatorio_bugs.md`.
- 🔴 **Arquivo de configuração versionado.** Nenhum valor real pode entrar aqui — ver **B-C23** em `docs/relatorio_bugs.md`.
- 🔴 **Documentação versionada.** Nenhuma credencial em texto claro — ver **B-C23**.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Verificar se o mesmo bug ocorre em contextos similares no código.
- Adicionar teste de regressão para garantir que o problema não retorne.
- Atualizar `docs/relatorio_bugs.md` marcando o achado como corrigido.

---

## Commit `66578f0` — 2026-08-24 12:20:52

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 📝 Documentação (`docs`) |
| **Hash Completo** | `66578f036e02d519b333ddd38ade852b27064ffd` |
| **Arquivos Alterados** | 1 arquivo(s) |
| **Linhas** | +89 / −5 |

### Título do Commit

```
docs(plano): sincroniza o BLOCO O com o código implementado
```

### Descrição

Segunda passagem sobre `plano_implementacao.md` depois de `94873ec`: a
primeira só marcou O.1–O.4 como concluídos e acrescentou a seção O.6.
Esta fecha as lacunas que sobraram entre o documento e a realidade.

Cabeçalho
- Nova linha "HEAD analisado (revisão 5.17)" apontando para `94873ec`,
  deixando explícito que — diferente da 5.16, que era só planejamento —
  esta revisão altera código.
- Data de 2026-08-24 na cadeia de "Atualizado em".

BLOCO O
- Banner de estado no topo do bloco, com tabela de referência rápida do
  que existe hoje: 6 rotas novas de frontend, 9 endpoints novos, 4
  endpoints alterados, o schema da migration e os testes acrescentados.
  A lista de endpoints foi conferida contra `app.openapi()`, não escrita
  de memória.
- Banner de conclusão no topo de cada fase (O.1–O.4), citando o commit e
  resumindo os defeitos daquela fase, com ponteiro para O.6.
- As 8 checklists deixaram de ser só "comandos a rodar" e passaram a
  registrar o resultado real de cada um, incluindo o que a validação
  cobriu por HTTP, o que foi exercitado contra o MySQL em transação com
  rollback e — explicitamente — o que **não** foi exercitado: exclusão
  de empresa pela aba Perfil e as marcas visuais `≠ template`/`custom`,
  que dependem de interação de navegador.
- Registrado na checklist de O.1 que `next typegen` precisa rodar antes
  de interpretar a saída do `tsc` em qualquer fase que crie rota nova —
  10 dos 12 erros da primeira execução eram falso positivo por tipos de
  rota ainda não gerados.
- Checklist de O.3 documenta o resultado dos dois SELECT no MySQL: as 11
  categorias (4 canônicas + 7 derivadas de `tag`) e os 0 órfãos, mais a
  observação de que `tag1`/`tag2`/`tag3` são lixo herdado do seed antigo,
  preservado de propósito e consolidável pelo CRUD de O.4.

Notas de supersessão (o documento descrevia código que não existe mais)
- D.6 ganhou aviso de que a gestão de cards saiu de `/private/admin` para
  `/private/admin/empresas/[id]/dashboard`, e de que `listAllCardsAction`,
  o tipo `DashboardCardListItem` do frontend e o filtro "Todas as
  empresas" foram removidos — com o que dali permanece válido.
- D.1 ganhou aviso de que o padrão SSR/RSC segue valendo (foi aplicado
  sem desvio nas 5 telas novas), mas que os blocos de código de
  `admin/page.tsx`/`admin-dashboard-client.tsx`/`admin/actions.ts` são a
  versão de 2026-08-07 e não batem mais com o código atual.
- Corrigidas duas afirmações que O.4 invalidou: o shape de resposta de
  `GET /dashboard/companies/{id}/cards` e a obrigatoriedade de
  `control_code` na criação manual de card.

O.5 — as advertências viraram registro do que aconteceu
- O.5.1: a ordem entre fases foi respeitada, mas as 4 saíram num commit
  único, o que na prática anula a independência de O.1/O.2 em relação ao
  schema neste repositório.
- O.5.8: o gap que a própria seção alertava se materializou pela terceira
  vez (E.10, I.5, agora O.3) — a migration tinha SyntaxError e a suíte
  seguia verde. Fica a conclusão prática: rodar `alembic upgrade head`
  contra o MySQL real é o primeiro passo da fase, não o último.
- O.5.10: registra o que foi de fato sincronizado (este plano e
  `relatorio_bugs.md`) e nomeia os 5 documentos de `docs/` que seguem
  desatualizados.

Nenhuma mudança de código nesta revisão — só documentação.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>

### Arquivos Modificados (1 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |

### Funcionalidades Impactadas

- Documentação Técnica

### Correções Realizadas

- Nenhuma referência a achado (`B-X00` / `RD-00`) identificada neste commit.

### Verificações Recomendadas

- Nenhuma verificação manual específica disparada pelos caminhos tocados.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Revisar consistência com os outros documentos de `docs/`.
- Verificar cada afirmação de estado contra o código, não contra a revisão anterior.

---

## Commit `94873ec` — 2026-08-24 12:11:30

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🚀 Nova Funcionalidade (`feat`) |
| **Hash Completo** | `94873ec8c368bd4e3d7ec4337ac02da7fbf5eafe` |
| **Arquivos Alterados** | 54 arquivo(s) |
| **Linhas** | +15076 / −834 |

### Título do Commit

```
feat(admin): BLOCO O — Home enxuta, Configurações do Cliente, categorias e templates editáveis
```

### Descrição

Implementa as 4 fases do BLOCO O do plano de implementação ("Planta do
Dashboard") e corrige 12 defeitos encontrados ao verificar a entrega por
execução real da aplicação — não só por leitura de código.

O.1 — Home enxuta + deep-link de mensagens
- `/private/admin` deixa de ser a tela de trabalho de cards: vira resumo
  com 4 KPIs, fila de sub-usuários, prévia de mensagens não lidas e lista
  rápida de empresas com "Configurar →".
- Novo `GET /dashboard/status-summary`: uma única query agregada por
  status, no lugar de buscar todos os cards de todas as empresas para
  somar no cliente (`listAllCardsAction` removida, sem consumidor).
- Deep-link `/private/admin/mensagens?empresa=&conversa=` rola até a
  mensagem e a destaca por alguns segundos.

O.2 — Aba única "Configurações do Cliente"
- `/private/admin/empresas/[id]` com casca de abas Perfil / Dashboard &
  Template / Usuários / Auditoria; a raiz redireciona para Perfil.
- `GET /admin/audits` ganha `company_id` opcional, filtrando pelos
  membros da empresa (principal + sub-usuários), já que `Audit` só tem
  `client_user_id`. `_member_user_ids` vira público (`member_user_ids`).

O.3 — Categoria como entidade (migration 4f2b8e6a91d3)
- Nova tabela `dashboard_card_categories`; `category_id` em
  `dashboard_cards`/`dashboard_template_cards`, mais
  `origin_template_card_id` e `hidden` em `dashboard_cards`.
- `tag` é preservada como campo histórico e mantida em sincronia com o
  nome da categoria em todo caminho de escrita (segue NOT NULL).
- Backfill cria 1 categoria por valor distinto de `tag` ainda não coberto
  pelas 4 canônicas, sem adivinhar agrupamentos.

O.4 — Editor de templates + aplicação/edição em massa
- `/private/admin/templates`: CRUD de template e de card de template.
- `POST /dashboard/companies/{id}/apply-template` idempotente — cria só o
  que falta (comparando por `origin_template_card_id`), nunca sobrescreve;
  sinaliza os cards que divergem do template.
- `PATCH /dashboard/companies/{id}/cards/bulk`: hide / unhide /
  set_category / remove / restore_from_template, com filtro por
  `dashboard_id` para nunca tocar em card de outra empresa.
- CRUD de categorias em `/admin/dashboard-categories`, com exclusão
  bloqueada (409) enquanto houver card usando a categoria.

Correções aplicadas na verificação (detalhe bug a bug em O.6 do plano)

Backend (7): `or 0` dentro de `select(...)` e `in_use + -(...)` no lugar
de `+=` em `delete_category` (TypeError em toda exclusão); `db.delete` /
`db.flush` inalcançáveis dentro do `if` após o `raise` em
`delete_template` (respondia 204 sem excluir); filtro por relationship
`origin_template_card` em vez da coluna FK (NotImplementedError);
`template_cards.id` no lugar de `template_card.id`; kwarg `_category_id=`;
`card.hidden == False` em vez de atribuição no `unhide` — falha silenciosa
que reportava sucesso sem reexibir nada; `name=payload.name` ausente no
PATCH de categoria.

Frontend (4): `"use client"` faltando em `perfil-client.tsx` (quebrava o
build); URL `/api/v1/bashboard/...` derrubando toda a edição em massa com
404; `listCardsForCompanyAction` sem `include_hidden`, deixando "Mostrar
cards ocultos" sem efeito; `LayoutProps<".../empresa/[id]">` sem o "s".

Migration (1): dois docstrings de módulo em sequência empurravam
`from __future__ import annotations` para fora do início do arquivo →
SyntaxError que impedia qualquer comando Alembic. Não foi pego pela suíte
porque `conftest.py` cria o schema com `Base.metadata.create_all`, nunca
por migration (gap já previsto em O.5.8). O arquivo também foi renomeado
para casar com o `revision` declarado (`4f2b8e6a91d3`), evitando repetir
o incidente de I.5.

Regressão revertida: `sub_user_emails` havia sido removido de
`CompanyAdminListItem`/`_to_list_item`, mas seguia consumido pela lista de
empresas, pela aba Usuários e por `test_get_company_detail_counts`.

Higiene: `AdminDshboardClient` → `AdminDashboardClient`;
`rejectingRequestId` voltando a `null` (botão preso em "Recusando..."
após falha); deps do `useEffect` de destaque; comentário solto removido
de `user-menu.tsx`.

Testes e validação
- `pytest -q` → 128 passed (era 6 failed, 122 passed); 12 testes novos em
  `test_dashboard_categories.py`, `test_dashboard_templates.py`,
  `test_dashboard_card_categories_migration.py` e `test_dashboard_cards.py`.
- `ruff check app` limpo; `alembic heads` com 1 único head.
- Migration aplicada ao MySQL 8.4 de desenvolvimento e validada pelos 2
  SELECT da checklist de O.3: 11 categorias e 0 linhas com `tag`
  preenchida e `category_id IS NULL`.
- Frontend: `tsc --noEmit`, `eslint .` e `npm run build` limpos, com as 5
  rotas novas geradas.
- Aplicação executada (uvicorn + next start): 10 telas do admin em 200;
  status-summary batendo com COUNT(*); hide/unhide/include_hidden e o 422
  de `set_category` sem categoria conferidos por HTTP; CRUD de template
  com round-trip completo (excluído → 404; padrão → 409); idempotência do
  apply-template (`created_count=0` na 2ª aplicação) e isolamento por
  empresa na edição em massa verificados contra o MySQL real em transação
  com rollback; filtro `company_id` de auditorias (7 → 2) e os deep-links
  de mensagens e auditorias funcionando.

Docs: plano em v5.17 com O.1–O.4 marcados como concluídos e a nova seção
O.6; `relatorio_bugs.md` em rev. 7.0 com o registro dos 12 achados.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>

### Arquivos Modificados (54 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Adicionado | `backend/alembic/versions/4f2b8e6a91d3_add_dashboard_card_categories.py` | Banco de Dados / Migrações |
| Modificado | `backend/app/api/v1/admin.py` | Auditorias (Admin) |
| Modificado | `backend/app/api/v1/dashboard_cards.py` | Dashboard Gerencial / Cards |
| Adicionado | `backend/app/api/v1/dashboard_categories.py` | Categorias de Card |
| Adicionado | `backend/app/api/v1/dashboard_templates.py` | Templates de Dashboard |
| Modificado | `backend/app/api/v1/router.py` | Roteamento da API |
| Modificado | `backend/app/models/__init__.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/company_dashboard.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/schemas/dashboard_runtime.py` | Schemas / Validação de Dados |
| Adicionado | `backend/app/schemas/dashboard_templates.py` | Schemas / Validação de Dados |
| Modificado | `backend/app/services/company_admin.py` | Serviços / Lógica de Negócio |
| Modificado | `backend/app/services/dashboard_builder.py` | Serviços / Lógica de Negócio |
| Adicionado | `backend/app/services/dashboard_template_admin.py` | Serviços / Lógica de Negócio |
| Modificado | `backend/scripts/seed_dashboard_templates.py` | Scripts de Inicialização / Seeds |
| Modificado | `backend/tests/test_admin_audits.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_dashboard_card_categories_migration.py` | Testes Automatizados (pytest) |
| Modificado | `backend/tests/test_dashboard_cards.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_dashboard_categories.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_dashboard_templates.py` | Testes Automatizados (pytest) |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |
| Modificado | `docs/relatorio_bugs.md` | Documentação Técnica |
| Modificado | `frontend/app/private/_components/user-menu.tsx` | Componentes Privados (Frontend) |
| Modificado | `frontend/app/private/admin/actions.ts` | Home do Admin (Frontend) |
| Modificado | `frontend/app/private/admin/admin-dashboard-client.tsx` | Home do Admin (Frontend) |
| Modificado | `frontend/app/private/admin/auditorias/page.tsx` | Gestão de Auditorias (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/_components/company-tabs-nav.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/auditoria/actions.ts` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/auditoria/error.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/auditoria/loading.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/auditoria/page.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/dashboard/actions.ts` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/dashboard/company-dashboard-client.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/dashboard/error.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/dashboard/loading.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/dashboard/page.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/layout.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/page.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/perfil/error.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/perfil/loading.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/perfil/page.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/perfil/perfil-client.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/usuarios/error.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/usuarios/loading.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/usuarios/page.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/[id]/usuarios/usuarios-client.tsx` | Gestão de Empresas (Frontend) |
| Modificado | `frontend/app/private/admin/empresas/empresas-client.tsx` | Gestão de Empresas (Frontend) |
| Modificado | `frontend/app/private/admin/mensagens/mensagens-client.tsx` | Mensagens Gerais (Frontend Admin) |
| Modificado | `frontend/app/private/admin/mensagens/page.tsx` | Mensagens Gerais (Frontend Admin) |
| Modificado | `frontend/app/private/admin/page.tsx` | Home do Admin (Frontend) |
| Adicionado | `frontend/app/private/admin/templates/actions.ts` | Editor de Templates (Frontend) |
| Adicionado | `frontend/app/private/admin/templates/error.tsx` | Editor de Templates (Frontend) |
| Adicionado | `frontend/app/private/admin/templates/loading.tsx` | Editor de Templates (Frontend) |
| Adicionado | `frontend/app/private/admin/templates/page.tsx` | Editor de Templates (Frontend) |
| Adicionado | `frontend/app/private/admin/templates/templates-client.tsx` | Editor de Templates (Frontend) |

### Funcionalidades Impactadas

- Auditorias (Admin)
- Banco de Dados / Migrações
- Categorias de Card
- Componentes Privados (Frontend)
- Dashboard Gerencial / Cards
- Documentação Técnica
- Editor de Templates (Frontend)
- Gestão de Auditorias (Frontend)
- Gestão de Empresas (Frontend)
- Home do Admin (Frontend)
- Mensagens Gerais (Frontend Admin)
- Modelos de Dados (ORM)
- Roteamento da API
- Schemas / Validação de Dados
- Scripts de Inicialização / Seeds
- Serviços / Lógica de Negócio
- Templates de Dashboard
- Testes Automatizados (pytest)

### Correções Realizadas

- Nenhuma referência a achado (`B-X00` / `RD-00`) identificada neste commit.

### Verificações Recomendadas

- ⚠️ **Migration alterada.** A suíte usa `Base.metadata.create_all` e **não** executa migrations (ver M-18 em `docs/relatorio_melhorias.md`) — uma suíte verde não prova que a migration roda. Execute `alembic upgrade head` contra o MySQL real e confirme `alembic heads` com um único head.
- ⚠️ **Endpoint alterado.** Confirme a dependência de autorização: posse (`_get_*_with_access`) não é permissão. Ver **B-A23** em `docs/relatorio_bugs.md`.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Adicionar testes automatizados para a nova funcionalidade.
- Exercitar os endpoints novos FORA do caminho que a UI percorre — os 4 achados de prioridade Alta de 2026-08-24 só apareceram assim (ver `docs/relatorio_bugs.md`).
- Atualizar `docs/relatorio_funcionalidades.md` se a feature ficou completa.
- Verificar dependências com itens pendentes em `docs/roadmap.md`.

---

## Commit `94d0223` — 2026-08-17 16:01:45

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 📝 Documentação (`docs`) |
| **Hash Completo** | `94d0223bd1991dd18a9f1ae354264d2789f786c2` |
| **Arquivos Alterados** | 12 arquivo(s) |
| **Linhas** | +414 / −187 |

### Título do Commit

```
docs: documenta N.1-N.3 retroativamente e sincroniza toda a pasta docs/
```

### Descrição

Executados os prompts de análise de projeto e atualização do plano de
implementação. HEAD analisado: 73444bd (5 commits à frente do último
estado documentado, 0398570).

plano_implementacao.md (v5.14 -> v5.15):
- 3 secoes novas, documentadas retroativamente (implementadas e
  commitadas antes desta revisao, mas sem secao propria ate agora):
  - N.1 (bf92636): status NAOCONFORME unificado entre AuditControl e
    DashboardCard (fecha B-M20), PATCH /admin/audit-controls/{id}/status,
    modulo frontend/lib/control-status.ts, redesign do UserMenu.
    Corrigida uma imprecisao da mensagem de commit original: a migration
    c2a7e6f1b8d3 menciona 'Postgres', mas o banco do projeto e MySQL
    (confirmado em backend/.env.example).
  - N.2 (3ce11a6): segmented control de status no Dashboard Admin
    (CONTROL_STATUS_ORDER/controlStatusButtonClass) + correcao de B-B12
    (logout-button.tsx: router.push -> window.location.href).
  - N.3 (04769c7): company_name via outerjoin em
    GET /sub-users/requests/pending, POST /sub-users/requests/{id}/reject,
    historico de solicitacoes no dashboard do cliente.
- Cabecalho de versao, HEAD e tabela de status atualizados (3 linhas
  novas: N.1/N.2/N.3); changelog de versao 5.15 adicionado.

Demais documentos de docs/ (11 arquivos) sincronizados com o estado
real do codigo em HEAD 73444bd:
- relatorio_geral.md (rev 5.0 -> 6.0): secoes 6.3/6.5/6.6 atualizadas,
  nova secao 6.7 (Gestao de Empresas), enums/migrations/scripts
  corrigidos, contagem de testes por arquivo reverificada por execucao
  real (python -m pytest -q -> 102 passed, 11 arquivos de teste).
- relatorio_funcionalidades.md (rev 5.0 -> 6.0): linha do tempo com os
  5 commits novos, F56-F61 adicionados, P06 movido para concluido
  (absorvido por F56), contadores corrigidos (55->61 concluidas,
  73 mapeadas no total).
- relatorio_bugs.md (rev 5.0 -> 6.0): confirma B-M20/B-B12 corrigidos,
  nenhum bug novo encontrado em M.1/M.2/N.1-N.3.
- roadmap.md (v4.0 -> v5.0): Fase 4 25% -> 35%, itens entregues fora
  do roadmap original (M.1/N.1-N.3) documentados separadamente.
- relatorio_melhorias.md, relatorio_documentacao.md: nota de
  sincronizacao e versao.
- index.md, dashboard_projeto.md: paineis central/executivo com
  metricas, HEAD e maturidade recalculados (~95% -> ~96%).
- executar_projeto.md, setup_completo.md: scripts novos
  (seed_demo_companies.py, seed_demo_audits.py), contagem de
  migrations corrigida (16, head 7e3f9c2b5a1d).
- backlog.md: nota de N.3/M.2 entregues fora do backlog original.

Nenhum documento novo criado nem removido nesta revisao — os 17
arquivos existentes ja cobriam a estrutura exigida. Nenhuma alteracao
de codigo-fonte; apenas docs/*.md.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (12 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `docs/backlog.md` | Documentação Técnica |
| Modificado | `docs/dashboard_projeto.md` | Documentação Técnica |
| Modificado | `docs/executar_projeto.md` | Documentação Técnica |
| Modificado | `docs/index.md` | Documentação Técnica |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |
| Modificado | `docs/relatorio_bugs.md` | Documentação Técnica |
| Modificado | `docs/relatorio_documentacao.md` | Documentação Técnica |
| Modificado | `docs/relatorio_funcionalidades.md` | Documentação Técnica |
| Modificado | `docs/relatorio_geral.md` | Documentação Técnica |
| Modificado | `docs/relatorio_melhorias.md` | Documentação Técnica |
| Modificado | `docs/roadmap.md` | Documentação Técnica |
| Modificado | `docs/setup_completo.md` | Documentação Técnica |

### Funcionalidades Impactadas

- Documentação Técnica

### Correções Realizadas

- Referências detectadas: **B-B12, B-M20**
  - Consulte `docs/relatorio_bugs.md` para o detalhamento de cada item.

### Verificações Recomendadas

- Nenhuma verificação manual específica disparada pelos caminhos tocados.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Revisar consistência com os outros documentos de `docs/`.
- Verificar cada afirmação de estado contra o código, não contra a revisão anterior.

---

## Commit `73444bd` — 2026-08-17 15:08:08

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🚀 Nova Funcionalidade (`feat`) |
| **Hash Completo** | `73444bd21b34219dd6efa5bd2d03253e5f971e16` |
| **Arquivos Alterados** | 25 arquivo(s) |
| **Linhas** | +1535 / −19 |

### Título do Commit

```
feat(admin): chat de controle, badges de nao lidas e dados demo
```

### Descrição

Conversa/Duvidas por controle (admin):
- Novo campo Message.read_at (nullable, indexado) + migration Alembic
  7e3f9c2b5a1d (add_messages_read_at).
- POST /admin/audit-controls/{id}/messages: admin responde a um
  controle (mesma tabela `messages` ja usada pelo cliente).
- PATCH /admin/audit-controls/{id}/messages/read: marca como lidas as
  mensagens do cliente/sub-usuario num controle.
- GET /admin/messages/unread-count: total global de nao lidas (chat de
  controle) para o badge do menu.
- audit_reporting.load_audit_report_data agora tambem carrega as
  mensagens de cada controle (mesma tecnica anti-N+1 das evidencias).
- auditorias-client.tsx: UI de conversa expansivel por controle
  (listar mensagens, responder, marcar como lida ao abrir).

Badge de nao lidas no menu do admin:
- GET /companies/unread-count (admin-only): agrega nao lidas do chat
  geral por empresa.
- UserMenu passa a exibir badges em "Auditorias" e "Mensagens", com
  polling a cada 45s e contagem inicial vinda do layout (Server
  Component).

Empresas (admin):
- CompanyAdminData/CompanyAdminListItem ganham sub_user_emails; tabela
  de empresas agora lista os e-mails dos sub-usuarios em vez de so a
  contagem, com coluna de acoes fixa (sticky) ao rolar a tabela.
- Botoes de exclusao padronizados nas novas classes utilitarias
  .btn-danger / .btn-danger-outline (globals.css), com title/aria-label
  descrevendo a acao irreversivel.

Dados de demonstracao:
- seed_catalog.py: adiciona 5 controles ISO/IEC 27001:2022 Anexo A
  (5.7, 5.23, 6.3, 7.4, 8.8) no mesmo tema do dashboard.
- scripts/seed_demo_companies.py (novo): 5 empresas ficticias com
  principal + 2 sub-usuarios, dashboards com 9 cards, notas, checklist,
  historico e mensagens.
- scripts/seed_demo_audits.py (novo): para cada empresa criada acima,
  gera auditorias com todos os controles do catalogo, status variado,
  evidencias em PDF reais (uploads/) e mensagens de chat nos itens
  nao conformes. Depende de seed_demo_companies.py ja ter rodado.
- backend/uploads/ (PDFs gerados pelo seed) adicionado ao
  backend/.gitignore — artefato de runtime, nao versionado.

Testes:
- test_admin_audit_management.py: cobre envio/leitura de mensagens do
  admin e o endpoint de contagem de nao lidas.
- test_company_messages.py: cobre GET /companies/unread-count.
- test_admin_companies.py: cobre sub_user_emails na listagem.

docs/plano_implementacao.md atualizado com o registro das propostas
implementadas (chat de controle, badges, empresas, dados demo).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (25 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `backend/.gitignore` | Outro / Não Categorizado |
| Adicionado | `backend/alembic/versions/7e3f9c2b5a1d_add_messages_read_at.py` | Banco de Dados / Migrações |
| Modificado | `backend/app/api/v1/admin.py` | Auditorias (Admin) |
| Modificado | `backend/app/api/v1/companies.py` | Gestão de Empresas (Admin) |
| Modificado | `backend/app/api/v1/company_messages.py` | Mensagens Gerais (Admin↔Cliente) |
| Modificado | `backend/app/models/message.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/schemas/admin.py` | Schemas / Validação de Dados |
| Modificado | `backend/app/schemas/company_admin.py` | Schemas / Validação de Dados |
| Modificado | `backend/app/services/audit_reporting.py` | Serviços / Lógica de Negócio |
| Modificado | `backend/app/services/company_admin.py` | Serviços / Lógica de Negócio |
| Modificado | `backend/scripts/seed_catalog.py` | Scripts de Inicialização / Seeds |
| Adicionado | `backend/scripts/seed_demo_audits.py` | Scripts de Inicialização / Seeds |
| Adicionado | `backend/scripts/seed_demo_companies.py` | Scripts de Inicialização / Seeds |
| Modificado | `backend/tests/test_admin_audit_management.py` | Testes Automatizados (pytest) |
| Modificado | `backend/tests/test_admin_companies.py` | Testes Automatizados (pytest) |
| Modificado | `backend/tests/test_company_messages.py` | Testes Automatizados (pytest) |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |
| Modificado | `frontend/app/globals.css` | Design System (Frontend) |
| Modificado | `frontend/app/private/_components/user-menu.tsx` | Componentes Privados (Frontend) |
| Modificado | `frontend/app/private/admin/actions.ts` | Home do Admin (Frontend) |
| Modificado | `frontend/app/private/admin/auditorias/actions.ts` | Gestão de Auditorias (Frontend) |
| Modificado | `frontend/app/private/admin/auditorias/auditorias-client.tsx` | Gestão de Auditorias (Frontend) |
| Modificado | `frontend/app/private/admin/empresas/actions.ts` | Gestão de Empresas (Frontend) |
| Modificado | `frontend/app/private/admin/empresas/empresas-client.tsx` | Gestão de Empresas (Frontend) |
| Modificado | `frontend/app/private/layout.tsx` | Layout Privado (Frontend) |

### Funcionalidades Impactadas

- Auditorias (Admin)
- Banco de Dados / Migrações
- Componentes Privados (Frontend)
- Design System (Frontend)
- Documentação Técnica
- Gestão de Auditorias (Frontend)
- Gestão de Empresas (Admin)
- Gestão de Empresas (Frontend)
- Home do Admin (Frontend)
- Layout Privado (Frontend)
- Mensagens Gerais (Admin↔Cliente)
- Modelos de Dados (ORM)
- Outro / Não Categorizado
- Schemas / Validação de Dados
- Scripts de Inicialização / Seeds
- Serviços / Lógica de Negócio
- Testes Automatizados (pytest)

### Correções Realizadas

- Nenhuma referência a achado (`B-X00` / `RD-00`) identificada neste commit.

### Verificações Recomendadas

- ⚠️ **Migration alterada.** A suíte usa `Base.metadata.create_all` e **não** executa migrations (ver M-18 em `docs/relatorio_melhorias.md`) — uma suíte verde não prova que a migration roda. Execute `alembic upgrade head` contra o MySQL real e confirme `alembic heads` com um único head.
- ⚠️ **Endpoint alterado.** Confirme a dependência de autorização: posse (`_get_*_with_access`) não é permissão. Ver **B-A23** em `docs/relatorio_bugs.md`.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Adicionar testes automatizados para a nova funcionalidade.
- Exercitar os endpoints novos FORA do caminho que a UI percorre — os 4 achados de prioridade Alta de 2026-08-24 só apareceram assim (ver `docs/relatorio_bugs.md`).
- Atualizar `docs/relatorio_funcionalidades.md` se a feature ficou completa.
- Verificar dependências com itens pendentes em `docs/roadmap.md`.

---

## Commit `04769c7` — 2026-08-17 13:41:39

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🚀 Nova Funcionalidade (`feat`) |
| **Hash Completo** | `04769c7ba0193fb4d5054b52dcc66a61a22b78fe` |
| **Arquivos Alterados** | 8 arquivo(s) |
| **Linhas** | +371 / −24 |

### Título do Commit

```
feat(sub-users): empresa no admin, recusa de solicitacao e ajustes de UI no cliente
```

### Descrição

Backend:
- SubUserRequestPublic ganha campo opcional `company_name`, resolvido via
  outerjoin de SubUserRequest com Company (por principal_user_id) em
  GET /sub-users/requests/pending — o admin agora ve de qual empresa e
  cada solicitacao pendente, nao so nome/e-mail do solicitado.
- Novo endpoint POST /sub-users/requests/{id}/reject (admin), com o
  mesmo lock (with_for_update) e validacao de status ja usados em
  approve_request: marca REJECTED, grava processed_by_admin_id e
  processed_at; segunda tentativa numa solicitacao ja processada
  retorna 400, nao 500. Nao cria usuario nem envia e-mail — a recusa
  e sinalizada ao cliente dentro da propria plataforma.
- 5 testes novos em test_sub_users.py: company_name no join da listagem
  pendente, recusa com sucesso, recusa exige admin, dupla-recusa 400,
  e confirmacao de que o solicitante ve status REJECTED em /requests/me.

Frontend (admin):
- PendingSubUserRequest.company_name; card de cada solicitacao pendente
  exibe "Empresa: <nome>" (ou "Nao identificada").
- rejectSubUserRequestAction + botao "Recusar solicitacao" ao lado de
  "Aprovar solicitacao", com confirmacao (window.confirm, mesmo padrao
  de auditorias-client.tsx) e estado de loading proprio.

Frontend (cliente):
- listMySubUserRequestsAction (GET /sub-users/requests/me); page.tsx
  busca o historico de solicitacoes do usuario principal no
  server-side (so quando role === "user") e passa para o client
  component.
- client-dashboard-client.tsx exibe o historico de solicitacoes do
  cliente (pendente/aprovada/recusada), com destaque vermelho e
  mensagem explicita para as recusadas.
- Ajuste de UI: mensagem de sucesso/erro do envio e cada item do
  historico agora sao dispensaveis (botao "x" que fecha o aviso
  localmente, sem apagar o historico no backend); espacamento do card
  "Solicitar Sub-usuario" revisado (mt-6 entre secoes, gaps e margens
  internas consistentes com o resto do dashboard).

Verificacao: pytest tests/test_sub_users.py (9/9), tsc --noEmit e
eslint no frontend, todos limpos.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (8 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `backend/app/api/v1/sub_users.py` | Sub-usuários |
| Modificado | `backend/app/schemas/sub_user.py` | Schemas / Validação de Dados |
| Modificado | `backend/tests/test_sub_users.py` | Testes Automatizados (pytest) |
| Modificado | `frontend/app/private/admin/actions.ts` | Home do Admin (Frontend) |
| Modificado | `frontend/app/private/admin/admin-dashboard-client.tsx` | Home do Admin (Frontend) |
| Modificado | `frontend/app/private/client/actions.ts` | Dashboard Cliente (Frontend) |
| Modificado | `frontend/app/private/client/client-dashboard-client.tsx` | Dashboard Cliente (Frontend) |
| Modificado | `frontend/app/private/client/page.tsx` | Dashboard Cliente (Frontend) |

### Funcionalidades Impactadas

- Dashboard Cliente (Frontend)
- Home do Admin (Frontend)
- Schemas / Validação de Dados
- Sub-usuários
- Testes Automatizados (pytest)

### Correções Realizadas

- Nenhuma referência a achado (`B-X00` / `RD-00`) identificada neste commit.

### Verificações Recomendadas

- ⚠️ **Endpoint alterado.** Confirme a dependência de autorização: posse (`_get_*_with_access`) não é permissão. Ver **B-A23** em `docs/relatorio_bugs.md`.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Adicionar testes automatizados para a nova funcionalidade.
- Exercitar os endpoints novos FORA do caminho que a UI percorre — os 4 achados de prioridade Alta de 2026-08-24 só apareceram assim (ver `docs/relatorio_bugs.md`).
- Atualizar `docs/relatorio_funcionalidades.md` se a feature ficou completa.
- Verificar dependências com itens pendentes em `docs/roadmap.md`.

---

## Commit `3ce11a6` — 2026-08-17 13:11:22

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🚀 Nova Funcionalidade (`feat`) |
| **Hash Completo** | `3ce11a636f1622a5cb59aab2e5e5a8841e12451b` |
| **Arquivos Alterados** | 5 arquivo(s) |
| **Linhas** | +79 / −46 |

### Título do Commit

```
feat(admin): unifica selecao de status do Dashboard Admin e corrige B-B12
```

### Descrição

Fecha o trabalho pendente registrado em docs/backlog.md (itens 0.1, 0.2
e 1.4/7.7): unificacao visual do seletor de status de controle no
Dashboard Admin (ja estava no working tree, sem commit) + correcao do
logout para reload completo (B-B12).

Frontend
- frontend/lib/control-status.ts: novas exportacoes CONTROL_STATUS_ORDER
  e controlStatusButtonClass() - classes de um segmented control (estado
  ativo/inativo por status), na mesma familia de cor ja usada pelos
  badges (controlStatusBadgeClass) e pelo destaque de KPI
  (controlStatusAccentClass).
- frontend/app/private/admin/admin-dashboard-client.tsx: os 4 botoes
  fixos "Marcar Em analise/Parcial/Conforme/Nao conforme" viram um
  segmented control gerado a partir de CONTROL_STATUS_ORDER
  (controlStatusButtonClass), com aria-pressed no botao ativo; a lista
  de cards (`cards`) agora e atualizada em atualizarStatus() junto com
  o card selecionado, entao a mudanca de status reflete imediatamente
  na coluna da esquerda, sem esperar um refetch.
- frontend/app/private/_components/logout-button.tsx (B-B12): troca
  router.push("/public/login") por window.location.href - reload
  completo depois do POST /api/auth/logout, para descartar qualquer
  estado/cache de Server Component da sessao anterior (getCurrentUser()/
  getCurrentUserProfile(), memoizados por requisicao via cache() em
  lib/session.ts) em vez de reaproveitar numa navegacao client-side.
  Import de useRouter removido (sem mais uso no arquivo).

Docs
- docs/relatorio_bugs.md: B-B12 marcado corrigido, com a correcao
  aplicada registrada.
- docs/backlog.md: itens 0.1, 0.2, 1.4 e 7.7 marcados concluidos.

Validado por execucao real: npx tsc --noEmit / npx eslint / npm run
build (Next.js 16.2.6) -> limpos, mesmas rotas geradas de antes.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (5 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `docs/backlog.md` | Documentação Técnica |
| Modificado | `docs/relatorio_bugs.md` | Documentação Técnica |
| Modificado | `frontend/app/private/_components/logout-button.tsx` | Componentes Privados (Frontend) |
| Modificado | `frontend/app/private/admin/admin-dashboard-client.tsx` | Home do Admin (Frontend) |
| Modificado | `frontend/lib/control-status.ts` | Status de Controle (Frontend) |

### Funcionalidades Impactadas

- Componentes Privados (Frontend)
- Documentação Técnica
- Home do Admin (Frontend)
- Status de Controle (Frontend)

### Correções Realizadas

- Referências detectadas: **B-B12**
  - Consulte `docs/relatorio_bugs.md` para o detalhamento de cada item.

### Verificações Recomendadas

- Nenhuma verificação manual específica disparada pelos caminhos tocados.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Adicionar testes automatizados para a nova funcionalidade.
- Exercitar os endpoints novos FORA do caminho que a UI percorre — os 4 achados de prioridade Alta de 2026-08-24 só apareceram assim (ver `docs/relatorio_bugs.md`).
- Atualizar `docs/relatorio_funcionalidades.md` se a feature ficou completa.
- Verificar dependências com itens pendentes em `docs/roadmap.md`.

---

## Commit `82a46a8` — 2026-08-17 13:02:58

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🚀 Nova Funcionalidade (`feat`) |
| **Hash Completo** | `82a46a879da4028997bad7d1438bfff949a7b1b2` |
| **Arquivos Alterados** | 15 arquivo(s) |
| **Linhas** | +2690 / −7 |

### Título do Commit

```
feat(admin): CRUD de empresas com exclusao em cascata transacional
```

### Descrição

Novo modulo "Lista de Empresas" no painel admin (/private/admin/empresas):
listar/buscar/paginar, criar, editar e excluir empresa, com exclusao em
cascata transacional de tudo que depende dela (usuario principal,
sub-usuarios, auditorias, evidencias, mensagens, dashboard e chat geral).

Backend
- backend/app/services/company_admin.py (novo): list_companies_admin,
  get_company_admin_detail, update_company_admin e
  delete_company_cascade() - apaga em ordem explicita (solicitacoes de
  sub-usuario -> auditorias/controles/evidencias/mensagens -> empresa
  (cascata ORM para dashboard/cards/notas/checklist/historico/mensagens
  e chat geral) -> sub-usuarios -> usuario principal), tudo numa unica
  transacao. Nao depende so do ON DELETE CASCADE do MySQL: o SQLite dos
  testes nao aplica FK por padrao, e Audit/SubUserRequest nao tem FK
  direta para companies (Audit.client_user_id aponta para users.id).
- backend/app/models/company_dashboard.py / company_message.py: novas
  relationships Company.dashboard / Company.messages
  (cascade="all, delete-orphan") - sem migration, so ORM.
- backend/app/api/v1/companies.py (novo): GET /admin/companies
  (paginado + busca por empresa ou responsavel), GET/{id} (detalhe +
  contagens de impacto), PATCH/{id} (edicao, 409 se nome/e-mail
  duplicado), DELETE/{id} (exclusao em cascata, 409 se restar
  referencia nao prevista) - todos admin-only.
- Criacao reaproveita POST /onboarding/principal-user (ja existente),
  evitando duplicar a regra de negocio de onboarding (e-mail de
  credenciais, tratamento de e-mail duplicado/concorrente).
- backend/tests/test_admin_companies.py (novo, 12 testes): lista,
  busca, paginacao, detalhe, edicao (sucesso/409/403), exclusao
  (404/403/cascata completa - cria evidencia, mensagens de controle e
  gerais, nota/checklist/historico/mensagem de card e solicitacao de
  sub-usuario antes de excluir e confere que tudo some - e empresa sem
  dados dependentes).

Frontend
- frontend/app/private/admin/empresas/: page.tsx (Server Component),
  actions.ts (Server Actions), empresas-client.tsx (tabela com busca
  debounced + paginacao server-side, modal de criacao, modal de edicao
  e modal de exclusao que busca o impacto real via GET/{id} antes de
  liberar o botao, so habilitado apos checkbox de confirmacao
  explicito), loading.tsx, error.tsx.
- frontend/app/private/_components/user-menu.tsx: novo item de
  navegacao "Empresas" (admin, antes de "Auditorias").

Docs
- docs/plano_implementacao.md: novo BLOCO M / M.1, seguindo o padrao de
  10 secoes do documento (objetivo, arquitetura, arquivos impactados,
  codigo completo, local, passo a passo, banco de dados, APIs,
  frontend, testes), painel executivo e cabecalho de versao
  atualizados (v5.12 -> v5.13).
- docs/backlog.md: nota de entrega do BLOCO M e novo item de debito
  tecnico (7.9 - UI de criacao de empresa duplicada entre esta tela e
  o modal "Novo usuario" do Dashboard Admin, mantido sem alteracao
  nesta entrega por decisao consciente de nao mexer num arquivo
  historicamente fragil).

Validado por execucao real: pytest -q -> 89 passed (12 novos, 0
regressao); ruff check app -> limpo; tsc --noEmit / eslint / npm run
build (Next.js 16.2.6) -> limpos, com /private/admin/empresas listada
entre as rotas geradas.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (15 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Adicionado | `backend/app/api/v1/companies.py` | Gestão de Empresas (Admin) |
| Modificado | `backend/app/api/v1/router.py` | Roteamento da API |
| Modificado | `backend/app/models/company_dashboard.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/company_message.py` | Modelos de Dados (ORM) |
| Adicionado | `backend/app/schemas/company_admin.py` | Schemas / Validação de Dados |
| Adicionado | `backend/app/services/company_admin.py` | Serviços / Lógica de Negócio |
| Adicionado | `backend/tests/test_admin_companies.py` | Testes Automatizados (pytest) |
| Modificado | `docs/backlog.md` | Documentação Técnica |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |
| Modificado | `frontend/app/private/_components/user-menu.tsx` | Componentes Privados (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/actions.ts` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/empresas-client.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/error.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/loading.tsx` | Gestão de Empresas (Frontend) |
| Adicionado | `frontend/app/private/admin/empresas/page.tsx` | Gestão de Empresas (Frontend) |

### Funcionalidades Impactadas

- Componentes Privados (Frontend)
- Documentação Técnica
- Gestão de Empresas (Admin)
- Gestão de Empresas (Frontend)
- Modelos de Dados (ORM)
- Roteamento da API
- Schemas / Validação de Dados
- Serviços / Lógica de Negócio
- Testes Automatizados (pytest)

### Correções Realizadas

- Nenhuma referência a achado (`B-X00` / `RD-00`) identificada neste commit.

### Verificações Recomendadas

- ⚠️ **Endpoint alterado.** Confirme a dependência de autorização: posse (`_get_*_with_access`) não é permissão. Ver **B-A23** em `docs/relatorio_bugs.md`.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Adicionar testes automatizados para a nova funcionalidade.
- Exercitar os endpoints novos FORA do caminho que a UI percorre — os 4 achados de prioridade Alta de 2026-08-24 só apareceram assim (ver `docs/relatorio_bugs.md`).
- Atualizar `docs/relatorio_funcionalidades.md` se a feature ficou completa.
- Verificar dependências com itens pendentes em `docs/roadmap.md`.

---

## Commit `bf92636` — 2026-08-17 12:06:19

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🚀 Nova Funcionalidade (`feat`) |
| **Hash Completo** | `bf926364a0742cc48a55b89d645df29d4f5d7d31` |
| **Arquivos Alterados** | 32 arquivo(s) |
| **Linhas** | +1696 / −1113 |

### Título do Commit

```
feat(audit): unifica status de controle (NAOCONFORME) e refaz cabeçalho privado
```

### Descrição

Backend
- Adiciona status NAOCONFORME a AuditControlStatus (backend/app/models/audit_control.py),
  alinhando o domínio Audit/AuditControl ao domínio DashboardCard, que já expunha
  4 status ao cliente (bug B-M20 do relatorio_bugs.md).
- Nova migration c2a7e6f1b8d3 (add_naoconforme_to_audit_control_status) alterando o
  enum audit_control_status no Postgres.
- Novo endpoint PATCH /api/v1/admin/audit-controls/{id}/status
  (backend/app/api/v1/admin.py) para o admin marcar o status de um controle avaliado;
  retorna a auditoria completa (AuditDetailOut) para a tela atualizar sem 2ª chamada.
- Novo schema AuditControlStatusUpdate (backend/app/schemas/admin.py).
- Testes novos em test_admin_audit_management.py: atualização para NAOCONFORME e
  propagação para /api/v1/client/controls, 403 para não-admin, 404 para controle
  inexistente.
- Script utilitário one-off backend/scripts/backfill_company_cliente01.py: cria
  Company/Dashboard para cliente01@teste.com, usuário que existia antes do fluxo de
  onboarding e ficava sem empresa vinculada (404 em /api/v1/companies/me).

Frontend
- Novo módulo frontend/lib/control-status.ts: fonte única de labels/cores/ordem dos
  4 status de controle, reaproveitado pelos dashboards admin, auditorias e cliente
  (antes cada tela tinha seu próprio label/cor e divergia entre si).
- admin-dashboard-client.tsx e client-dashboard-client.tsx passam a usar esse módulo
  e ganham o card de KPI "Não conforme".
- auditorias-client.tsx: lista de controles agora exibe badge de status com o
  vocabulário unificado e um <select> para o admin alterar o status via
  updateControlStatusAction (nova action em admin/auditorias/actions.ts que chama o
  endpoint PATCH acima).
- client/page.tsx: tipo do status do controle inclui NAOCONFORME.
- UserMenu reescrito como <header> fixo com navegação com item ativo, avatar com
  iniciais e rótulo de papel (admin/cliente/sub-usuário); LogoutButton com novo
  estilo (borda + hover vermelho) mantendo o comportamento existente.

Documentação
- Novo docs/backlog.md: backlog único e acionável, consolidando relatorio_bugs.md,
  relatorio_funcionalidades.md, relatorio_melhorias.md e roadmap.md.
- Atualiza os relatórios (relatorio_bugs, relatorio_funcionalidades, relatorio_geral,
  relatorio_melhorias, relatorio_documentacao, roadmap, dashboard_projeto, index,
  executar_projeto, deploy_producao, setup_completo, automacao_commits,
  mindmeister_automacao, trello_automacao, plano_implementacao) para refletir o
  estado atual do projeto após o fechamento do BLOCO L.
- Adiciona Prompt_Analise_de_projeto.txt e Prompt_Atualizar_Plano_Implemetacao.txt
  (prompts usados para gerar as análises/atualizações de documentação acima).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (32 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Adicionado | `Prompt_Analise_de_projeto.txt` | Outro / Não Categorizado |
| Adicionado | `Prompt_Atualizar_Plano_Implemetacao.txt` | Outro / Não Categorizado |
| Adicionado | `backend/alembic/versions/c2a7e6f1b8d3_add_naoconforme_to_audit_control_status.py` | Banco de Dados / Migrações |
| Modificado | `backend/app/api/v1/admin.py` | Auditorias (Admin) |
| Modificado | `backend/app/models/audit_control.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/schemas/admin.py` | Schemas / Validação de Dados |
| Adicionado | `backend/scripts/backfill_company_cliente01.py` | Scripts de Inicialização / Seeds |
| Modificado | `backend/tests/test_admin_audit_management.py` | Testes Automatizados (pytest) |
| Modificado | `docs/automacao_commits.md` | Documentação Técnica |
| Adicionado | `docs/backlog.md` | Documentação Técnica |
| Modificado | `docs/dashboard_projeto.md` | Documentação Técnica |
| Modificado | `docs/deploy_producao.md` | Documentação Técnica |
| Modificado | `docs/executar_projeto.md` | Documentação Técnica |
| Modificado | `docs/index.md` | Documentação Técnica |
| Modificado | `docs/mindmeister_automacao.md` | Documentação Técnica |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |
| Modificado | `docs/relatorio_bugs.md` | Documentação Técnica |
| Modificado | `docs/relatorio_documentacao.md` | Documentação Técnica |
| Modificado | `docs/relatorio_funcionalidades.md` | Documentação Técnica |
| Modificado | `docs/relatorio_geral.md` | Documentação Técnica |
| Modificado | `docs/relatorio_melhorias.md` | Documentação Técnica |
| Modificado | `docs/roadmap.md` | Documentação Técnica |
| Modificado | `docs/setup_completo.md` | Documentação Técnica |
| Modificado | `docs/trello_automacao.md` | Documentação Técnica |
| Modificado | `frontend/app/private/_components/logout-button.tsx` | Componentes Privados (Frontend) |
| Modificado | `frontend/app/private/_components/user-menu.tsx` | Componentes Privados (Frontend) |
| Modificado | `frontend/app/private/admin/admin-dashboard-client.tsx` | Home do Admin (Frontend) |
| Modificado | `frontend/app/private/admin/auditorias/actions.ts` | Gestão de Auditorias (Frontend) |
| Modificado | `frontend/app/private/admin/auditorias/auditorias-client.tsx` | Gestão de Auditorias (Frontend) |
| Modificado | `frontend/app/private/client/client-dashboard-client.tsx` | Dashboard Cliente (Frontend) |
| Modificado | `frontend/app/private/client/page.tsx` | Dashboard Cliente (Frontend) |
| Adicionado | `frontend/lib/control-status.ts` | Status de Controle (Frontend) |

### Funcionalidades Impactadas

- Auditorias (Admin)
- Banco de Dados / Migrações
- Componentes Privados (Frontend)
- Dashboard Cliente (Frontend)
- Documentação Técnica
- Gestão de Auditorias (Frontend)
- Home do Admin (Frontend)
- Modelos de Dados (ORM)
- Outro / Não Categorizado
- Schemas / Validação de Dados
- Scripts de Inicialização / Seeds
- Status de Controle (Frontend)
- Testes Automatizados (pytest)

### Correções Realizadas

- Referências detectadas: **B-M20**
  - Consulte `docs/relatorio_bugs.md` para o detalhamento de cada item.

### Verificações Recomendadas

- ⚠️ **Migration alterada.** A suíte usa `Base.metadata.create_all` e **não** executa migrations (ver M-18 em `docs/relatorio_melhorias.md`) — uma suíte verde não prova que a migration roda. Execute `alembic upgrade head` contra o MySQL real e confirme `alembic heads` com um único head.
- ⚠️ **Endpoint alterado.** Confirme a dependência de autorização: posse (`_get_*_with_access`) não é permissão. Ver **B-A23** em `docs/relatorio_bugs.md`.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Adicionar testes automatizados para a nova funcionalidade.
- Exercitar os endpoints novos FORA do caminho que a UI percorre — os 4 achados de prioridade Alta de 2026-08-24 só apareceram assim (ver `docs/relatorio_bugs.md`).
- Atualizar `docs/relatorio_funcionalidades.md` se a feature ficou completa.
- Verificar dependências com itens pendentes em `docs/roadmap.md`.

---

## Commit `0398570` — 2026-08-17 10:40:10

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🐛 Correção de Bug (`fix`) |
| **Hash Completo** | `0398570f6e5acdb81fbaa38ae29925140679cfb9` |
| **Arquivos Alterados** | 15 arquivo(s) |
| **Linhas** | +1160 / −30 |

### Título do Commit

```
fix(fullstack): corrige BLOCO L (L.2/L.3/L.4) e sincroniza plano_implementacao.md
```

### Descrição

L.2 (Encerramento Formal de Auditoria), L.3 (Exportação de Relatório em
PDF) e L.4 (Download de Evidência pelo Admin) foram encontradas
implementadas no working tree, sem commit, a partir do código já
documentado em docs/plano_implementacao.md — mas a cópia para os
arquivos reais divergiu do plano em 10 pontos, todos bugs reais que
impediam o funcionamento. Todos corrigidos e validados por execução
real nesta revisão.

Bugs de backend corrigidos:
- audit_reporting.py::load_audit_report_data: `.order_by(Evidence.
  created_at.asc)` sem invocar o método (faltavam os `()`) — quebrava
  todo GET /admin/audits/{id} com 500 (SQLAlchemy ArgumentError).
- Mesma função: `controls = [...]`/`return AuditReportData(...)`
  indentados dentro do `if control_ids:` — uma auditoria sem nenhum
  AuditControl caía em None implícito (404 indevido).
- Dataclass renomeada de `AuditResportData` (typo) para `AuditReportData`,
  batendo com o nome usado em toda a documentação.
- admin.py::download_evidence: `db.get(evidence, evidence_id)` usava a
  variável local minúscula em vez da classe `Evidence` — NameError em
  toda chamada a GET /admin/evidences/{id}/download.
- schemas/admin.py::EvidenceAdminOut: campo `size_type` não batia com
  `EvidenceData.size_bytes` — ValidationError em qualquer auditoria com
  evidência. Corrigido para `size_bytes: int | None`.
- report_generator.py: `toMargin` (parâmetro inexistente) → `topMargin`;
  `styles["title"]`/`["normal"]` (KeyError, reportlab é case-sensitive)
  → `styles["Title"]`/`["Normal"]`; seção "Resumo por status" do PDF
  (já documentada) estava faltando — adicionada.

Bugs de frontend corrigidos:
- auditorias-client.tsx: `"use cliet"` → `"use client"` (typo que fazia
  o Next.js tratar o Client Component como Server Component, quebrando
  o build por uso de hooks).
- error.tsx: `{ degest?: string }` → `{ digest?: string }`.
- Os dois Route Handlers de proxy autenticado (relatório PDF, download
  de evidência) haviam sido criados em frontend/app/private/admin/...
  em vez de frontend/app/api/admin/... — o Next.js os servia em
  /private/admin/... em vez de /api/admin/..., que é o path que a UI e
  o RouteContext<> de cada arquivo esperavam. Movidos para
  frontend/app/api/admin/audits/[auditId]/report/route.ts e
  frontend/app/api/admin/evidences/[evidenceId]/download/route.ts,
  seguindo a convenção já usada por frontend/app/api/auth/*.

Validação:
- backend: `pytest -q tests/test_admin_audit_management.py` → 11 passed
  (0 antes da correção); `pytest -q` completo → 74 passed; `ruff check
  app` → limpo.
- frontend: `npm run build` (Next.js 16.2.6/Turbopack) → build de
  produção completo, com as 2 rotas de proxy e /private/admin/
  auditorias corretamente listadas; `npm run lint` → limpo.

docs/plano_implementacao.md atualizado (v5.11 → v5.12): L.2/L.3/L.4
passam de 🔴 Pendente para ✅ Concluído (BLOCO L fica 100% concluído,
L.1-L.4); nota de correção completa (10 bugs, bug a bug) adicionada no
topo de L.2; tabela de status por arquivo da seção 3 atualizada;
Painel executivo ganha as 3 linhas novas; corrigida também uma tag
`</details>` órfã pré-existente na seção L.1 (sem `<details><summary>`
de abertura correspondente) e aplicado o mesmo padrão de bloco
recolhível às novas seções L.2/L.3/L.4, agora ✅.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (15 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `backend/app/api/v1/admin.py` | Auditorias (Admin) |
| Modificado | `backend/app/schemas/admin.py` | Schemas / Validação de Dados |
| Adicionado | `backend/app/services/audit_reporting.py` | Serviços / Lógica de Negócio |
| Adicionado | `backend/app/services/report_generator.py` | Serviços / Lógica de Negócio |
| Modificado | `backend/app/services/storage.py` | Serviços / Lógica de Negócio |
| Modificado | `backend/requirements.txt` | Dependências Python |
| Adicionado | `backend/tests/test_admin_audit_management.py` | Testes Automatizados (pytest) |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |
| Adicionado | `frontend/app/api/admin/audits/[auditId]/report/route.ts` | Proxy de Binário (PDF/Evidência) |
| Adicionado | `frontend/app/api/admin/evidences/[evidenceId]/download/route.ts` | Proxy de Binário (PDF/Evidência) |
| Adicionado | `frontend/app/private/admin/auditorias/actions.ts` | Gestão de Auditorias (Frontend) |
| Adicionado | `frontend/app/private/admin/auditorias/auditorias-client.tsx` | Gestão de Auditorias (Frontend) |
| Adicionado | `frontend/app/private/admin/auditorias/error.tsx` | Gestão de Auditorias (Frontend) |
| Adicionado | `frontend/app/private/admin/auditorias/loading.tsx` | Gestão de Auditorias (Frontend) |
| Adicionado | `frontend/app/private/admin/auditorias/page.tsx` | Gestão de Auditorias (Frontend) |

### Funcionalidades Impactadas

- Auditorias (Admin)
- Dependências Python
- Documentação Técnica
- Gestão de Auditorias (Frontend)
- Proxy de Binário (PDF/Evidência)
- Schemas / Validação de Dados
- Serviços / Lógica de Negócio
- Testes Automatizados (pytest)

### Correções Realizadas

- Nenhuma referência a achado (`B-X00` / `RD-00`) identificada neste commit.

### Verificações Recomendadas

- ⚠️ **Endpoint alterado.** Confirme a dependência de autorização: posse (`_get_*_with_access`) não é permissão. Ver **B-A23** em `docs/relatorio_bugs.md`.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Verificar se o mesmo bug ocorre em contextos similares no código.
- Adicionar teste de regressão para garantir que o problema não retorne.
- Atualizar `docs/relatorio_bugs.md` marcando o achado como corrigido.

---

## Commit `a55f319` — 2026-08-13 14:38:31

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🐛 Correção de Bug (`fix`) |
| **Hash Completo** | `a55f3199c2e14736b11d51159d774d34a69bb7f8` |
| **Arquivos Alterados** | 18 arquivo(s) |
| **Linhas** | +1196 / −25 |

### Título do Commit

```
fix(fullstack): corrige L.1 (Chat/Mensagens Gerais Admin-Cliente) e regressão em D.7
```

### Descrição

Backend (8 bugs corrigidos):
- send_company_message: Depends(get_current_user) -> Depends(get_db) no
  parametro db; remove virgula que criava tupla de 1 elemento em company
- _to_out(): content=message -> content=message.content;
  create_at=message.create_at (atributo inexistente) -> created_at=message.created_at
- list_company_messages: db.scalar(...).all() -> db.scalars(...).all()
- count_unread_company_messages: db.scalars(stmt) sobre select(func.count(...))
  -> db.scalar(stmt)
- CompanyMessageOut (schema): create_at/is_form_admin -> created_at/is_from_admin
- mark_company_messages_as_read: variavel local Company (sombreava a classe
  importada) renomeada para company
- migration bf7239a52df8_add_company_messages.py: revision interno
  "b3f7a1c9d2e6" -> "bf7239a52df8", alinhado ao nome do arquivo

Frontend (6 bugs corrigidos):
- admin/mensagens/actions.ts: reescrito com as funcoes admin-especificas
  (listCompaniesWithUnreadAction/listCompanyMessagesAction/
  sendCompanyMessageAction/markCompanyMessagesAsReadAction/CompanyWithUnread)
  em vez da copia indevida do actions.ts do cliente
- admin/mensagens/mensagens-client.tsx: usa listCompanyMessagesAction (./actions)
  em vez de listCompaniesAction (../actions, lista de empresas); le
  message.is_from_admin
- admin/actions.ts: remove parametro selectedCompanyId nunca lido de
  listCompaniesAction
- client/mensagens/actions.ts e mensagens-client.tsx: create_at/is_form_admin
  -> created_at/is_from_admin, consistente com o schema corrigido
- _components/user-menu.tsx: corrige typo de rota (/auitorias -> /auditorias)
  e classe Tailwind (text-(color-dark) -> text-(--color-dark))
- client/mensagens/error.tsx: useEffect ganha array de dependencias [error]

Regressao critica revertida:
- client/actions.ts: restaura uploadEvidenceAction/listMessagesAction/
  sendMessageAction/tipo ChatMessage (D.7), removidos por engano durante
  a tentativa anterior de L.1, a partir do conteudo original do commit a24bae6

Validado por execucao real: pytest backend 63/63 (test_company_messages.py
8/8), ruff limpo, alembic heads com um unico head; frontend tsc --noEmit
0 erros, eslint limpo, next build completo sem erros.

docs/plano_implementacao.md atualizado (v5.11): L.1 e D.7 marcados como
Concluido, historico das duas verificacoes anteriores preservado em bloco
recolhivel para rastreabilidade.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (18 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Adicionado | `backend/alembic/versions/bf7239a52df8_add_company_messages.py` | Banco de Dados / Migrações |
| Adicionado | `backend/app/api/v1/company_messages.py` | Mensagens Gerais (Admin↔Cliente) |
| Adicionado | `backend/app/models/company_message.py` | Modelos de Dados (ORM) |
| Adicionado | `backend/app/schemas/company_message.py` | Schemas / Validação de Dados |
| Adicionado | `backend/tests/test_company_messages.py` | Testes Automatizados (pytest) |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |
| Modificado | `frontend/app/private/_components/user-menu.tsx` | Componentes Privados (Frontend) |
| Adicionado | `frontend/app/private/admin/mensagens/actions.ts` | Mensagens Gerais (Frontend Admin) |
| Adicionado | `frontend/app/private/admin/mensagens/error.tsx` | Mensagens Gerais (Frontend Admin) |
| Adicionado | `frontend/app/private/admin/mensagens/loading.tsx` | Mensagens Gerais (Frontend Admin) |
| Adicionado | `frontend/app/private/admin/mensagens/mensagens-client.tsx` | Mensagens Gerais (Frontend Admin) |
| Adicionado | `frontend/app/private/admin/mensagens/page.tsx` | Mensagens Gerais (Frontend Admin) |
| Modificado | `frontend/app/private/client/actions.ts` | Dashboard Cliente (Frontend) |
| Adicionado | `frontend/app/private/client/mensagens/actions.ts` | Mensagens Gerais (Frontend Cliente) |
| Adicionado | `frontend/app/private/client/mensagens/error.tsx` | Mensagens Gerais (Frontend Cliente) |
| Adicionado | `frontend/app/private/client/mensagens/loading.tsx` | Mensagens Gerais (Frontend Cliente) |
| Adicionado | `frontend/app/private/client/mensagens/mensagens-client.tsx` | Mensagens Gerais (Frontend Cliente) |
| Adicionado | `frontend/app/private/client/mensagens/page.tsx` | Mensagens Gerais (Frontend Cliente) |

### Funcionalidades Impactadas

- Banco de Dados / Migrações
- Componentes Privados (Frontend)
- Dashboard Cliente (Frontend)
- Documentação Técnica
- Mensagens Gerais (Admin↔Cliente)
- Mensagens Gerais (Frontend Admin)
- Mensagens Gerais (Frontend Cliente)
- Modelos de Dados (ORM)
- Schemas / Validação de Dados
- Testes Automatizados (pytest)

### Correções Realizadas

- Nenhuma referência a achado (`B-X00` / `RD-00`) identificada neste commit.

### Verificações Recomendadas

- ⚠️ **Migration alterada.** A suíte usa `Base.metadata.create_all` e **não** executa migrations (ver M-18 em `docs/relatorio_melhorias.md`) — uma suíte verde não prova que a migration roda. Execute `alembic upgrade head` contra o MySQL real e confirme `alembic heads` com um único head.
- ⚠️ **Endpoint alterado.** Confirme a dependência de autorização: posse (`_get_*_with_access`) não é permissão. Ver **B-A23** em `docs/relatorio_bugs.md`.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Verificar se o mesmo bug ocorre em contextos similares no código.
- Adicionar teste de regressão para garantir que o problema não retorne.
- Atualizar `docs/relatorio_bugs.md` marcando o achado como corrigido.

---

## Commit `d81e980` — 2026-08-13 14:18:20

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 📝 Documentação (`docs`) |
| **Hash Completo** | `d81e980cb46852c8ce5cbcb123e7f9e88576f778` |
| **Arquivos Alterados** | 1 arquivo(s) |
| **Linhas** | +50 / −29 |

### Título do Commit

```
docs: reverifica L.1 apos tentativa de correcao do usuario - continua quebrado, com regressao em D.7
```

### Descrição

Contexto: o usuario reportou ter implementado L.1 (Chat/Mensagens Gerais
Admin<->Cliente) com base na proposta documentada em plano_implementacao.md,
e pediu verificacao da corretude da implementacao encontrada no working
tree (nao commitada) antes de qualquer commit.

Processo de verificacao (leitura arquivo a arquivo + execucao real, sem
alterar codigo):

Backend (company_messages.py, schemas/company_message.py, migration
bf7239a52df8, test_company_messages.py) - comparado byte a byte com o
estado documentado em 2026-08-12: nenhuma alteracao. Os 8 bugs ja
catalogados continuam todos presentes (Depends(get_current_user) no lugar
de get_db, tupla acidental em send_company_message, _to_out() lendo
message.create_at/content=message, list_company_messages chamando
.all() em cima de db.scalar(), count_unread_count usando db.scalars()
sobre um select(func.count(...)), typos create_at/is_form_admin no
schema, revision divergente do nome do arquivo de migration).
`python -m pytest -q tests/test_company_messages.py` -> 3 failed, 5
passed (os mesmos 3 testes de antes). Suite completa -> 60 passed, 3
failed, identico a 2026-08-12. `ruff check app` limpo.

Frontend - os arquivos que faltavam em 2026-08-12 (painel do cliente
completo, mensagens-client.tsx/loading.tsx/error.tsx do admin, navegacao
em user-menu.tsx) foram criados, mas com bugs novos que impedem a
compilacao: `npx tsc --noEmit` acusa 14 erros. Entre eles: (1)
admin/mensagens/actions.ts foi preenchido com uma copia do actions.ts do
lado cliente, sem nenhuma das funcoes que o admin precisa
(listCompaniesWithUnreadAction, sendCompanyMessageAction, etc.); (2)
admin/mensagens/mensagens-client.tsx chama listCompaniesAction() (lista
de empresas) esperando receber mensagens da empresa selecionada; (3)
admin/actions.ts::listCompaniesAction ganhou um parametro nunca usado no
corpo, tentativa mal-sucedida de resolver o problema anterior; (4)
admin e cliente usam nomes de campo (is_form_admin/is_from_admin)
inconsistentes entre si; (5-6) user-menu.tsx com typo no href
("auitorias") e classe CSS "text-(color-dark)" sem o "--" (custom
property invalida).

Achado mais grave: client/actions.ts teve uploadEvidenceAction,
listMessagesAction, sendMessageAction e o tipo ChatMessage REMOVIDOS -
essas quatro definicoes pertencem a D.7 (upload de evidencia + chat por
controle), ja documentado como Concluido desde 2026-08-10.
client-dashboard-client.tsx e client/page.tsx continuam importando as
quatro, hoje inexistentes (6 dos 14 erros de tsc vem daqui). Ou seja: a
tentativa de implementar L.1 regrediu uma funcionalidade ja concluida e
usada em producao pelo dashboard do cliente.

Conclusao: nenhum dos 8 bugs de backend catalogados em 2026-08-12 foi
corrigido, e a parte nova de frontend nao compila e regride D.7. Nada em
L.1 pode ser marcado como concluido nesta revisao.

Alteracoes neste commit (somente documentacao, nenhum codigo):
- Versao do documento 5.9 -> 5.10, changelog e cabecalho atualizados.
- Novo paragrafo de atualizacao (2026-08-13) resumindo a reverificacao.
- Painel executivo: L.1 atualizado com o resultado da reverificacao;
  D.7 sinalizado com a regressao causada por L.1 (codigo original de D.7
  permanece correto - o dano esta em client/actions.ts).
- Secao L.1: bloco de achados reescrito, bugs 9-15 documentados (novos,
  frontend), nota cruzada adicionada na secao D.7, tabela de arquivos
  (secao 3) atualizada linha a linha para o estado real de 2026-08-13,
  com 2 linhas novas para os arquivos alterados fora do escopo original
  (client/actions.ts, admin/actions.ts). Secao 9 (impacto em
  funcionalidades existentes) atualizada para registrar que a premissa
  de "nenhuma alteracao em arquivo existente" da proposta original foi
  violada na pratica.

Seguindo o mesmo padrao do commit c3d1c6f (K.1 corrigido e commitado,
L.1 documentado mas mantido fora do commit por estar quebrado): a
tentativa de implementacao de L.1 (backend + frontend, 12 arquivos
novos + 3 alterados) permanece nao commitada no working tree, quebrada,
a espera de correcao dos bugs 1-15 listados no documento.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (1 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |

### Funcionalidades Impactadas

- Documentação Técnica

### Correções Realizadas

- Nenhuma referência a achado (`B-X00` / `RD-00`) identificada neste commit.

### Verificações Recomendadas

- Nenhuma verificação manual específica disparada pelos caminhos tocados.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Revisar consistência com os outros documentos de `docs/`.
- Verificar cada afirmação de estado contra o código, não contra a revisão anterior.

---

## Commit `c3d1c6f` — 2026-08-12 18:29:19

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 📝 Documentação (`docs`) |
| **Hash Completo** | `c3d1c6f61bfbe5897c7b898ef9f4dc054b1f0ae5` |
| **Arquivos Alterados** | 5 arquivo(s) |
| **Linhas** | +61 / −38 |

### Título do Commit

```
docs: atualiza plano_implementacao.md (K.1 confirmado; L.1 documentado como quebrado) e aplica fix de K.1
```

### Descrição

Leitura completa de backend/ e frontend/ para atualizar docs/plano_implementacao.md
com o estado real do working tree, sem alterar nenhuma funcionalidade:

- K.1 (POST /auth/login e /auth/refresh retornando 422 sob Python 3.14): o fix
  recomendado pelo plano (remover `from __future__ import annotations` de
  auth.py) já estava aplicado no working tree, fora desta conversa, sem commit.
  Validado nesta revisão: tests/test_auth.py 9/9, ruff check limpo. Item passa
  de 🔴 Pendente para ✅ Concluído no painel executivo e no BLOCO K.
  Inclui também as alterações associadas já presentes no working tree:
  router.py (registro do router de company_messages + limpeza de formatação),
  models/__init__.py e alembic/env.py (registro do model CompanyMessage).

- L.1 (Chat/Mensagens Gerais entre Admin e Cliente): encontrada uma tentativa
  de implementação da proposta do BLOCO L no working tree (backend completo +
  metade do frontend admin), sem commit e QUEBRADA — catalogados 8 bugs reais
  (DI trocada em send_company_message, tupla acidental, typos create_at/
  is_form_admin no schema, uso incorreto de db.scalar/db.scalars em 2 lugares,
  page.tsx do admin referenciando um componente que não existe, nome de
  migration divergente do revision). 3 de 8 testes de test_company_messages.py
  falham; o frontend não compila. A pedido do usuário, nada desse código foi
  alterado nesta revisão — apenas lido, executado e documentado como ⚠️
  Necessita correção no painel executivo e no BLOCO L, com cada bug descrito
  para uma correção futura. Os arquivos dessa tentativa (backend/app/api/v1/
  company_messages.py, backend/app/models/company_message.py, backend/app/
  schemas/company_message.py, backend/alembic/versions/bf7239a52df8_*.py,
  backend/tests/test_company_messages.py, frontend/app/private/admin/
  mensagens/) permanecem fora deste commit, sem alteração.

Suíte de testes no momento deste commit: 60 passed, 3 failed (os 3 são os de
test_company_messages.py, cobertos pela nota de L.1 acima).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (5 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `backend/alembic/env.py` | Banco de Dados / Migrações |
| Modificado | `backend/app/api/v1/auth.py` | Autenticação / Login |
| Modificado | `backend/app/api/v1/router.py` | Roteamento da API |
| Modificado | `backend/app/models/__init__.py` | Modelos de Dados (ORM) |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |

### Funcionalidades Impactadas

- Autenticação / Login
- Banco de Dados / Migrações
- Documentação Técnica
- Modelos de Dados (ORM)
- Roteamento da API

### Correções Realizadas

- Nenhuma referência a achado (`B-X00` / `RD-00`) identificada neste commit.

### Verificações Recomendadas

- ⚠️ **Endpoint alterado.** Confirme a dependência de autorização: posse (`_get_*_with_access`) não é permissão. Ver **B-A23** em `docs/relatorio_bugs.md`.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Revisar consistência com os outros documentos de `docs/`.
- Verificar cada afirmação de estado contra o código, não contra a revisão anterior.

---

## Commit `76f1417` — 2026-08-12 14:20:28

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 📝 Documentação (`docs`) |
| **Hash Completo** | `76f1417d1428e0faf6ea5f112518f147e2ecbb67` |
| **Arquivos Alterados** | 15 arquivo(s) |
| **Linhas** | +3980 / −488 |

### Título do Commit

```
docs: sincroniza documentação completa (13 blocos) e reescreve BLOCO L com código executável
```

### Descrição

Execução completa dos dois prompts de análise/atualização de documentação
(Prompt_Analise_de_projeto.txt, 13 blocos, e
Prompt_Atualizar_Plano_Implemetacao.txt), seguida da reescrita do BLOCO L
do plano de implementação a pedido explícito do usuário, elevando o
padrão de detalhamento a "código completo, sem omissões" para toda
proposta de nova funcionalidade.

## Achado crítico novo (documentado, não corrigido nesta revisão)

Ao reexecutar a suíte de testes (python -m pytest -q), 3 dos 55 testes
falharam — todos em test_auth.py. Causa raiz isolada com reprodução
mínima fora do projeto: `from __future__ import annotations` combinado
com o decorator `@limiter.limit(...)` (slowapi) quebra a leitura do corpo
JSON pelo FastAPI especificamente sob Python 3.14 — o único Python
disponível neste ambiente de desenvolvimento (.venv local), enquanto
backend/Dockerfile e ci.yml fixam Python 3.12. POST /auth/login e
POST /auth/refresh retornam 422 para toda requisição válida (login
completamente quebrado neste ambiente). Documentado como B-C22
(relatorio_bugs.md) e K.1 (plano_implementacao.md, com o arquivo auth.py
completo pós-correção) — fix de 1 linha identificado e validado, não
aplicado ao código de produção por estar fora do escopo desta revisão de
documentação. Não confirmado se produção/CI (Python 3.12) são afetados.

## Sincronização geral (13 blocos do Prompt_Analise_de_projeto.txt)

7 commits desde a última sincronização de docs (6b4f0a3..6595065)
fecharam 100% do BLOCO I (7/7 achados) e 100% do inventário de código
morto/órfão E.3 (9/9) — subsistema de checklist "clássico" removido via
DROP TABLE, repository pattern 100% conectado a 3 endpoints novos, typos
de nomenclatura corrigidos, infraestrutura Docker/CI implementada e
validada estaticamente. Atualizados com essas mudanças e com o achado
B-C22: relatorio_geral.md, relatorio_funcionalidades.md,
relatorio_bugs.md, relatorio_melhorias.md, roadmap.md,
relatorio_documentacao.md, index.md, dashboard_projeto.md,
setup_completo.md (+ aviso para fixar Python 3.12 no .venv local),
executar_projeto.md, deploy_producao.md, automacao_commits.md,
trello_automacao.md, mindmeister_automacao.md.

## BLOCO K e L reescritos (plano_implementacao.md v5.6 -> v5.8)

- K.1: arquivo auth.py completo pós-correção do achado B-C22 (a versão
  anterior mostrava só um diff com "..."), com explicação de por que o
  fix funciona e como se relaciona com o resto do sistema.
- K.2: documentação retroativa do fix de
  sub_user_requests.request_full_name (commit 6595065), que não tinha
  seção própria até esta revisão.
- BLOCO L reescrito por completo — a versão anterior (mesmo dia) tinha
  esboços incompletos (funções sem corpo real, "esboço" no título dos
  blocos de código) e 2 decisões técnicas deixadas em aberto. Antes de
  escrever qualquer código novo, leitura direta e completa do
  código-fonte relevante: dashboard_cards.py, admin.py, client.py,
  deps.py, router.py, models/schemas/repositories envolvidos,
  conftest.py e os testes existentes; no frontend server-backend.ts,
  session.ts, admin/actions.ts, admin-dashboard-client.tsx,
  client/actions.ts, user-menu.tsx, globals.css, e a documentação local
  do Next.js 16.2.6 (node_modules/next/dist/docs/) para confirmar a
  convenção de params assíncrono em Route Handlers em vez de presumir.

  Achado real durante a análise: o frontend não tem nenhuma tela que
  liste Audit/AuditControl/Evidence — o dashboard admin opera só sobre o
  domínio paralelo DashboardCard. L.2/L.3/L.4 passam a compartilhar uma
  tela nova (/private/admin/auditorias) e um serviço único de
  carregamento de dados (services/audit_reporting.py::
  load_audit_report_data), reaproveitado tanto pelo endpoint JSON quanto
  pela geração do PDF, para nunca divergirem.

  As 2 decisões que ficavam em aberto foram resolvidas com justificativa
  registrada: L.1 adota uma thread por empresa, não um inbox único
  (reaproveita o padrão de navegação já usado no dashboard admin); L.3
  adota reportlab em vez de weasyprint (evita dependências de sistema
  Cairo/Pango que inflariam a imagem Docker enxuta do BLOCO H).

  Código completo entregue para ~30 arquivos novos/alterados (19 para
  L.1 — chat assíncrono geral admin<->cliente por empresa; 11
  compartilhados entre L.2 — encerramento formal de auditoria, L.3 —
  exportação de relatório em PDF, L.4 — download de evidência pelo
  admin), cobrindo o fluxo completo Frontend -> Server Action -> API
  FastAPI -> Service -> Model -> Banco de Dados -> volta, com migrations,
  19 testes novos e uma tabela de diagnóstico por sintoma em cada
  proposta. Nenhuma funcionalidade foi implementada no código de
  produção — só documentada, como pedido.

Validação estrutural: 14 blocos de código Python (sintaxe verificada via
AST) e 18 blocos TypeScript (balanceamento de chaves/parênteses/
colchetes) do BLOCO L conferidos sem erros.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (15 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `docs/automacao_commits.md` | Documentação Técnica |
| Modificado | `docs/dashboard_projeto.md` | Documentação Técnica |
| Modificado | `docs/deploy_producao.md` | Documentação Técnica |
| Modificado | `docs/executar_projeto.md` | Documentação Técnica |
| Modificado | `docs/index.md` | Documentação Técnica |
| Modificado | `docs/mindmeister_automacao.md` | Documentação Técnica |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |
| Modificado | `docs/relatorio_bugs.md` | Documentação Técnica |
| Modificado | `docs/relatorio_documentacao.md` | Documentação Técnica |
| Modificado | `docs/relatorio_funcionalidades.md` | Documentação Técnica |
| Modificado | `docs/relatorio_geral.md` | Documentação Técnica |
| Modificado | `docs/relatorio_melhorias.md` | Documentação Técnica |
| Modificado | `docs/roadmap.md` | Documentação Técnica |
| Modificado | `docs/setup_completo.md` | Documentação Técnica |
| Modificado | `docs/trello_automacao.md` | Documentação Técnica |

### Funcionalidades Impactadas

- Documentação Técnica

### Correções Realizadas

- Referências detectadas: **B-C22**
  - Consulte `docs/relatorio_bugs.md` para o detalhamento de cada item.

### Verificações Recomendadas

- Nenhuma verificação manual específica disparada pelos caminhos tocados.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Revisar consistência com os outros documentos de `docs/`.
- Verificar cada afirmação de estado contra o código, não contra a revisão anterior.

---

## Commit `6595065` — 2026-08-12 12:04:23

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🐛 Correção de Bug (`fix`) |
| **Hash Completo** | `6595065ec6521ee1841aca0f9c797f262701faa1` |
| **Arquivos Alterados** | 1 arquivo(s) |
| **Linhas** | +60 / −0 |

### Título do Commit

```
fix(backend): corrige coluna sub_user_requests.request_full_name divergente do schema
```

### Descrição

Erro 500 em GET /api/v1/sub-users/requests/pending (tela /private/admin):
OperationalError 1054 - Unknown column 'sub_user_requests.requested_full_name'.

Causa raiz: a migration 447a4e1de59d (create_table de sub_user_requests)
foi reescrita depois de já ter sido aplicada neste banco local, trocando
o nome da coluna de 'request_full_name' para 'requested_full_name' para
alinhar com o model ORM, o schema Pydantic, o router e o frontend — mas
a reescrita da migration não alcança bancos que já rodaram a versão
antiga dela. O código inteiro (SubUserRequest, SubUserRequestPublic,
sub_users.py, actions.ts do frontend, testes) já usava
'requested_full_name'; só a coluna física do banco ficou para trás.

Adiciona nova migration f224a87de1a4 que renomeia
request_full_name -> requested_full_name via ALTER TABLE, guardada por
inspector (checa se a coluna antiga existe antes de agir), então é
no-op em bancos criados a partir da migration já corrigida. Aplicada e
validada neste ambiente: DESCRIBE confirma a coluna renomeada e o
SELECT do endpoint /requests/pending volta a executar sem erro.

Nenhuma alteração de código de aplicação foi necessária — o model, o
schema e o router já esperavam o nome correto.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (1 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Adicionado | `backend/alembic/versions/f224a87de1a4_fix_sub_user_requests_full_name_typo.py` | Banco de Dados / Migrações |

### Funcionalidades Impactadas

- Banco de Dados / Migrações

### Correções Realizadas

- Nenhuma referência a achado (`B-X00` / `RD-00`) identificada neste commit.

### Verificações Recomendadas

- ⚠️ **Migration alterada.** A suíte usa `Base.metadata.create_all` e **não** executa migrations (ver M-18 em `docs/relatorio_melhorias.md`) — uma suíte verde não prova que a migration roda. Execute `alembic upgrade head` contra o MySQL real e confirme `alembic heads` com um único head.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Verificar se o mesmo bug ocorre em contextos similares no código.
- Adicionar teste de regressão para garantir que o problema não retorne.
- Atualizar `docs/relatorio_bugs.md` marcando o achado como corrigido.

---

## Commit `20efbf9` — 2026-08-12 11:50:46

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🐛 Correção de Bug (`fix`) |
| **Hash Completo** | `20efbf9bb34b6183bc6335e9b454ff0172c82dc1` |
| **Arquivos Alterados** | 22 arquivo(s) |
| **Linhas** | +1222 / −184 |

### Título do Commit

```
fix(backend): fecha I.4/I.5/I.7 e resolve E.3 por completo (9/9)
```

### Descrição

Verificação e atualização de docs/plano_implementacao.md contra o estado
real do código/banco, seguida da implementação dos itens pendentes
encontrados no processo.

I.4 — IntegrityError no onboarding concorrente
- Já implementado no working tree (fora desta sessão, sem commit). O
  teste de regressão que a própria doc propunha não exercitava o branch
  novo (uma chamada dupla sequencial cai no pre-check existente, não no
  except IntegrityError). Substituído por um teste com monkeypatch que
  neutraliza o pre-check e força o IntegrityError de verdade.

I.5 — Índices de dashboard_card_history_entries/dashboard_card_messages
- Migration eafa65e9df05 já existia, com revision = "<gerado pelo
  alembic>" (placeholder nunca preenchido) e já aplicada ao MySQL de dev
  com esse valor, quebrando alembic_version para qualquer migration
  futura. Corrigidos o arquivo e o banco (UPDATE alembic_version).

I.7 — frontend/app/api/profile/route.ts
- Rota já removida uma vez pelo I.2 havia reaparecido no working tree
  sem consumidor e sem commit. Removida de novo, com confirmação do
  usuário (tsc/eslint limpos). Sem diff neste commit por nunca ter sido
  rastreada pelo Git.

E.10 — Remove subsistema de checklist "clássico" (checklistItem/
checklistItemState)
- Nenhum endpoint HTTP jamais o consumiu; substituído na prática por
  DashboardCardchecklistItem. checklist_item_state tinha 0 linhas,
  checklist_items só as 7 do seed.
- Models, relationships (ControlCatalog.checklist_items,
  AuditControl.checklist_state), import em alembic/env.py e a seed em
  scripts/seed_catalog.py removidos.
- Migration 0ba953b10f8b (DROP TABLE) aplicada ao MySQL de dev, com
  confirmação explícita do usuário. Corrigidos 2 bugs só visíveis contra
  MySQL real: import hardcoded em env.py e DROP INDEX explícito que o
  InnoDB recusa por sustentar FK (upgrade() simplificado para só
  DROP TABLE).

E.11 — Conecta AuditRepository/UserRepository a consumidores reais
- UserRepository.get_by_id substitui db.get(User, ...) em
  get_current_user(), POST /auth/refresh e approve_request() de
  sub-usuário.
- Endpoints novos: GET /admin/users?role=, GET /client/audits e
  GET /client/audits/{id} (a "tela de minhas auditorias" cogitada desde
  o E.1). 11 testes novos.

E.12 — Corrige typos evidences.create_at / tabela messagens
- Evidence.create_at -> created_at; Message.__tablename__ "messagens" ->
  "messages". Migration 83cf1e14efa8 (ALTER + RENAME TABLE + RENAME
  INDEX) aplicada ao MySQL de dev; ambas as tabelas estavam vazias.

Resultado: E.3 (código morto/órfão do backend) fecha 9/9 — todos os
achados do inventário têm hoje uma decisão implementada e testada.
Suíte completa: 55 passed (era 43 no início desta sessão). ruff check
limpo. docs/plano_implementacao.md atualizado (v5.3 -> v5.6) com o
detalhamento de cada item, seções E.10/E.11/E.12 no padrão de 10 partes
já usado no documento, e tabelas executiva/prioridade sincronizadas.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (22 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `backend/alembic/env.py` | Banco de Dados / Migrações |
| Adicionado | `backend/alembic/versions/0ba953b10f8b_drop_classic_checklist_subsystem.py` | Banco de Dados / Migrações |
| Adicionado | `backend/alembic/versions/83cf1e14efa8_fix_evidences_and_messages_naming_typos.py` | Banco de Dados / Migrações |
| Adicionado | `backend/alembic/versions/eafa65e9df05_restore_dashboard_card_indices.py` | Banco de Dados / Migrações |
| Modificado | `backend/app/api/deps.py` | Autenticação / Autorização |
| Modificado | `backend/app/api/v1/admin.py` | Auditorias (Admin) |
| Modificado | `backend/app/api/v1/admin_onboarding.py` | Onboarding de Clientes |
| Modificado | `backend/app/api/v1/auth.py` | Autenticação / Login |
| Modificado | `backend/app/api/v1/client.py` | Interface do Cliente |
| Modificado | `backend/app/api/v1/sub_users.py` | Sub-usuários |
| Modificado | `backend/app/models/__init__.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/audit_control.py` | Modelos de Dados (ORM) |
| Removido | `backend/app/models/checklist.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/control_catalog.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/evidence.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/message.py` | Modelos de Dados (ORM) |
| Modificado | `backend/ruff.toml` | Lint / Qualidade de Código |
| Modificado | `backend/scripts/seed_catalog.py` | Scripts de Inicialização / Seeds |
| Adicionado | `backend/tests/test_admin_users.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_client_audits.py` | Testes Automatizados (pytest) |
| Modificado | `backend/tests/test_onboarding.py` | Testes Automatizados (pytest) |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |

### Funcionalidades Impactadas

- Auditorias (Admin)
- Autenticação / Autorização
- Autenticação / Login
- Banco de Dados / Migrações
- Documentação Técnica
- Interface do Cliente
- Lint / Qualidade de Código
- Modelos de Dados (ORM)
- Onboarding de Clientes
- Scripts de Inicialização / Seeds
- Sub-usuários
- Testes Automatizados (pytest)

### Correções Realizadas

- Nenhuma referência a achado (`B-X00` / `RD-00`) identificada neste commit.

### Verificações Recomendadas

- ⚠️ **Migration alterada.** A suíte usa `Base.metadata.create_all` e **não** executa migrations (ver M-18 em `docs/relatorio_melhorias.md`) — uma suíte verde não prova que a migration roda. Execute `alembic upgrade head` contra o MySQL real e confirme `alembic heads` com um único head.
- ⚠️ **Endpoint alterado.** Confirme a dependência de autorização: posse (`_get_*_with_access`) não é permissão. Ver **B-A23** em `docs/relatorio_bugs.md`.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Verificar se o mesmo bug ocorre em contextos similares no código.
- Adicionar teste de regressão para garantir que o problema não retorne.
- Atualizar `docs/relatorio_bugs.md` marcando o achado como corrigido.

---

## Commit `8313823` — 2026-08-11 18:00:52

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🚀 Nova Funcionalidade (`feat`) |
| **Hash Completo** | `8313823acf149a390fc7ae16aecbb2fe2de0a571` |
| **Arquivos Alterados** | 15 arquivo(s) |
| **Linhas** | +148 / −315 |

### Título do Commit

```
feat(cleanup): executa I.2, confirma I.1/I.3 e fecha o BLOCO I
```

### Descrição

Executado o item I.2 do plano de implementação (remoção do 2o lote de
rotas de API do Next.js sem consumidor). Ao reler o BLOCO I inteiro em
seguida para atualizar o que ja estava concluido, I.1 e I.3 foram
encontrados ja aplicados no codigo (implementados fora desta conversa,
nunca commitados - mesmo padrao ja observado no BLOCO H). Verificados,
testados e incluidos neste commit.

## I.2 - Remover 2o lote de rotas de API do Next.js sem consumidor

Revalidado com grep antes de remover (5 comandos da secao 6 do plano):
zero consumidores confirmados para os 9 arquivos. Removidos:

- frontend/app/api/profile/route.ts
- frontend/app/api/auth/refresh/route.ts
- frontend/app/api/client/controls/route.ts
- frontend/app/api/admin/onboarding/companies/route.ts
- frontend/app/api/admin/onboarding/principal-users/route.ts
- frontend/app/api/admin/onboarding/templates/route.ts
- frontend/app/api/sub-users/requests/route.ts
- frontend/app/api/sub-users/requests/pending/route.ts
- frontend/app/api/sub-users/requests/[id]/approve/route.ts

Diretorios vazios resultantes tambem removidos (app/api/profile/,
app/api/client/, app/api/admin/, app/api/sub-users/ e subpastas).
frontend/app/api/ agora so contem auth/{login,logout,register}, as 3
rotas que ainda tem consumidor real (setam cookies httpOnly a partir
de Client Components).

Validacao: npm run build regenerou os tipos e confirma que a lista de
rotas geradas so tem /api/auth/{login,logout,register}; npx tsc
--noEmit e npx eslint . limpos; suite de testes do backend inalterada
(nenhum endpoint FastAPI foi tocado).

## I.1 - Inverter ordem de validacao em POST /auth/register (confirmado)

backend/app/api/v1/auth.py::register() ja verificava
ALLOW_PUBLIC_REGISTRATION antes de consultar o e-mail duplicado -
aplicado fora desta conversa. Verificado linha a linha contra o
"Codigo completo" do plano: identico. Gap real encontrado: faltava o
teste de regressao que a propria secao 10 do item ja especificava.
Adicionado a backend/tests/test_auth.py:
test_register_returns_403_regardless_of_email_when_disabled - confirma
403 identico para e-mail cadastrado e nao cadastrado quando o registro
esta fechado.

## I.3 - Imports ausentes em alembic/env.py (confirmado)

backend/alembic/env.py ja importava app.models.company_dashboard e
app.models.sub_user_request - aplicado fora desta conversa. Validado
com conexao real ao MySQL: alembic current e alembic heads batem em
5457e7377a56, sem drift de schema.

## I.4 e I.5

Permanecem pendentes (nao implementados nesta revisao) - fora do
escopo pedido, que era executar I.2 e atualizar o que ja estava
concluido, nao implementar itens novos.

## Validacao final

- ruff check app: All checks passed!
- python -m pytest -q: 43 passed (era 42; +1 do teste novo de I.1)
- npx tsc --noEmit / npx eslint . (frontend): sem erros

## Documentacao

docs/plano_implementacao.md (v5.2 -> v5.3): tabela de status e de
prioridades atualizadas (I.1/I.2/I.3 concluidos); notas de verificacao
e execucao adicionadas as 3 secoes; checklists internos marcados;
changelog novo (v5.3).

docs/relatorio_bugs.md: B-A17, B-A18 e B-B14 marcados como corrigidos,
com referencia cruzada para I.3/I.1/I.2; contagens do resumo
quantitativo recalculadas (Alta 4->2, Baixa 6->5, Total ativo 18->13);
checklist de correcao e mapeamento OWASP atualizados.

docs/relatorio_funcionalidades.md: achado O01 (rotas orfas) marcado
como resolvido, com detalhamento da validacao; contagem de itens
orfaos na secao 1 atualizada.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (15 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `backend/alembic/env.py` | Banco de Dados / Migrações |
| Modificado | `backend/app/api/v1/auth.py` | Autenticação / Login |
| Modificado | `backend/tests/test_auth.py` | Testes Automatizados (pytest) |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |
| Modificado | `docs/relatorio_bugs.md` | Documentação Técnica |
| Modificado | `docs/relatorio_funcionalidades.md` | Documentação Técnica |
| Removido | `frontend/app/api/admin/onboarding/companies/route.ts` | Proxy de Binário (PDF/Evidência) |
| Removido | `frontend/app/api/admin/onboarding/principal-users/route.ts` | Proxy de Binário (PDF/Evidência) |
| Removido | `frontend/app/api/admin/onboarding/templates/route.ts` | Proxy de Binário (PDF/Evidência) |
| Removido | `frontend/app/api/auth/refresh/route.ts` | Proxy Auth (Next.js → FastAPI) |
| Removido | `frontend/app/api/client/controls/route.ts` | Outro / Não Categorizado |
| Removido | `frontend/app/api/profile/route.ts` | Outro / Não Categorizado |
| Removido | `frontend/app/api/sub-users/requests/[id]/approve/route.ts` | Outro / Não Categorizado |
| Removido | `frontend/app/api/sub-users/requests/pending/route.ts` | Outro / Não Categorizado |
| Removido | `frontend/app/api/sub-users/requests/route.ts` | Outro / Não Categorizado |

### Funcionalidades Impactadas

- Autenticação / Login
- Banco de Dados / Migrações
- Documentação Técnica
- Outro / Não Categorizado
- Proxy Auth (Next.js → FastAPI)
- Proxy de Binário (PDF/Evidência)
- Testes Automatizados (pytest)

### Correções Realizadas

- Referências detectadas: **B-A17, B-A18, B-B14**
  - Consulte `docs/relatorio_bugs.md` para o detalhamento de cada item.

### Verificações Recomendadas

- ⚠️ **Endpoint alterado.** Confirme a dependência de autorização: posse (`_get_*_with_access`) não é permissão. Ver **B-A23** em `docs/relatorio_bugs.md`.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Adicionar testes automatizados para a nova funcionalidade.
- Exercitar os endpoints novos FORA do caminho que a UI percorre — os 4 achados de prioridade Alta de 2026-08-24 só apareceram assim (ver `docs/relatorio_bugs.md`).
- Atualizar `docs/relatorio_funcionalidades.md` se a feature ficou completa.
- Verificar dependências com itens pendentes em `docs/roadmap.md`.

---

## Commit `6e02887` — 2026-08-11 17:35:28

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🚀 Nova Funcionalidade (`feat`) |
| **Hash Completo** | `6e028878b6824b6dc7b531c7daae42b972225db5` |
| **Arquivos Alterados** | 18 arquivo(s) |
| **Linhas** | +332 / −32 |

### Título do Commit

```
feat(infra): aplica BLOCO H (Docker + CI) ao repositório e corrige 5 bugs
```

### Descrição

Os arquivos de Docker/CI do BLOCO H já existiam no working tree (criados
fora desta conversa, nunca commitados) no mesmo formato que a revisão de
2026-08-05 do plano de implementação havia validado com docker build/run
reais e depois descartado (exercício documentação-only). Ao verificar a
implementação encontrada, 5 problemas reais foram identificados e
corrigidos antes do commit.

Bugs encontrados e corrigidos:

1. ruff check app falhava com 10 erros (imports não utilizados em 5
   arquivos) — o pré-requisito de limpar esses imports antes de habilitar
   o CI (já documentado desde a v4.0 do plano) nunca tinha sido executado.
   Sem a correção, o job 'backend' do ci.yml quebraria no primeiro
   push/PR. Corrigido: removidos os imports não usados de
   backend/app/api/v1/admin.py (HTTPException, status, AuditStatus,
   AuditControl, AuditControlStatus, ControlCatalog),
   backend/app/db/session.py (Base),
   backend/app/middleware/request_id.py (Request),
   backend/app/middleware/security_headers.py (Request) e
   backend/app/schemas/auth.py (Field). ruff check app passa limpo agora.

2. Sem backend/.dockerignore — backend/Dockerfile faz um COPY amplo num
   único estágio (sem isolamento multi-stage), então o .env real do
   backend (DATABASE_URL, JWT_SECRET, ADMIN_PASSWORD) seria copiado para
   dentro da imagem final, além de .venv/, .pytest_cache/, uploads/
   (arquivos de usuário) e db_auditoria.sql. Corrigido: criado
   backend/.dockerignore.

3. Sem frontend/.dockerignore — o estágio builder do frontend/Dockerfile
   copia todo o diretório depois de já ter copiado node_modules do
   estágio deps; sem ignorar node_modules nessa segunda cópia, o
   node_modules local do host (binários nativos para Windows/macOS, não
   para o node:20-slim Linux do container) sobrescreveria o node_modules
   correto recém-instalado via npm ci — risco real de quebrar o build
   para qualquer desenvolvedor que já tenha rodado npm install
   localmente (pré-requisito de setup_completo.md). .env.local
   (JWT_SECRET) também seria copiado ao contexto de build. Corrigido:
   criado frontend/.dockerignore.

4. Nenhum .gitignore cobria a raiz do projeto — o passo 8 do "passo a
   passo" do item H instrui criar Developer/.env na raiz para o
   docker-compose.yml ler MYSQL_PASSWORD/JWT_SECRET/ADMIN_EMAIL/
   ADMIN_PASSWORD; sem um .gitignore de raiz, esse arquivo seria
   rastreado pelo Git por padrão. Corrigido: criado .gitignore na raiz.

5. core.autocrlf=true no escopo --system do Git deste ambiente Windows
   deixava backend/docker-entrypoint.sh vulnerável: um checkout/clone/
   pull futuro converteria as quebras de linha para CRLF, quebrando o
   shebang do script no momento em que o Dockerfile copia o arquivo para
   dentro do container Linux, causando falha de boot do container.
   Confirmado via inspeção binária que o blob armazenado no Git contém
   só LF antes e depois da correção. Corrigido: criado .gitattributes na
   raiz forçando eol=lf para *.sh/Dockerfile/docker-entrypoint.sh.

Adicionalmente aplicado (já estava planejado, nunca tinha sido feito):
ruff==0.4.4 adicionado a backend/requirements.txt (seção "Dev/CI
apenas") — o plano já previa isso desde a v4.0 (2026-08-05) mas o
arquivo real nunca tinha sido alterado.

Validação realizada nesta revisão:
- ruff check app: todos os checks passaram
- python -m pytest -q: 42 passed (sem regressão pelos imports removidos)
- import de app.models e app.main: OK
- npx eslint / npx tsc --noEmit / npm run build (frontend): sem erros;
  .next/standalone/server.js gerado corretamente
- docker compose config (com as 4 variáveis obrigatórias definidas):
  YAML interpolado sem erro
- parse YAML de ci.yml e docker-compose.yml: válido

docker build/docker run/docker compose up reais NÃO foram re-executados
nesta revisão (Docker Desktop offline no momento da verificação) —
decisão explícita do usuário de prosseguir só com a validação estática
e das ferramentas adjacentes acima. Recomenda-se validar o build Docker
real antes do primeiro deploy (ver docs/plano_implementacao.md, seção H,
passos 4/6/9 do passo a passo).

Documentação: docs/plano_implementacao.md (v5.1 -> v5.2) — status do
item H atualizado de "Pendente" para "Concluído"; nota de validação e
correção completa adicionada ao topo da seção H; tabela de "Arquivos
impactados" e "Passo a passo" atualizados para refletir o que foi de
fato aplicado vs. o que segue pendente (docker build real, execução do
CI num PR real); seção "Testes e validação" atualizada com os cenários
confirmados nesta revisão; changelog novo (v5.2).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (18 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Adicionado | `.gitattributes` | Outro / Não Categorizado |
| Adicionado | `.github/workflows/ci.yml` | CI/CD e Automação |
| Adicionado | `.gitignore` | Outro / Não Categorizado |
| Adicionado | `backend/.dockerignore` | Outro / Não Categorizado |
| Adicionado | `backend/Dockerfile` | Infraestrutura / Docker |
| Modificado | `backend/app/api/v1/admin.py` | Auditorias (Admin) |
| Modificado | `backend/app/db/session.py` | Conexão com Banco de Dados |
| Modificado | `backend/app/middleware/request_id.py` | Middleware / Observabilidade |
| Modificado | `backend/app/middleware/security_headers.py` | Middleware / Observabilidade |
| Modificado | `backend/app/schemas/auth.py` | Schemas / Validação de Dados |
| Adicionado | `backend/docker-entrypoint.sh` | Infraestrutura / Docker |
| Modificado | `backend/requirements.txt` | Dependências Python |
| Adicionado | `backend/ruff.toml` | Lint / Qualidade de Código |
| Adicionado | `docker-compose.yml` | Infraestrutura / Docker |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |
| Adicionado | `frontend/.dockerignore` | Outro / Não Categorizado |
| Adicionado | `frontend/Dockerfile` | Infraestrutura / Docker |
| Modificado | `frontend/next.config.ts` | Configuração Next.js |

### Funcionalidades Impactadas

- Auditorias (Admin)
- CI/CD e Automação
- Conexão com Banco de Dados
- Configuração Next.js
- Dependências Python
- Documentação Técnica
- Infraestrutura / Docker
- Lint / Qualidade de Código
- Middleware / Observabilidade
- Outro / Não Categorizado
- Schemas / Validação de Dados

### Correções Realizadas

- Nenhuma referência a achado (`B-X00` / `RD-00`) identificada neste commit.

### Verificações Recomendadas

- ⚠️ **Endpoint alterado.** Confirme a dependência de autorização: posse (`_get_*_with_access`) não é permissão. Ver **B-A23** em `docs/relatorio_bugs.md`.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Adicionar testes automatizados para a nova funcionalidade.
- Exercitar os endpoints novos FORA do caminho que a UI percorre — os 4 achados de prioridade Alta de 2026-08-24 só apareceram assim (ver `docs/relatorio_bugs.md`).
- Atualizar `docs/relatorio_funcionalidades.md` se a feature ficou completa.
- Verificar dependências com itens pendentes em `docs/roadmap.md`.

---

## Commit `2fd729c` — 2026-08-11 17:06:23

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🚀 Nova Funcionalidade (`feat`) |
| **Hash Completo** | `2fd729cf71334f29ff38dba18543cc8afa5f9e22` |
| **Arquivos Alterados** | 20 arquivo(s) |
| **Linhas** | +1053 / −108 |

### Título do Commit

```
feat(backend): implementa E.4-E.9 do plano — resolve 6 dos 9 achados de E.3
```

### Descrição

Após reverificar item a item o inventário de código morto/funcionalidades
órfãs de E.3 (nenhuma divergência encontrada), triados os 9 achados por
risco/valor e implementados os 6 de menor risco/maior valor. Os 3
restantes permanecem catalogados em E.3: o subsistema de checklist
duplicado aguarda decisão de produto (envolve DROP TABLE); os métodos de
repository sem consumidor e os typos de nomenclatura (create_at/messagens)
são mantidos deliberadamente como dívida aceitável.

## Tier 1 — remoção pura (zero risco)

- E.4: remove o schema morto AuditCreateResponse (backend/app/schemas/
  admin.py) e o import não utilizado em admin.py — nunca era usado como
  response_model (create_audit usa AuditOut).
- E.5: remove o endpoint de debug GET /users/admin-only (backend/app/
  api/v1/users.py) e o import de require_admin, que só era usado por ele
  nesse arquivo. Também catalogado como B-M19 em relatorio_bugs.md.
- E.6: unifica generate_temporary_password/generate_initial_password —
  admin_onboarding.py passa a importar a função de services/users.py em
  vez de manter uma segunda implementação idêntica; remove os imports
  secrets/string, agora sem uso no arquivo.

## Tier 2 — completar funcionalidade já pronta na maior parte

- E.7: dashboard_cards.py::get_card_details() passa a popular
  actor_user/author_user em DashboardHistoryOut/DashboardMessageOut —
  os campos existiam no schema e a relationship já existia no model,
  só nunca eram preenchidos. Resolução em lote (1 query para todos os
  autores da página) para evitar N+1.
- E.8: services/users.py::create_user() passa a delegar para
  UserRepository.create() em vez de instanciar User(...) diretamente —
  fecha a última inconsistência da adoção do repository pattern (E.1).
- E.9: implementa POST/GET /dashboard/cards/{id}/notes (criar+listar
  DashboardCardNote) — model e FK já existiam sem nenhum endpoint.
  Restrito a admin (registro interno da auditoria, distinto do chat,
  que é bilateral com o cliente); sem update/delete, mesma semântica
  append-only já usada por histórico e chat do card.

## Testes

dashboard_cards.py não tinha nenhum teste antes desta revisão. Criado
backend/tests/test_dashboard_cards.py (8 testes novos, cobrindo E.7 e
E.9) e 3 fixtures reutilizáveis em conftest.py (company/dashboard/
dashboard_card). Suíte completa: 34 -> 42 passed.

## Documentação

docs/plano_implementacao.md (v5.0 -> v5.1): seções E.4-E.9 completas
no mesmo padrão de 10 partes do resto do documento; tabela de status,
tabela de prioridades e inventário de E.3 atualizados; changelog novo.

Sincronizados: docs/relatorio_bugs.md (B-M19 marcado corrigido, OWASP
A01 removido da lista de itens ativos, contagens recalculadas),
docs/relatorio_funcionalidades.md (O03/O04 atualizados, P01/P02 viram
F46/F47/F48), e a contagem de testes (34 -> 42) atualizada em todos os
documentos que a citavam como estado atual (relatorio_geral.md,
dashboard_projeto.md, index.md, relatorio_melhorias.md,
relatorio_documentacao.md, roadmap.md, executar_projeto.md,
setup_completo.md) — relatorio_commit.md (histórico auto-gerado) e as
notas datadas do próprio plano_implementacao.md foram preservadas
sem alteração, por serem registro histórico, não afirmação do estado
atual.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (20 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `backend/app/api/v1/admin.py` | Auditorias (Admin) |
| Modificado | `backend/app/api/v1/admin_onboarding.py` | Onboarding de Clientes |
| Modificado | `backend/app/api/v1/dashboard_cards.py` | Dashboard Gerencial / Cards |
| Modificado | `backend/app/api/v1/users.py` | Perfil do Usuário |
| Modificado | `backend/app/schemas/admin.py` | Schemas / Validação de Dados |
| Modificado | `backend/app/schemas/dashboard_runtime.py` | Schemas / Validação de Dados |
| Modificado | `backend/app/services/users.py` | Serviços / Lógica de Negócio |
| Modificado | `backend/tests/conftest.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_dashboard_cards.py` | Testes Automatizados (pytest) |
| Modificado | `docs/dashboard_projeto.md` | Documentação Técnica |
| Modificado | `docs/executar_projeto.md` | Documentação Técnica |
| Modificado | `docs/index.md` | Documentação Técnica |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |
| Modificado | `docs/relatorio_bugs.md` | Documentação Técnica |
| Modificado | `docs/relatorio_documentacao.md` | Documentação Técnica |
| Modificado | `docs/relatorio_funcionalidades.md` | Documentação Técnica |
| Modificado | `docs/relatorio_geral.md` | Documentação Técnica |
| Modificado | `docs/relatorio_melhorias.md` | Documentação Técnica |
| Modificado | `docs/roadmap.md` | Documentação Técnica |
| Modificado | `docs/setup_completo.md` | Documentação Técnica |

### Funcionalidades Impactadas

- Auditorias (Admin)
- Dashboard Gerencial / Cards
- Documentação Técnica
- Onboarding de Clientes
- Perfil do Usuário
- Schemas / Validação de Dados
- Serviços / Lógica de Negócio
- Testes Automatizados (pytest)

### Correções Realizadas

- Referências detectadas: **B-M19**
  - Consulte `docs/relatorio_bugs.md` para o detalhamento de cada item.

### Verificações Recomendadas

- ⚠️ **Endpoint alterado.** Confirme a dependência de autorização: posse (`_get_*_with_access`) não é permissão. Ver **B-A23** em `docs/relatorio_bugs.md`.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Adicionar testes automatizados para a nova funcionalidade.
- Exercitar os endpoints novos FORA do caminho que a UI percorre — os 4 achados de prioridade Alta de 2026-08-24 só apareceram assim (ver `docs/relatorio_bugs.md`).
- Atualizar `docs/relatorio_funcionalidades.md` se a feature ficou completa.
- Verificar dependências com itens pendentes em `docs/roadmap.md`.

---

## Commit `9e14706` — 2026-08-11 16:39:54

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 📝 Documentação (`docs`) |
| **Hash Completo** | `9e147062e08f966e7fa9911d94caf8f12398d457` |
| **Arquivos Alterados** | 1 arquivo(s) |
| **Linhas** | +12 / −0 |

### Título do Commit

```
docs(plano): verifica BLOCO E.3 — inventário de código morto/órfão confirmado atual
```

### Descrição

Reconferido item a item, por leitura direta do código-fonte atual em
backend/app/**, o inventário de código morto e funcionalidades órfãs
catalogado em E.3. Nenhum bug ou divergência encontrado — os 9 itens
do inventário continuam exatamente como descritos, sem nenhum ter
sido resolvido ou ficado desatualizado desde a última revisão:

- checklistItem/checklistItemState (subsistema de checklist
  'clássico'): confirmado, via grep em backend/app/api/**, que
  nenhuma rota HTTP os referencia — só DashboardCardchecklistItem
  (domínio paralelo) é usado.
- DashboardCardNote: confirmado sem nenhuma referência em
  dashboard_cards.py.
- AuditCreateResponse: confirmado importado em admin.py e nunca
  usado como response_model (create_audit usa AuditOut).
- DashboardHistoryOut.actor_user / DashboardMessageOut.author_user:
  confirmado que get_card_details() (linhas 178-233) segue
  construindo os dois schemas sem popular esses campos.
- AuditRepository.get_by_id/.list_by_client e
  UserRepository.get_by_id/.list_by_role/.create: confirmado sem
  nenhum chamador; create_user() em services/users.py segue
  instanciando User(...) diretamente.
- generate_temporary_password (services/users.py) e
  generate_initial_password (admin_onboarding.py): confirmadas como
  duas implementações independentes e idênticas.
- GET /users/admin-only: confirmado presente, sem consumidor —
  também catalogado como B-M19 em relatorio_bugs.md.
- Evidence.create_at e a tabela messagens: confirmados os typos de
  nomenclatura originais, sem alteração.

Como o item é por natureza um inventário de decisões de produto/
engenharia pendentes (não um bug funcional), nenhuma correção de
código foi necessária. Suíte de testes reexecutada como validação de
regressão: python -m pytest -q -> 34 passed, sem nenhuma mudança.

Adicionada ao plano uma nota de 'Verificação realizada em
2026-08-11' documentando o resultado item a item desta checagem, no
mesmo padrão já usado para os demais itens confirmados do documento.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (1 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |

### Funcionalidades Impactadas

- Documentação Técnica

### Correções Realizadas

- Referências detectadas: **B-M19**
  - Consulte `docs/relatorio_bugs.md` para o detalhamento de cada item.

### Verificações Recomendadas

- Nenhuma verificação manual específica disparada pelos caminhos tocados.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo.

### Próximos Passos Recomendados

- Revisar consistência com os outros documentos de `docs/`.
- Verificar cada afirmação de estado contra o código, não contra a revisão anterior.

---

## Commit `df7cd65` — 2026-08-11 15:25:30

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🚀 Nova Funcionalidade (`feat`) |
| **Hash Completo** | `df7cd65e548b6050ff2f6c1a9ff6e6e0849ff3e7` |
| **Arquivos Alterados** | 4 arquivo(s) |

### Título do Commit

```
feat(backend): conclui BLOCO E.2 — AuditControl herda TimestampMixim/SoftDeleteMixin
```

### Descrição

- AuditControl passa a herdar Base, TimestampMixim, SoftDeleteMixin,
  removendo a declaração local de created_at e os imports orfaos
  (datetime, DateTime, func); updated_at/deleted_at (ja existentes
  fisicamente desde a migration 5e977e8b49da) passam a ser
  mapeados pelo ORM.
- Audit e User removem a declaração duplicada de created_at (que ja
  vinha do mixin) e os mesmos imports orfaos.
- Nenhuma migration nova necessaria: alembic heads permanece em
  5457e7377a56.

Validado nesta revisão: os 3 models já estavam implementados
exatamente conforme o plano (docs/plano_implementacao.md, BLOCO E.2)
— nenhum bug encontrado, nenhuma correção necessária. Confirmado por
'python -c "import app.models; from app.main import app"' (OK) e
'python -m pytest -q' (34 passed, sem regressão).

docs(plano): marca E.2 como concluído (tabela de status, tabela de
pendências P3 e cabeçalho da seção), com nota de validação de
2026-08-11 na seção 10.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (4 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `backend/app/models/audit.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/audit_control.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/user.py` | Modelos de Dados (ORM) |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |

### Funcionalidades Impactadas

- Documentação Técnica
- Modelos de Dados (ORM)

### Correções Realizadas

- Nenhuma referência a bug (formato `B-X00`) identificada neste commit.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo do projeto.

### Próximos Passos Recomendados

- Adicionar testes automatizados para a nova funcionalidade.
- Atualizar `docs/relatorio_funcionalidades.md` se a feature agora está completa.
- Verificar se há dependências com funcionalidades pendentes no `docs/roadmap.md`.

---

## Commit `eda82cb` — 2026-08-10 16:59:32

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🐛 Correção de Bug (`fix`) |
| **Hash Completo** | `eda82cb18b9b39619d3a9e024529d8989b8c9744` |
| **Arquivos Alterados** | 6 arquivo(s) |

### Título do Commit

```
fix(backend): implementa BLOCO B.4 — resolve pendencias do chat persistido por controle
```

### Descrição

Verifica B.4 (chat persistido por controle): o backend (list_messages/
send_message) ja estava correto e funcional, e o frontend ja esta
conectado desde o D.7. Mas os "dois problemas adicionais" que o proprio
plano ja documentava nesta secao — e que o D.7 explicitamente deixou
fora do seu escopo — continuavam sem correcao.

- backend/app/api/v1/client.py: extrai _resolve_owner_user_id(current_user),
  a mesma logica que ja existia em list_client_controls (B.2), e reaplica
  em upload_evidence (B.3), list_messages e send_message (B.4). Resolve a
  inconsistencia em que um sub-usuario ja via o controle listado em
  GET /client/controls mas recebia 404 ao anexar evidencia ou enviar/ver
  mensagens desse mesmo controle — mesma causa raiz documentada tanto em
  B.3 quanto em B.4 (pendencia P1 combinada na tabela de prioridades).
- backend/app/schemas/audit.py: novo schema MessageCreate(content: str).
  send_message passa a receber payload: MessageCreate em vez de
  payload: dict — antes, payload.get("content", "").strip() quebrava
  com AttributeError (500) se content viesse como algo que nao fosse
  string (ex. um numero no JSON); agora o Pydantic rejeita com 422 antes
  mesmo da view rodar.

Testes novos (Bloco G):
- backend/tests/conftest.py: fixtures sub_user/sub_user_token.
- backend/tests/test_client_messages.py (novo): 7 testes cobrindo envio/
  listagem de mensagem, persistencia real, rejeicao de conteudo vazio/
  nao-string, acesso negado a controle de outro usuario, sub-usuario
  conseguindo enviar/listar mensagens do controle do principal, e
  sub-usuario orfao (sem parent_user_id) recebendo 400.
- backend/tests/test_evidence_upload.py: +1 teste (sub-usuario consegue
  fazer upload de evidencia), fechando a mesma pendencia registrada em B.3.

Verificado: suite pytest do backend 34/34 passando (26 anteriores + 8
novos), ruff check limpo nos arquivos alterados, backend importa sem
erro. Nenhuma mudanca de contrato de API (mesmos endpoints, mesmos
payloads de entrada/saida para quem ja enviava content como string).

docs(plano): marca B.4 como Concluido; atualiza a pendencia residual da
B.3 (mesma causa raiz, corrigida junto); marca o item P1 combinado
B.3/B.4 da tabela de prioridades como concluido.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (6 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `backend/app/api/v1/client.py` | Interface do Cliente |
| Modificado | `backend/app/schemas/audit.py` | Schemas / Validação de Dados |
| Modificado | `backend/tests/conftest.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_client_messages.py` | Testes Automatizados (pytest) |
| Modificado | `backend/tests/test_evidence_upload.py` | Testes Automatizados (pytest) |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |

### Funcionalidades Impactadas

- Documentação Técnica
- Interface do Cliente
- Schemas / Validação de Dados
- Testes Automatizados (pytest)

### Correções Realizadas

- Nenhuma referência a bug (formato `B-X00`) identificada neste commit.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo do projeto.

### Próximos Passos Recomendados

- Verificar se o mesmo bug ocorre em contextos similares no código.
- Adicionar teste de regressão para garantir que o problema não retorne.
- Atualizar `docs/relatorio_bugs.md` marcando o bug como corrigido (se aplicável).

---

## Commit `b054c7c` — 2026-08-10 16:35:11

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🔧 Manutenção / Configuração (`chore`) |
| **Hash Completo** | `b054c7c58a2e2de7f1ed1b94c8877b8654a758e0` |
| **Arquivos Alterados** | 4 arquivo(s) |

### Título do Commit

```
chore(frontend): implementa BLOCO D.8 — remove rotas de API do Next.js sem consumidor
```

### Descrição

Remove 2 rotas de API do Next.js sem nenhum consumidor no frontend e o
handler GET orfao de uma terceira rota, confirmado por grep cruzado em
frontend/app e frontend/lib (zero ocorrencias de uso fora dos proprios
arquivos removidos/alterados).

- app/api/me/route.ts removido por completo (so reexportava GET de
  /api/profile, que continua existindo e funcionando normalmente).
- app/api/admin/audits/route.ts removido por completo (unico handler,
  POST, sem consumidor). app/api/admin/onboarding/ (pasta irma dentro
  de app/api/admin/) nao foi afetada.
- app/api/sub-users/requests/route.ts: removido so o handler GET
  (nunca chamado); POST preservado sem mudanca de contrato — usado por
  "Solicitar criacao de sub-usuario" em client/page.tsx.

Nenhum endpoint do backend FastAPI e afetado (GET /users/perfil,
POST /admin/audits, GET /sub-users/requests/me continuam existindo
normalmente) — so deixam de ter um proxy Next.js nao utilizado.

Bug encontrado e corrigido durante a verificacao (working tree ja
trazia uma tentativa parcial e incorreta deste item, uncommitted):
- app/api/sub-users/requests/route.ts ja estava corrigido
  corretamente (so o GET removido).
- app/api/me/route.ts tinha sido esvaziado (0 bytes) em vez de
  excluido — um route.ts vazio, sem export de metodo HTTP, quebra o
  build ("next build"/tsc acusavam "Cannot find module
  '.../app/api/me/route.js'", gerado pelo validador de rotas do
  Next.js). Corrigido excluindo o arquivo e a pasta por completo.
- app/api/admin/audits/route.ts nao tinha sido tocado, continuando
  presente e identico ao original. Corrigido excluindo o arquivo e a
  pasta por completo.

Verificado apos a correcao: npx tsc --noEmit limpo, npm run build
completo sem erros (lista de rotas do build nao contem mais /api/me
nem /api/admin/audits; /api/sub-users/requests, so POST, preservado),
npx eslint limpo, suite pytest do backend 26/26 passando.

docs(plano): marca D.8 como Concluido — fecha o BLOCO D por completo
(D.1-D.8, todos ✅).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (4 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |
| Removido | `frontend/app/api/admin/audits/route.ts` | Proxy Admin (Next.js → FastAPI) |
| Removido | `frontend/app/api/me/route.ts` | Outro / Não Categorizado |
| Modificado | `frontend/app/api/sub-users/requests/route.ts` | Proxy Sub-usuários (Next.js → FastAPI) |

### Funcionalidades Impactadas

- Documentação Técnica
- Outro / Não Categorizado
- Proxy Admin (Next.js → FastAPI)
- Proxy Sub-usuários (Next.js → FastAPI)

### Correções Realizadas

- Nenhuma referência a bug (formato `B-X00`) identificada neste commit.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo do projeto.

### Próximos Passos Recomendados

- Verificar impacto nas dependências com `pip list` (backend) ou `npm audit` (frontend).
- Atualizar `docs/setup_completo.md` se o processo de instalação mudou.

---

## Commit `a24bae6` — 2026-08-10 16:17:13

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🚀 Nova Funcionalidade (`feat`) |
| **Hash Completo** | `a24bae6efab92623df1c7943a1844fd5fb7b7fea` |
| **Arquivos Alterados** | 6 arquivo(s) |

### Título do Commit

```
feat(frontend): implementa BLOCO D.7 — Dashboard Cliente com evidencia/chat reais
```

### Descrição

Conecta "Anexar evidencia" e "Conversa/Duvidas", em /private/client, aos
endpoints reais do backend, em vez de so mutar useState local (que zerava
a cada F5).

- lib/server-backend.ts: callBackend() passa a aceitar body: FormData
  (upload real de arquivo via Server Action) sem quebrar nenhum uso
  existente com JSON — detecta FormData e nao define Content-Type
  manualmente nem faz JSON.stringify.
- client/actions.ts: 3 novas Server Actions (uploadEvidenceAction,
  listMessagesAction, sendMessageAction) consumindo os endpoints ja
  existentes (POST .../evidences, GET/POST .../messages — Bloco B.3/B.4).
- client/page.tsx: Server Component pre-busca o historico de mensagens
  so do primeiro controle exibido; passa userId como prop (usado para
  distinguir autor CLIENTE/AUDITORIA das mensagens vindas do GET).
- client-dashboard-client.tsx: anexarEvidencia passa a receber o File
  real (nao so o nome) e enviar via FormData; enviarDuvida chama
  sendMessageAction; troca de controle busca mensagens sob demanda
  (useEffect que ignora a 1a renderizacao, mesmo padrao do D.6).

Bugs encontrados e corrigidos durante a verificacao (working tree ja
trazia os 5 arquivos, uncommitted, quebrando o build):
- client/actions.ts: RequestSubUserResult ainda usava a chave "Ok"
  (maiuscula, resquicio de antes do D.7) mas o consumidor ja lia
  "result.ok" (minuscula) — tsc acusava "Property 'ok' does not exist".
  Corrigido para "ok" em toda a union, consistente com os demais tipos
  de resultado do arquivo (UploadEvidenceResult/SendMessageResult).
- client/page.tsx: initialControles nao incluia "evidencias: []",
  campo obrigatorio do tipo Controle — tsc acusava "Property
  'evidencias' is missing". Adicionado.
- Comentarios desatualizados ("D.7 ainda pendente") removidos de
  client/actions.ts e client-dashboard-client.tsx.
- admin-dashboard-client.tsx: adicionado eslint-disable-next-line
  react-hooks/set-state-in-effect antes de setIsLoadingMessages(true)
  no useEffect de busca de mensagens sob demanda, mesmo padrao ja usado
  no card do D.6 — necessario para eslint passar limpo.

Verificado nesta revisao: nenhum arquivo de backend muda (endpoints de
evidencia/mensagem ja corretos desde B.3/B.4). Apos as correcoes:
npx tsc --noEmit limpo, npx eslint limpo, npm run build completo sem
erros, suite pytest do backend 26/26 passando.

docs(plano): marca D.7 como Concluido; atualiza cabecalho do BLOCO D
para D.1-D.7 concluidos (so D.8 pendente).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (6 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |
| Modificado | `frontend/app/private/admin/admin-dashboard-client.tsx` | Dashboard Admin (Frontend) |
| Modificado | `frontend/app/private/client/actions.ts` | Dashboard Cliente (Frontend) |
| Modificado | `frontend/app/private/client/client-dashboard-client.tsx` | Dashboard Cliente (Frontend) |
| Modificado | `frontend/app/private/client/page.tsx` | Dashboard Cliente (Frontend) |
| Modificado | `frontend/lib/server-backend.ts` | Utilitários do Frontend |

### Funcionalidades Impactadas

- Dashboard Admin (Frontend)
- Dashboard Cliente (Frontend)
- Documentação Técnica
- Utilitários do Frontend

### Correções Realizadas

- Nenhuma referência a bug (formato `B-X00`) identificada neste commit.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo do projeto.

### Próximos Passos Recomendados

- Adicionar testes automatizados para a nova funcionalidade.
- Atualizar `docs/relatorio_funcionalidades.md` se a feature agora está completa.
- Verificar se há dependências com funcionalidades pendentes no `docs/roadmap.md`.

---

## Commit `2964b05` — 2026-08-10 14:40:11

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🚀 Nova Funcionalidade (`feat`) |
| **Hash Completo** | `2964b05595bbda2c5d9b86e939af0bf706d04550` |
| **Arquivos Alterados** | 4 arquivo(s) |

### Título do Commit

```
feat(frontend): implementa BLOCO D.6 — Dashboard Admin com DashboardCard real
```

### Descrição

Substitui a lista de controles mockada (controlesIniciais/ControleAdmin,
3 registros fixos 5.1/5.2/5.3) por dados reais de DashboardCard, já
persistidos no banco (Bloco B.5).

- admin/actions.ts: 4 novas Server Actions (listAllCardsAction,
  getCardDetailAction, updateCardStatusAction, toggleChecklistItemAction)
  consumindo os endpoints já existentes de /dashboard.
- admin/page.tsx: Server Component busca os cards de todas as empresas
  via Promise.all + o detalhe do primeiro card, sem fetch no cliente.
- admin-dashboard-client.tsx: renderiza os cards reais; troca de card
  busca o detalhe sob demanda (useEffect que ignora a 1a renderização);
  atualizarStatus/alternarChecklist passam a persistir via Server Action
  em vez de só mutar estado local. control_code nulo exibe "—".

Verificado nesta revisão: os 3 arquivos já implementados no working tree
batem com a especificação do plano (só diferem em formatação); npx tsc
--noEmit limpo; suite pytest do backend 26/26 passando, incluindo os
testes que cobrem os endpoints de dashboard_cards consumidos aqui.

docs(plano): marca D.6 (e D.1-D.5, que já estavam concluídos no código
mas com a tabela-resumo desatualizada) como Concluído.

fix(backend): reverte corrupção acidental de "OK"->"ok" em 15 arquivos
não relacionados a D.6 (dashboard_cards.py, health.py, users.py,
check_db.py, workflow de CI, docs de automação, package-lock.json,
proxy.ts, auth routes) — o replace global havia quebrado
status.HTTP_200_OK (crash do backend inteiro na importação),
secrets.GITHUB_TOKEN no CI e hashes integrity do package-lock.json.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (4 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |
| Modificado | `frontend/app/private/admin/actions.ts` | Dashboard Admin (Frontend) |
| Modificado | `frontend/app/private/admin/admin-dashboard-client.tsx` | Dashboard Admin (Frontend) |
| Modificado | `frontend/app/private/admin/page.tsx` | Dashboard Admin (Frontend) |

### Funcionalidades Impactadas

- Dashboard Admin (Frontend)
- Documentação Técnica

### Correções Realizadas

- Nenhuma referência a bug (formato `B-X00`) identificada neste commit.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo do projeto.

### Próximos Passos Recomendados

- Adicionar testes automatizados para a nova funcionalidade.
- Atualizar `docs/relatorio_funcionalidades.md` se a feature agora está completa.
- Verificar se há dependências com funcionalidades pendentes no `docs/roadmap.md`.

---

## Commit `2167dac` — 2026-08-07 17:34:10

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 📝 Documentação (`docs`) |
| **Hash Completo** | `2167dac75d6ad956e01cee98a31ede5ecdfdc2dc` |
| **Arquivos Alterados** | 1 arquivo(s) |

### Título do Commit

```
docs(plano): marca BLOCO D.1-D.5 como concluído e documenta validação
```

### Descrição

Atualiza docs/plano_implementacao.md para refletir que a migração de
sessão/autenticação/carregamento de dados do BLOCO D foi implementada
em frontend/ e revisada arquivo a arquivo nesta data:

- Heading do BLOCO D e dos itens D.1, D.3, D.4 e D.5 marcados como
  ✅ Concluído em 2026-08-07 (D.2 já era absorvido por D.1; D.3 e D.5
  também são superados por D.1, como já indicavam suas próprias notas
  de sequenciamento). D.6, D.7 e D.8 continuam pendentes — não houve
  nenhuma mudança de código nessas três seções, então seus headings
  (🔴/🟡) permanecem como estavam.
- Novo blockquote de validação logo após a introdução do bloco,
  listando os 5 bugs que a implementação inicial continha (JWT_SECRET
  placeholder nunca substituído em .env.local, requireClient() com
  condição de papel invertida causando loop de redirecionamento,
  admin/actions.ts sem "use server" quebrando o build, endpoint de
  sub-usuário com typo /request em vez de /requests, client/page.tsx
  com shape de dado incompatível) e os arquivos que ainda estavam na
  versão pré-migração (layout.tsx, user-menu.tsx, login-form.tsx) ou
  eram órfãos removidos (auth-context.tsx, sub-user-requests-panel.tsx,
  um duplicado de user-menu.tsx em frontend/_components/).
- Bloco de código de `frontend/.env.local` (seção 4 de D.1) passa a
  incluir também `JWT_EXPIRES_MINUTES`, com nota explicando por que:
  o código assume 60 min quando ausente, mas o backend real está
  configurado para 480 — divergência que expirava o cookie no
  navegador bem antes do JWT deixar de ser válido.
- Aviso explícito sobre o próprio bug do JWT_SECRET-placeholder, já
  que .env.local não é versionado e por isso nunca aparece em nenhum
  diff — só é detectável testando o login manualmente, como o plano
  já recomendava no passo 3 da seção 6 de D.1.

Revalidação registrada: `npx tsc --noEmit`, `npx next build`,
`npx eslint .` e `pytest -q` (26/26) executados após as correções
(commits e5de18c e 785ef0a), todos passando.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (1 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |

### Funcionalidades Impactadas

- Documentação Técnica

### Correções Realizadas

- Nenhuma referência a bug (formato `B-X00`) identificada neste commit.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo do projeto.

### Próximos Passos Recomendados

- Revisar consistência com outros documentos em `docs/`.
- Verificar se `docs/setup_completo.md` precisa de atualização.

---

## Commit `785ef0a` — 2026-08-07 17:27:16

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🐛 Correção de Bug (`fix`) |
| **Hash Completo** | `785ef0ae9d82a14f7d324e848b60dd56d5d18e83` |
| **Arquivos Alterados** | 8 arquivo(s) |

### Título do Commit

```
fix(backend): padroniza nomes de campo em SubUserRequest (request_email)
```

### Descrição

Corrige a inconsistência documentada como B-M08 em docs/relatorio_bugs.md:
o schema Pydantic usava `requested_full_name`/`requested_email`, o modelo
ORM usava `request_full_name`/`request_email`, e o contrato realmente
consumido pelo frontend (RequestSubUserInput, ver BLOCO D) usa
`requested_full_name`/`request_email` — uma combinação que não batia
com nenhum dos dois lados, quebrando a atribuição ORM sempre que o nome
do campo divergia entre schema e modelo.

Padronização adotada em todos os pontos: `requested_full_name` (schema,
modelo, migration) + `request_email` (schema, modelo, migration),
igual ao que o frontend já envia/espera:

- backend/app/models/sub_user_request.py: coluna `request_full_name`
  renomeada para `requested_full_name`
- backend/alembic/versions/447a4e1de59d_add_sub_user_role_flow.py:
  migration correspondente atualizada para criar a coluna já com o
  nome `requested_full_name`
- backend/app/schemas/sub_user.py: `SubUserRequestCreate.requested_email`
  e `SubUserRequestPublic.requested_email` renomeados para `request_email`
- backend/app/api/v1/sub_users.py: todos os pontos que liam/escreviam
  `payload.requested_email` e `row.request_full_name` corrigidos para
  os nomes padronizados (`payload.request_email` / `row.requested_full_name`)
- backend/tests/test_sub_users.py: payloads e asserções dos testes de
  criação/aprovação de solicitação de sub-usuário atualizados para
  `request_email`
- docs/relatorio_bugs.md, docs/relatorio_melhorias.md,
  docs/plano_implementacao.md: exemplos de código e descrição do bug
  B-M08 atualizados para refletir a padronização final

Sem mudança de schema de banco além da migration já existente (só o
nome da coluna criada nela); nenhuma migration nova é necessária pois
o banco ainda não tinha sido migrado com o nome antigo em produção.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (8 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `backend/alembic/versions/447a4e1de59d_add_sub_user_role_flow.py` | Banco de Dados / Migrações |
| Modificado | `backend/app/api/v1/sub_users.py` | Sub-usuários |
| Modificado | `backend/app/models/sub_user_request.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/schemas/sub_user.py` | Schemas / Validação de Dados |
| Modificado | `backend/tests/test_sub_users.py` | Testes Automatizados (pytest) |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |
| Modificado | `docs/relatorio_bugs.md` | Documentação Técnica |
| Modificado | `docs/relatorio_melhorias.md` | Documentação Técnica |

### Funcionalidades Impactadas

- Banco de Dados / Migrações
- Documentação Técnica
- Modelos de Dados (ORM)
- Schemas / Validação de Dados
- Sub-usuários
- Testes Automatizados (pytest)

### Correções Realizadas

- Referências a bugs detectadas: **B-M08**
  - Consulte `docs/relatorio_bugs.md` para detalhes de cada item.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo do projeto.

### Próximos Passos Recomendados

- Verificar se o mesmo bug ocorre em contextos similares no código.
- Adicionar teste de regressão para garantir que o problema não retorne.
- Atualizar `docs/relatorio_bugs.md` marcando o bug como corrigido (se aplicável).

---

## Commit `e5de18c` — 2026-08-07 17:22:41

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🐛 Correção de Bug (`fix`) |
| **Hash Completo** | `e5de18c729c5c84f90387c92eb29617bfdc95c80` |
| **Arquivos Alterados** | 21 arquivo(s) |

### Título do Commit

```
fix(frontend): corrige bugs do BLOCO D
```

### Descrição

Corrige a implementação da migração de sessão/autenticação/carregamento
de dados (BLOCO D) para Server Components + Server Actions + Proxy:

Críticos (quebravam a aplicação):
- lib/session.ts: requireClient() tinha a condição de papel invertida,
  causando loop infinito de redirecionamento para todo usuário não-admin
- admin/actions.ts: faltava a diretiva "use server", quebrando o build
- client/actions.ts: endpoint de solicitação de sub-usuário apontava
  para /sub-users/request (singular) em vez de /sub-users/requests
- client/page.tsx: montava o campo `evidencia` em formato incompatível
  com ClientDashboardClient, quebrando a tipagem

Altos (D.1 documentado mas não aplicado):
- private/layout.tsx e _components/user-menu.tsx: reescritos como
  Server Component puro, usando a DAL (getCurrentUserProfile) em vez
  de fetch("/api/profile") em useEffect
- public/login/login-form.tsx: passa a usar o `role` já devolvido por
  /api/auth/login, eliminando a 2ª chamada de rede a /api/profile
- api/auth/login/route.ts: devolve `{ ok, role }` em minúsculo,
  consistente com o novo login-form.tsx

Médios:
- Cria admin/loading.tsx e admin/error.tsx (só existiam no lado client)
- Remove lib/auth-context.tsx (órfão, 0 consumidores — D.3)
- Remove admin_components/sub-user-requests-panel.tsx (duplicata
  órfã — D.4)
- proxy.ts: adiciona checagem de payload.type ausente em
  verifyAccessToken, alinhando com lib/session.ts (defesa em
  profundidade)

Validado com `npx tsc --noEmit`, `npx next build` e `npx eslint .`.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (21 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `frontend/app/api/auth/login/route.ts` | Proxy Auth (Next.js → FastAPI) |
| Modificado | `frontend/app/private/_components/user-menu.tsx` | Componentes Privados (Frontend) |
| Adicionado | `frontend/app/private/admin/actions.ts` | Dashboard Admin (Frontend) |
| Adicionado | `frontend/app/private/admin/admin-dashboard-client.tsx` | Dashboard Admin (Frontend) |
| Adicionado | `frontend/app/private/admin/error.tsx` | Dashboard Admin (Frontend) |
| Adicionado | `frontend/app/private/admin/loading.tsx` | Dashboard Admin (Frontend) |
| Modificado | `frontend/app/private/admin/page.tsx` | Dashboard Admin (Frontend) |
| Removido | `frontend/app/private/admin_components/sub-user-requests-panel.tsx` | Outro / Não Categorizado |
| Adicionado | `frontend/app/private/client/actions.ts` | Dashboard Cliente (Frontend) |
| Adicionado | `frontend/app/private/client/client-dashboard-client.tsx` | Dashboard Cliente (Frontend) |
| Adicionado | `frontend/app/private/client/error.tsx` | Dashboard Cliente (Frontend) |
| Adicionado | `frontend/app/private/client/loading.tsx` | Dashboard Cliente (Frontend) |
| Modificado | `frontend/app/private/client/page.tsx` | Dashboard Cliente (Frontend) |
| Modificado | `frontend/app/private/layout.tsx` | Layout Privado (Frontend) |
| Modificado | `frontend/app/public/login/login-form.tsx` | Página de Login |
| Removido | `frontend/lib/auth-context.tsx` | Utilitários do Frontend |
| Adicionado | `frontend/lib/session.ts` | Utilitários do Frontend |
| Removido | `frontend/middleware.ts` | Middleware de Autenticação (legado) |
| Modificado | `frontend/package-lock.json` | Outro / Não Categorizado |
| Modificado | `frontend/package.json` | Dependências Node.js |
| Adicionado | `frontend/proxy.ts` | Proxy/Middleware de Autenticação |

### Funcionalidades Impactadas

- Componentes Privados (Frontend)
- Dashboard Admin (Frontend)
- Dashboard Cliente (Frontend)
- Dependências Node.js
- Layout Privado (Frontend)
- Middleware de Autenticação (legado)
- Outro / Não Categorizado
- Proxy Auth (Next.js → FastAPI)
- Proxy/Middleware de Autenticação
- Página de Login
- Utilitários do Frontend

### Correções Realizadas

- Nenhuma referência a bug (formato `B-X00`) identificada neste commit.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo do projeto.

### Próximos Passos Recomendados

- Verificar se o mesmo bug ocorre em contextos similares no código.
- Adicionar teste de regressão para garantir que o problema não retorne.
- Atualizar `docs/relatorio_bugs.md` marcando o bug como corrigido (se aplicável).

---

## Commit `549625d` — 2026-08-06 14:59:06

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🚀 Nova Funcionalidade (`feat`) |
| **Hash Completo** | `549625d3ddb547492a61510841338cf7f4e4c557` |
| **Arquivos Alterados** | 11 arquivo(s) |

### Título do Commit

```
feat(backend): implementa BLOCO G — suíte de testes automatizados (pytest)
```

### Descrição

Cria a suíte mínima de testes de backend documentada no plano de
implementação (Bloco G), cobrindo os fluxos que já sofreram regressão
silenciosa neste projeto (B.3, B.6, C.2.a, C.2.b, A.6, A.12).

Infraestrutura de teste:
- backend/pytest.ini: configuração do pytest (testpaths=tests).
- backend/tests/conftest.py: banco SQLite em memória isolado por teste
  (StaticPool + create_all/drop_all autouse), override de get_db via
  app.dependency_overrides, isolamento de upload de arquivo via
  monkeypatch de storage.UPLOAD_DIR (tmp_path), e fixtures de apoio
  (admin_user/admin_token, principal_user/user_token, catalog_control,
  audit_with_control).
- backend/requirements.txt: adiciona pytest==8.2.0, httpx==0.27.0 e
  pytest-cov==5.0.0.
- backend/.gitignore: ignora o artefato .coverage gerado por
  'pytest --cov'.

Cobertura por arquivo (26 testes, todos com comentário indicando qual
regressão histórica cada um pega quando aplicável):
- test_auth.py: login (sucesso/senha errada/e-mail inexistente),
  registro (sucesso/senha fraca/e-mail duplicado — regressão do A.6),
  GET /users/perfil (com e sem token).
- test_evidence_upload.py: upload de evidência (sucesso, colunas
  persistidas corretamente, extensão não permitida, arquivo grande
  demais, acesso negado a controle de outro usuário) — regressão do B.3.
- test_admin_audits.py: criação de auditoria, autorização por papel,
  listagem paginada e serializável — regressão do B.6.
- test_onboarding.py: onboarding sem telefone, onboarding com template
  (cards sem control_code) — regressões do C.2.a/C.2.b —, e-mail
  duplicado, autorização por papel.
- test_sub_users.py: solicitação e aprovação de sub-usuário, dupla
  aprovação retornando 400 em vez de 500 — regressão do A.12 —,
  autorização por papel.

Validação: 'python -m pytest -v' -> 26 passed; 'python -m pytest
--cov=app --cov-report=term-missing' -> cobertura total de 83%
(TOTAL 1125 187 83%), sem nenhum arquivo extra deixado em
backend/uploads/ (isolamento de upload confirmado).

docs(plano): atualiza o Bloco G de 🔴 Pendente para ✅ Concluído

- Painel executivo e tabela de prioridades: item G e G.1/G.2 marcados
  como concluídos (2026-08-06).
- Bloco G: título e validação atualizados para refletir que a suíte
  foi implementada e commitada de verdade (não mais um dry-run
  documentação-only como na revisão de 2026-08-05) — números de teste
  e cobertura reexecutados e confirmados idênticos.
- Cross-references de B.3, B.6 e A.6 atualizadas: cada uma agora aponta
  para o teste real que cobre a regressão, em vez de 'ainda não criado'.
- Cabeçalho do documento: versão 4.1, HEAD analisado atualizado.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (11 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `backend/.gitignore` | Outro / Não Categorizado |
| Adicionado | `backend/pytest.ini` | Outro / Não Categorizado |
| Modificado | `backend/requirements.txt` | Dependências Python |
| Adicionado | `backend/tests/__init__.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/conftest.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_admin_audits.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_auth.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_evidence_upload.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_onboarding.py` | Testes Automatizados (pytest) |
| Adicionado | `backend/tests/test_sub_users.py` | Testes Automatizados (pytest) |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |

### Funcionalidades Impactadas

- Dependências Python
- Documentação Técnica
- Outro / Não Categorizado
- Testes Automatizados (pytest)

### Correções Realizadas

- Nenhuma referência a bug (formato `B-X00`) identificada neste commit.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo do projeto.

### Próximos Passos Recomendados

- Adicionar testes automatizados para a nova funcionalidade.
- Atualizar `docs/relatorio_funcionalidades.md` se a feature agora está completa.
- Verificar se há dependências com funcionalidades pendentes no `docs/roadmap.md`.

---

## Commit `7691c4a` — 2026-08-05 19:03:23

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 📝 Documentação (`docs`) |
| **Hash Completo** | `7691c4a77e1fcad92ba84bf30eecf0bec054ad93` |
| **Arquivos Alterados** | 1 arquivo(s) |

### Título do Commit

```
docs(plano): reforça BLOCO D com separação de responsabilidades e estratégia de cache
```

### Descrição

Contexto: pedido explícito para revisar o BLOCO D — Frontend: Sessão,
Autenticação e Carregamento de Dados, reportando em uso real os sintomas
já diagnosticados no item D.1 (listas/dashboards que não carregam na
primeira renderização, exigindo F5 ou nova tentativa). Reconferido o
código real do frontend antes de editar: nada mudou desde o commit
anterior (git status limpo), então o diagnóstico do D.1 permanece 100%
válido e nenhuma nova causa raiz foi encontrada — o trabalho aqui é
fechar duas lacunas do checklist do pedido que estavam implícitas demais
na versão anterior do documento.

Alterações em docs/plano_implementacao.md (26 inserções, 1 remoção):

1. Introdução do BLOCO D reescrita para conectar explicitamente a
   linguagem usada na descrição do problema ("precisa atualizar a
   página", "tentar novamente") ao diagnóstico técnico já existente no
   D.1, e para deixar claro como D.2/D.3/D.4/D.5/D.6/D.7/D.8 se
   relacionam entre si (D.2 absorvido por D.1; D.3/D.4/D.5/D.8
   independentes e aplicáveis isoladamente; D.6/D.7 aplicam a arquitetura
   do D.1 às duas telas com dado mockado/local).

2. Nova tabela "Separação de responsabilidades" no início da seção 2 do
   item D.1 — mapeia cada camada (proxy.ts, lib/session.ts,
   lib/server-backend.ts, page.tsx, actions.ts,
   *-dashboard-client.tsx, loading.tsx, error.tsx) para exatamente uma
   responsabilidade, contrastando com o estado atual (admin/page.tsx e
   client/page.tsx fazem autenticação + busca de dado + estado de UI +
   mutação + feedback de carregamento/erro todos misturados no mesmo
   arquivo "use client").

3. Nova seção "Cache e revalidação" na seção 2 do item D.1 — explica por
   que cache: "no-store" em toda chamada ao backend (dado privado por
   usuário, sem uso do Cache de Dados do Next.js, que arriscaria vazar
   dado entre sessões); diferencia cache() do React (dedupe só dentro do
   mesmo request) do Cache de Dados do Next.js (não usado aqui);
   documenta revalidatePath() nas Server Actions como o mecanismo de
   atualização pós-mutação, eliminando qualquer necessidade de F5 manual.

4. Novo parágrafo descrevendo os 4 estados de UI (carregando/erro/
   vazio/sucesso) como resolvidos por convenção de arquivo
   (loading.tsx/error.tsx) e checagem de array vazio já presente no
   código documentado em D.6/D.7, em vez de isLoading/useEffect manual
   espalhado pelo componente (padrão atual).

Nenhuma mudança de código de produção — só docs/plano_implementacao.md.
O restante do checklist do pedido (centralizar chamadas no servidor,
tratar auth/cookies/tokens no servidor, eliminar inconsistência de
hidratação, reduzir chamadas duplicadas, arquivos afetados + ordem +
passo a passo + código completo + validação) já estava coberto nas 10
seções do item D.1 documentadas em commits anteriores — conferido item a
item contra o pedido nesta revisão, sem lacunas adicionais encontradas.

Não incluído neste commit: Prompt_Analise_de_projeto.txt e
Prompt_Atualizar_Plano_Implemetacao.txt (prompts pessoais, não são código
do projeto).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (1 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |

### Funcionalidades Impactadas

- Documentação Técnica

### Correções Realizadas

- Nenhuma referência a bug (formato `B-X00`) identificada neste commit.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo do projeto.

### Próximos Passos Recomendados

- Revisar consistência com outros documentos em `docs/`.
- Verificar se `docs/setup_completo.md` precisa de atualização.

---

## Commit `e372810` — 2026-08-05 18:09:01

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 📝 Documentação (`docs`) |
| **Hash Completo** | `e3728103dc60b0dc91bc99d5b4e9e263ff1a4e6b` |
| **Arquivos Alterados** | 2 arquivo(s) |

### Título do Commit

```
docs(plano): documentação técnica completa dos 12 itens pendentes (10 seções + código final)
```

### Descrição

Contexto: seguindo diretrizes explícitas para que docs/plano_implementacao.md
funcione como especificação autoexplicativa — cada implementação pendente
documentada com objetivo, arquitetura, arquivos impactados, código COMPLETO
(sem trechos parciais), local exato da alteração, passo a passo com ordem de
dependência, banco de dados, APIs, frontend e testes/validação. Trabalho
feito em 4 lotes, nesta ordem de prioridade/dependência.

Lote 1 — itens P1 pequenos e autocontidos, independentes de D.1:
- D.3: remover AuthProvider do layout privado (decisão registrada: opção
  mínima em vez de já conectar useAuth(), para não investir em arquitetura
  que D.1 substituiria em breve).
- D.4: remover SubUserRequestsPanel duplicado/órfão.
- D.5: corrigir double-push no redirecionamento pós-login.
- D.8: remover 2 rotas de API do Next.js sem consumidor + 1 método HTTP
  órfão de uma terceira rota (GET de /api/sub-users/requests, POST
  preservado).
- E.2: completar TimestampMixin/SoftDeleteMixin em AuditControl, remover
  duplicação de created_at em User/Audit.
Notas de sequenciamento adicionadas em D.3/D.5 explicando que D.1, quando
aplicado, já resolve os dois por completo.

Lote 2 — D.1 (migração para Server Components/Server Actions/Proxy),
absorvendo D.2 (validação de papel no middleware, fisicamente substituído
pelo proxy.ts novo). 20 arquivos documentados com código final completo:
package.json, .env.local, lib/session.ts (DAL com getCurrentUser/
getCurrentUserProfile memoizados via cache(), requireAdmin/requireClient),
proxy.ts (substitui middleware.ts — confirmado via
node_modules/next/dist/docs que "middleware" está deprecado desde a v16.0.0
nesta versão do Next.js; proxy.ts inclui verificação real de assinatura JWT
via jose, renovação silenciosa de sessão fechando o loop deixado em aberto
no item A.10, e validação de papel simétrica para /private/admin e
/private/client), layout.tsx/user-menu.tsx como Server Components,
admin/{actions.ts, admin-dashboard-client.tsx, page.tsx, loading.tsx,
error.tsx}, os 5 equivalentes em client/, login/route.ts (retorna role no
corpo) e login-form.tsx (remove a 2a chamada a /api/profile). Inclui 13
cenarios de teste e tabela de riscos.

Lote 3 — D.6 e D.7, construídos sobre a arquitetura do D.1 (sem repetir o
que já foi documentado lá):
- D.6: substitui a lista mockada de controles do admin por DashboardCard
  real (endpoints já Concluidos do Bloco B.5). Decisão registrada: busca em
  paralelo por empresa (backend não tem endpoint agregador), detalhe do
  card sob demanda via Server Action (só o primeiro card vem pré-carregado
  via SSR).
- D.7: conecta upload de evidência e chat aos endpoints reais (B.3/B.4).
  lib/server-backend.ts estendido para aceitar FormData (upload via Server
  Action, sem Route Handler intermediário). Limitação de autorização de
  sub-usuário em evidências/mensagens documentada como fora do escopo
  (bug de backend já registrado em B.3/B.4).

Verificação avulsa — B.4 (chat persistido): conferido código real contra a
documentação existente, confirmada correta; corrigidos apenas 2 números de
linha desatualizados (177->180, 181->184) por deslocamento causado pela
correção anterior do B.3.

Lote 4 — G (testes automatizados) e H (DevOps), ambos VALIDADOS DE VERDADE
antes de documentados (código criado, executado, resultado real registrado,
removido do repositório em seguida — mesmo padrão documentação-only dos
lotes anteriores):
- G: 7 arquivos de teste (pytest.ini, conftest.py, 5 test_*.py) criados e
  executados contra SQLite em memória isolado — 26/26 testes passaram,
  83% de cobertura (pytest --cov=app). Cada teste sensível a regressão
  histórica (B.3, B.6, C.2.a, C.2.b, A.6, A.12) documentado com comentário
  explicando qual bug ele pegaria. Confirmado que a suíte não vaza arquivos
  para backend/uploads/ real (fixture _isolate_uploads via monkeypatch).
- H: backend/Dockerfile e frontend/Dockerfile buildados com "docker build"
  e executados com "docker run" contra o MySQL real do projeto — backend
  respondeu {"status":"Ok","db_status":"Ok"} em /health, frontend serviu
  200 em / e /public/login. ruff check testado com regras completas (63
  erros, majoritariamente E501 em company_dashboard.py — não realista sem
  reformatar o projeto) versus a configuração final documentada em
  ruff.toml (select=["F"], ignore=["F821"] — falso-positivo confirmado do
  SQLAlchemy Mapped["NomeDaClasse"] como forward reference): 11 erros
  reais (imports não usados), listados como limpeza única a fazer antes de
  habilitar o job de CI. docker-compose.yml raiz e .github/workflows/ci.yml
  documentados com base nos dois Dockerfiles validados.

Nenhuma mudança de código de produção foi aplicada por este commit — só
docs/plano_implementacao.md (5367 inserções, 226 remoções; arquivo total
agora com 6225 linhas). O único arquivo de código tocado
(backend/app/api/v1/client.py) é uma reformatação/comentário cosmético
pré-existente na working tree no início desta sessão de documentação (não
autoria deste commit), sem mudança de comportamento — incluído aqui só
para manter a árvore de trabalho limpa.

Não incluído neste commit: Prompt_Analise_de_projeto.txt e
Prompt_Atualizar_Plano_Implemetacao.txt (prompts pessoais, não são código
do projeto).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (2 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `backend/app/api/v1/client.py` | Interface do Cliente |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |

### Funcionalidades Impactadas

- Documentação Técnica
- Interface do Cliente

### Correções Realizadas

- Nenhuma referência a bug (formato `B-X00`) identificada neste commit.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo do projeto.

### Próximos Passos Recomendados

- Revisar consistência com outros documentos em `docs/`.
- Verificar se `docs/setup_completo.md` precisa de atualização.

---

## Commit `707e854` — 2026-08-05 16:41:00

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🚀 Nova Funcionalidade (`feat`) |
| **Hash Completo** | `707e85442d820dc8fc8c9655eecba25cdba73983` |
| **Arquivos Alterados** | 10 arquivo(s) |

### Título do Commit

```
feat(backend,frontend): implementa JWT refresh token (A.10)
```

### Descrição

Contexto: item A.10 do plano de implementação estava marcado como
pendente/opcional para o MVP. Implementado e validado de ponta a ponta
nesta sessão.

Backend:
- core/config.py: nova setting JWT_REFRESH_EXPIRES_DAYS (padrão 7 dias).
- core/jwt.py: create_access_token() agora inclui "type": "access" no
  payload. Nova create_refresh_token(subject) — payload
  {sub, type=refresh, exp}, sem role (o role é sempre relido do banco no
  momento do refresh, não fica congelado no token de vida longa). Nova
  decode_refresh_token(), que reaproveita decore_token() mas recusa
  qualquer token cujo type não seja "refresh".
- api/deps.py::get_current_user: passa a rejeitar qualquer token cujo
  type seja diferente de "access"/ausente, impedindo que um
  refresh_token seja usado diretamente em endpoints autenticados. Tokens
  antigos sem claim "type" (emitidos antes desta mudança) continuam
  aceitos — ninguém é deslogado à força.
- schemas/auth.py: TokenResponse ganhou refresh_token: str; novo
  RefreshTokenRequest.
- api/v1/auth.py: POST /auth/login agora retorna access_token e
  refresh_token. Novo POST /auth/refresh (rate-limited 10/minute, mesmo
  padrão de limiter do /login): valida o refresh_token, relê o usuário
  no banco e emite um novo par access/refresh (rotação simples a cada
  uso).
- .env.example: documenta JWT_REFRESH_EXPIRES_DAYS (opcional, já tem
  default no código).

Frontend (integração mínima, para o endpoint novo não ficar órfão):
- app/api/auth/login/route.ts: grava dois cookies httpOnly agora
  (access_token curto + refresh_token longo, JWT_REFRESH_EXPIRES_DAYS
  dias).
- app/api/auth/logout/route.ts: limpa os dois cookies.
- app/api/auth/refresh/route.ts (novo): lê o cookie refresh_token, chama
  POST /api/v1/auth/refresh e regrava os dois cookies com os novos
  valores, ou limpa ambos e retorna 401 se o refresh falhar.

Fora de escopo, por decisão registrada em docs/plano_implementacao.md:
nenhum fluxo do frontend chama /api/auth/refresh automaticamente ainda
(ex. interceptar 401 e tentar renovar antes de redirecionar pro login)
— isso fica para a migração de sessão do Bloco D (D.1, Server
Components/DAL), que já vai redesenhar como o frontend gerencia sessão;
implementar auto-refresh em cima da arquitetura client-side atual
duplicaria trabalho.

Validação executada (não só leitura de código):
- Unitário (Python): access token inclui type=access; refresh token
  inclui type=refresh e não inclui role; decode_refresh_token rejeita um
  access_token; token "estilo antigo" sem type continua decodificando
  (retrocompatibilidade).
- HTTP direto no backend (uvicorn + MySQL real): login retorna os dois
  tokens; GET /users/perfil com access_token -> 200; POST /auth/refresh
  com refresh_token -> 200 com novo par; GET /users/perfil com o novo
  access_token -> 200; refresh_token usado como access_token -> 401;
  access_token usado como refresh_token -> 401; token malformado -> 401.
- Ponta a ponta via Next.js (backend + npm run dev + MySQL real):
  POST /api/auth/login grava os dois cookies; GET /api/profile funciona;
  POST /api/auth/refresh renova os cookies; GET /api/profile funciona de
  novo; POST /api/auth/logout limpa os cookies; POST /api/auth/refresh
  após logout -> 401 Sessão expirada.

docs/plano_implementacao.md: A.10 atualizado para Concluído, com o
detalhamento da implementação, dos testes executados e da limitação
conhecida (sem revogação server-side — solução stateless, sem tabela de
sessões no banco; rotação do refresh token a cada uso reduz mas não
elimina a janela de reuso de um token vazado).

Não incluído neste commit: Prompt_Analise_de_projeto.txt e
Prompt_Atualizar_Plano_Implemetacao.txt (prompts pessoais, não são
código do projeto).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (10 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `backend/.env.example` | Outro / Não Categorizado |
| Modificado | `backend/app/api/deps.py` | Autenticação / Login |
| Modificado | `backend/app/api/v1/auth.py` | Autenticação / Login |
| Modificado | `backend/app/core/config.py` | Configuração e Segurança |
| Modificado | `backend/app/core/jwt.py` | Configuração e Segurança |
| Modificado | `backend/app/schemas/auth.py` | Schemas / Validação de Dados |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |
| Modificado | `frontend/app/api/auth/login/route.ts` | Proxy Auth (Next.js → FastAPI) |
| Modificado | `frontend/app/api/auth/logout/route.ts` | Proxy Auth (Next.js → FastAPI) |
| Adicionado | `frontend/app/api/auth/refresh/route.ts` | Proxy Auth (Next.js → FastAPI) |

### Funcionalidades Impactadas

- Autenticação / Login
- Configuração e Segurança
- Documentação Técnica
- Outro / Não Categorizado
- Proxy Auth (Next.js → FastAPI)
- Schemas / Validação de Dados

### Correções Realizadas

- Nenhuma referência a bug (formato `B-X00`) identificada neste commit.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo do projeto.

### Próximos Passos Recomendados

- Adicionar testes automatizados para a nova funcionalidade.
- Atualizar `docs/relatorio_funcionalidades.md` se a feature agora está completa.
- Verificar se há dependências com funcionalidades pendentes no `docs/roadmap.md`.

---

## Commit `1a69192` — 2026-08-05 16:02:05

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 📌 Alteração Geral (`other`) |
| **Hash Completo** | `1a69192df9230b5aa83dab27404978d49d1b7bcc` |
| **Arquivos Alterados** | 7 arquivo(s) |

### Título do Commit

```
docs+fix(backend): reescreve plano de implementação e corrige 4 bugs P0
```

### Descrição

Contexto: análise completa do projeto (backend + frontend) comparando
código-fonte real com a documentação existente, seguida da correção dos
bugs de maior prioridade identificados.

docs/plano_implementacao.md — reescrita completa (v3.1 -> v4.0):
- Documento reorganizado em blocos por dependência técnica (Fundação ->
  Funcionalidades Core -> Onboarding -> Testes -> Frontend -> Refatoração
  -> Observabilidade -> DevOps), substituindo as fases cronológicas
  anteriores.
- Cada implementação revalidada por leitura direta do código (não da
  documentação anterior nem de mensagens de commit), com status
  justificado, código real e números de linha.
- Identificadas e documentadas duas regressões: upload de evidências e
  paginação de auditorias, ambas já haviam sido corrigidas e validadas
  em runtime (FASE 1B do plano anterior) e foram revertidas pelo commit
  aa9d61b.
- Identificados dois bugs novos, não documentados antes, no onboarding
  de cliente (Company.phone e DashboardCard.control_code NOT NULL vs.
  dados tratados como opcionais pela API/UI).
- Identificados achados adicionais do agente de análise de backend:
  ordem de validação invertida em POST /auth/register, duas instâncias
  de Limiter (slowapi) deixando headers de rate-limit inconsistentes,
  autorização de sub-usuário não resolvida em evidências/mensagens, e
  inventário de código morto/funcionalidades órfãs (checklistItem
  clássico sem API, DashboardCardNote sem API, schemas não usados).
- Bloco de testes automatizados reposicionado para logo após as
  funcionalidades core, dado que a maioria dos bugs encontrados são
  recorrências que uma suíte mínima teria pego.

Correção dos 4 bugs P0 identificados (todos validados nesta sessão):

- app/api/v1/client.py: upload_evidence() instanciava Evidence com
  kwargs inexistentes no model (original_file_name, uploaded_by_user_id).
  Corrigido para storage_key/file_name/uploaded_by_id, com mime_type e
  size_bytes preenchidos. Validado instanciando Evidence(**kwargs) sem
  TypeError.

- app/api/v1/admin.py: GET /admin/audits usava
  response_model=PaginatedResponse sem parametrizar o generic e devolvia
  instâncias ORM cruas em items, causando PydanticSerializationError
  sempre que havia ao menos uma auditoria no banco (reproduzido e
  confirmado antes da correção). Corrigido para
  PaginatedResponse[AuditOut] com AuditOut.model_validate(a) por item.

- app/models/company_dashboard.py + schemas/dashboard_runtime.py: dois
  bugs de onboarding não documentados antes de hoje —
  Company.phone e DashboardCard.control_code eram NOT NULL no banco mas
  tratados como opcionais pelo schema/UI de onboarding, quebrando com
  IntegrityError sempre que o admin deixava o telefone em branco ou
  usava um template com cards. Colunas relaxadas para nullable (criação
  manual de card via POST /dashboard/companies/{id}/cards continua
  exigindo control_code, validação feita no schema Pydantic, não no
  banco). Migration nova alembic/versions/5457e7377a56 aplicada contra o
  MySQL real; fluxo completo de onboarding com template e sem telefone
  testado de ponta a ponta (User+Company+Dashboard+3 DashboardCard),
  dados de teste removidos em seguida.

- scripts/seed_catalog.py: corrigido o último typo residual
  ('colaboradoress' -> 'colaboradores') de uma leva de correções
  anteriores. Seed reexecutado para inserir o registro corrigido; as
  duas linhas antigas com o typo foram removidas do banco após
  confirmar ausência de referências em checklist_item_state.

Não incluído neste commit: Prompt_Analise_de_projeto.txt e
Prompt_Atualizar_Plano_Implemetacao.txt (prompts pessoais usados para
gerar esta revisão, não são código do projeto).

Pendente (fora do escopo P0, ver docs/plano_implementacao.md, tabela de
prioridades): suíte de testes automatizados (P1) e resolução de
parent_user_id de sub-usuário em evidências/mensagens (P1).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (7 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Adicionado | `backend/alembic/versions/5457e7377a56_relax_company_phone_and_card_control_.py` | Banco de Dados / Migrações |
| Modificado | `backend/app/api/v1/admin.py` | Painel do Administrador |
| Modificado | `backend/app/api/v1/client.py` | Interface do Cliente |
| Modificado | `backend/app/models/company_dashboard.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/schemas/dashboard_runtime.py` | Schemas / Validação de Dados |
| Modificado | `backend/scripts/seed_catalog.py` | Scripts de Inicialização / Seeds |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |

### Funcionalidades Impactadas

- Banco de Dados / Migrações
- Documentação Técnica
- Interface do Cliente
- Modelos de Dados (ORM)
- Painel do Administrador
- Schemas / Validação de Dados
- Scripts de Inicialização / Seeds

### Correções Realizadas

- Nenhuma referência a bug (formato `B-X00`) identificada neste commit.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo do projeto.

### Próximos Passos Recomendados

- Revisar os arquivos modificados em contexto com `docs/relatorio_bugs.md`.
- Consultar `docs/roadmap.md` para verificar alinhamento com o plano de desenvolvimento.

---

## Commit `96f88ce` — 2026-08-05 14:10:02

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🚀 Nova Funcionalidade (`feat`) |
| **Hash Completo** | `96f88ce994e1193c2714117a895607d28474ef9a` |
| **Arquivos Alterados** | 9 arquivo(s) |

### Título do Commit

```
feat(backend,frontend): health check, timestamp/soft-delete mixins ativos e validação de role no middleware
```

### Descrição

Continuação do trabalho da aula/tutorial em andamento na working tree
(comentários "Continuar a aula 2.4" no middleware antigo). Revisei tudo
que apareceu desde o commit anterior e corrigi 3 bugs antes de
commitar.

Backend:
- api/health.py (novo): GET /health faz SELECT 1 no banco e retorna
  status/db_status/timestamp. Registrado em main.py.
  BUG corrigido: o router já define a rota como "/health" e main.py
  registrava com prefix="/health" de novo, resultando em
  "/health/health". Removido o prefixo duplicado no include_router.
- models/user.py e models/audit.py: agora herdam de TimestampMixim e
  SoftDeleteMixin (db/mixins.py), então created_at/updated_at/
  deleted_at passam a ser gerenciados pelo ORM nesses dois models
  (colunas já existem no banco desde a migration 5e977e8b49da).
  BUG corrigido: os dois imports apontavam para
  app.db.create_with_controls — nome antigo do arquivo, restaurado
  para app.db.mixins no commit anterior (710324a). O arquivo tinha
  voltado a se chamar create_with_controls.py na working tree
  (suspeita de sync do OneDrive/NextCloud revertendo o rename);
  renomeado de volta para mixins.py e os imports corrigidos.

Frontend:
- middleware.ts: adiciona validação de role para rotas
  /private/admin/* via jwt-decode (client não-admin é redirecionado
  para /private/client). Nova dependência jwt-decode em package.json/
  package-lock.json.
  BUG corrigido: usava a variável `accessToken`, que não existe nesse
  escopo (a variável é `token`) — gerava ReferenceError em toda
  requisição para /private/admin/*. Também restaurei o redirecionamento
  para /public/login em qualquer /private/* sem token, que tinha sido
  removido por completo em vez de mantido junto da checagem de role
  (regressão de segurança: rotas privadas não-admin, ex. /private/client,
  ficaram sem checagem de autenticação nenhuma).
- layout.tsx: envolve o layout privado em AuthProvider
  (lib/auth-context.tsx) e remove o wrapper <main>/<div> redundante.
- sub-user-requests-panel.tsx: only formatação/copy (import ordering,
  espaço extra, travessão, cor do botão Aprovar).

Não incluído neste commit: Prompt_Analise_de_projeto.txt e
Prompt_Atualizar_Plano_Implemetacao.txt (prompts pessoais para
regenerar os relatórios em docs/, não são código do projeto).

### Arquivos Modificados (9 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Adicionado | `backend/app/api/health.py` | Health Check / Observabilidade |
| Modificado | `backend/app/main.py` | Outro / Não Categorizado |
| Modificado | `backend/app/models/audit.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/user.py` | Modelos de Dados (ORM) |
| Modificado | `frontend/app/private/admin_components/sub-user-requests-panel.tsx` | Outro / Não Categorizado |
| Modificado | `frontend/app/private/layout.tsx` | Layout Privado (Frontend) |
| Modificado | `frontend/middleware.ts` | Middleware de Autenticação (legado) |
| Modificado | `frontend/package-lock.json` | Outro / Não Categorizado |
| Modificado | `frontend/package.json` | Dependências Node.js |

### Funcionalidades Impactadas

- Dependências Node.js
- Health Check / Observabilidade
- Layout Privado (Frontend)
- Middleware de Autenticação (legado)
- Modelos de Dados (ORM)
- Outro / Não Categorizado

### Correções Realizadas

- Nenhuma referência a bug (formato `B-X00`) identificada neste commit.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo do projeto.

### Próximos Passos Recomendados

- Adicionar testes automatizados para a nova funcionalidade.
- Atualizar `docs/relatorio_funcionalidades.md` se a feature agora está completa.
- Verificar se há dependências com funcionalidades pendentes no `docs/roadmap.md`.

---

## Commit `710324a` — 2026-08-05 12:20:53

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🐛 Correção de Bug (`fix`) |
| **Hash Completo** | `710324a8af0b5e37b76efce56de1294464f430af` |
| **Arquivos Alterados** | 7 arquivo(s) |

### Título do Commit

```
fix(backend): refatora criação de auditoria via repository e corrige 2 regressões críticas
```

### Descrição

Contexto: durante a investigação de uma migration duplicada
(5891af95a16d, arquivo não versionado e já removido do disco — duplicava
5e977e8b49da e causava "Duplicate column name 'updated_at'" no
alembic upgrade), revisei o restante das mudanças pendentes na working
tree e encontrei 2 bugs que quebrariam produção se fossem commitados
como estavam.

Correções críticas:
- app/services/users.py: get_user_by_email() calculava o resultado em
  `existing_user` mas não fazia `return`, então sempre voltava None.
  Isso derrubava authenticate_user() (login sempre 401) e todo check
  de e-mail duplicado (register/sub-users/onboarding). É regressão do
  bug B-C16 (docs/relatorio_bugs.md), já corrigido antes e reintroduzido
  nesta working tree — restaurado o `return`.
- app/schemas/admin.py: AuditCreateRequest usava o campo `client_use_id`
  (typo, bug B-M02 do relatório), que não batia com
  `payload.client_user_id` referenciado no novo admin.py, causando
  AttributeError em toda chamada de POST /admin/audits. Renomeado para
  `client_user_id`, consistente com o model Audit e com
  AuditRepository.

Refatoração:
- api/v1/admin.py: create_audit_and_instantiate_controls() tinha toda a
  lógica de criação de auditoria (validar cliente, buscar catálogo,
  criar Audit + AuditControl em loop) inline na rota. Extraída para
  AuditRepository.create_with_controls(), que já existia mas não era
  usada. Rota renomeada para create_audit(), resposta trocada de
  AuditCreateResponse para AuditOut (schema já usado no GET) e o
  parâmetro de dependência de admin passou de `_` para `admin` (nome
  descritivo, mesmo sem uso direto).
- db/create_with_controls.py -> db/mixins.py: arquivo continha
  TimestampMixim/SoftDeleteMixin mas estava salvo com o nome errado
  (nome de método de outro módulo). Renomeado para refletir o
  conteúdo real; ainda não está importado por nenhum model.

Limpeza:
- main.py e repositories/audit_repository.py: apenas formatação
  (espaços em branco, linhas em branco duplicadas, newline final
  faltando) sem mudança de comportamento.

Não incluído neste commit: Prompt_Analise_de_projeto.txt e
Prompt_Atualizar_Plano_Implemetacao.txt (prompts pessoais usados para
regenerar os relatórios em docs/, não são código do projeto).

### Arquivos Modificados (7 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `backend/app/api/v1/admin.py` | Painel do Administrador |
| Removido | `backend/app/db/create_with_controls.py` | Conexão com Banco de Dados |
| Adicionado | `backend/app/db/mixins.py` | Conexão com Banco de Dados |
| Modificado | `backend/app/main.py` | Outro / Não Categorizado |
| Modificado | `backend/app/repositories/audit_repository.py` | Repository Pattern (ORM) |
| Modificado | `backend/app/schemas/admin.py` | Schemas / Validação de Dados |
| Modificado | `backend/app/services/users.py` | Serviços / Lógica de Negócio |

### Funcionalidades Impactadas

- Conexão com Banco de Dados
- Outro / Não Categorizado
- Painel do Administrador
- Repository Pattern (ORM)
- Schemas / Validação de Dados
- Serviços / Lógica de Negócio

### Correções Realizadas

- Referências a bugs detectadas: **B-C16, B-M02**
  - Consulte `docs/relatorio_bugs.md` para detalhes de cada item.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo do projeto.

### Próximos Passos Recomendados

- Verificar se o mesmo bug ocorre em contextos similares no código.
- Adicionar teste de regressão para garantir que o problema não retorne.
- Atualizar `docs/relatorio_bugs.md` marcando o bug como corrigido (se aplicável).

---

## Commit `aa9d61b` — 2026-08-04 17:56:08

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🐛 Correção de Bug (`fix`) |
| **Hash Completo** | `aa9d61b6eff62527df81d5f28647e7271998e0f0` |
| **Arquivos Alterados** | 8 arquivo(s) |

### Título do Commit

```
fix(backend): corrige migration duplicada de índices e ajusta upload/paginação
```

### Descrição

- alembic: torna a migration d5c4d7cd6687_add_performance_indices idempotente
  (checagem via information_schema.statistics antes de criar/derrubar cada
  índice), pois ix_audit_controls_status, ix_audits_client_user_id e
  ix_audits_status já eram criados pela migration anterior
  56d322bbd83a_add_performance_indices, causando erro 1061 "Duplicate key
  name" ao rodar `alembic upgrade head`.

- api/v1/client.py: corrige upload_evidence, que estava instanciando o
  model Evidence com campos inexistentes (storage_key, uploaded_by_id,
  mime_type, size_bytes). Ajustado para os campos reais do model
  (file_name, original_file_name, uploaded_by_user_id).

- api/v1/admin.py: list_audits volta a usar PaginatedResponse sem o
  parâmetro genérico explícito [AuditOut] na assinatura/retorno, evitando
  incompatibilidade de tipos no response_model.

- api/v1/dashboard_cards.py, schemas/pagination.py, services/email_sender.py,
  services/storage.py: formatação (black) sem mudança de comportamento.

- docs/plano_implementacao.md: atualiza o plano de implementação com o
  progresso e estado atual do projeto.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (8 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Adicionado | `backend/alembic/versions/d5c4d7cd6687_add_performance_indices.py` | Banco de Dados / Migrações |
| Modificado | `backend/app/api/v1/admin.py` | Painel do Administrador |
| Modificado | `backend/app/api/v1/client.py` | Interface do Cliente |
| Modificado | `backend/app/api/v1/dashboard_cards.py` | Dashboard Gerencial / Cards |
| Modificado | `backend/app/schemas/pagination.py` | Schemas / Validação de Dados |
| Modificado | `backend/app/services/email_sender.py` | Serviços / Lógica de Negócio |
| Modificado | `backend/app/services/storage.py` | Serviços / Lógica de Negócio |
| Modificado | `docs/plano_implementacao.md` | Documentação Técnica |

### Funcionalidades Impactadas

- Banco de Dados / Migrações
- Dashboard Gerencial / Cards
- Documentação Técnica
- Interface do Cliente
- Painel do Administrador
- Schemas / Validação de Dados
- Serviços / Lógica de Negócio

### Correções Realizadas

- Nenhuma referência a bug (formato `B-X00`) identificada neste commit.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo do projeto.

### Próximos Passos Recomendados

- Verificar se o mesmo bug ocorre em contextos similares no código.
- Adicionar teste de regressão para garantir que o problema não retorne.
- Atualizar `docs/relatorio_bugs.md` marcando o bug como corrigido (se aplicável).

---

## Commit `d5c16b5` — 2026-07-27 09:58:06

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 📝 Documentação (`docs`) |
| **Hash Completo** | `d5c16b57e8d3fed13b502306e497d99311674d31` |
| **Arquivos Alterados** | 33 arquivo(s) |

### Título do Commit

```
docs: move @developer/ para docs/ e sincroniza com o estado atual do projeto
```

### Descrição

Reorganiza a pasta de documentação técnica de @developer/ para docs/ e
remove a nota de correção pontual correcao_alembic.md, já superada pelo
conteúdo consolidado abaixo.

Atualiza toda a documentação (16 arquivos) para refletir o estado real do
backend/frontend em HEAD, incluindo:
- plano_implementacao.md (v3.0): nova FASE 1B documentando e corrigindo
  5 regressões críticas introduzidas pelos commits dce4dd3/d0a3266 (login,
  upload de evidências, chat, checklist de dashboard, paginação), mais os
  pontos de integração pendentes entre frontend e backend (AuthContext,
  painel de sub-usuários duplicado, middleware sem checagem de role)
- relatorio_bugs.md (v2.0): 6 bugs novos catalogados (B-C16..B-C21),
  status de correção atualizado nos bugs pré-existentes
- relatorio_funcionalidades.md, relatorio_geral.md, roadmap.md,
  dashboard_projeto.md, index.md, relatorio_documentacao.md,
  relatorio_melhorias.md: datas, métricas e status sincronizados
- setup_completo.md, executar_projeto.md, deploy_producao.md,
  automacao_commits.md: avisos operacionais e referências corrigidas

Todas as correções da FASE 1B foram aplicadas e validadas em runtime
(commit anterior); a documentação já reflete esse estado corrigido.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (33 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Removido | `@developer/automacao_commits.md` | Outro / Não Categorizado |
| Removido | `@developer/dashboard_projeto.md` | Outro / Não Categorizado |
| Removido | `@developer/deploy_producao.md` | Outro / Não Categorizado |
| Removido | `@developer/executar_projeto.md` | Outro / Não Categorizado |
| Removido | `@developer/index.md` | Outro / Não Categorizado |
| Removido | `@developer/mindmeister_automacao.md` | Outro / Não Categorizado |
| Removido | `@developer/plano_implementacao.md` | Outro / Não Categorizado |
| Removido | `@developer/relatorio_bugs.md` | Outro / Não Categorizado |
| Removido | `@developer/relatorio_commit.md` | Outro / Não Categorizado |
| Removido | `@developer/relatorio_documentacao.md` | Outro / Não Categorizado |
| Removido | `@developer/relatorio_funcionalidades.md` | Outro / Não Categorizado |
| Removido | `@developer/relatorio_geral.md` | Outro / Não Categorizado |
| Removido | `@developer/relatorio_melhorias.md` | Outro / Não Categorizado |
| Removido | `@developer/roadmap.md` | Outro / Não Categorizado |
| Removido | `@developer/setup_completo.md` | Outro / Não Categorizado |
| Removido | `@developer/trello_automacao.md` | Outro / Não Categorizado |
| Removido | `correcao_alembic.md` | Outro / Não Categorizado |
| Adicionado | `docs/automacao_commits.md` | Documentação Técnica |
| Adicionado | `docs/dashboard_projeto.md` | Documentação Técnica |
| Adicionado | `docs/deploy_producao.md` | Documentação Técnica |
| Adicionado | `docs/executar_projeto.md` | Documentação Técnica |
| Adicionado | `docs/index.md` | Documentação Técnica |
| Adicionado | `docs/mindmeister_automacao.md` | Documentação Técnica |
| Adicionado | `docs/plano_implementacao.md` | Documentação Técnica |
| Adicionado | `docs/relatorio_bugs.md` | Documentação Técnica |
| Adicionado | `docs/relatorio_commit.md` | Documentação Técnica |
| Adicionado | `docs/relatorio_documentacao.md` | Documentação Técnica |
| Adicionado | `docs/relatorio_funcionalidades.md` | Documentação Técnica |
| Adicionado | `docs/relatorio_geral.md` | Documentação Técnica |
| Adicionado | `docs/relatorio_melhorias.md` | Documentação Técnica |
| Adicionado | `docs/roadmap.md` | Documentação Técnica |
| Adicionado | `docs/setup_completo.md` | Documentação Técnica |
| Adicionado | `docs/trello_automacao.md` | Documentação Técnica |

### Funcionalidades Impactadas

- Documentação Técnica
- Outro / Não Categorizado

### Correções Realizadas

- Referências a bugs detectadas: **B-C16, B-C21**
  - Consulte `docs/relatorio_bugs.md` para detalhes de cada item.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo do projeto.

### Próximos Passos Recomendados

- Revisar consistência com outros documentos em `docs/`.
- Verificar se `docs/setup_completo.md` precisa de atualização.

---

## Commit `8036834` — 2026-07-27 09:57:46

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🐛 Correção de Bug (`fix`) |
| **Hash Completo** | `803683414b5059fe145578bc728670ffb02ed205` |
| **Arquivos Alterados** | 5 arquivo(s) |

### Título do Commit

```
fix(backend): corrige regressões críticas de login, upload, chat e checklist
```

### Descrição

Corrige 6 bugs introduzidos pelos commits dce4dd3/d0a3266 que deixavam a
plataforma inutilizável: login/cadastro sempre falhando (get_user_by_email
sem return), upload de evidências e checklist de dashboard quebrados por
incompatibilidade de campos/schema, JOIN incorreto no chat, paginação sem
tipo genérico e import de Path colidindo entre fastapi/pathlib.

- app/services/users.py: adiciona return em get_user_by_email
- app/api/v1/client.py: corrige campos de Evidence(...), extensões
  .docx/.xlsx, JOIN de send_message, e import Path (pathlib, não fastapi)
- app/api/v1/admin.py + schemas/admin.py: adiciona AuditOut e parametriza
  PaginatedResponse[AuditOut] em GET /admin/audits
- alembic: nova migration 5a9233d65599 corrige a PK de
  dashboard_card_checklist_items (iid -> id), deixada inconsistente pela
  migration d60f999c1fca

Corrigido, aplicado e validado via HTTP contra um MySQL real (login,
upload de evidências, chat, paginação e checklist testados de ponta a
ponta). Ver docs/plano_implementacao.md FASE 1B para o detalhamento.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Arquivos Modificados (5 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Adicionado | `backend/alembic/versions/5a9233d65599_fix_dashboard_card_checklist_items_pk.py` | Banco de Dados / Migrações |
| Modificado | `backend/app/api/v1/admin.py` | Painel do Administrador |
| Modificado | `backend/app/api/v1/client.py` | Interface do Cliente |
| Modificado | `backend/app/schemas/admin.py` | Schemas / Validação de Dados |
| Modificado | `backend/app/services/users.py` | Serviços / Lógica de Negócio |

### Funcionalidades Impactadas

- Banco de Dados / Migrações
- Interface do Cliente
- Painel do Administrador
- Schemas / Validação de Dados
- Serviços / Lógica de Negócio

### Correções Realizadas

- Nenhuma referência a bug (formato `B-X00`) identificada neste commit.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo do projeto.

### Próximos Passos Recomendados

- Verificar se o mesmo bug ocorre em contextos similares no código.
- Adicionar teste de regressão para garantir que o problema não retorne.
- Atualizar `docs/relatorio_bugs.md` marcando o bug como corrigido (se aplicável).

---

## Commit `d0a3266` — 2026-06-26 17:01:18

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🚀 Nova Funcionalidade (`feat`) |
| **Hash Completo** | `d0a32661afb8f7c6a4212a1ed0d679c853dfd0ac` |
| **Arquivos Alterados** | 11 arquivo(s) |

### Título do Commit

```
feat(backend/frontend): logging estruturado, repositórios, mixins e componentes admin
```

### Descrição

### Observabilidade — structlog
- Adiciona backend/app/core/logging.py com configure_logging() que inicializa
  structlog (JSONRenderer + TimeStamper ISO + merge_contextvars) respeitando IS_DEBUG
- Adiciona backend/app/middleware/request_id.py: RequestIDMiddleware que gera UUID
  por requisição, injeta em structlog via bind_contextvars e retorna X-Request-ID
  no header da resposta, facilitando rastreamento de logs em produção
- Registra RequestIDMiddleware e chama configure_logging() no main.py na inicialização
- Adiciona structlog nas dependências (requirements.txt)

### Camada de repositórios (Repository Pattern)
- Cria backend/app/repositories/user_repository.py com UserRepository:
    get_by_id, get_by_email, list_by_role, create (com flush para retornar id)
- Cria backend/app/repositories/audit_repository.py com AuditRepository:
    get_by_id, list_by_client, create_with_controls (instancia todos os controles
    do catálogo automaticamente via flush)
- Refatora services/users.py: get_user_by_email passa a usar UserRepository,
  isolando queries SQL da camada de serviço

### Mixins de modelo (Timestamp e SoftDelete)
- Cria backend/app/db/create_with_controls.py com:
    TimestampMixin: campos created_at e updated_at com server_default e onupdate
    SoftDeleteMixin: campo deleted_at nullable + propriedade is_deleted
- Esses mixins serão aplicados progressivamente nos modelos existentes

### Migration — timestamps e soft delete
- Adiciona migration 5e977e8b49da que aplica colunas updated_at e deleted_at
  nas tabelas users, audits e audit_controls (encadeia após 56d322bbd83a)

### Frontend — painel admin e contexto de autenticação
- Cria frontend/app/private/admin_components/sub-user-requests-panel.tsx:
    componente SubUserRequestsPanel que lista solicitações pendentes de sub-usuários
    e permite aprovar individualmente com chamada ao endpoint de aprovação
- Cria frontend/lib/auth-context.tsx:
    AuthContext com AuthProvider que busca /api/profile ao montar e expõe
    user (id, email, full_name, role), loading e refresh()
    Hook useAuth() para consumo nos componentes filhos

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Arquivos Modificados (11 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Adicionado | `backend/alembic/versions/5e977e8b49da_add_timestamp_and_soft_delete_columns.py` | Banco de Dados / Migrações |
| Adicionado | `backend/app/core/logging.py` | Configuração e Segurança |
| Adicionado | `backend/app/db/create_with_controls.py` | Conexão com Banco de Dados |
| Modificado | `backend/app/main.py` | Outro / Não Categorizado |
| Adicionado | `backend/app/middleware/request_id.py` | Middleware / Observabilidade |
| Adicionado | `backend/app/repositories/audit_repository.py` | Repository Pattern (ORM) |
| Adicionado | `backend/app/repositories/user_repository.py` | Repository Pattern (ORM) |
| Modificado | `backend/app/services/users.py` | Serviços / Lógica de Negócio |
| Modificado | `backend/requirements.txt` | Dependências Python |
| Adicionado | `frontend/app/private/admin_components/sub-user-requests-panel.tsx` | Outro / Não Categorizado |
| Adicionado | `frontend/lib/auth-context.tsx` | Utilitários do Frontend |

### Funcionalidades Impactadas

- Banco de Dados / Migrações
- Conexão com Banco de Dados
- Configuração e Segurança
- Dependências Python
- Middleware / Observabilidade
- Outro / Não Categorizado
- Repository Pattern (ORM)
- Serviços / Lógica de Negócio
- Utilitários do Frontend

### Correções Realizadas

- Nenhuma referência a bug (formato `B-X00`) identificada neste commit.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo do projeto.

### Próximos Passos Recomendados

- Adicionar testes automatizados para a nova funcionalidade.
- Atualizar `docs/relatorio_funcionalidades.md` se a feature agora está completa.
- Verificar se há dependências com funcionalidades pendentes no `docs/roadmap.md`.

---

## Commit `dce4dd3` — 2026-06-26 14:18:42

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🚀 Nova Funcionalidade (`feat`) |
| **Hash Completo** | `dce4dd331f938478512e641b693f2004f7513904` |
| **Arquivos Alterados** | 35 arquivo(s) |

### Título do Commit

```
feat(backend): segurança, upload de evidências, paginação e performance
```

### Descrição

### Segurança
- Adiciona middleware SecurityHeadersMiddleware com headers X-Content-Type-Options,
  X-Frame-Options, X-XSS-Protection, Referrer-Policy e Permissions-Policy
- Integra slowapi no FastAPI: rate limit global + decorator 5/minute no POST /auth/login
- Valida força de senha no schema UserCreate via field_validator (mín. 8 chars,
  ao menos uma maiúscula e um número)
- Corrige encoding explícito UTF-8 no bcrypt hash/verify (security.py)
- Remove senha temporária dos logs de e-mail em ambiente dev (email_sender.py)
- Adiciona SELECT FOR UPDATE no approve_request de sub-usuários para evitar race condition

### Novos endpoints e funcionalidades
- POST /client/controls/{id}/evidences: upload de evidência com validação de tipo
  (pdf, png, jpg, jpeg, webp, docx, xlsx) e tamanho (max 10 MB)
- GET /client/controls/{id}/messages: listagem de mensagens de um controle
- POST /client/controls/{id}/messages: envio de mensagem em um controle
- GET /admin/audits: listagem paginada de auditorias (usa PaginatedResponse genérico)

### Novos arquivos
- backend/app/middleware/security_headers.py: middleware de headers HTTP de segurança
- backend/app/schemas/pagination.py: schema genérico PaginatedResponse[T]
- backend/app/services/storage.py: serviço assíncrono de armazenamento de arquivos (aiofiles)
- backend/alembic/versions/56d322bbd83a_add_performance_indices.py: migration que
  adiciona índices em audit_controls.status, audits.client_user_id e audits.status

### Correções e refatorações
- Renomeia ChecklistItem/ChecklistItemState → checklistItem/checklistItemState em models,
  schemas e scripts para consistência com convenção local
- Renomeia DashboardCardChecklistItem → DashboardCardchecklistItem e corrige PK iid → id
- Corrige toggle_checklist_item: admin acessa diretamente; cliente valida ownership via JOIN
- Corrige bug no seed_catalog.py: comparações == trocadas por = na atualização de campos
- Corrige typos em dados do seed (comunicação, colaboradores)
- Habilita ALLOW_PUBLIC_REGISTRATION=True por padrão (dev); documenta variável no .env.example
- Adiciona variáveis ADMIN_EMAIL/ADMIN_FULL_NAME/ADMIN_PASSWORD no .env.example
- Adiciona dependências: slowapi==0.1.9, python-multipart==0.0.9, aiofiles==23.2.1
- Melhora template de e-mail de credenciais do sub-usuário com logging estruturado

### Documentação (@developer)
- Atualiza plano_implementacao.md com progresso e próximas etapas
- Atualiza relatorio_bugs.md, relatorio_funcionalidades.md, roadmap.md e demais relatórios

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Arquivos Modificados (35 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Adicionado | `.vscode/settings.json` | Outro / Não Categorizado |
| Modificado | `@developer/dashboard_projeto.md` | Outro / Não Categorizado |
| Modificado | `@developer/mindmeister_automacao.md` | Outro / Não Categorizado |
| Modificado | `@developer/plano_implementacao.md` | Outro / Não Categorizado |
| Modificado | `@developer/relatorio_bugs.md` | Outro / Não Categorizado |
| Modificado | `@developer/relatorio_documentacao.md` | Outro / Não Categorizado |
| Modificado | `@developer/relatorio_funcionalidades.md` | Outro / Não Categorizado |
| Modificado | `@developer/relatorio_geral.md` | Outro / Não Categorizado |
| Modificado | `@developer/roadmap.md` | Outro / Não Categorizado |
| Modificado | `backend/.env.example` | Outro / Não Categorizado |
| Adicionado | `backend/alembic/versions/56d322bbd83a_add_performance_indices.py` | Banco de Dados / Migrações |
| Modificado | `backend/app/api/v1/admin.py` | Painel do Administrador |
| Modificado | `backend/app/api/v1/auth.py` | Autenticação / Login |
| Modificado | `backend/app/api/v1/client.py` | Interface do Cliente |
| Modificado | `backend/app/api/v1/dashboard_cards.py` | Dashboard Gerencial / Cards |
| Modificado | `backend/app/api/v1/sub_users.py` | Sub-usuários |
| Modificado | `backend/app/core/config.py` | Configuração e Segurança |
| Modificado | `backend/app/core/security.py` | Configuração e Segurança |
| Modificado | `backend/app/main.py` | Outro / Não Categorizado |
| Adicionado | `backend/app/middleware/security_headers.py` | Middleware / Observabilidade |
| Modificado | `backend/app/models/__init__.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/audit_control.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/checklist.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/company_dashboard.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/control_catalog.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/user.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/schemas/auth.py` | Schemas / Validação de Dados |
| Modificado | `backend/app/schemas/dashboard_runtime.py` | Schemas / Validação de Dados |
| Adicionado | `backend/app/schemas/pagination.py` | Schemas / Validação de Dados |
| Modificado | `backend/app/services/email_sender.py` | Serviços / Lógica de Negócio |
| Adicionado | `backend/app/services/storage.py` | Serviços / Lógica de Negócio |
| Modificado | `backend/requirements.txt` | Dependências Python |
| Modificado | `backend/scripts/seed_admin.py` | Scripts de Inicialização / Seeds |
| Modificado | `backend/scripts/seed_catalog.py` | Scripts de Inicialização / Seeds |
| Modificado | `frontend/app/private/admin/page.tsx` | Dashboard Admin (Frontend) |

### Funcionalidades Impactadas

- Autenticação / Login
- Banco de Dados / Migrações
- Configuração e Segurança
- Dashboard Admin (Frontend)
- Dashboard Gerencial / Cards
- Dependências Python
- Interface do Cliente
- Middleware / Observabilidade
- Modelos de Dados (ORM)
- Outro / Não Categorizado
- Painel do Administrador
- Schemas / Validação de Dados
- Scripts de Inicialização / Seeds
- Serviços / Lógica de Negócio
- Sub-usuários

### Correções Realizadas

- Nenhuma referência a bug (formato `B-X00`) identificada neste commit.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo do projeto.

### Próximos Passos Recomendados

- Adicionar testes automatizados para a nova funcionalidade.
- Atualizar `docs/relatorio_funcionalidades.md` se a feature agora está completa.
- Verificar se há dependências com funcionalidades pendentes no `docs/roadmap.md`.

---

## Commit `df83715` — 2026-06-25 09:12:21

| Campo | Valor |
|---|---|
| **Autor** | RodigOsantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `fix/audit-repository-refactor-and-regressions` |
| **Tipo** | 🚀 Nova Funcionalidade (`feat`) |
| **Hash Completo** | `df837154880788611e36d93b1a33c6f3d766ea85` |
| **Arquivos Alterados** | 61 arquivo(s) |

### Título do Commit

```
feat: adiciona documentação técnica, dashboard, onboarding e automações
```

### Descrição

## Documentação (@developer/)
- Adiciona central de documentação com 16 arquivos cobrindo análise de maturidade, bugs, melhorias, roadmap, setup, deploy e automações
- index.md reorganizado em 5 grupos (Visão Geral → Setup → Análise Técnica → Planejamento → Automação) com ordem de leitura recomendada
- plano_implementacao.md: guia consolidado com todos os bugs, melhorias e funcionalidades pendentes com convenções de prioridade
- roadmap.md: 4 fases / 36 semanas com sprints e entregáveis detalhados
- deploy_producao.md: checklist completo de segurança, Nginx, HTTPS, CI/CD e backup automático
- executar_projeto.md: guia operacional com Docker, seeds, logs e troubleshooting

## Arquivos de Especificação (Arquivo/)
- Adiciona documentos originais de requisitos: Especificacao_de_Requisitos.docx, formulário de auditoria (.pptx/.pdf) e plataforma auditoria v02 (.docx/.pdf)

## Backend — Dashboard e Onboarding
- company_dashboard.py: modelos Domain e DashboardCard com relacionamentos
- admin_onboarding.py (API): endpoints para templates, empresas e usuários principais
- dashboard_cards.py (API): endpoints de cards com runtime dinâmico
- dashboard_builder.py (service): lógica de construção e cálculo de cards
- admin_onboarding.py (schema): schemas Pydantic para onboarding administrativo
- dashboard_runtime.py (schema): schemas de resposta de cards em tempo real
- seed_dashboard_templates.py: seed inicial de templates de dashboard ISO 27001
- Novas migrations: sub_user_role_flow (x2) e dashboard_domain_tables

## Backend — Ajustes e Correções
- admin.py: refatora endpoints de gestão de usuários e aprovação de sub-usuários
- auth.py: corrige fluxo de autenticação com verificação de bytes no bcrypt
- router.py: registra novos módulos (onboarding, dashboard_cards)
- sub_users.py: adiciona controle de race condition na aprovação
- config.py: adiciona variáveis de ambiente para email e dashboard
- models/user.py e __init__.py: expõe novos modelos e ajusta relacionamentos
- email_sender.py: melhora tratamento de erros no envio
- docker-compose.yml: ajusta healthcheck e volumes do MySQL
- requirements.txt: adiciona dependências (aiofiles, python-multipart, pillow)
- seed_admin.py: corrige NameError e padroniza criação de hash bcrypt com bytes
- correcao_alembic.md: documenta correção aplicada ao env.py do Alembic

## Frontend — Layout e Componentes Privados
- layout.tsx: layout base para área privada com header, sidebar e autenticação
- logout-button.tsx: componente de logout com invalidação de sessão
- user-menu.tsx: menu de usuário com exibição de perfil e navegação
- admin/page.tsx: página administrativa com listagem e aprovação de sub-usuários
- client/page.tsx: dashboard do cliente com cards dinâmicos
- login-form.tsx e login/route.ts: corrige fluxo de login com redirect seguro
- middleware.ts: adiciona proteção de rotas privadas com verificação de sessão

## Frontend — APIs BFF
- /api/admin/onboarding/companies, principal-users, templates: proxies para o backend de onboarding
- /api/sub-users/requests, requests/[id]/approve, requests/pending: gestão de solicitações de sub-usuários
- safe-redirect.ts: utilitário para validação de URLs de redirecionamento

## GitHub Actions
- commit-report.yml: workflow para geração automática de relatório de commits
- generate_commit_report.py: script Python que compila histórico e métricas de commits

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Arquivos Modificados (61 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Adicionado | `.github/scripts/generate_commit_report.py` | CI/CD e Automação |
| Adicionado | `.github/workflows/commit-report.yml` | CI/CD e Automação |
| Adicionado | `@developer/automacao_commits.md` | Outro / Não Categorizado |
| Adicionado | `@developer/dashboard_projeto.md` | Outro / Não Categorizado |
| Adicionado | `@developer/deploy_producao.md` | Outro / Não Categorizado |
| Adicionado | `@developer/executar_projeto.md` | Outro / Não Categorizado |
| Adicionado | `@developer/index.md` | Outro / Não Categorizado |
| Adicionado | `@developer/mindmeister_automacao.md` | Outro / Não Categorizado |
| Adicionado | `@developer/plano_implementacao.md` | Outro / Não Categorizado |
| Adicionado | `@developer/relatorio_bugs.md` | Outro / Não Categorizado |
| Adicionado | `@developer/relatorio_commit.md` | Outro / Não Categorizado |
| Adicionado | `@developer/relatorio_documentacao.md` | Outro / Não Categorizado |
| Adicionado | `@developer/relatorio_funcionalidades.md` | Outro / Não Categorizado |
| Adicionado | `@developer/relatorio_geral.md` | Outro / Não Categorizado |
| Adicionado | `@developer/relatorio_melhorias.md` | Outro / Não Categorizado |
| Adicionado | `@developer/roadmap.md` | Outro / Não Categorizado |
| Adicionado | `@developer/setup_completo.md` | Outro / Não Categorizado |
| Adicionado | `@developer/trello_automacao.md` | Outro / Não Categorizado |
| Adicionado | `Arquivo/Especificacao_de_Requisitos.docx` | Outro / Não Categorizado |
| Adicionado | `"Arquivo/Formul\303\241rio Auditoria.pptx"` | Outro / Não Categorizado |
| Adicionado | `Arquivo/formulario_auditoria.pdf` | Outro / Não Categorizado |
| Adicionado | `Arquivo/plataforma auditoria vers 02.docx` | Outro / Não Categorizado |
| Adicionado | `Arquivo/plataforma auditoria vers 02.pdf` | Outro / Não Categorizado |
| Modificado | `backend/README.md` | Outro / Não Categorizado |
| Adicionado | `backend/alembic/versions/447a4e1de59d_add_sub_user_role_flow.py` | Banco de Dados / Migrações |
| Adicionado | `backend/alembic/versions/9d5a3c1b2e77_add_dashboard_domain_tables.py` | Banco de Dados / Migrações |
| Adicionado | `backend/alembic/versions/d60f999c1fca_add_sub_user_role_flow.py` | Banco de Dados / Migrações |
| Modificado | `backend/app/api/v1/admin.py` | Painel do Administrador |
| Adicionado | `backend/app/api/v1/admin_onboarding.py` | Onboarding de Clientes |
| Modificado | `backend/app/api/v1/auth.py` | Autenticação / Login |
| Adicionado | `backend/app/api/v1/dashboard_cards.py` | Dashboard Gerencial / Cards |
| Modificado | `backend/app/api/v1/router.py` | Roteamento da API |
| Modificado | `backend/app/api/v1/sub_users.py` | Sub-usuários |
| Modificado | `backend/app/core/config.py` | Configuração e Segurança |
| Modificado | `backend/app/models/__init__.py` | Modelos de Dados (ORM) |
| Adicionado | `backend/app/models/company_dashboard.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/user.py` | Modelos de Dados (ORM) |
| Adicionado | `backend/app/schemas/admin_onboarding.py` | Schemas / Validação de Dados |
| Adicionado | `backend/app/schemas/dashboard_runtime.py` | Schemas / Validação de Dados |
| Adicionado | `backend/app/services/dashboard_builder.py` | Serviços / Lógica de Negócio |
| Modificado | `backend/app/services/email_sender.py` | Serviços / Lógica de Negócio |
| Modificado | `backend/docker-compose.yml` | Infraestrutura / Docker |
| Modificado | `backend/requirements.txt` | Dependências Python |
| Modificado | `backend/scripts/seed_admin.py` | Scripts de Inicialização / Seeds |
| Adicionado | `backend/scripts/seed_dashboard_templates.py` | Scripts de Inicialização / Seeds |
| Adicionado | `correcao_alembic.md` | Outro / Não Categorizado |
| Adicionado | `frontend/app/api/admin/onboarding/companies/route.ts` | Proxy Admin (Next.js → FastAPI) |
| Adicionado | `frontend/app/api/admin/onboarding/principal-users/route.ts` | Proxy Admin (Next.js → FastAPI) |
| Adicionado | `frontend/app/api/admin/onboarding/templates/route.ts` | Proxy Admin (Next.js → FastAPI) |
| Modificado | `frontend/app/api/auth/login/route.ts` | Proxy Auth (Next.js → FastAPI) |
| Adicionado | `frontend/app/api/sub-users/requests/[id]/approve/route.ts` | Proxy Sub-usuários (Next.js → FastAPI) |
| Adicionado | `frontend/app/api/sub-users/requests/pending/route.ts` | Proxy Sub-usuários (Next.js → FastAPI) |
| Adicionado | `frontend/app/api/sub-users/requests/route.ts` | Proxy Sub-usuários (Next.js → FastAPI) |
| Adicionado | `frontend/app/private/_components/logout-button.tsx` | Componentes Privados (Frontend) |
| Adicionado | `frontend/app/private/_components/user-menu.tsx` | Componentes Privados (Frontend) |
| Modificado | `frontend/app/private/admin/page.tsx` | Dashboard Admin (Frontend) |
| Modificado | `frontend/app/private/client/page.tsx` | Dashboard Cliente (Frontend) |
| Adicionado | `frontend/app/private/layout.tsx` | Layout Privado (Frontend) |
| Modificado | `frontend/app/public/login/login-form.tsx` | Página de Login |
| Adicionado | `frontend/lib/safe-redirect.ts` | Utilitários do Frontend |
| Modificado | `frontend/middleware.ts` | Middleware de Autenticação (legado) |

### Funcionalidades Impactadas

- Autenticação / Login
- Banco de Dados / Migrações
- CI/CD e Automação
- Componentes Privados (Frontend)
- Configuração e Segurança
- Dashboard Admin (Frontend)
- Dashboard Cliente (Frontend)
- Dashboard Gerencial / Cards
- Dependências Python
- Infraestrutura / Docker
- Layout Privado (Frontend)
- Middleware de Autenticação (legado)
- Modelos de Dados (ORM)
- Onboarding de Clientes
- Outro / Não Categorizado
- Painel do Administrador
- Proxy Admin (Next.js → FastAPI)
- Proxy Auth (Next.js → FastAPI)
- Proxy Sub-usuários (Next.js → FastAPI)
- Página de Login
- Roteamento da API
- Schemas / Validação de Dados
- Scripts de Inicialização / Seeds
- Serviços / Lógica de Negócio
- Sub-usuários
- Utilitários do Frontend

### Correções Realizadas

- Nenhuma referência a bug (formato `B-X00`) identificada neste commit.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo do projeto.

### Próximos Passos Recomendados

- Adicionar testes automatizados para a nova funcionalidade.
- Atualizar `docs/relatorio_funcionalidades.md` se a feature agora está completa.
- Verificar se há dependências com funcionalidades pendentes no `docs/roadmap.md`.

---

## Commit `1fe4a41` — 2026-05-21 13:34:23

| Campo | Valor |
|---|---|
| **Autor** | Rodig0SantOs (rodrigo.santos@stwbrasil.com) |
| **Branch** | `main` |
| **Tipo** | 🚀 Nova Funcionalidade (`feat`) |
| **Hash Completo** | `1fe4a416c6db1f12e44aaee9631dacabb3e5efaa` |
| **Arquivos Alterados** | 14 arquivo(s) |

### Título do Commit

```
feat(backend): adiciona fluxo completo de sub-user com aprovação administrativa
```

### Descrição

Implementa a nova role  e o fluxo onde o usuário principal solicita a criação, o admin aprova, e o sistema cria a conta com senha aleatória. Inclui envio de credenciais por e-mail (com fallback para log em ambiente de desenvolvimento) e garante que o sub-user visualize o dashboard do usuário principal.

### Arquivos Modificados (14 arquivo(s))

| Status | Arquivo | Funcionalidade |
|---|---|---|
| Modificado | `backend/app/api/deps.py` | Outro / Não Categorizado |
| Modificado | `backend/app/api/v1/auth.py` | Autenticação / Login |
| Modificado | `backend/app/api/v1/client.py` | Interface do Cliente |
| Modificado | `backend/app/api/v1/router.py` | Roteamento da API |
| Adicionado | `backend/app/api/v1/sub_users.py` | Sub-usuários |
| Modificado | `backend/app/api/v1/users.py` | Outro / Não Categorizado |
| Modificado | `backend/app/core/config.py` | Configuração e Segurança |
| Modificado | `backend/app/models/__init__.py` | Modelos de Dados (ORM) |
| Adicionado | `backend/app/models/sub_user_request.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/models/user.py` | Modelos de Dados (ORM) |
| Modificado | `backend/app/schemas/auth.py` | Schemas / Validação de Dados |
| Adicionado | `backend/app/schemas/sub_user.py` | Schemas / Validação de Dados |
| Adicionado | `backend/app/services/email_sender.py` | Serviços / Lógica de Negócio |
| Modificado | `backend/app/services/users.py` | Serviços / Lógica de Negócio |

### Funcionalidades Impactadas

- Autenticação / Login
- Configuração e Segurança
- Interface do Cliente
- Modelos de Dados (ORM)
- Outro / Não Categorizado
- Roteamento da API
- Schemas / Validação de Dados
- Serviços / Lógica de Negócio
- Sub-usuários

### Correções Realizadas

- Nenhuma referência a bug (formato `B-X00`) identificada neste commit.

### Pendências Identificadas

- Nenhuma pendência identificada automaticamente.
- Consulte `docs/roadmap.md` para o backlog completo do projeto.

### Próximos Passos Recomendados

- Adicionar testes automatizados para a nova funcionalidade.
- Atualizar `docs/relatorio_funcionalidades.md` se a feature agora está completa.
- Verificar se há dependências com funcionalidades pendentes no `docs/roadmap.md`.

