# Spec — Quadro Kanban de Colunas e Cards

| Campo | Valor |
|---|---|
| **Documento** | Especificação Técnica (tradução do [`PRD.md`](PRD.md) v1.0) |
| **Data** | 2026-08-27 |
| **Branch base** | `fix/audit-repository-refactor-and-regressions` · HEAD `754ed58` |
| **Head de migrations** | `b7c02e91d4a5` |
| **Escopo** | 20 arquivos novos · 24 arquivos modificados · 3 dependências npm |

> **Duas divergências do PRD corrigidas nesta spec**, ambas descobertas na leitura do código:
> **(1)** `frontend/app/private/client/client-dashboard-client.tsx` **não** renderiza
> `DashboardCard` — renderiza `AuditControl` vindo de `GET /api/v1/client/controls`. A visão de
> quadro do cliente é **rota nova**, não modificação (§2.4.3 / §3.4).
> **(2)** `backend/tests/test_migrations_smoke.py` é **análise estática** (importável, nome ==
> `revision`, head único) e roda **sem banco** — não pode verificar CA-02/CA-03. O backfill
> precisa de arquivo de teste próprio (§2.5.4).

---

## 1. Árvore de Arquivos

`[+]` criar · `[~]` modificar · sem marca = contexto inalterado

```
Developer/
├── [~] .gitignore                                    # + trello*.json (CA-30)
│
├── backend/
│   ├── alembic/versions/
│   │   └── [+] c8f1a3e57b90_add_dashboard_columns_and_labels.py
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── [+] dashboard_board.py                # board + colunas + move
│   │   │   ├── [+] dashboard_labels.py               # CRUD de etiquetas
│   │   │   ├── [~] dashboard_cards.py                # campos novos na saída
│   │   │   ├── [~] dashboard_templates.py            # + colunas de template
│   │   │   └── [~] router.py                         # + 2 include_router
│   │   ├── core/
│   │   │   ├── [~] access.py                         # + get_column_with_access
│   │   │   └── [~] policy.py                         # + 3 Action
│   │   ├── models/
│   │   │   ├── [+] dashboard_board.py                # 3 models + tabela M:N
│   │   │   ├── [~] company_dashboard.py              # 6 colunas + 4 relationships
│   │   │   └── [~] __init__.py                       # registro em Base.metadata
│   │   ├── schemas/
│   │   │   ├── [+] dashboard_board.py                # BoardOut e I/O de coluna
│   │   │   ├── [+] dashboard_labels.py               # I/O de etiqueta
│   │   │   ├── [~] dashboard_runtime.py              # + description/column/labels
│   │   │   └── [~] dashboard_templates.py            # + column_id/position/labels
│   │   └── services/
│   │       ├── [+] fractional_index.py               # key_between / n_keys_between
│   │       ├── [+] dashboard_board.py                # regra de board e move
│   │       ├── [~] dashboard_template_admin.py       # colunas + description
│   │       ├── [~] dashboard_builder.py              # onboarding com colunas
│   │       └── [~] company_admin.py                  # cascade de colunas
│   ├── scripts/
│   │   ├── [+] import_trello_board.py                # importador one-shot
│   │   └── [~] seed_dashboard_templates.py           # semear colunas
│   └── tests/
│       ├── [+] test_fractional_index.py
│       ├── [+] test_dashboard_board.py
│       ├── [+] test_dashboard_labels.py
│       ├── [+] test_migration_board_backfill.py      # substitui o CA-02/03 do PRD
│       ├── [~] conftest.py                           # 3 fixtures novas
│       ├── [~] test_authorization_matrix.py          # + rotas novas
│       ├── [~] test_query_budget.py                  # + teto de GET /board
│       ├── [~] test_dashboard_cards.py               # campos novos
│       └── [~] test_dashboard_templates.py           # idempotência com colunas
│
├── frontend/
│   ├── app/
│   │   ├── [~] globals.css                           # 4 classes em @layer components
│   │   └── private/
│   │       ├── admin/
│   │       │   ├── [~] actions.ts                    # DashboardCardDetail
│   │       │   ├── dashboard-labels/                 # tela nova de CRUD
│   │       │   │   ├── [+] page.tsx
│   │       │   │   ├── [+] actions.ts
│   │       │   │   ├── [+] actions.test.ts
│   │       │   │   ├── [+] dashboard-labels-client.tsx
│   │       │   │   ├── [+] loading.tsx
│   │       │   │   └── [+] error.tsx
│   │       │   ├── empresas/[id]/dashboard/
│   │       │   │   ├── _components/
│   │       │   │   │   ├── [+] board.tsx
│   │       │   │   │   ├── [+] board-column.tsx
│   │       │   │   │   ├── [+] board-card.tsx
│   │       │   │   │   ├── [+] card-detail-panel.tsx
│   │       │   │   │   ├── [+] move-card-menu.tsx
│   │       │   │   │   ├── [+] board.test.tsx
│   │       │   │   │   ├── [+] board-column.test.tsx
│   │       │   │   │   └── [+] move-card-menu.test.tsx
│   │       │   │   ├── [~] company-dashboard-client.tsx   # refatoração maior
│   │       │   │   ├── [~] actions.ts                     # 9 actions novas
│   │       │   │   ├── [~] actions.test.ts
│   │       │   │   └── [~] page.tsx                       # carrega board
│   │       │   └── templates/
│   │       │       ├── [~] templates-client.tsx           # colunas de template
│   │       │       ├── [~] actions.ts
│   │       │       └── [~] actions.test.ts
│   │       └── client/
│   │           └── quadro/                           # ROTA NOVA (não é o page.tsx atual)
│   │               ├── [+] page.tsx
│   │               ├── [+] actions.ts
│   │               ├── [+] actions.test.ts
│   │               ├── [+] client-board-client.tsx
│   │               ├── [+] loading.tsx
│   │               └── [+] error.tsx
│   ├── lib/
│   │   ├── [+] board-labels.ts                       # molde de control-status.ts
│   │   └── [+] board-labels.test.ts
│   ├── [~] package.json                              # 3 deps @dnd-kit
│   └── [~] package-lock.json
│
└── docs/
    ├── [~] backlog.md · [~] roadmap.md
    ├── [~] relatorio_funcionalidades.md · [~] index.md
    ├── PRD.md
    └── [+] Spec.md
```

---

## 2. Arquivos para Criar

### 2.1 Backend — modelo e persistência

#### `backend/app/models/dashboard_board.py`
Models novos, isolados de `company_dashboard.py` para não engordar um arquivo de 290 linhas.

| Símbolo | Responsabilidade |
|---|---|
| `DashboardColumnKind(str, enum.Enum)` | `COLUMN` \| `SECTION`. `SECTION` é a lista separadora `>>` do Trello: renderiza como divisor, não aceita card. |
| `DashboardColumn(Base)` | Tabela `dashboard_columns`. Campos: `id`, `dashboard_id` (FK `CASCADE`, index), `name` `String(160)`, `kind` (`Enum`, default `COLUMN`), `position` `String(64)` not-null, `hidden` `Boolean` default `False`, `wip_limit` `Integer` nullable, `origin_template_column_id` (FK `SET NULL`, index), `created_at`. `__table_args__` com `UniqueConstraint("dashboard_id", "origin_template_column_id", name="uq_dashboard_column_origin_per_dashboard")` — mesma invariante que `uq_dashboard_card_origin_per_dashboard`. Relationships: `dashboard`, `cards` (`back_populates="column"`, **sem** `delete-orphan`: apagar coluna não apaga card, a FK é `SET NULL`), `origin_template_column`. |
| `DashboardTemplateColumn(Base)` | Tabela `dashboard_template_columns`. `id`, `template_id` (FK `CASCADE`, index), `name`, `kind`, `position`. `UniqueConstraint("template_id", "name")`. Relationships: `template`, `cards`. |
| `DashboardLabel(Base)` | Tabela `dashboard_labels`. `id`, `name` `String(60)` unique, `color` `String(20)` default `#788c5d`, `sort_order` `Integer` default `0`. Espelho estrutural de `DashboardCardCategory` (`company_dashboard.py:76-92`). |
| `dashboard_card_labels` (`Table`) | M:N. `card_id` (FK `dashboard_cards.id`, `CASCADE`) + `label_id` (FK `dashboard_labels.id`, `CASCADE`), PK composta. Declarada como `Table` do Core (não model), consumida via `secondary=` em `DashboardCard.labels`. |

Índices declarados aqui via `Index(...)` em `__table_args__`:
`ix_dashboard_columns_board_position (dashboard_id, position)`.

> **Nota de import circular:** `DashboardColumn.dashboard` aponta para `Dashboard`, que vive em
> `company_dashboard.py`, que por sua vez precisa de `DashboardColumn` em `DashboardCard.column`.
> Resolver com string forward-ref (`Mapped["Dashboard"]`) nos dois lados e importar ambos em
> `app/models/__init__.py` — é como `DashboardCardHistoryEntry.actor_user` → `User` já funciona.

#### `backend/alembic/versions/c8f1a3e57b90_add_dashboard_columns_and_labels.py`
`down_revision = "b7c02e91d4a5"`. Docstring no formato de `4f2b8e6a91d3` (explica a estratégia de
dados, não a mecânica).

`upgrade()` em 6 passos, nesta ordem:
1. `op.create_table` × 4 (`dashboard_template_columns` **antes** de `dashboard_columns`, que a
   referencia; `dashboard_labels` antes de `dashboard_card_labels`).
2. `op.add_column` × 6 — `dashboard_cards`: `column_id`, `position`, `description`, `due_date`;
   `dashboard_template_cards`: `template_column_id`, `position`. **`position` entra nullable**,
   é preenchida no passo 4, e só então vira `NOT NULL` via `op.alter_column` — `ADD COLUMN NOT
   NULL` sem default falha em tabela populada no MySQL.
3. **Backfill de colunas:** por `dashboards.id`, uma `dashboard_columns` por `category_id`
   distinto em uso naquele quadro, nomeada com o nome da categoria, ordenada por
   `dashboard_card_categories.sort_order`; bucket `Sem categoria` para `category_id IS NULL`.
   Depois `UPDATE dashboard_cards SET column_id = <coluna correspondente>`.
4. **Backfill de `position`:** chaves fracionárias geradas em Python (import direto de
   `app.services.fractional_index` — a migration **pode** importar do app, precedente em
   `a3d81f4c7b02`), na ordem `sort_order ASC, id ASC`. Idem para `dashboard_template_cards`.
5. **Backfill de `description`:** `UPDATE dashboard_cards c JOIN dashboard_template_cards t ON
   c.origin_template_card_id = t.id SET c.description = t.description WHERE t.description IS NOT
   NULL` — recupera o dado que `apply_template_to_company` descarta desde O.3.
6. **Seed** das 8 etiquetas aprovadas (PRD §2.1) via `op.bulk_insert`.
7. `op.create_index` × 2.

`downgrade()`: `drop_index` × 2 → `drop_column` × 6 → `drop_table` × 4 em ordem inversa.
**Sem `pass`** (B13) — o job `migrations` do CI reverte até `base` e reaplica.

#### `backend/app/services/fractional_index.py`
Sem dependência externa. Alfabeto base-62 (`0-9A-Za-z`, ordem ASCII crescente).

| Função | Contrato |
|---|---|
| `key_between(prev: str \| None, next: str \| None) -> str` | Chave estritamente entre as duas. `None` = ponta da lista. Levanta `ValueError` se `prev >= next`. |
| `n_keys_between(prev, next, n) -> list[str]` | `n` chaves ordenadas entre as âncoras — usada pelos backfills e pelo importador. |
| `INITIAL_KEY: str` | Chave da primeira inserção numa lista vazia. |

Puro, sem `Session`, sem I/O — é o que torna `test_fractional_index.py` um teste de propriedade
barato e o que permite a migration importá-lo sem carregar o app inteiro.

### 2.2 Backend — serviços

#### `backend/app/services/dashboard_board.py`
Camada de regra. Chama `db.flush()`, **nunca** `db.commit()` (B4). Retorna `dataclass` (B10).

| Símbolo | Responsabilidade |
|---|---|
| `ColumnNotFoundError` | Coluna inexistente → 404 no router. |
| `ColumnNotEmptyError` | `DELETE` de coluna com card não-oculto → 409. Docstring explica a escolha (não apagar em cascata), no molde de `CategoryInUseError`. |
| `ColumnKindError` | Tentativa de soltar card em coluna `SECTION` → 422. |
| `LabelNotFoundError` | `label_id` inexistente em `set_card_labels` → 404. |
| `AnchorMismatchError` | Âncora (`prev_card_id`/`next_card_id`) que não pertence à coluna de destino → 422. Fecha o buraco de o cliente mandar âncoras inconsistentes e o servidor gerar chave fora de ordem. |
| `BoardData` (`@dataclass`) | Agregado pronto do quadro: colunas ordenadas + cards por coluna + etiquetas. |
| `get_board(db, dashboard_id, *, include_hidden, search) -> BoardData` | **3 queries fixas**, independentemente do número de colunas (CA-13): (1) colunas por `dashboard_id`; (2) cards por `dashboard_id` com `selectinload(DashboardCard.labels)`; (3) vocabulário de etiquetas. Agrupamento em memória. Cards com `column_id IS NULL` vão para um bucket sintético `Sem coluna`. |
| `create_column(db, dashboard, *, name, kind, after_column_id) -> DashboardColumn` | `position` = `key_between(after.position, seguinte.position)`. |
| `update_column(db, column_id, *, name, hidden, wip_limit)` | Renomear / arquivar / limitar. |
| `move_column(db, column_id, *, prev_column_id, next_column_id)` | Lê as âncoras na transação, calcula 1 chave, 1 `UPDATE`. |
| `delete_column(db, column_id)` | Conta cards não-ocultos; `ColumnNotEmptyError` se > 0. |
| `move_card(db, card, *, column_id, prev_card_id, next_card_id) -> DashboardCard` | O núcleo. Valida: coluna destino no **mesmo** `dashboard_id` do card; coluna não é `SECTION`; âncoras pertencem à coluna destino. Calcula `key_between` e faz **exatamente 1 `UPDATE`** (CA-06). |
| `set_card_labels(db, card, label_ids) -> list[DashboardLabel]` | Substitui o conjunto inteiro (semântica `PUT`). Valida todos os ids antes de tocar no vínculo. |
| `list_labels` / `create_label` / `update_label` / `delete_label` | Espelho literal de `dashboard_template_admin.py:69-129`. `delete_label` bloqueia com `LabelInUseError` (409) se houver card vinculado — mesma regra de `CategoryInUseError`. |

### 2.3 Backend — schemas e rotas

#### `backend/app/schemas/dashboard_board.py`
`LabelRef` (`id`, `name`, `color`) · `BoardCardOut` (`id`, `control_code`, `title`, `description`,
`status`, `position`, `category_id`, `category_name`, `labels`, `hidden`,
`origin_template_card_id`, `is_outdated`) · `BoardColumnOut` (`id`, `name`, `kind`, `position`,
`hidden`, `wip_limit`, `cards`, `card_count`) · `BoardOut` (`dashboard_id`, `company_id`,
`title`, `columns`, `uncolumned: list[BoardCardOut]`) · `ColumnCreateIn` · `ColumnUpdateIn` ·
`ColumnMoveIn` · `CardMoveIn` (`column_id`, `prev_card_id`, `next_card_id`) · `CardUpdateIn`
(`title`, `description`, `control_code`, `category_id`) · `CardLabelsIn` (`label_ids`).

#### `backend/app/schemas/dashboard_labels.py`
`DashboardLabelOut` / `Create` / `Update` — cópia estrutural de
`dashboard_templates.py:8-25` (`DashboardCardCategory*`), com os mesmos limites de `Field`.

#### `backend/app/api/v1/dashboard_board.py`
`APIRouter(prefix="/dashboard", tags=["Dashboard Board"])` — **mesmo prefixo** que
`dashboard_cards.py`, arquivo separado só para não crescer o de 600 linhas. O FastAPI mescla os
dois sob a mesma tag de rota sem conflito, desde que nenhum path se repita.

Helper `_get_column_with_access(db, column_id, current_user) -> DashboardColumn`: `JOIN`
`dashboard_columns → dashboards → companies`, admin passa direto, cliente compara
`company.principal_user_id == resolve_owner_user_id(current_user)`, e **404 em qualquer outro
caso** (B7). Molde literal de `dashboard_cards.py:58-80`.

| Rota | Guard |
|---|---|
| `GET /companies/{company_id}/board` | `get_company_with_access` (admin, user, sub-user) |
| `POST /companies/{company_id}/columns` | `require_admin` + `assert_can(MANAGE_COLUMN)` |
| `PATCH /columns/{column_id}` | `assert_can(MANAGE_COLUMN)` → `_get_column_with_access` |
| `PATCH /columns/{column_id}/move` | idem |
| `DELETE /columns/{column_id}` | idem · 409 em `ColumnNotEmptyError` |
| `PATCH /cards/{card_id}/move` | `assert_can(MOVE_CARD)` → `_get_card_with_access` |
| `PATCH /cards/{card_id}` | `require_admin` → `_get_card_with_access` |
| `PUT /cards/{card_id}/labels` | `assert_can(MANAGE_LABEL)` → `_get_card_with_access` |

**Ordem obrigatória em toda rota: permissão (`assert_can`) antes de escopo (`_get_*_with_access`)**
— é a ordem de `update_card_status` (`dashboard_cards.py:421-451`) e o que garante 403 para papel
errado e 404 para tenant errado, nunca o inverso.

#### `backend/app/api/v1/dashboard_labels.py`
`APIRouter(prefix="/admin/dashboard-labels", tags=["Admin — Etiquetas de Card"])`.
CRUD de 4 rotas, tradução de `IntegrityError` → 409 e `LabelNotFoundError` → 404. Cópia
estrutural de `dashboard_categories.py` inteiro (109 linhas), incluindo o helper `_to_out`.

### 2.4 Frontend

#### 2.4.1 `frontend/lib/board-labels.ts`
Vocabulário visual centralizado (F7). Exporta `type BoardLabel`, `labelChipClass(color)`,
`TRELLO_COLOR_MAP` (mapeia `red_dark`/`orange`/… do export para hex do tema) e
`sortLabels(labels)`. **Nenhum componente define cor de etiqueta localmente** — foi exatamente o
defeito B-M20.

#### 2.4.2 Componentes de quadro — `…/empresas/[id]/dashboard/_components/`

| Arquivo | Responsabilidade |
|---|---|
| `board.tsx` | `"use client"`. Dono do `DndContext` (sensores `PointerSensor` + `KeyboardSensor`), `SortableContext` horizontal das colunas, `DragOverlay`, `announcements` em pt-BR para `aria-live`. Recebe `readOnly?: boolean` — com `true` **não monta o `DndContext`** (não basta desabilitar sensores: CA-17 exige que o cliente não veja controle de edição). Estado do quadro via `useOptimistic`; on-drop chama `moveCardAction` e reverte no erro. |
| `board-column.tsx` | Coluna droppable. Cabeçalho com nome, `card_count`, menu (renomear/arquivar/excluir). `kind === "SECTION"` renderiza divisor sem `useDroppable` e sem contador (CA-18). Rolagem vertical interna. |
| `board-card.tsx` | Card `useSortable`. `control_code`, título, chips via `board-labels.ts`, badge via `controlStatusBadgeClass` (reuso de `lib/control-status.ts`), checkbox de seleção em massa, menu "Mover para…". |
| `card-detail-panel.tsx` | **Extração pura**, sem lógica nova: o painel de detalhe que hoje vive dentro de `company-dashboard-client.tsx` (status, checklist, histórico, chat, notas) + o campo `description` novo. Extrair **antes** de trocar o agrupamento (mitigação de R1). |
| `move-card-menu.tsx` | Fallback sem arrasto (CA-15): `<select>` de coluna + `<select>` de posição, resolve para `prev_card_id`/`next_card_id` e chama a mesma `moveCardAction`. É também o caminho que os testes de integração usam, já que jsdom não simula arrasto. |
| `board.test.tsx` · `board-column.test.tsx` · `move-card-menu.test.tsx` | CA-14, CA-16, CA-18, CA-19, CA-21 / CA-18 / CA-15. |

#### 2.4.3 Rota nova do cliente — `frontend/app/private/client/quadro/`

> ⚠️ **Divergência do PRD §5.4.** O PRD listava `client-dashboard-client.tsx` como *modificação*.
> Esse arquivo renderiza `AuditControl` (`GET /api/v1/client/controls`) — domínio de auditoria,
> não de dashboard. O cliente **hoje não tem nenhuma visão do quadro da própria empresa**.
> Entregar U6/U7 é criar rota, não alterar a existente. `client-dashboard-client.tsx` fica
> **intocado**.

`page.tsx` (Server Component, `requireClient()`, resolve a empresa do usuário e chama
`getClientBoardAction`) · `actions.ts` (só leitura: `getClientBoardAction`,
`getCardDetailAction`) · `actions.test.ts` · `client-board-client.tsx` (monta `<Board readOnly>`
+ `<CardDetailPanel readOnly>`) · `loading.tsx` · `error.tsx` (F2).

O backend não precisa de rota nova: `GET /dashboard/companies/{id}/board` já usa
`get_company_with_access`, que aceita `user` e `sub-user`.

#### 2.4.4 Tela de etiquetas — `frontend/app/private/admin/dashboard-labels/`
`page.tsx` · `actions.ts` · `actions.test.ts` · `dashboard-labels-client.tsx` · `loading.tsx` ·
`error.tsx`. Estrutura idêntica a `app/private/admin/templates/` (F2, F3).

### 2.5 Backend — scripts e testes

#### `backend/scripts/import_trello_board.py`
`argparse`: `arquivo` posicional, `--template-name` (obrigatório), `--dry-run`.
Funções: `parse_board(raw) -> ParsedBoard` (pura, testável) · `split_control_code(name)` (regex
`^(\d+(?:\.\d+)*)\s+(.*)$`, 144 casos) · `clean_description(desc)` (remove `U+200C`, CA-25) ·
`is_section(list_name)` (sufixo `>>`) · `persist(db, parsed, template_name)` (idempotente por
nome de template) · `main()`.
Ignora `closed=true`, `actions[]`, `members[]`, `memberships[]`, `prefs`, `limits`,
`pluginData`. `position` **regenerada** com `n_keys_between`, nunca copiada de `pos`.

#### `backend/tests/test_fractional_index.py`
Docstring de módulo no padrão T5. Propriedades: `prev < key_between(prev, next) < next` para
todas as combinações de ponta; **1 000 inserções consecutivas no mesmo par** mantêm ordem
lexicográfica estrita e não estouram `String(64)` (CA-04); `n_keys_between` devolve `n` chaves
ordenadas; `ValueError` quando `prev >= next`.

#### `backend/tests/test_dashboard_board.py`
CA-05 (board ordenado e agrupado), CA-06 (`ContadorDeQueries` de `test_query_budget.py` provando
**1** `UPDATE`), CA-07 (404 cross-tenant no move), CA-08 (409/204 no delete), `SECTION` recusa
card (422), âncora inconsistente (422), coluna arquivada só aparece com `include_hidden=true`.

#### `backend/tests/test_dashboard_labels.py`
CRUD, 409 de nome duplicado, 409 de etiqueta em uso, `PUT /cards/{id}/labels` substituindo o
conjunto, e CA-12 (etiquetar **não** muda `status`).

#### `backend/tests/test_migration_board_backfill.py`

> ⚠️ **Divergência do PRD §7.1.** CA-02 e CA-03 estavam atribuídos a
> `test_migrations_smoke.py`, que faz **apenas análise estática** (`importlib`, nome ==
> `revision`, `single_head`) e nunca abre conexão. Ele não consegue verificar backfill.

Arquivo próprio: monta o schema **anterior** à migration em SQLite, popula dashboards/cards com
`sort_order` conhecido, executa as funções de backfill do módulo de migration e afirma:
nenhum card com `column_id IS NULL` num quadro que tinha cards (CA-02); ordem por `position`
idêntica à ordem por `sort_order` anterior (CA-02); `description` propagada do
`DashboardTemplateCard` de origem (CA-03).
`test_migrations_smoke.py` continua cobrindo a cadeia; o `upgrade`/`downgrade` real contra MySQL
8.4 permanece no job `migrations` do CI (CA-01).

---

## 3. Arquivos para Modificar

### 3.1 Backend — modelo

#### `backend/app/models/company_dashboard.py` — 🟡 Médio

| Linhas | Alteração | Porquê |
|---|---|---|
| `112-133` `DashboardTemplateCard` | + `template_column_id: Mapped[int \| None]` (FK `dashboard_template_columns.id`, `SET NULL`, index) e `position: Mapped[str]` `String(64)`. + relationship `template_column`. | O card de template precisa saber em que coluna nasce (§4.1.2 do PRD). `sort_order` (L129) **permanece** como campo histórico (B12). |
| `135-155` `Dashboard` | + `columns: Mapped[list["DashboardColumn"]] = relationship(back_populates="dashboard", cascade="all, delete-orphan")` | Sem o `cascade`, `delete_company_cascade` deixa colunas órfãs no SQLite dos testes, que não respeita `ON DELETE CASCADE` sem `PRAGMA foreign_keys=ON` — o mesmo motivo já documentado no comentário de `Company.dashboard` (L57-70). |
| `95-110` `DashboardTemplate` | + `columns` com `cascade="all, delete-orphan"` | Idem, para o template. |
| `157-169` `DashboardCard.__table_args__` | + `Index("ix_dashboard_cards_column_position", "column_id", "position")` | Cobre o `ORDER BY` do board (CA-13). |
| `após 191` (`hidden`) | + `column_id` (FK `dashboard_columns.id`, `SET NULL`, index), `position` `String(64)`, `description` `Text` nullable, `due_date` `DateTime(timezone=True)` nullable | `SET NULL` e não `CASCADE`: apagar coluna nunca apaga card — mesma escolha já feita para `category_id` (L181-185). |
| `199` `sort_order` | **Inalterado.** Comentário novo marcando-o como campo histórico substituído por `position`. | B12 — precedente de `tag` (L180). |
| `205-219` relationships | + `column: Mapped["DashboardColumn \| None"]` e `labels: Mapped[list["DashboardLabel"]] = relationship(secondary=dashboard_card_labels)` | `secondary` na tabela do Core declarada em `models/dashboard_board.py`. |

#### `backend/app/models/__init__.py` — 🟢 Baixo
Bloco de import (L9-20) e `__all__` (L22-42): acrescentar `DashboardColumn`,
`DashboardColumnKind`, `DashboardTemplateColumn`, `DashboardLabel`.
**Obrigatório** — `conftest.py:9` importa `app.models` justamente para popular
`Base.metadata`; sem isso as tabelas novas não são criadas nos testes.

### 3.2 Backend — API

#### `backend/app/api/v1/dashboard_cards.py` — 🟠 Alto (600 linhas, 2 suítes cobrindo)

| Linhas / função | Alteração | Porquê |
|---|---|---|
| `83-88` `_card_is_outdated` | Passa a comparar também `column_id` vs `origin.template_column_id` e `description` vs `origin.description`, além de `title`/`category_id`. | Um card que divergiu do template na coluna ou no texto normativo está tão desatualizado quanto um que divergiu no título. |
| `120-168` `list_cards_by_company` | `selectinload(DashboardCard.labels)` no `.options()` (L161-164); `ORDER BY` passa de `sort_order, id` para `position, id`; monta os 4 campos novos na saída. | Sem o `selectinload`, N+1 de etiquetas com 215 cards (B9). |
| `170-235` `create_card_for_company` | Aceita `column_id` e `description`; calcula `position` com `key_between` do fim da coluna, no lugar de `max(sort_order)+1` (L216-221); valida que a coluna é do mesmo dashboard e não é `SECTION`. | Card novo precisa nascer dentro de uma coluna. |
| `276-320` `bulk_update_company_cards` | Trata a operação `set_column` e valida `column_id` obrigatório para ela, no mesmo molde do `set_category` de L286-291. | Mover 50 cards de coluna em lote. |
| `322-419` `get_card_details` | `DashboardCardDetailOut` ganha `description`, `column_id`, `labels`. Carregar etiquetas junto do card. **Não mexer** na regra de `checklist`/`history` (L339-357) — é B-A28. | Cliente precisa ler a descrição do controle (U7). |
| `421-451` `update_card_status` | Só a construção de `DashboardCardWithCategoryOut` no retorno (L442-451), pelos campos novos. Regra inalterada. | Retrocompatibilidade do contrato. |

#### `backend/app/api/v1/dashboard_templates.py` — 🟡 Médio
- `39-48` `_card_to_out`: + `template_column_id`, `position`.
- `50-60` `_build_detail`: + `columns: list[TemplateColumnOut]`, ordenadas por `position`.
- `169-198` `create_dashboard_template_card` e `219+` `update_dashboard_template_card`: aceitam
  `template_column_id`; `position` calculada por `key_between`.
- **Rotas novas** no mesmo router: `GET/POST /{template_id}/columns`,
  `PATCH/DELETE /{template_id}/columns/{column_id}`, `PATCH …/columns/{column_id}/move`.

#### `backend/app/api/v1/router.py` — 🟢 Baixo
+ 2 linhas de `import` e 2 de `include_router` (`dashboard_board_router`,
`dashboard_labels_router`). **Ordem importa**: `dashboard_board_router` depois de
`dashboard_cards_router` — ambos usam `prefix="/dashboard"` e o FastAPI resolve por ordem de
registro; `/dashboard/cards/{card_id}` (existente) não pode ser sombreado por um path novo.

### 3.3 Backend — serviços e núcleo

#### `backend/app/services/dashboard_template_admin.py` — 🟠 Alto (coração da idempotência)

| Linhas / função | Alteração | Porquê |
|---|---|---|
| `340-346` `ApplyTemplateOutcome` | + `columns_created_count: int` | "0 cards criados" com 25 colunas criadas não pode se parecer com "não fez nada" — mesma razão de `adopted_count` (L339-346, B-A24). |
| `348-451` `apply_template_to_company` | **Fase nova antes do loop de cards (antes de L378):** casar `DashboardTemplateColumn` → `DashboardColumn` por `origin_template_column_id`, criar as faltantes. No loop de cards (L410-441): resolver `column_id` pela coluna correspondente, copiar `description`, gerar `position` com `n_keys_between` no lugar de `next_sort += 1` (L437). | A idempotência de coluna repousa na mesma `UniqueConstraint` que a de card (R2). Copiar `description` corrige o defeito de origem. |
| `410-441` bloco de criação | Deixa de gravar `sort_order=next_sort`; grava `position`. `sort_order` mantido com valor incremental para compatibilidade. | Transição sem quebrar consumidor antigo. |
| `459+` `bulk_update_cards` | + ramo `elif operation == "set_column":` valida a coluna (mesmo dashboard, não `SECTION`), atribui `column_id` e uma `position` no fim da coluna destino. | Operação em lote pedida por O.4. |
| `271-297` / `299-321` `add_template_card` / `update_template_card` | + parâmetro `template_column_id`, validado contra o mesmo `template_id`. | Impede vincular card ao template A com coluna do template B. |
| **Novas funções** no mesmo arquivo | `add_template_column`, `update_template_column`, `delete_template_column` (409 se houver `DashboardTemplateCard` vinculado — molde de `delete_template_card`, L323-337), `move_template_column`. | Coesão: CRUD de template mora aqui. |

#### `backend/app/services/dashboard_builder.py` — 🟡 Médio
`31-83` `create_company_dashboard_from_template`: entre a criação do `Dashboard` (L48-53) e o
loop de cards (L68-80), inserir a criação das `DashboardColumn` a partir de
`DashboardTemplateColumn`, guardando o mapa `template_column_id → column_id`. O loop passa a
gravar `column_id`, `description` e `position`. Retorno `tuple[Company, Dashboard, int]`
**inalterado** — `admin_onboarding.py` o consome posicionalmente.

#### `backend/app/core/policy.py` — 🟢 Baixo
- `23-37` (enum `Action`): + `MANAGE_COLUMN`, `MOVE_CARD`, `MANAGE_LABEL`, com comentário
  citando o PRD §4.4.
- `42-56` (`ALLOWED_ROLES`): + 3 entradas `frozenset({"admin"})`.

> `test_authorization_matrix.py:192-193` (`test_every_action_has_an_explicit_decision`) é
> parametrizado sobre `list(Action)` — as 3 ações novas entram na cobertura **automaticamente**.
> Esquecer a linha em `ALLOWED_ROLES` reprova o teste com `KeyError`, que é o comportamento
> desejado.

#### `backend/app/core/access.py` — 🟢 Baixo
+ `get_column_with_access(db, column_id, current_user) -> DashboardColumn` após
`get_company_with_access` (L63+), com o mesmo `JOIN` até `companies`, o mesmo uso de
`resolve_owner_user_id` (L30) e o mesmo 404 genérico.

#### `backend/app/services/company_admin.py` — 🟡 Médio
`304-420` `delete_company_cascade`: **verificar**, não necessariamente alterar. Com
`Dashboard.columns` marcado `cascade="all, delete-orphan"` (§3.1), o `db.delete(company)` de L400
já remove as colunas via ORM. A alteração obrigatória é o `CompanyDeletionSummaryData`, se ele
enumerar entidades removidas — conferir e acrescentar a contagem de colunas se for o caso.

### 3.4 Backend — schemas

| Arquivo | Linhas | Alteração |
|---|---|---|
| `app/schemas/dashboard_runtime.py` | `8-17` `DashboardCardCreate` | + `column_id: int \| None`, `description: str \| None = Field(default=None, max_length=20000)`. 20 000 porque as descrições reais são texto normativo longo (PRD §1.1). |
| idem | `45-54` `DashboardCardDetailOut` | + `description`, `column_id`, `labels: list[LabelRef]` |
| `app/schemas/dashboard_templates.py` | `27-34` `DashboardTemplateCardOut` | + `template_column_id`, `position` |
| idem | `60-66` / `67-72` `DashboardTemplateCardCreate` / `Update` | + `template_column_id: int \| None` |
| idem | `85-91` `BulkCardOperation` | `Literal[...]` ganha `"set_column"`; + `column_id: int \| None` |
| idem | `78-83` `ApplyTemplateResult` | + `columns_created_count: int` |
| idem | `97-115` `DashboardCardWithCategoryOut` | + `column_id`, `position`, `description`, `labels: list[LabelRef]` |

### 3.5 Backend — scripts e testes

| Arquivo | Alteração |
|---|---|
| `backend/scripts/seed_dashboard_templates.py` | `main()` (L20) e o bloco `DashboardTemplateCard(` (L64): criar `DashboardTemplateColumn` antes dos cards e vincular. Sem isso, todo ambiente novo nasce com template sem coluna. |
| `backend/tests/conftest.py` | Após a fixture `dashboard` (L184-192): fixtures `dashboard_column`, `board_com_3_colunas`, `etiquetas`. A fixture `dashboard_card` (L193-206) passa a preencher `column_id` e `position` — `position` é `NOT NULL`. |
| `backend/tests/test_authorization_matrix.py` | `WRITE_ENDPOINTS` (L20-53): + as 8 rotas de escrita novas com `forbidden_roles=["user","sub-user"]`. `READ_ENDPOINTS` (L123-136): + `GET …/board` com `forbidden_roles=[]` (leitura permitida a todos) — registrar a decisão explicitamente é o que M-23 exige. |
| `backend/tests/test_query_budget.py` | + teste de teto para `GET …/board` parametrizado com **5 e 20 colunas** sob o mesmo teto, usando `ContadorDeQueries` (L~30). Duas quantidades sob um teto único é o que prova custo constante; uma só pode passar por acaso (docstring do arquivo). |
| `backend/tests/test_dashboard_cards.py` | Ajustar asserções de payload pelos campos novos; ordenação esperada passa de `sort_order` para `position`. |
| `backend/tests/test_dashboard_templates.py` | CA-09 (aplicar 2× cria colunas na 1ª e nada na 2ª) e CA-10 (`description` copiada). |

### 3.6 Frontend

#### `…/empresas/[id]/dashboard/company-dashboard-client.tsx` — 🔴 Refatoração maior (890 linhas)

**Executar em dois commits** (mitigação de R1):
*Commit A* — extrair o painel de detalhe (L~700-890 do JSX + `atualizarStatus` L347-365 +
`alternarChecklist` L367-387) para `_components/card-detail-panel.tsx`, sem mudar comportamento.
*Commit B* — trocar o agrupamento.

| Linhas | Alteração |
|---|---|
| `28` `UNCATEGORIZED_KEY` | **Remover** — substituído pelo bucket `uncolumned` do `BoardOut`. |
| `39-44` `type CardGroup` | **Remover** — o agrupamento vem pronto do servidor (D-5). |
| `54-79` bloco de estado | `cards` → `board: BoardOut`; `collapsedCategories` (L69-71) → `collapsedColumns`; + `useOptimistic` para o quadro. `busca`, `showHidden`, `selectedCardIds`, `outdatedFromLastApply`, `feedback`, `isPending` **permanecem**. |
| `125-162` `groups` (`useMemo`) | **Remover inteiro** (38 linhas). É a lógica que migra para `dashboard_board.py::get_board`. |
| `164-171` `toggleCategoryCollapse` | Renomear para `toggleColumnCollapse`, chave passa a ser `column.id`. |
| `182-193` `toggleGroupSelection` | Passa a receber `BoardColumnOut`. |
| `195-199` `refreshCards` | Passa a chamar `getBoardAction`. |
| `201-237` `runBulk` | + operação `set_column`. |
| `458-703` (render dos grupos) | **Substituir** por `<Board … />`. ~245 linhas de JSX saem. |
| `239-346` (aplicar template, criar card, criar categoria, trocar categoria) | **Permanecem**, com `+ Adicionar card` passando a receber `column_id`. |

#### `…/empresas/[id]/dashboard/actions.ts` — 🟢 Baixo (aditivo)
Todas as actions atuais permanecem. + `getBoardAction`, `createColumnAction`,
`updateColumnAction`, `moveColumnAction`, `deleteColumnAction`, `moveCardAction`,
`updateCardAction`, `setCardLabelsAction`, `listLabelsAction` — todas com
`await requireAdmin()` + `getAccessToken()` + `callBackend` + retorno discriminado (F4, F5, F6).
`CompanyDashboardCardListItem` ganha `column_id`, `position`, `description`, `labels`.

> `moveCardAction` **não** chama `revalidatePath` (PRD §4.7): revalidar recarregaria 215 cards a
> cada arrasto e anularia o `useOptimistic`. `createColumnAction` / `deleteColumnAction` /
> `applyTemplateToCompanyAction` **chamam**.

#### `…/empresas/[id]/dashboard/page.tsx` — 🟢 Baixo
`Promise.all` (L18-23): `listCardsForCompanyAction` → `getBoardAction`; + `listLabelsAction`.
`firstVisibleCard` (L26-29) passa a varrer `board.columns.flatMap(c => c.cards)`.

#### `frontend/app/private/admin/actions.ts` — 🟢 Baixo
`143-153` `type DashboardCardDetail`: + `description: string | null`,
`column_id: number | null`, `labels: BoardLabel[]`. `getCardDetailAction` (L155-163) inalterada.

#### `frontend/app/private/admin/templates/templates-client.tsx` + `actions.ts` — 🟡 Médio
`25-37` `CardFormState`: + `templateColumnId`. `186-240` (bloco de card): + seletor de coluna.
+ seção de gestão de colunas do template (criar/renomear/reordenar/excluir).
`actions.ts`: + 4 actions de coluna de template.

#### `frontend/app/globals.css` — 🟢 Baixo
Dentro do `@layer components` existente (L27-70), após `.status-chip` (L66):
`.board-scroller` (rolagem horizontal, `overflow-x:auto`, sem estourar o `body` — CA-20),
`.board-column` (largura fixa, rolagem vertical interna), `.board-card`, `.label-chip`.
Tokens de cor vêm do `:root` já existente (L3-9).

#### `.gitignore` — 🟢 Baixo · **primeira fase, não a última**
+ `trello*.json` (CA-30, R6). O arquivo tem 12 nomes completos de membros e IDs de organização
do Trello, e hoje está *untracked* na raiz. Nada mais nesta entrega depende disso, e por isso
mesmo é o que se esquece.

#### `docs/backlog.md` · `docs/roadmap.md` · `docs/relatorio_funcionalidades.md` · `docs/index.md`
Registrar a entrega e abrir os itens D-2 (`NAO_APLICAVEL` como status) e D-4 (anexos em card)
como backlog (CA-31).

---

## 4. Dependências

### 4.1 Novas — frontend

| Pacote | Versão | Escopo | Papel |
|---|---|---|---|
| `@dnd-kit/core` | `6.3.1` | `dependencies` | `DndContext`, sensores, `DragOverlay` |
| `@dnd-kit/sortable` | `10.0.0` | `dependencies` | `SortableContext` / `useSortable` — colunas e cards |
| `@dnd-kit/modifiers` | `9.0.0` | `dependencies` | `restrictToHorizontalAxis` para o arrasto de coluna |

**Regras de instalação (não negociáveis):**
1. **Versões fixas, sem `^`** — mesmo regime do `slowapi==0.1.9` / `aiofiles==23.2.1` do backend.
2. `package-lock.json` commitado no mesmo commit — o job `frontend` do CI roda `npm ci`, que
   falha se o lock divergir do `package.json`.
3. `@dnd-kit/utilities` entra como transitiva de `sortable`; **não declarar** explicitamente.
4. Rodar `npm audit --omit=dev` antes de abrir o PR (R4).

Estas são as **primeiras** dependências de UI do projeto — hoje `dependencies` tem só `jose`,
`next`, `react`, `react-dom`, `server-only`.

### 4.2 Novas — backend

**Nenhuma.** O índice fracionário é implementado em `app/services/fractional_index.py` (~60
linhas, sem dependência externa) justamente para não acrescentar superfície ao `pip-audit`, que
já carrega uma exceção justificada (`PYSEC-2026-1325`). O importador do Trello usa só `json`,
`argparse` e `re` da biblioteca padrão.

### 4.3 Sem alteração

`requirements.txt` · `docker-compose.yml` · `.github/workflows/ci.yml` (os 4 jobs cobrem o
escopo novo sem mudança: `pytest` pega os testes novos, `npm ci` resolve o `@dnd-kit`,
`alembic upgrade/downgrade` valida a migration, `gitleaks` varre o histórico).

### 4.4 Avaliadas e rejeitadas

| Pacote | Motivo da rejeição |
|---|---|
| `react-beautiful-dnd` | Arquivada em 2024; quebra no StrictMode do React 19 |
| `@hello-pangea/dnd` | Viável, mas sem `KeyboardSensor` de fábrica no nível que CA-14 exige |
| `fractional-indexing` (npm) | O cálculo é **do servidor** por decisão de contrato (PRD §4.2) — o frontend nunca gera chave |
| Biblioteca Python de LexoRank | Nenhuma mantida com adoção relevante; 60 linhas próprias custam menos que a dependência |
