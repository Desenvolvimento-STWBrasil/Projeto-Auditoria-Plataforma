# PRD — Quadro Kanban de Colunas e Cards (Board estilo Trello)

| Campo | Valor |
|---|---|
| **Documento** | Product Requirements Document (PRD) |
| **Funcionalidade** | Quadro de **colunas** e **cards** arrastáveis no dashboard da empresa |
| **Data** | 2026-08-27 |
| **Versão** | 1.0 |
| **Autor** | Tech Lead / Eng. Sênior |
| **Branch base** | `fix/audit-repository-refactor-and-regressions` · HEAD `754ed58` |
| **Head de migrations** | `b7c02e91d4a5` (`unique_card_origin`) |
| **Fonte de requisito** | `trello exemplo para ser implementado.json` — export do quadro *"[MODELO] Due Diligence - Celcoin <> STWBrasil - Pix Indireto"* |
| **Documentos irmãos** | [`backlog.md`](backlog.md) · [`roadmap.md`](roadmap.md) · [`plano_implementacao.md`](plano_implementacao.md) · [`relatorio_geral.md`](relatorio_geral.md) |

---

## 1. Visão Geral da Funcionalidade

### 1.1 O problema

A plataforma **já implementa** o domínio de cards de auditoria (`DashboardCard`), com status de
conformidade, checklist, histórico, chat bilateral e notas internas. O que ela **não** tem é a
dimensão espacial que o Trello dá ao mesmo domínio:

1. **Não existe coluna.** Hoje o agrupamento visual é derivado de `DashboardCardCategory` — um
   vocabulário **global**, compartilhado por todas as empresas. O quadro-modelo real da STW tem
   **31 listas nomeadas por norma e por controle** (`Controle 5 - Controles Organizacionais`,
   `Controle 11.0 Direitos dos Titulares`, `RESOLUÇÃO 4893`, …). Um cliente candidato a Pix
   Indireto pela Celcoin tem colunas que um cliente só-ISO não tem. **Um vocabulário global não
   consegue expressar "este quadro tem estas colunas".**
2. **Não existe ordenação manual.** `sort_order` é `Integer`, atribuído por `max()+1` na criação
   e nunca alterado depois. Não há endpoint de *move*, não há arrasto, não há reordenação.
3. **Não existe descrição de card.** `DashboardTemplateCard.description` existe, mas
   `DashboardCard` **não tem a coluna** — e `apply_template_to_company()` copia
   `title`/`tag`/`category_id` e **descarta silenciosamente a descrição**. No export real,
   **146 dos 213 cards abertos (68 %) têm descrição**, e ela é o texto normativo do controle
   (`**Controle** — Convém que a política de segurança da informação…`). Hoje esse conteúdo
   simplesmente não teria onde existir na plataforma.
4. **Não existe etiqueta.** **178 dos 213 cards (84 %)** carregam etiqueta de criticidade
   (`Item Critico`, `Alta/Média/Baixa Criticidade`). O `DashboardCardStatus` responde *"está
   conforme?"*, não *"quão crítico é?"* — são eixos ortogonais.

### 1.2 O que será entregue

Um **quadro (board) por empresa**, renderizado como colunas horizontais roláveis, onde o
**admin** cria/renomeia/reordena/arquiva colunas, arrasta cards entre colunas e dentro delas, e
etiqueta cards por criticidade. O **cliente** vê o mesmo quadro em modo leitura, com a mesma
disposição que o auditor montou — e continua podendo abrir o card, ler a descrição e conversar
no chat.

O quadro nasce de um **template**, que agora carrega colunas além de cards. O template de
referência é gerado a partir do próprio export do Trello por um **importador one-shot**.

### 1.3 Personas e histórias de usuário

| # | Como… | Quero… | Para… |
|---|---|---|---|
| U1 | Admin (auditor) | criar, renomear, reordenar e arquivar colunas no quadro de uma empresa | espelhar o escopo normativo daquele cliente (ISO, LGPD, BCB, Pix) |
| U2 | Admin | arrastar um card de uma coluna para outra e posicioná-lo dentro dela | refletir o andamento real da due diligence |
| U3 | Admin | escrever/ler a descrição normativa do card | ter o texto do controle junto da evidência, sem consultar outro sistema |
| U4 | Admin | etiquetar cards por criticidade | priorizar o que o cliente precisa tratar primeiro |
| U5 | Admin | montar um template com colunas e aplicá-lo a uma empresa nova | não remontar 31 colunas e 213 cards a cada cliente |
| U6 | Cliente (`user` / `sub-user`) | ver o quadro com as colunas e cards na ordem que o auditor montou | acompanhar o progresso sem depender de reunião |
| U7 | Cliente | abrir um card e ler a descrição do controle | saber exatamente o que precisa entregar |

### 1.4 O que NÃO precisa ser construído (já existe e será reaproveitado)

| Conceito Trello | Já existe na base | Arquivo |
|---|---|---|
| Board | `Dashboard` (1:1 com `Company`) | `backend/app/models/company_dashboard.py` |
| Card | `DashboardCard` | idem |
| Comentário | `DashboardCardMessage` (QUESTION/ANSWER) | idem |
| Checklist | `DashboardCardchecklistItem` | idem |
| Activity / log | `DashboardCardHistoryEntry` | idem |
| Arquivar card | `DashboardCard.hidden` | idem |
| Board template | `DashboardTemplate` + `DashboardTemplateCard` | idem |
| Aplicar template (idempotente) | `apply_template_to_company()` | `backend/app/services/dashboard_template_admin.py` |
| Ação em lote | `bulk_update_cards()` + `PATCH …/cards/bulk` | idem · `api/v1/dashboard_cards.py` |
| Busca por título / código | `list_cards_by_company(search=…)` | `api/v1/dashboard_cards.py` |
| Permissão por papel | `core/policy.py` (`Action` / `ALLOWED_ROLES`) | `backend/app/core/policy.py` |
| Escopo por empresa (404, não 403) | `get_company_with_access()` | `backend/app/core/access.py` |

> **Consequência de escopo:** esta funcionalidade é **aditiva**. Não reescreve o domínio de
> cards — acrescenta a ele *coluna*, *posição*, *descrição* e *etiqueta*, e troca a camada de
> renderização de lista agrupada para quadro arrastável.

---

## 2. Análise do Export do Trello (dados reais, não hipóteses)

Números extraídos de `trello exemplo para ser implementado.json` (1,19 MB):

| Métrica | Valor | Consequência de projeto |
|---|---|---|
| Listas | **31** (25 abertas, 6 arquivadas) | Coluna precisa de flag de arquivamento |
| Listas separadoras (nome termina em `>>`, 0 cards) | **3** (`ISO 27001:2022 >>`, `LGPD >>`, `Banco Central (BCB) >>`) | Coluna precisa de um tipo "seção" |
| Cards | **214** (213 abertos, 1 arquivado) | Volume real por quadro ≈ 215 — virtualização **não** é obrigatória em v1 |
| Cards com descrição | **146 (68 %)** | `DashboardCard.description` é **obrigatório** no escopo |
| Cards com etiqueta | **178 (84 %)** | Etiquetas são **obrigatórias** no escopo |
| Cards com título prefixado por código (`5.1 `, `11.0 `) | **144 (68 %)** | Alimenta `control_code` no importador |
| Etiquetas definidas no quadro | **11** | Ver §2.1 |
| Cards com `due` | **0** | Prazo → **v2**, não v1 |
| Cards com membro atribuído | **0** | Responsável → **v2**, não v1 |
| Cards com anexo | **0** | Anexo → **fora de escopo** (ver `Evidence`, D-4) |
| Cards com checklist | **0** | Checklist já existe; nada a importar |
| Cards com comentário | **0** | Chat já existe; nada a importar |
| Campos customizados | **0** | Fora de escopo |
| `pos` (ordenação Trello) | float, `4096` → `2 359 295`, degraus de 65 535 | Confirma o padrão de **índice esparso** (§4.2) |

### 2.1 As 11 etiquetas do quadro e o destino de cada uma

| Etiqueta Trello | Cor | Cards | Destino |
|---|---|---|---|
| `Item Critico` | `red_dark` | 63 | ✅ Importar |
| `Alta Criticidade` | `orange` | 61 | ✅ Importar |
| `Baixa Criticidade` | `blue` | 36 | ✅ Importar |
| `Média Criticidade` | `yellow_light` | 17 | ✅ Importar |
| `Check-list` | `purple` | 1 | ✅ Importar (uso residual) |
| `Aguardando empresa` | `blue_light` | 0 | ✅ Importar — estado de fluxo legítimo |
| `Final do projeto` | `blue_dark` | 0 | ✅ Importar |
| `Inserir doc atualizado no final do projeto` | `yellow_dark` | 0 | ✅ Importar |
| `Não Aplicável` | `black_dark` | 0 | ⚠️ **Decisão D-2** — é status, não etiqueta |
| `Concluído com evidência` | `green` | 0 | ❌ **Não importar** — redundante com `CONFORME` |
| `Entregue - Inove Educação` | `pink_dark` | 0 | ❌ **Não importar** — específico de um cliente |

> **Regra de ouro, herdada de B-A23:** etiqueta **nunca** determina conformidade.
> `DashboardCardStatus` continua sendo a única declaração do auditor sobre o auditado, e
> continua sendo `admin`-only. Uma etiqueta `Concluído com evidência` coexistindo com um status
> `EM_ANALISE` criaria duas fontes de verdade para a mesma pergunta — por isso ela fica fora do
> import.

---

## 3. Decisões de Modelagem

### D-1 — Coluna é **por quadro**; categoria continua **global** `RESOLVIDA`

Esta é a decisão estruturante do PRD, e a leitura ingênua é a errada.

| | `DashboardColumn` (**novo**) | `DashboardCardCategory` (**existente**) |
|---|---|---|
| Escopo | Por `dashboard_id` (uma empresa) | Global (todas as empresas) |
| Responde | *"Onde este card está no quadro?"* | *"Que tipo de card é este?"* |
| Análogo Trello | **List** | **Label** / taxonomia |
| Quem cria | Admin, no quadro da empresa (ou o template) | Admin, no CRUD global |
| Exemplo real | `Controle 8 - Controles tecnológicos` | `Compliance` |
| Ordenação | Sim, arrastável | `sort_order` fixo |

**Por que não promover `DashboardCardCategory` a coluna (alternativa rejeitada):**

1. `name` é `unique=True` **global**. Duas empresas não poderiam ter, cada uma, a sua coluna
   `Controle 5` — e é exatamente isso que o quadro-modelo exige.
2. `bulk_update_cards(operation="set_category")` e o filtro por categoria são operações
   **transversais a empresas**; virar por-quadro esvaziaria as entregas O.3/O.4 inteiras.
3. `delete_category()` já bloqueia exclusão com `CategoryInUseError` contando cards de **todas**
   as empresas. Com escopo por quadro essa contagem deixa de fazer sentido.
4. As categorias semeadas pela migration `4f2b8e6a91d3` são `Financeiro / Operacional / Vendas /
   Compliance` — vocabulário de classificação, não de fluxo.

**Consequência:** `DashboardCard` passa a ter **`column_id` e `category_id`**, e a UI de quadro
agrupa por **coluna**. A categoria deixa de ser o eixo de agrupamento visual e vira filtro
lateral — sem perda de dado nem de endpoint.

### D-2 — `Não Aplicável` é status ou etiqueta? `EM ABERTO`

Um controle "não aplicável" não é `CONFORME` nem `NAOCONFORME`, e deixá-lo em `EM_ANALISE`
para sempre polui os 4 KPIs de `get_dashboard_status_summary`.

| Opção | Custo | Efeito |
|---|---|---|
| **(a)** 5º valor `NAO_APLICAVEL` no enum `DashboardCardStatus` | Migration de `ENUM` MySQL + `control-status.ts` + `DashboardStatusSummary` + os 3 dashboards + testes | Correto semanticamente; KPIs honestos |
| **(b)** Etiqueta comum | Zero custo extra | KPI continua contando não-aplicáveis como trabalho em aberto |

**Recomendação:** (b) em v1 (não bloqueia a entrega), (a) como item de backlog imediatamente a
seguir — o precedente existe e está documentado: a migration `c2a7e6f1b8d3` já acrescentou
`NAOCONFORME` a `audit_control_status` exatamente assim.

### D-3 — Ordenação: índice fracionário em `String`, não `Integer` reindexado `RESOLVIDA`

Ver §4.2. **`position: String(64)`**, índice fracionário base-62, com `sort_order` mantido como
campo histórico (mesma política conservadora que a migration `4f2b8e6a91d3` aplicou a `tag`).

### D-4 — Anexos ficam fora de v1 `RESOLVIDA`

`Evidence` existe, mas é `FK → audit_controls.id`. Ligar anexo a card exigiria uma segunda FK
opcional (`evidences.dashboard_card_id`) e revisar `storage.py`, `test_storage_path_guard.py` e
o download autenticado do frontend. O export tem **0 anexos** — não há requisito comprovado.
**Backlog.**

### D-5 — O quadro é lido por um endpoint só `RESOLVIDA`

Hoje o cliente React monta o agrupamento em memória (`groups: CardGroup[]` em
`company-dashboard-client.tsx`). Com colunas persistidas, a montagem passa a ser
responsabilidade do servidor: **`GET /dashboard/companies/{id}/board`** devolve o quadro
pronto. Isso mantém o custo em queries constante e sob teste (§7, `test_query_budget.py`), e
evita repetir a lógica de ordenação em dois lugares.

---

## 4. Arquitetura Proposta

### 4.1 Modelo de dados

#### 4.1.1 Tabelas novas

```
dashboard_columns                       (coluna de UM quadro)
├── id                          PK
├── dashboard_id                FK dashboards.id  ON DELETE CASCADE            [index]
├── name                        VARCHAR(160)  NOT NULL
├── kind                        ENUM('COLUMN','SECTION') NOT NULL DEFAULT 'COLUMN'
├── position                    VARCHAR(64)   NOT NULL      -- índice fracionário
├── hidden                      BOOLEAN       NOT NULL DEFAULT FALSE   -- "closed" do Trello
├── wip_limit                   INTEGER       NULL          -- v2; coluna criada já em v1
├── origin_template_column_id   FK dashboard_template_columns.id ON DELETE SET NULL [index]
├── created_at                  DATETIME(tz)  DEFAULT now()
└── UNIQUE (dashboard_id, origin_template_column_id)   -- idempotência do apply-template

dashboard_template_columns              (coluna de UM template)
├── id                          PK
├── template_id                 FK dashboard_templates.id ON DELETE CASCADE    [index]
├── name                        VARCHAR(160)  NOT NULL
├── kind                        ENUM('COLUMN','SECTION') NOT NULL DEFAULT 'COLUMN'
├── position                    VARCHAR(64)   NOT NULL
└── UNIQUE (template_id, name)

dashboard_labels                        (vocabulário global de etiquetas)
├── id                          PK
├── name                        VARCHAR(60)   NOT NULL UNIQUE
├── color                       VARCHAR(20)   NOT NULL DEFAULT '#788c5d'
└── sort_order                  INTEGER       NOT NULL DEFAULT 0

dashboard_card_labels                   (M:N card ↔ etiqueta)
├── card_id                     FK dashboard_cards.id  ON DELETE CASCADE
├── label_id                    FK dashboard_labels.id ON DELETE CASCADE
└── PRIMARY KEY (card_id, label_id)
```

> **`UNIQUE (dashboard_id, origin_template_column_id)`** é a mesma invariante que
> `uq_dashboard_card_origin_per_dashboard` (migration `b7c02e91d4a5`) instalou para cards, pela
> mesma razão: é ela que sustenta a idempotência de `apply_template_to_company`. Em MySQL,
> `NULL` não participa da unicidade — colunas criadas à mão pelo admin seguem livres.

#### 4.1.2 Colunas acrescentadas a tabelas existentes

| Tabela | Coluna | Tipo | Nulo | Justificativa |
|---|---|---|---|---|
| `dashboard_cards` | `column_id` | FK `dashboard_columns.id` `ON DELETE SET NULL`, index | ✅ | Card órfão cai no bucket "Sem coluna" em vez de sumir — mesma escolha já feita para `category_id` |
| `dashboard_cards` | `position` | `VARCHAR(64)` | ❌ | Ordenação dentro da coluna |
| `dashboard_cards` | `description` | `TEXT` | ✅ | 68 % dos cards reais têm; hoje se perde no `apply_template` |
| `dashboard_cards` | `due_date` | `DATETIME(tz)` | ✅ | Coluna criada em v1, UI só em v2 — evita uma 2ª migration |
| `dashboard_template_cards` | `template_column_id` | FK `dashboard_template_columns.id` `ON DELETE SET NULL`, index | ✅ | Diz em que coluna o card nasce |
| `dashboard_template_cards` | `position` | `VARCHAR(64)` | ❌ | Idem |

#### 4.1.3 Índices

```sql
CREATE INDEX ix_dashboard_columns_board_position ON dashboard_columns (dashboard_id, position);
CREATE INDEX ix_dashboard_cards_column_position  ON dashboard_cards   (column_id, position);
```

> O segundo índice é o que torna o carregamento do quadro barato: a listagem lê
> `WHERE dashboard_id = ? ORDER BY column_id, position` e o índice cobre o `ORDER BY`,
> eliminando `filesort` com 215 cards. Segue o padrão já estabelecido pelas migrations
> `56d322bbd83a` / `d5c4d7cd6687` / `eafa65e9df05`.

#### 4.1.4 Migration

Arquivo único: `backend/alembic/versions/<rev>_add_dashboard_columns_and_labels.py`, com
`down_revision = "b7c02e91d4a5"`.

Estratégia de dados — **nenhum quadro existente pode ficar vazio depois do upgrade**:

1. `CREATE TABLE` das 4 tabelas novas + `ADD COLUMN` das 6 colunas.
2. **Backfill de colunas:** para cada `dashboards.id`, criar uma `dashboard_columns` por
   categoria **efetivamente usada** por cards daquele quadro (`SELECT DISTINCT category_id`),
   com `name` = nome da categoria, na ordem de `dashboard_card_categories.sort_order`. Cards
   com `category_id IS NULL` vão para uma coluna `Sem categoria`.
3. **Backfill de `position`:** gerar chaves fracionárias na ordem `sort_order ASC, id ASC` —
   preserva exatamente a ordem que o usuário vê hoje.
4. **Backfill de `description`:**
   `UPDATE dashboard_cards c JOIN dashboard_template_cards t ON c.origin_template_card_id = t.id
   SET c.description = t.description` — recupera a descrição que `apply_template_to_company`
   vinha descartando desde O.3.
5. **Seed de etiquetas:** as 8 aprovadas em §2.1.
6. `downgrade()` **completo**: `DROP` das colunas e tabelas em ordem inversa. O job `migrations`
   do CI executa `upgrade head → downgrade base → upgrade head` contra MySQL 8.4 real — uma
   cadeia quebrada reprova o PR (foi exatamente assim que **B-A30** apareceu).

### 4.2 Ordenação fracionária (`position`)

**Problema.** Com `sort_order: Integer`, arrastar um card para o meio da coluna obriga a
reescrever o `sort_order` de todos os cards seguintes: `O(n)` `UPDATE`s por arrasto e uma janela
de corrida entre dois admins arrastando ao mesmo tempo.

**Solução adotada.** Índice fracionário em `String`: entre `"a0"` e `"a1"` sempre cabe `"a0V"`;
entre `"a0"` e `"a0V"` cabe `"a0G"`. **Um `UPDATE` por arrasto, sempre**, sem rebalanceamento e
sem limite prático de inserções.

| Alternativa | Escritas por arrasto | Rebalanceamento | Veredito |
|---|---|---|---|
| `Integer` reindexado | `O(n)` | — | ❌ Corrida entre admins; até 215 `UPDATE`s |
| `Integer` com degraus de 65 535 (o que o Trello faz) | 1 | Necessário após ~16 inserções no mesmo intervalo | ❌ Job de manutenção escondido |
| `Float` / `Decimal` | 1 | Necessário: precisão dupla esgota em ~50 inserções consecutivas no mesmo par | ❌ Falha silenciosa e tardia |
| **`String` fracionária base-62** | **1** | **Nunca** | ✅ **Adotada** |

**Contrato do endpoint de mover.** O cliente **não inventa** a chave — manda as **âncoras**:

```jsonc
PATCH /api/v1/dashboard/cards/{card_id}/move
{ "column_id": 12, "prev_card_id": 88, "next_card_id": 91 }   // null nas pontas
```

O servidor lê as `position` das âncoras **dentro da transação** e gera a chave intermediária.
Isso elimina a classe inteira de bugs "dois clientes calcularam a mesma chave", mantém o
frontend burro e deixa a validação de escopo (o card e as âncoras pertencem à mesma empresa?)
num só lugar. A resposta devolve o card com a `position` efetiva, para o otimismo do frontend
reconciliar.

Implementação em `backend/app/services/fractional_index.py` (~60 linhas, porte direto do
algoritmo de `rocicorp/fractional-indexing`), com teste de propriedade dedicado
(`backend/tests/test_fractional_index.py`).

### 4.3 Contrato de API

Prefixos mantidos: `/api/v1/dashboard` (runtime) e `/api/v1/admin/dashboard-*` (CRUD
administrativo) — mesma divisão que `dashboard_categories.py` já usa.

| Método | Rota | Papel | Descrição |
|---|---|---|---|
| `GET` | `/dashboard/companies/{company_id}/board` | admin, user, sub-user | **Quadro completo**: colunas ordenadas + cards por coluna + etiquetas |
| `POST` | `/dashboard/companies/{company_id}/columns` | admin | Cria coluna (`name`, `kind`, `after_column_id?`) |
| `PATCH` | `/dashboard/columns/{column_id}` | admin | Renomeia / arquiva / define `wip_limit` |
| `PATCH` | `/dashboard/columns/{column_id}/move` | admin | Reordena coluna (`prev_column_id`, `next_column_id`) |
| `DELETE` | `/dashboard/columns/{column_id}` | admin | **409** se houver card não-oculto — mesma regra de `CategoryInUseError` |
| `PATCH` | `/dashboard/cards/{card_id}/move` | admin | Move card entre / dentro de colunas |
| `PATCH` | `/dashboard/cards/{card_id}` | admin | Edita `title`, `description`, `control_code`, `category_id` |
| `PUT` | `/dashboard/cards/{card_id}/labels` | admin | Substitui o conjunto de etiquetas (`label_ids`) |
| `GET` `POST` `PATCH` `DELETE` | `/admin/dashboard-labels[/{id}]` | admin | CRUD de etiquetas — **espelho literal** de `dashboard_categories.py` |
| `GET` `POST` `PATCH` `DELETE` | `/admin/templates/{id}/columns[/{col_id}]` | admin | CRUD de colunas de template, espelhando o de cards de template |

**Alterações em endpoints existentes** (todas retrocompatíveis, só por adição de campo):

- `list_cards_by_company` → `DashboardCardWithCategoryOut` ganha `column_id`, `position`,
  `labels: list[LabelRef]`, `description`.
- `get_card_details` → `DashboardCardDetailOut` ganha `description`, `column_id`, `labels`.
- `apply_template_to_company()` → cria as colunas faltantes **antes** dos cards, casa por
  `origin_template_column_id` (mesma lógica de idempotência de `origin_template_card_id`), e
  passa a copiar `description`.
- `create_company_dashboard_from_template()` → idem, no caminho de onboarding.
- `bulk_update_cards()` → nova operação `set_column`.
- `_card_is_outdated()` → passa a considerar também divergência de coluna e de descrição.

### 4.4 Autorização

`backend/app/core/policy.py` ganha 3 ações. O quadro é **leitura para o cliente, escrita só para
o auditor** — mesma lógica de B-A23 (status é declaração do auditor sobre o auditado):

```python
    MANAGE_COLUMN = "MANAGE_COLUMN"   # criar/renomear/mover/arquivar coluna
    MOVE_CARD     = "MOVE_CARD"       # arrastar card
    MANAGE_LABEL  = "MANAGE_LABEL"    # CRUD do vocabulário + aplicar em card

ALLOWED_ROLES = {
    ...,
    Action.MANAGE_COLUMN: frozenset({"admin"}),
    Action.MOVE_CARD:     frozenset({"admin"}),
    Action.MANAGE_LABEL:  frozenset({"admin"}),
}
```

Escopo por empresa continua vindo de `get_company_with_access()` / `_get_card_with_access()` —
**404, nunca 403**, para card ou coluna de outra empresa (regra B-B23, já implementada). Toda
rota nova de coluna precisa de um `_get_column_with_access()` construído no mesmo molde de
`_get_card_with_access()`.

### 4.5 Importador do quadro Trello

`backend/scripts/import_trello_board.py` — script one-shot, no mesmo formato dos 8 seeds já
existentes em `backend/scripts/`.

```
python -m scripts.import_trello_board "trello exemplo para ser implementado.json" \
       --template-name "[MODELO] Due Diligence - Pix Indireto" [--dry-run]
```

Regras de conversão:

| Origem (Trello) | Destino | Regra |
|---|---|---|
| `lists[]` com `closed=false` | `DashboardTemplateColumn` | Ordenado por `pos`; `position` fracionária regenerada |
| `lists[]` com nome terminando em `>>` | `kind = SECTION` | Heurística explícita, registrada no log do import |
| `lists[]` com `closed=true` | — | **Ignoradas** (6 listas, todas de fase encerrada) |
| `cards[]` com `closed=false` | `DashboardTemplateCard` | 213 cards |
| `card.name` com prefixo `^\d+(\.\d+)*\s` | `control_code` + `title` | 144 casos; o resto vai inteiro para `title` |
| `card.desc` | `description` | Markdown preservado como texto; **remover `U+200C`** (ZWNJ) — o export usa esse caractere invisível como espaçador de parágrafo |
| `card.idLabels` → `labels[].name` | `DashboardLabel` | Filtrado pela lista aprovada em §2.1 |
| `card.pos` | `position` | **Regenerada**, não copiada — o alfabeto é outro |
| `actions[]`, `members[]`, `memberships[]`, `prefs`, `limits`, `pluginData` | — | Ignorados |

O importador é **idempotente por nome de template**: rodar duas vezes não duplica. `--dry-run`
imprime o plano (colunas, cards, etiquetas) sem escrever, e é obrigatório para revisão antes do
primeiro import real.

> ⚠️ **O arquivo `trello exemplo para ser implementado.json` não deve ser commitado.** Ele
> contém 12 nomes completos de membros e IDs de organização do Trello — dado pessoal, sob LGPD,
> num repositório que já teve um incidente de segredos no histórico (item 0.7 do
> [`backlog.md`](backlog.md)). Hoje ele aparece como *untracked* na raiz. Acrescentar
> `trello*.json` ao `.gitignore` **faz parte desta entrega**.

### 4.6 Frontend — biblioteca de arrastar e soltar

O `frontend/package.json` hoje tem **zero** dependências de UI (`next`, `react`, `react-dom`,
`jose`, `server-only`). Esta é a primeira, e a escolha precisa sobreviver a React 19 + Next 16.

| Opção | React 19 | Acessibilidade | Toque | Veredito |
|---|---|---|---|---|
| `react-beautiful-dnd` | ❌ Descontinuada (arquivada em 2024); quebra em StrictMode | Boa | Boa | ❌ Não usar |
| `@hello-pangea/dnd` | ✅ (v18+) | Boa | Boa | 🟡 Alternativa viável; API idêntica à RBD |
| **`@dnd-kit/core` + `@dnd-kit/sortable`** | ✅ | ✅ Teclado + `aria-live` nativos | ✅ `PointerSensor` | ✅ **Adotada** |
| HTML5 Drag & Drop nativo | ✅ | ❌ | ❌ Sem suporte em toque | ❌ Não usar |

**Escolhido: `@dnd-kit`** — mantido, sem dependências transitivas pesadas, com `KeyboardSensor`
de fábrica (requisito de acessibilidade, §7 CA-14) e com `DragOverlay` para o card seguir o
cursor sem reflow da lista.

**Regra de operação obrigatória:** o `npm ci` do job `frontend` do CI passa a resolver esta
dependência; o `package-lock.json` **deve** ser commitado junto, e a versão **fixada** (sem
`^`), no mesmo espírito do `slowapi==0.1.9` / `aiofiles==23.2.1` do backend.

**Fallback sem arrasto (obrigatório).** Todo card tem, no menu de contexto, um item
**"Mover para…"** com `<select>` de coluna + posição. Isso cobre leitor de tela, tablet e o caso
de a biblioteca falhar em carregar — e é o mesmo caminho usado pelos testes de integração, que
não simulam arrasto.

### 4.7 Frontend — estado e otimismo

- **Server Components** carregam o quadro em `page.tsx` (`getBoardAction`) e passam por props,
  exatamente como `dashboard/page.tsx` já faz com `initialCards` / `initialCardDetail`.
- **Server Actions** (`"use server"`) para toda escrita, em `dashboard/actions.ts`, retornando o
  discriminated union `{ ok: true, … } | { ok: false, message }` que **todo** o projeto já usa.
- **`useOptimistic`** (React 19, disponível) para o arrasto: a UI reposiciona na hora, a Server
  Action confirma, e o `catch` reverte com mensagem em `feedback` — o mesmo slot de feedback
  textual que `company-dashboard-client.tsx` já mantém.
- **Sem `revalidatePath` após arrasto.** Recarregar 215 cards a cada movimento anularia o
  otimismo. O estado local é a verdade durante a sessão; `revalidatePath` fica para
  criar/excluir coluna e aplicar template.

---

## 5. Arquivos Afetados na Base Atual

### 5.1 Backend — criar

| Arquivo | Conteúdo |
|---|---|
| `backend/app/models/dashboard_board.py` | `DashboardColumn`, `DashboardColumnKind`, `DashboardTemplateColumn`, `DashboardLabel`, tabela `dashboard_card_labels` |
| `backend/app/schemas/dashboard_board.py` | `BoardOut`, `BoardColumnOut`, `BoardCardOut`, `LabelRef`, `ColumnCreate/Update/Move`, `CardMoveIn`, `CardUpdateIn`, `CardLabelsIn` |
| `backend/app/schemas/dashboard_labels.py` | `DashboardLabelOut/Create/Update` — espelho de `dashboard_templates.py::DashboardCardCategory*` |
| `backend/app/services/fractional_index.py` | `key_between(prev, next) -> str`, `n_keys_between(prev, next, n)` |
| `backend/app/services/dashboard_board.py` | `get_board()`, `create_column()`, `move_column()`, `move_card()`, `set_card_labels()`, exceções de domínio (`ColumnNotFoundError`, `ColumnNotEmptyError`, `LabelNotFoundError`) |
| `backend/app/api/v1/dashboard_board.py` | Router de colunas + move + board |
| `backend/app/api/v1/dashboard_labels.py` | CRUD de etiquetas |
| `backend/alembic/versions/<rev>_add_dashboard_columns_and_labels.py` | Migration §4.1.4 (`down_revision = "b7c02e91d4a5"`) |
| `backend/scripts/import_trello_board.py` | Importador §4.5 |

### 5.2 Backend — alterar

| Arquivo | Alteração | Risco |
|---|---|---|
| `app/models/company_dashboard.py` | `DashboardCard`: `column_id`, `position`, `description`, `due_date`, `labels` (M:N), relacionamento `column`. `Dashboard`: `columns` com `cascade="all, delete-orphan"`. `DashboardTemplate`: `columns`. `DashboardTemplateCard`: `template_column_id`, `position` | 🟡 Médio — `cascade` precisa entrar em `Dashboard.columns` ou `delete_company_cascade` deixa colunas órfãs no SQLite dos testes |
| `app/models/__init__.py` | Registrar os models novos em `Base.metadata` | 🟢 Baixo |
| `app/api/v1/router.py` | `include_router` dos 2 routers novos | 🟢 Baixo |
| `app/api/v1/dashboard_cards.py` | `list_cards_by_company` e `get_card_details` devolvem os campos novos; `create_card_for_company` aceita `column_id` e `description`; `_card_is_outdated` considera coluna/descrição | 🟠 **Alto** — arquivo de 500+ linhas, coberto por `test_dashboard_cards.py` e `test_card_internals_visibility.py` |
| `app/services/dashboard_template_admin.py` | `apply_template_to_company` cria colunas antes dos cards e copia `description`; `bulk_update_cards` ganha `set_column`; CRUD de colunas de template | 🟠 **Alto** — é o coração da idempotência |
| `app/services/dashboard_builder.py` | `create_company_dashboard_from_template` cria colunas e copia `description`/`position` | 🟡 Médio — caminho de onboarding |
| `app/core/policy.py` | 3 `Action` novas + 3 linhas em `ALLOWED_ROLES` | 🟢 Baixo |
| `app/core/access.py` | `get_column_with_access()` no molde de `get_company_with_access()` | 🟢 Baixo |
| `app/schemas/dashboard_runtime.py` | `DashboardCardCreate` (+`column_id`, `description`); `DashboardCardDetailOut` (+`description`, `column_id`, `labels`) | 🟢 Baixo |
| `app/schemas/dashboard_templates.py` | `DashboardCardWithCategoryOut` (+`column_id`, `position`, `labels`, `description`); `BulkCardOperation` aceita `set_column`; `DashboardTemplateCard*` (+`template_column_id`) | 🟢 Baixo |
| `app/api/v1/dashboard_templates.py` | Rotas de coluna de template | 🟡 Médio |
| `app/services/company_admin.py` | Conferir que `delete_company_cascade` remove colunas | 🟡 Médio |
| `backend/scripts/seed_dashboard_templates.py` | Semear colunas junto dos cards | 🟢 Baixo |

### 5.3 Frontend — criar

| Arquivo | Conteúdo |
|---|---|
| `frontend/app/private/admin/empresas/[id]/dashboard/_components/board.tsx` | `<Board>` — `DndContext`, `SortableContext` horizontal de colunas, `DragOverlay` |
| `…/_components/board-column.tsx` | Coluna droppable: cabeçalho, contador, menu (renomear/arquivar/excluir), `+ Adicionar card` |
| `…/_components/board-card.tsx` | Card arrastável: `control_code`, título, chips de etiqueta, badge de status, menu "Mover para…" |
| `…/_components/card-detail-panel.tsx` | Painel lateral extraído do que hoje vive dentro de `company-dashboard-client.tsx` (descrição, status, checklist, histórico, chat, notas) |
| `…/_components/move-card-menu.tsx` | Fallback acessível sem arrasto (§4.6) |
| `frontend/lib/board-labels.ts` | Vocabulário de etiqueta (label + classes de cor), **no molde exato de `lib/control-status.ts`** |
| `frontend/app/private/admin/dashboard-labels/…` | Tela de CRUD de etiquetas (`page.tsx`, `actions.ts`, `*-client.tsx`, `loading.tsx`, `error.tsx`) |
| Testes: `board.test.tsx`, `board-column.test.tsx`, `move-card-menu.test.tsx`, `board-labels.test.ts` | Vitest + Testing Library |

### 5.4 Frontend — alterar

| Arquivo | Alteração |
|---|---|
| `…/dashboard/company-dashboard-client.tsx` (890 linhas) | **Refatoração maior.** O agrupamento por categoria (`groups: CardGroup[]`, `UNCATEGORIZED_KEY`, `collapsedCategories`) sai; entra `<Board>`. Busca, seleção em massa, aplicar template e barra de ação em lote **permanecem** |
| `…/dashboard/actions.ts` | `getBoardAction`, `createColumnAction`, `updateColumnAction`, `moveColumnAction`, `deleteColumnAction`, `moveCardAction`, `updateCardAction`, `setCardLabelsAction`, `listLabelsAction` |
| `…/dashboard/page.tsx` | Carrega o board (`getBoardAction`) em vez da lista de cards |
| `frontend/app/private/client/client-dashboard-client.tsx` (518 linhas) | Renderiza o mesmo `<Board>` em modo `readOnly` |
| `frontend/app/private/client/actions.ts` / `page.tsx` | Ler o board da própria empresa |
| `frontend/app/private/admin/actions.ts` | `DashboardCardDetail` ganha `description`, `column_id`, `labels` |
| `frontend/app/private/admin/templates/templates-client.tsx` (594 linhas) | Gerir colunas de template |
| `frontend/app/private/admin/templates/actions.ts` | Actions de coluna de template |
| `frontend/app/globals.css` | Componentes `.board-scroller`, `.board-column`, `.board-card`, `.label-chip` — mesmo `@layer components` já usado por `.card` / `.status-chip` |
| `frontend/package.json` + `package-lock.json` | `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/modifiers` — versões **fixas** |

### 5.5 Testes e infraestrutura

| Arquivo | Alteração |
|---|---|
| `backend/tests/conftest.py` | Fixtures `coluna`, `board_com_3_colunas`, `etiquetas` |
| `backend/tests/test_dashboard_board.py` | **Novo** — CRUD de coluna, mover card/coluna, 409 de coluna não vazia, 404 cross-tenant |
| `backend/tests/test_fractional_index.py` | **Novo** — propriedade: `key_between` sempre estritamente entre; 1 000 inserções consecutivas no mesmo par mantêm a ordem |
| `backend/tests/test_dashboard_labels.py` | **Novo** — CRUD + `PUT /cards/{id}/labels` |
| `backend/tests/test_authorization_matrix.py` | Linhas para as 3 `Action` novas e para cada rota nova (**inclusive as de leitura**, seção `LEITURAS_RESTRITAS`, precedente M-23) |
| `backend/tests/test_query_budget.py` | Teto de queries para `GET …/board`, parametrizado com **5 e 20 colunas** sob o mesmo teto — é a parametrização por duas quantidades que prova custo constante (padrão já estabelecido no arquivo) |
| `backend/tests/test_migrations_smoke.py` | A migration nova entra na cadeia `upgrade → downgrade → upgrade` |
| `backend/tests/test_dashboard_templates.py` | Aplicar template **com colunas** é idempotente; `description` é copiada |
| `.gitignore` | `trello*.json` |
| `docs/backlog.md` · `docs/roadmap.md` · `docs/relatorio_funcionalidades.md` · `docs/index.md` | Registrar a entrega e os itens D-2/D-4 no backlog |

---

## 6. Padrões de Código a Serem Seguidos

Estes não são conselhos genéricos — são os padrões **já praticados nesta base**, com o arquivo
de referência ao lado. Divergir deles é o que produz revisão longa.

### 6.1 Backend

| # | Padrão | Referência na base |
|---|---|---|
| B1 | **`from __future__ import annotations`** na primeira linha de todo módulo | todos os `app/**/*.py` |
| B2 | **SQLAlchemy 2.0 tipado**: `Mapped[...]` + `mapped_column(...)`, nunca `Column(...)` | `models/company_dashboard.py` |
| B3 | **`select()` + `db.scalars/db.execute`**, nunca `db.query(...)` (legado 1.x) | `api/v1/dashboard_cards.py` |
| B4 | **Camadas:** router valida entrada e traduz exceção → HTTP; **service** contém a regra e chama `db.flush()`; **o router chama `db.commit()`** | `dashboard_categories.py` ↔ `dashboard_template_admin.py` |
| B5 | **Exceção de domínio por regra**, com docstring explicando o *porquê*, traduzida para status HTTP no router (`CategoryInUseError` → 409) | `dashboard_template_admin.py` |
| B6 | **Permissão ≠ posse.** `assert_can(Action.X, role)` para permissão; `_get_*_with_access()` para escopo. Nas duas ordens, nesta ordem | `update_card_status()` |
| B7 | **404, nunca 403, para recurso de outro tenant** (B-B23) | `_get_card_with_access()` |
| B8 | **Idempotência por vínculo de origem** (`origin_template_*_id`) + `UniqueConstraint` que a sustenta | `apply_template_to_company()` · migration `b7c02e91d4a5` |
| B9 | **`selectinload()` para evitar N+1**; agregação em **uma** query com `GROUP BY` | `list_cards_by_company()` · `get_dashboard_status_summary()` |
| B10 | **`dataclass` para resultado de service** (`ApplyTemplateOutcome`, `BulkOperationOutcome`) | `dashboard_template_admin.py` |
| B11 | **Comentários explicam decisão, não mecânica**, e citam o ID do achado (`B-A23`, `O.4`, `M-25`) | toda a base |
| B12 | **Coluna herdada não é removida na mesma migration** que a substitui — vira campo histórico | `tag` na migration `4f2b8e6a91d3` |
| B13 | **`downgrade()` real e testado**, nunca `pass` | todas as migrations |
| B14 | **`ruff check app` limpo** — é o 1º passo do job `backend` do CI | `.github/workflows/ci.yml` |
| B15 | **Mensagens de erro e docstrings em português**; identificadores em inglês | toda a base |

### 6.2 Frontend

| # | Padrão | Referência na base |
|---|---|---|
| F1 | **Server Component busca, Client Component renderiza.** `page.tsx` chama a action e passa `initial*` por props | `dashboard/page.tsx` → `company-dashboard-client.tsx` |
| F2 | **Cada rota tem `page.tsx` + `loading.tsx` + `error.tsx`** | todas as rotas de `app/private/admin/**` |
| F3 | **Server Actions com `"use server"`**, uma por arquivo `actions.ts` ao lado da página | `dashboard/actions.ts` |
| F4 | **Toda action começa por `await requireAdmin()` / `requireClient()`** e obtém o token com `getAccessToken()` — a barreira do frontend nunca substitui a do backend, ela a duplica | `dashboard/actions.ts` |
| F5 | **`callBackend<T>(path, { method, token, body })`** — nunca `fetch` direto para o backend | `lib/server-backend.ts` |
| F6 | **Retorno discriminado `{ ok: true, … }` ou `{ ok: false, message }`** para toda escrita; leitura pode lançar (o `error.tsx` captura) | `applyTemplateToCompanyAction` |
| F7 | **Vocabulário visual centralizado em `lib/`** (label + classes de cor + ordem canônica), nunca duplicado por tela — foi o defeito B-M20 | `lib/control-status.ts` |
| F8 | **Estilo via `@layer components` no `globals.css`** + utilitários Tailwind; tokens em `:root` | `globals.css` |
| F9 | **`useTransition` + slot de `feedback` textual** para o estado de escrita | `company-dashboard-client.tsx` |
| F10 | **Nomes de variável e texto de UI em português**; tipos e funções em inglês | toda a base |
| F11 | **Um `*.test.ts(x)` ao lado de cada `actions.ts`** — a suíte de frontend nasceu em 114 testes e não regride | `actions.test.ts` em 8 rotas |
| F12 | **`tsc --noEmit` e `eslint` limpos** — job `frontend` do CI | `.github/workflows/ci.yml` |

### 6.3 Testes

| # | Padrão | Referência |
|---|---|---|
| T1 | **Uma barreira por correção.** Toda regra nova entra com o teste que falha sem ela | `plano_implementacao.md` |
| T2 | **Matriz de autorização é obrigatória**, escrita *e* leitura | `test_authorization_matrix.py` |
| T3 | **Orçamento de queries parametrizado por duas quantidades** sob o mesmo teto | `test_query_budget.py` |
| T4 | **SQLite em memória** via `conftest.py`, `Base.metadata.create_all` por teste | `conftest.py` |
| T5 | **Docstring de módulo explicando que defeito o arquivo previne** | `test_query_budget.py` |

---

## 7. Critérios de Aceite

Cada critério é verificável e tem um teste nomeado. A tarefa está pronta quando **todos**
passarem e o CI estiver verde nos 4 jobs.

### 7.1 Modelo e migration

| # | Critério | Como verificar |
|---|---|---|
| **CA-01** | `alembic upgrade head` → `downgrade base` → `upgrade head` completa contra **MySQL 8.4 real** sem erro | Job `migrations` do CI |
| **CA-02** | Após o upgrade, **nenhum** `dashboard_cards` fica com `column_id IS NULL` num quadro que tinha cards; a ordem visível antes e depois é idêntica | `test_migrations_smoke.py` |
| **CA-03** | Cards derivados de template recebem, no backfill, a `description` do `DashboardTemplateCard` de origem | `test_migrations_smoke.py` |
| **CA-04** | `key_between(a, b)` devolve sempre `a < k < b`; 1 000 inserções consecutivas no mesmo par preservam a ordem sem rebalancear | `test_fractional_index.py` |

### 7.2 API e regras de negócio

| # | Critério | Como verificar |
|---|---|---|
| **CA-05** | `GET /dashboard/companies/{id}/board` devolve colunas ordenadas por `position`, cada uma com seus cards ordenados por `position`, com etiquetas embutidas | `test_dashboard_board.py` |
| **CA-06** | `PATCH /dashboard/cards/{id}/move` reposiciona o card e **executa exatamente 1 `UPDATE`** no card movido; nenhum outro card é reescrito | `test_dashboard_board.py` + `ContadorDeQueries` |
| **CA-07** | Mover card para coluna de **outra empresa** responde **404** (não 403, não 200) | `test_dashboard_board.py` |
| **CA-08** | `DELETE /dashboard/columns/{id}` com card não-oculto responde **409** com mensagem em português; com a coluna vazia, **204** | `test_dashboard_board.py` |
| **CA-09** | `apply_template_to_company` chamado **2×** com o mesmo template cria colunas e cards na 1ª e **nada** na 2ª (`created_count == 0`) | `test_dashboard_templates.py` |
| **CA-10** | Aplicar template copia `description` para o card da empresa | `test_dashboard_templates.py` |
| **CA-11** | `user` e `sub-user` recebem **403** em `move`, CRUD de coluna e CRUD/atribuição de etiqueta; recebem **200** em `GET …/board` | `test_authorization_matrix.py` |
| **CA-12** | Etiqueta **não** altera `status`, e `status` continua `admin`-only | `test_dashboard_labels.py` |
| **CA-13** | `GET …/board` custa um número **constante** de queries: mesmo teto com 5 e com 20 colunas | `test_query_budget.py` |

### 7.3 Interface

| # | Critério | Como verificar |
|---|---|---|
| **CA-14** | O quadro é operável **inteiramente por teclado**: `Tab` foca o card, `Espaço` levanta, setas movem, `Espaço` solta, `Esc` cancela — e cada passo é anunciado via `aria-live` | `board.test.tsx` + verificação manual com leitor de tela |
| **CA-15** | O menu **"Mover para…"** move card sem nenhum arrasto | `move-card-menu.test.tsx` |
| **CA-16** | Arrastar reposiciona o card **imediatamente** (`useOptimistic`); falha do servidor **reverte** a posição e exibe a mensagem de erro | `board.test.tsx` com action mockada rejeitando |
| **CA-17** | O cliente (`user` / `sub-user`) vê o quadro com as colunas na mesma ordem do admin e **não** consegue arrastar nem ver controles de edição | `client-dashboard-client.test.tsx` |
| **CA-18** | Colunas `kind = SECTION` renderizam como separador visual, sem área de soltar e sem contador de cards | `board-column.test.tsx` |
| **CA-19** | Colunas com `hidden = true` só aparecem com o *toggle* "Mostrar arquivadas" ligado — mesmo comportamento que `showHidden` já tem para cards | `board.test.tsx` |
| **CA-20** | O quadro rola horizontalmente sem estourar o `body`; cada coluna rola verticalmente por dentro | Verificação manual em 1280 px e 375 px |
| **CA-21** | Busca, seleção em massa e a barra de ação em lote continuam funcionando sobre o quadro | `board.test.tsx` |

### 7.4 Importação

| # | Critério | Como verificar |
|---|---|---|
| **CA-22** | `import_trello_board.py --dry-run` sobre o export real reporta **25 colunas** (3 delas `SECTION`), **213 cards**, **146 descrições** e **8 etiquetas**, sem escrever no banco | Execução manual + `--dry-run` no CI local |
| **CA-23** | Rodar o importador **2×** com o mesmo `--template-name` não duplica coluna, card nem etiqueta | Execução manual contra base de desenvolvimento |
| **CA-24** | Os 144 cards com prefixo numérico saem com `control_code` preenchido e o título **sem** o prefixo duplicado | `--dry-run` + inspeção |
| **CA-25** | Nenhum `U+200C` sobrevive em `description` | `grep -P '\x{200c}'` no dump do `--dry-run` |

### 7.5 Portões de qualidade

| # | Critério |
|---|---|
| **CA-26** | `ruff check app` sem achados; `pip-audit` sem CVE nova |
| **CA-27** | `npm run lint`, `tsc --noEmit` e `npm run build` limpos |
| **CA-28** | `pytest --cov=app` verde; a suíte **cresce** (nenhum teste existente removido ou marcado `skip`) |
| **CA-29** | `vitest run` verde; a suíte de frontend **cresce** a partir dos 114 atuais |
| **CA-30** | `trello*.json` no `.gitignore` e o arquivo **fora** do índice do git |
| **CA-31** | `docs/backlog.md`, `docs/roadmap.md`, `docs/relatorio_funcionalidades.md` e `docs/index.md` atualizados; D-2 e D-4 registrados como itens de backlog |

---

## 8. Referências Técnicas e Links Úteis

### 8.1 Documentação oficial das tecnologias do projeto

| Tema | Link |
|---|---|
| SQLAlchemy 2.0 — ORM declarativo tipado (`Mapped` / `mapped_column`) | https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html |
| SQLAlchemy 2.0 — estratégias de carregamento (`selectinload`, N+1) | https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html |
| SQLAlchemy 2.0 — relacionamento muitos-para-muitos (`secondary`) | https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html#many-to-many |
| Alembic — operações de migration (`op.create_table`, `op.add_column`, `op.bulk_insert`) | https://alembic.sqlalchemy.org/en/latest/ops.html |
| Alembic — migração de dados dentro do upgrade | https://alembic.sqlalchemy.org/en/latest/cookbook.html#conditional-migration-elements |
| FastAPI — `response_model` e `Depends` | https://fastapi.tiangolo.com/tutorial/response-model/ |
| FastAPI — organização de rotas grandes com `APIRouter` | https://fastapi.tiangolo.com/tutorial/bigger-applications/ |
| Pydantic v2 — `Field`, `Literal`, validação | https://docs.pydantic.dev/latest/concepts/fields/ |
| Next.js 16 — Server Actions e mutações | https://nextjs.org/docs/app/getting-started/updating-data |
| Next.js 16 — Server vs Client Components | https://nextjs.org/docs/app/getting-started/server-and-client-components |
| Next.js 16 — `loading.tsx` / `error.tsx` | https://nextjs.org/docs/app/api-reference/file-conventions/error |
| React 19 — `useOptimistic` | https://react.dev/reference/react/useOptimistic |
| React 19 — `useTransition` | https://react.dev/reference/react/useTransition |
| Tailwind CSS 4 — `@layer components` e tokens | https://tailwindcss.com/docs/adding-custom-styles |
| MySQL 8.4 — índices compostos e `ORDER BY` | https://dev.mysql.com/doc/refman/8.4/en/order-by-optimization.html |
| MySQL 8.4 — `NULL` em índices `UNIQUE` | https://dev.mysql.com/doc/refman/8.4/en/create-index.html |
| Vitest + Testing Library | https://testing-library.com/docs/react-testing-library/intro/ |

### 8.2 Biblioteca de arrastar e soltar

| Tema | Link |
|---|---|
| dnd-kit — documentação | https://docs.dndkit.com/ |
| dnd-kit — preset `sortable` (listas e quadros) | https://docs.dndkit.com/presets/sortable |
| dnd-kit — acessibilidade (`KeyboardSensor`, `announcements`, `screenReaderInstructions`) | https://docs.dndkit.com/guides/accessibility |
| dnd-kit — repositório | https://github.com/clauderic/dnd-kit |
| `@hello-pangea/dnd` (fork mantido da `react-beautiful-dnd`) — alternativa avaliada | https://github.com/hello-pangea/dnd |
| `react-beautiful-dnd` — aviso oficial de descontinuação | https://github.com/atlassian/react-beautiful-dnd/issues/2672 |
| WAI-ARIA Authoring Practices — padrão de arrastar e soltar acessível | https://www.w3.org/WAI/ARIA/apg/patterns/ |

### 8.3 Ordenação fracionária (padrão de mercado)

| Tema | Link |
|---|---|
| `rocicorp/fractional-indexing` — implementação de referência (algoritmo portado em §4.2) | https://github.com/rocicorp/fractional-indexing |
| "Implementing Fractional Indexing" — Evan Wallace (Figma), a explicação canônica | https://observablehq.com/@dgreensp/implementing-fractional-indexing |
| Figma — "Realtime Editing of Ordered Sequences" (por que Figma usa índice fracionário) | https://www.figma.com/blog/realtime-editing-of-ordered-sequences/ |
| Atlassian — LexoRank, a solução do Jira para o mesmo problema | https://www.youtube.com/watch?v=OjQv9xMoFbg |
| Discussão StackOverflow — "How to store ordered lists in a database" | https://stackoverflow.com/questions/9536262/best-representation-of-an-ordered-list-in-a-database |
| Trello — semântica do campo `pos` na API | https://developer.atlassian.com/cloud/trello/guides/rest-api/object-definitions/#card-object |

### 8.4 Referências do domínio Trello

| Tema | Link |
|---|---|
| Trello REST API — objetos `Board`, `List`, `Card`, `Label`, `Checklist` | https://developer.atlassian.com/cloud/trello/rest/ |
| Trello — formato do export JSON de um quadro | https://support.atlassian.com/trello/docs/exporting-data-from-trello/ |
| Trello — modelo conceitual de listas e etiquetas | https://developer.atlassian.com/cloud/trello/guides/rest-api/object-definitions/ |

### 8.5 Arquitetura e padrões aplicáveis

| Tema | Link |
|---|---|
| Kanban — limite de WIP por coluna (base do campo `wip_limit`) | https://www.atlassian.com/agile/kanban/wip-limits |
| Multi-tenancy — isolamento por linha e a regra "404, não 403" | https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/ |
| OWASP API Security Top 10 — BOLA (a razão de `_get_*_with_access()`) | https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/ |
| Optimistic UI — padrão e armadilhas de reconciliação | https://react.dev/reference/react/useOptimistic |

### 8.6 Referências internas obrigatórias antes de codar

| Documento | Por quê |
|---|---|
| [`plano_implementacao.md`](plano_implementacao.md) → BLOCO O | O.3 e O.4 explicam por que categoria e template estão modelados assim; alterá-los sem ler é retrabalho garantido |
| [`relatorio_bugs.md`](relatorio_bugs.md) → B-A23, B-A24, B-A25, B-A28, B-B23, B-M23 | As 6 regras que o código novo precisa preservar |
| [`relatorio_melhorias.md`](relatorio_melhorias.md) → M-23, M-25 | Matriz de autorização e orçamento de queries são obrigatórios, não opcionais |
| [`INSTRUCTIONS.md`](../INSTRUCTIONS.md) | Diretivas de escrita e documentação do repositório |

---

## 9. Faseamento e Estimativa

| Fase | Entrega | Esforço | Bloqueia |
|---|---|---|---|
| **1** | `fractional_index.py` + teste de propriedade | 0,5 dia | Tudo |
| **2** | Models + migration + backfill + smoke de migration | 1,5 dia | 3, 4 |
| **3** | Services (`dashboard_board.py`) + `apply_template` com colunas + `description` | 1,5 dia | 4 |
| **4** | Routers + schemas + `policy.py` + matriz de autorização + orçamento de queries | 1,5 dia | 5 |
| **5** | Frontend admin: `<Board>`, colunas, arrasto, fallback acessível, painel de detalhe | 3 dias | 6 |
| **6** | Frontend cliente (`readOnly`) + CRUD de etiquetas + colunas de template | 1,5 dia | — |
| **7** | Importador do Trello + `--dry-run` + `.gitignore` | 1 dia | — |
| **8** | Testes de frontend, documentação (`backlog`, `roadmap`, `funcionalidades`, `index`) | 1 dia | — |
| | **Total** | **≈ 11,5 dias** | |

**Sequência recomendada de PRs** (cada um verde no CI antes do seguinte):

1. `feat(board): índice fracionário` — fases 1
2. `feat(board): colunas, etiquetas e descrição no modelo` — fase 2
3. `feat(board): serviços e API de quadro` — fases 3 e 4
4. `feat(board): quadro arrastável no admin` — fase 5
5. `feat(board): quadro do cliente, etiquetas e colunas de template` — fase 6
6. `chore(board): importador do quadro Trello` — fase 7
7. `docs: registrar a entrega do quadro` — fase 8

---

## 10. Riscos

| # | Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|---|
| R1 | Refatorar `company-dashboard-client.tsx` (890 linhas) quebra busca / seleção em massa / aplicar template | Alta | Alto | Extrair o painel de detalhe **antes** de trocar o agrupamento; um PR por passo; testes de frontend antes do refactor |
| R2 | `apply_template_to_company` perde a idempotência ao ganhar colunas | Média | Alto | `UNIQUE (dashboard_id, origin_template_column_id)` + CA-09 no mesmo commit da mudança |
| R3 | Backfill da migration deixa cards sem coluna em produção | Média | Alto | CA-02 + ensaio do `upgrade` contra uma cópia do banco de produção antes do deploy |
| R4 | `@dnd-kit` introduz CVE ou incompatibilidade com Next 16 | Baixa | Médio | Versão fixa, `npm audit` no job `frontend`, e o fallback "Mover para…" mantém a funcionalidade se a lib precisar sair |
| R5 | Arrasto inutilizável em tablet / leitor de tela | Média | Médio | CA-14 e CA-15 são bloqueantes, não desejáveis |
| R6 | O export do Trello é commitado por engano, expondo 12 nomes de membros | Média | Alto | CA-30 — `.gitignore` na **primeira** fase, não na última |
| R7 | Quadro com 215 cards fica lento no navegador | Baixa | Médio | Medir com o quadro real importado; se necessário, virtualizar só a lista interna da coluna (v2) |

---

## 11. Fora de Escopo (registrado, não esquecido)

| Item | Por quê | Destino |
|---|---|---|
| Anexos em card | 0 no export; `Evidence` está ligada a `audit_control` (D-4) | Backlog |
| Responsável / membro do card | 0 no export; exige decidir se cliente pode ser atribuído | v2 |
| Prazo (`due_date`) na UI | 0 no export; a **coluna** já entra em v1 para evitar 2ª migration | v2 |
| Limite de WIP por coluna | Idem — coluna criada, UI depois | v2 |
| Múltiplos quadros por empresa | `Dashboard` é 1:1 com `Company` por decisão de produto | — |
| Tempo real (WebSocket / SSE) entre admins | Sem requisito; o otimismo local resolve o caso de um admin por vez | Backlog |
| Campos customizados do Trello | 0 no export | — |
| Automações estilo Butler | Sem requisito | — |
| Importar `actions[]` (527 eventos) como `DashboardCardHistoryEntry` | Histórico do Trello não é histórico da plataforma; poluiria a trilha de auditoria com atores que não existem aqui | — |
