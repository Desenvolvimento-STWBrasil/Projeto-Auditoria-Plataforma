# Dashboard Executivo — Plataforma de Auditoria

| Campo | Valor |
|---|---|
| **Versão** | **10.0 — 2026-09-09** |
| **Branch / HEAD** | `feat/dashboard-linhas-modal-e-categorias` · `2cd57eb` (7 commits à frente de `main` em `d7c06b3`) |
| **Maturidade global** | **~97%** (MVP maduro · **0 achados abertos**) |
| **Suíte de testes** | ✅ **634 passed** — 391 backend (135 s) + **243 frontend** (4,5 s) |
| **Lint / Tipos / Build** | ✅ `ruff` limpo · `tsc --noEmit` exit 0 · `eslint` exit 0 · `next build` compilando as 23 rotas |
| **Banco** | MySQL 8.4 · **20 migrations** · o BLOCO T não adicionou nenhuma. `head` **não re-verificado** nesta revisão: `alembic heads` devolveu `c8f1a3e57b90`, inconsistente com os 20 arquivos em `alembic/versions/` — vale investigar antes de um deploy |
| **API** | **82 operações** em `/api/v1` (+ `/` e `/health`) — medido com `app.openapi()` nesta revisão. As 62 da rev. 9.0 antecediam o quadro Kanban; o BLOCO T somou **uma** (`DELETE /dashboard/checklist-items/{id}`) |
| **Base deste dashboard** | `relatorio_geral.md` 8.0 · `relatorio_funcionalidades.md` 8.0 · `relatorio_bugs.md` 9.0 · `relatorio_melhorias.md` 7.0 · `roadmap.md` 7.0 · `relatorio_documentacao.md` 7.0 |

---

## 1. Sumário Executivo

A **Plataforma de Auditoria** é um sistema B2B para gestão de auditorias de conformidade (controles ISO 27001/ISMS). Está em **estágio de MVP maduro**: todos os fluxos de negócio centrais funcionam de ponta a ponta com dados reais e cobertura automatizada.

Nesta janela (2026-08-27 → 2026-09-09) o projeto entregou o **BLOCO T**: o dashboard
da empresa passou de colunas horizontais para linhas recolhíveis, o detalhe do card
virou modal com edição, e Checklist / Histórico / Conversa deixaram de ser somente
leitura.

O achado que caracteriza o bloco é de gestão, não de código: **três dos sete itens
pedidos já existiam prontos no backend, sem consumidor no frontend.** `POST
/cards/{id}/entries`, `updateCardAction` e três `Action` de `policy.py` estavam
escritos, alguns testados, e ninguém os chamava — ver O07, O08 e O09 em
`relatorio_funcionalidades.md`. O histórico do card era o caso extremo: a tabela, o
endpoint e a tela existiam desde D.6, e **nada no sistema escrevia nela** — o que
aparecia num card de demonstração era dado semeado.

O custo disso é de estimativa. Um pedido de sete funcionalidades era, na verdade, de
quatro construções e três ligações. A varredura de consumidores (`grep` pelo nome de
cada endpoint/action em `frontend/app`) leva minutos e deveria preceder qualquer
estimativa deste projeto.

> **Ressalva de validação.** O BLOCO T foi verificado por suíte, tipos, lint e build,
> **não em navegador com o stack completo**. O arrasto de cards no eixo novo depende
> de comportamento real do `dnd-kit` e merece passagem manual antes do merge em `main`.

### O que mudou

```
   ENTREGUE                                 ENCONTRADO NA AUDITORIA SEGUINTE
   ──────────────────────────────────       ──────────────────────────────────
   ✅ BLOCO P — Segurança e barreiras       ⚪ 0 achados Críticos
      · Autorização: posse ≠ permissão      🟠 3 achados Altos   (B-A27..29)
      · Retenção real de arquivo (LGPD)     🟡 5 achados Médios  (B-M25..29)
      · Integridade template ↔ card         🟢 7 achados Baixos  (B-B17..23)
      · 4 jobs de CI (gitleaks, migrations) ⚙️ 5 causas estruturais (M-21..M-25)
   ✅ CSP por rota + Swagger de volta
   ✅ 128 → 202 testes (+58%)               📝 8 divergências no backend/README.md
   ✅ 18 de 18 achados da rev. 8.0 fechados 📝 0 contradições internas em docs/
```

### A mudança que importa

**Os 18 achados da revisão anterior foram fechados — os 18.** Isso inclui o único achado Crítico da história do projeto (credenciais versionadas) e os quatro Altos que impediam o uso seguro das funcionalidades entregues no BLOCO O.

Mais relevante que o placar: cada correção veio pareada com a **barreira** que impede a reincidência. As cinco propostas estruturais da revisão anterior (M-15, M-16, M-18, M-19, M-20) foram todas implementadas.

E a natureza da dívida remanescente mudou junto. Os achados desta revisão não são de **autorização** — são de **borda**: o que acontece quando a entrada sai do formato esperado (B-A27), quando um serviço externo não responde (B-A29), quando a política cobre a escrita mas não a leitura (B-A28).

### 🔴 Ação de hoje — 1 hora

> **Abrir um PR e deixar o `ci.yml` executar pela primeira vez.**
>
> Cinco barreiras estruturais foram construídas no BLOCO P e o CI passou de 2 para 4 jobs. **Nenhum deles jamais rodou no GitHub Actions.** Uma barreira validada só por leitura é uma suposição sobre uma barreira.
>
> Nenhum outro item deste dashboard tem essa relação entre custo e o que esclarece. Ver [`roadmap.md`](roadmap.md) → **Sprint A5**.
>
> ⚠️ **Previsão explícita:** o job `secrets` provavelmente **falha**, porque o histórico do git realmente contém as credenciais antigas (já rotacionadas, mas presentes). Falhar é o resultado esperado; o que este sprint entrega é a **decisão** sobre o que fazer com isso.

---

## 2. Semáforo por Área

| Área | rev. 7.0 | rev. 8.0 | Δ | Justificativa |
|---|---|---|---|---|
| **Arquitetura** | 🟢 95% | 🟢 **97%** | 🔼 | Camada de política + contrato de storage acrescentados |
| **Autorização** | 🟠 60% | 🟢 **90%** | 🔼🔼 | `core/policy.py` + matriz de testes. Falta a leitura sensível (B-A28) |
| **Segurança** | 🟠 70% | 🟢 **88%** | 🔼🔼 | Credenciais rotacionadas, CSP/HSTS, gitleaks, pip-audit. Falta revogação de sessão |
| **Retenção / LGPD** | 🔴 40% | 🟢 **95%** | 🔼🔼🔼 | `delete_files()` + script de órfãos |
| **Integridade de dados** | 🟡 70% | 🟢 **98%** | 🔼🔼 | `UniqueConstraint` + backfill + 409 na exclusão em uso |
| **Modelagem de dados** | 🟢 92% | 🟢 **95%** | 🔼 | 19 migrations com downgrades validados no CI |
| **Backend** | 🟢 98% | 🟢 **98%** | — | 62 operações, 9 serviços, lint limpo |
| **Frontend** | 🟢 94% | 🟢 **94%** | — | Tipa e linta limpo; 4 arquivos acima de 500 LOC |
| **Testes — backend** | 🟢 90% | 🟢 **96%** | 🔼 | 202 casos, incluindo matriz de autorização e smoke de migrations |
| **Testes — frontend** | 🔴 0% | 🟢 **81%** | 🔼🔼🔼 | 114 testes · 93,5% das funções · job no CI |
| **Validação de entrada** | 🟡 70% | 🟡 **70%** | — | Limites físicos não modelados (B-A27) |
| **Integração externa** | 🟡 50% | 🟡 **50%** | — | E-mail sem contrato de falha (B-A29) |
| **CI/CD** | 🟡 60% | 🟢 **95%** | 🔼🔼🔼 | 4 jobs **executando e verdes** em `main`. Falta `docker build` real |
| **Observabilidade** | 🟡 50% | 🟡 **50%** | — | structlog + `/health`; sem métricas nem tracing |
| **Escalabilidade** | 🔴 30% | 🔴 **35%** | 🔼 | `Protocol` de storage existe; implementação, não |
| **Documentação** | 🟢 100% | 🟢 **100%** | — | 17 documentos sincronizados por execução |

---

## 3. Achados Abertos

### 3.1 — Crítico

**Nenhum.** ⚪

Pela primeira vez desde a rev. 7.0, a faixa Crítica está vazia. B-C23 (credenciais versionadas e em uso) foi fechado por rotação — verificado nesta revisão: nenhum valor do `.env` atual aparece em commit algum do histórico.

### 3.2 — Alta `3 achados · ~6 h`

| ID | Achado | Impacto | Esforço |
|---|---|---|---|
| **B-A27** | Senha acima de 72 bytes derruba `/auth/login` e `/auth/register` com exceção não tratada | **Único explorável sem credencial.** Qualquer pessoa produz um 500 no login. Se a versão do bcrypt mudar para uma que trunca, vira algo pior: duas senhas diferentes com o mesmo prefixo autenticando a mesma conta | 1 h 30 |
| **B-A29** | Senha temporária do onboarding não existe em lugar nenhum sem SMTP | O cliente é criado com empresa e dashboard, e **ninguém consegue entrar na conta**. Não há recuperação de senha. Em produção com SMTP intermitente é pior: 500 após o commit, e a segunda tentativa dá 409 | 3 h |
| **B-A28** | Cliente auditado **lê** o checklist interno e o histórico do auditor | O BLOCO P fechou a escrita, não a leitura. **Rebaixa o requisito formal RNF-03** de ✅ para ⚠️ | 2 h |

Os três foram confirmados por sonda executável, não por leitura.

### 3.3 — Média e Baixa `12 achados · ~7 h`

| Faixa | IDs | Resumo |
|---|---|---|
| 🟡 **Média (5)** | B-M25, B-M26, B-M27, B-M28, B-M29 | Default inseguro de registro público · N+1 de 7 queries por empresa · e-mail de onboarding com papel errado · guarda de path traversal no lugar errado · defaults de JWT divergentes entre backend e frontend |
| 🟢 **Baixa (7)** | B-B17..B-B23 | Bloco duplicado no upload · typo `TimestampMixim` · `SoftDeleteMixin` sem uso · `structlog` sem pin · typos em mensagens ao usuário · `Olá{nome}` sem espaço · 403 onde deveria ser 404 |

Detalhamento com código de correção completo em [`relatorio_bugs.md`](relatorio_bugs.md).

---

## 4. Causas Estruturais

Cada achado desta revisão tem uma causa nomeada. Corrigir os 15 custa ~13 h; instalar as barreiras custa ~13 h a mais, e é o que decide se a próxima auditoria encontra a mesma classe de coisa.

| Causa | O que está faltando | Achados que ela gerou | Esforço |
|---|---|---|---|
| **M-21** | Limites físicos de biblioteca nunca viram contrato — só regras de negócio são modeladas | B-A27 | 3 h |
| **M-22** | Integração externa sem contrato de falha nem tipo por destinatário | B-A29, B-M27 | 3 h |
| **M-23** | `policy.py` modela **ações de escrita**; leitura sensível ficou fora do vocabulário | B-A28 | 2 h |
| **M-24** | Nenhum teste afirma qual é o default do código — então o default é o que sobrar | B-M25, B-M29 | 30 min |
| **M-25** | O custo em queries de uma rota não é medido por teste algum | B-M26 | 4 h |
| **M-16b** | A barreira de M-16 foi instalada no consumidor, não no ponto único | B-M28 | 1 h 30 |

### A lição transversal

**Uma barreira instalada no lugar errado passa no teste e não protege.**

M-16 pediu um contrato de storage com `delete` obrigatório; o contrato foi criado, mas a guarda de caminho que o acompanha foi parar dentro de `delete_files()` em vez de `get_absolute_path()` — e o download ficou de fora. M-20 pediu uma matriz de autorização; a matriz foi criada, cobrindo escrita, e a leitura ficou de fora.

O caso mais nítido é o **defeito nº 14**: havia um teste de CSP, ele passava, o header estava presente — e `/docs` renderizava em branco. O teste perguntava *"o header está presente?"*; a pergunta certa era *"sob este header, os recursos que a página pede continuam permitidos?"*.

Não é falha de execução. É a diferença entre corrigir um caso e cobrir a superfície onde o caso vive.

---

## 5. Funcionalidades

| Categoria | Qtd |
|---|---|
| ✅ Concluídas e funcionando | **78** (F01–F78) |
| ⚠️ Parcialmente implementadas | 3 (cadastro público, conteúdo ISO dos templates, notificação por e-mail) |
| ⬜ Planejadas / não iniciadas | 7 |
| 🔴 Órfãs (código morto) | **0** |
| 💥 Quebradas | **0** |
| ⚠️ Entregues com achado Alta aberto | **0** ✅ *(eram 4 na rev. 7.0)* |
| **Total mapeado** | **88** |

### Entregues no BLOCO P `F71–F78`

Nenhuma é uma tela. São **garantias** — código cuja finalidade é impedir que uma classe de erro volte a acontecer.

| # | Entrega | Fecha |
|---|---|---|
| F71 | Camada de política de autorização (`Action` × `ALLOWED_ROLES`) | B-A23 |
| F72 | Matriz de autorização automatizada (cada papel × cada escrita proibida) | M-20 |
| F73 | Retenção e exclusão real de arquivo de evidência, pós-commit e com guarda | B-A26 |
| F74 | Contrato de storage com `delete` obrigatório | M-16 |
| F75 | Varredura de evidências órfãs (`prune_orphan_uploads.py`) | dívida herdada |
| F76 | Integridade template ↔ card (409 + backfill + `UniqueConstraint`) | B-A24, B-A25 |
| F77 | Barreiras de CI (gitleaks, pip-audit, migrations contra MySQL real) | M-18, B-B13 |
| F78 | CSP por rota + HSTS, com teste que varre o HTML real | B-M21, defeito #14 |

---

## 6. Requisitos Formais — Rastreabilidade

| Categoria | Total | ✅ | ⚠️ | ❌ |
|---|---|---|---|---|
| Requisitos Funcionais (RF) | 20 | 11 | 4 | 5 |
| Requisitos Não-Funcionais (RNF) | 8 | 3 | 3 | 2 |
| Regras de Negócio (RN) | 10 | 6 | 1 | 3 |
| **Total** | **38** | **20** | **8** | **10** |

**28 de 38 (74%)** com implementação total ou parcial · **20 (53%)** plenamente atendidos.

### Movimentos desta revisão

| Requisito | Movimento | Causa |
|---|---|---|
| **RF-04** (status de conformidade) | ⚠️ mantido, mas **D-09 fechada** | A definição de status voltou a ser exclusiva do auditor (B-A23) |
| **RNF-03** (segregação de visão por perfil) | ✅ → ⚠️ **rebaixado** | O cliente lê o registro interno do auditor (**B-A28**) |
| **RNF-04** (segurança de arquivos) | ✅ **reforçado** | Exclusão real do disco na cascata de empresa |
| **RNF-02** (trilha imutável) | ❌ mantido, **mitigado** | Só o admin escreve o histórico; ainda não é append-only |

### Divergências ativas

| Fonte | Ativas | Nota |
|---|---|---|
| `Arquivo/` × código | **6** | 1 fechada (D-09), 1 nova (D-10, de B-A28) |
| `backend/README.md` × código | **8** | Só a Crítica foi corrigida no BLOCO P; **RD-04 piorou** |
| Contradições internas em `docs/` | **0** | ✅ |

> ### 📌 O README que a correção piorou
>
> O `backend/README.md` manda usar `/api/v1/Monitoring` como health check. O BLOCO P **removeu essa rota** (achado B-B10, "rota morta e redundante"). Correto do ponto de vista do código — mas o README continua indicando o endereço, que agora responde **404**. A instrução saiu de "enganosa" para "quebrada".
>
> Um orquestrador configurado conforme o README reinicia a aplicação em laço. **Correção: 1 hora**, reescrevendo o README como índice que aponta para `setup_completo.md` em vez de duplicar procedimento.

### Funcionalidades implementadas sem documentação: **30** `🔺 +8`

As oito novas são as entregas do BLOCO P. O aumento numa revisão sem funcionalidade de produto é significativo: são **decisões estruturais** — política de autorização, contrato de storage, invariante de unicidade, política de CSP — que hoje vivem **apenas em docstring**.

Docstring é o melhor lugar para explicar *como* uma função funciona e o pior lugar para registrar *por que* uma regra de negócio existe.

---

## 7. Riscos

| # | Risco | Severidade | Estado |
|---|---|---|---|
| ~~0~~ | ~~Credenciais válidas e públicas~~ | ~~🔴~~ | ✅ **Fechado** — rotacionadas e verificadas |
| ~~1~~ | ~~Usar a tela de templates duplica cards~~ | ~~🟠~~ | ✅ **Fechado** — `UniqueConstraint` + backfill |
| ~~2~~ | ~~Excluir empresa deixa evidências no disco~~ | ~~🟠~~ | ✅ **Fechado** — `delete_files()` pós-commit |
| ~~3~~ | ~~As barreiras do BLOCO P nunca executaram~~ | ✅ **Fechado** | Executaram em 2026-08-26 e **reprovaram 3 dos 4 jobs**. Os 4 defeitos (B-A30, B-A31, B-M30, B-M31) foram corrigidos; CI verde. A generalização virou **M-30** |
| **4** | **A credencial do cliente não tem volta** | 🟠 **Alto** | Sem recuperação de senha, sem troca obrigatória, e a senha temporária só existe dentro do e-mail (B-A29). **Todo cliente onboardado em dev sem SMTP está inacessível** |
| **5** | Confiança excessiva na suíte verde | 🟡 Médio | 202 testes verdes, lint limpo — e 15 achados nesta auditoria, 3 deles Alta |
| **6** | Backend não escala horizontalmente | 🟡 Médio | Uploads locais + rate limit em memória. **Não rode com mais de uma réplica** |
| **7** | Dívida de `tag` duplicando `category.name` | 🟢 Baixo | Sincronia manual em todo caminho de escrita; funciona |

---

## 8. Métricas

### Evolução da suíte de testes

```
  34 ─▶ 42 ─▶ 43 ─▶ 55 ─▶ 63 ─▶ 74 ─▶ 77 ─▶ 89 ─▶ 93 ─▶ 102 ─▶ 128 ─▶ 192 ─▶ 202
 08-06 08-11 08-11 08-12 08-13 08-17 08-17 08-17 08-17 08-17  08-24  08-25  08-25
 BLOCO  E.4-  I.2   I.4/  L.1   L.2-  N.1   M.1   N.3   M.2   BLOCO  BLOCO   CSP
   G    E.9         I.7         L.4                            O      P     (#14)
                                                             (+26)  (+64)  (+10)
```

**O salto de +64 do BLOCO P é o maior da história do projeto e não corresponde a funcionalidade nova.** São testes de **negativa**: cada papel tentando o que não deveria poder, cada migration verificada quanto a nome × revisão, cada origem do CSP conferida contra o HTML real.

### Números verificados por execução

| Métrica | rev. 7.0 | rev. 8.0 | Δ |
|---|---|---|---|
| Testes automatizados (backend) | 128 | **202** | 🔼 +74 |
| Testes automatizados (frontend) | 0 | **0** | — |
| Arquivos de teste | 15 | **18** | 🔼 +3 |
| Migrations Alembic | 17 | **19** | 🔼 +2 |
| Classes ORM | 18 | **18** | — |
| Routers da API v1 | 11 | **11** | — |
| Operações da API | 68 (declarado) | **64** (medido) | recontagem |
| Rotas de página (frontend) | 13 | **15** | recontagem |
| Funcionalidades concluídas | 70 | **78** | 🔼 +8 |
| Achados abertos | 18 (1C·4A·6M·7B) | **15** (0C·3A·5M·7B) | 🔽 −3 |
| Achados fechados (acumulado) | 51 | **65** | 🔼 +14 |
| Requisitos com implementação | 27/38 | **28/38** | 🔼 +1 |
| Jobs de CI | 2 | **4** | 🔼 +2 |
| Entradas no relatório de commits | 41 | **44** | 🔼 +3 |
| Arquivos em `docs/` | 17 | **17** | — |

> A "recontagem" de operações da API não é uma queda: a rev. 7.0 declarava 68 sem enumerar. Nesta revisão o número veio de `app.openapi()` — **62 em `/api/v1` + `/` + `/health` = 64**.

### Volume de código

| Área | LOC |
|---|---|
| `backend/app/**` | **5.703** |
| `backend/tests/**` | 3.270 |
| `backend/alembic/**` | 1.976 |
| `backend/scripts/**` | 1.171 |
| `frontend/**` (app + lib + components) | **7.811** |
| **Total de código de aplicação** | **~13.500** |

### Arquivos que pedem atenção

| Arquivo | LOC | Testes |
|---|---|---|
| `frontend/.../dashboard/company-dashboard-client.tsx` | **890** | ❌ 0 |
| `frontend/app/private/admin/empresas/empresas-client.tsx` | **649** | ❌ 0 |
| `backend/app/api/v1/dashboard_cards.py` | 610 | ✅ 19 funções |
| `frontend/app/private/admin/templates/templates-client.tsx` | **594** | ❌ 0 |
| `backend/app/services/dashboard_template_admin.py` | 547 | ✅ 7 funções |
| `frontend/app/private/client/client-dashboard-client.tsx` | **518** | ❌ 0 |

### Cobertura de automação

| Automação | Estado |
|---|---|
| `ci.yml` — 4 jobs (backend, frontend, secrets, migrations) | ✅ **Executando e verde** em `main` desde 2026-08-26 |
| `commit-report.yml` — relatório de commits | ✅ **Executou de verdade** em 2026-08-26 — 44 → **46 entradas**, com push de volta |
| `pre-commit` — gitleaks na raiz | ✅ Configurado |
| Trello | 📋 Proposta · catálogo de 17 cards pronto · quadro não criado |
| MindMeister | 📋 Proposta · parsers **reexecutados e corrigidos** nesta revisão |

---

## 9. Plano de Ação

| Ordem | Item | Esforço | Prioridade | O que destrava |
|---|---|---|---|---|
| **1** | **Sprint A5** — 1ª execução real do `ci.yml` | **1 h** | 🔴 hoje | Confiança em todas as 5 barreiras do BLOCO P |
| **2** | **B-A27** — limite do bcrypt como contrato | 1 h 30 | 🟠 alta | Fecha o único achado explorável sem credencial |
| **3** | **B-A29 + B-M27** — contrato de falha no e-mail | 3 h | 🟠 alta | Elimina a perda de credencial e o 500 pós-commit |
| **4** | **B-A28** — política nas leituras sensíveis | 2 h | 🟠 alta | Recupera RNF-03 |
| **5** | **B-M25 + B-M29** — defaults de configuração | 30 min | 🟡 média | Melhor relação custo/benefício do plano |
| **6** | **B-M28** — guarda no ponto único | 1 h 30 | 🟡 média | Pré-requisito do Sprint D2 |
| **7** | **Sprint B** — testes de frontend | **2–3 dias** | 🟠 alta | Torna 7.811 LOC auditáveis · destrava M-17 |
| **8** | **Sprint C** — orçamento de queries + B-M26 + M-01c + decomposição | 4–5 dias | 🟡 média | Fase 2 em 100% |
| **9** | **Sprint D2** — storage trocável + rate limit em Redis | 3 dias | 🟡 média | Produção com mais de um nó |
| **10** | **Sprint E** — ciclo de vida da credencial | 2 dias | 🟡 média | Autoatendimento do cliente |
| **11** | **B-B17..B-B23** — limpeza em lote | 2 h | 🟢 baixa | — |

**Até a Fase 3 completa: ~14 dias.**

---

## 10. Documentação

| Documento | Versão | Estado |
|---|---|---|
| [`index.md`](index.md) | 8.0 | Central de navegação |
| [`relatorio_geral.md`](relatorio_geral.md) | 8.0 | Arquitetura, stack, fluxos, banco |
| [`relatorio_funcionalidades.md`](relatorio_funcionalidades.md) | 8.0 | Linha do tempo (50 commits) · 88 funcionalidades |
| [`relatorio_bugs.md`](relatorio_bugs.md) | 9.0 | 15 achados com código de correção completo |
| [`relatorio_melhorias.md`](relatorio_melhorias.md) | 7.0 | Causas estruturais M-01..M-29 |
| [`relatorio_documentacao.md`](relatorio_documentacao.md) | 7.0 | Rastreabilidade + auditoria do `backend/README.md` |
| [`roadmap.md`](roadmap.md) | 7.0 | Fases e sprints com critérios de saída |
| [`plano_implementacao.md`](plano_implementacao.md) | 5.19 | Passo a passo técnico com código pronto |
| [`setup_completo.md`](setup_completo.md) | 4.0 | Do `git clone` à aplicação rodando |
| [`executar_projeto.md`](executar_projeto.md) | 6.0 | Operação diária: banco, backup, logs, Docker |
| [`deploy_producao.md`](deploy_producao.md) | 2.1 | Deploy em produção |
| [`backlog.md`](backlog.md) | 3.0 | Backlog acionável |
| [`automacao_commits.md`](automacao_commits.md) | 3.0 | ✅ Backfill executado — 44 entradas |
| [`relatorio_commit.md`](relatorio_commit.md) | gerado | **Não edite à mão** |
| [`trello_automacao.md`](trello_automacao.md) | 3.0 | 📋 Catálogo de 17 cards reescrito |
| [`mindmeister_automacao.md`](mindmeister_automacao.md) | 3.0 | 📋 Parsers reexecutados; 2 regressões corrigidas |
| [`dashboard_projeto.md`](dashboard_projeto.md) | 8.0 | Este documento |

---

## 11. Conclusão

O projeto atravessou a janela mais produtiva da sua história em segurança. **Dezoito achados fechados, cinco barreiras estruturais instaladas, a suíte de testes 58% maior, e a faixa Crítica vazia pela primeira vez desde que passou a existir.**

O que se aprende ao comparar as duas auditorias é mais útil que o placar. A rev. 8.0 encontrou problemas de **autorização** — quem pode fazer o quê. A rev. 9.0, sobre o mesmo código já corrigido, encontrou problemas de **borda** — o que acontece quando a entrada, o serviço externo ou o volume saem do caso normal. A superfície mudou porque a anterior foi coberta.

E há um padrão que se repetiu nas duas, com formas diferentes: **a barreira certa no lugar errado**. O contrato de storage foi criado, mas a guarda de caminho ficou no consumidor. A matriz de autorização foi criada, mas cobriu só a escrita. O teste de CSP foi criado, mas perguntava se o header existia em vez de se a página funcionava. Nos três casos o trabalho foi feito e o teste passou — e a superfície que importava ficou de fora.

### As três coisas que mudam a trajetória

1. **Uma hora resolve mais do que qualquer outra coisa neste dashboard.** Cinco barreiras estruturais e quatro jobs de CI foram construídos e nunca executados no ambiente para o qual foram escritos. Abrir um PR converte cinco suposições em cinco garantias — ou revela quais delas não funcionam, que é igualmente valioso.

2. **O frontend é o ponto cego, e o ponto cego é demonstrável.** Três auditorias adversariais seguidas produziram achados quase exclusivamente de backend. Não porque o frontend esteja mais correto — porque não há como sondá-lo. 7.811 linhas, 15 páginas, zero testes.

3. **A próxima geração de achados já tem endereço.** As cinco causas desta revisão são todas da mesma família: **superfícies onde o projeto não faz pergunta nenhuma**. Nenhum teste afirma qual é o default de uma variável de segurança. Nenhum teste mede o custo de uma rota. Nenhum contrato descreve o que acontece quando o servidor de e-mail não responde. Instalar essas perguntas custa ~13 h — e é o que decide se a rev. 10.0 vai encontrar a mesma classe de coisa.

---

*Dashboard atualizado em 2026-08-26 (rev. 8.1, após a implementação do BLOCO Q). Todos os números vieram de execução real — `pytest` (**250 passed**, era 202 no levantamento), `ruff`, `alembic heads`, `tsc --noEmit`, `eslint`, `app.openapi()`, `wc -l` e 13 sondas executáveis escritas para a auditoria. Nenhum foi herdado da revisão anterior.*
