# Plataforma de Auditoria — Central de Documentação

| Campo | Valor |
|---|---|
| **Versão desta central** | **9.0 — 2026-08-26** |
| **Repositório** | https://github.com/Rodig0SantOs/Projeto-Auditoria |
| **Branch / HEAD** | `main` · `c769526` |
| **Stack** | FastAPI 0.115 + SQLAlchemy 2.0 + Alembic + MySQL 8.4 (Docker) · Next.js 16.2.6 + React 19.2 + Tailwind 4 · structlog · slowapi · reportlab |
| **Maturidade** | **~97%** — MVP maduro · **0 achados abertos** · **CI verde nos 4 jobs** |
| **Suíte de testes** | ✅ **372 passed** — 258 backend + 114 frontend · **executada no CI** |

---

## 🎯 Comece por aqui

> ### ✅ O CI executou — e encontrou 4 defeitos que ninguém sabia que existiam
>
> O `ci.yml` existia desde 2026-08-11 e **nunca havia rodado**. Rodou em 2026-08-26, depois do merge do PR #1, e reprovou **3 dos 4 jobs**:
>
> | Defeito | Despercebido por |
> |---|---|
> | **B-A30** — a cadeia de `alembic downgrade` nunca funcionou (6 migrations, 3 causas) | até **3 meses** |
> | **B-A31** — 9 CVEs, **7 no `python-multipart`**, o parser do upload de evidências | desde que a versão foi fixada |
> | **B-M30** — o job `backend` não tinha variáveis de ambiente e **nunca poderia ter passado** | **2 meses e meio** |
> | **B-M31** — `tsc` reprovava código correto por falta dos tipos gerados pelo Next | desde sempre |
>
> Os quatro foram corrigidos. **Os 4 jobs passam em `main`.**
>
> **O que isso ensina** está registrado como **M-30** em [`relatorio_melhorias.md`](relatorio_melhorias.md): *uma barreira que nunca executou não é uma barreira* — com a lista do que **ainda** não executou neste projeto (Docker, restore de backup, Trello, MindMeister, deploy).

---

## O que mudou nesta revisão (2026-08-26, rev. 8.1)

Três commits desde a rev. 7.0, dois deles com código: **`4fd576f` — BLOCO P** (o commit de segurança do projeto) e **`34f8444`** (correção do CSP que deixava o Swagger em branco).

### Entregue

| Fase | O quê |
|---|---|
| **P.0** | Credenciais **rotacionadas**; `db_auditoria.sql` removido; `.env.example` com 21 placeholders; gitleaks no pre-commit (movido para a **raiz**, onde de fato roda) |
| **P.1** | **Autorização: posse ≠ permissão.** `require_admin` em status de card e checklist; novo `app/core/policy.py` como fonte única; matriz de testes que exercita cada papel contra cada escrita proibida |
| **P.2** | **Retenção de arquivo.** `storage.delete_files()` pós-commit com guarda de caminho; `StorageBackend` Protocol com `delete` obrigatório; `prune_orphan_uploads.py` |
| **P.3** | **Integridade template ↔ card.** 409 ao excluir template em uso; migrations de backfill e `UniqueConstraint` |
| **P.4** | **Barreiras de CI.** `test_migrations_smoke.py` + job `migrations` contra MySQL 8.4 real; `pip-audit`; 5 achados Baixos fechados |
| **#14** | **CSP por rota.** `API_CSP` nas rotas de dados, `DOCS_CSP` liberando exatamente o que `/docs` e `/redoc` pedem; teste que varre o HTML real |

**Números:** 17 → **19** migrations · 128 → **202** testes (+58%) · 2 → **4** jobs de CI · 5 → **7** cabeçalhos de segurança · 70 → **78** funcionalidades.

**Todos os 18 achados da rev. 8.0 foram fechados** — incluindo o único Crítico da história do projeto.

### Encontrado

A auditoria seguinte, sobre o código já corrigido, encontrou **15 achados** — todos confirmados por sonda executável, nenhum por leitura:

| ID | Achado | Confirmado por |
|---|---|---|
| 🟠 **B-A27** | Senha > 72 bytes derruba `/auth/login` com exceção não tratada — **sem autenticação** | `ValueError: password cannot be longer than 72 bytes` |
| 🟠 **B-A28** | Cliente auditado **lê** o checklist interno e o histórico do auditor | Sonda HTTP: `200` como `user` e como `sub-user` |
| 🟠 **B-A29** | Senha temporária do onboarding não existe em lugar nenhum sem SMTP | `201` com corpo sem senha |
| 🟡 **B-M25** | `ALLOW_PUBLIC_REGISTRATION` tem default `True` | `Settings(...).ALLOW_PUBLIC_REGISTRATION == True` |
| 🟡 **B-M26** | `GET /admin/companies` faz **7 queries por empresa** | Contador de `before_cursor_execute`: 73 para 10 |

Mais 2 Médios, 7 Baixos e **8 divergências** ainda ativas entre `backend/README.md` e o código.

**Duas hipóteses foram refutadas** pelas sondas e não viraram achado: o N+1 suspeito em `GET /companies/{id}/messages` (4 queries para 12 mensagens — o identity map resolve) e a diferença de tempo entre login com e-mail existente e inexistente (razão 0,9× — sem oráculo de enumeração).

### Corrigido nas automações

- **Relatório de commits:** backfill de `66578f0..HEAD` executado — 41 → **44 entradas**, 0 duplicatas. A guarda de idempotência foi exercitada rodando o backfill duas vezes.
- **Gerador de mapas mentais:** os parsers foram reexecutados contra a documentação nova e **duas regressões silenciosas** apareceram — a Fase 4 do roadmap virava galho vazio e as 13 melhorias vinham sem estimativa. Corrigidos, com um piso de **conteúdo** (não só de contagem) acrescentado.
- **Automação Trello:** catálogo reescrito para os achados atuais — **17 cards** contra os 18 da revisão anterior, todos já fechados.

---

## Achados Ativos

| # | Item | Prioridade | Esforço | Onde |
|---|---|---|---|---|
| 1 | 1ª execução real do `ci.yml` | 🔴 **Hoje** | 1 h | [`roadmap.md`](roadmap.md) Sprint A5 |
| 2 | 8 divergências no `backend/README.md` | 🟡 Média | 1 h | [`relatorio_documentacao.md`](relatorio_documentacao.md) Seção 0 |
| 3 | Decompor os 4 arquivos > 500 LOC | 🟡 Média | 3 dias | `relatorio_melhorias.md` M-17 — **destravado** pelos testes |
| 4 | Escala horizontal (storage + Redis) | 🟡 Média | 3 dias | [`roadmap.md`](roadmap.md) Sprint D2 |

**Corrigidos em 2026-08-26 (BLOCO Q):** B-A27, B-A28, B-A29, B-M25, B-M27, B-M28, B-M29 e
B-B17..B-B23 — **14 de 15**. Suíte de 202 para **250 testes**, com as 5 barreiras verificadas
por reversão. Detalhes em [`plano_implementacao.md`](plano_implementacao.md) → **Q.7**.

---

## Métricas

| Métrica | Valor | Δ desde a rev. 7.0 |
|---|---|---|
| Testes automatizados (backend) | **258** passed, 0 failed | 🔼 +130 |
| Testes automatizados (frontend) | **114** passed · 81% de cobertura | 🔼 **+114** |
| Migrations Alembic | **19** (head `b7c02e91d4a5`) | 🔼 +2 |
| Classes ORM | **18** em 9 arquivos | — |
| Routers da API v1 | **11** (62 operações; 64 no total) | — |
| Rotas de página (frontend) | **15** | — |
| Funcionalidades concluídas | **78** (F01–F78) | 🔼 +8 |
| Achados abertos | **0** em todas as faixas | 🔽 −18 |
| Achados fechados (acumulado) | **79** | 🔼 +28 |
| Requisitos formais com implementação | **28 de 38** (74%) · **21 plenamente** (RNF-03 recuperado) | 🔼 +1 |
| Jobs de CI | **4** | 🔼 +2 |
| LOC backend `app/` / frontend | 5.703 / 7.811 | 🔼 |
| Entradas no relatório de commits | **44** | 🔼 +3 |
| Arquivos em `docs/` | **17** | — |

---

## Índice de Documentação

### 📊 Visão Geral

| Documento | Versão | Para quê |
|---|---|---|
| [`dashboard_projeto.md`](dashboard_projeto.md) | 8.1 | **Visão executiva** — semáforo por área, riscos, métricas, plano de ação |
| [`relatorio_geral.md`](relatorio_geral.md) | 8.0 | Arquitetura, stack, estrutura de pastas, fluxos, banco de dados |
| [`relatorio_funcionalidades.md`](relatorio_funcionalidades.md) | 8.0 | Linha do tempo (50 commits) e inventário de 88 funcionalidades |

### 🚀 Setup & Operação

| Documento | Versão | Para quê |
|---|---|---|
| [`setup_completo.md`](setup_completo.md) | 4.0 | **Do `git clone` à aplicação rodando**, com verificação em cada etapa |
| [`executar_projeto.md`](executar_projeto.md) | 6.0 | Operação diária: banco, backup, logs, Docker, primeiros passos |
| [`deploy_producao.md`](deploy_producao.md) | 2.1 | Deploy em produção |

### 🔍 Análise Técnica

| Documento | Versão | Para quê |
|---|---|---|
| [`relatorio_bugs.md`](relatorio_bugs.md) | 9.1 | 15 achados levantados, **14 corrigidos** — localização exata, impacto e código de correção |
| [`relatorio_melhorias.md`](relatorio_melhorias.md) | 7.0 | Causas estruturais (M-01..M-29) — por que os achados aconteceram |
| [`relatorio_documentacao.md`](relatorio_documentacao.md) | 7.0 | Rastreabilidade requisitos × código + auditoria do `backend/README.md` |

### 🗺️ Planejamento & Execução

| Documento | Versão | Para quê |
|---|---|---|
| [`roadmap.md`](roadmap.md) | 7.0 | Fases e sprints com critérios de saída e dependências |
| [`plano_implementacao.md`](plano_implementacao.md) | 5.20 | Passo a passo técnico de cada bloco, com código pronto |
| [`backlog.md`](backlog.md) | 3.0 | Backlog acionável, sem o volume do plano |
| [`PRD.md`](PRD.md) | 1.0 | **Quadro Kanban** — problema, personas, requisitos e 30 critérios de aceite |
| [`Spec.md`](Spec.md) | 1.0 | Tradução técnica do PRD: árvore de arquivos, contratos de API, migration |
| [`Code.md`](Code.md) | 1.0 | Guia de implementação manual em 13 fases, com o código-fonte integral |

### 🤖 Automação & Integrações

| Documento | Versão | Estado |
|---|---|---|
| [`automacao_commits.md`](automacao_commits.md) | 4.0 | ✅ **Executou no CI** — 44 → 46 entradas, com push de volta |
| [`relatorio_commit.md`](relatorio_commit.md) | gerado | 44 entradas, até `34f8444` — **não edite à mão** |
| [`trello_automacao.md`](trello_automacao.md) | 3.0 | 📋 Proposta — quadro não criado; catálogo de 17 cards pronto |
| [`mindmeister_automacao.md`](mindmeister_automacao.md) | 3.0 | 📋 Proposta — parsers reexecutados; 2 regressões corrigidas |

---

## Por onde começar, dependendo de quem você é

| Se você… | Leia nesta ordem |
|---|---|
| **Acabou de clonar o repositório** | [`setup_completo.md`](setup_completo.md) → [`relatorio_geral.md`](relatorio_geral.md) → [`executar_projeto.md`](executar_projeto.md) |
| **Vai corrigir os achados abertos** | [`relatorio_bugs.md`](relatorio_bugs.md) → [`roadmap.md`](roadmap.md) (Sprints A5 e A4) → [`plano_implementacao.md`](plano_implementacao.md) (BLOCO Q) |
| **Precisa decidir prioridade** | [`dashboard_projeto.md`](dashboard_projeto.md) → [`backlog.md`](backlog.md) → [`roadmap.md`](roadmap.md) |
| **Quer entender por que os bugs aconteceram** | [`relatorio_melhorias.md`](relatorio_melhorias.md) (M-21 a M-25) |
| **Vai implementar uma funcionalidade nova** | [`relatorio_geral.md`](relatorio_geral.md) → [`relatorio_funcionalidades.md`](relatorio_funcionalidades.md) → [`relatorio_documentacao.md`](relatorio_documentacao.md) |
| **Vai fazer deploy** | [`deploy_producao.md`](deploy_producao.md) → [`roadmap.md`](roadmap.md) (Sprint D2 — **escala horizontal ainda não funciona**) |
| **Vai cadastrar um cliente pela interface** | [`setup_completo.md`](setup_completo.md) **Seção 9.4** — leia antes (B-A29) |

---

## Próximos Passos Recomendados

### Hoje (1 h)

1. **Abrir um PR e deixar o `ci.yml` executar.** Cinco barreiras e quatro jobs esperam a primeira execução real.

### Sprint A4 (1,5 dia)

2. **B-A27** — o limite do bcrypt vira contrato explícito. Único achado explorável sem credencial.
3. **B-A29 + B-M27** — contrato de falha no e-mail e função própria por destinatário. Mesmo arquivo, entrega conjunta.
4. **B-A28** — `Action.READ_CARD_INTERNALS` e filtro na leitura. Recupera o requisito RNF-03.
5. **B-M25 + B-M29** — defaults de configuração, com o teste que os fixa. 30 minutos.
6. **B-M28** — guarda de path traversal no ponto único. Pré-requisito do Sprint D2.

### Semanas seguintes

7. **Testes de frontend** (Vitest + Testing Library) — Server Actions primeiro. Torna 7.811 LOC auditáveis.
8. **Orçamento de queries por rota**, e só então corrigir o N+1 de `GET /admin/companies`.
9. **Unificar as 4 implementações** de checagem de posse em `core/access.py`.
10. **Decompor** os 4 arquivos de frontend acima de 500 LOC — depois dos testes.
11. **Escala horizontal** (Sprint D2) — storage trocável + rate limit em Redis.
12. **Ciclo de vida da credencial** (Sprint E) — troca obrigatória, recuperação e revogação.

---

## Avisos operacionais

> ✅ **Cadastrar um cliente sem SMTP voltou a ser seguro** (B-A29, corrigido em 2026-08-26). Quando o e-mail não é entregue, a senha temporária é exibida ao admin na própria tela, com aviso — e uma falha de SMTP não derruba mais o onboarding com 500 depois do commit. **Anote a senha quando ela aparecer**: continua não havendo recuperação de senha na plataforma (Sprint E).
>
> ⚠️ **Não rode o backend com mais de um worker/réplica** — evidências em volume local e rate limit em memória de processo. Ver Sprint D2.
>
> ⚠️ **`GET /api/v1/Monitoring` não existe mais.** O health check é **`GET /health`**, que executa `SELECT 1`. O `backend/README.md` ainda indica a rota antiga, que responde 404 — um orquestrador configurado por ele reinicia a aplicação em laço.
>
> ⚠️ **`docs/relatorio_commit.md` é gerado**, não editado à mão. Alterações manuais são sobrescritas.
>
> ✅ **"Aplicar template" numa empresa já configurada voltou a ser seguro.** A `UniqueConstraint` e o backfill de `origin_template_card_id` fecharam B-A24.
>
> ✅ **Excluir uma empresa agora apaga também os arquivos de evidência do disco.** Para os órfãos deixados por exclusões anteriores: `python scripts/prune_orphan_uploads.py --apply`.

---

*Central atualizada em 2026-08-26 (rev. 8.1, após a implementação do BLOCO Q). Todos os 17 documentos de `docs/` foram revisados nesta rodada; os números desta página foram verificados por execução — `pytest` (**250 passed**), `ruff`, `alembic heads`, `tsc --noEmit`, `eslint`, `app.openapi()`, `git log --all -S` e 13 sondas escritas para a auditoria — não copiados da revisão anterior.*
