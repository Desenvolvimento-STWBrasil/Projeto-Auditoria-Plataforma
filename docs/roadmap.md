# Roadmap de Desenvolvimento — Plataforma de Auditoria

| Campo | Valor |
|---|---|
| **Data** | 2026-06-24 (criação) · 2026-07-27 (rev. 1.1) · 2026-08-11 (rev. 2.0) · 2026-08-12 (rev. 3.0) · 2026-08-17 (rev. 4.0) · 2026-08-17 (rev. 5.0) · 2026-08-24 (rev. 6.0) · **2026-08-26 (rev. 7.0 — esta revisão)** |
| **Versão** | 8.0 |
| **Branch / HEAD** | `main` · `c769526` (PRs #1 e #2 mergeados) |
| **Relatórios Base** | `relatorio_geral.md` (8.0), `relatorio_funcionalidades.md` (8.0), `relatorio_bugs.md` (9.0), `relatorio_melhorias.md` (7.0) |
| **Estado em 2026-08-24** | Backend 98% · Frontend 94% · Testes 128/128 · DevOps 85% · **1 Crítico + 4 Alta abertos** |
| **Estado em 2026-08-26 (manhã)** | Testes 202 · DevOps 90% · 0 Crítico · 3 Alta abertos |
| **Estado em 2026-08-26 (fim)** | Testes **372** (258 backend + 114 frontend) · DevOps **100%** · **0 achados abertos** · **CI verde nos 4 jobs** |

> ### ✅ Mudança de prioridade nesta revisão
>
> A rev. 6.0 abriu com um alerta vermelho: 1 achado Crítico e 4 Alta, e o Sprint B (testes de frontend) cedendo a vez ao Sprint A3.
>
> **O Sprint A0 e o Sprint A3 foram executados** (commits `4fd576f` e `34f8444`). Os 5 achados foram fechados, e com eles vieram as 5 barreiras estruturais que a rev. 6.0 do `relatorio_melhorias.md` havia pedido — todas entregues. A faixa **Crítica está vazia**.
>
> A auditoria seguinte (rev. 9.0 de `relatorio_bugs.md`) encontrou **3 novos achados Alta**, de natureza diferente: não são de autorização, são de **borda** — o que acontece quando a entrada sai do formato esperado (**B-A27**), quando um serviço externo não responde (**B-A29**) e quando a política cobre a escrita mas não a leitura (**B-A28**).
>
> **Consequência para o planejamento:** o Sprint A4 é curto (1,5 dia contra os 4 do A3) e, pela primeira vez em três revisões, **o Sprint B entra na mesma janela**. A dívida de correção deixou de ser o gargalo; o gargalo agora é a ausência de testes de frontend.

---

## Visão do Roadmap

```
        CONCLUÍDO ATÉ AQUI                     │      A PARTIR DE HOJE (2026-08-26)
────────────────────────────────────────────  │  ───────────────────────────────────────
FASE 1 — Estabilização e Segurança      100%  │  Sprint A5 — 1ª execução real do CI
  auth, rate limit, security headers,         │    (1 hora)         ◀── HOJE
  health check, refresh token, CSP/HSTS,      │
  credenciais rotacionadas, gitleaks,         │  Sprint A4 — Achados de borda
  pip-audit, política de autorização          │    (1,5 dia)        ◀── EM SEGUIDA
                                              │
FASE 2 — Qualidade e Confiança           88%  │  Sprint B  — Testes de frontend
  202 testes backend, matriz de autorização,  │    (2–3 dias)       ◀── DESTRAVADO
  smoke de migrations, teste de CSP real,     │
  repository pattern, docs sincronizada       │  Sprint C  — Componentização +
  ⚠️ 0 testes de frontend                     │              observabilidade (4–5 dias)
                                              │
FASE 3 — Preparação para Produção        70%  │  Sprint D2 — Storage trocável +
  Dockerfiles, compose raiz, ci.yml 4 jobs    │              escala horizontal (3 dias)
  ⚠️ CI ✅ verde · Docker sem build real       │
                                              │  Sprint E  — Ciclo de vida da credencial
FASE 4 — Crescimento e Escala            45%  │              (2 dias)
  BLOCO L, M.1/M.2, N.1-N.3, BLOCO O          │
  (templates, categorias, bulk, KPIs)         │  FASE 4 (resto) — Iterações C e D
```

---

## Estado Atual — Maturidade por Área

| Área | 2026-08-24 | 2026-08-26 | Δ | O que falta para 100% |
|---|---|---|---|---|
| **Autenticação e sessão** | 95% | **95%** | — | Revogação de token (M-28), recuperação de senha (M-29), troca no 1º login (M-02b) |
| **Autorização** | 60% | **90%** | 🔼 +30 | Leitura sensível fora de `policy.py` (**B-A28** / M-23) |
| **Domínio (auditoria, dashboard)** | 95% | **97%** | 🔼 +2 | Rejeição formal de evidência (N05) |
| **Integridade de dados** | 70% | **98%** | 🔼 +28 | Decidir o destino do soft delete (N11) |
| **Retenção / LGPD** | 40% | **95%** | 🔼 +55 | Política de retenção declarada (hoje é exclusão imediata) |
| **Validação de entrada** | 70% | **70%** | — | Limites físicos não modelados (**B-A27** / M-21) |
| **Integração externa (e-mail)** | 50% | **50%** | — | Sem contrato de falha (**B-A29** / M-22); síncrono (M-09) |
| **Testes — backend** | 90% | **96%** | 🔼 +6 | Orçamento de queries (M-25); leitura na matriz (M-23) |
| **Testes — frontend** | 0% | **0%** | — | Tudo (**M-08b**) |
| **CI/CD** | 60% | **85%** | 🔼 +25 | **1ª execução real** · `docker build`/`run` |
| **Observabilidade** | 50% | **50%** | — | Métricas (M-07b), `audit_log` (M-07c) |
| **Escalabilidade** | 30% | **35%** | 🔼 +5 | Storage remoto e rate limit compartilhado (M-26) |
| **Documentação** | 100% | **100%** | — | — |

---

## FASE 1 — Estabilização e Segurança `✅ 100% — concluída em 2026-08-25`

### Critérios de saída

| Critério | Estado |
|---|---|
| JWT com expiração curta + refresh | ✅ 15 min / 7 dias |
| Rate limiting nos endpoints de autenticação | ✅ Verificado por sonda: 6º login → 429 |
| Cabeçalhos de segurança HTTP | ✅ 7 headers, CSP por rota, HSTS sob HTTPS |
| Health check com verificação real de banco | ✅ `SELECT 1` |
| Nenhum segredo em arquivo versionado | ✅ Rotacionado + gitleaks no pre-commit e no CI |
| Autorização não derivada de posse | ✅ `core/policy.py` + matriz de testes |
| Varredura de CVE em dependências | ✅ `pip-audit` no CI |
| Exclusão de dado pessoal alcança o disco | ✅ `delete_files()` + `prune_orphan_uploads.py` |

> **A ressalva da Fase 1 foi levantada em 2026-08-26.** Os quatro últimos critérios eram garantidos por barreiras que nunca haviam executado. Elas executaram — e **reprovaram 3 dos 4 jobs**, revelando que a cadeia de `alembic downgrade` nunca funcionara e que o job `backend` sequer podia rodar. Corrigidos, os 4 jobs passam em `main`: agora "100%" significa **verificado no ambiente de destino**.

---

## FASE 2 — Qualidade e Confiança `🟡 88% concluída`

### Critérios de saída

| Critério | Estado |
|---|---|
| Suíte de testes de backend cobrindo os fluxos críticos | ✅ 202 testes, 100% verdes |
| Autorização negativa testada (cada papel × cada escrita) | ✅ `test_authorization_matrix.py` |
| Migrations verificadas por teste e contra MySQL real | ✅ `test_migrations_smoke.py` + job `migrations` |
| Zero código morto / órfão | ✅ Verificado por `grep` nesta revisão |
| Lint limpo nos dois lados | ✅ `ruff`, `eslint`, `tsc` |
| **Testes de frontend** | 🔴 **0** |
| **Custo de query medido por teste** | 🔴 Nenhum |
| Nenhum arquivo acima de 500 LOC no frontend | 🔴 4 arquivos (890 / 649 / 594 / 518) |

---

## Sprints

### Sprint A — Arquitetura ✅ concluído
### Sprint A2 — BLOCO L, M.1/M.2, N.1–N.3, BLOCO O ✅ concluído
### Sprint A0 — Contenção do Crítico ✅ concluído em `4fd576f`
### Sprint A3 — Achados Alta + barreiras estruturais ✅ concluído em `4fd576f` + `34f8444`
### Sprint A6 — Quadro Kanban de colunas e cards ✅ concluído

**Entregue:** B-C23, B-A23, B-A24, B-A25, B-A26, B-M21, B-M22, B-M23, B-M24, B-M15, B-M18, B-B09..B-B16 · M-15, M-16, M-18, M-19, M-20 · 128 → 202 testes · 17 → 19 migrations · 2 → 4 jobs de CI.

**Aprendizado registrado (P.7 do plano):** dos 13 defeitos encontrados na verificação do próprio bloco, **11 foram pegos pela suíte de testes do bloco**, e o padrão dominante foi *código correto no lugar errado* — um `raise` antes de um `db.delete`, um bloco aninhado dentro de uma docstring de exceção, uma rota sobrescrevendo outra. Não erro de digitação: erro de posicionamento. O 14º defeito (CSP) escapou porque o teste perguntava a coisa errada.

---

### Sprint A5 — Primeira execução real do CI `✅ CONCLUÍDO em 2026-08-26`

> **Resultado: 3 dos 4 jobs reprovaram, e cada reprovação era um defeito real.**
>
> | Job | Achado | Despercebido por |
> |---|---|---|
> | `migrations` | **B-A30** — a cadeia de `alembic downgrade` nunca funcionou (6 migrations) | até 3 meses |
> | `backend` | **B-A31** — 9 CVEs, 7 no parser de upload · **B-M30** — job sem variáveis de ambiente | 2 meses e meio |
> | `frontend` | **B-M31** — `tsc` sem os tipos gerados pelo Next | desde sempre |
> | `secrets` | ✅ passou — **contrariando a previsão registrada abaixo** |
>
> Os quatro foram corrigidos no mesmo dia. **CI verde nos 4 jobs em `main`.** Registro completo em
> `plano_implementacao.md` → **BLOCO S**; causa estrutural em `relatorio_melhorias.md` → **M-30**.
>
> **Custo real: ~2 h**, contra 1 h estimada. A diferença foi o que o sprint encontrou, não erro de
> estimativa.

<details>
<summary>Plano original do sprint (mantido para referência)</summary>


**Por que é o primeiro item do roadmap.** Cinco barreiras foram construídas no BLOCO P para impedir a reincidência de cinco classes de defeito. Nenhuma delas jamais executou no GitHub Actions. Uma barreira validada apenas por leitura é uma suposição sobre uma barreira.

| Passo | Comando / ação | Verificação |
|---|---|---|
| 1 | `git push origin fix/audit-repository-refactor-and-regressions` | Branch publicada |
| 2 | `gh pr create --base main --title "BLOCO P + correção do CSP" --body-file docs/relatorio_bugs.md` | PR aberto |
| 3 | Aguardar os 4 jobs | `backend` · `frontend` · `secrets` · `migrations` |
| 4 | **Job `secrets`** — gitleaks sobre `fetch-depth: 0` | ⚠️ **Vai encontrar as credenciais antigas no histórico.** É o resultado correto: elas estão lá. Decidir entre `.gitleaksignore` com as revisões conhecidas (documentando a rotação) ou purgar o histórico |
| 5 | **Job `migrations`** — `upgrade head` → `downgrade base` → `upgrade head` contra MySQL 8.4 | Primeiro teste real dos 19 downgrades |
| 6 | **Job `backend`** — `pip-audit` sobre `requirements.txt` | Primeira varredura real de CVE |
| 7 | **Job `frontend`** — `npm ci` + `lint` + `tsc` + `build` | `npm ci` usa `package-lock.json`, não o `node_modules` local |

**Critério de saída:** os 4 jobs concluídos, com o resultado de cada um registrado — inclusive se algum falhar. **Um job que falha na primeira execução é o retorno esperado deste sprint**, não um contratempo.

</details>

> ✅ **O critério de saída foi cumprido, e a previsão sobre "um job que falha é o retorno esperado" se confirmou três vezes.** A única previsão errada foi sobre *qual* job falharia.

> ⚠️ **Previsão explícita:** o job `secrets` provavelmente falha, porque o histórico realmente contém as credenciais antigas. A decisão sobre o que fazer com isso (ignorar as revisões conhecidas × reescrever o histórico) está aberta desde a rev. 8.0 e precisa ser tomada — este sprint força a decisão.

---

### Sprint A6 — Quadro Kanban de colunas e cards `CONCLUÍDA`

Traduz o quadro-modelo real da STW (31 listas, 214 cards) para a plataforma.
Acrescenta ao domínio de card quatro conceitos que ele não tinha: **coluna** por quadro
(`DashboardColumn`), **posição** manual (índice fracionário em `String(64)`),
**descrição** normativa e **etiqueta** de criticidade.

- Migration `c8f1a3e57b90` (`down_revision = b7c02e91d4a5`), com backfill de coluna,
  posição e descrição — nenhum quadro existente fica vazio depois do upgrade.
- `GET /dashboard/companies/{id}/board` devolve o quadro pronto, em custo constante
  de queries (barreira em `test_query_budget.py`, 5 e 20 colunas sob o mesmo teto).
- `PATCH /dashboard/cards/{id}/move` faz **exatamente 1 UPDATE** por arrasto.
- Primeira dependência de UI do projeto: `@dnd-kit` (3 pacotes, versão fixa), com
  fallback obrigatório sem arrasto ("Mover para…") para teclado e toque.
- Rota nova `/private/client/quadro`: o cliente passa a ver o quadro da própria
  empresa em modo leitura (U6/U7).
- Corrige, de passagem, um defeito de origem: `apply_template_to_company` descartava
  em silêncio a `description` do card de template desde O.3.

Itens abertos como backlog: **D-2** (`NAO_APLICAVEL` como status) e **D-4** (anexos
em card).

---

### Sprint A4 — Achados de borda `🔴 EM SEGUIDA — 1,5 dia`

#### Dia 1 (manhã) — Entrada e credencial

| # | Item | Achado | Onde | Esforço |
|---|---|---|---|---|
| 1 | Limite do bcrypt como contrato explícito | **B-A27** | `core/security.py`, `schemas/auth.py`, `api/v1/auth.py` | 1 h |
| 2 | `tests/test_password_limits.py` (8 testes) | barreira | — | 30 min |
| 3 | Contrato de falha no e-mail + função por papel | **B-A29**, **B-M27** | `services/email_sender.py`, `admin_onboarding.py`, `sub_users.py`, 2 schemas, 1 componente | 2 h |
| 4 | `tests/test_credentials_delivery.py` + `test_email_content.py` (7 testes) | barreira | — | 1 h |

**Critério de saída:** `POST /auth/login` com senha de 100 caracteres → **401** (não 500). Onboarding sem SMTP → a senha temporária aparece na tela do admin, com aviso, e autentica.

#### Dia 1 (tarde) — Leitura e configuração

| # | Item | Achado | Onde | Esforço |
|---|---|---|---|---|
| 5 | `Action.READ_CARD_INTERNALS` + filtro em `get_card_details` | **B-A28** | `core/policy.py`, `api/v1/dashboard_cards.py` | 1 h 30 |
| 6 | `tests/test_card_internals_visibility.py` + seção de leitura na matriz | barreira **M-23** | — | 1 h |
| 7 | Defaults: `ALLOW_PUBLIC_REGISTRATION=False`, `JWT_EXPIRES_MINUTES ?? 15` | **B-M25**, **B-M29** | `core/config.py`, `proxy.ts`, `login/route.ts` | 15 min |
| 8 | `tests/test_config_defaults.py` (3 testes) | barreira **M-24** | — | 15 min |

**Critério de saída:** cliente e sub-usuário recebem `checklist: []` e `history: []`; admin continua vendo tudo; a tela do admin não muda.

#### Dia 2 (manhã) — Storage e limpeza

| # | Item | Achado | Onde | Esforço |
|---|---|---|---|---|
| 9 | Guarda de path traversal em `get_absolute_path` | **B-M28** / **M-16b** | `services/storage.py`, `api/v1/admin.py` | 1 h |
| 10 | `tests/test_storage_path_guard.py` (parametrizado) | barreira | — | 30 min |
| 11 | Achados Baixos em lote | **B-B17..B-B23** | 6 arquivos | 2 h |

**Critério de saída do Sprint A4:** `pytest -q` → **~225 passed**; `ruff`, `tsc` e `eslint` limpos; 0 achados Alta em `relatorio_bugs.md`.

> **Fora deste sprint, de propósito: B-M26 (N+1 na listagem de empresas).** É o achado mais delicado de corrigir — muda um caminho de código já coberto por testes — e o menos urgente operacionalmente (5 empresas na base). Vai para o Sprint C, junto com M-25 (orçamento de queries), onde a correção e a barreira que a protege são entregues juntas.

---

### Sprint B — Testes de Frontend `2–3 dias` `🔓 DESTRAVADO`

Pela primeira vez em três revisões, este sprint não cede a vez. Detalhamento completo em `relatorio_melhorias.md` → **M-08b**.

| Dia | Entrega | Critério de saída |
|---|---|---|
| **1** | Vitest + Testing Library + `vitest.config.ts` + `npm test` no job `frontend` do CI | `npm test` roda no CI e falha se um teste falhar |
| **1–2** | Testes dos **9 grupos de Server Actions** (`actions.ts`), com `callBackend` mockado | Cada action: caminho feliz, erro do backend, e a URL/método corretos |
| **2** | `lib/session.ts`, `lib/safe-redirect.ts`, `proxy.ts` | Guardas de papel e anti-open-redirect cobertos |
| **3** | Os 4 componentes acima de 500 LOC — testes de comportamento, não de snapshot | Fluxos principais de cada um |

**Meta de cobertura:** ≥ 60% nas Server Actions e em `lib/`. Não perseguir número global — a cobertura de componentes vem no Sprint C, junto com a decomposição.

**Justificativa que não muda:** três auditorias adversariais seguidas produziram achados quase só de backend. Não porque o frontend esteja mais correto — porque não há como sondá-lo.

---

### Sprint C — Componentização, Performance e Observabilidade `4–5 dias`

| Dia | Entrega | Item |
|---|---|---|
| **1** | Fixture de contagem de queries + orçamento em 5 rotas | **M-25** |
| **1** | Corrigir o N+1 de `GET /admin/companies` (`_bulk_admin_data`) | **B-M26** |
| **2** | `core/access.py` — unificar as 4 implementações de posse | **M-01c** |
| **2–4** | Decompor os 4 arquivos acima de 500 LOC | **M-17** |
| **5** | Métricas Prometheus + `/metrics` | **M-07b** |

**Critério de saída:** nenhum arquivo de frontend acima de 500 LOC; nenhuma rota de listagem com custo linear em queries; uma implementação de posse; `/metrics` respondendo.

**Ordem obrigatória:** M-25 **antes** de B-M26 (a barreira precisa reprovar o código atual para provar que funciona) e M-08b **antes** de M-17 (decompor sem teste é reescrever no escuro).

---

## FASE 3 — Preparação para Produção `🟡 70% concluída`

### Critérios de saída

| Critério | Estado |
|---|---|
| Dockerfiles para backend e frontend | ✅ Escritos (multi-stage no frontend, `output: standalone`) |
| `docker-compose.yml` da stack completa | ✅ Com healthcheck de MySQL e variáveis obrigatórias |
| Pipeline de CI | ✅ **4 jobs, executando e verdes** em `main` |
| `docker build` / `docker run` validados | 🔴 Nunca executados |
| Backend roda com mais de uma réplica | 🔴 **Não** — ver Sprint D2 |
| Backup e restore documentados e testados | 🟡 Documentados em `executar_projeto.md`; restore nunca ensaiado |
| Segredos fora do repositório | ✅ |

### Sprint D — Docker e CI/CD `🟡 validação real pendente`

| # | Passo | Esforço |
|---|---|---|
| 1 | `docker compose build` na raiz | 30 min |
| 2 | `docker compose up -d` com `.env` de teste | 30 min |
| 3 | Verificar: MySQL saudável, `alembic upgrade head` no entrypoint, `/health` respondendo, frontend em `:3000` | 1 h |
| 4 | `GET /docs` **dentro do container** — o defeito nº 14 só aparece no navegador | 15 min |
| 5 | Registrar o resultado em `deploy_producao.md` | 30 min |

### Sprint D2 — Escala horizontal `3 dias` `🔴 bloqueador de produção multi-nó`

| Dia | Entrega | Item |
|---|---|---|
| **1** | `S3StorageBackend` satisfazendo o `Protocol` (inclusive `delete`) + `STORAGE_BACKEND` em `Settings` | **M-26** |
| **2** | Migração dos arquivos existentes + `prune_orphan_uploads.py` ciente do backend ativo | **M-26** |
| **3** | Rate limit com `storage_uri` Redis + teste com 2 réplicas atrás de um proxy | **M-26** |

**Critério de saída:** duas réplicas do backend; upload numa e download na outra; o limite de 5 logins/min respeitado no conjunto, não por réplica.

> ⚠️ **Até o fim deste sprint, não rode o backend com mais de um worker ou réplica.** Evidências em volume local e rate limit em memória de processo.

---

### Sprint E — Ciclo de vida da credencial `2 dias`

Agrupado nesta revisão porque os três itens são o mesmo problema visto de ângulos diferentes: **a credencial do cliente não tem volta**.

| # | Entrega | Item |
|---|---|---|
| 1 | `must_change_password` + bloqueio de rota até a troca | **M-02b** |
| 2 | Recuperação de senha (token de uso único, expiração curta, e-mail) | **M-29** |
| 3 | Revogação de sessão (blocklist de `jti` ou tabela de sessões) | **M-28** |
| 4 | E-mail assíncrono, agora que existe contrato de falha (M-22) | **M-09** |

**Critério de saída:** um cliente que perdeu a senha consegue recuperá-la sozinho; um logout invalida o `refresh_token` no servidor; a senha temporária tem prazo.

---

## FASE 4 — Crescimento e Escala `🟢 45% concluída`

- ✅ Exportação de relatório de auditoria em PDF (Iteração A)
- ✅ KPIs agregados de conformidade em uma única query (Iteração A)
- ⬜ Exportação de dados em CSV (Iteração A)
- ⬜ Histórico de evolução de conformidade ao longo do tempo (Iteração A)
- ✅ Chat por controle, por card e canal geral por empresa (Iteração B)
- ✅ Badges de mensagens não lidas com contadores independentes (Iteração B)
- ⬜ Notificação por e-mail em mudança de status (Iteração B — N06)
- ⬜ Notificação in-app (Iteração B)
- ⬜ Rejeição formal de evidência (Iteração C — N05)
- ⬜ Bloqueio de conta por tentativas de login (Iteração C — N02)
- ⬜ Portal de autoatendimento do cliente (Iteração C)
- ⬜ Trilha de auditoria append-only (Iteração D — M-07c)
- ⬜ Webhooks para sistemas externos (Iteração D)
- ⬜ Chaves de API para integração (Iteração D)
- ⬜ Versionamento da API em v2 (Iteração D)

| Iteração | Tema | Conclusão |
|---|---|---|
| **A** | Relatórios e Analytics | 🟢 ~60% |
| **B** | Comunicação e Notificações | 🟡 ~40% |
| **C** | Multi-Empresa e Self-Service | ⬜ 0% |
| **D** | Integrações e API Pública | ⬜ 0% |

> **Nota de formato.** Esta seção usava linhas com itens separados por `·`. Foi convertida em lista porque `parse_roadmap` (em `docs/mindmeister_automacao.md`) lê itens de fase a partir de listas e de tabelas — no formato anterior, a Fase 4 aparecia no mapa mental como um galho **vazio**, sem erro nenhum. É a mesma classe de falha silenciosa que o diagnóstico da v2.0 daquele documento descreve.

---

## Dependências Técnicas

```
Sprint A5 (1ª execução do CI)
  └── Não depende de NADA. Bloqueia a confiança em tudo do BLOCO P.
      └── Decisão pendente que ele força: histórico do git (ignorar × purgar)

Sprint A4 (achados de borda)
  ├── B-A27 → independente
  ├── B-A29 + B-M27 → mesmo arquivo, entrega conjunta obrigatória
  ├── B-A28 → depende de policy.py (já existe)
  ├── B-M25 + B-M29 → independentes, um teste cobre os dois
  └── B-M28 → PRÉ-REQUISITO do Sprint D2
                └── se o S3StorageBackend nascer antes, nasce sem a guarda

Sprint B (testes de frontend)
  └── Não depende de nada
      └── DESBLOQUEIA Sprint C (M-17: decompor sem teste é reescrever no escuro)

Sprint C
  ├── M-25 (orçamento) ANTES de B-M26 (correção do N+1)
  │     └── a barreira precisa reprovar o código atual para provar que funciona
  ├── M-01c depende de decidir B-B23 (403 × 404) — a unificação carrega a decisão
  └── M-17 depende de Sprint B

Sprint D2 (escala horizontal)
  ├── Depende de B-M28 (guarda no ponto único)
  ├── StorageBackend Protocol já existe (M-16) — o delete é obrigatório por contrato
  └── Bloqueia: qualquer deploy com mais de uma réplica

Sprint E (ciclo de vida da credencial)
  ├── M-09 (e-mail assíncrono) depende de M-22 (contrato de falha) — Sprint A4
  └── M-29 (recuperação) resolve a consequência de longo prazo de B-A29

audit_log append-only (M-07c)
  └── Parcialmente mitigado por B-A23 (só admin escreve o histórico)
  └── Depende de decisão sobre retenção e volume
```

---

## Riscos e Alertas

### ~~Risco 0 — Credenciais válidas e públicas~~ `✅ FECHADO em 2026-08-25`
Rotacionadas. Verificado nesta revisão: nenhum valor do `.env` atual aparece em commit algum. Resta a **decisão** sobre o histórico, que o Sprint A5 força.

### ~~Risco 1 — Usar a tela de templates~~ `✅ FECHADO`
`UniqueConstraint` + backfill + 409 na exclusão em uso. Aplicar template a uma empresa existente é seguro e idempotente.

### ~~Risco 2 — Exclusão de empresa com evidências~~ `✅ FECHADO`
`delete_files()` após o commit. Para os órfãos anteriores: `python scripts/prune_orphan_uploads.py --apply`.

### Risco 3 — Confiança excessiva na suíte verde `🟡 MÉDIO, persistente`

202 testes verdes, `ruff` limpo, `tsc` limpo, `eslint` limpo — e a auditoria desta revisão encontrou 15 achados, três deles Alta.

O caso mais instrutivo continua sendo o **defeito nº 14**: havia um teste de CSP, ele passava, e `/docs` renderizava em branco. O teste perguntava *"o header está presente?"*; a pergunta certa era *"sob este header, os recursos que a página pede continuam permitidos?"*.

**Mitigação:** manter a auditoria adversarial por sonda a cada ciclo, e escrever o teste de barreira **verificando que ele reprova o código antigo** antes de aplicar a correção. Foi o que o BLOCO P fez (P.4.4 documenta a verificação por reversão) e é o que os testes propostos no Sprint A4 devem fazer.

### ~~Risco 4 — As barreiras do BLOCO P nunca executaram~~ `✅ FECHADO em 2026-08-26`

O risco se materializou exatamente como descrito: **3 dos 4 jobs reprovaram na primeira execução**, e um deles (`backend`) tinha erro de configuração — faltavam as variáveis de ambiente, então ele nunca poderia ter passado.

Os 4 jobs agora executam e passam em `main`. A generalização deste risco — *quais automações ainda não executaram* — virou o item **M-30** de `relatorio_melhorias.md`, com a lista do que continua sendo intenção documentada (Docker, restore de backup, Trello, MindMeister, deploy).

### Risco 5 — Backend não escala horizontalmente `🟡 MÉDIO, futuro`

Evidências em volume local, rate limit em memória. **Não rode com mais de um worker/réplica** até o Sprint D2.

### Risco 6 — A credencial do cliente não tem volta `🟠 ALTO` `🆕`

Não há recuperação de senha, não há troca obrigatória no primeiro login, e a senha temporária existe apenas dentro do e-mail. Sem SMTP, ela não existe em lugar nenhum (**B-A29**).

**Consequência operacional imediata:** todo cliente onboardado em dev ou homologação sem SMTP está inacessível. **Mitigação de curto prazo:** Sprint A4, item 3 (a senha volta na resposta). **Mitigação completa:** Sprint E.

### Risco 7 — Dívida de `tag` duplicando `category.name` `🟢 BAIXO`

`DashboardCard.tag` e `DashboardTemplateCard.tag` são mantidos em sincronia com o nome da categoria em todo caminho de escrita. Funciona, e é sincronia manual. A remoção exige antes tornar `category_id` NOT NULL.

---

## Métricas de Sucesso por Fase

### Fase 1 — Estabilização `✅ 100%`

| Métrica | Meta | Atual |
|---|---|---|
| Achados Críticos abertos | 0 | **0** ✅ |
| Segredos em arquivo versionado | 0 | **0** ✅ |
| Cabeçalhos de segurança | 7 | **7** ✅ |
| Ações de escrita com política explícita | 100% | **100%** ✅ |
| Varredura de CVE no CI | sim | **sim** ✅ (nunca executada) |

### Fase 2 — Qualidade `🟡 88% → meta 100% ao fim do Sprint C`

| Métrica | Meta | Atual |
|---|---|---|
| Testes de backend | ≥ 200 | **202** ✅ |
| Testes de frontend | ≥ 40 | **0** 🔴 |
| Achados Alta abertos | 0 | **3** 🟠 |
| Arquivos > 500 LOC (frontend) | 0 | **4** 🔴 |
| Rotas com orçamento de queries | ≥ 5 | **0** 🔴 |
| Implementações de checagem de posse | 1 | **4** 🔴 |

### Fase 3 — Produção `🟡 70% → meta 100% ao fim do Sprint D2`

| Métrica | Meta | Atual |
|---|---|---|
| Execuções reais do pipeline | ≥ 1 | **0** 🔴 |
| `docker build` validado | sim | **não** 🔴 |
| Réplicas de backend suportadas | ≥ 2 | **1** 🔴 |
| Restore de backup ensaiado | sim | **não** 🔴 |

### Fase 4 — Crescimento `🟢 45%`

| Métrica | Meta | Atual |
|---|---|---|
| Requisitos formais atendidos | 38/38 | **28/38** (74%) |
| Funcionalidades concluídas | — | **78** (F01–F78) |
| Endpoints sem UI consumidora | 0 | **2** |

---

## Resumo de Esforço Restante

| Sprint | Esforço | Prioridade | Destrava |
|---|---|---|---|
| **A5** — 1ª execução do CI | **1 h** | 🔴 hoje | Confiança em todo o BLOCO P |
| **A4** — Achados de borda | **1,5 dia** | 🔴 em seguida | Faixa Alta zerada |
| **B** — Testes de frontend | **2–3 dias** | 🟠 alta | Sprint C · auditabilidade do frontend |
| **C** — Componentização + performance + métricas | **4–5 dias** | 🟡 média | Fase 2 em 100% |
| **D** — Validação de Docker | **3 h** | 🟡 média | Deploy |
| **D2** — Escala horizontal | **3 dias** | 🟡 média | Produção multi-nó |
| **E** — Ciclo de vida da credencial | **2 dias** | 🟡 média | Autoatendimento do cliente |
| **Total até Fase 3 completa** | **~14 dias** | | |

### Se houver tempo para apenas uma coisa

**Sprint A5.** Uma hora. Cinco barreiras estruturais e quatro jobs de CI foram construídos e nunca executados no ambiente para o qual foram escritos. Nenhum outro item deste roadmap tem essa relação entre custo e o que esclarece.

### Se houver tempo para apenas duas

**Sprint A5 + Sprint B.** A primeira converte suposições em garantias; a segunda torna 7.811 linhas auditáveis pela primeira vez. Juntas, mudam a natureza da próxima auditoria — que hoje só consegue enxergar metade do sistema.

---

*Roadmap atualizado em 2026-08-26 (rev. 7.0) a partir do estado real do código em `34f8444`, com percentuais recalculados por verificação — não herdados da revisão anterior. Os Sprints A0 e A3, previstos na rev. 6.0, foram executados e verificados item a item; os 5 itens estruturais que os acompanhavam foram entregues.*
