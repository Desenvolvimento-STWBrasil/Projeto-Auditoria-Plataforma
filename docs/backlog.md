# Backlog — Plataforma de Auditoria

| Campo | Valor |
|---|---|
| **Versão** | **4.0 — 2026-08-26** |
| **Branch / HEAD** | `main` · `c769526` |
| **Fontes consolidadas** | [`relatorio_bugs.md`](relatorio_bugs.md) 10.0 · [`relatorio_melhorias.md`](relatorio_melhorias.md) 8.0 · [`roadmap.md`](roadmap.md) 8.0 · [`relatorio_funcionalidades.md`](relatorio_funcionalidades.md) 9.0 · [`relatorio_documentacao.md`](relatorio_documentacao.md) 7.1 |
| **Documentos irmãos** | [`index.md`](index.md) (navegação) · [`plano_implementacao.md`](plano_implementacao.md) (código pronto) · [`roadmap.md`](roadmap.md) (fases e sprints) |

---

## Como usar este documento

Este é o **backlog único e acionável** — a lista do que falta fazer, sem o volume técnico do `plano_implementacao.md` nem o horizonte de fases do `roadmap.md`. Cada item tem prioridade, esforço e um link para o contexto completo.

> ### ✅ O que mudou na v4.0
>
> **As Seções 0, 1 e 2 foram executadas por completo em 2026-08-26.** O que era o topo urgente do
> backlog — validar as barreiras, corrigir os 3 achados Alta, escrever os testes de frontend —
> está feito.
>
> | Bloco | Entregue |
> |---|---|
> | **Q** | Os 3 achados Alta + 4 Médios + 7 Baixos · suíte de 202 → 250 |
> | **R** | Frontend de **0 → 114 testes** · orçamento de queries · ponto único de posse |
> | **S** | **O CI executou pela primeira vez** e revelou 4 defeitos, todos corrigidos |
>
> **0 achados abertos.** O topo do backlog volta a ser trabalho planejado, não dívida.
>
> ⚠️ **A única coisa que continua em aberto do bloco urgente** é o item 0.7: a decisão sobre o
> histórico do git. E ela mudou de natureza — o `gitleaks` **passou**, enquanto o GitGuardian
> acusa **14 segredos** nos mesmos 39 commits. Dois scanners, o mesmo histórico, respostas
> opostas.

---

## 0. ~~HOJE — Validar as barreiras~~ `✅ CONCLUÍDO em 2026-08-26`

> Executado. **3 dos 4 jobs reprovaram na primeira execução**, e cada reprovação era um defeito
> real: **B-A30** (cadeia de downgrade quebrada), **B-A31** (9 CVEs, 7 no parser de upload),
> **B-M30** (job sem variáveis de ambiente) e **B-M31** (`tsc` sem os tipos gerados).
>
> Todos corrigidos; CI verde nos 4 jobs em `main`. O item 0.7 — a decisão sobre o histórico do
> git — **continua em aberto**, e mudou de natureza: o `gitleaks` **passou**, enquanto o
> GitGuardian acusa 14 segredos nos mesmos commits.
>
> Registro em `plano_implementacao.md` → **BLOCO S**.

<details>
<summary>Plano original (mantido para referência)</summary>


| # | Item | ID | Esforço |
|---|---|---|---|
| 0.1 | `git push` da branch para `origin` | **A5** | 2 min |
| 0.2 | Abrir PR contra `main` | **A5** | 5 min |
| 0.3 | Acompanhar o job **`backend`** — `ruff` + `pip-audit` + `pytest --cov` | A5 | — |
| 0.4 | Acompanhar o job **`frontend`** — `npm ci` + `lint` + `tsc` + `build` | A5 | — |
| 0.5 | Acompanhar o job **`secrets`** — gitleaks sobre o histórico completo | A5 | — |
| 0.6 | Acompanhar o job **`migrations`** — `upgrade head` → `downgrade base` → `upgrade head` contra MySQL 8.4 real | A5 | — |
| 0.7 | **Decidir e registrar:** `.gitleaksignore` com as revisões conhecidas **ou** purgar o histórico | B-C23 | 20 min |
| 0.8 | Registrar o resultado de cada job em [`automacao_commits.md`](automacao_commits.md) | A5 | 15 min |

> **Por que isto vem antes de tudo.** O BLOCO P instalou cinco barreiras estruturais e o CI passou de 2 para 4 jobs. **Nenhum deles rodou no GitHub Actions.** Uma barreira validada só por leitura é uma suposição sobre uma barreira, e todos os outros itens deste backlog assumem que elas funcionam.
>
> ⚠️ **Previsão explícita:** o job `secrets` provavelmente **falha** — o histórico realmente contém as credenciais antigas, já rotacionadas mas presentes. Falhar é o resultado esperado; o item 0.7 é o que este bloco entrega.

---

</details>

---

## 1. ~~Prioridade Alta — Sprint A4~~ `✅ CONCLUÍDO — BLOCO Q`

> Os 15 achados da auditoria de 2026-08-26 estão fechados. `pytest` foi de 202 para **250**, e as
> 5 barreiras foram **verificadas por reversão** — cada correção desfeita individualmente para
> confirmar que o teste falha sem ela.
>
> A aplicação encontrou **6 defeitos**, três da família *código correto no lugar errado* — um
> deles impedia a aplicação de inicializar. Relatório em `plano_implementacao.md` → **Q.7**.

<details>
<summary>Plano original do Sprint A4 (mantido para referência)</summary>


Cada correção vem pareada com a **barreira** que impede a reincidência. Corrigir sem a barreira já foi tentado aqui mais de uma vez.

### 1.1 — Entrada e credencial (Dia 1, manhã)

| # | Item | ID | Esforço |
|---|---|---|---|
| 1.1.1 | `MAX_PASSWORD_BYTES` + `PasswordTooLongError` em `core/security.py` | **B-A27** | 30 min |
| 1.1.2 | `verify_password` devolve `False` (não levanta) acima do limite — sem oráculo | **B-A27** | 10 min |
| 1.1.3 | `except ValueError` defensivo para hash corrompido no banco | B-A27 | 5 min |
| 1.1.4 | Validador de tamanho em `UserCreate` e `UserLogin` | **B-A27** | 15 min |
| 1.1.5 | Tratamento de `PasswordTooLongError` em `auth.py::register` → 422 | B-A27 | 10 min |
| 1.1.6 | **Barreira:** `tests/test_password_limits.py` — 8 testes | **M-21** | 30 min |
| 1.1.7 | `_enviar(msg) -> bool` captura `SMTPException`/`OSError` e nunca propaga | **B-A29** | 45 min |
| 1.1.8 | `send_principal_user_credentials_email` — função própria por destinatário | **B-M27** | 30 min |
| 1.1.9 | `email_delivered` + `temporary_password` nas respostas de onboarding e aprovação | **B-A29** | 45 min |
| 1.1.10 | Frontend exibe a senha com aviso âmbar quando `emailDelivered === false` | B-A29 | 30 min |
| 1.1.11 | **Barreira:** `tests/test_credentials_delivery.py` + `test_email_content.py` — 7 testes | **M-22** | 1 h |

**Saída:** `POST /auth/login` com senha de 100 caracteres responde **401** (não 500). Onboarding sem SMTP exibe a senha na tela do admin, e essa senha autentica.

### 1.2 — Leitura e configuração (Dia 1, tarde)

| # | Item | ID | Esforço |
|---|---|---|---|
| 1.2.1 | `Action.READ_CARD_INTERNALS` em `core/policy.py` | **B-A28** | 15 min |
| 1.2.2 | `get_card_details` filtra `checklist` e `history` para não-admin (listas vazias, não 403) | **B-A28** | 45 min |
| 1.2.3 | **Barreira:** `tests/test_card_internals_visibility.py` — 3 testes | B-A28 | 30 min |
| 1.2.4 | **Barreira:** seção `LEITURAS_RESTRITAS` em `test_authorization_matrix.py` | **M-23** | 30 min |
| 1.2.5 | `ALLOW_PUBLIC_REGISTRATION: bool = False` | **B-M25** | 2 min |
| 1.2.6 | `JWT_EXPIRES_MINUTES ?? 15` em `proxy.ts` e `login/route.ts` | **B-M29** | 10 min |
| 1.2.7 | **Barreira:** `tests/test_config_defaults.py` — 3 asserções | **M-24** | 15 min |

**Saída:** cliente e sub-usuário recebem `checklist: []` e `history: []`; o admin continua vendo tudo; a tela do admin não muda.

### 1.3 — Storage e limpeza (Dia 2, manhã)

| # | Item | ID | Esforço |
|---|---|---|---|
| 1.3.1 | `_resolver_dentro_do_upload_dir()` como ponto único em `storage.py` | **B-M28** | 30 min |
| 1.3.2 | `get_absolute_path()` passa a usá-lo; `delete_files()` o consome | **B-M28** | 20 min |
| 1.3.3 | `StorageKeyOutsideUploadDirError` tratada em `download_evidence` → 404 | B-M28 | 15 min |
| 1.3.4 | **Barreira:** `tests/test_storage_path_guard.py` parametrizado | **M-16b** | 30 min |
| 1.3.5 | Achados Baixos em lote — **B-B17 a B-B23** | — | 2 h |

> ⚠️ **B-B23 (403 → 404) toca 3 arquivos** e as asserções de teste que hoje afirmam 403. Aplicar junto com **M-01c** (Seção 3), que unifica os três — ou aceitar aplicar duas vezes.

**Saída do Sprint A4:** `pytest -q` → **~225 passed**; `ruff`, `tsc` e `eslint` limpos; **0 achados Alta** em `relatorio_bugs.md`.

</details>

> ✅ **Resultado real: 250 passed** — acima da estimativa, porque as barreiras acabaram maiores que
> o previsto (o orçamento de `test_storage_path_guard.py` sozinho ficou em 12 testes).

---

## 2. ~~Curto prazo — testes de frontend~~ `✅ CONCLUÍDO — BLOCO R`

> **114 testes**, 81% de statements e **93,5% de funções**, cobrindo os 9 grupos de Server
> Actions, `lib/session.ts`, `lib/safe-redirect.ts` e `proxy.ts`. Job `npm run test` acrescentado
> ao `ci.yml` e **executando**.
>
> Restam desta seção: o item **2.4** (reescrever o `backend/README.md`) e o **2.5** (atualizar os
> `PATH_ALERTS`) — ambos movidos para a Seção 3.

<details>
<summary>Plano original (mantido para referência)</summary>

### 2 — Curto prazo (original)

| # | Item | ID | Esforço | Por quê |
|---|---|---|---|---|
| 2.1 | **Testes de frontend** — Vitest + Testing Library + job no CI | **M-08b** | 2–3 dias | Maior gap do projeto. 7.811 LOC, 15 páginas, zero testes |
| 2.2 | Testes dos 9 grupos de Server Actions (`callBackend` mockado) | M-08b | incluso | Contrato com o backend, sem DOM |
| 2.3 | Testes de `lib/session.ts`, `lib/safe-redirect.ts` e `proxy.ts` | M-08b | incluso | Autorização e anti-open-redirect |
| 2.4 | Reescrever `backend/README.md` como índice | **RD-02..RD-11** | 1 h | Fecha 8 divergências de uma vez. **RD-04 é urgente**: manda usar uma rota que responde 404 |
| 2.5 | Atualizar `PATH_ALERTS` do gerador de relatório de commits | — | 20 min | Os alertas citam achados já fechados |

> **Justificativa de 2.1, que não muda:** três auditorias adversariais seguidas produziram achados quase exclusivamente de backend. Não porque o frontend esteja mais correto — porque não há como sondá-lo.

---

</details>

---

## 3. Médio prazo — próximo mês

| # | Item | ID | Esforço | Por quê |
|---|---|---|---|---|
| 3.1 | **Orçamento de queries por rota** — fixture + 5 rotas | **M-25** | 4 h | A suíte tem 202 testes e nenhum mede custo |
| 3.2 | Corrigir o N+1 de `GET /admin/companies` (`_bulk_admin_data`) | **B-M26** | 3 h | 73 queries para 10 empresas. ⚠️ **depois de 3.1** |
| 3.3 | `core/access.py` — unificar as 4 implementações de posse | **M-01c** | 3 h | Uma delas já carrega um typo que as outras não têm |
| 3.4 | Decompor os 4 arquivos de frontend acima de 500 LOC | **M-17** | 3 dias | ⚠️ **depende de 2.1** — decompor sem teste é reescrever no escuro |
| 3.5 | Storage trocável (S3/Azure) + rate limit em Redis | **M-26** | 2–3 dias | ⚠️ **depende de 1.3** — sem a guarda no ponto único, o backend novo nasce sem ela |
| 3.6 | Troca de senha obrigatória no 1º login + recuperação de senha | **M-02b, M-29** | 2 dias | A credencial do cliente hoje não tem volta |
| 3.7 | Métricas Prometheus + `/metrics` | **M-07b** | 4 h | Responder "está lento?" com dado |
| 3.8 | Validar `docker build` / `docker run` reais | **Sprint D** | 3 h | Nunca foram executados |

> ⚠️ **Ordem obrigatória em 3.1 → 3.2.** A barreira precisa **reprovar o código atual** para provar que funciona. Escrever o orçamento depois da correção produz um teste que nunca falhou.

---

## 4. Longo prazo — próximo trimestre

| # | Item | ID | Esforço | Por quê |
|---|---|---|---|---|
| 4.1 | `audit_log` append-only | **M-07c** | 1–2 dias | Requisito formal **RNF-02** ainda aberto |
| 4.2 | Revogação de sessão (blocklist de `jti` ou tabela de sessões) | **M-28** | 1 dia | Logout é client-side; `refresh_token` vazado vale 7 dias |
| 4.3 | E-mail assíncrono (fila) | **M-09** | 1 dia | Destravado por M-22 (Sprint A4) |
| 4.4 | Validação de arquivo por conteúdo, não por extensão | **M-02d** | 1 dia | Hoje um `.exe` renomeado para `.pdf` passa |
| 4.5 | Decidir o destino do soft delete | **N11 / B-B19** | 1 dia | Os mixins existem e **zero queries** os consultam |
| 4.6 | Índices / FULLTEXT para a busca de empresas | **M-27** | 4 h | Só quando a base justificar |
| 4.7 | Gerar o catálogo do Trello a partir de `relatorio_bugs.md` | — | 4 h | Segundo ciclo em que o catálogo precisa ser reescrito à mão |

---

## 5. Próximo ciclo de produto — Fase 4 do roadmap

| # | Item | Origem | Esforço |
|---|---|---|---|
| 5.1 | Gráficos de progresso no dashboard admin (os números já existem) | **FNI-12** | 2 dias |
| 5.2 | Exportação de dados em CSV | Iteração A | 1 dia |
| 5.3 | Histórico de evolução de conformidade no tempo | Iteração A | 3 dias |
| 5.4 | Notificação por e-mail em mudança de status | **N06 / P05** | 2 dias |
| 5.5 | Rejeição formal de evidência (novo status + migration) | **N05** | 2 dias |
| 5.6 | Máquina de estados: checklist completo → status automático | **FNI-05** | 2 dias |
| 5.7 | Gatilho: upload de evidência → status `EM_ANALISE` | **FNI-09** | 2 h |
| 5.8 | Regra: status "Parcial" obriga comentário | **FNI-10** | 1 dia |
| 5.9 | Bloqueio de conta por tentativas de login | **N02** | 1 dia |
| 5.10 | CRUD do `ControlCatalog` via interface | **FNI-15** | 2 dias |
| 5.11 | Branding STW na homepage | **FNI-16 / D-08** | 2 h |
| 5.12 | MFA | **RF-17 / FNI-14** | 1 semana |
| 5.13 | Notificações em tempo real (WebSocket/SSE) | **RF-11 / FNI-13** | 2 semanas |
| 5.14 | Chat compartilhado entre admins | **RF-13** | 3 dias |
| 5.15 | `NAO_APLICAVEL` como 5º valor de `DashboardCardStatus` | **D-2** (PRD Quadro Kanban) | 2 dias |
| 5.16 | Anexos em card de dashboard | **D-4** (PRD Quadro Kanban) | 3 dias |

### Quadro Kanban — as duas decisões deixadas fora da v1 (CA-31)

#### D-2 — `NAO_APLICAVEL` como 5º valor de `DashboardCardStatus`

**Origem:** decisão D-2 do PRD do Quadro Kanban (2026-08-27), resolvida em v1 pela
opção (b) — etiqueta comum — e registrada aqui para a opção (a).

**Problema.** Um controle "não aplicável" não é `CONFORME` nem `NAOCONFORME`, e
deixá-lo em `EM_ANALISE` para sempre polui os 4 KPIs de
`get_dashboard_status_summary`: a Home mostra como trabalho em aberto algo que nunca
será fechado.

**Escopo.** Migration de `ENUM` no MySQL + `lib/control-status.ts` +
`DashboardStatusSummary` + os 3 dashboards que exibem status + testes. O precedente
existe e está documentado: a migration `c2a7e6f1b8d3` acrescentou `NAOCONFORME` a
`audit_control_status` exatamente assim.

**Por que não entrou em v1.** Não bloqueia o quadro, e a etiqueta `Não Aplicável` do
quadro de origem tem 0 cards — não há dado real esperando por ela.

#### D-4 — Anexos em card de dashboard

**Origem:** decisão D-4 do PRD do Quadro Kanban (2026-08-27).

**Problema.** `Evidence` existe, mas é `FK → audit_controls.id`. Ligar anexo a
`DashboardCard` exige uma segunda FK opcional (`evidences.dashboard_card_id`) e
revisar `storage.py`, `test_storage_path_guard.py` e o download autenticado do
frontend.

**Por que não entrou em v1.** O export de referência tem **0 anexos** — não há
requisito comprovado. Entrar sem requisito significaria projetar a regra de posse do
arquivo (quem pode baixar o anexo de um card?) sem nenhum caso real para validá-la.

---

## 6. Funcionalidades parciais — decisão de produto pendente

| ID | Item | O que falta | Natureza |
|---|---|---|---|
| **P03** | Cadastro público | Nada tecnicamente — está atrás de `ALLOW_PUBLIC_REGISTRATION` | Decisão de produto |
| **P04** | Conteúdo dos templates vs. ISO 27001 Anexo A | Curadoria item a item. A ferramenta existe (F68) e aplicar template ficou seguro (F76) | Trabalho de conteúdo |
| **P05** | Notificação por e-mail ao mudar status | Decidir **quais** eventos notificam | Decisão de produto |

---

## 7. Débito técnico e achados abertos

### Achados ativos — 15

| Faixa | Qtd | IDs | Esforço total |
|---|---|---|---|
| 🔴 Crítica | **0** | — | — |
| 🟠 Alta | **3** | B-A27, B-A28, B-A29 | ~6 h |
| 🟡 Média | **5** | B-M25, B-M26, B-M27, B-M28, B-M29 | ~9 h |
| 🟢 Baixa | **7** | B-B17..B-B23 | ~2 h |

### Causas estruturais — 6 abertas

| ID | Causa | Achados que gerou | Esforço |
|---|---|---|---|
| **M-21** | Limites físicos de biblioteca não viram contrato | B-A27 | 3 h |
| **M-22** | Integração externa sem contrato de falha | B-A29, B-M27 | 3 h |
| **M-23** | `policy.py` só modela escrita | B-A28 | 2 h |
| **M-24** | Nenhum teste afirma o default do código | B-M25, B-M29 | 30 min |
| **M-25** | Custo de query não é medido | B-M26 | 4 h |
| **M-16b** | Barreira instalada no consumidor, não no ponto único | B-M28 | 1 h 30 |

### Divergências de documentação — 14

| Fonte | Qtd | Nota |
|---|---|---|
| `backend/README.md` × código | **8** | RD-04 **piorou**: indica uma rota que agora responde 404 |
| `Arquivo/` × código | **6** | D-10 é nova, vinda de B-A28 |
| Contradições internas em `docs/` | **0** | ✅ |

### Lacunas que bloqueiam produção

| Lacuna | Estado | Sprint |
|---|---|---|
| ~~Barreiras de CI nunca executaram~~ | ✅ | **Feito** — 4 jobs verdes em `main`; a 1ª execução revelou 4 defeitos |
| 0% de testes no frontend | 🔴 | B — 2–3 dias |
| Backend não escala horizontalmente | 🔴 | D2 — 3 dias |
| `docker build` nunca validado | 🔴 | D — 3 h |
| Restore de backup nunca ensaiado | 🔴 | D — 2 h |
| Credencial do cliente sem recuperação | 🟠 | E — 2 dias |

---

## 8. Ordem recomendada de execução

```
HOJE (1 h)
└── 0.1–0.8  Abrir PR e deixar o ci.yml rodar
    └── decide: histórico do git (ignorar × purgar)

SPRINT A4 (1,5 dia)
├── 1.1  Entrada e credencial   (B-A27 · B-A29 + B-M27 · M-21 · M-22)
├── 1.2  Leitura e configuração (B-A28 · B-M25 + B-M29 · M-23 · M-24)
└── 1.3  Storage e limpeza      (B-M28 · M-16b · B-B17..B-B23)
    └── 1.3 é PRÉ-REQUISITO de 3.5

SPRINT B (2–3 dias)
└── 2.1–2.3  Testes de frontend
    └── DESBLOQUEIA 3.4

SPRINT C (4–5 dias)
├── 3.1  Orçamento de queries   ◀── ANTES de 3.2
├── 3.2  Corrigir o N+1
├── 3.3  core/access.py         ◀── carrega a decisão de B-B23
├── 3.4  Decompor > 500 LOC     ◀── depende do Sprint B
└── 3.7  Métricas

SPRINT D + D2 (3 dias + 3 h)
├── 3.8  Validar Docker
└── 3.5  Storage trocável + Redis   ◀── depende de 1.3

SPRINT E (2 dias)
└── 3.6 + 4.2 + 4.3  Ciclo de vida da credencial

FASE 4 (contínuo)
└── Seção 5 — produto
```

**Esforço até a Fase 3 completa: ~14 dias.**

### Se houver tempo para apenas uma coisa

**Seção 0.** Uma hora. Cinco barreiras estruturais e quatro jobs de CI foram construídos e nunca executados no ambiente para o qual foram escritos. Nenhum outro item deste backlog tem essa relação entre custo e o que esclarece.

### Se houver tempo para apenas duas

**Seção 0 + Seção 2.1.** A primeira converte suposições em garantias; a segunda torna 7.811 linhas auditáveis pela primeira vez.

---

## 9. Referências

| Precisa de… | Leia |
|---|---|
| O código de correção de cada achado | [`relatorio_bugs.md`](relatorio_bugs.md) |
| Por que os achados aconteceram | [`relatorio_melhorias.md`](relatorio_melhorias.md) |
| O passo a passo técnico com código pronto | [`plano_implementacao.md`](plano_implementacao.md) |
| O sequenciamento em fases e sprints | [`roadmap.md`](roadmap.md) |
| A visão executiva | [`dashboard_projeto.md`](dashboard_projeto.md) |
| Navegar por tudo | [`index.md`](index.md) |

---

*Backlog atualizado em 2026-08-26 (v3.0). Os 18 itens da v2.0 foram executados e verificados um a um; os itens desta versão vêm da rev. 9.0 de `relatorio_bugs.md` e da rev. 7.0 de `relatorio_melhorias.md`, ambas confirmadas por sonda executável.*
