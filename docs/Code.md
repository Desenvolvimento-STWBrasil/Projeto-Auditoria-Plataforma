# Guia de Implementação Manual — Quadro Kanban de Colunas e Cards

| Campo | Valor |
|---|---|
| **Documento** | Guia de Implementação Manual (derivado de [`Spec.md`](Spec.md), que traduz o [`PRD.md`](PRD.md) v1.0) |
| **Data** | 2026-08-27 |
| **Branch base** | `fix/audit-repository-refactor-and-regressions` · HEAD `754ed58` |
| **Head de migrations antes desta entrega** | `b7c02e91d4a5` |
| **Head de migrations depois desta entrega** | `c8f1a3e57b90` |
| **Modo de execução** | **100 % manual.** Nenhum script gera código; o desenvolvedor cria/edita cada arquivo à mão, na ordem das fases |

> **Como usar este guia.** As fases estão em ordem de dependência: a Fase N só compila
> depois da Fase N−1. Cada arquivo aparece com **(1) Ação Manual** — o que digitar no
> terminal / qual arquivo abrir — e **(2) Código Fonte Completo** — o conteúdo integral,
> pronto para copiar. Onde o arquivo é *modificado*, o código apresentado é o **arquivo
> inteiro depois da modificação**, não um patch: não há `// ... resto do código`.

---

## Sumário

- [1. Visão Geral e Pré-requisitos](#1-visão-geral-e-pré-requisitos)
- [2. Estrutura de Diretórios](#2-estrutura-de-diretórios)
- [3. Passo a Passo da Implementação Manual](#3-passo-a-passo-da-implementação-manual)
  - [Fase 0 — Higiene do repositório](#fase-0--higiene-do-repositório)
  - [Fase 1 — Índice fracionário](#fase-1--índice-fracionário)
  - [Fase 2 — Modelo, migration e backfill](#fase-2--modelo-migration-e-backfill)
  - [Fase 3 — Núcleo e serviços](#fase-3--núcleo-e-serviços)
  - [Fase 4 — Schemas e rotas](#fase-4--schemas-e-rotas)
  - [Fase 5 — Testes de backend](#fase-5--testes-de-backend)
  - [Fase 6 — Fundação do frontend](#fase-6--fundação-do-frontend)
  - [Fase 7 — Quadro do admin](#fase-7--quadro-do-admin)
  - [Fase 8 — Quadro do cliente](#fase-8--quadro-do-cliente)
  - [Fase 9 — Tela de etiquetas](#fase-9--tela-de-etiquetas)
  - [Fase 10 — Colunas de template](#fase-10--colunas-de-template)
  - [Fase 11 — Importador do Trello e seed](#fase-11--importador-do-trello-e-seed)
  - [Fase 12 — Documentação](#fase-12--documentação)
- [4. Checklist final de verificação](#4-checklist-final-de-verificação)
- [5. Divergências assumidas em relação à Spec](#5-divergências-assumidas-em-relação-à-spec)

---

## 1. Visão Geral e Pré-requisitos

### 1.1 O que esta entrega faz

Acrescenta ao domínio de cards já existente (`DashboardCard`, com status, checklist,
histórico, chat e notas) quatro conceitos novos:

| Conceito | Entidade nova | Efeito visível |
|---|---|---|
| **Coluna do quadro** | `DashboardColumn` (por `dashboard_id`) | O dashboard da empresa vira um quadro Kanban horizontal |
| **Posição manual** | `DashboardCard.position` (`String(64)`, índice fracionário) | Arrastar card/coluna com **1 `UPDATE`** por movimento |
| **Descrição do controle** | `DashboardCard.description` (`Text`) | O texto normativo passa a existir no card (hoje é descartado por `apply_template_to_company`) |
| **Etiqueta de criticidade** | `DashboardLabel` + M:N `dashboard_card_labels` | Chips de criticidade no card, ortogonais ao status |

A entrega é **aditiva**: nenhuma rota existente muda de contrato (só ganha campos), nenhum
teste existente é removido.

### 1.2 Requisitos de ambiente

| Item | Versão | Verificação |
|---|---|---|
| Python | **3.12** | `python --version` |
| Node.js | **20 LTS** | `node --version` |
| npm | 10+ | `npm --version` |
| MySQL | **8.4** (via Docker) | `docker compose ps` na raiz |
| Docker / Docker Compose | v2 | `docker compose version` |
| Git | 2.40+ | `git --version` |

O backend roda os testes em **SQLite em memória** (`backend/tests/conftest.py`), então
`pytest` **não** exige MySQL no ar. O MySQL é necessário apenas para exercitar a migration
localmente do mesmo jeito que o job `migrations` do CI faz.

### 1.3 Variáveis de ambiente

Nenhuma variável nova é introduzida por esta entrega. Confirme que os dois arquivos já
existem antes de começar (ambos são *gitignored*):

**`backend/.env`** — copiado de `backend/.env.example`. As chaves relevantes:

```dotenv
DATABASE_URL=mysql+pymysql://auditoria_app:SENHA@127.0.0.1:3307/auditoria
JWT_SECRET=<64 caracteres hex — idêntico ao do frontend>
JWT_ALGORITHM=HS256
```

**`frontend/.env.local`**:

```dotenv
BACKEND_API_URL=http://127.0.0.1:8000
JWT_SECRET=<o MESMO valor de backend/.env>
JWT_ALGORITHM=HS256
```

### 1.4 Dependências a instalar

**Backend — nenhuma dependência nova.** O índice fracionário é implementado em
`app/services/fractional_index.py` (~140 linhas, só biblioteca padrão) justamente para não
acrescentar superfície ao `pip-audit`, que já carrega uma exceção justificada
(`PYSEC-2026-1325`). O importador do Trello usa só `json`, `argparse` e `re`.

**Frontend — três dependências novas, em versão fixa (sem `^`):**

```bash
cd frontend
npm install --save-exact @dnd-kit/core@6.3.1 @dnd-kit/sortable@10.0.0 @dnd-kit/modifiers@9.0.0
```

Regras não negociáveis:

1. `--save-exact` — mesmo regime do `slowapi==0.1.9` / `aiofiles==23.2.1` do backend.
2. `package-lock.json` commitado **no mesmo commit** — o job `frontend` do CI roda
   `npm ci`, que falha se o lock divergir do `package.json`.
3. `@dnd-kit/utilities` entra como transitiva de `sortable`; **não declarar** explicitamente.
4. Rodar `npm audit --omit=dev` antes de abrir o PR.

### 1.5 Comandos de verificação usados ao longo do guia

```bash
# Backend (a partir de backend/)
ruff check app
pytest --cov=app --cov-report=term-missing
alembic upgrade head && alembic downgrade base && alembic upgrade head
alembic heads          # tem de listar exatamente 1

# Frontend (a partir de frontend/)
npm run lint
npx next typegen && npx tsc --noEmit
npm run test
npm run build
```

---

## 2. Estrutura de Diretórios

`[+]` criar · `[~]` modificar · sem marca = contexto inalterado

```
Developer/
├── [~] .gitignore
│
├── backend/
│   ├── alembic/
│   │   ├── [~] env.py                                       # registrar o módulo de models novo
│   │   └── versions/
│   │       └── [+] c8f1a3e57b90_add_dashboard_columns_and_labels.py
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── [+] dashboard_board.py
│   │   │   ├── [+] dashboard_labels.py
│   │   │   ├── [~] dashboard_cards.py
│   │   │   ├── [~] dashboard_templates.py
│   │   │   └── [~] router.py
│   │   ├── core/
│   │   │   ├── [~] access.py
│   │   │   └── [~] policy.py
│   │   ├── models/
│   │   │   ├── [+] dashboard_board.py
│   │   │   ├── [~] company_dashboard.py
│   │   │   └── [~] __init__.py
│   │   ├── schemas/
│   │   │   ├── [+] dashboard_board.py
│   │   │   ├── [+] dashboard_labels.py
│   │   │   ├── [~] dashboard_runtime.py
│   │   │   └── [~] dashboard_templates.py
│   │   └── services/
│   │       ├── [+] fractional_index.py
│   │       ├── [+] dashboard_board.py
│   │       ├── [~] dashboard_template_admin.py
│   │       └── [~] dashboard_builder.py
│   ├── scripts/
│   │   ├── [+] import_trello_board.py
│   │   └── [~] seed_dashboard_templates.py
│   └── tests/
│       ├── [+] test_fractional_index.py
│       ├── [+] test_dashboard_board.py
│       ├── [+] test_dashboard_labels.py
│       ├── [+] test_migration_board_backfill.py
│       ├── [~] conftest.py
│       ├── [~] test_authorization_matrix.py
│       ├── [~] test_query_budget.py
│       ├── [~] test_dashboard_cards.py
│       └── [~] test_dashboard_templates.py
│
├── frontend/
│   ├── app/
│   │   ├── [~] globals.css
│   │   └── private/
│   │       ├── admin/
│   │       │   ├── [~] actions.ts
│   │       │   ├── dashboard-labels/
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
│   │       │   │   ├── [~] company-dashboard-client.tsx
│   │       │   │   ├── [~] actions.ts
│   │       │   │   ├── [~] actions.test.ts
│   │       │   │   └── [~] page.tsx
│   │       │   └── templates/
│   │       │       ├── [~] templates-client.tsx
│   │       │       ├── [~] actions.ts
│   │       │       └── [~] actions.test.ts
│   │       └── client/
│   │           └── quadro/
│   │               ├── [+] page.tsx
│   │               ├── [+] actions.ts
│   │               ├── [+] actions.test.ts
│   │               ├── [+] client-board-client.tsx
│   │               ├── [+] loading.tsx
│   │               └── [+] error.tsx
│   ├── lib/
│   │   ├── [+] board-labels.ts
│   │   └── [+] board-labels.test.ts
│   ├── [~] package.json
│   └── [~] package-lock.json
│
└── docs/
    ├── [~] backlog.md · [~] roadmap.md
    ├── [~] relatorio_funcionalidades.md · [~] index.md
    ├── PRD.md · Spec.md
    └── [+] Code.md          ← este arquivo
```

**Comandos de criação de diretórios** (a partir da raiz `Developer/`):

```bash
mkdir -p "frontend/app/private/admin/empresas/[id]/dashboard/_components"
mkdir -p frontend/app/private/admin/dashboard-labels
mkdir -p frontend/app/private/client/quadro
```

---

## 3. Passo a Passo da Implementação Manual

### Fase 0 — Higiene do repositório

> **Por que é a primeira fase e não a última (R6/CA-30).** O arquivo
> `trello exemplo para ser implementado.json` está hoje *untracked* na raiz e contém **12
> nomes completos de membros e IDs de organização do Trello** — dado pessoal sob LGPD, num
> repositório que já teve incidente de segredos no histórico. Nada mais nesta entrega
> depende deste passo, e é exatamente por isso que ele é o que se esquece.

---

#### `.gitignore`

##### 1. Ação Manual

Abra o arquivo `.gitignore` na **raiz** do repositório (`Developer/.gitignore`) e substitua
seu conteúdo pelo bloco abaixo. Depois confirme que o export do Trello está fora do índice:

```bash
git check-ignore -v "trello exemplo para ser implementado.json"
# deve imprimir: .gitignore:NN:trello*.json  trello exemplo para ser implementado.json

git ls-files --error-unmatch "trello exemplo para ser implementado.json" 2>/dev/null \
  && echo "ATENÇÃO: o arquivo ESTÁ rastreado — rode: git rm --cached 'trello exemplo para ser implementado.json'" \
  || echo "OK: fora do índice"
```

##### 2. Código Fonte Completo

```gitignore
# Segredos do docker-compose.yml da raiz (MYSQL_PASSWORD, JWT_SECRET,
# ADMIN_EMAIL, ADMIN_PASSWORD — ver BLOCO H / item H do plano de
# implementação). backend/.env e frontend/.env.local já são ignorados
# pelos .gitignore de cada subprojeto; este cobre o .env da raiz.
.env
.env.*
!.env.example

# Exports de quadro do Trello (CA-30 / R6 do PRD do Quadro Kanban).
# O export de referência traz 12 nomes completos de membros e o ID da
# organização — dado pessoal sob LGPD. O importador
# (backend/scripts/import_trello_board.py) lê o arquivo do disco local do
# operador; ele NUNCA entra no repositório.
trello*.json
Trello*.json

# Sistema operacional
.DS_Store
Thumbs.db

# Editores/IDEs
.vscode/
.idea/
```

---

### Fase 1 — Índice fracionário

> **Bloqueia tudo.** A migration, os serviços, o importador e o seed dependem deste módulo.
> Ele é **puro** — sem `Session`, sem I/O, sem import de `app.*` — e é isso que permite à
> migration importá-lo sem carregar a aplicação inteira.

---

#### `backend/app/services/fractional_index.py`

##### 1. Ação Manual

Crie o arquivo `backend/app/services/fractional_index.py`.

##### 2. Código Fonte Completo

```python
from __future__ import annotations

"""
Índice fracionário em `String` — a ordenação manual de cards e colunas do
quadro (D-3 do PRD).

O problema que resolve: com `sort_order: Integer`, arrastar um card para o
meio da coluna obriga a reescrever o `sort_order` de todos os seguintes —
`O(n)` UPDATEs por arrasto e uma janela de corrida entre dois admins
arrastando ao mesmo tempo. Com chave fracionária, entre "a0" e "a1" sempre
cabe "a0V"; entre "a0" e "a0V" cabe "a0F". **Um UPDATE por arrasto,
sempre**, sem rebalanceamento.

Porte direto do algoritmo de `rocicorp/fractional-indexing` (o mesmo que
Figma e Linear usam), alfabeto base-62 em ordem ASCII crescente — a mesma
ordem que `ORDER BY position` dá no MySQL com collation binária ou
`utf8mb4_bin`-compatível para os caracteres [0-9A-Za-z].

**Anatomia de uma chave.** Ela tem uma parte INTEIRA e uma parte
FRACIONÁRIA:

    "a0"     -> inteiro "a0",  fração ""
    "a0V"    -> inteiro "a0",  fração "V"
    "b00"    -> inteiro "b00", fração ""

O primeiro caractere codifica o comprimento da parte inteira ('a' = 2,
'b' = 3, …, 'Z' = 2, 'Y' = 3, …). É esse truque que faz **acrescentar no
fim** — a operação mais comum, um card novo — custar comprimento
constante: "a0", "a1", …, "az" (62 chaves), depois "b00" … "bzz" (3 844
chaves), e assim por diante. Um quadro de 215 cards nunca passa de 3
caracteres se for só preenchido em ordem.

**Limite conhecido e MEDIDO.** Inserir repetidamente no MESMO intervalo
(sempre logo depois da mesma âncora) gasta ~1 caractere a cada 5
inserções. Com `position VARCHAR(64)` isso suporta exatamente **310
inserções consecutivas no mesmo intervalo** antes de estourar a coluna —
número medido, não estimado, e fixado como barreira em
`tests/test_fractional_index.py::test_o_pior_caso_cabe_em_64_caracteres`.

Os padrões de uso reais ficam ordens de grandeza abaixo disso (também
medidos, e cobertos por teste):

| Padrão | 1 000 operações | Comprimento máximo |
|---|---|---|
| Acrescentar no fim (criar card) | `key_between(último, None)` | **3** |
| Gerar em lote (`n_keys_between`) | aplicar template / importar | **3** |
| Arrastar para posição arbitrária | inserção aleatória | **7** |
| Arrastar sempre para o mesmo ponto | patológico | 169 (estoura) |

Não é um limite teórico do algoritmo, é o limite do TIPO da coluna. Se
algum dia for atingido em produção, a correção é alargar `position`, não
trocar o índice fracionário.
"""

BASE_62_DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

#: Chave da primeira inserção numa lista vazia.
INITIAL_KEY = "a0"

#: Tamanho da coluna `position` (`String(64)`) — ver a docstring do módulo.
MAX_KEY_LENGTH = 64

#: Menor parte inteira representável; nenhuma chave válida é igual a ela,
#: porque não haveria como gerar nada antes.
SMALLEST_INTEGER = "A" + BASE_62_DIGITS[0] * 26


def _integer_length(head: str) -> int:
    """Comprimento total da parte inteira, deduzido do primeiro caractere."""
    if "a" <= head <= "z":
        return ord(head) - ord("a") + 2
    if "A" <= head <= "Z":
        return ord("Z") - ord(head) + 2
    raise ValueError(f"Cabeça de chave inválida: {head!r}")


def _validate_integer(value: str) -> None:
    if len(value) != _integer_length(value[0]):
        raise ValueError(f"Parte inteira inválida: {value!r}")


def _integer_part(key: str) -> str:
    if not key:
        raise ValueError("Chave de ordenação vazia")
    length = _integer_length(key[0])
    if length > len(key):
        raise ValueError(f"Chave de ordenação inválida: {key!r}")
    return key[:length]


def _validate_key(key: str) -> None:
    """
    Uma chave é válida quando: não é o menor inteiro possível; tem parte
    inteira completa; e a parte fracionária não termina em '0'.

    A regra do '0' final não é estética. Se a fração pudesse terminar em
    '0', existiriam duas grafias para o mesmo ponto ("a0V" e "a0V0") e o
    cálculo do ponto médio deixaria de ser fechado.
    """
    if key == SMALLEST_INTEGER:
        raise ValueError(f"Chave de ordenação inválida: {key!r}")
    integer = _integer_part(key)
    fraction = key[len(integer) :]
    if fraction.endswith(BASE_62_DIGITS[0]):
        raise ValueError(f"Chave de ordenação inválida (fração termina em '0'): {key!r}")


def _increment_integer(value: str) -> str | None:
    """Próxima parte inteira, ou `None` se o espaço acabou (`z…`)."""
    _validate_integer(value)
    head, digits = value[0], list(value[1:])

    carry = True
    for i in range(len(digits) - 1, -1, -1):
        if not carry:
            break
        position = BASE_62_DIGITS.index(digits[i]) + 1
        if position == len(BASE_62_DIGITS):
            digits[i] = BASE_62_DIGITS[0]
        else:
            digits[i] = BASE_62_DIGITS[position]
            carry = False

    if not carry:
        return head + "".join(digits)

    if head == "Z":
        return "a" + BASE_62_DIGITS[0]
    if head == "z":
        return None

    next_head = chr(ord(head) + 1)
    if next_head > "a":
        digits.append(BASE_62_DIGITS[0])
    else:
        digits.pop()
    return next_head + "".join(digits)


def _decrement_integer(value: str) -> str | None:
    """Parte inteira anterior, ou `None` se o espaço acabou (`A…`)."""
    _validate_integer(value)
    head, digits = value[0], list(value[1:])

    borrow = True
    for i in range(len(digits) - 1, -1, -1):
        if not borrow:
            break
        position = BASE_62_DIGITS.index(digits[i]) - 1
        if position == -1:
            digits[i] = BASE_62_DIGITS[-1]
        else:
            digits[i] = BASE_62_DIGITS[position]
            borrow = False

    if not borrow:
        return head + "".join(digits)

    if head == "a":
        return "Z" + BASE_62_DIGITS[-1]
    if head == "A":
        return None

    previous_head = chr(ord(head) - 1)
    if previous_head < "Z":
        digits.append(BASE_62_DIGITS[-1])
    else:
        digits.pop()
    return previous_head + "".join(digits)


def _midpoint(a: str, b: str | None) -> str:
    """
    Menor fração estritamente entre `a` e `b`, onde ambas são partes
    FRACIONÁRIAS (sem parte inteira). `b is None` significa "1,0".

    O laço de prefixo comum preenche `a` com '0' à direita — é o que
    permite comparar "" com "0V" corretamente (prefixo comum de 1
    caractere) em vez de devolver "0", que terminaria em zero e violaria
    a invariante de `_validate_key`.
    """
    if b is not None and a >= b:
        raise ValueError(f"{a!r} >= {b!r}")
    if a.endswith(BASE_62_DIGITS[0]) or (b is not None and b.endswith(BASE_62_DIGITS[0])):
        raise ValueError("Fração não pode terminar em '0'")

    if b is not None:
        common = 0
        while common < len(b) and (a[common] if common < len(a) else BASE_62_DIGITS[0]) == b[common]:
            common += 1
        if common > 0:
            return b[:common] + _midpoint(a[common:], b[common:])

    digit_a = BASE_62_DIGITS.index(a[0]) if a else 0
    digit_b = BASE_62_DIGITS.index(b[0]) if b else len(BASE_62_DIGITS)

    if digit_b - digit_a > 1:
        return BASE_62_DIGITS[(digit_a + digit_b) // 2]

    if b is not None and len(b) > 1:
        return b[:1]

    return BASE_62_DIGITS[digit_a] + _midpoint(a[1:], None)


def key_between(prev: str | None, next: str | None) -> str:
    """
    Chave estritamente entre `prev` e `next`. `None` representa a ponta da
    lista (`prev=None` = início, `next=None` = fim).

    Levanta `ValueError` se `prev >= next` — âncoras fora de ordem são um
    erro do chamador, nunca um caso a tolerar em silêncio: tolerá-lo
    produziria uma chave que quebra a ordenação de todo o quadro.
    """
    if prev is not None:
        _validate_key(prev)
    if next is not None:
        _validate_key(next)
    if prev is not None and next is not None and prev >= next:
        raise ValueError(f"Âncoras fora de ordem: {prev!r} >= {next!r}")

    if prev is None:
        if next is None:
            return INITIAL_KEY
        integer_b = _integer_part(next)
        fraction_b = next[len(integer_b) :]
        if integer_b == SMALLEST_INTEGER:
            return integer_b + _midpoint("", fraction_b)
        if integer_b < next:
            return integer_b
        decremented = _decrement_integer(integer_b)
        if decremented is None:
            raise ValueError("Não há espaço de ordenação antes desta chave")
        return decremented

    if next is None:
        integer_a = _integer_part(prev)
        fraction_a = prev[len(integer_a) :]
        incremented = _increment_integer(integer_a)
        if incremented is None:
            return integer_a + _midpoint(fraction_a, None)
        return incremented

    integer_a = _integer_part(prev)
    fraction_a = prev[len(integer_a) :]
    integer_b = _integer_part(next)
    fraction_b = next[len(integer_b) :]

    if integer_a == integer_b:
        return integer_a + _midpoint(fraction_a, fraction_b)

    incremented = _increment_integer(integer_a)
    if incremented is None:
        raise ValueError("Não há espaço de ordenação depois desta chave")
    if incremented < next:
        return incremented
    return integer_a + _midpoint(fraction_a, None)


def n_keys_between(prev: str | None, next: str | None, n: int) -> list[str]:
    """
    `n` chaves ordenadas entre as âncoras — usada pelos backfills da
    migration, pelo importador do Trello e por `apply_template_to_company`.

    Divide o intervalo ao meio recursivamente em vez de encadear `n`
    chamadas a `key_between`: encadear faria a n-ésima chave crescer
    linearmente em comprimento, enquanto a divisão binária mantém o
    comprimento em `O(log n)`.
    """
    if n < 0:
        raise ValueError("n não pode ser negativo")
    if n == 0:
        return []
    if n == 1:
        return [key_between(prev, next)]

    if next is None:
        current = key_between(prev, None)
        keys = [current]
        for _ in range(n - 1):
            current = key_between(current, None)
            keys.append(current)
        return keys

    if prev is None:
        current = key_between(None, next)
        keys = [current]
        for _ in range(n - 1):
            current = key_between(None, current)
            keys.append(current)
        keys.reverse()
        return keys

    middle = n // 2
    pivot = key_between(prev, next)
    return [
        *n_keys_between(prev, pivot, middle),
        pivot,
        *n_keys_between(pivot, next, n - middle - 1),
    ]
```

---

#### `backend/tests/test_fractional_index.py`

##### 1. Ação Manual

Crie o arquivo `backend/tests/test_fractional_index.py`. Rode só ele para validar a Fase 1:

```bash
cd backend
pytest tests/test_fractional_index.py -v
```

##### 2. Código Fonte Completo

```python
"""
CA-04: a ordenação do quadro inteiro repousa neste módulo.

O defeito que este arquivo previne é silencioso e tardio: uma chave gerada
FORA do intervalo pedido não quebra nada na hora — o card só aparece no
lugar errado na próxima leitura do quadro, depois do commit, sem erro
nenhum no log. Nenhum teste de rota pegaria isso, porque a rota devolveria
200.

Por isso o teste é de PROPRIEDADE, não de exemplo: para toda combinação de
âncoras (as duas presentes, só a da esquerda, só a da direita, nenhuma), a
chave devolvida tem de ser estritamente maior que a da esquerda e
estritamente menor que a da direita — em ordem lexicográfica de string,
que é a ordem que o `ORDER BY position` do banco vai usar.
"""

from __future__ import annotations

import random

import pytest

from app.services.fractional_index import (
    INITIAL_KEY,
    MAX_KEY_LENGTH,
    key_between,
    n_keys_between,
)


def test_lista_vazia_recebe_a_chave_inicial():
    assert key_between(None, None) == INITIAL_KEY


def test_chave_no_fim_e_maior_que_a_anterior():
    primeira = key_between(None, None)
    segunda = key_between(primeira, None)
    assert primeira < segunda


def test_chave_no_inicio_e_menor_que_a_seguinte():
    primeira = key_between(None, None)
    anterior = key_between(None, primeira)
    assert anterior < primeira


def test_chave_no_meio_fica_estritamente_entre_as_ancoras():
    a = key_between(None, None)
    b = key_between(a, None)
    meio = key_between(a, b)
    assert a < meio < b


@pytest.mark.parametrize("quantidade", [1, 2, 3, 10, 50])
def test_n_keys_between_devolve_n_chaves_ordenadas(quantidade: int):
    chaves = n_keys_between(None, None, quantidade)
    assert len(chaves) == quantidade
    assert chaves == sorted(chaves)
    assert len(set(chaves)) == quantidade


def test_n_keys_between_respeita_as_ancoras():
    a = key_between(None, None)
    b = key_between(a, None)
    chaves = n_keys_between(a, b, 7)
    assert all(a < chave < b for chave in chaves)
    assert chaves == sorted(chaves)


def test_n_keys_between_com_zero_devolve_lista_vazia():
    assert n_keys_between(None, None, 0) == []


def test_ancoras_fora_de_ordem_levantam_value_error():
    a = key_between(None, None)
    b = key_between(a, None)
    with pytest.raises(ValueError):
        key_between(b, a)


def test_ancoras_iguais_levantam_value_error():
    a = key_between(None, None)
    with pytest.raises(ValueError):
        key_between(a, a)


def test_chave_malformada_levanta_value_error():
    """Fração terminada em '0' não é chave válida — ver `_validate_key`."""
    with pytest.raises(ValueError):
        key_between("a0V0", None)


def test_mil_insercoes_consecutivas_no_mesmo_ponto_mantem_a_ordem():
    """
    CA-04, cláusula de ordem: 1 000 inserções consecutivas no MESMO ponto
    (sempre logo depois da mesma âncora) preservam a ordem lexicográfica
    estrita, **sem nenhum rebalanceamento** — nenhuma chave já existente
    é reescrita.
    """
    ancora = key_between(None, None)
    seguinte = key_between(ancora, None)

    lista = [ancora, seguinte]
    for _ in range(1000):
        nova = key_between(lista[0], lista[1])
        assert lista[0] < nova < lista[1]
        lista.insert(1, nova)

    assert lista == sorted(lista)
    assert len(set(lista)) == len(lista)


def test_mil_insercoes_no_fim_nao_estouram_o_tamanho_da_coluna():
    """
    O caso REAL de volume: 1 000 cards criados em sequência (é o que
    `apply_template_to_company` e o importador do Trello fazem). A parte
    inteira da chave absorve o crescimento e o comprimento fica em 3-4
    caracteres, muito abaixo de `String(64)`.
    """
    chaves: list[str] = []
    atual: str | None = None
    for _ in range(1000):
        atual = key_between(atual, None)
        chaves.append(atual)

    assert chaves == sorted(chaves)
    assert max(len(c) for c in chaves) <= MAX_KEY_LENGTH


def test_lote_de_mil_chaves_nao_estoura_o_tamanho_da_coluna():
    """
    O caminho de `apply_template_to_company` e do importador do Trello:
    `n_keys_between` divide o intervalo binariamente, então 1 000 chaves
    de uma vez cabem em 3 caracteres.
    """
    chaves = n_keys_between(None, None, 1000)
    assert chaves == sorted(chaves)
    assert max(len(c) for c in chaves) <= MAX_KEY_LENGTH


def test_mil_arrastos_para_posicoes_arbitrarias_nao_estouram_a_coluna():
    """
    O padrão de uso real do arrasto: 1 000 movimentos para posições
    variadas de uma lista que cresce. `random.seed` fixo para o teste ser
    determinístico — um teste de ordenação que muda de resultado a cada
    execução não é barreira, é ruído.
    """
    random.seed(20260827)
    lista = n_keys_between(None, None, 2)

    for _ in range(1000):
        indice = random.randrange(1, len(lista))
        nova = key_between(lista[indice - 1], lista[indice])
        assert lista[indice - 1] < nova < lista[indice]
        lista.insert(indice, nova)

    assert lista == sorted(lista)
    assert max(len(c) for c in lista) <= MAX_KEY_LENGTH


def test_o_pior_caso_cabe_em_64_caracteres():
    """
    Barreira do limite documentado no módulo: inserir SEMPRE no mesmo
    intervalo gasta ~1 caractere a cada 5 inserções, e `String(64)` cobre
    exatamente 310 dessas. Fixamos 300 como barreira, com margem.

    Se este teste falhar, a leitura é: o algoritmo continua correto, mas o
    tipo da coluna ficou apertado — a correção é alargar `position`, não
    trocar o índice fracionário.
    """
    ancora = key_between(None, None)
    atual = key_between(ancora, None)

    for _ in range(300):
        atual = key_between(ancora, atual)
        assert ancora < atual

    assert len(atual) <= MAX_KEY_LENGTH
```

---

### Fase 2 — Modelo, migration e backfill

---

#### `backend/app/models/dashboard_board.py`

##### 1. Ação Manual

Crie o arquivo `backend/app/models/dashboard_board.py`.

> **Sobre o import circular.** `DashboardColumn.dashboard` aponta para `Dashboard`, que vive
> em `company_dashboard.py` — e `company_dashboard.py` precisa da tabela
> `dashboard_card_labels` daqui. A dependência é resolvida em **um sentido só**: este módulo
> importa apenas `Base` e referencia `Dashboard` por *forward-ref* em string
> (`Mapped["Dashboard"]`), enquanto `company_dashboard.py` importa este. Não há ciclo — é o
> mesmo mecanismo que já faz `DashboardCardHistoryEntry.actor_user` → `User` funcionar.

##### 2. Código Fonte Completo

```python
from __future__ import annotations

"""
Colunas de quadro e etiquetas de card — o eixo ESPACIAL do dashboard.

Isolado de `company_dashboard.py` de propósito: aquele arquivo já tem 290
linhas e nove models; empilhar mais quatro ali tornaria a leitura do
domínio de card pior sem ganho nenhum.

Duas entidades, duas perguntas diferentes (D-1 do PRD):

- `DashboardColumn` responde *"onde este card está NESTE quadro?"* — é
  por `dashboard_id`, arrastável, e o análogo direto da *list* do Trello.
- `DashboardCardCategory` (em `company_dashboard.py`) continua respondendo
  *"que TIPO de card é este?"* — global, `name` único em toda a
  plataforma, e é o que `bulk_update_cards(operation="set_category")` e o
  filtro por categoria usam. Promover categoria a coluna quebraria as
  duas coisas: `name` é único globalmente (duas empresas não poderiam ter
  cada uma a sua coluna "Controle 5") e a contagem de
  `CategoryInUseError` deixaria de fazer sentido.

`DashboardLabel` é o terceiro eixo, ortogonal aos outros dois: criticidade.
`DashboardCardStatus` responde *"está conforme?"*; a etiqueta responde
*"quão crítico é?"*. A regra de B-A23 continua valendo integralmente —
**etiqueta nunca determina conformidade**, e por isso a etiqueta
`Concluído com evidência` do quadro de origem foi deliberadamente deixada
fora do vocabulário semeado (ver a migration c8f1a3e57b90).
"""

from datetime import datetime
import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DashboardColumnKind(str, enum.Enum):
    """
    `SECTION` é a lista separadora do Trello (nome terminado em `>>`, ex.:
    `ISO 27001:2022 >>`): existe para dividir visualmente o quadro em
    blocos normativos, tem zero cards por definição e **não aceita** que
    um card seja solto nela. Renderiza como divisor, não como coluna.
    """

    COLUMN = "COLUMN"
    SECTION = "SECTION"


#: M:N entre card e etiqueta. Declarada como `Table` do Core (e não como
#: model) porque não tem identidade nem comportamento próprios — é
#: consumida via `secondary=` em `DashboardCard.labels`.
dashboard_card_labels = Table(
    "dashboard_card_labels",
    Base.metadata,
    Column(
        "card_id",
        ForeignKey("dashboard_cards.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "label_id",
        ForeignKey("dashboard_labels.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class DashboardTemplateColumn(Base):
    """Coluna de UM template — a planta a partir da qual as colunas de
    cada empresa nascem em `apply_template_to_company`."""

    __tablename__ = "dashboard_template_columns"

    __table_args__ = (
        UniqueConstraint(
            "template_id", "name", name="uq_dashboard_template_column_name"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("dashboard_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[DashboardColumnKind] = mapped_column(
        Enum(DashboardColumnKind, name="dashboard_column_kind"),
        nullable=False,
        default=DashboardColumnKind.COLUMN,
    )
    # O default existe só para não quebrar inserts diretos de seed/teste;
    # a chave real vem sempre de `app.services.fractional_index`
    # (INITIAL_KEY == "a0").
    position: Mapped[str] = mapped_column(String(64), nullable=False, default="a0")

    template: Mapped["DashboardTemplate"] = relationship(back_populates="columns")
    cards: Mapped[list["DashboardTemplateCard"]] = relationship(
        back_populates="template_column"
    )


class DashboardColumn(Base):
    __tablename__ = "dashboard_columns"

    __table_args__ = (
        # Mesma invariante que `uq_dashboard_card_origin_per_dashboard`
        # (migration b7c02e91d4a5) instalou para cards, pela mesma razão:
        # é ela que sustenta a idempotência de apply_template_to_company.
        # Em MySQL, NULL não participa da unicidade — colunas criadas à
        # mão pelo admin seguem livres.
        UniqueConstraint(
            "dashboard_id",
            "origin_template_column_id",
            name="uq_dashboard_column_origin_per_dashboard",
        ),
        # Cobre o ORDER BY do carregamento do quadro (CA-13).
        Index("ix_dashboard_columns_board_position", "dashboard_id", "position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dashboard_id: Mapped[int] = mapped_column(
        ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[DashboardColumnKind] = mapped_column(
        Enum(DashboardColumnKind, name="dashboard_column_kind"),
        nullable=False,
        default=DashboardColumnKind.COLUMN,
    )
    position: Mapped[str] = mapped_column(String(64), nullable=False, default="a0")
    # Equivalente ao `closed` da lista do Trello: arquiva sem apagar.
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Limite de WIP — coluna criada em v1, UI em v2 (evita uma 2ª migration).
    wip_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    origin_template_column_id: Mapped[int | None] = mapped_column(
        ForeignKey("dashboard_template_columns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    dashboard: Mapped["Dashboard"] = relationship(back_populates="columns")
    # SEM `delete-orphan`: apagar uma coluna NUNCA apaga card. A FK é
    # ON DELETE SET NULL e o card cai no bucket "Sem coluna" — mesma
    # escolha já feita para `category_id`.
    cards: Mapped[list["DashboardCard"]] = relationship(back_populates="column")
    origin_template_column: Mapped["DashboardTemplateColumn | None"] = relationship()


class DashboardLabel(Base):
    """
    Vocabulário GLOBAL de etiquetas, espelho estrutural de
    `DashboardCardCategory`: mesmo formato de campos, mesmo CRUD, mesma
    regra de exclusão bloqueada quando em uso.
    """

    __tablename__ = "dashboard_labels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="#788c5d")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
```

---

#### `backend/app/models/company_dashboard.py`

##### 1. Ação Manual

Abra `backend/app/models/company_dashboard.py` e substitua o conteúdo **inteiro** pelo bloco
abaixo. As mudanças são seis: `DashboardTemplate.columns`, `DashboardTemplateCard`
(+`template_column_id`, +`position`, +`template_column`), `Dashboard.columns`,
`DashboardCard` (+`column_id`, +`position`, +`description`, +`due_date`, +índice composto,
+`column`, +`labels`) e o comentário histórico em `sort_order`.

##### 2. Código Fonte Completo

```python
from __future__ import annotations

from datetime import datetime
import enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.dashboard_board import dashboard_card_labels


class DashboardMessageType(str, enum.Enum):
    QUESTION = "QUESTION"
    ANSWER = "ANSWER"


class DashboardCardStatus(str, enum.Enum):
    EM_ANALISE = "EM_ANALISE"
    PARCIAL = "PARCIAL"
    CONFORME = "CONFORME"
    NAOCONFORME = "NAOCONFORME"


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(160), nullable=False, unique=True, index=True
    )
    email: Mapped[str] = mapped_column(
        String(160), nullable=False, unique=True, index=True
    )
    phone: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)

    principal_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relacionamentos de posse usados pela exclusão em cascata de empresa
    # (ver services/company_admin.py::delete_company_cascade, proposta
    # M.1). `cascade="all, delete-orphan"` faz o SQLAlchemy apagar
    # dashboard/cards/notes/checklist/history/messages e company_messages
    # no nível do ORM quando `db.delete(company)` é chamado — não dependemos
    # só do `ON DELETE CASCADE` do banco (que existe desde 9d5a3c1b2e77 /
    # bf7239a52df8, mas não é respeitado pelo SQLite dos testes sem
    # `PRAGMA foreign_keys=ON`).
    dashboard: Mapped["Dashboard | None"] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
        uselist=False,
    )
    messages: Mapped[list["CompanyMessage"]] = relationship(  # type: ignore
        back_populates="company",
        cascade="all, delete-orphan",
    )


class DashboardCardCategory(Base):
    """
    Vocabulário fechado de categorias de card, editável pelo admin — o
    mesmo papel que `ControlCatalog` cumpre para `AuditControl`, aplicado
    ao domínio do dashboard (proposta O.3 em docs/plano_implementacao.md).
    Substitui `DashboardCard.tag`/`DashboardTemplateCard.tag` (texto
    livre) como forma de agrupar/filtrar/editar em massa por categoria.
    `tag` permanece nas duas tabelas como campo histórico — ver a
    migration 4f2b8e6a91d3 para a estratégia de backfill.

    Desde o quadro Kanban (migration c8f1a3e57b90) a categoria deixou de
    ser o eixo de AGRUPAMENTO VISUAL — esse papel passou a
    `DashboardColumn`, que é por quadro. A categoria continua sendo o eixo
    de CLASSIFICAÇÃO global, e continua alimentando o filtro lateral e o
    `bulk_update_cards(operation="set_category")`. Ver D-1 do PRD.
    """

    __tablename__ = "dashboard_card_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="#788c5d")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class DashboardTemplate(Base):
    __tablename__ = "dashboard_templates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    cards: Mapped[list["DashboardTemplateCard"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
    )
    # Mesmo motivo do cascade em `Company.dashboard`: sem ele, excluir um
    # template deixa colunas órfãs no SQLite dos testes, que não aplica
    # `ON DELETE CASCADE` sem `PRAGMA foreign_keys=ON`.
    columns: Mapped[list["DashboardTemplateColumn"]] = relationship(  # type: ignore
        back_populates="template",
        cascade="all, delete-orphan",
    )


class DashboardTemplateCard(Base):
    __tablename__ = "dashboard_template_cards"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("dashboard_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tag: Mapped[str] = mapped_column(String(60), nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("dashboard_card_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Em que coluna do template este card nasce (§4.1.2 do PRD).
    template_column_id: Mapped[int | None] = mapped_column(
        ForeignKey("dashboard_template_columns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Campo histórico desde c8f1a3e57b90 — substituído por `position`.
    # Mantido preenchido para não quebrar consumidor antigo, mesma
    # política conservadora aplicada a `tag` na migration 4f2b8e6a91d3.
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    position: Mapped[str] = mapped_column(String(64), nullable=False, default="a0")

    template: Mapped["DashboardTemplate"] = relationship(back_populates="cards")
    category: Mapped["DashboardCardCategory | None"] = relationship()
    template_column: Mapped["DashboardTemplateColumn | None"] = relationship(  # type: ignore
        back_populates="cards"
    )


class Dashboard(Base):
    __tablename__ = "dashboards"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    cards: Mapped[list["DashboardCard"]] = relationship(
        back_populates="dashboard",
        cascade="all, delete-orphan",
    )
    # Sem este cascade, `delete_company_cascade` deixa colunas órfãs no
    # SQLite dos testes — exatamente o motivo já documentado no comentário
    # de `Company.dashboard` logo acima.
    columns: Mapped[list["DashboardColumn"]] = relationship(  # type: ignore
        back_populates="dashboard",
        cascade="all, delete-orphan",
    )
    company: Mapped["Company"] = relationship(back_populates="dashboard")


class DashboardCard(Base):
    __tablename__ = "dashboard_cards"

    __table_args__ = (
        # M-19: a invariante que sustenta a idempotência de
        # apply_template_to_company. NULL não participa da unicidade em
        # MySQL, então cards customizados seguem livres.
        UniqueConstraint(
            "dashboard_id",
            "origin_template_card_id",
            name="uq_dashboard_card_origin_per_dashboard",
        ),
        # Cobre o ORDER BY do carregamento do quadro e elimina o filesort
        # com 215 cards (CA-13). Mesmo padrão das migrations 56d322bbd83a /
        # d5c4d7cd6687 / eafa65e9df05.
        Index("ix_dashboard_cards_column_position", "column_id", "position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dashboard_id: Mapped[int] = mapped_column(
        ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False, index=True
    )

    control_code: Mapped[str | None] = mapped_column(
        String(40), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    tag: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("dashboard_card_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    origin_template_card_id: Mapped[int | None] = mapped_column(
        ForeignKey("dashboard_template_cards.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[DashboardCardStatus] = mapped_column(
        Enum(DashboardCardStatus, name="dashboard_card_status"),
        nullable=False,
        default=DashboardCardStatus.EM_ANALISE,
        index=True,
    )

    # SET NULL e não CASCADE: apagar uma coluna nunca apaga card — o card
    # cai no bucket sintético "Sem coluna" do quadro. Mesma escolha já
    # feita para `category_id` logo acima.
    column_id: Mapped[int | None] = mapped_column(
        ForeignKey("dashboard_columns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    position: Mapped[str] = mapped_column(String(64), nullable=False, default="a0")
    # 68 % dos cards do quadro real têm descrição, e ela é o texto
    # normativo do controle. Sem esta coluna, `apply_template_to_company`
    # descartava silenciosamente `DashboardTemplateCard.description`
    # desde O.3.
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Coluna criada em v1 sem UI (v2), para evitar uma 2ª migration.
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Campo histórico desde c8f1a3e57b90 — a ordenação real do quadro é
    # `position`. Mantido preenchido por retrocompatibilidade, mesma
    # política que `tag` recebeu na migration 4f2b8e6a91d3 (B12).
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    dashboard: Mapped["Dashboard"] = relationship(back_populates="cards")
    category: Mapped["DashboardCardCategory | None"] = relationship()
    origin_template_card: Mapped["DashboardTemplateCard | None"] = relationship()
    column: Mapped["DashboardColumn | None"] = relationship(  # type: ignore
        back_populates="cards"
    )
    labels: Mapped[list["DashboardLabel"]] = relationship(  # type: ignore
        secondary=dashboard_card_labels,
        order_by="DashboardLabel.sort_order",
    )
    notes: Mapped[list["DashboardCardNote"]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )
    checklist_items: Mapped[list["DashboardCardchecklistItem"]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )
    history_items: Mapped[list["DashboardCardHistoryEntry"]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )
    messages: Mapped[list["DashboardCardMessage"]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )


class DashboardCardNote(Base):
    __tablename__ = "dashboard_card_notes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(
        ForeignKey("dashboard_cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    card: Mapped["DashboardCard"] = relationship(back_populates="notes")


class DashboardCardchecklistItem(Base):
    __tablename__ = "dashboard_card_checklist_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(
        ForeignKey("dashboard_cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    card: Mapped["DashboardCard"] = relationship(back_populates="checklist_items")


class DashboardCardHistoryEntry(Base):
    __tablename__ = "dashboard_card_history_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(
        ForeignKey("dashboard_cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    card: Mapped["DashboardCard"] = relationship(back_populates="history_items")
    actor_user: Mapped["User"] = relationship(back_populates="history_items")  # type: ignore


class DashboardCardMessage(Base):
    __tablename__ = "dashboard_card_messages"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(
        ForeignKey("dashboard_cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    message_type: Mapped[DashboardMessageType] = mapped_column(
        Enum(DashboardMessageType, name="dashboard_message_type"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    card: Mapped["DashboardCard"] = relationship(back_populates="messages")
    author_user: Mapped["User"] = relationship(back_populates="messages")  # type: ignore
```

---

#### `backend/app/models/__init__.py`

##### 1. Ação Manual

Abra `backend/app/models/__init__.py` e substitua o conteúdo inteiro.

> **Este passo é obrigatório, não cosmético.** `tests/conftest.py:9` importa `app.models`
> justamente para popular `Base.metadata` antes do `create_all`. Sem o registro aqui, as
> quatro tabelas novas simplesmente não são criadas no SQLite dos testes, e todo teste de
> quadro falha com `no such table: dashboard_columns`.

##### 2. Código Fonte Completo

```python
from app.models.user import User
from app.models.audit import Audit
from app.models.control_catalog import ControlCatalog
from app.models.audit_control import AuditControl
from app.models.evidence import Evidence
from app.models.message import Message
from app.models.sub_user_request import SubUserRequest
from app.models.company_message import CompanyMessage
from app.models.dashboard_board import (
    DashboardColumn,
    DashboardColumnKind,
    DashboardLabel,
    DashboardTemplateColumn,
    dashboard_card_labels,
)
from app.models.company_dashboard import (
    Company,
    DashboardTemplate,
    DashboardTemplateCard,
    Dashboard,
    DashboardCard,
    DashboardCardCategory,
    DashboardCardNote,
    DashboardCardchecklistItem,
    DashboardCardHistoryEntry,
    DashboardCardMessage,
)

__all__ = [
    "User",
    "Audit",
    "ControlCatalog",
    "AuditControl",
    "Evidence",
    "Message",
    "SubUserRequest",
    "CompanyMessage",
    "Company",
    "DashboardTemplate",
    "DashboardTemplateCard",
    "Dashboard",
    "DashboardCard",
    "DashboardCardCategory",
    "DashboardCardNote",
    "DashboardCardchecklistItem",
    "DashboardCardHistoryEntry",
    "DashboardCardMessage",
    "DashboardColumn",
    "DashboardColumnKind",
    "DashboardTemplateColumn",
    "DashboardLabel",
    "dashboard_card_labels",
]
```

---

#### `backend/alembic/env.py`

##### 1. Ação Manual

Abra `backend/alembic/env.py` e acrescente **uma linha** no bloco de imports de models
(logo antes de `import app.models.company_dashboard`, por volta da linha 37).

> **Por quê.** O `env.py` importa os módulos de model **um a um**, de propósito, para não
> depender dos exports de `__init__.py`. Um módulo novo que não entre nessa lista fica fora
> do `target_metadata` — e qualquer `--autogenerate` futuro proporia *dropar* as quatro
> tabelas novas. Este arquivo é o único lugar de toda a entrega em que a omissão não quebra
> nada hoje e quebra tudo depois.

##### 2. Código Fonte Completo (bloco de imports, linhas 26-40 do arquivo)

```python
# Import Base + models so metadata is populated
from app.db.base import Base  # noqa: E402
from app.core.config import settings  # noqa: E402

# Import modules (not app.models.* wildcard) to avoid relying on __init__.py exports.
import app.models.audit  # noqa: E402,F401
import app.models.audit_control  # noqa: E402,F401
import app.models.control_catalog  # noqa: E402,F401
import app.models.evidence  # noqa: E402,F401
import app.models.message  # noqa: E402,F401
import app.models.user  # noqa: E402,F401
import app.models.dashboard_board  # noqa: E402,F401
import app.models.company_dashboard  # noqa: E402, F401
import app.models.sub_user_request  # noqa: E402, F401
import app.models.company_message  # noqa: E402, F401
```

---

#### `backend/alembic/versions/c8f1a3e57b90_add_dashboard_columns_and_labels.py`

##### 1. Ação Manual

Crie o arquivo `backend/alembic/versions/c8f1a3e57b90_add_dashboard_columns_and_labels.py`.

> **Não gere este arquivo com `alembic revision --autogenerate`.** O autogenerate produz o
> DDL, mas não os três *backfills*, que são o coração da migration — e sem eles todo quadro
> existente fica vazio depois do upgrade (R3/CA-02). O nome do arquivo tem de começar com
> `c8f1a3e57b90`, senão `test_migrations_smoke.py::test_filename_matches_declared_revision`
> reprova (incidentes I.5 e O.5).

Depois de criar, valide a cadeia inteira contra o MySQL de verdade — é exatamente o que o
job `migrations` do CI faz:

```bash
cd backend
docker compose up -d          # sobe o MySQL 8.4
alembic upgrade head
alembic downgrade base
alembic upgrade head
alembic heads                 # tem de listar exatamente 1
```

##### 2. Código Fonte Completo

```python
"""add_dashboard_columns_and_labels

Revision ID: c8f1a3e57b90
Revises: b7c02e91d4a5
Create Date: 2026-08-27 10:14:22.108431

Quadro Kanban de colunas e cards. Acrescenta ao domínio de card três
eixos que ele não tinha: ONDE o card está no quadro (`dashboard_columns`),
EM QUE ORDEM ele está dentro da coluna (`position`, índice fracionário) e
QUÃO CRÍTICO ele é (`dashboard_labels`, M:N).

Estratégia de dados — a regra que governa tudo aqui é **nenhum quadro
existente pode ficar vazio depois do upgrade**:

1. As 4 tabelas novas são criadas antes de qualquer ALTER, e nesta ordem:
   `dashboard_template_columns` antes de `dashboard_columns` (que a
   referencia) e `dashboard_labels` antes de `dashboard_card_labels`.

2. As 6 colunas novas entram com `position` **NULLABLE**. Não é
   preferência de estilo: `ADD COLUMN ... NOT NULL` sem default falha em
   tabela populada no MySQL. A coluna vira `NOT NULL` no passo 5, depois
   do backfill.

3. **Backfill de coluna** (`backfill_columns`): para cada quadro, uma
   `dashboard_columns` por `category_id` EFETIVAMENTE em uso naquele
   quadro, nomeada com o nome da categoria, na ordem de
   `dashboard_card_categories.sort_order`; cards sem categoria vão para
   um balde `Sem categoria`. Não criamos uma coluna por categoria
   existente — só pelas usadas: um quadro de 12 cards não deve nascer com
   40 colunas vazias.

4. **Backfill de `position`** (`backfill_positions`): chaves fracionárias
   geradas em Python na ordem `sort_order ASC, id ASC` — ou seja, a ordem
   que o usuário JÁ VÊ hoje é preservada exatamente. A migration importa
   `app.services.fractional_index`; o precedente de migration que importa
   do app é `a3d81f4c7b02`, e o módulo é puro (sem Session, sem I/O), o
   que torna o import barato e seguro.

5. **Backfill de `description`** (`backfill_descriptions`): copia a
   descrição do `DashboardTemplateCard` de origem para o card da empresa.
   Recupera o dado que `apply_template_to_company` vinha DESCARTANDO
   silenciosamente desde O.3 — 68 % dos cards do quadro real têm
   descrição, e ela é o texto normativo do controle.

6. **Seed de 8 etiquetas** (§2.1 do PRD). Ficam de fora, de propósito:
   `Concluído com evidência` (redundante com o status `CONFORME` — duas
   fontes de verdade para "está conforme?" é exatamente o que B-A23
   proíbe), `Entregue - Inove Educação` (específica de um cliente) e
   `Não Aplicável` (é status, não etiqueta — decisão D-2, registrada no
   backlog).

As três funções de backfill são de módulo, e não código inline dentro de
`upgrade()`, porque é o que permite testá-las sem MySQL — ver
`tests/test_migration_board_backfill.py`. `test_migrations_smoke.py` faz
só análise estática e nunca abre conexão; não teria como verificar
CA-02/CA-03.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.services.fractional_index import n_keys_between

# revision identifiers, used by Alembic.
revision: str = "c8f1a3e57b90"
down_revision: Union[str, None] = "b7c02e91d4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


#: As 8 etiquetas aprovadas em §2.1 do PRD: (nome, cor, ordem).
#: A cor é o hex do tema correspondente à cor do Trello de origem — o mapa
#: completo vive em `frontend/lib/board-labels.ts::TRELLO_COLOR_MAP`.
APPROVED_LABELS = [
    ("Item Critico", "#96311D", 0),
    ("Alta Criticidade", "#C2410C", 1),
    ("Média Criticidade", "#A16207", 2),
    ("Baixa Criticidade", "#2C5A8C", 3),
    ("Aguardando empresa", "#0E7490", 4),
    ("Check-list", "#6D28D9", 5),
    ("Inserir doc atualizado no final do projeto", "#854D0E", 6),
    ("Final do projeto", "#1E3A8A", 7),
]

UNCATEGORIZED_COLUMN_NAME = "Sem categoria"


# ------------------------------------------------------------ backfills


def backfill_columns(bind) -> None:
    """
    Cria uma `dashboard_columns` por categoria em uso em cada quadro e
    liga os cards a ela.

    Chamada por `upgrade()` e, diretamente, por
    `tests/test_migration_board_backfill.py` — é por isso que recebe o
    `bind` em vez de chamar `op.get_bind()` por dentro.
    """
    categorias = bind.execute(
        sa.text(
            "SELECT id, name FROM dashboard_card_categories "
            "ORDER BY sort_order ASC, name ASC"
        )
    ).fetchall()
    ordem_da_categoria = {linha[0]: indice for indice, linha in enumerate(categorias)}
    nome_da_categoria = {linha[0]: linha[1] for linha in categorias}

    quadros = bind.execute(
        sa.text("SELECT id FROM dashboards ORDER BY id ASC")
    ).fetchall()

    for (dashboard_id,) in quadros:
        usadas = [
            linha[0]
            for linha in bind.execute(
                sa.text(
                    "SELECT DISTINCT category_id FROM dashboard_cards "
                    "WHERE dashboard_id = :dashboard_id"
                ),
                {"dashboard_id": dashboard_id},
            ).fetchall()
        ]
        if not usadas:
            # Quadro sem card nenhum: nada a preservar, e criar colunas
            # vazias aqui seria inventar informação.
            continue

        com_categoria = sorted(
            [cid for cid in usadas if cid is not None],
            # Categoria referenciada por card mas ausente da tabela (FK
            # SET NULL de uma exclusão antiga) vai para o fim, nunca some.
            key=lambda cid: ordem_da_categoria.get(cid, 10**6),
        )
        alvos: list[tuple[int | None, str]] = [
            (cid, nome_da_categoria.get(cid, UNCATEGORIZED_COLUMN_NAME))
            for cid in com_categoria
        ]
        if any(cid is None for cid in usadas):
            alvos.append((None, UNCATEGORIZED_COLUMN_NAME))

        for (category_id, nome), position in zip(
            alvos, n_keys_between(None, None, len(alvos))
        ):
            bind.execute(
                sa.text(
                    "INSERT INTO dashboard_columns "
                    "(dashboard_id, name, kind, position, hidden) "
                    "VALUES (:dashboard_id, :nome, 'COLUMN', :position, 0)"
                ),
                {"dashboard_id": dashboard_id, "nome": nome, "position": position},
            )
            column_id = bind.execute(
                sa.text(
                    "SELECT id FROM dashboard_columns "
                    "WHERE dashboard_id = :dashboard_id AND position = :position"
                ),
                {"dashboard_id": dashboard_id, "position": position},
            ).scalar_one()

            if category_id is None:
                bind.execute(
                    sa.text(
                        "UPDATE dashboard_cards SET column_id = :column_id "
                        "WHERE dashboard_id = :dashboard_id AND category_id IS NULL"
                    ),
                    {"column_id": column_id, "dashboard_id": dashboard_id},
                )
            else:
                bind.execute(
                    sa.text(
                        "UPDATE dashboard_cards SET column_id = :column_id "
                        "WHERE dashboard_id = :dashboard_id "
                        "AND category_id = :category_id"
                    ),
                    {
                        "column_id": column_id,
                        "dashboard_id": dashboard_id,
                        "category_id": category_id,
                    },
                )


def backfill_positions(bind) -> None:
    """
    Gera `position` para cards de empresa e de template, na ordem
    `sort_order ASC, id ASC` — a mesma ordem que as duas telas usam hoje.

    `n_keys_between` divide o intervalo binariamente, então 213 cards
    saem com chaves de 3 caracteres, não de 213.
    """
    for tabela, escopo in (
        ("dashboard_cards", "dashboard_id"),
        ("dashboard_template_cards", "template_id"),
    ):
        grupos = bind.execute(
            sa.text(f"SELECT DISTINCT {escopo} FROM {tabela}")
        ).fetchall()
        for (grupo,) in grupos:
            ids = [
                linha[0]
                for linha in bind.execute(
                    sa.text(
                        f"SELECT id FROM {tabela} WHERE {escopo} = :grupo "
                        "ORDER BY sort_order ASC, id ASC"
                    ),
                    {"grupo": grupo},
                ).fetchall()
            ]
            if not ids:
                continue
            for registro_id, position in zip(
                ids, n_keys_between(None, None, len(ids))
            ):
                bind.execute(
                    sa.text(
                        f"UPDATE {tabela} SET position = :position WHERE id = :id"
                    ),
                    {"position": position, "id": registro_id},
                )


def backfill_descriptions(bind) -> None:
    """
    Recupera a descrição descartada por `apply_template_to_company` desde
    O.3, a partir do card de template de origem.

    Só preenche onde ainda está NULL: um card cuja descrição já tenha sido
    escrita à mão não pode ser sobrescrito pelo template — é a mesma regra
    de "nunca sobrescrever card existente" que sustenta a idempotência.
    """
    bind.execute(
        sa.text(
            """
            UPDATE dashboard_cards
               SET description = (
                   SELECT t.description
                     FROM dashboard_template_cards t
                    WHERE t.id = dashboard_cards.origin_template_card_id
               )
             WHERE origin_template_card_id IS NOT NULL
               AND description IS NULL
            """
        )
    )


# ------------------------------------------------------------- upgrade


def upgrade() -> None:
    bind = op.get_bind()

    # --- 1. Tabelas novas (ordem de dependência) ---
    op.create_table(
        "dashboard_template_columns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("COLUMN", "SECTION", name="dashboard_column_kind"),
            nullable=False,
            server_default="COLUMN",
        ),
        sa.Column("position", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["template_id"], ["dashboard_templates.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "template_id", "name", name="uq_dashboard_template_column_name"
        ),
    )
    op.create_index(
        "ix_dashboard_template_columns_template_id",
        "dashboard_template_columns",
        ["template_id"],
    )

    op.create_table(
        "dashboard_columns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dashboard_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("COLUMN", "SECTION", name="dashboard_column_kind"),
            nullable=False,
            server_default="COLUMN",
        ),
        sa.Column("position", sa.String(length=64), nullable=False),
        sa.Column(
            "hidden", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("wip_limit", sa.Integer(), nullable=True),
        sa.Column("origin_template_column_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["dashboard_id"], ["dashboards.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["origin_template_column_id"],
            ["dashboard_template_columns.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dashboard_id",
            "origin_template_column_id",
            name="uq_dashboard_column_origin_per_dashboard",
        ),
    )
    op.create_index(
        "ix_dashboard_columns_dashboard_id", "dashboard_columns", ["dashboard_id"]
    )
    op.create_index(
        "ix_dashboard_columns_origin_template_column_id",
        "dashboard_columns",
        ["origin_template_column_id"],
    )

    op.create_table(
        "dashboard_labels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column(
            "color", sa.String(length=20), nullable=False, server_default="#788c5d"
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_dashboard_labels_name"),
    )

    op.create_table(
        "dashboard_card_labels",
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("label_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["card_id"], ["dashboard_cards.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["label_id"], ["dashboard_labels.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("card_id", "label_id"),
    )

    # --- 2. Colunas novas (position entra NULLABLE, ver docstring) ---
    op.add_column("dashboard_cards", sa.Column("column_id", sa.Integer(), nullable=True))
    op.add_column(
        "dashboard_cards", sa.Column("position", sa.String(length=64), nullable=True)
    )
    op.add_column("dashboard_cards", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "dashboard_cards",
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_dashboard_cards_column_id",
        "dashboard_cards",
        "dashboard_columns",
        ["column_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_dashboard_cards_column_id", "dashboard_cards", ["column_id"])

    op.add_column(
        "dashboard_template_cards",
        sa.Column("template_column_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "dashboard_template_cards",
        sa.Column("position", sa.String(length=64), nullable=True),
    )
    op.create_foreign_key(
        "fk_dashboard_template_cards_template_column_id",
        "dashboard_template_cards",
        "dashboard_template_columns",
        ["template_column_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_dashboard_template_cards_template_column_id",
        "dashboard_template_cards",
        ["template_column_id"],
    )

    # --- 3, 4 e 5. Backfills ---
    backfill_columns(bind)
    backfill_positions(bind)
    backfill_descriptions(bind)

    # --- 6. Só agora `position` pode ser NOT NULL ---
    op.alter_column(
        "dashboard_cards",
        "position",
        existing_type=sa.String(length=64),
        nullable=False,
    )
    op.alter_column(
        "dashboard_template_cards",
        "position",
        existing_type=sa.String(length=64),
        nullable=False,
    )

    # --- 7. Vocabulário de etiquetas ---
    labels_table = sa.table(
        "dashboard_labels",
        sa.column("name", sa.String),
        sa.column("color", sa.String),
        sa.column("sort_order", sa.Integer),
    )
    op.bulk_insert(
        labels_table,
        [
            {"name": name, "color": color, "sort_order": sort_order}
            for name, color, sort_order in APPROVED_LABELS
        ],
    )

    # --- 8. Índices compostos que cobrem o ORDER BY do quadro (CA-13) ---
    op.create_index(
        "ix_dashboard_columns_board_position",
        "dashboard_columns",
        ["dashboard_id", "position"],
    )
    op.create_index(
        "ix_dashboard_cards_column_position",
        "dashboard_cards",
        ["column_id", "position"],
    )


# ----------------------------------------------------------- downgrade


def downgrade() -> None:
    """
    A ordem aqui não é estilística — é a lição de B-A30, que só apareceu
    na PRIMEIRA execução real do job `migrations` contra MySQL 8.4:

        (1553, "Cannot drop index '...': needed in a foreign key constraint")

    No MySQL, uma FOREIGN KEY exige um índice, e o servidor RECUSA remover
    esse índice enquanto a constraint existir. A ordem correta é sempre
    **constraint → índice → coluna**, e as tabelas caem na ordem inversa
    da criação.

    Nada de `pass` (B13): o job `migrations` do CI reverte até `base` e
    reaplica a cada PR — um downgrade incompleto reprova o build.
    """
    # --- dashboard_cards: constraint, depois índices, depois colunas ---
    op.drop_constraint(
        "fk_dashboard_cards_column_id", "dashboard_cards", type_="foreignkey"
    )
    op.drop_index("ix_dashboard_cards_column_position", table_name="dashboard_cards")
    op.drop_index("ix_dashboard_cards_column_id", table_name="dashboard_cards")
    op.drop_column("dashboard_cards", "due_date")
    op.drop_column("dashboard_cards", "description")
    op.drop_column("dashboard_cards", "position")
    op.drop_column("dashboard_cards", "column_id")

    # --- dashboard_template_cards: mesma ordem ---
    op.drop_constraint(
        "fk_dashboard_template_cards_template_column_id",
        "dashboard_template_cards",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_dashboard_template_cards_template_column_id",
        table_name="dashboard_template_cards",
    )
    op.drop_column("dashboard_template_cards", "position")
    op.drop_column("dashboard_template_cards", "template_column_id")

    # --- Tabelas, na ordem inversa da criação ---
    op.drop_table("dashboard_card_labels")
    op.drop_table("dashboard_labels")

    op.drop_index("ix_dashboard_columns_board_position", table_name="dashboard_columns")
    op.drop_index(
        "ix_dashboard_columns_origin_template_column_id",
        table_name="dashboard_columns",
    )
    op.drop_index("ix_dashboard_columns_dashboard_id", table_name="dashboard_columns")
    op.drop_table("dashboard_columns")

    op.drop_index(
        "ix_dashboard_template_columns_template_id",
        table_name="dashboard_template_columns",
    )
    op.drop_table("dashboard_template_columns")
```

---

#### `backend/tests/test_migration_board_backfill.py`

##### 1. Ação Manual

Crie o arquivo `backend/tests/test_migration_board_backfill.py`.

> **Por que um arquivo próprio, e não linhas em `test_migrations_smoke.py`.** Aquele arquivo
> faz **apenas análise estática** — `importlib`, `revision == nome do arquivo`, head único —
> e nunca abre conexão com banco nenhum. Ele não consegue verificar backfill, e atribuir
> CA-02/CA-03 a ele seria dar por coberto o que não está. Aqui montamos o schema
> **posterior ao DDL e anterior ao backfill** em SQLite e chamamos as três funções de
> backfill diretamente.

```bash
cd backend
pytest tests/test_migration_board_backfill.py -v
```

##### 2. Código Fonte Completo

```python
"""
CA-02 e CA-03: o backfill da migration c8f1a3e57b90.

O defeito que este arquivo previne é o pior desta entrega inteira (R3):
um `upgrade` que roda sem erro, o CI fica verde, e o quadro de todas as
empresas de produção aparece VAZIO — porque `column_id` ficou NULL — ou
com os cards em ordem trocada, porque `position` foi gerada na ordem
errada. Nenhum teste de rota pega isso: as rotas passariam a responder
200 com uma lista vazia legítima.

`test_migrations_smoke.py` cobre a CADEIA (importável, revision bate com o
nome do arquivo, head único) e o job `migrations` do CI cobre o
`upgrade`/`downgrade` real contra MySQL 8.4. O que faltava era verificar
o CONTEÚDO do backfill, e é o que se faz aqui: montamos em SQLite o
schema exatamente como ele fica depois do DDL e antes do backfill,
populamos com dados de ordem conhecida e chamamos as três funções.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = (
    BACKEND_ROOT
    / "alembic"
    / "versions"
    / "c8f1a3e57b90_add_dashboard_columns_and_labels.py"
)

# Schema no estado "depois do DDL, antes do backfill": as colunas novas
# existem e `position` ainda é NULLABLE. Só as tabelas que os backfills
# tocam — montar o schema inteiro aqui seria duplicar os models.
SCHEMA_POS_DDL = [
    """
    CREATE TABLE dashboard_card_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(60) NOT NULL UNIQUE,
        color VARCHAR(20) NOT NULL DEFAULT '#788c5d',
        sort_order INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE dashboards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        title VARCHAR(200) NOT NULL
    )
    """,
    """
    CREATE TABLE dashboard_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(120) NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE dashboard_template_columns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_id INTEGER NOT NULL,
        name VARCHAR(160) NOT NULL,
        kind VARCHAR(20) NOT NULL DEFAULT 'COLUMN',
        position VARCHAR(64)
    )
    """,
    """
    CREATE TABLE dashboard_template_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_id INTEGER NOT NULL,
        title VARCHAR(160) NOT NULL,
        description TEXT,
        tag VARCHAR(60) NOT NULL DEFAULT '',
        category_id INTEGER,
        template_column_id INTEGER,
        sort_order INTEGER NOT NULL DEFAULT 0,
        position VARCHAR(64)
    )
    """,
    """
    CREATE TABLE dashboard_columns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dashboard_id INTEGER NOT NULL,
        name VARCHAR(160) NOT NULL,
        kind VARCHAR(20) NOT NULL DEFAULT 'COLUMN',
        position VARCHAR(64) NOT NULL,
        hidden BOOLEAN NOT NULL DEFAULT 0,
        wip_limit INTEGER,
        origin_template_column_id INTEGER,
        created_at DATETIME
    )
    """,
    """
    CREATE TABLE dashboard_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dashboard_id INTEGER NOT NULL,
        control_code VARCHAR(40),
        title VARCHAR(160) NOT NULL,
        tag VARCHAR(60) NOT NULL DEFAULT '',
        category_id INTEGER,
        origin_template_card_id INTEGER,
        hidden BOOLEAN NOT NULL DEFAULT 0,
        status VARCHAR(20) NOT NULL DEFAULT 'EM_ANALISE',
        column_id INTEGER,
        position VARCHAR(64),
        description TEXT,
        due_date DATETIME,
        sort_order INTEGER NOT NULL DEFAULT 0
    )
    """,
]


def _carregar_migration():
    """Importa o módulo da migration pelo caminho, como test_migrations_smoke."""
    spec = importlib.util.spec_from_file_location(MIGRATION_PATH.stem, MIGRATION_PATH)
    assert spec and spec.loader, f"não foi possível carregar {MIGRATION_PATH}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def conexao():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        for ddl in SCHEMA_POS_DDL:
            conn.execute(text(ddl))
        yield conn


@pytest.fixture
def migration():
    return _carregar_migration()


def _semear(conn) -> None:
    """
    Dois quadros, três categorias, cards com `sort_order` conhecido e um
    card sem categoria — a forma de dado que o backfill precisa tratar.
    """
    conn.execute(
        text(
            "INSERT INTO dashboard_card_categories (id, name, color, sort_order) "
            "VALUES (1, 'Compliance', '#96311D', 3), "
            "       (2, 'Financeiro', '#2C5A8C', 0), "
            "       (3, 'Vendas', '#8A6114', 2)"
        )
    )
    conn.execute(
        text(
            "INSERT INTO dashboards (id, company_id, title) "
            "VALUES (1, 10, 'Dash A'), (2, 20, 'Dash B')"
        )
    )
    conn.execute(text("INSERT INTO dashboard_templates (id, name) VALUES (1, 'T1')"))
    conn.execute(
        text(
            "INSERT INTO dashboard_template_cards "
            "(id, template_id, title, description, sort_order) "
            "VALUES (100, 1, 'Política de SI', 'Texto normativo do controle 5.1', 0), "
            "       (101, 1, 'Inventário', NULL, 1)"
        )
    )
    # Quadro 1: 4 cards, um deles sem categoria, sort_order fora de ordem
    # de id de propósito — é a ordem por sort_order que tem de sobreviver.
    conn.execute(
        text(
            "INSERT INTO dashboard_cards "
            "(id, dashboard_id, title, category_id, origin_template_card_id, sort_order) "
            "VALUES (1, 1, 'Card Financeiro B', 2, NULL, 3), "
            "       (2, 1, 'Card Compliance',   1, 100,  1), "
            "       (3, 1, 'Card sem categoria', NULL, NULL, 2), "
            "       (4, 1, 'Card Financeiro A', 2, 101,  0)"
        )
    )
    # Quadro 2: 1 card, categoria Vendas.
    conn.execute(
        text(
            "INSERT INTO dashboard_cards "
            "(id, dashboard_id, title, category_id, sort_order) "
            "VALUES (5, 2, 'Card Vendas', 3, 0)"
        )
    )


def test_nenhum_card_fica_sem_coluna(conexao, migration):
    """CA-02, primeira metade: quadro que tinha cards não pode ficar vazio."""
    _semear(conexao)

    migration.backfill_columns(conexao)

    orfaos = conexao.execute(
        text("SELECT COUNT(*) FROM dashboard_cards WHERE column_id IS NULL")
    ).scalar_one()
    assert orfaos == 0, "há card sem coluna depois do backfill — ver R3 do PRD"


def test_colunas_nascem_por_categoria_em_uso_e_na_ordem_da_categoria(
    conexao, migration
):
    _semear(conexao)

    migration.backfill_columns(conexao)

    nomes_quadro_1 = [
        linha[0]
        for linha in conexao.execute(
            text(
                "SELECT name FROM dashboard_columns "
                "WHERE dashboard_id = 1 ORDER BY position ASC"
            )
        ).fetchall()
    ]
    # Financeiro (sort_order 0) < Vendas (2) < Compliance (3); Vendas não
    # é usada no quadro 1, então não vira coluna. "Sem categoria" por último.
    assert nomes_quadro_1 == ["Financeiro", "Compliance", "Sem categoria"]

    nomes_quadro_2 = [
        linha[0]
        for linha in conexao.execute(
            text("SELECT name FROM dashboard_columns WHERE dashboard_id = 2")
        ).fetchall()
    ]
    assert nomes_quadro_2 == ["Vendas"]


def test_quadro_sem_cards_nao_ganha_colunas(conexao, migration):
    """Criar colunas vazias num quadro vazio seria inventar informação."""
    conexao.execute(
        text("INSERT INTO dashboards (id, company_id, title) VALUES (9, 90, 'Vazio')")
    )

    migration.backfill_columns(conexao)

    total = conexao.execute(
        text("SELECT COUNT(*) FROM dashboard_columns WHERE dashboard_id = 9")
    ).scalar_one()
    assert total == 0


def test_ordem_por_position_reproduz_a_ordem_por_sort_order(conexao, migration):
    """
    CA-02, segunda metade: a ordem que o usuário vê hoje (`sort_order ASC,
    id ASC`) tem de ser exatamente a ordem depois do upgrade
    (`position ASC`).
    """
    _semear(conexao)

    migration.backfill_positions(conexao)

    antes = [
        linha[0]
        for linha in conexao.execute(
            text(
                "SELECT id FROM dashboard_cards WHERE dashboard_id = 1 "
                "ORDER BY sort_order ASC, id ASC"
            )
        ).fetchall()
    ]
    depois = [
        linha[0]
        for linha in conexao.execute(
            text(
                "SELECT id FROM dashboard_cards WHERE dashboard_id = 1 "
                "ORDER BY position ASC"
            )
        ).fetchall()
    ]
    assert antes == [4, 2, 3, 1]
    assert depois == antes


def test_position_e_preenchida_em_todos_os_cards_e_cards_de_template(
    conexao, migration
):
    _semear(conexao)

    migration.backfill_positions(conexao)

    for tabela in ("dashboard_cards", "dashboard_template_cards"):
        nulos = conexao.execute(
            text(f"SELECT COUNT(*) FROM {tabela} WHERE position IS NULL")
        ).scalar_one()
        assert nulos == 0, f"{tabela} ficou com position NULL — o ALTER NOT NULL falharia"


def test_position_cabe_na_coluna_de_64_caracteres(conexao, migration):
    _semear(conexao)

    migration.backfill_positions(conexao)

    maior = conexao.execute(
        text("SELECT MAX(LENGTH(position)) FROM dashboard_cards")
    ).scalar_one()
    assert maior <= 64


def test_descricao_e_propagada_do_card_de_template_de_origem(conexao, migration):
    """
    CA-03: recupera o dado que `apply_template_to_company` descartava
    desde O.3.
    """
    _semear(conexao)

    migration.backfill_descriptions(conexao)

    descricao = conexao.execute(
        text("SELECT description FROM dashboard_cards WHERE id = 2")
    ).scalar_one()
    assert descricao == "Texto normativo do controle 5.1"


def test_descricao_nao_e_inventada_para_card_sem_origem(conexao, migration):
    _semear(conexao)

    migration.backfill_descriptions(conexao)

    # Card 4 tem origem (101), mas o template card 101 tem description NULL.
    assert (
        conexao.execute(
            text("SELECT description FROM dashboard_cards WHERE id = 4")
        ).scalar_one()
        is None
    )
    # Card 3 não tem origem nenhuma.
    assert (
        conexao.execute(
            text("SELECT description FROM dashboard_cards WHERE id = 3")
        ).scalar_one()
        is None
    )


def test_descricao_escrita_a_mao_nao_e_sobrescrita(conexao, migration):
    """Mesma regra de 'nunca sobrescrever card existente' que sustenta a
    idempotência de apply_template_to_company."""
    _semear(conexao)
    conexao.execute(
        text("UPDATE dashboard_cards SET description = 'Escrita pelo auditor' WHERE id = 2")
    )

    migration.backfill_descriptions(conexao)

    assert (
        conexao.execute(
            text("SELECT description FROM dashboard_cards WHERE id = 2")
        ).scalar_one()
        == "Escrita pelo auditor"
    )


def test_as_oito_etiquetas_aprovadas_estao_declaradas(migration):
    """
    CA-12/§2.1: `Concluído com evidência` NÃO pode entrar — ela criaria
    uma segunda fonte de verdade para "está conforme?", que é exatamente
    o que B-A23 proíbe. `Não Aplicável` também fica fora (é status, não
    etiqueta — decisão D-2).
    """
    nomes = {nome for nome, _cor, _ordem in migration.APPROVED_LABELS}

    assert len(migration.APPROVED_LABELS) == 8
    assert "Item Critico" in nomes
    assert "Concluído com evidência" not in nomes
    assert "Entregue - Inove Educação" not in nomes
    assert "Não Aplicável" not in nomes
```

---

### Fase 3 — Núcleo e serviços

---

#### `backend/app/core/policy.py`

##### 1. Ação Manual

Abra `backend/app/core/policy.py` e substitua o conteúdo inteiro. São 3 valores novos no
enum `Action` e 3 linhas novas em `ALLOWED_ROLES`.

> **Não pule a linha em `ALLOWED_ROLES`.** `test_authorization_matrix.py:192` é
> parametrizado sobre `list(Action)`: as 3 ações novas entram na cobertura
> **automaticamente**, e esquecer a linha correspondente reprova o teste com
> `KeyError` — que é exatamente o comportamento desejado.

##### 2. Código Fonte Completo

```python
from __future__ import annotations

import enum

from fastapi import HTTPException, status


class Action(str, enum.Enum):
    """
    Ações cujo direito NÃO decorre de posse. Existe porque posse e
    permissão são coisas diferentes numa plataforma de auditoria: o
    cliente é dono dos próprios cards e evidências, mas quem declara
    conformidade é o auditor (ver B-A23 em docs/relatorio_bugs.md).

    Desde B-A28 o enum cobre também LEITURA. O enum nasceu da pergunta
    "quem pode declarar conformidade?" e respondeu só a ela; leitura
    ficou fora do vocabulário, então cada endpoint decidia sozinho — e
    `get_card_details` decidiu não decidir. O registro interno do auditor
    (checklist e histórico) é confidencial em relação ao auditado, do
    mesmo modo que a escrita é privativa dele.
    """

    SET_CARD_STATUS = "SET_CARD_STATUS"
    SET_CONTROL_STATUS = "SET_CONTROL_STATUS"
    WRITE_CARD_HISTORY = "WRITE_CARD_HISTORY"
    TOGGLE_CHECKLIST = "TOGGLE_CHECKLIST"
    WRITE_CARD_NOTE = "WRITE_CARD_NOTE"
    CLOSE_AUDIT = "CLOSE_AUDIT"
    MANAGE_TEMPLATE = "MANAGE_TEMPLATE"
    MANAGE_CATEGORY = "MANAGE_CATEGORY"
    DELETE_COMPANY = "DELETE_COMPANY"
    # Leitura de registro interno do auditor (B-A28):
    READ_CARD_INTERNALS = "READ_CARD_INTERNALS"
    # Escritas legítimas do lado auditado:
    UPLOAD_EVIDENCE = "UPLOAD_EVIDENCE"
    ASK_QUESTION = "ASK_QUESTION"
    REQUEST_SUB_USER = "REQUEST_SUB_USER"
    # Quadro Kanban (PRD §4.4). O quadro é LEITURA para o cliente e
    # ESCRITA só para o auditor, pela mesma razão de B-A23: a disposição
    # do quadro é a leitura que o auditor faz do andamento da due
    # diligence, não um espaço de trabalho compartilhado. O cliente vê o
    # quadro inteiro em GET /dashboard/companies/{id}/board — só não o
    # rearranja.
    MANAGE_COLUMN = "MANAGE_COLUMN"  # criar/renomear/mover/arquivar/excluir coluna
    MOVE_CARD = "MOVE_CARD"  # arrastar card entre e dentro de colunas
    MANAGE_LABEL = "MANAGE_LABEL"  # CRUD do vocabulário + aplicar em card


# Fonte única de verdade. Uma linha aqui é mais fácil de revisar num PR
# do que uma condição espalhada por 11 routers.
ALLOWED_ROLES: dict[Action, frozenset[str]] = {
    Action.SET_CARD_STATUS: frozenset({"admin"}),
    Action.SET_CONTROL_STATUS: frozenset({"admin"}),
    Action.WRITE_CARD_HISTORY: frozenset({"admin"}),
    Action.TOGGLE_CHECKLIST: frozenset({"admin"}),
    Action.WRITE_CARD_NOTE: frozenset({"admin"}),
    Action.CLOSE_AUDIT: frozenset({"admin"}),
    Action.MANAGE_TEMPLATE: frozenset({"admin"}),
    Action.MANAGE_CATEGORY: frozenset({"admin"}),
    Action.DELETE_COMPANY: frozenset({"admin"}),
    Action.READ_CARD_INTERNALS: frozenset({"admin"}),
    Action.UPLOAD_EVIDENCE: frozenset({"user", "sub-user"}),
    Action.ASK_QUESTION: frozenset({"admin", "user", "sub-user"}),
    Action.REQUEST_SUB_USER: frozenset({"user"}),
    Action.MANAGE_COLUMN: frozenset({"admin"}),
    Action.MOVE_CARD: frozenset({"admin"}),
    Action.MANAGE_LABEL: frozenset({"admin"}),
}


def can(action: Action, role: str) -> bool:
    """True se `role` pode executar `action`."""
    return role in ALLOWED_ROLES[action]


def assert_can(action: Action, role: str) -> None:
    """Levanta 403 se `role` não pode executar `action`."""
    if not can(action, role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Papel '{role}' não pode executar {action.value}",
        )
```

---

#### `backend/app/core/access.py`

##### 1. Ação Manual

Abra `backend/app/core/access.py` e substitua o conteúdo inteiro. A única adição é a
função `get_column_with_access`, no fim do arquivo.

##### 2. Código Fonte Completo

```python
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company_dashboard import Company, Dashboard
from app.models.dashboard_board import DashboardColumn
from app.models.user import User

"""
Posse de recurso por usuário — ponto único (M-01c).

Este conceito existia em **quatro** cópias: `client.py`,
`dashboard_cards.py`, `company_messages.py` e, na direção inversa,
`company_admin.py::member_user_ids`. Quatro cópias de uma regra de acesso
significam quatro lugares para corrigir quando a regra muda — e três para
esquecer.

O custo disso foi medido, não suposto: B-B21 corrigiu um typo (`vísculo`)
que existia em **uma** das quatro; B-B23 (403 → 404) precisou ser aplicado
em três arquivos. A unificação faz a próxima mudança ser de um lugar só.

**Posse não é permissão.** Este módulo responde "este recurso é deste
usuário?". Quem responde "este papel pode executar esta ação?" é
`app/core/policy.py`. Os dois são necessários, e confundi-los foi
exatamente o que produziu B-A23 e B-A28.
"""


def resolve_owner_user_id(current_user: User) -> int:
    """
    ID do usuário "dono" dos dados: o próprio, ou o principal de quem ele
    é sub-usuário.

    Sub-usuários não têm dados próprios — têm acesso aos do principal ao
    qual estão vinculados.
    """
    if current_user.role == "sub-user":
        if current_user.parent_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sub-usuário sem vínculo com usuário principal",
            )
        return current_user.parent_user_id
    return current_user.id


def member_user_ids(db: Session, principal_user_id: int) -> list[int]:
    """
    A relação inversa de `resolve_owner_user_id`: usuário principal +
    todos os seus sub-usuários.

    Usada onde é preciso partir da empresa para achar os usuários — o
    filtro de auditoria por empresa (`Audit` não tem `company_id`, só
    `client_user_id`) e a exclusão em cascata.
    """
    sub_user_ids = db.scalars(
        select(User.id).where(User.parent_user_id == principal_user_id)
    ).all()
    return [principal_user_id, *sub_user_ids]


def get_company_with_access(
    db: Session, company_id: int, current_user: User
) -> Company:
    """
    Empresa acessível pelo chamador, ou 404.

    Devolve **404 — e não 403** — quando a empresa existe mas não é do
    chamador (B-B23). Distinguir "não existe" de "existe e não é sua"
    permite enumerar os `company_id` da plataforma. Mesma convenção já
    usada em `client.py::get_my_audit` ("não encontrada ou sem acesso").
    """
    company = db.get(Company, company_id)

    if company is not None:
        if current_user.role == "admin":
            return company
        if company.principal_user_id == resolve_owner_user_id(current_user):
            return company

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Empresa não encontrada ou sem acesso",
    )


def get_column_with_access(
    db: Session, column_id: int, current_user: User
) -> DashboardColumn:
    """
    Coluna de quadro acessível pelo chamador, ou 404.

    Mesmo molde de `get_company_with_access`, um JOIN mais longe
    (`dashboard_columns → dashboards → companies`) e com a mesma
    convenção de **404 em qualquer caso que não seja acesso legítimo**:
    coluna inexistente e coluna de outra empresa são indistinguíveis para
    quem chama (B-B23).

    Note que esta função responde só POSSE. A permissão de mexer na
    coluna é `Action.MANAGE_COLUMN`, verificada ANTES, no router — a
    ordem de `update_card_status`, que garante 403 para papel errado e
    404 para tenant errado, nunca o inverso.
    """
    row = db.execute(
        select(DashboardColumn, Company)
        .join(Dashboard, Dashboard.id == DashboardColumn.dashboard_id)
        .join(Company, Company.id == Dashboard.company_id)
        .where(DashboardColumn.id == column_id)
    ).first()

    if row is not None:
        column, company = row
        if current_user.role == "admin":
            return column
        if company.principal_user_id == resolve_owner_user_id(current_user):
            return column

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Coluna não encontrada ou sem acesso",
    )
```

---

#### `backend/app/services/dashboard_board.py`

##### 1. Ação Manual

Crie o arquivo `backend/app/services/dashboard_board.py`.

##### 2. Código Fonte Completo

```python
from __future__ import annotations

"""
Regra de negócio do quadro: montar, criar/mover/arquivar coluna, mover
card e etiquetar.

Segue as camadas já praticadas na base (B4): este módulo chama
`db.flush()` e **nunca** `db.commit()` — quem controla a transação é o
router, que é também quem traduz as exceções de domínio daqui para
status HTTP. Cada exceção existe para uma regra, e a docstring dela
explica a decisão, não a mecânica (B5).
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.company_dashboard import Dashboard, DashboardCard
from app.models.dashboard_board import (
    DashboardColumn,
    DashboardColumnKind,
    DashboardLabel,
)
from app.services.fractional_index import key_between


class ColumnNotFoundError(Exception):
    """
    Coluna inexistente, ou de outro quadro — o router converte para 404
    nos dois casos.

    Não são dois erros diferentes de propósito: distinguir "não existe" de
    "existe e não é sua" permitiria enumerar as colunas da plataforma
    inteira (B-B23).
    """


class ColumnNotEmptyError(Exception):
    """
    Tentativa de excluir coluna que ainda tem card não-oculto — o router
    converte para 409.

    Regra deliberadamente simples, a mesma de `CategoryInUseError`:
    exclusão **bloqueada**, não em cascata. Perder a posição (e, com a FK
    `SET NULL`, o agrupamento) de dezenas de cards por um clique errado é
    pior que exigir um passo a mais do admin — mover os cards para outra
    coluna antes de excluir a antiga.

    Cards OCULTOS não contam. Um card oculto já não é trabalho em aberto
    aos olhos do resumo (mesma decisão de O.4 em
    `get_dashboard_status_summary`), e exigir reexibir 30 cards
    arquivados só para poder apagar uma coluna vazia seria burocracia sem
    ganho.
    """


class ColumnKindError(Exception):
    """
    Tentativa de soltar um card numa coluna `SECTION` — o router converte
    para 422.

    `SECTION` é a lista separadora do Trello (`ISO 27001:2022 >>`):
    existe para dividir o quadro em blocos normativos e, por definição,
    não tem cards. Aceitar o card aqui produziria um card invisível, já
    que a UI renderiza `SECTION` como divisor e não como área de soltar.
    """


class AnchorMismatchError(Exception):
    """
    Âncora (`prev_card_id` / `next_card_id`) que não pertence à coluna de
    destino, ou que está fora de ordem — o router converte para 422.

    Fecha a classe inteira de bugs em que o cliente manda âncoras
    inconsistentes e o servidor gera, em silêncio, uma chave fora de
    ordem — o pior tipo de defeito desta funcionalidade, porque não
    produz erro nenhum na hora: o card só aparece no lugar errado na
    próxima leitura do quadro.
    """


class LabelNotFoundError(Exception):
    """Etiqueta inexistente — o router converte para 404."""


class LabelInUseError(Exception):
    """
    Etiqueta ainda vinculada a algum card — o router converte para 409.
    Mesma regra e mesma razão de `CategoryInUseError`.
    """


@dataclass
class BoardColumnData:
    """Uma coluna do quadro com os cards que caem dentro dela."""

    column: DashboardColumn
    cards: list[DashboardCard]


@dataclass
class BoardData:
    """
    Quadro pronto para serialização: colunas ordenadas, cards agrupados,
    balde dos cards sem coluna e o vocabulário de etiquetas.

    `outdated_card_ids` vem calculado daqui porque a comparação com o
    template precisa saber de que coluna de template a coluna atual
    nasceu — informação que já está carregada aqui e que o router teria
    de reconsultar.
    """

    dashboard: Dashboard
    columns: list[BoardColumnData]
    uncolumned: list[DashboardCard]
    labels: list[DashboardLabel]
    outdated_card_ids: set[int]


# ------------------------------------------------------------- Leitura


def _card_is_outdated(
    card: DashboardCard, origin_column_by_column_id: dict[int, int | None]
) -> bool:
    """
    O card divergiu da definição de template da qual nasceu?

    Compara título, categoria, descrição e **coluna**. A comparação de
    coluna não é `card.column_id != origin.template_column_id` — esses
    dois números vivem em tabelas diferentes (`dashboard_columns` e
    `dashboard_template_columns`) e compará-los diretamente daria
    "desatualizado" para todo card. O que se compara é a ORIGEM da coluna
    atual do card com a coluna de template declarada no card de template.
    """
    if card.origin_template_card_id is None or card.origin_template_card is None:
        return False
    origin = card.origin_template_card

    coluna_de_origem = (
        origin_column_by_column_id.get(card.column_id)
        if card.column_id is not None
        else None
    )

    return (
        card.title != origin.title
        or card.category_id != origin.category_id
        or (card.description or "") != (origin.description or "")
        or coluna_de_origem != origin.template_column_id
    )


def get_board(
    db: Session,
    dashboard: Dashboard,
    *,
    include_hidden: bool = False,
    search: str = "",
) -> BoardData:
    """
    Monta o quadro inteiro num número CONSTANTE de queries (CA-13),
    independentemente de quantas colunas o quadro tem: uma para as
    colunas, uma para os cards, três `selectinload` (etiquetas,
    categoria, card de template de origem) e uma para o vocabulário de
    etiquetas. O agrupamento é feito em memória.

    Foi para isto que a montagem migrou do cliente React para o servidor
    (D-5 do PRD): com colunas persistidas, repetir a lógica de ordenação
    em dois lugares garantiria que os dois divergissem.

    Cards com `column_id IS NULL` — órfãos de uma coluna excluída, pela FK
    `SET NULL` — vão para `uncolumned` em vez de sumir do quadro.
    """
    colunas_stmt = select(DashboardColumn).where(
        DashboardColumn.dashboard_id == dashboard.id
    )
    if not include_hidden:
        colunas_stmt = colunas_stmt.where(DashboardColumn.hidden.is_(False))
    colunas = list(
        db.scalars(
            colunas_stmt.order_by(
                DashboardColumn.position.asc(), DashboardColumn.id.asc()
            )
        ).all()
    )

    cards_stmt = select(DashboardCard).where(
        DashboardCard.dashboard_id == dashboard.id
    )
    if not include_hidden:
        cards_stmt = cards_stmt.where(DashboardCard.hidden.is_(False))
    termo = search.strip()
    if termo:
        padrao = f"%{termo}%"
        cards_stmt = cards_stmt.where(
            (DashboardCard.title.ilike(padrao))
            | (DashboardCard.control_code.ilike(padrao))
        )

    cards = list(
        db.scalars(
            cards_stmt.options(
                # Sem estes três, o quadro real (215 cards) faria 645
                # queries extras (B9).
                selectinload(DashboardCard.labels),
                selectinload(DashboardCard.category),
                selectinload(DashboardCard.origin_template_card),
            ).order_by(DashboardCard.position.asc(), DashboardCard.id.asc())
        ).all()
    )

    etiquetas = list(
        db.scalars(
            select(DashboardLabel).order_by(
                DashboardLabel.sort_order.asc(), DashboardLabel.name.asc()
            )
        ).all()
    )

    por_coluna: dict[int, list[DashboardCard]] = {coluna.id: [] for coluna in colunas}
    sem_coluna: list[DashboardCard] = []
    for card in cards:
        destino = por_coluna.get(card.column_id) if card.column_id is not None else None
        if destino is None:
            # column_id NULL, ou coluna arquivada e não pedida: o card
            # não pode simplesmente desaparecer do quadro.
            sem_coluna.append(card)
        else:
            destino.append(card)

    origem_por_coluna = {
        coluna.id: coluna.origin_template_column_id for coluna in colunas
    }
    desatualizados = {
        card.id for card in cards if _card_is_outdated(card, origem_por_coluna)
    }

    return BoardData(
        dashboard=dashboard,
        columns=[
            BoardColumnData(column=coluna, cards=por_coluna[coluna.id])
            for coluna in colunas
        ],
        uncolumned=sem_coluna,
        labels=etiquetas,
        outdated_card_ids=desatualizados,
    )


# -------------------------------------------------------------- Colunas


def _column_of_dashboard(
    db: Session, column_id: int, dashboard_id: int
) -> DashboardColumn:
    coluna = db.get(DashboardColumn, column_id)
    if coluna is None or coluna.dashboard_id != dashboard_id:
        raise ColumnNotFoundError("Coluna não encontrada")
    return coluna


def create_column(
    db: Session,
    dashboard: Dashboard,
    *,
    name: str,
    kind: DashboardColumnKind = DashboardColumnKind.COLUMN,
    after_column_id: int | None = None,
) -> DashboardColumn:
    """
    Cria uma coluna depois de `after_column_id`, ou no fim do quadro se
    ele for `None`.
    """
    colunas = list(
        db.scalars(
            select(DashboardColumn)
            .where(DashboardColumn.dashboard_id == dashboard.id)
            .order_by(DashboardColumn.position.asc(), DashboardColumn.id.asc())
        ).all()
    )

    if after_column_id is None:
        anterior = colunas[-1].position if colunas else None
        seguinte = None
    else:
        indices = [i for i, c in enumerate(colunas) if c.id == after_column_id]
        if not indices:
            raise ColumnNotFoundError("Coluna de referência não encontrada")
        indice = indices[0]
        anterior = colunas[indice].position
        seguinte = colunas[indice + 1].position if indice + 1 < len(colunas) else None

    coluna = DashboardColumn(
        dashboard_id=dashboard.id,
        name=name,
        kind=kind,
        position=key_between(anterior, seguinte),
    )
    db.add(coluna)
    db.flush()
    return coluna


def update_column(
    db: Session,
    column: DashboardColumn,
    *,
    name: str,
    hidden: bool,
    wip_limit: int | None,
) -> DashboardColumn:
    """Renomear / arquivar / limitar WIP. Não mexe em `position`."""
    column.name = name
    column.hidden = hidden
    column.wip_limit = wip_limit
    db.flush()
    return column


def move_column(
    db: Session,
    column: DashboardColumn,
    *,
    prev_column_id: int | None,
    next_column_id: int | None,
) -> DashboardColumn:
    """
    Reordena a coluna. As âncoras são lidas DENTRO da transação e a chave
    é calculada aqui — o cliente nunca inventa chave (§4.2 do PRD).
    """
    anterior = _column_anchor_position(db, prev_column_id, column)
    seguinte = _column_anchor_position(db, next_column_id, column)

    try:
        column.position = key_between(anterior, seguinte)
    except ValueError as exc:
        raise AnchorMismatchError(
            "Âncoras de posição de coluna inconsistentes"
        ) from exc

    db.flush()
    return column


def _column_anchor_position(
    db: Session, anchor_id: int | None, column: DashboardColumn
) -> str | None:
    if anchor_id is None:
        return None
    ancora = db.get(DashboardColumn, anchor_id)
    if (
        ancora is None
        or ancora.dashboard_id != column.dashboard_id
        or ancora.id == column.id
    ):
        raise AnchorMismatchError("Âncora de coluna não pertence a este quadro")
    return ancora.position


def delete_column(db: Session, column: DashboardColumn) -> None:
    em_uso = (
        db.scalar(
            select(func.count(DashboardCard.id)).where(
                DashboardCard.column_id == column.id,
                DashboardCard.hidden.is_(False),
            )
        )
        or 0
    )
    if em_uso > 0:
        raise ColumnNotEmptyError(
            f"Coluna com {em_uso} card(s) visível(is). Mova-os para outra coluna "
            "antes de excluir esta."
        )

    db.delete(column)
    db.flush()


# ---------------------------------------------------------- Mover card


def _card_anchor_position(
    db: Session,
    anchor_id: int | None,
    card: DashboardCard,
    destino_column_id: int | None,
) -> str | None:
    if anchor_id is None:
        return None
    ancora = db.get(DashboardCard, anchor_id)
    if (
        ancora is None
        or ancora.id == card.id
        or ancora.dashboard_id != card.dashboard_id
        or ancora.column_id != destino_column_id
    ):
        raise AnchorMismatchError(
            "Âncora de posição não pertence à coluna de destino"
        )
    return ancora.position


def move_card(
    db: Session,
    card: DashboardCard,
    *,
    column_id: int | None,
    prev_card_id: int | None,
    next_card_id: int | None,
) -> DashboardCard:
    """
    O núcleo da funcionalidade. Valida três coisas, nesta ordem, e depois
    faz **exatamente um UPDATE** (CA-06):

    1. A coluna de destino é do MESMO quadro do card (senão 404 — nunca
       403, nunca 200 silencioso).
    2. A coluna de destino não é `SECTION`.
    3. As duas âncoras pertencem à coluna de destino e estão em ordem.

    Nenhum outro card é reescrito — é a propriedade que justifica o
    índice fracionário existir.
    """
    coluna: DashboardColumn | None = None
    if column_id is not None:
        coluna = _column_of_dashboard(db, column_id, card.dashboard_id)
        if coluna.kind == DashboardColumnKind.SECTION:
            raise ColumnKindError(
                "Coluna do tipo seção não aceita cards — ela é um separador visual"
            )

    destino_id = coluna.id if coluna is not None else None

    anterior = _card_anchor_position(db, prev_card_id, card, destino_id)
    seguinte = _card_anchor_position(db, next_card_id, card, destino_id)

    try:
        nova_position = key_between(anterior, seguinte)
    except ValueError as exc:
        raise AnchorMismatchError("Âncoras de posição inconsistentes") from exc

    card.column_id = destino_id
    card.position = nova_position
    db.flush()
    return card


# ------------------------------------------------------------ Etiquetas


def set_card_labels(
    db: Session, card: DashboardCard, label_ids: list[int]
) -> list[DashboardLabel]:
    """
    Substitui o CONJUNTO inteiro de etiquetas do card — semântica de
    `PUT`, não de `PATCH`.

    Todos os ids são validados ANTES de tocar no vínculo: uma lista com
    um id inválido no meio não pode deixar o card com metade das
    etiquetas aplicadas.

    Não toca em `status` sob nenhuma circunstância (CA-12). Etiqueta é
    criticidade; status é a declaração do auditor sobre conformidade
    (B-A23). São eixos ortogonais e continuam sendo.
    """
    unicos = list(dict.fromkeys(label_ids))
    if not unicos:
        card.labels = []
        db.flush()
        return []

    etiquetas = list(
        db.scalars(select(DashboardLabel).where(DashboardLabel.id.in_(unicos))).all()
    )
    encontrados = {etiqueta.id for etiqueta in etiquetas}
    faltando = [label_id for label_id in unicos if label_id not in encontrados]
    if faltando:
        raise LabelNotFoundError(
            f"Etiqueta(s) não encontrada(s): {', '.join(str(i) for i in faltando)}"
        )

    ordenadas = sorted(etiquetas, key=lambda e: (e.sort_order, e.name))
    card.labels = ordenadas
    db.flush()
    return ordenadas


def list_labels(db: Session) -> list[DashboardLabel]:
    return list(
        db.scalars(
            select(DashboardLabel).order_by(
                DashboardLabel.sort_order.asc(), DashboardLabel.name.asc()
            )
        ).all()
    )


def create_label(
    db: Session, *, name: str, color: str, sort_order: int
) -> DashboardLabel:
    label = DashboardLabel(name=name, color=color, sort_order=sort_order)
    db.add(label)
    db.flush()
    return label


def update_label(
    db: Session, label_id: int, *, name: str, color: str, sort_order: int
) -> DashboardLabel:
    label = db.get(DashboardLabel, label_id)
    if label is None:
        raise LabelNotFoundError("Etiqueta não encontrada")
    label.name = name
    label.color = color
    label.sort_order = sort_order
    db.flush()
    return label


def delete_label(db: Session, label_id: int) -> None:
    label = db.get(DashboardLabel, label_id)
    if label is None:
        raise LabelNotFoundError("Etiqueta não encontrada")

    em_uso = (
        db.scalar(
            select(func.count(DashboardCard.id))
            .select_from(DashboardCard)
            .join(DashboardCard.labels)
            .where(DashboardLabel.id == label_id)
        )
        or 0
    )
    if em_uso > 0:
        raise LabelInUseError(f"Etiqueta em uso por {em_uso} card(s)")

    db.delete(label)
    db.flush()
```

---

#### `backend/app/services/dashboard_template_admin.py`

##### 1. Ação Manual

Abra `backend/app/services/dashboard_template_admin.py` e substitua o conteúdo inteiro.

> **Este é o arquivo de maior risco da entrega (R2).** É aqui que mora a idempotência de
> `apply_template_to_company`, e ela passa a valer também para colunas. A invariante que a
> sustenta é a mesma dos cards: `UNIQUE (dashboard_id, origin_template_column_id)`,
> instalada pela migration da Fase 2. Execute
> `pytest tests/test_dashboard_templates.py -v` logo depois de salvar.

##### 2. Código Fonte Completo

```python
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.company_dashboard import (
    Company,
    Dashboard,
    DashboardCard,
    DashboardCardCategory,
    DashboardCardStatus,
    DashboardTemplate,
    DashboardTemplateCard,
)
from app.models.dashboard_board import (
    DashboardColumn,
    DashboardColumnKind,
    DashboardTemplateColumn,
)
from app.services.dashboard_board import ColumnKindError, ColumnNotFoundError
from app.services.fractional_index import key_between, n_keys_between


class CategoryNotFoundError(Exception):
    """Categoria não encontrada — o router converte para 404."""


class CategoryInUseError(Exception):
    """
    Categoria ainda referenciada por algum card/template-card — o
    router converte para 409. Regra deliberadamente simples: exclusão
    bloqueada, não em cascata (perder o agrupamento de dezenas de cards
    por um clique errado seria pior que exigir 1 passo a mais do admin:
    trocar a categoria dos cards antes de excluir a antiga).
    """


class TemplateNotFoundError(Exception):
    """Template não encontrado — o router converte para 404."""


class TemplateCardNotFoundError(Exception):
    """Card de template não encontrado — o router converte para 404."""


class TemplateColumnNotFoundError(Exception):
    """Coluna de template não encontrada — o router converte para 404."""


class TemplateColumnInUseError(Exception):
    """
    Coluna de template ainda referenciada por algum `DashboardTemplateCard`
    — o router converte para 409.

    Mesma regra de `TemplateInUseError`, e pela mesma razão: a FK é
    `ON DELETE SET NULL`, então excluir apagaria em silêncio o vínculo que
    diz em que coluna cada card nasce, e todo dashboard criado depois
    disso nasceria com os cards fora de coluna.
    """


class DefaultTemplateDeletionError(Exception):
    """Tentativa de excluir o template marcado como padrão — o router
    converte para 409. Precisa haver sempre 0 ou 1 template padrão, e
    nunca um "buraco" (nenhum) sem decisão explícita do admin."""


class TemplateInUseError(Exception):
    """
    Template (ou card de template) ainda referenciado por
    `dashboard_cards.origin_template_card_id` — o router converte para
    409. Mesma regra de CategoryInUseError, e pela mesma razão (B-A25):
    a FK é ON DELETE SET NULL, então excluir apagaria em silêncio o
    vínculo que sustenta a idempotência de apply_template_to_company,
    o `is_outdated` e o restore_from_template de TODAS as empresas
    derivadas. Trocar o template dos cards antes de excluir é um passo a
    mais; recuperar o vínculo depois é impossível.
    """


class DashboardNotFoundError(Exception):
    """Empresa sem dashboard (não deveria acontecer para uma empresa
    onboardada por create_company_dashboard_from_template, mas defensivo
    para empresas manuais antigas) — o router converte para 404."""


# ---------------------------------------------------------------- Categorias


def list_categories(db: Session) -> list[DashboardCardCategory]:
    return list(
        db.scalars(
            select(DashboardCardCategory).order_by(
                DashboardCardCategory.sort_order.asc(), DashboardCardCategory.name.asc()
            )
        ).all()
    )


def create_category(
    db: Session, *, name: str, color: str, sort_order: int
) -> DashboardCardCategory:
    category = DashboardCardCategory(name=name, color=color, sort_order=sort_order)
    db.add(category)
    db.flush()
    return category


def update_category(
    db: Session, category_id: int, *, name: str, color: str, sort_order: int
) -> DashboardCardCategory:
    category = db.get(DashboardCardCategory, category_id)
    if category is None:
        raise CategoryNotFoundError("Categoria não encontrada")
    category.name = name
    category.color = color
    category.sort_order = sort_order
    db.flush()
    return category


def delete_category(db: Session, category_id: int) -> None:
    category = db.get(DashboardCardCategory, category_id)
    if category is None:
        raise CategoryNotFoundError("Categoria não encontrada")

    in_use = (
        db.scalar(
            select(func.count(DashboardCard.id)).where(
                DashboardCard.category_id == category_id
            )
        )
        or 0
    )
    in_use += (
        db.scalar(
            select(func.count(DashboardTemplateCard.id)).where(
                DashboardTemplateCard.category_id == category_id
            )
        )
        or 0
    )
    if in_use > 0:
        raise CategoryInUseError(
            f"Categoria em uso por {in_use} card(s)/definição(ões) de template"
        )

    db.delete(category)
    db.flush()


# ---------------------------------------------------------------- Templates
@dataclass
class TemplateWithCount:
    template: DashboardTemplate
    card_count: int


def list_templates(db: Session) -> list[TemplateWithCount]:
    """
    Uma única query com LEFT JOIN + GROUP BY, no lugar de N+1 lazy loads
    de `template.cards` só para chamar len() (B-M24). `outerjoin` para
    que template sem nenhum card apareça com card_count = 0.
    """
    rows = db.execute(
        select(DashboardTemplate, func.count(DashboardTemplateCard.id))
        .outerjoin(
            DashboardTemplateCard,
            DashboardTemplateCard.template_id == DashboardTemplate.id,
        )
        .group_by(DashboardTemplate.id)
        .order_by(DashboardTemplate.name.asc())
    ).all()
    return [
        TemplateWithCount(template=template, card_count=card_count)
        for template, card_count in rows
    ]


def get_template_detail(db: Session, template_id: int) -> DashboardTemplate:
    template = db.get(DashboardTemplate, template_id)
    if template is None:
        raise TemplateNotFoundError("Template não encontrado")
    return template


def _clear_default_flag(db: Session) -> None:
    db.execute(
        update(DashboardTemplate)
        .where(DashboardTemplate.is_default.is_(True))
        .values(is_default=False)
    )


def create_template(
    db: Session, *, name: str, description: str | None, is_default: bool
) -> DashboardTemplate:
    if is_default:
        _clear_default_flag(db)
    template = DashboardTemplate(
        name=name, description=description, is_default=is_default
    )
    db.add(template)
    db.flush()
    return template


def update_template(
    db: Session,
    template_id: int,
    *,
    name: str,
    description: str | None,
    is_default: bool,
) -> DashboardTemplate:
    template = db.get(DashboardTemplate, template_id)
    if template is None:
        raise TemplateNotFoundError("Template não encontrado")

    if is_default and not template.is_default:
        _clear_default_flag(db)

    template.name = name
    template.description = description
    template.is_default = is_default
    db.flush()
    return template


def _cards_derived_from_template(db: Session, template_id: int) -> int:
    """Quantos cards de empresa nasceram de algum card DESTE template."""
    return (
        db.scalar(
            select(func.count(DashboardCard.id))
            .select_from(DashboardCard)
            .join(
                DashboardTemplateCard,
                DashboardTemplateCard.id == DashboardCard.origin_template_card_id,
            )
            .where(DashboardTemplateCard.template_id == template_id)
        )
        or 0
    )


def _cards_derived_from_template_card(db: Session, template_card_id: int) -> int:
    """Quantos cards de empresa nasceram DESTE card de template."""
    return (
        db.scalar(
            select(func.count(DashboardCard.id)).where(
                DashboardCard.origin_template_card_id == template_card_id
            )
        )
        or 0
    )


def delete_template(db: Session, template_id: int) -> None:
    template = db.get(DashboardTemplate, template_id)
    if template is None:
        raise TemplateNotFoundError("Template não encontrado")
    if template.is_default:
        raise DefaultTemplateDeletionError(
            "Defina outro template como padrão antes de excluir este"
        )

    in_use = _cards_derived_from_template(db, template_id)
    if in_use > 0:
        raise TemplateInUseError(
            f"Template em uso por {in_use} card(s) de empresas já configuradas. "
            "Remova ou desvincule esses cards antes de excluir o template."
        )

    db.delete(template)
    db.flush()


def _category_tag(db: Session, category_id: int | None) -> str:
    """
    `tag` continua NOT NULL (schema herdado de antes de O.3 — ver
    migration 4f2b8e6a91d3) mesmo depois de category_id virar a fonte de
    verdade; para todo card/template-card criado ou editado pela UI nova
    (O.4), `tag` é mantida em sincronia com o nome da categoria, evitando
    que os dois campos divirjam de forma visível.
    """
    if category_id is None:
        return "Sem categoria"
    category = db.get(DashboardCardCategory, category_id)
    return category.name if category else "Sem categoria"


# ------------------------------------------------- Colunas de template


def list_template_columns(
    db: Session, template_id: int
) -> list[DashboardTemplateColumn]:
    return list(
        db.scalars(
            select(DashboardTemplateColumn)
            .where(DashboardTemplateColumn.template_id == template_id)
            .order_by(
                DashboardTemplateColumn.position.asc(),
                DashboardTemplateColumn.id.asc(),
            )
        ).all()
    )


def add_template_column(
    db: Session,
    template_id: int,
    *,
    name: str,
    kind: DashboardColumnKind = DashboardColumnKind.COLUMN,
) -> DashboardTemplateColumn:
    """Acrescenta uma coluna no FIM do template."""
    template = db.get(DashboardTemplate, template_id)
    if template is None:
        raise TemplateNotFoundError("Template não encontrado")

    existentes = list_template_columns(db, template_id)
    ultima = existentes[-1].position if existentes else None

    coluna = DashboardTemplateColumn(
        template_id=template.id,
        name=name,
        kind=kind,
        position=key_between(ultima, None),
    )
    db.add(coluna)
    db.flush()
    return coluna


def update_template_column(
    db: Session, template_column_id: int, *, name: str, kind: DashboardColumnKind
) -> DashboardTemplateColumn:
    coluna = db.get(DashboardTemplateColumn, template_column_id)
    if coluna is None:
        raise TemplateColumnNotFoundError("Coluna de template não encontrada")
    coluna.name = name
    coluna.kind = kind
    db.flush()
    return coluna


def move_template_column(
    db: Session,
    template_column_id: int,
    *,
    prev_column_id: int | None,
    next_column_id: int | None,
) -> DashboardTemplateColumn:
    coluna = db.get(DashboardTemplateColumn, template_column_id)
    if coluna is None:
        raise TemplateColumnNotFoundError("Coluna de template não encontrada")

    def _ancora(anchor_id: int | None) -> str | None:
        if anchor_id is None:
            return None
        ancora = db.get(DashboardTemplateColumn, anchor_id)
        if (
            ancora is None
            or ancora.template_id != coluna.template_id
            or ancora.id == coluna.id
        ):
            raise TemplateColumnNotFoundError(
                "Âncora de coluna não pertence a este template"
            )
        return ancora.position

    coluna.position = key_between(_ancora(prev_column_id), _ancora(next_column_id))
    db.flush()
    return coluna


def delete_template_column(db: Session, template_column_id: int) -> None:
    coluna = db.get(DashboardTemplateColumn, template_column_id)
    if coluna is None:
        raise TemplateColumnNotFoundError("Coluna de template não encontrada")

    em_uso = (
        db.scalar(
            select(func.count(DashboardTemplateCard.id)).where(
                DashboardTemplateCard.template_column_id == template_column_id
            )
        )
        or 0
    )
    if em_uso > 0:
        raise TemplateColumnInUseError(
            f"Coluna de template em uso por {em_uso} card(s) de template. "
            "Mova esses cards para outra coluna antes de excluir esta."
        )

    db.delete(coluna)
    db.flush()


def _validate_template_column(
    db: Session, template_id: int, template_column_id: int | None
) -> None:
    """
    Impede vincular um card do template A a uma coluna do template B —
    o quadro resultante teria um card apontando para uma coluna que nunca
    vai existir no dashboard derivado.
    """
    if template_column_id is None:
        return
    coluna = db.get(DashboardTemplateColumn, template_column_id)
    if coluna is None or coluna.template_id != template_id:
        raise TemplateColumnNotFoundError("Coluna de template não encontrada")


# ---------------------------------------------------- Cards de template


def add_template_card(
    db: Session,
    template_id: int,
    *,
    title: str,
    description: str | None,
    category_id: int | None,
    template_column_id: int | None,
    sort_order: int,
) -> DashboardTemplateCard:
    template = db.get(DashboardTemplate, template_id)
    if template is None:
        raise TemplateNotFoundError("Template não encontrado")
    if category_id is not None and db.get(DashboardCardCategory, category_id) is None:
        raise CategoryNotFoundError("Categoria não encontrada")
    _validate_template_column(db, template_id, template_column_id)

    ultima = db.scalar(
        select(func.max(DashboardTemplateCard.position)).where(
            DashboardTemplateCard.template_id == template_id,
            DashboardTemplateCard.template_column_id.is_(None)
            if template_column_id is None
            else DashboardTemplateCard.template_column_id == template_column_id,
        )
    )

    card = DashboardTemplateCard(
        template_id=template.id,
        title=title,
        description=description,
        category_id=category_id,
        template_column_id=template_column_id,
        tag=_category_tag(db, category_id),
        sort_order=sort_order,
        position=key_between(ultima, None),
    )
    db.add(card)
    db.flush()
    return card


def update_template_card(
    db: Session,
    template_card_id: int,
    *,
    title: str,
    description: str | None,
    category_id: int | None,
    template_column_id: int | None,
    sort_order: int,
) -> DashboardTemplateCard:
    card = db.get(DashboardTemplateCard, template_card_id)
    if card is None:
        raise TemplateCardNotFoundError("Card de template não encontrado")
    if category_id is not None and db.get(DashboardCardCategory, category_id) is None:
        raise CategoryNotFoundError("Categoria não encontrada")
    _validate_template_column(db, card.template_id, template_column_id)

    card.title = title
    card.description = description
    card.category_id = category_id
    card.template_column_id = template_column_id
    card.tag = _category_tag(db, category_id)
    card.sort_order = sort_order
    db.flush()
    return card


def delete_template_card(db: Session, template_card_id: int) -> None:
    card = db.get(DashboardTemplateCard, template_card_id)
    if card is None:
        raise TemplateCardNotFoundError("Card de template não encontrado")

    in_use = _cards_derived_from_template_card(db, template_card_id)
    if in_use > 0:
        raise TemplateInUseError(
            f"Card de template em uso por {in_use} card(s) de empresas já "
            "configuradas. Remova esses cards antes de excluir a definição."
        )

    db.delete(card)
    db.flush()


# ---------------------------------------------------------------- Aplicação de template
@dataclass
class ApplyTemplateOutcome:
    created_count: int
    adopted_count: int
    skipped_existing_count: int
    outdated_card_ids: list[int]
    # B-A24 aplicado a colunas: "0 cards criados" com 25 colunas criadas
    # não pode parecer, para o admin, que nada aconteceu.
    columns_created_count: int = 0


def apply_template_to_company(
    db: Session, company, template: DashboardTemplate
) -> ApplyTemplateOutcome:
    """
    Idempotente: cria os `DashboardColumn` e os `DashboardCard` que
    faltam (comparando por `origin_template_column_id` /
    `origin_template_card_id`), nunca sobrescreve nada já existente — só
    sinaliza, em `outdated_card_ids`, quais cards divergem do template
    atual.

    B-A24: cards criados ANTES de O.3 não têm `origin_template_card_id`.
    Para eles, casamos por título e ADOTAMOS o card (gravando o vínculo)
    em vez de criar uma cópia. `adopted_count` deixa isso explícito no
    retorno, para o admin não interpretar "0 criados" como "não fez nada".

    As COLUNAS são criadas numa fase própria ANTES do laço de cards, e
    por dois motivos: o card precisa do `column_id` no momento em que é
    inserido, e a idempotência de coluna repousa na mesma
    `UniqueConstraint` que a de card (R2 do PRD).
    """
    dashboard = db.scalar(select(Dashboard).where(Dashboard.company_id == company.id))
    if dashboard is None:
        raise DashboardNotFoundError("Empresa sem dashboard")

    # ---- Fase 1: colunas ----
    template_columns = list(
        db.scalars(
            select(DashboardTemplateColumn)
            .where(DashboardTemplateColumn.template_id == template.id)
            .order_by(
                DashboardTemplateColumn.position.asc(),
                DashboardTemplateColumn.id.asc(),
            )
        ).all()
    )

    company_columns = list(
        db.scalars(
            select(DashboardColumn)
            .where(DashboardColumn.dashboard_id == dashboard.id)
            .order_by(DashboardColumn.position.asc(), DashboardColumn.id.asc())
        ).all()
    )
    column_by_origin: dict[int, DashboardColumn] = {
        coluna.origin_template_column_id: coluna
        for coluna in company_columns
        if coluna.origin_template_column_id is not None
    }

    faltantes = [
        coluna for coluna in template_columns if coluna.id not in column_by_origin
    ]
    columns_created_count = 0
    if faltantes:
        ultima = company_columns[-1].position if company_columns else None
        for template_column, position in zip(
            faltantes, n_keys_between(ultima, None, len(faltantes))
        ):
            nova = DashboardColumn(
                dashboard_id=dashboard.id,
                name=template_column.name,
                kind=template_column.kind,
                position=position,
                origin_template_column_id=template_column.id,
            )
            db.add(nova)
            column_by_origin[template_column.id] = nova
            columns_created_count += 1
        # Os ids são necessários para gravar `column_id` nos cards abaixo.
        db.flush()

    # ---- Fase 2: cards ----
    template_cards = db.scalars(
        select(DashboardTemplateCard)
        .where(DashboardTemplateCard.template_id == template.id)
        .order_by(
            DashboardTemplateCard.position.asc(),
            DashboardTemplateCard.sort_order.asc(),
            DashboardTemplateCard.id.asc(),
        )
    ).all()

    company_cards = list(
        db.scalars(
            select(DashboardCard).where(DashboardCard.dashboard_id == dashboard.id)
        ).all()
    )

    existing_by_origin: dict[int, DashboardCard] = {
        card.origin_template_card_id: card
        for card in company_cards
        if card.origin_template_card_id is not None
    }

    # Candidatos à adoção: sem vínculo de origem, indexados por título.
    # Um título repetido entre cards órfãos é ambíguo — não adotamos
    # nenhum dos dois, pelo mesmo motivo da migration a3d81f4c7b02.
    orphans_by_title: dict[str, DashboardCard | None] = {}
    for card in company_cards:
        if card.origin_template_card_id is not None:
            continue
        if card.title in orphans_by_title:
            orphans_by_title[card.title] = None  # ambíguo
        else:
            orphans_by_title[card.title] = card

    max_sort = db.scalar(
        select(func.max(DashboardCard.sort_order)).where(
            DashboardCard.dashboard_id == dashboard.id
        )
    )
    next_sort = (max_sort + 1) if max_sort is not None else 0

    # Última posição por coluna, para o card novo nascer no FIM da coluna
    # dele em vez de disputar chave com os que já estão lá.
    ultima_position: dict[int | None, str | None] = {}
    for card in company_cards:
        atual = ultima_position.get(card.column_id)
        if atual is None or card.position > atual:
            ultima_position[card.column_id] = card.position

    created_count = 0
    adopted_count = 0
    skipped_existing_count = 0
    outdated_card_ids: list[int] = []

    for template_card in template_cards:
        coluna_destino = (
            column_by_origin.get(template_card.template_column_id)
            if template_card.template_column_id is not None
            else None
        )
        column_id = coluna_destino.id if coluna_destino is not None else None

        existing = existing_by_origin.get(template_card.id)

        if existing is None:
            orphan = orphans_by_title.get(template_card.title)
            if orphan is not None:
                orphan.origin_template_card_id = template_card.id
                existing_by_origin[template_card.id] = orphan
                orphans_by_title[template_card.title] = None
                adopted_count += 1
                existing = orphan

        if existing is None:
            position = key_between(ultima_position.get(column_id), None)
            ultima_position[column_id] = position
            db.add(
                DashboardCard(
                    dashboard_id=dashboard.id,
                    title=template_card.title,
                    tag=template_card.tag,
                    category_id=template_card.category_id,
                    # Corrige o defeito de origem: até aqui a descrição
                    # do template era descartada em silêncio (O.3).
                    description=template_card.description,
                    column_id=column_id,
                    position=position,
                    origin_template_card_id=template_card.id,
                    hidden=False,
                    status=DashboardCardStatus.EM_ANALISE,
                    sort_order=next_sort,
                )
            )
            next_sort += 1
            created_count += 1
        else:
            skipped_existing_count += 1
            coluna_de_origem = (
                existing.column.origin_template_column_id
                if existing.column is not None
                else None
            )
            if (
                existing.title != template_card.title
                or existing.category_id != template_card.category_id
                or (existing.description or "") != (template_card.description or "")
                or coluna_de_origem != template_card.template_column_id
            ):
                outdated_card_ids.append(existing.id)

    db.flush()
    return ApplyTemplateOutcome(
        created_count=created_count,
        adopted_count=adopted_count,
        skipped_existing_count=skipped_existing_count,
        outdated_card_ids=outdated_card_ids,
        columns_created_count=columns_created_count,
    )


# ---------------------------------------------------------------- Edição em massa
@dataclass
class BulkOperationOutcome:
    affected_count: int


def bulk_update_cards(
    db: Session,
    company: Company,
    *,
    card_ids: list[int],
    operation: str,
    category_id: int | None,
    column_id: int | None = None,
) -> BulkOperationOutcome:
    """
     Aplica uma operação a vários cards de UMA empresa de uma vez — barra
    de ação da aba "Dashboard & Template" (proposta O.4). Filtra por
    `dashboard_id` da própria empresa (não só por `id in card_ids`): um
    id de outra empresa enviado por engano (ou de propósito) é
    silenciosamente ignorado, nunca afeta outro cliente.
    """
    dashboard = db.scalar(select(Dashboard).where(Dashboard.company_id == company.id))
    if dashboard is None:
        raise DashboardNotFoundError("Empresa sem dashboard")

    cards = list(
        db.scalars(
            select(DashboardCard).where(
                DashboardCard.dashboard_id == dashboard.id,
                DashboardCard.id.in_(card_ids),
            )
        ).all()
    )

    affected = 0

    if operation == "hide":
        for card in cards:
            if not card.hidden:
                card.hidden = True
                affected += 1
    elif operation == "unhide":
        for card in cards:
            if card.hidden:
                card.hidden = False
                affected += 1
    elif operation == "remove":
        for card in cards:
            db.delete(card)
            affected += 1
    elif operation == "set_category":
        if (
            category_id is not None
            and db.get(DashboardCardCategory, category_id) is None
        ):
            raise CategoryNotFoundError("Categoria não encontrada")
        tag_value = _category_tag(db, category_id)
        for card in cards:
            card.category_id = category_id
            card.tag = tag_value
            affected += 1
    elif operation == "set_column":
        # Mover 50 cards de coluna em lote (O.4 aplicado ao quadro). As
        # duas validações são as mesmas de `move_card`: coluna do mesmo
        # quadro e coluna que aceita card.
        coluna = db.get(DashboardColumn, column_id) if column_id is not None else None
        if column_id is not None:
            if coluna is None or coluna.dashboard_id != dashboard.id:
                raise ColumnNotFoundError("Coluna não encontrada")
            if coluna.kind == DashboardColumnKind.SECTION:
                raise ColumnKindError(
                    "Coluna do tipo seção não aceita cards — ela é um separador visual"
                )
        ultima = db.scalar(
            select(func.max(DashboardCard.position)).where(
                DashboardCard.column_id.is_(None)
                if column_id is None
                else DashboardCard.column_id == column_id
            )
        )
        for card in cards:
            card.column_id = column_id
            ultima = key_between(ultima, None)
            card.position = ultima
            affected += 1
    elif operation == "restore_from_template":
        origin_ids = {
            c.origin_template_card_id for c in cards if c.origin_template_card_id
        }
        origin_by_id: dict[int, DashboardTemplateCard] = {}
        if origin_ids:
            origin_by_id = {
                tc.id: tc
                for tc in db.scalars(
                    select(DashboardTemplateCard).where(
                        DashboardTemplateCard.id.in_(origin_ids)
                    )
                ).all()
            }
        # Mapa coluna-de-template -> coluna-do-quadro, para restaurar
        # também a coluna e não só os campos de texto.
        column_by_origin = {
            coluna.origin_template_column_id: coluna
            for coluna in db.scalars(
                select(DashboardColumn).where(
                    DashboardColumn.dashboard_id == dashboard.id
                )
            ).all()
            if coluna.origin_template_column_id is not None
        }
        for card in cards:
            origin = (
                origin_by_id.get(card.origin_template_card_id)
                if card.origin_template_card_id
                else None
            )
            # B-M23: card sem origem (ou com origem já excluída, ver
            # B-A25) NÃO conta como restaurado — reportar sucesso aqui
            # mascarava exatamente o problema que o admin precisa ver.
            if origin is None:
                continue
            card.title = origin.title
            card.category_id = origin.category_id
            card.tag = origin.tag
            card.description = origin.description
            if origin.template_column_id is not None:
                coluna = column_by_origin.get(origin.template_column_id)
                if coluna is not None:
                    card.column_id = coluna.id
            affected += 1
    else:
        raise ValueError(f"Operação desconhecida: {operation}")

    db.flush()
    return BulkOperationOutcome(affected_count=affected)
```

---

#### `backend/app/services/dashboard_builder.py`

##### 1. Ação Manual

Abra `backend/app/services/dashboard_builder.py` e substitua o conteúdo inteiro.

> **O retorno `tuple[Company, Dashboard, int]` NÃO muda.** `admin_onboarding.py` o consome
> posicionalmente; acrescentar um quarto elemento quebraria o onboarding sem que nenhum
> teste de dashboard reclamasse.

##### 2. Código Fonte Completo

```python
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company_dashboard import (
    Company,
    Dashboard,
    DashboardCard,
    DashboardTemplate,
    DashboardTemplateCard,
)
from app.models.dashboard_board import DashboardColumn, DashboardTemplateColumn
from app.models.user import User
from app.services.fractional_index import key_between, n_keys_between


def resolve_template(db: Session, template_id: int | None) -> DashboardTemplate:
    if template_id is not None:
        template = db.get(DashboardTemplate, template_id)
        if not template:
            raise ValueError("Template não encontrado")
        return template

    default_template = db.scalar(
        select(DashboardTemplate).where(DashboardTemplate.is_default.is_(True))
    )
    if not default_template:
        raise ValueError("Nenhum template padrão configurado")
    return default_template


def create_company_dashboard_from_template(
    db: Session,
    *,
    principal_user: User,
    company_name: str,
    company_email: str,
    company_phone: str | None = None,
    template: DashboardTemplate | None = None,
) -> tuple[Company, Dashboard, int]:
    """
    Caminho de ONBOARDING: cria empresa, quadro, colunas e cards a partir
    do template, numa transação só.

    O retorno continua sendo `(company, dashboard, cards_criados)` — a
    contagem de colunas não entra na tupla porque `admin_onboarding.py`
    a desempacota posicionalmente. Quem precisa desse número é
    `apply_template_to_company`, que devolve um dataclass e pode crescer
    sem quebrar chamador.
    """
    company = Company(
        name=company_name,
        email=company_email,
        phone=company_phone,
        principal_user_id=principal_user.id,
    )
    db.add(company)
    db.flush()

    dashboard = Dashboard(
        company_id=company.id,
        title=f"Dashboard - {company_name}",
    )
    db.add(dashboard)
    db.flush()

    if template is None:
        db.flush()
        return company, dashboard, 0

    # ---- Colunas antes dos cards: o card precisa do `column_id` no
    # momento do insert, e o mapa template_column_id -> column_id é o que
    # torna esse insert possível numa passada só.
    template_columns = list(
        db.scalars(
            select(DashboardTemplateColumn)
            .where(DashboardTemplateColumn.template_id == template.id)
            .order_by(
                DashboardTemplateColumn.position.asc(),
                DashboardTemplateColumn.id.asc(),
            )
        ).all()
    )

    column_by_template_column: dict[int, DashboardColumn] = {}
    if template_columns:
        for template_column, position in zip(
            template_columns, n_keys_between(None, None, len(template_columns))
        ):
            coluna = DashboardColumn(
                dashboard_id=dashboard.id,
                name=template_column.name,
                kind=template_column.kind,
                position=position,
                origin_template_column_id=template_column.id,
            )
            db.add(coluna)
            column_by_template_column[template_column.id] = coluna
        db.flush()

    template_cards = db.scalars(
        select(DashboardTemplateCard)
        .where(DashboardTemplateCard.template_id == template.id)
        .order_by(
            DashboardTemplateCard.position.asc(),
            DashboardTemplateCard.sort_order.asc(),
            DashboardTemplateCard.id.asc(),
        )
    ).all()

    ultima_position: dict[int | None, str | None] = {}
    created_cards = 0
    for card in template_cards:
        coluna = (
            column_by_template_column.get(card.template_column_id)
            if card.template_column_id is not None
            else None
        )
        column_id = coluna.id if coluna is not None else None

        position = key_between(ultima_position.get(column_id), None)
        ultima_position[column_id] = position

        db.add(
            DashboardCard(
                dashboard_id=dashboard.id,
                title=card.title,
                tag=card.tag,
                category_id=card.category_id,
                # A descrição do template deixa de ser descartada aqui
                # também — o defeito era simétrico nos dois caminhos.
                description=card.description,
                column_id=column_id,
                position=position,
                origin_template_card_id=card.id,
                sort_order=created_cards,
            )
        )
        created_cards += 1

    db.flush()
    return company, dashboard, created_cards
```

---

#### `backend/app/services/company_admin.py`

##### 1. Ação Manual

Este arquivo tem 420+ linhas e apenas **duas** alterações pontuais. Não substitua o arquivo
inteiro; aplique as duas edições abaixo.

> **A verificação primeiro.** Com `Dashboard.columns` marcado `cascade="all, delete-orphan"`
> na Fase 2, o `db.delete(company)` da linha ~400 já remove as colunas via ORM — inclusive
> no SQLite dos testes, que não aplica `ON DELETE CASCADE` sem `PRAGMA foreign_keys=ON`.
> Nada precisa mudar na *mecânica* da exclusão. O que precisa mudar é o **resumo**: ele
> enumera o que foi removido, e uma entidade removida que não aparece no resumo é uma
> exclusão silenciosa.

**Edição 1 — `CompanyDeletionSummaryData` (linha ~42).** Acrescente o campo:

```python
@dataclass
class CompanyDeletionSummaryData:
    company_id: int
    company_name: str
    deleted_principal_user_id: int
    deleted_sub_users: int
    deleted_sub_user_requests: int
    deleted_audits: int
    deleted_audit_controls: int
    deleted_dashboard_cards: int
    deleted_company_messages: int
    evidence_storage_keys: list[str]
    # Contado ANTES do `db.delete(company)`, pelo mesmo motivo que
    # `audit_control_count`: depois do flush o objeto está expirado e a
    # cascata ORM já apagou as linhas.
    deleted_dashboard_columns: int = 0
```

**Edição 2 — dentro de `delete_company_cascade`.** Logo depois de
`data = _load_admin_data(db, company)` (linha ~345), acrescente a contagem; e acrescente o
campo no `return` final (linha ~418):

```python
    # Números "antes" da exclusão, para o resumo devolvido ao frontend —
    # reaproveita a mesma contagem exposta em GET /admin/companies/{id},
    # calculada antes de qualquer `db.delete()` desta função.
    data = _load_admin_data(db, company)

    # Colunas do quadro: removidas pela cascata ORM de `Dashboard.columns`
    # junto com o dashboard, no `db.delete(company)` mais abaixo.
    dashboard_column_count = 0
    if company.dashboard is not None:
        dashboard_column_count = (
            db.scalar(
                select(func.count(DashboardColumn.id)).where(
                    DashboardColumn.dashboard_id == company.dashboard.id
                )
            )
            or 0
        )
```

```python
    return CompanyDeletionSummaryData(
        company_id=company_id,
        company_name=company_name,
        deleted_principal_user_id=principal_user_id,
        deleted_sub_users=len(sub_users),
        deleted_sub_user_requests=len(pending_requests),
        deleted_audits=len(audits),
        deleted_audit_controls=audit_control_count,
        deleted_dashboard_cards=data.dashboard_card_count,
        deleted_dashboard_columns=dashboard_column_count,
        deleted_company_messages=data.company_message_count,
        evidence_storage_keys=evidence_storage_keys,
    )
```

**Edição 3 — import.** No topo do arquivo, junto dos outros imports de model, acrescente:

```python
from app.models.dashboard_board import DashboardColumn
```

---

#### `backend/app/schemas/company_admin.py`

##### 1. Ação Manual

Abra `backend/app/schemas/company_admin.py`, localize `class CompanyDeletionSummary`
(linha 43) e acrescente **uma linha** de campo. Nada mais no arquivo muda.

##### 2. Código Fonte Completo (classe alterada)

```python
class CompanyDeletionSummary(BaseModel):
    """Retorno de DELETE /admin/companies/{id} — números do que foi
    removido em cascata, para o frontend confirmar ao usuário o que
    aconteceu (a mesma contagem que já foi mostrada como aviso antes da
    confirmação, via GET /admin/companies/{id})."""

    company_id: int
    company_name: str
    deleted_principal_user_id: int
    deleted_sub_users: int
    deleted_sub_user_requests: int
    deleted_audits: int
    deleted_audit_controls: int
    deleted_dashboard_cards: int
    # Quadro Kanban: as colunas caem junto com o dashboard, via cascata
    # ORM de `Dashboard.columns`. Aparecem no resumo porque uma entidade
    # removida que não aparece no resumo é uma exclusão silenciosa.
    deleted_dashboard_columns: int = 0
    deleted_company_messages: int
    # B-A26: quantos arquivos de evidência saíram do disco de fato. Zero
    # não é erro — uma empresa pode não ter nenhuma evidência anexada.
    deleted_evidence_files: int = 0
```

---

#### `backend/app/api/v1/companies.py`

##### 1. Ação Manual

Abra `backend/app/api/v1/companies.py`, localize o `return CompanyDeletionSummary(` (linha
~156) e acrescente **uma linha**, logo depois de `deleted_dashboard_cards=`:

```python
        deleted_dashboard_columns=summary.deleted_dashboard_columns,
```

---

### Fase 4 — Schemas e rotas

---

#### `backend/app/schemas/dashboard_board.py`

##### 1. Ação Manual

Crie o arquivo `backend/app/schemas/dashboard_board.py`.

##### 2. Código Fonte Completo

```python
from __future__ import annotations

"""
Contrato HTTP do quadro.

`BoardOut` é a resposta de UMA chamada (`GET /dashboard/companies/{id}/board`)
que traz o quadro pronto: colunas ordenadas, cards já agrupados dentro
delas e o vocabulário de etiquetas. É a decisão D-5 do PRD — antes, o
cliente React montava esse agrupamento em memória
(`groups: CardGroup[]` em `company-dashboard-client.tsx`), e com colunas
persistidas repetir a lógica de ordenação em dois lugares garantiria que
os dois divergissem.

Nos schemas de ENTRADA de movimento (`ColumnMoveIn`, `CardMoveIn`) o
cliente manda ÂNCORAS, nunca a chave de ordenação. Quem calcula a chave é
o servidor, dentro da transação (§4.2 do PRD): é o que elimina a classe
inteira de bugs "dois clientes calcularam a mesma chave" e mantém a
validação de escopo num lugar só.
"""

from typing import Literal

from pydantic import BaseModel, Field


class LabelRef(BaseModel):
    """Etiqueta como ela aparece EMBUTIDA num card."""

    id: int
    name: str
    color: str


class BoardCardOut(BaseModel):
    id: int
    control_code: str | None
    title: str
    description: str | None
    status: str
    position: str
    column_id: int | None
    category_id: int | None
    category_name: str | None
    labels: list[LabelRef]
    hidden: bool
    origin_template_card_id: int | None
    is_outdated: bool


class BoardColumnOut(BaseModel):
    id: int
    name: str
    kind: Literal["COLUMN", "SECTION"]
    position: str
    hidden: bool
    wip_limit: int | None
    cards: list[BoardCardOut]
    card_count: int


class BoardOut(BaseModel):
    dashboard_id: int
    company_id: int
    title: str
    columns: list[BoardColumnOut]
    # Cards órfãos de coluna (FK SET NULL de uma coluna excluída). Ficam
    # num balde próprio em vez de sumir do quadro.
    uncolumned: list[BoardCardOut]
    # Vocabulário completo de etiquetas, para a UI montar o seletor sem
    # uma segunda chamada.
    labels: list[LabelRef]


class ColumnCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    kind: Literal["COLUMN", "SECTION"] = "COLUMN"
    after_column_id: int | None = None


class ColumnUpdateIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    hidden: bool = False
    wip_limit: int | None = Field(default=None, ge=1)


class ColumnMoveIn(BaseModel):
    prev_column_id: int | None = None
    next_column_id: int | None = None


class ColumnOut(BaseModel):
    id: int
    name: str
    kind: Literal["COLUMN", "SECTION"]
    position: str
    hidden: bool
    wip_limit: int | None


class CardMoveIn(BaseModel):
    column_id: int | None = None
    prev_card_id: int | None = None
    next_card_id: int | None = None


class CardUpdateIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    # 20 000 porque as descrições reais são texto normativo longo: o
    # quadro de referência tem descrições de controle com vários
    # parágrafos (PRD §1.1).
    description: str | None = Field(default=None, max_length=20000)
    control_code: str | None = Field(default=None, max_length=40)
    category_id: int | None = None


class CardLabelsIn(BaseModel):
    """
    Semântica de PUT: a lista enviada SUBSTITUI o conjunto inteiro de
    etiquetas do card. Lista vazia remove todas.
    """

    label_ids: list[int] = Field(default_factory=list)
```

---

#### `backend/app/schemas/dashboard_labels.py`

##### 1. Ação Manual

Crie o arquivo `backend/app/schemas/dashboard_labels.py`.

##### 2. Código Fonte Completo

```python
from __future__ import annotations

"""
CRUD do vocabulário de etiquetas — cópia estrutural de
`DashboardCardCategory*` em `dashboard_templates.py`, com os mesmos
limites de `Field`.

A duplicação é deliberada: são dois vocabulários com ciclos de vida
independentes (categoria classifica, etiqueta prioriza), e um schema
genérico compartilhado acoplaria os dois só para poupar 20 linhas.
"""

from pydantic import BaseModel, Field


class DashboardLabelOut(BaseModel):
    id: int
    name: str
    color: str
    sort_order: int


class DashboardLabelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: str = Field(default="#788c5d", max_length=20)
    sort_order: int = Field(default=0)


class DashboardLabelUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: str = Field(max_length=20)
    sort_order: int
```

---

#### `backend/app/schemas/dashboard_runtime.py`

##### 1. Ação Manual

Abra `backend/app/schemas/dashboard_runtime.py` e substitua o conteúdo inteiro.

##### 2. Código Fonte Completo

```python
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal

from app.schemas.dashboard_board import LabelRef


class DashboardCardCreate(BaseModel):
    control_code: str | None = Field(
        default=None, description="Código do controle (opcional)"
    )
    title: str = Field(min_length=1, max_length=160, description="Título do card")
    category_id: int = Field(description="Categoria do card (obrigatória desde O.4)")
    column_id: int | None = Field(
        default=None, description="Coluna do quadro em que o card nasce"
    )
    # 20 000 porque as descrições reais são texto normativo longo (PRD §1.1).
    description: str | None = Field(
        default=None, max_length=20000, description="Texto normativo do controle"
    )
    status: Literal["EM_ANALISE", "PARCIAL", "CONFORME", "NAOCONFORME"] = Field(
        default="EM_ANALISE", description="Status do card"
    )


class DashboardchecklistItem(BaseModel):
    id: int
    title: str
    done: bool


class DashboardUserRef(BaseModel):
    id: int
    full_name: str


class DashboardHistoryOut(BaseModel):
    id: int
    action: str
    created_at: datetime
    actor_user: DashboardUserRef | None = None


class DashboardMessageOut(BaseModel):
    id: int
    message_type: str
    content: str
    created_at: datetime
    author_user: DashboardUserRef | None = None


class DashboardCardDetailOut(BaseModel):
    id: int
    control_code: str | None = None
    title: str
    tag: str
    status: str
    # Campos do quadro. `description` é o que o cliente precisa ler para
    # saber o que entregar (U7) — até aqui esse texto não tinha onde
    # existir na plataforma.
    description: str | None = None
    column_id: int | None = None
    labels: list[LabelRef] = Field(default_factory=list)
    checklist: list[DashboardchecklistItem]
    history: list[DashboardHistoryOut]
    chat: list[DashboardMessageOut]


class CardStatusUpdateIn(BaseModel):
    status: Literal["EM_ANALISE", "PARCIAL", "CONFORME", "NAOCONFORME"]


class CardEntryCreateIn(BaseModel):
    entry_type: Literal["CHECKLIST", "HISTORY", "CHAT_QUESTION", "CHAT_ANSWER"]
    content: str = Field(min_length=1, max_length=1000)


class DashboardCardNoteCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class DashboardCardNoteOut(BaseModel):
    id: int
    content: str
    created_by_user_id: int
    created_by_name: str
    created_at: datetime


class DashboardStatusSummary(BaseModel):
    """
    Contagem agregada de `DashboardCard` por status, em TODAS as empresas
    (excluindo ocultos desde O.4) — alimenta os 4 KPIs do topo da Home.
    """

    em_analise: int
    parcial: int
    conforme: int
    naoconforme: int
```

---

#### `backend/app/schemas/dashboard_templates.py`

##### 1. Ação Manual

Abra `backend/app/schemas/dashboard_templates.py` e substitua o conteúdo inteiro.

##### 2. Código Fonte Completo

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.dashboard_board import LabelRef


class DashboardCardCategoryOut(BaseModel):
    id: int
    name: str
    color: str
    sort_order: int


class DashboardCardCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: str = Field(default="#788c5d", max_length=20)
    sort_order: int = Field(default=0)


class DashboardCardCategoryUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: str = Field(max_length=20)
    sort_order: int


class DashboardTemplateColumnOut(BaseModel):
    id: int
    name: str
    kind: Literal["COLUMN", "SECTION"]
    position: str
    card_count: int


class DashboardTemplateColumnCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    kind: Literal["COLUMN", "SECTION"] = "COLUMN"


class DashboardTemplateColumnUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    kind: Literal["COLUMN", "SECTION"] = "COLUMN"


class DashboardTemplateColumnMove(BaseModel):
    prev_column_id: int | None = None
    next_column_id: int | None = None


class DashboardTemplateCardOut(BaseModel):
    id: int
    title: str
    description: str | None
    category_id: int | None
    category_name: str | None
    template_column_id: int | None
    position: str
    sort_order: int


class DashboardTemplateOut(BaseModel):
    id: int
    name: str
    description: str | None
    is_default: bool
    card_count: int


class DashboardTemplateDetailOut(DashboardTemplateOut):
    cards: list[DashboardTemplateCardOut]
    columns: list[DashboardTemplateColumnOut]


class DashboardTemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    is_default: bool = False


class DashboardTemplateUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    is_default: bool


class DashboardTemplateCardCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    # 20 000, e não 2 000: a descrição de template é a MESMA coisa que a
    # descrição do card (texto normativo do controle), e um limite menor
    # aqui truncaria na origem o que o card consegue guardar.
    description: str | None = Field(default=None, max_length=20000)
    category_id: int | None = None
    template_column_id: int | None = None
    sort_order: int = 0


class DashboardTemplateCardUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=20000)
    category_id: int | None = None
    template_column_id: int | None = None
    sort_order: int


class ApplyTemplateRequest(BaseModel):
    template_id: int


class ApplyTemplateResult(BaseModel):
    created_count: int
    adopted_count: int = 0
    already_applied_count: int
    outdated_card_ids: list[int]
    # B-A24 aplicado a colunas: sem este número, aplicar um template de
    # 25 colunas numa empresa que já tem todos os cards mostraria
    # "0 criados" e o admin concluiria que nada aconteceu.
    columns_created_count: int = 0


class BulkCardOperation(BaseModel):
    card_ids: list[int] = Field(min_length=1)
    operation: Literal[
        "hide",
        "unhide",
        "remove",
        "set_category",
        "set_column",
        "restore_from_template",
    ]
    category_id: int | None = None
    column_id: int | None = None


class BulkCardOperationResult(BaseModel):
    affected_count: int


class DashboardCardWithCategoryOut(BaseModel):
    """
    Saída de card com os campos de O.3 expostos — usada pela listagem de
    cards por empresa a partir de O.4. O endpoint de detalhe de card (GET /dashboard/cards/{id}) não
    muda: checklist/histórico/chat continuam fora do escopo de
    categoria/template.

    Desde o quadro Kanban, carrega também os quatro campos espaciais
    (`column_id`, `position`, `description`, `labels`). São adições — o
    contrato antigo continua válido para qualquer consumidor que os
    ignore.
    """

    id: int
    control_code: str | None
    title: str
    tag: str
    status: str
    category_id: int | None
    category_name: str | None
    hidden: bool
    origin_template_card_id: int | None
    is_outdated: bool
    column_id: int | None = None
    position: str = "a0"
    description: str | None = None
    labels: list[LabelRef] = Field(default_factory=list)
```

---

#### `backend/app/api/v1/dashboard_board.py`

##### 1. Ação Manual

Crie o arquivo `backend/app/api/v1/dashboard_board.py`.

> **A ordem `assert_can` → `_get_*_with_access` é obrigatória em toda rota.** É a ordem de
> `update_card_status` (`dashboard_cards.py:433-434`) e é o que garante **403 para papel
> errado** e **404 para tenant errado**, nunca o inverso. Invertida, um `user` de outra
> empresa descobriria que a coluna existe.

##### 2. Código Fonte Completo

```python
from __future__ import annotations

"""
Rotas do quadro: leitura do board, CRUD de coluna, mover card e etiquetar.

Usa o MESMO prefixo `/dashboard` de `dashboard_cards.py` — é um arquivo
separado só para não fazer aquele, que já tem 600 linhas, crescer mais.
O FastAPI mescla os dois sem conflito desde que nenhum path se repita, e
`router.py` registra este DEPOIS daquele, de propósito: nenhuma rota nova
pode sombrear `/dashboard/cards/{card_id}`, que já existe.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.access import (
    get_column_with_access,
    get_company_with_access,
    resolve_owner_user_id,
)
from app.core.policy import Action, assert_can
from app.db.session import get_db
from app.models.company_dashboard import (
    Company,
    Dashboard,
    DashboardCard,
    DashboardCardCategory,
)
from app.models.dashboard_board import DashboardColumn, DashboardColumnKind, DashboardLabel
from app.models.user import User
from app.schemas.dashboard_board import (
    BoardCardOut,
    BoardColumnOut,
    BoardOut,
    CardLabelsIn,
    CardMoveIn,
    CardUpdateIn,
    ColumnCreateIn,
    ColumnMoveIn,
    ColumnOut,
    ColumnUpdateIn,
    LabelRef,
)
from app.services.dashboard_board import (
    AnchorMismatchError,
    BoardData,
    ColumnKindError,
    ColumnNotEmptyError,
    ColumnNotFoundError,
    LabelNotFoundError,
    create_column,
    delete_column,
    get_board,
    move_card,
    move_column,
    set_card_labels,
    update_column,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard Board"])


def _get_card_with_access(
    db: Session, card_id: int, current_user: User
) -> DashboardCard:
    """
    Cópia intencional de `dashboard_cards.py::_get_card_with_access`.

    Duplicar 20 linhas aqui é melhor que importar de um router para
    outro: routers não se importam entre si nesta base, e mover o helper
    para `core/access.py` exigiria mexer no arquivo de 600 linhas no mesmo
    PR do quadro — exatamente o risco que a Spec pede para evitar.
    """
    row = db.execute(
        select(DashboardCard, Company)
        .join(Dashboard, Dashboard.id == DashboardCard.dashboard_id)
        .join(Company, Company.id == Dashboard.company_id)
        .where(DashboardCard.id == card_id)
    ).first()
    if row is not None:
        card, company = row
        if current_user.role == "admin":
            return card
        if company.principal_user_id == resolve_owner_user_id(current_user):
            return card

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Card não encontrado ou sem acesso",
    )


def _label_refs(labels: list[DashboardLabel]) -> list[LabelRef]:
    return [
        LabelRef(id=label.id, name=label.name, color=label.color) for label in labels
    ]


def _card_out(card: DashboardCard, *, is_outdated: bool) -> BoardCardOut:
    return BoardCardOut(
        id=card.id,
        control_code=card.control_code,
        title=card.title,
        description=card.description,
        status=card.status.value,
        position=card.position,
        column_id=card.column_id,
        category_id=card.category_id,
        category_name=card.category.name if card.category else None,
        labels=_label_refs(card.labels),
        hidden=card.hidden,
        origin_template_card_id=card.origin_template_card_id,
        is_outdated=is_outdated,
    )


def _board_out(board: BoardData, company: Company) -> BoardOut:
    return BoardOut(
        dashboard_id=board.dashboard.id,
        company_id=company.id,
        title=board.dashboard.title,
        columns=[
            BoardColumnOut(
                id=grupo.column.id,
                name=grupo.column.name,
                kind=grupo.column.kind.value,
                position=grupo.column.position,
                hidden=grupo.column.hidden,
                wip_limit=grupo.column.wip_limit,
                cards=[
                    _card_out(card, is_outdated=card.id in board.outdated_card_ids)
                    for card in grupo.cards
                ],
                card_count=len(grupo.cards),
            )
            for grupo in board.columns
        ],
        uncolumned=[
            _card_out(card, is_outdated=card.id in board.outdated_card_ids)
            for card in board.uncolumned
        ],
        labels=_label_refs(board.labels),
    )


def _column_out(column: DashboardColumn) -> ColumnOut:
    return ColumnOut(
        id=column.id,
        name=column.name,
        kind=column.kind.value,
        position=column.position,
        hidden=column.hidden,
        wip_limit=column.wip_limit,
    )


# ------------------------------------------------------------- Leitura


@router.get("/companies/{company_id}/board", response_model=BoardOut)
def get_company_board(
    company_id: int,
    include_hidden: bool = Query(default=False),
    search: str = Query(default=""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BoardOut:
    """
    Quadro completo da empresa.

    Leitura permitida a **admin, user e sub-user** — é a mesma decisão de
    `list_cards_by_company`: o cliente tem direito de ver o quadro da
    própria empresa (U6/U7), só não de rearranjá-lo. Por isso a rota usa
    `get_company_with_access` e NÃO `require_admin`.

    Empresa sem dashboard devolve um quadro vazio, não 404: uma empresa
    antiga criada à mão pode não ter dashboard, e 404 aqui faria a tela do
    cliente quebrar em vez de mostrar "nada ainda".
    """
    company = get_company_with_access(db, company_id, current_user)

    dashboard = db.scalar(select(Dashboard).where(Dashboard.company_id == company.id))
    if dashboard is None:
        return BoardOut(
            dashboard_id=0,
            company_id=company.id,
            title=f"Dashboard - {company.name}",
            columns=[],
            uncolumned=[],
            labels=[],
        )

    board = get_board(db, dashboard, include_hidden=include_hidden, search=search)
    return _board_out(board, company)


# -------------------------------------------------------------- Colunas


@router.post(
    "/companies/{company_id}/columns",
    response_model=ColumnOut,
    status_code=status.HTTP_201_CREATED,
)
def create_board_column(
    company_id: int,
    payload: ColumnCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ColumnOut:
    assert_can(Action.MANAGE_COLUMN, current_user.role)  # permissão
    company = get_company_with_access(db, company_id, current_user)  # escopo

    dashboard = db.scalar(select(Dashboard).where(Dashboard.company_id == company.id))
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Empresa sem dashboard")

    try:
        column = create_column(
            db,
            dashboard,
            name=payload.name,
            kind=DashboardColumnKind(payload.kind),
            after_column_id=payload.after_column_id,
        )
        db.commit()
    except ColumnNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))

    db.refresh(column)
    return _column_out(column)


@router.patch("/columns/{column_id}", response_model=ColumnOut)
def update_board_column(
    column_id: int,
    payload: ColumnUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ColumnOut:
    assert_can(Action.MANAGE_COLUMN, current_user.role)
    column = get_column_with_access(db, column_id, current_user)

    update_column(
        db,
        column,
        name=payload.name,
        hidden=payload.hidden,
        wip_limit=payload.wip_limit,
    )
    db.commit()
    db.refresh(column)
    return _column_out(column)


@router.patch("/columns/{column_id}/move", response_model=ColumnOut)
def move_board_column(
    column_id: int,
    payload: ColumnMoveIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ColumnOut:
    assert_can(Action.MANAGE_COLUMN, current_user.role)
    column = get_column_with_access(db, column_id, current_user)

    try:
        move_column(
            db,
            column,
            prev_column_id=payload.prev_column_id,
            next_column_id=payload.next_column_id,
        )
        db.commit()
    except AnchorMismatchError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))

    db.refresh(column)
    return _column_out(column)


@router.delete("/columns/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_board_column(
    column_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    assert_can(Action.MANAGE_COLUMN, current_user.role)
    column = get_column_with_access(db, column_id, current_user)

    try:
        delete_column(db, column)
        db.commit()
    except ColumnNotEmptyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


# ---------------------------------------------------------- Cards


@router.patch("/cards/{card_id}/move", response_model=BoardCardOut)
def move_board_card(
    card_id: int,
    payload: CardMoveIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> BoardCardOut:
    """
    O endpoint de arrastar. Um `UPDATE` no card movido, e nenhum outro
    card reescrito (CA-06).

    Coluna de destino de OUTRA empresa devolve **404** (CA-07), não 403 e
    muito menos 200: quem não tem acesso à coluna não pode nem descobrir
    que ela existe (B-B23).
    """
    assert_can(Action.MOVE_CARD, current_user.role)  # permissão
    card = _get_card_with_access(db, card_id, current_user)  # escopo

    try:
        move_card(
            db,
            card,
            column_id=payload.column_id,
            prev_card_id=payload.prev_card_id,
            next_card_id=payload.next_card_id,
        )
        db.commit()
    except ColumnNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
    except ColumnKindError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except AnchorMismatchError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))

    db.refresh(card)
    return _card_out(card, is_outdated=False)


@router.patch("/cards/{card_id}", response_model=BoardCardOut)
def update_board_card(
    card_id: int,
    payload: CardUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> BoardCardOut:
    """
    Edita os campos de TEXTO do card. Não toca em `status` — status é
    declaração de conformidade e continua tendo rota própria, com
    `Action.SET_CARD_STATUS` (B-A23).
    """
    card = _get_card_with_access(db, card_id, current_user)

    if payload.category_id is not None:
        category = db.get(DashboardCardCategory, payload.category_id)
        if category is None:
            raise HTTPException(status_code=404, detail="Categoria não encontrada")
        card.tag = category.name

    card.title = payload.title
    card.description = payload.description
    card.control_code = payload.control_code
    card.category_id = payload.category_id
    db.commit()
    db.refresh(card)
    return _card_out(card, is_outdated=False)


@router.put("/cards/{card_id}/labels", response_model=list[LabelRef])
def replace_card_labels(
    card_id: int,
    payload: CardLabelsIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[LabelRef]:
    """
    Substitui o conjunto de etiquetas do card (semântica de `PUT`).

    CA-12: etiquetar **não** altera `status`. São eixos ortogonais —
    "quão crítico é" e "está conforme" são perguntas diferentes, e
    misturá-las criaria duas fontes de verdade para a segunda.
    """
    assert_can(Action.MANAGE_LABEL, current_user.role)
    card = _get_card_with_access(db, card_id, current_user)

    try:
        labels = set_card_labels(db, card, payload.label_ids)
        db.commit()
    except LabelNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))

    return _label_refs(labels)
```

---

#### `backend/app/api/v1/dashboard_labels.py`

##### 1. Ação Manual

Crie o arquivo `backend/app/api/v1/dashboard_labels.py`.

##### 2. Código Fonte Completo

```python
from __future__ import annotations

"""
CRUD do vocabulário de etiquetas.

Cópia estrutural de `dashboard_categories.py` inteiro, incluindo o helper
`_to_out` e a tradução `IntegrityError` → 409. São dois vocabulários
distintos (classificação e criticidade) com o mesmo formato de CRUD;
generalizá-los num router único acoplaria os dois para poupar 40 linhas.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.policy import Action, assert_can
from app.db.session import get_db
from app.models.dashboard_board import DashboardLabel
from app.models.user import User
from app.schemas.dashboard_labels import (
    DashboardLabelCreate,
    DashboardLabelOut,
    DashboardLabelUpdate,
)
from app.services.dashboard_board import (
    LabelInUseError,
    LabelNotFoundError,
    create_label,
    delete_label,
    list_labels,
    update_label,
)

router = APIRouter(prefix="/admin/dashboard-labels", tags=["Admin — Etiquetas de Card"])


def _to_out(label: DashboardLabel) -> DashboardLabelOut:
    return DashboardLabelOut(
        id=label.id,
        name=label.name,
        color=label.color,
        sort_order=label.sort_order,
    )


@router.get("", response_model=list[DashboardLabelOut])
def list_dashboard_labels(
    db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> list[DashboardLabelOut]:
    return [_to_out(label) for label in list_labels(db)]


@router.post("", response_model=DashboardLabelOut, status_code=status.HTTP_201_CREATED)
def create_dashboard_label(
    payload: DashboardLabelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> DashboardLabelOut:
    assert_can(Action.MANAGE_LABEL, current_user.role)
    try:
        label = create_label(
            db, name=payload.name, color=payload.color, sort_order=payload.sort_order
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma etiqueta com esse nome",
        )
    return _to_out(label)


@router.patch("/{label_id}", response_model=DashboardLabelOut)
def update_dashboard_label(
    label_id: int,
    payload: DashboardLabelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> DashboardLabelOut:
    assert_can(Action.MANAGE_LABEL, current_user.role)
    try:
        label = update_label(
            db,
            label_id,
            name=payload.name,
            color=payload.color,
            sort_order=payload.sort_order,
        )
        db.commit()
    except LabelNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Etiqueta não encontrada")
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma etiqueta com esse nome",
        )
    return _to_out(label)


@router.delete("/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dashboard_label(
    label_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    assert_can(Action.MANAGE_LABEL, current_user.role)
    try:
        delete_label(db, label_id)
        db.commit()
    except LabelNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Etiqueta não encontrada")
    except LabelInUseError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
```

---

#### `backend/app/api/v1/router.py`

##### 1. Ação Manual

Abra `backend/app/api/v1/router.py` e substitua o conteúdo inteiro.

> **A ordem importa.** `dashboard_board_router` tem de vir **depois** de
> `dashboard_cards_router`: os dois usam `prefix="/dashboard"` e o FastAPI resolve por ordem
> de registro. Registrado antes, `PATCH /dashboard/cards/{card_id}` (novo) poderia sombrear
> rotas já existentes sob o mesmo prefixo.

##### 2. Código Fonte Completo

```python
from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.client import router as client_router
from app.api.v1.admin import router as admin_router
from app.api.v1.sub_users import router as sub_users_router
from app.api.v1.admin_onboarding import router as admin_onboarding_router
from app.api.v1.dashboard_cards import router as dashboard_cards_router
from app.api.v1.dashboard_board import router as dashboard_board_router
from app.api.v1.dashboard_categories import router as dashboard_categories_router
from app.api.v1.dashboard_labels import router as dashboard_labels_router
from app.api.v1.dashboard_templates import router as dashboard_templates_router
from app.api.v1.company_messages import router as company_messages_router
from app.api.v1.companies import router as companies_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(users_router)
router.include_router(client_router)
router.include_router(admin_router)
router.include_router(sub_users_router)
router.include_router(admin_onboarding_router)
router.include_router(dashboard_cards_router)
# DEPOIS de dashboard_cards_router: os dois compartilham prefix="/dashboard"
# e o FastAPI resolve por ordem de registro.
router.include_router(dashboard_board_router)
router.include_router(dashboard_categories_router)
router.include_router(dashboard_labels_router)
router.include_router(dashboard_templates_router)
router.include_router(company_messages_router)
router.include_router(companies_router)
```

---

#### `backend/app/api/v1/dashboard_cards.py`

##### 1. Ação Manual

Abra `backend/app/api/v1/dashboard_cards.py` e substitua o conteúdo inteiro.

> **Arquivo de risco 🟠 alto:** 600 linhas cobertas por `test_dashboard_cards.py`,
> `test_card_internals_visibility.py`, `test_authorization_matrix.py` e
> `test_query_budget.py`. Rode as quatro suítes logo depois de salvar:
>
> ```bash
> cd backend
> pytest tests/test_dashboard_cards.py tests/test_card_internals_visibility.py \
>        tests/test_authorization_matrix.py tests/test_query_budget.py -v
> ```

##### 2. Código Fonte Completo

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_admin
from app.core.access import get_company_with_access, resolve_owner_user_id
from app.db.session import get_db
from app.models.company_dashboard import (
    Company,
    Dashboard,
    DashboardCard,
    DashboardCardCategory,
    DashboardCardchecklistItem,
    DashboardCardHistoryEntry,
    DashboardCardMessage,
    DashboardCardNote,
    DashboardCardStatus,
    DashboardMessageType,
    DashboardTemplate,
)
from app.models.dashboard_board import (
    DashboardColumn,
    DashboardColumnKind,
    DashboardLabel,
)
from app.models.user import User
from app.schemas.dashboard_board import LabelRef
from app.schemas.dashboard_runtime import (
    CardEntryCreateIn,
    CardStatusUpdateIn,
    DashboardCardCreate,
    DashboardCardDetailOut,
    DashboardCardNoteCreate,
    DashboardCardNoteOut,
    DashboardchecklistItem,
    DashboardHistoryOut,
    DashboardMessageOut,
    DashboardStatusSummary,
    DashboardUserRef,
)
from app.schemas.dashboard_templates import (
    ApplyTemplateRequest,
    ApplyTemplateResult,
    BulkCardOperation,
    BulkCardOperationResult,
    DashboardCardWithCategoryOut,
)
from app.services.dashboard_board import ColumnKindError, ColumnNotFoundError
from app.services.dashboard_template_admin import (
    CategoryNotFoundError,
    DashboardNotFoundError,
    apply_template_to_company,
    bulk_update_cards,
)
from app.services.fractional_index import key_between

from app.core.policy import Action, assert_can, can

ADMIN_ONLY_ENTRY_TYPES = frozenset({"CHECKLIST", "HISTORY", "CHAT_ANSWER"})

router = APIRouter(prefix="/dashboard", tags=["Dashboard Runtime"])


def _get_card_with_access(
    db: Session, card_id: int, current_user: User
) -> DashboardCard:
    stmt = (
        select(DashboardCard, Company)
        .join(Dashboard, Dashboard.id == DashboardCard.dashboard_id)
        .join(Company, Company.id == Dashboard.company_id)
        .where(DashboardCard.id == card_id)
    )
    row = db.execute(stmt).first()
    if row is not None:
        card, company = row
        if current_user.role == "admin":
            return card
        if company.principal_user_id == resolve_owner_user_id(current_user):
            return card

    # 404 também para card de outra empresa (B-B23) — ver
    # core/access.py::get_company_with_access.
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Card não encontrado ou sem acesso",
    )


def _card_is_outdated(card: DashboardCard) -> bool:
    """
    O card divergiu da definição de template da qual nasceu?

    Desde o quadro Kanban compara quatro coisas, não duas: título,
    categoria, **coluna** e **descrição**. Um card que divergiu do
    template na coluna em que está, ou no texto normativo, está tão
    desatualizado quanto um que divergiu no título — e é justamente a
    divergência de texto que o admin precisa ver para decidir se restaura.

    A comparação de coluna NÃO é `card.column_id != origin.template_column_id`:
    esses dois números vivem em tabelas diferentes (`dashboard_columns` e
    `dashboard_template_columns`) e compará-los diretamente marcaria todo
    card como desatualizado. O que se compara é a ORIGEM da coluna atual
    do card com a coluna de template declarada na definição.
    """
    if card.origin_template_card_id is None or card.origin_template_card is None:
        return False
    origin = card.origin_template_card

    coluna_de_origem = (
        card.column.origin_template_column_id if card.column is not None else None
    )

    return (
        card.title != origin.title
        or card.category_id != origin.category_id
        or (card.description or "") != (origin.description or "")
        or coluna_de_origem != origin.template_column_id
    )


def _label_refs(labels: list[DashboardLabel]) -> list[LabelRef]:
    return [
        LabelRef(id=label.id, name=label.name, color=label.color) for label in labels
    ]


def _card_out(card: DashboardCard) -> DashboardCardWithCategoryOut:
    """Serialização única do card de listagem — antes ela estava repetida
    em três rotas, e os campos novos teriam de entrar nas três."""
    return DashboardCardWithCategoryOut(
        id=card.id,
        control_code=card.control_code,
        title=card.title,
        tag=card.tag,
        status=card.status.value,
        category_id=card.category_id,
        category_name=card.category.name if card.category else None,
        hidden=card.hidden,
        origin_template_card_id=card.origin_template_card_id,
        is_outdated=_card_is_outdated(card),
        column_id=card.column_id,
        position=card.position,
        description=card.description,
        labels=_label_refs(card.labels),
    )


@router.get("/status-summary", response_model=DashboardStatusSummary)
def get_dashboard_status_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DashboardStatusSummary:
    """
    Contagem agregada de cards por status, em UMA única query SQL agrupada
    — alimenta os 4 KPIs do topo da Home (/private/admin), substituindo o
    padrão anterior de buscar a lista completa de cards de TODAS as
    empresas só para somar localmente no frontend (`listAllCardsAction`,
    removida em O.1). Desde O.4, cards ocultos (`hidden=True`) não entram
    na contagem — um card oculto não é mais "trabalho em aberto" aos
    olhos do resumo.
    """
    rows = db.execute(
        select(DashboardCard.status, func.count(DashboardCard.id))
        .where(DashboardCard.hidden.is_(False))
        .group_by(DashboardCard.status)
    ).all()
    counts = {status_enum.value: 0 for status_enum in DashboardCardStatus}
    for status_value, count in rows:
        counts[status_value.value] = count
    return DashboardStatusSummary(
        em_analise=counts["EM_ANALISE"],
        parcial=counts["PARCIAL"],
        conforme=counts["CONFORME"],
        naoconforme=counts["NAOCONFORME"],
    )


@router.get(
    "/companies/{company_id}/cards", response_model=list[DashboardCardWithCategoryOut]
)
def list_cards_by_company(
    company_id: int,
    search: str = Query(default=""),
    include_hidden: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DashboardCardWithCategoryOut]:
    """
    Listagem plana de cards da empresa.

    Continua existindo depois do quadro: é o que alimenta consumidores que
    não querem o agrupamento (busca, exportação, checagens). Quem quer o
    quadro pronto usa `GET /dashboard/companies/{id}/board`.
    """
    get_company_with_access(db, company_id, current_user)

    dashboard = db.scalar(select(Dashboard).where(Dashboard.company_id == company_id))
    if not dashboard:
        return []

    stmt = select(DashboardCard).where(DashboardCard.dashboard_id == dashboard.id)
    if not include_hidden:
        stmt = stmt.where(DashboardCard.hidden.is_(False))
    if search.strip():
        query = f"%{search.strip()}%"
        stmt = stmt.where(
            (DashboardCard.title.ilike(query))
            | (DashboardCard.control_code.ilike(query))
        )

    cards = db.scalars(
        stmt.options(
            selectinload(DashboardCard.category),
            selectinload(DashboardCard.origin_template_card),
            # Sem estes dois, 215 cards custam 430 queries extras (B9):
            # `labels` é M:N e `column` é lida por `_card_is_outdated`.
            selectinload(DashboardCard.labels),
            selectinload(DashboardCard.column),
        )
        # A ordenação passa a ser a do quadro (`position`), e não mais
        # `sort_order` — os dois convergem para os dados existentes
        # porque o backfill da migration c8f1a3e57b90 gerou `position` na
        # ordem `sort_order ASC, id ASC`.
        .order_by(DashboardCard.position.asc(), DashboardCard.id.asc())
    ).all()

    return [_card_out(card) for card in cards]


@router.post(
    "/companies/{company_id}/cards",
    response_model=DashboardCardWithCategoryOut,
    status_code=status.HTTP_201_CREATED,
)
def create_card_for_company(
    company_id: int,
    payload: DashboardCardCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DashboardCardWithCategoryOut:
    """
    Desde O.4, `category_id` é obrigatório (o "+ Adicionar card" da aba
    Dashboard & Template sempre pede uma categoria) — `tag` deixou de ser
    aceito no payload e é derivado do nome da categoria, mesma regra já
    aplicada a `dashboard_template_admin.py::_category_tag`.

    Desde o quadro Kanban, o card nasce DENTRO de uma coluna: o
    "+ Adicionar card" agora vive no rodapé de cada coluna, e a posição é
    calculada com `key_between` a partir do fim daquela coluna — não mais
    `max(sort_order) + 1` sobre o dashboard inteiro.
    """
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada"
        )

    dashboard = db.scalar(select(Dashboard).where(Dashboard.company_id == company_id))
    if not dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard não encontrado"
        )

    category = db.get(DashboardCardCategory, payload.category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")

    column: DashboardColumn | None = None
    if payload.column_id is not None:
        column = db.get(DashboardColumn, payload.column_id)
        # Coluna de outro quadro é indistinguível de coluna inexistente
        # para quem chama (B-B23).
        if column is None or column.dashboard_id != dashboard.id:
            raise HTTPException(status_code=404, detail="Coluna não encontrada")
        if column.kind == DashboardColumnKind.SECTION:
            raise HTTPException(
                status_code=422,
                detail="Coluna do tipo seção não aceita cards — ela é um separador visual",
            )

    max_sort = db.scalar(
        select(func.max(DashboardCard.sort_order)).where(
            DashboardCard.dashboard_id == dashboard.id
        )
    )
    next_sort = (max_sort + 1) if max_sort is not None else 0

    ultima_position = db.scalar(
        select(func.max(DashboardCard.position)).where(
            DashboardCard.dashboard_id == dashboard.id,
            DashboardCard.column_id.is_(None)
            if column is None
            else DashboardCard.column_id == column.id,
        )
    )

    card = DashboardCard(
        dashboard_id=dashboard.id,
        control_code=payload.control_code,
        title=payload.title,
        tag=category.name,
        category_id=category.id,
        description=payload.description,
        column_id=column.id if column is not None else None,
        position=key_between(ultima_position, None),
        status=DashboardCardStatus(payload.status),
        sort_order=next_sort,
    )
    db.add(card)
    db.commit()
    db.refresh(card)

    return _card_out(card)


@router.post(
    "/companies/{company_id}/apply-template",
    response_model=ApplyTemplateResult,
)
def apply_template_to_company_endpoint(
    company_id: int,
    payload: ApplyTemplateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> ApplyTemplateResult:
    """
    Aplica um template numa empresa já existente — proposta O.4, §3.5 do
    documento de origem ("Planta do Dashboard"). Idempotente: chamado 2x
    seguidas com o mesmo template, a segunda chamada não cria nada novo
    (ver services/dashboard_template_admin.py::apply_template_to_company).
    """
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    template = db.get(DashboardTemplate, payload.template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template não encontrado")

    try:
        outcome = apply_template_to_company(db, company, template)
        db.commit()
    except DashboardNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Empresa sem dashboard")

    return ApplyTemplateResult(
        created_count=outcome.created_count,
        adopted_count=outcome.adopted_count,
        already_applied_count=outcome.skipped_existing_count,
        outdated_card_ids=outcome.outdated_card_ids,
        columns_created_count=outcome.columns_created_count,
    )


@router.patch(
    "/companies/{company_id}/cards/bulk",
    response_model=BulkCardOperationResult,
)
def bulk_update_company_cards(
    company_id: int,
    payload: BulkCardOperation,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> BulkCardOperationResult:
    """
    Ocultar / reexibir / mudar categoria / mudar coluna / remover /
    restaurar do template, em lote, sobre os cards de UMA empresa — a
    peça de UI que faltava para "50 cards" deixar de ser 50 cliques
    (proposta O.4, §3.4 do documento de origem). `card_ids` de outra
    empresa são filtrados silenciosamente pelo service (ver
    bulk_update_cards).
    """
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    if payload.operation == "set_category" and payload.category_id is None:
        raise HTTPException(
            status_code=422,
            detail="category_id é obrigatório para a operação set_category",
        )

    if payload.operation == "set_column" and payload.column_id is None:
        raise HTTPException(
            status_code=422,
            detail="column_id é obrigatório para a operação set_column",
        )

    try:
        outcome = bulk_update_cards(
            db,
            company,
            card_ids=payload.card_ids,
            operation=payload.operation,
            category_id=payload.category_id,
            column_id=payload.column_id,
        )
        db.commit()
    except DashboardNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Empresa sem dashboard")
    except CategoryNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    except ColumnNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Coluna não encontrada")
    except ColumnKindError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))

    return BulkCardOperationResult(affected_count=outcome.affected_count)


@router.get("/cards/{card_id}", response_model=DashboardCardDetailOut)
def get_card_details(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardCardDetailOut:
    """
    Detalhe de um card.

    O chat é bilateral e sempre visível às duas partes. O **checklist** e o
    **histórico** são registro interno da equipe de auditoria (B-A28): o
    cliente vê listas vazias, não 403 — o card existe e ele tem direito de
    vê-lo, apenas não a essas duas coleções. Manter o mesmo formato de
    resposta evita quebrar qualquer consumidor e mantém a semântica
    honesta ("nada a exibir para você aqui"), em vez de fingir que o card
    não tem checklist.

    Efeito colateral bem-vindo: para papel não-admin, duas queries deixam
    de ser executadas.

    A `description` NÃO segue essa regra: ela é o texto normativo do
    controle, e é exatamente o que o cliente precisa ler para saber o que
    entregar (U7). Vai para os dois papéis.
    """
    card = _get_card_with_access(db, card_id, current_user)

    pode_ver_interno = can(Action.READ_CARD_INTERNALS, current_user.role)

    checklist: list[DashboardCardchecklistItem] = []
    history: list[DashboardCardHistoryEntry] = []
    if pode_ver_interno:
        checklist = list(
            db.scalars(
                select(DashboardCardchecklistItem)
                .where(DashboardCardchecklistItem.card_id == card.id)
                .order_by(DashboardCardchecklistItem.id.asc())
            ).all()
        )
        history = list(
            db.scalars(
                select(DashboardCardHistoryEntry)
                .where(DashboardCardHistoryEntry.card_id == card.id)
                .order_by(DashboardCardHistoryEntry.id.asc())
            ).all()
        )

    chat = db.scalars(
        select(DashboardCardMessage)
        .where(DashboardCardMessage.card_id == card.id)
        .order_by(DashboardCardMessage.id.asc())
    ).all()

    user_ids = {
        item.actor_user_id for item in history if item.actor_user_id is not None
    }
    user_ids |= {item.author_user_id for item in chat}
    users_by_id: dict[int, User] = {}
    if user_ids:
        rows = db.scalars(select(User).where(User.id.in_(user_ids))).all()
        users_by_id = {u.id: u for u in rows}

    def _user_ref(user_id: int | None) -> DashboardUserRef | None:
        user = users_by_id.get(user_id) if user_id is not None else None
        if user is None:
            return None
        return DashboardUserRef(id=user.id, full_name=user.full_name)

    return DashboardCardDetailOut(
        id=card.id,
        control_code=card.control_code,
        title=card.title,
        tag=card.tag,
        status=card.status.value,
        description=card.description,
        column_id=card.column_id,
        labels=_label_refs(card.labels),
        checklist=[
            DashboardchecklistItem(
                id=item.id,
                title=item.title,
                done=item.done,
            )
            for item in checklist
        ],
        history=[
            DashboardHistoryOut(
                id=item.id,
                action=item.action,
                created_at=item.created_at,
                actor_user=_user_ref(item.actor_user_id),
            )
            for item in history
        ],
        chat=[
            DashboardMessageOut(
                id=item.id,
                message_type=item.message_type.value,
                content=item.content,
                created_at=item.created_at,
                author_user=_user_ref(item.author_user_id),
            )
            for item in chat
        ],
    )


@router.patch("/cards/{card_id}/status", response_model=DashboardCardWithCategoryOut)
def update_card_status(
    card_id: int,
    payload: CardStatusUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> DashboardCardWithCategoryOut:
    """
    Status de conformidade é declaração DO AUDITOR sobre o auditado —
    restrito a admin (B-A23). O cliente continua VENDO o status em
    GET /dashboard/companies/{id}/cards; só não pode alterá-lo.
    """
    assert_can(Action.SET_CARD_STATUS, current_user.role)  # permissão
    card = _get_card_with_access(db, card_id, current_user)  # escopo
    card.status = DashboardCardStatus(payload.status)
    db.commit()
    db.refresh(card)

    return _card_out(card)


@router.post("/cards/{card_id}/entries", status_code=status.HTTP_201_CREATED)
def create_card_entry(
    card_id: int,
    payload: CardEntryCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    card = _get_card_with_access(db, card_id, current_user)

    # B-A23: checklist, histórico e resposta de chat são registro do
    # auditor. Só CHAT_QUESTION é escrita legítima do cliente.
    if payload.entry_type in ADMIN_ONLY_ENTRY_TYPES and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas a equipe de auditoria pode registrar esse tipo de entrada",
        )

    if payload.entry_type == "CHECKLIST":
        db.add(
            DashboardCardchecklistItem(
                card_id=card.id, title=payload.content, done=False
            )
        )
    elif payload.entry_type == "HISTORY":
        db.add(
            DashboardCardHistoryEntry(
                card_id=card.id,
                action=payload.content,
                actor_user_id=current_user.id,
            )
        )
    elif payload.entry_type == "CHAT_QUESTION":
        db.add(
            DashboardCardMessage(
                card_id=card.id,
                author_user_id=current_user.id,
                message_type=DashboardMessageType.QUESTION,
                content=payload.content,
            )
        )
    elif payload.entry_type == "CHAT_ANSWER":
        db.add(
            DashboardCardMessage(
                card_id=card.id,
                author_user_id=current_user.id,
                message_type=DashboardMessageType.ANSWER,
                content=payload.content,
            )
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de entrada inválido"
        )

    db.commit()
    return {"message": "Entrada criada com sucesso"}


@router.patch("/checklist-items/{item_id}/toggle", status_code=status.HTTP_200_OK)
def toggle_checklist_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    """
    Checklist interno da equipe de auditoria — restrito a admin (B-A23).
    A checagem de posse por empresa deixa de ser necessária: o admin tem
    acesso a todas as empresas por definição, e o cliente não tem acesso
    nenhum a esta rota.
    """
    item = db.get(DashboardCardchecklistItem, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado"
        )

    item.done = not item.done
    db.commit()
    db.refresh(item)
    return {"ok": True, "done": item.done}


@router.post(
    "/cards/{card_id}/notes",
    response_model=DashboardCardNoteOut,
    status_code=status.HTTP_201_CREATED,
)
def create_card_note(
    card_id: int,
    payload: DashboardCardNoteCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> DashboardCardNoteOut:
    """
    Cria uma nota interna no card — anotação da equipe de auditoria, distinta
    do chat (DashboardCardMessage), que é o canal de Q&A com o cliente.
    Restrito a admin: notas são um registro interno, não visível/editável
    pelo cliente (ao contrário do chat e do checklist).
    """
    card = db.get(DashboardCard, card_id)
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Card não encontrado"
        )

    note = DashboardCardNote(
        card_id=card.id,
        content=payload.content,
        created_by_user_id=admin.id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    return DashboardCardNoteOut(
        id=note.id,
        content=note.content,
        created_by_user_id=note.created_by_user_id,
        created_by_name=admin.full_name,
        created_at=note.created_at,
    )


@router.get("/cards/{card_id}/notes", response_model=list[DashboardCardNoteOut])
def list_card_notes(
    card_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[DashboardCardNoteOut]:
    card = db.get(DashboardCard, card_id)
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Card não encontrado"
        )

    rows = db.execute(
        select(DashboardCardNote, User.full_name)
        .join(User, User.id == DashboardCardNote.created_by_user_id)
        .where(DashboardCardNote.card_id == card_id)
        .order_by(DashboardCardNote.id.asc())
    ).all()

    return [
        DashboardCardNoteOut(
            id=note.id,
            content=note.content,
            created_by_user_id=note.created_by_user_id,
            created_by_name=full_name,
            created_at=note.created_at,
        )
        for note, full_name in rows
    ]
```

---

#### `backend/app/api/v1/dashboard_templates.py`

##### 1. Ação Manual

Abra `backend/app/api/v1/dashboard_templates.py` e substitua o conteúdo inteiro. Além dos
campos novos nos cards de template, o arquivo ganha **5 rotas** de coluna de template.

##### 2. Código Fonte Completo

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.policy import Action, assert_can
from app.db.session import get_db
from app.models.company_dashboard import DashboardTemplateCard
from app.models.dashboard_board import DashboardColumnKind, DashboardTemplateColumn
from app.models.user import User
from app.schemas.dashboard_templates import (
    DashboardTemplateCardCreate,
    DashboardTemplateCardOut,
    DashboardTemplateCardUpdate,
    DashboardTemplateColumnCreate,
    DashboardTemplateColumnMove,
    DashboardTemplateColumnOut,
    DashboardTemplateColumnUpdate,
    DashboardTemplateCreate,
    DashboardTemplateDetailOut,
    DashboardTemplateOut,
    DashboardTemplateUpdate,
)
from app.services.dashboard_template_admin import (
    CategoryNotFoundError,
    DefaultTemplateDeletionError,
    TemplateCardNotFoundError,
    TemplateColumnInUseError,
    TemplateColumnNotFoundError,
    TemplateInUseError,
    TemplateNotFoundError,
    add_template_card,
    add_template_column,
    create_template,
    delete_template,
    delete_template_card,
    delete_template_column,
    get_template_detail,
    list_template_columns,
    list_templates,
    move_template_column,
    update_template,
    update_template_card,
    update_template_column,
)

router = APIRouter(prefix="/admin/templates", tags=["Admin — Templates de Dashboard"])


def _card_to_out(card: DashboardTemplateCard) -> DashboardTemplateCardOut:
    return DashboardTemplateCardOut(
        id=card.id,
        title=card.title,
        description=card.description,
        category_id=card.category_id,
        category_name=card.category.name if card.category else None,
        template_column_id=card.template_column_id,
        position=card.position,
        sort_order=card.sort_order,
    )


def _column_to_out(
    column: DashboardTemplateColumn, card_count: int
) -> DashboardTemplateColumnOut:
    return DashboardTemplateColumnOut(
        id=column.id,
        name=column.name,
        kind=column.kind.value,
        position=column.position,
        card_count=card_count,
    )


def _build_detail(template) -> DashboardTemplateDetailOut:
    # A ordenação primária é `position` (a do quadro); `sort_order` entra
    # como desempate para os templates anteriores à migration
    # c8f1a3e57b90, cujas posições foram todas geradas no mesmo backfill.
    cards = sorted(template.cards, key=lambda c: (c.position, c.sort_order, c.id))
    colunas = sorted(template.columns, key=lambda c: (c.position, c.id))

    cards_por_coluna: dict[int, int] = {}
    for card in cards:
        if card.template_column_id is not None:
            cards_por_coluna[card.template_column_id] = (
                cards_por_coluna.get(card.template_column_id, 0) + 1
            )

    return DashboardTemplateDetailOut(
        id=template.id,
        name=template.name,
        description=template.description,
        is_default=template.is_default,
        card_count=len(cards),
        cards=[_card_to_out(c) for c in cards],
        columns=[
            _column_to_out(coluna, cards_por_coluna.get(coluna.id, 0))
            for coluna in colunas
        ],
    )


@router.get("", response_model=list[DashboardTemplateOut])
def list_dashboard_templates(
    db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> list[DashboardTemplateOut]:
    rows = list_templates(db)
    return [
        DashboardTemplateOut(
            id=row.template.id,
            name=row.template.name,
            description=row.template.description,
            is_default=row.template.is_default,
            card_count=row.card_count,
        )
        for row in rows
    ]


@router.post(
    "", response_model=DashboardTemplateOut, status_code=status.HTTP_201_CREATED
)
def create_dashboard_template(
    payload: DashboardTemplateCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DashboardTemplateOut:
    try:
        template = create_template(
            db,
            name=payload.name,
            description=payload.description,
            is_default=payload.is_default,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um template com esse nome",
        )
    return DashboardTemplateOut(
        id=template.id,
        name=template.name,
        description=template.description,
        is_default=template.is_default,
        card_count=0,
    )


@router.get("/{template_id}", response_model=DashboardTemplateDetailOut)
def get_dashboard_template(
    template_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DashboardTemplateDetailOut:
    try:
        template = get_template_detail(db, template_id)
    except TemplateNotFoundError:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    return _build_detail(template)


@router.patch("/{template_id}", response_model=DashboardTemplateDetailOut)
def update_dashboard_template(
    template_id: int,
    payload: DashboardTemplateUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DashboardTemplateDetailOut:
    try:
        template = update_template(
            db,
            template_id,
            name=payload.name,
            description=payload.description,
            is_default=payload.is_default,
        )
        db.commit()
    except TemplateNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Template não encontrado")
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um template com esse nome",
        )
    db.refresh(template)
    return _build_detail(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dashboard_template(
    template_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    try:
        delete_template(db, template_id)
        db.commit()
    except TemplateNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Template não encontrado")
    except (DefaultTemplateDeletionError, TemplateInUseError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


# ------------------------------------------------- Colunas de template


@router.get(
    "/{template_id}/columns", response_model=list[DashboardTemplateColumnOut]
)
def list_dashboard_template_columns(
    template_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[DashboardTemplateColumnOut]:
    try:
        template = get_template_detail(db, template_id)
    except TemplateNotFoundError:
        raise HTTPException(status_code=404, detail="Template não encontrado")

    cards_por_coluna: dict[int, int] = {}
    for card in template.cards:
        if card.template_column_id is not None:
            cards_por_coluna[card.template_column_id] = (
                cards_por_coluna.get(card.template_column_id, 0) + 1
            )

    return [
        _column_to_out(coluna, cards_por_coluna.get(coluna.id, 0))
        for coluna in list_template_columns(db, template_id)
    ]


@router.post(
    "/{template_id}/columns",
    response_model=DashboardTemplateColumnOut,
    status_code=status.HTTP_201_CREATED,
)
def create_dashboard_template_column(
    template_id: int,
    payload: DashboardTemplateColumnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> DashboardTemplateColumnOut:
    assert_can(Action.MANAGE_TEMPLATE, current_user.role)
    try:
        coluna = add_template_column(
            db,
            template_id,
            name=payload.name,
            kind=DashboardColumnKind(payload.kind),
        )
        db.commit()
    except TemplateNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Template não encontrado")
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma coluna com esse nome neste template",
        )
    db.refresh(coluna)
    return _column_to_out(coluna, 0)


@router.patch(
    "/{template_id}/columns/{column_id}",
    response_model=DashboardTemplateColumnOut,
)
def update_dashboard_template_column(
    template_id: int,
    column_id: int,
    payload: DashboardTemplateColumnUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> DashboardTemplateColumnOut:
    assert_can(Action.MANAGE_TEMPLATE, current_user.role)
    try:
        coluna = update_template_column(
            db,
            column_id,
            name=payload.name,
            kind=DashboardColumnKind(payload.kind),
        )
        if coluna.template_id != template_id:
            db.rollback()
            raise HTTPException(
                status_code=404, detail="Coluna de template não encontrada"
            )
        db.commit()
    except TemplateColumnNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Coluna de template não encontrada")
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma coluna com esse nome neste template",
        )
    db.refresh(coluna)
    return _column_to_out(coluna, 0)


@router.patch(
    "/{template_id}/columns/{column_id}/move",
    response_model=DashboardTemplateColumnOut,
)
def move_dashboard_template_column(
    template_id: int,
    column_id: int,
    payload: DashboardTemplateColumnMove,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> DashboardTemplateColumnOut:
    assert_can(Action.MANAGE_TEMPLATE, current_user.role)
    try:
        coluna = move_template_column(
            db,
            column_id,
            prev_column_id=payload.prev_column_id,
            next_column_id=payload.next_column_id,
        )
        if coluna.template_id != template_id:
            db.rollback()
            raise HTTPException(
                status_code=404, detail="Coluna de template não encontrada"
            )
        db.commit()
    except TemplateColumnNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Coluna de template não encontrada")
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    db.refresh(coluna)
    return _column_to_out(coluna, 0)


@router.delete(
    "/{template_id}/columns/{column_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_dashboard_template_column(
    template_id: int,
    column_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    assert_can(Action.MANAGE_TEMPLATE, current_user.role)
    coluna = db.get(DashboardTemplateColumn, column_id)
    if coluna is None or coluna.template_id != template_id:
        raise HTTPException(status_code=404, detail="Coluna de template não encontrada")

    try:
        delete_template_column(db, column_id)
        db.commit()
    except TemplateColumnNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Coluna de template não encontrada")
    except TemplateColumnInUseError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


# --------------------------------------------------- Cards de template


@router.post(
    "/{template_id}/cards",
    response_model=DashboardTemplateCardOut,
    status_code=status.HTTP_201_CREATED,
)
def create_dashboard_template_card(
    template_id: int,
    payload: DashboardTemplateCardCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DashboardTemplateCardOut:
    try:
        card = add_template_card(
            db,
            template_id,
            title=payload.title,
            description=payload.description,
            category_id=payload.category_id,
            template_column_id=payload.template_column_id,
            sort_order=payload.sort_order,
        )
        db.commit()
    except TemplateNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Template não encontrado")
    except CategoryNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    except TemplateColumnNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Coluna de template não encontrada")
    db.refresh(card)
    return _card_to_out(card)


@router.delete(
    "/template-cards/{template_card_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_dashboard_template_card(
    template_card_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    try:
        delete_template_card(db, template_card_id)
        db.commit()
    except TemplateCardNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Card de template não encontrado")
    except TemplateInUseError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.patch(
    "/template-cards/{template_card_id}", response_model=DashboardTemplateCardOut
)
def update_dashboard_template_card(
    template_card_id: int,
    payload: DashboardTemplateCardUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DashboardTemplateCardOut:
    try:
        card = update_template_card(
            db,
            template_card_id,
            title=payload.title,
            description=payload.description,
            category_id=payload.category_id,
            template_column_id=payload.template_column_id,
            sort_order=payload.sort_order,
        )
        db.commit()
    except TemplateCardNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Card de template não encontrado")
    except CategoryNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    except TemplateColumnNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Coluna de template não encontrada")
    db.refresh(card)
    return _card_to_out(card)
```

---

### Fase 5 — Testes de backend

---

#### `backend/tests/conftest.py`

##### 1. Ação Manual

Abra `backend/tests/conftest.py` e substitua o conteúdo inteiro. São três fixtures novas
(`dashboard_column`, `board_com_3_colunas`, `etiquetas`) e um ajuste em `dashboard_card`.

##### 2. Código Fonte Completo

```python
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - registra todos os models em Base.metadata
from app.core.jwt import create_access_token
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.audit import Audit, AuditStatus
from app.models.audit_control import AuditControl, AuditControlStatus
from app.models.company_dashboard import Company, Dashboard, DashboardCard
from app.models.control_catalog import ControlCatalog
from app.models.dashboard_board import (
    DashboardColumn,
    DashboardColumnKind,
    DashboardLabel,
)
from app.models.user import User
from app.services.fractional_index import n_keys_between

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    """
    Zera os contadores do slowapi entre testes.

    O rate limit de `/auth/login` (5/min por IP) é global ao processo e
    todos os testes chegam do mesmo "IP". Sem este reset, um teste que
    faça login passa isolado e falha na suíte completa, com 429 no lugar
    do status esperado — uma falha que depende da ORDEM de execução e
    aponta para o lugar errado.

    As duas instâncias de `Limiter` são resetadas porque são objetos
    distintos: `app.main.limiter` (registrada em `app.state`) e
    `app.api.v1.auth.limiter` (a que os decoradores de /login e /refresh
    de fato usam).
    """
    from app.api.v1 import auth as auth_module
    from app import main as main_module

    for limiter in (main_module.limiter, auth_module.limiter):
        try:
            limiter.reset()
        except Exception:  # pragma: no cover - backend de storage sem reset
            pass
    yield


@pytest.fixture(autouse=True)
def _isolate_uploads(tmp_path, monkeypatch):
    """Evita que os testes gravem arquivos reais em backend/uploads/."""
    from app.services import storage

    test_upload_dir = tmp_path / "uploads"
    test_upload_dir.mkdir()
    monkeypatch.setattr(storage, "UPLOAD_DIR", test_upload_dir)


@pytest.fixture
def db():
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db) -> User:
    admin = User(
        full_name="Admin Teste",
        email="admin@test.com",
        password_hash=hash_password("Admin123!"),
        role="admin",
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def admin_token(admin_user: User) -> str:
    return create_access_token(subject=str(admin_user.id), role="admin")


@pytest.fixture
def principal_user(db) -> User:
    user = User(
        full_name="Cliente Teste",
        email="cliente@test.com",
        password_hash=hash_password("Cliente123!"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_token(principal_user: User) -> str:
    return create_access_token(subject=str(principal_user.id), role="user")


@pytest.fixture
def sub_user(db, principal_user: User) -> User:
    sub = User(
        full_name="Sub-usuário Teste",
        email="subusuario@test.com",
        password_hash=hash_password("SubUser123!"),
        role="sub-user",
        parent_user_id=principal_user.id,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@pytest.fixture
def sub_user_token(sub_user: User) -> str:
    return create_access_token(subject=str(sub_user.id), role="sub-user")


@pytest.fixture
def catalog_control(db) -> ControlCatalog:
    control = ControlCatalog(
        code="5.1",
        title="Política de Segurança da Informação",
        description="Política deve ser definida, aprovada, comunicada e revisada.",
        expected_evidence="Política assinada",
    )
    db.add(control)
    db.commit()
    db.refresh(control)
    return control


@pytest.fixture
def company(db, principal_user: User) -> Company:
    company_obj = Company(
        name="Empresa Teste",
        email="empresa@test.com",
        phone="11999999999",
        principal_user_id=principal_user.id,
    )
    db.add(company_obj)
    db.commit()
    db.refresh(company_obj)
    return company_obj


@pytest.fixture
def dashboard(db, company: Company) -> Dashboard:
    dashboard_obj = Dashboard(company_id=company.id, title=f"Dashboard - {company.name}")
    db.add(dashboard_obj)
    db.commit()
    db.refresh(dashboard_obj)
    return dashboard_obj


@pytest.fixture
def dashboard_column(db, dashboard: Dashboard) -> DashboardColumn:
    """Uma coluna comum (`kind=COLUMN`) no quadro da empresa de teste."""
    coluna = DashboardColumn(
        dashboard_id=dashboard.id,
        name="Controles Organizacionais",
        kind=DashboardColumnKind.COLUMN,
        position="a0",
    )
    db.add(coluna)
    db.commit()
    db.refresh(coluna)
    return coluna


@pytest.fixture
def board_com_3_colunas(db, dashboard: Dashboard) -> list[DashboardColumn]:
    """
    Quadro de três colunas, a do meio sendo uma `SECTION`.

    A seção no meio (e não na ponta) é deliberada: é a disposição do
    quadro real (`ISO 27001:2022 >>` separa blocos normativos) e é a que
    quebra código que assume "toda coluna aceita card".
    """
    posicoes = n_keys_between(None, None, 3)
    colunas = [
        DashboardColumn(
            dashboard_id=dashboard.id,
            name="A fazer",
            kind=DashboardColumnKind.COLUMN,
            position=posicoes[0],
        ),
        DashboardColumn(
            dashboard_id=dashboard.id,
            name="ISO 27001:2022 >>",
            kind=DashboardColumnKind.SECTION,
            position=posicoes[1],
        ),
        DashboardColumn(
            dashboard_id=dashboard.id,
            name="Concluído",
            kind=DashboardColumnKind.COLUMN,
            position=posicoes[2],
        ),
    ]
    db.add_all(colunas)
    db.commit()
    for coluna in colunas:
        db.refresh(coluna)
    return colunas


@pytest.fixture
def etiquetas(db) -> list[DashboardLabel]:
    """Subconjunto do vocabulário semeado pela migration c8f1a3e57b90."""
    labels = [
        DashboardLabel(name="Item Critico", color="#96311D", sort_order=0),
        DashboardLabel(name="Alta Criticidade", color="#C2410C", sort_order=1),
        DashboardLabel(name="Baixa Criticidade", color="#2C5A8C", sort_order=3),
    ]
    db.add_all(labels)
    db.commit()
    for label in labels:
        db.refresh(label)
    return labels


@pytest.fixture
def dashboard_card(db, dashboard: Dashboard, dashboard_column: DashboardColumn) -> DashboardCard:
    card = DashboardCard(
        dashboard_id=dashboard.id,
        control_code="5.1",
        title="Política de Segurança da Informação",
        tag="governanca",
        column_id=dashboard_column.id,
        position="a0",
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


@pytest.fixture
def audit_with_control(db, principal_user: User, catalog_control: ControlCatalog):
    audit = Audit(
        name="Auditoria Teste",
        client_user_id=principal_user.id,
        status=AuditStatus.ACTIVE,
    )
    db.add(audit)
    db.flush()

    audit_control = AuditControl(
        audit_id=audit.id,
        control_id=catalog_control.id,
        status=AuditControlStatus.EM_ANALISE,
    )
    db.add(audit_control)
    db.commit()
    db.refresh(audit_control)
    return audit, audit_control
```

---

#### `backend/tests/test_dashboard_board.py`

##### 1. Ação Manual

Crie o arquivo `backend/tests/test_dashboard_board.py`.

##### 2. Código Fonte Completo

```python
"""
CA-05 a CA-08: o quadro, o arrasto e as duas regras que impedem o arrasto
de corromper dados.

Duas classes de defeito justificam este arquivo, e nenhuma delas produz
erro visível na hora:

1. **Chave fora de ordem.** O servidor calcula a `position` a partir das
   âncoras que o cliente manda. Âncoras de outra coluna produziriam uma
   chave "válida" que coloca o card no lugar errado — e a rota
   responderia 200. Por isso `AnchorMismatchError` → 422.

2. **Escrita em cascata.** O índice fracionário existe para que um
   arrasto custe UM UPDATE. Uma regressão que volte a reindexar a coluna
   inteira continua passando em todo teste funcional; só um contador de
   queries a pega (CA-06).

O terceiro eixo é isolamento entre empresas: mover um card para a coluna
de outra empresa responde **404**, não 403 e muito menos 200 (B-B23).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.models.company_dashboard import Company, Dashboard, DashboardCard
from app.models.dashboard_board import DashboardColumn, DashboardColumnKind
from app.models.user import User
from app.services.fractional_index import n_keys_between
from tests.test_query_budget import ContadorDeQueries


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _criar_cards(db, dashboard, coluna, titulos: list[str]) -> list[DashboardCard]:
    cards = [
        DashboardCard(
            dashboard_id=dashboard.id,
            title=titulo,
            tag="t",
            column_id=coluna.id if coluna is not None else None,
            position=position,
        )
        for titulo, position in zip(titulos, n_keys_between(None, None, len(titulos)))
    ]
    db.add_all(cards)
    db.commit()
    for card in cards:
        db.refresh(card)
    return cards


def _outra_empresa(db) -> tuple[Company, Dashboard, DashboardColumn]:
    """Empresa completamente separada, para os testes de isolamento."""
    outro_usuario = User(
        full_name="Outro Cliente",
        email="outro@test.com",
        password_hash=hash_password("Outro123!"),
        role="user",
    )
    db.add(outro_usuario)
    db.flush()

    outra = Company(
        name="Outra Empresa",
        email="outra@test.com",
        principal_user_id=outro_usuario.id,
    )
    db.add(outra)
    db.flush()

    outro_dashboard = Dashboard(company_id=outra.id, title="Dash Outra")
    db.add(outro_dashboard)
    db.flush()

    outra_coluna = DashboardColumn(
        dashboard_id=outro_dashboard.id, name="Coluna Alheia", position="a0"
    )
    db.add(outra_coluna)
    db.commit()
    db.refresh(outra_coluna)
    return outra, outro_dashboard, outra_coluna


# ------------------------------------------------------- CA-05: leitura


def test_board_devolve_colunas_e_cards_ordenados_por_position(
    client: TestClient, db, admin_token: str, company, dashboard, board_com_3_colunas
):
    a_fazer, _secao, concluido = board_com_3_colunas
    _criar_cards(db, dashboard, a_fazer, ["Card 1", "Card 2", "Card 3"])
    _criar_cards(db, dashboard, concluido, ["Card 4"])

    resposta = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board",
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["company_id"] == company.id
    assert [c["name"] for c in corpo["columns"]] == [
        "A fazer",
        "ISO 27001:2022 >>",
        "Concluído",
    ]
    assert [c["title"] for c in corpo["columns"][0]["cards"]] == [
        "Card 1",
        "Card 2",
        "Card 3",
    ]
    assert corpo["columns"][0]["card_count"] == 3
    assert corpo["columns"][1]["cards"] == []
    assert [c["title"] for c in corpo["columns"][2]["cards"]] == ["Card 4"]
    assert corpo["uncolumned"] == []


def test_board_embute_as_etiquetas_do_card(
    client: TestClient, db, admin_token: str, company, dashboard_card, etiquetas
):
    dashboard_card.labels = [etiquetas[0], etiquetas[2]]
    db.commit()

    corpo = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board",
        headers=_headers(admin_token),
    ).json()

    card = corpo["columns"][0]["cards"][0]
    assert [etiqueta["name"] for etiqueta in card["labels"]] == [
        "Item Critico",
        "Baixa Criticidade",
    ]
    assert card["labels"][0]["color"] == "#96311D"


def test_card_sem_coluna_cai_no_balde_uncolumned(
    client: TestClient, db, admin_token: str, company, dashboard, dashboard_column
):
    _criar_cards(db, dashboard, None, ["Órfão"])

    corpo = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board",
        headers=_headers(admin_token),
    ).json()

    assert [c["title"] for c in corpo["uncolumned"]] == ["Órfão"]


def test_coluna_arquivada_so_aparece_com_include_hidden(
    client: TestClient, db, admin_token: str, company, dashboard_column
):
    dashboard_column.hidden = True
    db.commit()

    sem_flag = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board",
        headers=_headers(admin_token),
    ).json()
    assert sem_flag["columns"] == []

    com_flag = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board?include_hidden=true",
        headers=_headers(admin_token),
    ).json()
    assert [c["name"] for c in com_flag["columns"]] == ["Controles Organizacionais"]


def test_busca_no_board_filtra_por_titulo_e_codigo(
    client: TestClient, db, admin_token: str, company, dashboard, dashboard_column
):
    _criar_cards(db, dashboard, dashboard_column, ["Backup", "Gestão de Acesso"])

    corpo = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board?search=backup",
        headers=_headers(admin_token),
    ).json()

    assert [c["title"] for c in corpo["columns"][0]["cards"]] == ["Backup"]


def test_cliente_le_o_quadro_da_propria_empresa(
    client: TestClient, user_token: str, company, dashboard_column
):
    """U6/CA-11: leitura é permitida a user e sub-user."""
    resposta = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board",
        headers=_headers(user_token),
    )
    assert resposta.status_code == 200


def test_empresa_sem_dashboard_devolve_quadro_vazio(
    client: TestClient, db, admin_token: str, company
):
    """404 aqui quebraria a tela do cliente em vez de mostrar 'nada ainda'."""
    resposta = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board",
        headers=_headers(admin_token),
    )
    assert resposta.status_code == 200
    assert resposta.json()["columns"] == []


# ------------------------------------------------- CA-06: um UPDATE só


def test_mover_card_executa_exatamente_um_update(
    client: TestClient, db, admin_token: str, dashboard, dashboard_column
):
    """
    CA-06. É o teste que justifica o índice fracionário existir: com
    `sort_order: Integer`, mover o primeiro card para o fim reescreveria
    todos os outros.
    """
    cards = _criar_cards(
        db, dashboard, dashboard_column, [f"Card {i}" for i in range(10)]
    )
    primeiro, ultimo = cards[0], cards[-1]

    with ContadorDeQueries() as contador:
        resposta = client.patch(
            f"/api/v1/dashboard/cards/{primeiro.id}/move",
            json={
                "column_id": dashboard_column.id,
                "prev_card_id": ultimo.id,
                "next_card_id": None,
            },
            headers=_headers(admin_token),
        )

    assert resposta.status_code == 200
    updates = [s for s in contador.statements if s.strip().upper().startswith("UPDATE")]
    assert len(updates) == 1, (
        f"{len(updates)} UPDATEs para mover 1 card — a reindexação em cascata "
        f"voltou:\n" + "\n".join(f"  {s}" for s in updates)
    )

    db.expire_all()
    ordem = [
        c.title
        for c in db.query(DashboardCard)
        .filter(DashboardCard.column_id == dashboard_column.id)
        .order_by(DashboardCard.position.asc())
        .all()
    ]
    assert ordem[-1] == "Card 0"


def test_mover_card_entre_colunas_atualiza_column_id(
    client: TestClient, db, admin_token: str, dashboard, board_com_3_colunas
):
    a_fazer, _secao, concluido = board_com_3_colunas
    card = _criar_cards(db, dashboard, a_fazer, ["Card"])[0]

    resposta = client.patch(
        f"/api/v1/dashboard/cards/{card.id}/move",
        json={"column_id": concluido.id, "prev_card_id": None, "next_card_id": None},
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 200
    assert resposta.json()["column_id"] == concluido.id


# ------------------------------------------- CA-07: isolamento (404)


def test_mover_card_para_coluna_de_outra_empresa_devolve_404(
    client: TestClient, db, admin_token: str, dashboard_card
):
    """
    CA-07. 404, não 403: distinguir "coluna não existe" de "coluna existe
    e não é sua" permitiria enumerar as colunas da plataforma (B-B23).
    """
    _outra, _outro_dashboard, coluna_alheia = _outra_empresa(db)

    resposta = client.patch(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/move",
        json={"column_id": coluna_alheia.id, "prev_card_id": None, "next_card_id": None},
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 404


def test_cliente_de_outra_empresa_nao_ve_o_quadro(
    client: TestClient, db, user_token: str
):
    outra, _outro_dashboard, _coluna = _outra_empresa(db)

    resposta = client.get(
        f"/api/v1/dashboard/companies/{outra.id}/board",
        headers=_headers(user_token),
    )
    assert resposta.status_code == 404


# --------------------------------------- Regras que protegem a ordem


def test_soltar_card_em_coluna_secao_devolve_422(
    client: TestClient, db, admin_token: str, dashboard, board_com_3_colunas
):
    a_fazer, secao, _concluido = board_com_3_colunas
    card = _criar_cards(db, dashboard, a_fazer, ["Card"])[0]

    resposta = client.patch(
        f"/api/v1/dashboard/cards/{card.id}/move",
        json={"column_id": secao.id, "prev_card_id": None, "next_card_id": None},
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 422
    assert "seção" in resposta.json()["detail"]


def test_ancora_de_outra_coluna_devolve_422(
    client: TestClient, db, admin_token: str, dashboard, board_com_3_colunas
):
    """
    A âncora pertence à coluna de ORIGEM, não à de destino. Sem esta
    validação o servidor geraria uma chave a partir de uma posição de
    outra coluna — e o card apareceria em lugar arbitrário, com 200.
    """
    a_fazer, _secao, concluido = board_com_3_colunas
    cards_origem = _criar_cards(db, dashboard, a_fazer, ["A", "B"])
    _criar_cards(db, dashboard, concluido, ["C"])

    resposta = client.patch(
        f"/api/v1/dashboard/cards/{cards_origem[0].id}/move",
        json={
            "column_id": concluido.id,
            "prev_card_id": cards_origem[1].id,  # âncora da coluna errada
            "next_card_id": None,
        },
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 422


def test_ancoras_invertidas_devolvem_422(
    client: TestClient, db, admin_token: str, dashboard, dashboard_column
):
    cards = _criar_cards(db, dashboard, dashboard_column, ["A", "B", "C"])

    resposta = client.patch(
        f"/api/v1/dashboard/cards/{cards[0].id}/move",
        json={
            "column_id": dashboard_column.id,
            # prev depois de next: fora de ordem.
            "prev_card_id": cards[2].id,
            "next_card_id": cards[1].id,
        },
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 422


# ------------------------------------------------ CA-08: CRUD de coluna


def test_criar_coluna_no_fim_do_quadro(
    client: TestClient, admin_token: str, company, dashboard_column
):
    resposta = client.post(
        f"/api/v1/dashboard/companies/{company.id}/columns",
        json={"name": "Em revisão", "kind": "COLUMN", "after_column_id": None},
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 201
    assert resposta.json()["name"] == "Em revisão"
    assert resposta.json()["position"] > dashboard_column.position


def test_criar_coluna_depois_de_outra(
    client: TestClient, admin_token: str, company, board_com_3_colunas
):
    a_fazer, secao, _concluido = board_com_3_colunas

    nova = client.post(
        f"/api/v1/dashboard/companies/{company.id}/columns",
        json={"name": "Meio", "kind": "COLUMN", "after_column_id": a_fazer.id},
        headers=_headers(admin_token),
    ).json()

    assert a_fazer.position < nova["position"] < secao.position


def test_renomear_e_arquivar_coluna(
    client: TestClient, admin_token: str, dashboard_column
):
    resposta = client.patch(
        f"/api/v1/dashboard/columns/{dashboard_column.id}",
        json={"name": "Renomeada", "hidden": True, "wip_limit": 5},
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["name"] == "Renomeada"
    assert corpo["hidden"] is True
    assert corpo["wip_limit"] == 5


def test_mover_coluna_reordena(
    client: TestClient, admin_token: str, board_com_3_colunas
):
    a_fazer, _secao, concluido = board_com_3_colunas

    resposta = client.patch(
        f"/api/v1/dashboard/columns/{a_fazer.id}/move",
        json={"prev_column_id": concluido.id, "next_column_id": None},
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 200
    assert resposta.json()["position"] > concluido.position


def test_excluir_coluna_com_card_visivel_devolve_409(
    client: TestClient, db, admin_token: str, dashboard, dashboard_column
):
    """CA-08, primeira metade. Mensagem em português, com o número de
    cards — o admin precisa saber quantos mover."""
    _criar_cards(db, dashboard, dashboard_column, ["Card"])

    resposta = client.delete(
        f"/api/v1/dashboard/columns/{dashboard_column.id}",
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 409
    assert "card(s)" in resposta.json()["detail"]


def test_excluir_coluna_vazia_devolve_204(
    client: TestClient, admin_token: str, dashboard_column
):
    """CA-08, segunda metade."""
    resposta = client.delete(
        f"/api/v1/dashboard/columns/{dashboard_column.id}",
        headers=_headers(admin_token),
    )
    assert resposta.status_code == 204


def test_card_oculto_nao_impede_excluir_a_coluna(
    client: TestClient, db, admin_token: str, dashboard, dashboard_column
):
    """
    Card oculto já não é trabalho em aberto (decisão de O.4 em
    `get_dashboard_status_summary`). Exigir reexibir 30 cards arquivados
    só para apagar uma coluna seria burocracia sem ganho.
    """
    card = _criar_cards(db, dashboard, dashboard_column, ["Arquivado"])[0]
    card.hidden = True
    db.commit()

    resposta = client.delete(
        f"/api/v1/dashboard/columns/{dashboard_column.id}",
        headers=_headers(admin_token),
    )
    assert resposta.status_code == 204


def test_excluir_coluna_nao_apaga_o_card(
    client: TestClient, db, admin_token: str, dashboard, board_com_3_colunas
):
    """A FK é SET NULL: o card cai em `uncolumned`, nunca some."""
    a_fazer, _secao, concluido = board_com_3_colunas
    card = _criar_cards(db, dashboard, a_fazer, ["Card"])[0]

    client.patch(
        f"/api/v1/dashboard/cards/{card.id}/move",
        json={"column_id": concluido.id, "prev_card_id": None, "next_card_id": None},
        headers=_headers(admin_token),
    )
    resposta = client.delete(
        f"/api/v1/dashboard/columns/{a_fazer.id}", headers=_headers(admin_token)
    )

    assert resposta.status_code == 204
    db.expire_all()
    assert db.get(DashboardCard, card.id) is not None


def test_coluna_de_outra_empresa_devolve_404(
    client: TestClient, db, admin_token: str, user_token: str
):
    _outra, _outro_dashboard, coluna_alheia = _outra_empresa(db)

    resposta = client.patch(
        f"/api/v1/dashboard/columns/{coluna_alheia.id}",
        json={"name": "X", "hidden": False, "wip_limit": None},
        headers=_headers(user_token),
    )
    assert resposta.status_code in (403, 404)


# ---------------------------------------------------- Edição de card


def test_editar_card_grava_descricao(
    client: TestClient, admin_token: str, dashboard_card
):
    resposta = client.patch(
        f"/api/v1/dashboard/cards/{dashboard_card.id}",
        json={
            "title": "Política revisada",
            "description": "**Controle** — Convém que a política seja aprovada.",
            "control_code": "5.1",
            "category_id": None,
        },
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["title"] == "Política revisada"
    assert corpo["description"].startswith("**Controle**")


def test_bulk_set_column_move_varios_cards(
    client: TestClient, db, admin_token: str, company, dashboard, board_com_3_colunas
):
    a_fazer, _secao, concluido = board_com_3_colunas
    cards = _criar_cards(db, dashboard, a_fazer, ["A", "B", "C"])

    resposta = client.patch(
        f"/api/v1/dashboard/companies/{company.id}/cards/bulk",
        json={
            "card_ids": [c.id for c in cards],
            "operation": "set_column",
            "column_id": concluido.id,
        },
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 200
    assert resposta.json()["affected_count"] == 3

    db.expire_all()
    assert all(
        db.get(DashboardCard, c.id).column_id == concluido.id for c in cards
    )


def test_bulk_set_column_sem_column_id_devolve_422(
    client: TestClient, db, admin_token: str, company, dashboard, dashboard_column
):
    cards = _criar_cards(db, dashboard, dashboard_column, ["A"])

    resposta = client.patch(
        f"/api/v1/dashboard/companies/{company.id}/cards/bulk",
        json={"card_ids": [cards[0].id], "operation": "set_column"},
        headers=_headers(admin_token),
    )
    assert resposta.status_code == 422


def test_bulk_set_column_para_secao_devolve_422(
    client: TestClient, db, admin_token: str, company, dashboard, board_com_3_colunas
):
    a_fazer, secao, _concluido = board_com_3_colunas
    cards = _criar_cards(db, dashboard, a_fazer, ["A"])

    resposta = client.patch(
        f"/api/v1/dashboard/companies/{company.id}/cards/bulk",
        json={
            "card_ids": [cards[0].id],
            "operation": "set_column",
            "column_id": secao.id,
        },
        headers=_headers(admin_token),
    )
    assert resposta.status_code == 422


@pytest.mark.parametrize(
    "metodo,rota,corpo",
    [
        ("PATCH", "/api/v1/dashboard/cards/{card_id}/move", {"column_id": None}),
        (
            "PATCH",
            "/api/v1/dashboard/cards/{card_id}",
            {
                "title": "x",
                "description": None,
                "control_code": None,
                "category_id": None,
            },
        ),
        ("PUT", "/api/v1/dashboard/cards/{card_id}/labels", {"label_ids": []}),
    ],
)
def test_cliente_nao_pode_escrever_no_quadro(
    client: TestClient, user_token: str, dashboard_card, metodo, rota, corpo
):
    """CA-11: o quadro é leitura para o cliente e escrita só para o auditor."""
    resposta = client.request(
        metodo,
        rota.format(card_id=dashboard_card.id),
        json=corpo,
        headers=_headers(user_token),
    )
    assert resposta.status_code == 403
```

---

#### `backend/tests/test_dashboard_labels.py`

##### 1. Ação Manual

Crie o arquivo `backend/tests/test_dashboard_labels.py`.

##### 2. Código Fonte Completo

```python
"""
CA-12: etiqueta é criticidade, status é conformidade — e nunca o
contrário.

A regra que este arquivo protege é a de B-A23. O quadro de referência
tinha uma etiqueta `Concluído com evidência` que responde à MESMA
pergunta que `DashboardCardStatus.CONFORME`. Duas fontes de verdade para
"este controle está conforme?" é o defeito, não a etiqueta: por isso ela
ficou fora do vocabulário semeado, e por isso o teste abaixo verifica
explicitamente que etiquetar um card não mexe no status dele.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.company_dashboard import DashboardCardStatus


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _criar_etiqueta(client: TestClient, token: str, nome: str, cor: str = "#96311D"):
    resposta = client.post(
        "/api/v1/admin/dashboard-labels",
        json={"name": nome, "color": cor, "sort_order": 0},
        headers=_headers(token),
    )
    assert resposta.status_code == 201
    return resposta.json()


def test_crud_de_etiqueta(client: TestClient, admin_token: str):
    criada = _criar_etiqueta(client, admin_token, "Item Critico")
    assert criada["color"] == "#96311D"

    listadas = client.get(
        "/api/v1/admin/dashboard-labels", headers=_headers(admin_token)
    )
    assert listadas.status_code == 200
    assert [e["name"] for e in listadas.json()] == ["Item Critico"]

    editada = client.patch(
        f"/api/v1/admin/dashboard-labels/{criada['id']}",
        json={"name": "Crítico", "color": "#000000", "sort_order": 2},
        headers=_headers(admin_token),
    )
    assert editada.status_code == 200
    assert editada.json()["name"] == "Crítico"

    excluida = client.delete(
        f"/api/v1/admin/dashboard-labels/{criada['id']}",
        headers=_headers(admin_token),
    )
    assert excluida.status_code == 204


def test_nome_duplicado_devolve_409(client: TestClient, admin_token: str):
    _criar_etiqueta(client, admin_token, "Alta Criticidade")

    repetida = client.post(
        "/api/v1/admin/dashboard-labels",
        json={"name": "Alta Criticidade", "color": "#C2410C", "sort_order": 1},
        headers=_headers(admin_token),
    )
    assert repetida.status_code == 409


def test_etiqueta_inexistente_devolve_404(client: TestClient, admin_token: str):
    resposta = client.patch(
        "/api/v1/admin/dashboard-labels/9999",
        json={"name": "X", "color": "#000000", "sort_order": 0},
        headers=_headers(admin_token),
    )
    assert resposta.status_code == 404


def test_excluir_etiqueta_em_uso_devolve_409(
    client: TestClient, admin_token: str, dashboard_card
):
    """Mesma regra de `CategoryInUseError`: exclusão bloqueada, não em
    cascata."""
    etiqueta = _criar_etiqueta(client, admin_token, "Em uso")

    client.put(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/labels",
        json={"label_ids": [etiqueta["id"]]},
        headers=_headers(admin_token),
    )

    resposta = client.delete(
        f"/api/v1/admin/dashboard-labels/{etiqueta['id']}",
        headers=_headers(admin_token),
    )
    assert resposta.status_code == 409
    assert "em uso" in resposta.json()["detail"].lower()


def test_put_substitui_o_conjunto_inteiro_de_etiquetas(
    client: TestClient, admin_token: str, dashboard_card, etiquetas
):
    """Semântica de PUT, não de PATCH: a lista enviada É o conjunto."""
    primeiro, segundo, terceiro = etiquetas

    client.put(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/labels",
        json={"label_ids": [primeiro.id, segundo.id]},
        headers=_headers(admin_token),
    )

    resposta = client.put(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/labels",
        json={"label_ids": [terceiro.id]},
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 200
    assert [e["name"] for e in resposta.json()] == ["Baixa Criticidade"]


def test_lista_vazia_remove_todas_as_etiquetas(
    client: TestClient, admin_token: str, dashboard_card, etiquetas
):
    client.put(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/labels",
        json={"label_ids": [etiquetas[0].id]},
        headers=_headers(admin_token),
    )

    resposta = client.put(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/labels",
        json={"label_ids": []},
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_id_de_etiqueta_inexistente_devolve_404_sem_aplicar_nada(
    client: TestClient, db, admin_token: str, dashboard_card, etiquetas
):
    """
    Todos os ids são validados ANTES de tocar no vínculo: uma lista com um
    id inválido no meio não pode deixar o card com metade das etiquetas.
    """
    resposta = client.put(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/labels",
        json={"label_ids": [etiquetas[0].id, 999999]},
        headers=_headers(admin_token),
    )

    assert resposta.status_code == 404
    db.expire_all()
    assert db.get(type(dashboard_card), dashboard_card.id).labels == []


def test_etiquetar_nao_altera_o_status_do_card(
    client: TestClient, db, admin_token: str, dashboard_card, etiquetas
):
    """
    CA-12. Etiqueta responde "quão crítico é"; status responde "está
    conforme". Misturar os dois recriaria B-A23.
    """
    status_antes = dashboard_card.status

    client.put(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/labels",
        json={"label_ids": [etiquetas[0].id]},
        headers=_headers(admin_token),
    )

    db.expire_all()
    card = db.get(type(dashboard_card), dashboard_card.id)
    assert card.status == status_antes == DashboardCardStatus.EM_ANALISE


def test_cliente_nao_acessa_o_crud_de_etiquetas(
    client: TestClient, user_token: str
):
    resposta = client.get(
        "/api/v1/admin/dashboard-labels", headers=_headers(user_token)
    )
    assert resposta.status_code == 403
```

---

#### `backend/tests/test_authorization_matrix.py`

##### 1. Ação Manual

Abra `backend/tests/test_authorization_matrix.py` e substitua o conteúdo inteiro. As
adições são: 8 rotas de escrita novas em `WRITE_ENDPOINTS`, uma rota de leitura em
`READ_ENDPOINTS` e o teste que registra explicitamente que `GET …/board` é permitido a
todos os papéis.

##### 2. Código Fonte Completo

```python
"""
M-20: cada endpoint de ESCRITA exercitado por cada papel que NÃO deveria
poder executá-lo.

Complementa os testes de caminho feliz. Os 4 achados de prioridade Alta
da rev. 8.0 de docs/relatorio_bugs.md estavam TODOS fora do caminho que
a UI percorre — e por isso nenhum teste os alcançava.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.policy import ALLOWED_ROLES, Action

ALL_ROLES = ["admin", "user", "sub-user"]

# (método, template de rota, corpo, papéis que DEVEM receber 403)
WRITE_ENDPOINTS = [
    (
        "PATCH",
        "/api/v1/dashboard/cards/{card_id}/status",
        {"status": "CONFORME"},
        ["user", "sub-user"],
    ),
    (
        "POST",
        "/api/v1/dashboard/cards/{card_id}/entries",
        {"entry_type": "HISTORY", "content": "x"},
        ["user", "sub-user"],
    ),
    (
        "POST",
        "/api/v1/dashboard/cards/{card_id}/entries",
        {"entry_type": "CHECKLIST", "content": "x"},
        ["user", "sub-user"],
    ),
    (
        "POST",
        "/api/v1/dashboard/cards/{card_id}/entries",
        {"entry_type": "CHAT_ANSWER", "content": "x"},
        ["user", "sub-user"],
    ),
    (
        "POST",
        "/api/v1/dashboard/cards/{card_id}/notes",
        {"content": "x"},
        ["user", "sub-user"],
    ),
    # ---- Quadro Kanban (PRD §4.4 / CA-11) ----
    (
        "PATCH",
        "/api/v1/dashboard/cards/{card_id}/move",
        {"column_id": None, "prev_card_id": None, "next_card_id": None},
        ["user", "sub-user"],
    ),
    (
        "PATCH",
        "/api/v1/dashboard/cards/{card_id}",
        {
            "title": "x",
            "description": None,
            "control_code": None,
            "category_id": None,
        },
        ["user", "sub-user"],
    ),
    (
        "PUT",
        "/api/v1/dashboard/cards/{card_id}/labels",
        {"label_ids": []},
        ["user", "sub-user"],
    ),
]

# Rotas de escrita do quadro que NÃO são endereçadas por card_id — têm
# template próprio porque a formatação da URL é diferente.
COLUMN_WRITE_ENDPOINTS = [
    (
        "POST",
        "/api/v1/dashboard/companies/{company_id}/columns",
        {"name": "Nova", "kind": "COLUMN", "after_column_id": None},
        ["user", "sub-user"],
    ),
]

LABEL_WRITE_ENDPOINTS = [
    (
        "POST",
        "/api/v1/admin/dashboard-labels",
        {"name": "X", "color": "#000000", "sort_order": 0},
        ["user", "sub-user"],
    ),
]


@pytest.mark.parametrize("method,route,body,forbidden_roles", WRITE_ENDPOINTS)
def test_write_endpoint_rejects_forbidden_roles(
    method,
    route,
    body,
    forbidden_roles,
    client: TestClient,
    user_token: str,
    sub_user_token: str,
    dashboard_card,
):
    tokens = {"user": user_token, "sub-user": sub_user_token}
    url = route.format(card_id=dashboard_card.id)

    for role in forbidden_roles:
        response = client.request(
            method,
            url,
            json=body,
            headers={"Authorization": f"Bearer {tokens[role]}"},
        )
        assert response.status_code == 403, (
            f"{method} {url} aceitou escrita do papel '{role}' "
            f"(status {response.status_code}) — ver B-A23"
        )


@pytest.mark.parametrize("method,route,body,forbidden_roles", COLUMN_WRITE_ENDPOINTS)
def test_column_write_endpoint_rejects_forbidden_roles(
    method,
    route,
    body,
    forbidden_roles,
    client: TestClient,
    user_token: str,
    sub_user_token: str,
    company,
    dashboard_column,
):
    tokens = {"user": user_token, "sub-user": sub_user_token}
    url = route.format(company_id=company.id, column_id=dashboard_column.id)

    for role in forbidden_roles:
        response = client.request(
            method,
            url,
            json=body,
            headers={"Authorization": f"Bearer {tokens[role]}"},
        )
        assert response.status_code == 403, (
            f"{method} {url} aceitou escrita do papel '{role}' "
            f"(status {response.status_code}) — ver PRD §4.4"
        )


@pytest.mark.parametrize(
    "method,route,body",
    [
        (
            "PATCH",
            "/api/v1/dashboard/columns/{column_id}",
            {"name": "X", "hidden": False, "wip_limit": None},
        ),
        (
            "PATCH",
            "/api/v1/dashboard/columns/{column_id}/move",
            {"prev_column_id": None, "next_column_id": None},
        ),
        ("DELETE", "/api/v1/dashboard/columns/{column_id}", None),
    ],
)
@pytest.mark.parametrize("role", ["user", "sub-user"])
def test_column_mutations_reject_client_roles(
    method,
    route,
    body,
    role,
    client: TestClient,
    user_token: str,
    sub_user_token: str,
    dashboard_column,
):
    """
    Estas três rotas passam por `require_admin` ANTES do escopo, então o
    cliente recebe 403 — e não 404. É a ordem de `update_card_status`, e
    é o que garante que papel errado e tenant errado tenham respostas
    distintas e corretas.
    """
    tokens = {"user": user_token, "sub-user": sub_user_token}
    url = route.format(column_id=dashboard_column.id)

    response = client.request(
        method, url, json=body, headers={"Authorization": f"Bearer {tokens[role]}"}
    )
    assert response.status_code == 403


@pytest.mark.parametrize("method,route,body,forbidden_roles", LABEL_WRITE_ENDPOINTS)
def test_label_write_endpoint_rejects_forbidden_roles(
    method,
    route,
    body,
    forbidden_roles,
    client: TestClient,
    user_token: str,
    sub_user_token: str,
):
    tokens = {"user": user_token, "sub-user": sub_user_token}

    for role in forbidden_roles:
        response = client.request(
            method,
            route,
            json=body,
            headers={"Authorization": f"Bearer {tokens[role]}"},
        )
        assert response.status_code == 403


def test_client_can_still_ask_question_in_card_chat(
    client: TestClient, user_token: str, dashboard_card
):
    """A restrição de B-A23 não pode fechar o canal legítimo do cliente."""
    response = client.post(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/entries",
        json={"entry_type": "CHAT_QUESTION", "content": "Qual evidência enviar?"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 201


def test_client_cannot_toggle_checklist_item(
    client: TestClient, user_token: str, db, dashboard_card
):
    from app.models.company_dashboard import DashboardCardchecklistItem

    item = DashboardCardchecklistItem(
        card_id=dashboard_card.id, title="Conferir política", done=False
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    response = client.patch(
        f"/api/v1/dashboard/checklist-items/{item.id}/toggle",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------- LEITURA
#
# M-23: leitura sensível também é decisão de política. A matriz nasceu
# cobrindo só escrita — e por isso B-A28 (o cliente lendo o checklist
# interno do auditor) passou por ela sem ser notado.
#
# (rota, papéis que NÃO podem ver, campos que não podem vir preenchidos)
# `campos_vedados = None` significa "a rota inteira é vedada" (403).
# Uma lista de campos significa "a rota é permitida, mas estes campos
# voltam vazios" — o cliente tem direito ao card, não ao trabalho interno
# do auditor sobre ele.
READ_ENDPOINTS = [
    (
        "/api/v1/dashboard/cards/{card_id}",
        ["user", "sub-user"],
        ["checklist", "history"],
    ),
    (
        "/api/v1/dashboard/cards/{card_id}/notes",
        ["user", "sub-user"],
        None,
    ),
]


@pytest.mark.parametrize("route,forbidden_roles,campos_vedados", READ_ENDPOINTS)
def test_read_endpoint_hides_internals_from_forbidden_roles(
    route,
    forbidden_roles,
    campos_vedados,
    client: TestClient,
    db,
    admin_user,
    user_token: str,
    sub_user_token: str,
    dashboard_card,
):
    from app.models.company_dashboard import (
        DashboardCardchecklistItem,
        DashboardCardHistoryEntry,
    )

    db.add(
        DashboardCardchecklistItem(
            card_id=dashboard_card.id, title="INTERNO checklist", done=False
        )
    )
    db.add(
        DashboardCardHistoryEntry(
            card_id=dashboard_card.id,
            action="INTERNO historico",
            actor_user_id=admin_user.id,
        )
    )
    db.commit()

    tokens = {"user": user_token, "sub-user": sub_user_token}
    url = route.format(card_id=dashboard_card.id)

    for role in forbidden_roles:
        response = client.get(
            url, headers={"Authorization": f"Bearer {tokens[role]}"}
        )
        if campos_vedados is None:
            assert response.status_code == 403, (
                f"GET {url} devolveu {response.status_code} para o papel "
                f"'{role}' — esperado 403"
            )
            continue

        assert response.status_code == 200
        corpo = response.json()
        for campo in campos_vedados:
            assert corpo[campo] == [], (
                f"GET {url} devolveu '{campo}' preenchido para o papel "
                f"'{role}' — ver B-A28"
            )
        assert "INTERNO" not in response.text


@pytest.mark.parametrize("role", ["admin", "user", "sub-user"])
def test_board_read_is_allowed_for_every_role(
    role,
    client: TestClient,
    admin_token: str,
    user_token: str,
    sub_user_token: str,
    company,
    dashboard_column,
):
    """
    M-23 exige que a decisão de leitura seja REGISTRADA, inclusive quando
    ela é "permitido para todos". `GET …/board` é leitura da própria
    empresa: o cliente vê o quadro com as colunas na ordem que o auditor
    montou (U6), e só não consegue rearranjá-lo.

    Sem esta linha explícita, "todos podem ler o quadro" ficaria sendo
    uma propriedade acidental do código em vez de uma decisão.
    """
    tokens = {
        "admin": admin_token,
        "user": user_token,
        "sub-user": sub_user_token,
    }
    response = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board",
        headers={"Authorization": f"Bearer {tokens[role]}"},
    )
    assert response.status_code == 200


@pytest.mark.parametrize("action", list(Action))
def test_every_action_has_an_explicit_decision(action: Action):
    """
    Nenhuma ação pode ficar sem decisão declarada. Um `Action` novo
    acrescentado sem a linha correspondente em ALLOWED_ROLES falha aqui,
    em vez de silenciosamente permitir (ou negar) tudo.
    """
    assert action in ALLOWED_ROLES, f"{action.value} não tem papéis declarados"
    assert isinstance(ALLOWED_ROLES[action], frozenset)
    assert ALLOWED_ROLES[action] <= set(ALL_ROLES), (
        f"{action.value} declara papel desconhecido: "
        f"{ALLOWED_ROLES[action] - set(ALL_ROLES)}"
    )
```

---

#### `backend/tests/test_query_budget.py`

##### 1. Ação Manual

Duas edições neste arquivo. **Não** o substitua inteiro.

**Edição 1 — teto de `GET …/cards` (linha 199).** A rota ganhou dois `selectinload`
(`labels` e `column`), cada um custando uma query fixa. Suba o teto de 8 para 12 e registre
o porquê na mensagem:

```python
    assert contador.count <= 12, (
        f"{contador.count} queries para 20 cards — N+1 em "
        "list_cards_by_company (o `selectinload` foi removido?).\n"
        "O teto subiu de 8 para 12 quando a rota passou a carregar "
        "`labels` (M:N) e `column` (usada por `_card_is_outdated`): cada "
        "`selectinload` custa UMA query fixa a mais, não uma por card — "
        "é justamente essa diferença que o teto protege."
    )
```

**Edição 2 — acrescente ao FINAL do arquivo** o orçamento do quadro.

##### 2. Código Fonte Completo (bloco a acrescentar ao final)

```python
# ------------------------------------------- GET .../board (quadro Kanban)


def _semear_quadro(db, company, colunas: int, cards_por_coluna: int = 5) -> None:
    """
    Um quadro com `colunas` colunas e `colunas * cards_por_coluna` cards.

    Semeado por SQL do ORM direto (e não pela API) de propósito: o que se
    mede aqui é o custo da LEITURA, e criar via API poluiria o contador
    com as queries de escrita.
    """
    from app.models.dashboard_board import DashboardColumn
    from app.services.fractional_index import n_keys_between

    dashboard = Dashboard(company_id=company.id, title="Dash Quadro")
    db.add(dashboard)
    db.flush()

    posicoes_coluna = n_keys_between(None, None, colunas)
    for indice, posicao in enumerate(posicoes_coluna):
        coluna = DashboardColumn(
            dashboard_id=dashboard.id, name=f"Coluna {indice}", position=posicao
        )
        db.add(coluna)
        db.flush()
        for card_posicao in n_keys_between(None, None, cards_por_coluna):
            db.add(
                DashboardCard(
                    dashboard_id=dashboard.id,
                    title=f"Card {indice}-{card_posicao}",
                    tag="x",
                    column_id=coluna.id,
                    position=card_posicao,
                )
            )
    db.commit()


@pytest.mark.parametrize("colunas", [5, 20])
def test_board_tem_custo_constante_em_queries(client, db, admin_token, company, colunas):
    """
    CA-13. Parametrizado com DUAS quantidades sob o MESMO teto, pela razão
    explicada na docstring do módulo: um teto absoluto medido com uma
    quantidade só pode ser satisfeito por acaso; com 5 e 20 colunas sob o
    mesmo teto, só passa se o custo for de fato constante.

    O defeito que isto previne é concreto e fácil de introduzir: uma
    query de cards POR COLUNA dentro do laço de montagem do quadro. Com 5
    colunas ninguém nota; com as 25 do quadro real, a tela trava.
    """
    _semear_quadro(db, company, colunas)

    with ContadorDeQueries() as contador:
        resposta = client.get(
            f"/api/v1/dashboard/companies/{company.id}/board",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo["columns"]) == colunas
    assert sum(len(c["cards"]) for c in corpo["columns"]) == colunas * 5

    assert contador.count <= 15, (
        f"{contador.count} queries para {colunas} colunas — o custo do quadro "
        f"virou linear no número de colunas (CA-13).\n"
        + "\n".join(f"  {s}" for s in contador.statements[:25])
    )


def test_mover_card_nao_reescreve_a_coluna_inteira(client, db, admin_token, company):
    """
    CA-06 medido do lado do orçamento: o índice fracionário existe para
    que um arrasto custe UM UPDATE. Com `sort_order: Integer` seriam até
    100.
    """
    from app.models.dashboard_board import DashboardColumn

    _semear_quadro(db, company, colunas=1, cards_por_coluna=100)
    coluna = db.scalars(select(DashboardColumn)).first()
    cards = (
        db.query(DashboardCard)
        .filter(DashboardCard.column_id == coluna.id)
        .order_by(DashboardCard.position.asc())
        .all()
    )

    with ContadorDeQueries() as contador:
        resposta = client.patch(
            f"/api/v1/dashboard/cards/{cards[0].id}/move",
            json={
                "column_id": coluna.id,
                "prev_card_id": cards[-1].id,
                "next_card_id": None,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resposta.status_code == 200
    updates = [s for s in contador.statements if s.strip().upper().startswith("UPDATE")]
    assert len(updates) == 1, f"{len(updates)} UPDATEs para mover 1 card entre 100"
```

**Edição 3 — import.** O bloco novo usa `select`; acrescente-o ao import de `sqlalchemy` no
topo do arquivo:

```python
from sqlalchemy import event, select
```

---

#### `backend/tests/test_dashboard_templates.py`

##### 1. Ação Manual

Acrescente ao **final** do arquivo `backend/tests/test_dashboard_templates.py` o bloco
abaixo (CA-09 e CA-10). Nenhuma linha existente do arquivo precisa mudar: os campos novos
de `DashboardTemplateCardCreate` são todos opcionais.

##### 2. Código Fonte Completo (bloco a acrescentar ao final)

```python
# ------------------------------------------- Quadro Kanban: CA-09 e CA-10


def _criar_template_com_coluna(client: TestClient, headers: dict) -> tuple[int, int]:
    template = client.post(
        "/api/v1/admin/templates",
        headers=headers,
        json={"name": "Due Diligence", "description": None, "is_default": False},
    ).json()

    coluna = client.post(
        f"/api/v1/admin/templates/{template['id']}/columns",
        headers=headers,
        json={"name": "Controle 5 - Organizacionais", "kind": "COLUMN"},
    )
    assert coluna.status_code == 201
    return template["id"], coluna.json()["id"]


def test_coluna_de_template_aparece_no_detalhe(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    template_id, coluna_id = _criar_template_com_coluna(client, headers)

    detalhe = client.get(f"/api/v1/admin/templates/{template_id}", headers=headers)

    assert detalhe.status_code == 200
    colunas = detalhe.json()["columns"]
    assert [c["id"] for c in colunas] == [coluna_id]
    assert colunas[0]["kind"] == "COLUMN"


def test_nome_de_coluna_duplicado_no_mesmo_template_devolve_409(
    client: TestClient, admin_token: str
):
    headers = {"Authorization": f"Bearer {admin_token}"}
    template_id, _coluna_id = _criar_template_com_coluna(client, headers)

    repetida = client.post(
        f"/api/v1/admin/templates/{template_id}/columns",
        headers=headers,
        json={"name": "Controle 5 - Organizacionais", "kind": "COLUMN"},
    )
    assert repetida.status_code == 409


def test_excluir_coluna_de_template_com_card_devolve_409(
    client: TestClient, admin_token: str
):
    headers = {"Authorization": f"Bearer {admin_token}"}
    template_id, coluna_id = _criar_template_com_coluna(client, headers)

    client.post(
        f"/api/v1/admin/templates/{template_id}/cards",
        headers=headers,
        json={
            "title": "Política de SI",
            "description": None,
            "category_id": None,
            "template_column_id": coluna_id,
            "sort_order": 0,
        },
    )

    resposta = client.delete(
        f"/api/v1/admin/templates/{template_id}/columns/{coluna_id}", headers=headers
    )
    assert resposta.status_code == 409


def test_card_nao_pode_apontar_para_coluna_de_outro_template(
    client: TestClient, admin_token: str
):
    headers = {"Authorization": f"Bearer {admin_token}"}
    _template_a, coluna_a = _criar_template_com_coluna(client, headers)

    template_b = client.post(
        "/api/v1/admin/templates",
        headers=headers,
        json={"name": "Outro Template", "description": None, "is_default": False},
    ).json()

    resposta = client.post(
        f"/api/v1/admin/templates/{template_b['id']}/cards",
        headers=headers,
        json={
            "title": "Card do B",
            "description": None,
            "category_id": None,
            "template_column_id": coluna_a,
            "sort_order": 0,
        },
    )
    assert resposta.status_code == 404


def test_aplicar_template_com_colunas_duas_vezes_e_idempotente(
    client: TestClient, admin_token: str, company, dashboard
):
    """
    CA-09. A idempotência de coluna repousa na MESMA `UniqueConstraint`
    que a de card — `uq_dashboard_column_origin_per_dashboard`. Sem ela, a
    segunda aplicação duplicaria as 25 colunas do quadro real (R2).
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    template_id, coluna_id = _criar_template_com_coluna(client, headers)

    for titulo in ("Política de SI", "Inventário de Ativos"):
        client.post(
            f"/api/v1/admin/templates/{template_id}/cards",
            headers=headers,
            json={
                "title": titulo,
                "description": None,
                "category_id": None,
                "template_column_id": coluna_id,
                "sort_order": 0,
            },
        )

    primeira = client.post(
        f"/api/v1/dashboard/companies/{company.id}/apply-template",
        headers=headers,
        json={"template_id": template_id},
    ).json()
    assert primeira["created_count"] == 2
    assert primeira["columns_created_count"] == 1

    segunda = client.post(
        f"/api/v1/dashboard/companies/{company.id}/apply-template",
        headers=headers,
        json={"template_id": template_id},
    ).json()
    assert segunda["created_count"] == 0
    assert segunda["columns_created_count"] == 0

    quadro = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board", headers=headers
    ).json()
    assert len(quadro["columns"]) == 1
    assert len(quadro["columns"][0]["cards"]) == 2


def test_aplicar_template_copia_a_descricao_para_o_card_da_empresa(
    client: TestClient, admin_token: str, company, dashboard
):
    """
    CA-10. Até esta entrega, `apply_template_to_company` copiava
    título/tag/categoria e DESCARTAVA a descrição em silêncio — 68 % dos
    cards do quadro real perderiam o texto normativo do controle.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    template_id, coluna_id = _criar_template_com_coluna(client, headers)

    texto = "**Controle** — Convém que a política de segurança seja aprovada."
    client.post(
        f"/api/v1/admin/templates/{template_id}/cards",
        headers=headers,
        json={
            "title": "Política de SI",
            "description": texto,
            "category_id": None,
            "template_column_id": coluna_id,
            "sort_order": 0,
        },
    )

    client.post(
        f"/api/v1/dashboard/companies/{company.id}/apply-template",
        headers=headers,
        json={"template_id": template_id},
    )

    quadro = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board", headers=headers
    ).json()
    assert quadro["columns"][0]["cards"][0]["description"] == texto


def test_aplicar_template_posiciona_o_card_na_coluna_correspondente(
    client: TestClient, admin_token: str, company, dashboard
):
    headers = {"Authorization": f"Bearer {admin_token}"}
    template_id, coluna_id = _criar_template_com_coluna(client, headers)

    client.post(
        f"/api/v1/admin/templates/{template_id}/cards",
        headers=headers,
        json={
            "title": "Card com coluna",
            "description": None,
            "category_id": None,
            "template_column_id": coluna_id,
            "sort_order": 0,
        },
    )
    client.post(
        f"/api/v1/admin/templates/{template_id}/cards",
        headers=headers,
        json={
            "title": "Card sem coluna",
            "description": None,
            "category_id": None,
            "template_column_id": None,
            "sort_order": 1,
        },
    )

    client.post(
        f"/api/v1/dashboard/companies/{company.id}/apply-template",
        headers=headers,
        json={"template_id": template_id},
    )

    quadro = client.get(
        f"/api/v1/dashboard/companies/{company.id}/board", headers=headers
    ).json()
    assert [c["title"] for c in quadro["columns"][0]["cards"]] == ["Card com coluna"]
    assert [c["title"] for c in quadro["uncolumned"]] == ["Card sem coluna"]
```

---

#### `backend/tests/test_dashboard_cards.py`

##### 1. Ação Manual

Nenhuma linha existente precisa mudar: os campos novos de `DashboardCardWithCategoryOut`
têm default, e os `DashboardCard(...)` construídos direto nos testes usam o default
`position="a0"` do model. Acrescente ao **final** do arquivo o bloco abaixo, que cobre os
campos novos e a troca de ordenação.

##### 2. Código Fonte Completo (bloco a acrescentar ao final)

```python
# --------------------------------------------- Quadro Kanban na listagem


def test_listagem_de_cards_traz_os_campos_do_quadro(
    client: TestClient, db, admin_token: str, company, dashboard_card, etiquetas
):
    """
    Os quatro campos novos (`column_id`, `position`, `description`,
    `labels`) são ADIÇÕES ao contrato — nenhum consumidor antigo quebra,
    e quem precisa deles não faz uma segunda chamada.
    """
    dashboard_card.description = "Texto normativo"
    dashboard_card.labels = [etiquetas[0]]
    db.commit()

    resposta = client.get(
        f"/api/v1/dashboard/companies/{company.id}/cards",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resposta.status_code == 200
    card = resposta.json()[0]
    assert card["column_id"] == dashboard_card.column_id
    assert card["position"] == dashboard_card.position
    assert card["description"] == "Texto normativo"
    assert [e["name"] for e in card["labels"]] == ["Item Critico"]


def test_listagem_de_cards_ordena_por_position(
    client: TestClient, db, admin_token: str, company, dashboard, dashboard_column
):
    """
    A ordenação passou de `sort_order` para `position`. Os `sort_order`
    abaixo estão em ordem INVERSA à das posições, de propósito: se a rota
    ainda ordenasse pelo campo antigo, o teste falharia.
    """
    from app.models.company_dashboard import DashboardCard
    from app.services.fractional_index import n_keys_between

    posicoes = n_keys_between(None, None, 3)
    for indice, (titulo, posicao) in enumerate(
        zip(["Primeiro", "Segundo", "Terceiro"], posicoes)
    ):
        db.add(
            DashboardCard(
                dashboard_id=dashboard.id,
                title=titulo,
                tag="t",
                column_id=dashboard_column.id,
                position=posicao,
                sort_order=10 - indice,
            )
        )
    db.commit()

    corpo = client.get(
        f"/api/v1/dashboard/companies/{company.id}/cards",
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()

    assert [c["title"] for c in corpo] == ["Primeiro", "Segundo", "Terceiro"]


def test_criar_card_dentro_de_uma_coluna(
    client: TestClient, admin_token: str, db, company, dashboard, dashboard_column
):
    from app.models.company_dashboard import DashboardCardCategory

    categoria = DashboardCardCategory(name="Governança", color="#000000", sort_order=0)
    db.add(categoria)
    db.commit()

    resposta = client.post(
        f"/api/v1/dashboard/companies/{company.id}/cards",
        json={
            "title": "Card novo",
            "category_id": categoria.id,
            "column_id": dashboard_column.id,
            "description": "Descrição do controle",
            "control_code": "5.2",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["column_id"] == dashboard_column.id
    assert corpo["description"] == "Descrição do controle"
    assert corpo["position"]


def test_criar_card_em_coluna_de_outra_empresa_devolve_404(
    client: TestClient, admin_token: str, db, company, dashboard
):
    from app.core.security import hash_password
    from app.models.company_dashboard import Company, DashboardCardCategory
    from app.models.dashboard_board import DashboardColumn
    from app.models.user import User

    categoria = DashboardCardCategory(name="Governança", color="#000000", sort_order=0)
    outro_usuario = User(
        full_name="Outro",
        email="outro2@test.com",
        password_hash=hash_password("Outro123!"),
        role="user",
    )
    db.add_all([categoria, outro_usuario])
    db.flush()

    outra = Company(
        name="Empresa Alheia",
        email="alheia@test.com",
        principal_user_id=outro_usuario.id,
    )
    db.add(outra)
    db.flush()
    outro_dashboard = Dashboard(company_id=outra.id, title="Dash Alheio")
    db.add(outro_dashboard)
    db.flush()
    coluna_alheia = DashboardColumn(
        dashboard_id=outro_dashboard.id, name="Alheia", position="a0"
    )
    db.add(coluna_alheia)
    db.commit()

    resposta = client.post(
        f"/api/v1/dashboard/companies/{company.id}/cards",
        json={
            "title": "Card",
            "category_id": categoria.id,
            "column_id": coluna_alheia.id,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resposta.status_code == 404


def test_detalhe_do_card_traz_descricao_para_o_cliente(
    client: TestClient, db, user_token: str, dashboard_card, etiquetas
):
    """
    U7: a `description` é o texto normativo do controle — é exatamente o
    que o cliente precisa ler para saber o que entregar. Ao contrário de
    checklist e histórico (B-A28), ela NÃO é registro interno.
    """
    dashboard_card.description = "Convém que a política seja aprovada."
    dashboard_card.labels = [etiquetas[1]]
    db.commit()

    corpo = client.get(
        f"/api/v1/dashboard/cards/{dashboard_card.id}",
        headers={"Authorization": f"Bearer {user_token}"},
    ).json()

    assert corpo["description"] == "Convém que a política seja aprovada."
    assert corpo["column_id"] == dashboard_card.column_id
    assert [e["name"] for e in corpo["labels"]] == ["Alta Criticidade"]
    # B-A28 continua valendo para o registro interno.
    assert corpo["checklist"] == []
    assert corpo["history"] == []
```

**Import necessário.** O bloco usa `Dashboard`; confirme que o import no topo do arquivo
inclui:

```python
from app.models.company_dashboard import (
    Dashboard,
    DashboardCard,
    DashboardCardHistoryEntry,
    DashboardCardMessage,
    DashboardCardStatus,
    DashboardMessageType,
)
```

---

### Fase 6 — Fundação do frontend

---

#### `frontend/package.json`

##### 1. Ação Manual

Instale as três dependências **com versão fixa** e commite o `package-lock.json` no mesmo
commit:

```bash
cd frontend
npm install --save-exact @dnd-kit/core@6.3.1 @dnd-kit/sortable@10.0.0 @dnd-kit/modifiers@9.0.0
npm audit --omit=dev
```

Confira que o bloco `dependencies` ficou exatamente assim (sem `^` nas três novas):

##### 2. Código Fonte Completo

```json
{
  "name": "plataforma-auditoria-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage"
  },
  "dependencies": {
    "@dnd-kit/core": "6.3.1",
    "@dnd-kit/modifiers": "9.0.0",
    "@dnd-kit/sortable": "10.0.0",
    "jose": "^6.2.8",
    "next": "16.2.6",
    "react": "19.2.4",
    "react-dom": "19.2.4",
    "server-only": "^0.0.1"
  },
  "devDependencies": {
    "@tailwindcss/postcss": "^4",
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/react": "^16.3.2",
    "@testing-library/user-event": "^14.6.6",
    "@types/node": "^20",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "@vitejs/plugin-react": "^4.7.0",
    "@vitest/coverage-v8": "^2.1.9",
    "eslint": "^9",
    "eslint-config-next": "16.2.6",
    "jsdom": "^25.0.1",
    "tailwindcss": "^4",
    "typescript": "^5",
    "vitest": "^2.1.9"
  }
}
```

> `@dnd-kit/utilities` entra como transitiva de `@dnd-kit/sortable`. **Não a declare** —
> declarar uma transitiva cria dois lugares para atualizar a mesma coisa.

---

#### `frontend/app/globals.css`

##### 1. Ação Manual

Abra `frontend/app/globals.css` e substitua o conteúdo inteiro. As quatro classes novas
entram dentro do `@layer components` já existente, depois de `.status-chip`.

##### 2. Código Fonte Completo

```css
@import "tailwindcss";

:root {
  --color-primary: #ff4d00;
  --color-dark: #262626;
  --color-neutral: #c5c6cd;
  --color-white: #ffffff;
  --color-surface: #f7f7f9;
}

@theme inline {
  --font-sans: var(--font-geist-sans);
  --font-mono: var(--font-geist-mono);
}

body {
  background: var(--color-white);
  color: var(--color-dark);
  font-family: var(--font-sans), Arial, Helvetica, sans-serif;
}

a {
  color: inherit;
  text-decoration: none;
}

@layer components {
  .container-page {
    @apply mx-auto w-full max-w-6xl px-4 md:px-6;
  }

  .card {
    border: 1px solid var(--color-neutral);
    @apply rounded-2xl bg-white p-5 shadow-sm;
  }

  .btn-primary {
    background: var(--color-primary);
    color: white;
    @apply rounded-xl px-4 py-2 font-medium text-white transition hover:opacity-90;
  }

  .btn-secondary {
    border: 1px solid var(--color-neutral);
    @apply rounded-xl bg-white px-4 py-2 font-medium transition hover:bg-zinc-100;
  }

  .btn-danger {
    background: #dc2626;
    color: white;
    @apply rounded-xl px-4 py-2 font-medium text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50;
  }

  .btn-danger-outline {
    border: 1px solid #fca5a5;
    color: #b91c1c;
    @apply rounded-xl bg-white px-4 py-2 font-medium transition hover:bg-red-50;
  }

  .field {
    border: 1px solid var(--color-neutral);
    @apply w-full rounded-xl bg-white px-3 py-2 outline-none transition focus:ring-2;
    --tw-ring-color: color-mix(in srgb, var(--color-primary) 35%, transparent);
  }

  .status-chip {
    @apply rounded-full px-3 py-1 text-xs font-semibold;
  }

  /*
   * Quadro Kanban (CA-20). A rolagem HORIZONTAL vive aqui e em nenhum
   * outro lugar: é o contêiner que rola, nunca o `body`. Sem
   * `overflow-x: auto` neste nível, 25 colunas de 288 px estouram a
   * largura da janela e a página inteira passa a rolar de lado, levando
   * junto o cabeçalho e a barra de ação em lote.
   */
  .board-scroller {
    @apply flex w-full items-start gap-4 overflow-x-auto pb-4;
    scrollbar-gutter: stable;
  }

  /*
   * Largura FIXA e não flexível: colunas de largura variável fazem o
   * quadro "respirar" a cada card criado, e a posição de destino do
   * arrasto muda debaixo do cursor.
   */
  .board-column {
    border: 1px solid var(--color-neutral);
    @apply flex max-h-[70vh] w-72 shrink-0 flex-col rounded-xl bg-(--color-surface);
  }

  /* A rolagem VERTICAL é por dentro da coluna (CA-20). */
  .board-column-body {
    @apply flex-1 space-y-2 overflow-y-auto p-2;
  }

  .board-card {
    border: 1px solid var(--color-neutral);
    @apply w-full rounded-lg bg-white p-2 text-left shadow-sm transition hover:shadow;
  }

  .board-card-selected {
    border-color: var(--color-primary);
    @apply ring-2;
    --tw-ring-color: color-mix(in srgb, var(--color-primary) 35%, transparent);
  }

  /*
   * A cor de fundo NÃO vem daqui: ela é o hex guardado em
   * `dashboard_labels.color`, aplicado por `style` inline em
   * `lib/board-labels.ts`. Tailwind não gera classe para valor dinâmico
   * vindo do banco, e fingir que gera produziria chip sem cor nenhuma em
   * produção (só em dev, com o JIT lendo o código-fonte).
   */
  .label-chip {
    @apply inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold leading-tight;
  }

  .board-section-divider {
    @apply flex w-10 shrink-0 items-center justify-center self-stretch rounded-xl bg-(--color-dark) py-4;
  }
}
```

---

#### `frontend/lib/board-labels.ts`

##### 1. Ação Manual

Crie o arquivo `frontend/lib/board-labels.ts`.

##### 2. Código Fonte Completo

```typescript
/**
 * Vocabulário visual de etiqueta de card — o análogo de
 * `lib/control-status.ts` para o eixo de criticidade.
 *
 * Existe pela razão de B-M20: antes daquela unificação, cada tela
 * definia label e cor de status localmente, e as três divergiam. A
 * etiqueta tem o mesmo risco, agravado por um detalhe: **nenhum
 * componente pode decidir cor de etiqueta sozinho**, porque a cor não é
 * uma constante do frontend — é o hex guardado em
 * `dashboard_labels.color`, editável pelo admin no CRUD de etiquetas.
 *
 * Consequência prática, e a razão de `labelChipStyle` existir: Tailwind
 * gera classes a partir do código-fonte, em tempo de build. Uma classe
 * montada em runtime (`bg-[${cor}]`) funciona em dev, com o JIT lendo os
 * arquivos, e produz chip SEM COR NENHUMA no build de produção. Cor
 * dinâmica vinda do banco vai por `style` inline; a forma do chip vai
 * pela classe `.label-chip` do globals.css.
 */

export type BoardLabel = {
  id: number;
  name: string;
  color: string;
};

/**
 * Cores nomeadas do export do Trello -> hex do tema.
 *
 * Usado UMA vez, pelo importador (`scripts/import_trello_board.py`, que
 * carrega o mesmo mapa em Python) e pela migration que semeia as 8
 * etiquetas aprovadas. Fica aqui também para que a tela de etiquetas
 * possa oferecer a paleta de origem como sugestão, em vez de o admin ter
 * de descobrir os hexes.
 */
export const TRELLO_COLOR_MAP: Record<string, string> = {
  red_dark: "#96311D",
  orange: "#C2410C",
  yellow_light: "#A16207",
  yellow_dark: "#854D0E",
  blue: "#2C5A8C",
  blue_light: "#0E7490",
  blue_dark: "#1E3A8A",
  purple: "#6D28D9",
  green: "#1F6B4C",
  black_dark: "#3F3F46",
  pink_dark: "#9D174D",
};

/** Cor de fallback — a mesma default de `dashboard_labels.color`. */
export const DEFAULT_LABEL_COLOR = "#788c5d";

const HEX_COMPLETO = /^#[0-9a-fA-F]{6}$/;
const HEX_CURTO = /^#[0-9a-fA-F]{3}$/;

function normalizarHex(color: string): string {
  const valor = (color ?? "").trim();
  if (HEX_COMPLETO.test(valor)) return valor;
  if (HEX_CURTO.test(valor)) {
    const [, r, g, b] = valor;
    return `#${r}${r}${g}${g}${b}${b}`;
  }
  // Nome de cor do Trello ainda não convertido, ou lixo: nunca deixamos
  // o chip sem cor.
  return TRELLO_COLOR_MAP[valor] ?? DEFAULT_LABEL_COLOR;
}

/**
 * Luminância relativa aproximada (0 = preto, 1 = branco), na fórmula
 * simplificada do WCAG. Serve a uma pergunta só: o texto por cima deste
 * fundo tem de ser claro ou escuro?
 */
function luminancia(hex: string): number {
  const valor = normalizarHex(hex);
  const r = parseInt(valor.slice(1, 3), 16) / 255;
  const g = parseInt(valor.slice(3, 5), 16) / 255;
  const b = parseInt(valor.slice(5, 7), 16) / 255;
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/**
 * Classes do chip de etiqueta. A COR DE FUNDO não sai daqui — sai de
 * `labelChipStyle`. O que esta função decide é a cor do TEXTO, para o
 * contraste funcionar tanto sobre `#96311D` (vermelho escuro) quanto
 * sobre `#A16207` (âmbar).
 */
export function labelChipClass(color: string): string {
  return luminancia(color) > 0.6
    ? "label-chip text-zinc-900"
    : "label-chip text-white";
}

/** Estilo inline do chip — ver a docstring do módulo para o porquê. */
export function labelChipStyle(color: string): { backgroundColor: string } {
  return { backgroundColor: normalizarHex(color) };
}

/**
 * Ordem canônica de exibição: `sort_order` do banco primeiro, nome como
 * desempate. Duas telas que ordenem etiquetas de formas diferentes
 * mostram o mesmo card de dois jeitos — foi exatamente B-M20.
 *
 * Não muta o array recebido: o quadro guarda os cards em estado
 * otimista, e ordenar no lugar corromperia a lista que o React ainda
 * está renderizando.
 */
export function sortLabels<T extends BoardLabel & { sort_order?: number }>(
  labels: T[],
): T[] {
  return [...labels].sort((a, b) => {
    const ordemA = a.sort_order ?? 0;
    const ordemB = b.sort_order ?? 0;
    if (ordemA !== ordemB) return ordemA - ordemB;
    return a.name.localeCompare(b.name, "pt-BR");
  });
}

/** Converte a cor nomeada do export do Trello para o hex do tema. */
export function trelloColorToHex(color: string | null | undefined): string {
  if (!color) return DEFAULT_LABEL_COLOR;
  return TRELLO_COLOR_MAP[color] ?? DEFAULT_LABEL_COLOR;
}
```

---

#### `frontend/lib/board-labels.test.ts`

##### 1. Ação Manual

Crie o arquivo `frontend/lib/board-labels.test.ts`.

```bash
cd frontend
npx vitest run lib/board-labels.test.ts
```

##### 2. Código Fonte Completo

```typescript
import { describe, expect, it } from "vitest";

import {
  DEFAULT_LABEL_COLOR,
  TRELLO_COLOR_MAP,
  labelChipClass,
  labelChipStyle,
  sortLabels,
  trelloColorToHex,
  type BoardLabel,
} from "./board-labels";

describe("labelChipStyle", () => {
  it("usa o hex do banco como cor de fundo", () => {
    expect(labelChipStyle("#96311D")).toEqual({ backgroundColor: "#96311D" });
  });

  it("expande hex curto", () => {
    expect(labelChipStyle("#abc")).toEqual({ backgroundColor: "#aabbcc" });
  });

  it("cai no default em vez de deixar o chip sem cor", () => {
    expect(labelChipStyle("nao-e-cor")).toEqual({
      backgroundColor: DEFAULT_LABEL_COLOR,
    });
  });

  it("aceita nome de cor do Trello ainda não convertido", () => {
    expect(labelChipStyle("red_dark")).toEqual({ backgroundColor: "#96311D" });
  });
});

describe("labelChipClass", () => {
  it("usa texto claro sobre fundo escuro", () => {
    expect(labelChipClass("#96311D")).toContain("text-white");
  });

  it("usa texto escuro sobre fundo claro", () => {
    expect(labelChipClass("#FFFFFF")).toContain("text-zinc-900");
  });

  it("sempre inclui a classe de forma do chip", () => {
    expect(labelChipClass("#000000")).toContain("label-chip");
  });
});

describe("sortLabels", () => {
  const etiquetas: (BoardLabel & { sort_order: number })[] = [
    { id: 3, name: "Baixa Criticidade", color: "#2C5A8C", sort_order: 3 },
    { id: 1, name: "Item Critico", color: "#96311D", sort_order: 0 },
    { id: 2, name: "Alta Criticidade", color: "#C2410C", sort_order: 1 },
  ];

  it("ordena por sort_order", () => {
    expect(sortLabels(etiquetas).map((e) => e.name)).toEqual([
      "Item Critico",
      "Alta Criticidade",
      "Baixa Criticidade",
    ]);
  });

  it("desempata por nome", () => {
    const empatadas = [
      { id: 1, name: "Zebra", color: "#000", sort_order: 0 },
      { id: 2, name: "Alfa", color: "#000", sort_order: 0 },
    ];
    expect(sortLabels(empatadas).map((e) => e.name)).toEqual(["Alfa", "Zebra"]);
  });

  it("não muta o array recebido", () => {
    const original = [...etiquetas];
    sortLabels(etiquetas);
    expect(etiquetas).toEqual(original);
  });

  it("trata sort_order ausente como 0", () => {
    const semOrdem: BoardLabel[] = [
      { id: 1, name: "B", color: "#000" },
      { id: 2, name: "A", color: "#000" },
    ];
    expect(sortLabels(semOrdem).map((e) => e.name)).toEqual(["A", "B"]);
  });
});

describe("trelloColorToHex", () => {
  it("converte todas as 11 cores do quadro de origem", () => {
    expect(Object.keys(TRELLO_COLOR_MAP)).toHaveLength(11);
    for (const nome of Object.keys(TRELLO_COLOR_MAP)) {
      expect(trelloColorToHex(nome)).toMatch(/^#[0-9A-F]{6}$/i);
    }
  });

  it("cai no default para cor desconhecida ou ausente", () => {
    expect(trelloColorToHex("sky_neon")).toBe(DEFAULT_LABEL_COLOR);
    expect(trelloColorToHex(null)).toBe(DEFAULT_LABEL_COLOR);
    expect(trelloColorToHex(undefined)).toBe(DEFAULT_LABEL_COLOR);
  });
});
```

---

### Fase 7 — Quadro do admin

---

#### `frontend/app/private/admin/actions.ts`

##### 1. Ação Manual

Abra `frontend/app/private/admin/actions.ts` e altere **apenas** o bloco de tipos de card
(linhas 143-152). O resto do arquivo fica intocado, incluindo `getCardDetailAction`.

##### 2. Código Fonte Completo (bloco alterado)

```typescript
export type CardStatus = "EM_ANALISE" | "PARCIAL" | "CONFORME" | "NAOCONFORME";

/**
 * Etiqueta embutida no card. Declarada aqui, e não importada de
 * `empresas/[id]/dashboard/actions.ts`, para não criar um ciclo de
 * import entre os dois módulos de action (aquele já importa `CardStatus`
 * deste). São três campos estruturais; o que NÃO pode ser duplicado é a
 * COR — isso vive em `lib/board-labels.ts`, e duplicá-lo por tela foi
 * exatamente o defeito B-M20.
 */
export type BoardLabelRef = {
  id: number;
  name: string;
  color: string;
};

export type DashboardChecklistItem = {
  id: number;
  title: string;
  done: boolean;
};
export type DashboardHistoryEntry = {
  id: number;
  action: string;
  created_at: string;
};
export type DashboardChatMessage = {
  id: number;
  message_type: string;
  content: string;
  created_at: string;
};

export type DashboardCardDetail = {
  id: number;
  control_code: string | null;
  title: string;
  tag: string;
  status: CardStatus;
  // Campos do quadro Kanban. `description` é o texto normativo do
  // controle — é o que o cliente precisa ler para saber o que entregar
  // (U7), e até esta entrega não tinha onde existir na plataforma.
  description: string | null;
  column_id: number | null;
  labels: BoardLabelRef[];
  checklist: DashboardChecklistItem[];
  history: DashboardHistoryEntry[];
  chat: DashboardChatMessage[];
};
```

**Nenhum import novo é necessário** — `BoardLabelRef` é declarado no próprio bloco acima.
`empresas/[id]/dashboard/actions.ts` declara um tipo estruturalmente idêntico, de propósito:
importá-lo daqui criaria um ciclo (aquele arquivo já importa `CardStatus` deste). Tipos
estruturais em TypeScript são compatíveis por forma, então os dois interoperam sem cast.

---

#### `frontend/app/private/admin/empresas/[id]/dashboard/actions.ts`

##### 1. Ação Manual

Abra o arquivo e substitua o conteúdo inteiro. Todas as actions atuais permanecem; entram
nove novas.

> **`moveCardAction` NÃO chama `revalidatePath`** (PRD §4.7). Revalidar recarregaria os 215
> cards a cada arrasto e anularia o `useOptimistic` — a UI voltaria ao estado do servidor no
> meio da interação. `createColumnAction`, `deleteColumnAction` e
> `applyTemplateToCompanyAction` **chamam**, porque mudam a estrutura do quadro e não a
> posição de um item.

##### 2. Código Fonte Completo

```typescript
"use server";

import { revalidatePath } from "next/cache";
import { getAccessToken, requireAdmin } from "@/lib/session";
import { CardStatus } from "../../../actions";
import { callBackend } from "@/lib/server-backend";

export type BoardLabelRef = {
  id: number;
  name: string;
  color: string;
};

export type CompanyDashboardCardListItem = {
  id: number;
  control_code: string | null;
  title: string;
  tag: string;
  status: CardStatus;
  category_id: number | null;
  category_name: string | null;
  hidden: boolean;
  origin_template_card_id: number | null;
  is_outdated: boolean;
  column_id: number | null;
  position: string;
  description: string | null;
  labels: BoardLabelRef[];
};

export type BoardCard = {
  id: number;
  control_code: string | null;
  title: string;
  description: string | null;
  status: CardStatus;
  position: string;
  column_id: number | null;
  category_id: number | null;
  category_name: string | null;
  labels: BoardLabelRef[];
  hidden: boolean;
  origin_template_card_id: number | null;
  is_outdated: boolean;
};

export type BoardColumnKind = "COLUMN" | "SECTION";

export type BoardColumn = {
  id: number;
  name: string;
  kind: BoardColumnKind;
  position: string;
  hidden: boolean;
  wip_limit: number | null;
  cards: BoardCard[];
  card_count: number;
};

export type Board = {
  dashboard_id: number;
  company_id: number;
  title: string;
  columns: BoardColumn[];
  uncolumned: BoardCard[];
  labels: BoardLabelRef[];
};

export type DashboardCardCategory = {
  id: number;
  name: string;
  color: string;
  sort_order: number;
};

export type DashboardLabel = {
  id: number;
  name: string;
  color: string;
  sort_order: number;
};

export type DashboardTemplateOption = {
  id: number;
  name: string;
  description: string | null;
  is_default: boolean;
  card_count: number;
};

const ROTA_DASHBOARD = "/private/admin/empresas/[id]/dashboard";

/**
 * Quadro completo da empresa — colunas ordenadas, cards agrupados e o
 * vocabulário de etiquetas, numa chamada só.
 * Backend: GET /api/v1/dashboard/companies/{id}/board.
 */
export async function getBoardAction(
  companyId: number,
  includeHidden = false,
  search = "",
): Promise<Board> {
  await requireAdmin();
  const token = await getAccessToken();
  const parametros = new URLSearchParams({
    include_hidden: String(includeHidden),
    search,
  });
  return callBackend<Board>(
    `/api/v1/dashboard/companies/${companyId}/board?${parametros.toString()}`,
    { token: token ?? undefined },
  );
}

/**
 * Cards de UMA empresa, com categoria/ocultação/rastreio de template.
 * Backend: GET /api/v1/dashboard/companies/{id}/cards.
 */
export async function listCardsForCompanyAction(
  companyId: number,
  includeHidden = true,
): Promise<CompanyDashboardCardListItem[]> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<CompanyDashboardCardListItem[]>(
    `/api/v1/dashboard/companies/${companyId}/cards?include_hidden=${includeHidden}`,
    { token: token ?? undefined },
  );
}

/* Categorias disponíveis. Backend: GET /api/v1/admin/dashboard-categories.  */
export async function listCategoriesAction(): Promise<DashboardCardCategory[]> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<DashboardCardCategory[]>(
    "/api/v1/admin/dashboard-categories",
    {
      token: token ?? undefined,
    },
  );
}

/* Vocabulário de etiquetas. Backend: GET /api/v1/admin/dashboard-labels. */
export async function listLabelsAction(): Promise<DashboardLabel[]> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<DashboardLabel[]>("/api/v1/admin/dashboard-labels", {
    token: token ?? undefined,
  });
}

export type CreateCategoryResult =
  | { ok: true; category: DashboardCardCategory }
  | { ok: false; message: string };

/* Cria uma categoria nova sem sair da tela de cards ("+ Nova categoria"). */
export async function createCategoryAction(
  name: string,
  color: string,
): Promise<CreateCategoryResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const category = await callBackend<DashboardCardCategory>(
      "/api/v1/admin/dashboard-categories",
      {
        method: "POST",
        token: token ?? undefined,
        body: { name, color, sort_order: 0 },
      },
    );
    return { ok: true, category };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao criar a categoria.";
    return { ok: false, message };
  }
}

/* Templates disponíveis para aplicar. Backend: GET /api/v1/admin/templates. */
export async function listTemplatesAction(): Promise<
  DashboardTemplateOption[]
> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<DashboardTemplateOption[]>("/api/v1/admin/templates", {
    token: token ?? undefined,
  });
}

export type ApplyTemplateResult =
  | {
      ok: true;
      created_count: number;
      adopted_count: number;
      already_applied_count: number;
      outdated_card_ids: number[];
      columns_created_count: number;
    }
  | { ok: false; message: string };

/*
 * Aplica um template numa empresa já existente — idempotente: cria só o
 * que falta e sinaliza (sem sobrescrever) os cards que divergem do
 * template atual. Backend: POST
 * /api/v1/dashboard/companies/{id}/apply-template.
 */
export async function applyTemplateToCompanyAction(
  companyId: number,
  templateId: number,
): Promise<ApplyTemplateResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const result = await callBackend<{
      created_count: number;
      adopted_count: number;
      already_applied_count: number;
      outdated_card_ids: number[];
      columns_created_count: number;
    }>(`/api/v1/dashboard/companies/${companyId}/apply-template`, {
      method: "POST",
      token: token ?? undefined,
      body: { template_id: templateId },
    });
    revalidatePath(ROTA_DASHBOARD, "page");
    return { ok: true, ...result };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao aplicar o template.";
    return { ok: false, message };
  }
}

export type BulkCardOperation =
  | "hide"
  | "unhide"
  | "remove"
  | "set_category"
  | "set_column"
  | "restore_from_template";

export type BulkCardOperationResult =
  | { ok: true; affected_count: number }
  | { ok: false; message: string };

/*
 * Operação em lote sobre os cards de uma empresa. Backend: PATCH
 * /api/v1/dashboard/companies/{id}/cards/bulk.
 */
export async function bulkUpdateCardsAction(
  companyId: number,
  cardIds: number[],
  operation: BulkCardOperation,
  categoryId: number | null = null,
  columnId: number | null = null,
): Promise<BulkCardOperationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const result = await callBackend<{ affected_count: number }>(
      `/api/v1/dashboard/companies/${companyId}/cards/bulk`,
      {
        method: "PATCH",
        token: token ?? undefined,
        body: {
          card_ids: cardIds,
          operation,
          category_id: categoryId,
          column_id: columnId,
        },
      },
    );
    return { ok: true, affected_count: result.affected_count };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao aplicar a operação";
    return { ok: false, message };
  }
}

export type CreateCardResult =
  | { ok: true; card: CompanyDashboardCardListItem }
  | { ok: false; message: string };

/*
 * Cria um card manual ("+ Adicionar card" no rodapé de uma coluna). O
 * card nasce sem `origin_template_card_id` — é o que o distingue
 * visualmente como "custom" na lista.
 */
export async function createCardForCompanyAction(
  companyId: number,
  title: string,
  categoryId: number,
  controlCode: string | null,
  columnId: number | null = null,
  description: string | null = null,
): Promise<CreateCardResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const card = await callBackend<CompanyDashboardCardListItem>(
      `/api/v1/dashboard/companies/${companyId}/cards`,
      {
        method: "POST",
        token: token ?? undefined,
        body: {
          title,
          category_id: categoryId,
          control_code: controlCode,
          column_id: columnId,
          description,
        },
      },
    );
    return { ok: true, card };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao criar o card";
    return { ok: false, message };
  }
}

// -------------------------------------------------- Colunas do quadro

export type BoardColumnRef = {
  id: number;
  name: string;
  kind: BoardColumnKind;
  position: string;
  hidden: boolean;
  wip_limit: number | null;
};

export type ColumnMutationResult =
  | { ok: true; column: BoardColumnRef }
  | { ok: false; message: string };

/* Backend: POST /api/v1/dashboard/companies/{id}/columns. */
export async function createColumnAction(
  companyId: number,
  name: string,
  kind: BoardColumnKind = "COLUMN",
  afterColumnId: number | null = null,
): Promise<ColumnMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const column = await callBackend<BoardColumnRef>(
      `/api/v1/dashboard/companies/${companyId}/columns`,
      {
        method: "POST",
        token: token ?? undefined,
        body: { name, kind, after_column_id: afterColumnId },
      },
    );
    // Criar coluna muda a ESTRUTURA do quadro, não a posição de um item:
    // revalidar aqui é barato e mantém o Server Component em dia.
    revalidatePath(ROTA_DASHBOARD, "page");
    return { ok: true, column };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao criar a coluna.";
    return { ok: false, message };
  }
}

/* Backend: PATCH /api/v1/dashboard/columns/{id}. */
export async function updateColumnAction(
  columnId: number,
  name: string,
  hidden: boolean,
  wipLimit: number | null,
): Promise<ColumnMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const column = await callBackend<BoardColumnRef>(
      `/api/v1/dashboard/columns/${columnId}`,
      {
        method: "PATCH",
        token: token ?? undefined,
        body: { name, hidden, wip_limit: wipLimit },
      },
    );
    return { ok: true, column };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao editar a coluna.";
    return { ok: false, message };
  }
}

/* Backend: PATCH /api/v1/dashboard/columns/{id}/move. */
export async function moveColumnAction(
  columnId: number,
  prevColumnId: number | null,
  nextColumnId: number | null,
): Promise<ColumnMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const column = await callBackend<BoardColumnRef>(
      `/api/v1/dashboard/columns/${columnId}/move`,
      {
        method: "PATCH",
        token: token ?? undefined,
        body: { prev_column_id: prevColumnId, next_column_id: nextColumnId },
      },
    );
    return { ok: true, column };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao mover a coluna.";
    return { ok: false, message };
  }
}

export type DeleteColumnResult = { ok: true } | { ok: false; message: string };

/* Backend: DELETE /api/v1/dashboard/columns/{id} — 409 se houver card visível. */
export async function deleteColumnAction(
  columnId: number,
): Promise<DeleteColumnResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(`/api/v1/dashboard/columns/${columnId}`, {
      method: "DELETE",
      token: token ?? undefined,
    });
    revalidatePath(ROTA_DASHBOARD, "page");
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao excluir a coluna.";
    return { ok: false, message };
  }
}

// ------------------------------------------------------- Cards do quadro

export type MoveCardResult =
  | { ok: true; card: BoardCard }
  | { ok: false; message: string };

/**
 * Move um card entre/dentro de colunas.
 *
 * O cliente manda ÂNCORAS (`prevCardId`/`nextCardId`), nunca a chave de
 * ordenação: quem calcula a `position` é o servidor, dentro da transação
 * (§4.2 do PRD).
 *
 * **Sem `revalidatePath` de propósito** (§4.7 do PRD): revalidar
 * recarregaria os 215 cards a cada arrasto e desfaria o `useOptimistic`
 * no meio da interação. O estado local é a verdade durante a sessão.
 */
export async function moveCardAction(
  cardId: number,
  columnId: number | null,
  prevCardId: number | null,
  nextCardId: number | null,
): Promise<MoveCardResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const card = await callBackend<BoardCard>(
      `/api/v1/dashboard/cards/${cardId}/move`,
      {
        method: "PATCH",
        token: token ?? undefined,
        body: {
          column_id: columnId,
          prev_card_id: prevCardId,
          next_card_id: nextCardId,
        },
      },
    );
    return { ok: true, card };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao mover o card.";
    return { ok: false, message };
  }
}

export type UpdateCardResult =
  | { ok: true; card: BoardCard }
  | { ok: false; message: string };

/* Backend: PATCH /api/v1/dashboard/cards/{id} — texto do card, nunca status. */
export async function updateCardAction(
  cardId: number,
  title: string,
  description: string | null,
  controlCode: string | null,
  categoryId: number | null,
): Promise<UpdateCardResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const card = await callBackend<BoardCard>(
      `/api/v1/dashboard/cards/${cardId}`,
      {
        method: "PATCH",
        token: token ?? undefined,
        body: {
          title,
          description,
          control_code: controlCode,
          category_id: categoryId,
        },
      },
    );
    return { ok: true, card };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao editar o card.";
    return { ok: false, message };
  }
}

export type SetCardLabelsResult =
  | { ok: true; labels: BoardLabelRef[] }
  | { ok: false; message: string };

/* Backend: PUT /api/v1/dashboard/cards/{id}/labels — substitui o conjunto. */
export async function setCardLabelsAction(
  cardId: number,
  labelIds: number[],
): Promise<SetCardLabelsResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const labels = await callBackend<BoardLabelRef[]>(
      `/api/v1/dashboard/cards/${cardId}/labels`,
      {
        method: "PUT",
        token: token ?? undefined,
        body: { label_ids: labelIds },
      },
    );
    return { ok: true, labels };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao aplicar as etiquetas.";
    return { ok: false, message };
  }
}
```

---

#### `…/dashboard/_components/board.tsx`

##### 1. Ação Manual

Crie o diretório `_components` dentro de
`frontend/app/private/admin/empresas/[id]/dashboard/` e, dentro dele, o arquivo
`board.tsx`.

> **`readOnly` não desabilita sensores — ele NÃO MONTA o `DndContext`** (CA-17). Sensor
> desabilitado ainda registra ouvintes de ponteiro e ainda renderiza os controles de
> edição; o cliente não pode ver nem os controles nem o comportamento de arrasto.

##### 2. Código Fonte Completo

```tsx
"use client";

import { useMemo, useState, type ReactNode } from "react";
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  closestCorners,
  useSensor,
  useSensors,
  type Announcements,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  horizontalListSortingStrategy,
  sortableKeyboardCoordinates,
} from "@dnd-kit/sortable";

import type {
  Board as BoardData,
  BoardCard as BoardCardData,
  BoardColumn as BoardColumnData,
} from "../actions";
import { BoardCard } from "./board-card";
import { BoardColumn } from "./board-column";

/** Intenção de mover um card, na forma que o backend espera (âncoras). */
export type MoveIntent = {
  cardId: number;
  columnId: number | null;
  prevCardId: number | null;
  nextCardId: number | null;
};

export type ColumnMenuHandlers = {
  onRenameColumn: (column: BoardColumnData) => void;
  onArchiveColumn: (column: BoardColumnData) => void;
  onDeleteColumn: (column: BoardColumnData) => void;
  onMoveColumn: (column: BoardColumnData, direcao: -1 | 1) => void;
  onAddCard: (column: BoardColumnData) => void;
};

type BoardProps = {
  board: BoardData;
  readOnly?: boolean;
  selectedCardId: number | null;
  onSelectCard: (cardId: number) => void;
  selectedCardIds?: Set<number>;
  onToggleCardSelection?: (cardId: number) => void;
  onToggleColumnSelection?: (column: BoardColumnData) => void;
  collapsedColumns?: Set<number>;
  onToggleColumnCollapse?: (columnId: number) => void;
  onMoveCard?: (intent: MoveIntent) => void;
  columnHandlers?: ColumnMenuHandlers;
  outdatedCardIds?: number[];
  addCardColumnId?: number | null;
  addCardSlot?: ReactNode;
};

const PREFIXO_CARD = "card:";
const PREFIXO_COLUNA = "column:";
const PREFIXO_AREA = "column-drop:";

/** Todos os cards do quadro, incluindo o balde `uncolumned`. */
export function allCards(board: BoardData): BoardCardData[] {
  return [...board.columns.flatMap((coluna) => coluna.cards), ...board.uncolumned];
}

/**
 * Aplica um movimento de card ao quadro, em memória.
 *
 * Função PURA e exportada de propósito: é ela que o `useOptimistic` do
 * `company-dashboard-client.tsx` usa para reposicionar o card na hora, e
 * é ela que os testes exercitam sem precisar simular arrasto (jsdom não
 * simula). A `position` de verdade vem do servidor; aqui só a ORDEM
 * importa.
 */
export function moveCardInBoard(
  board: BoardData,
  intent: MoveIntent,
): BoardData {
  const card = allCards(board).find((c) => c.id === intent.cardId);
  if (!card) return board;

  const semCard = (cards: BoardCardData[]) =>
    cards.filter((c) => c.id !== intent.cardId);

  function inserir(cards: BoardCardData[]): BoardCardData[] {
    const restantes = semCard(cards);
    const movido = { ...card!, column_id: intent.columnId };

    if (intent.prevCardId !== null) {
      const indice = restantes.findIndex((c) => c.id === intent.prevCardId);
      if (indice >= 0) {
        return [
          ...restantes.slice(0, indice + 1),
          movido,
          ...restantes.slice(indice + 1),
        ];
      }
    }
    if (intent.nextCardId !== null) {
      const indice = restantes.findIndex((c) => c.id === intent.nextCardId);
      if (indice >= 0) {
        return [...restantes.slice(0, indice), movido, ...restantes.slice(indice)];
      }
    }
    // Sem âncora válida: vai para o fim da coluna.
    return [...restantes, movido];
  }

  return {
    ...board,
    columns: board.columns.map((coluna) => {
      if (coluna.id === intent.columnId) {
        const cards = inserir(coluna.cards);
        return { ...coluna, cards, card_count: cards.length };
      }
      const cards = semCard(coluna.cards);
      return { ...coluna, cards, card_count: cards.length };
    }),
    uncolumned:
      intent.columnId === null ? inserir(board.uncolumned) : semCard(board.uncolumned),
  };
}

/**
 * Calcula as âncoras a partir de uma coluna de destino e de um índice
 * de inserção — o que o `<select>` do menu "Mover para…" e o `onDragEnd`
 * precisam produzir.
 */
export function ancorasPorIndice(
  cardsDaColuna: BoardCardData[],
  cardId: number,
  indiceDestino: number,
): { prevCardId: number | null; nextCardId: number | null } {
  const restantes = cardsDaColuna.filter((c) => c.id !== cardId);
  const indice = Math.max(0, Math.min(indiceDestino, restantes.length));
  return {
    prevCardId: indice > 0 ? restantes[indice - 1].id : null,
    nextCardId: indice < restantes.length ? restantes[indice].id : null,
  };
}

export function Board({
  board,
  readOnly = false,
  selectedCardId,
  onSelectCard,
  selectedCardIds,
  onToggleCardSelection,
  onToggleColumnSelection,
  collapsedColumns,
  onToggleColumnCollapse,
  onMoveCard,
  columnHandlers,
  outdatedCardIds = [],
  addCardColumnId = null,
  addCardSlot = null,
}: BoardProps) {
  const [cardArrastado, setCardArrastado] = useState<BoardCardData | null>(null);

  const sensors = useSensors(
    // 8 px de tolerância: sem isso, um clique no card vira arrasto de
    // zero pixel e o painel de detalhe nunca abre.
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const colunasVisiveis = board.columns;
  const idsDeColuna = useMemo(
    () => colunasVisiveis.map((coluna) => `${PREFIXO_COLUNA}${coluna.id}`),
    [colunasVisiveis],
  );

  const cardPorId = useMemo(() => {
    const mapa = new Map<number, BoardCardData>();
    for (const card of allCards(board)) mapa.set(card.id, card);
    return mapa;
  }, [board]);

  function colunaDoCard(cardId: number): BoardColumnData | null {
    return (
      colunasVisiveis.find((coluna) =>
        coluna.cards.some((c) => c.id === cardId),
      ) ?? null
    );
  }

  /**
   * Anúncios em pt-BR para `aria-live` (CA-14). O dnd-kit anuncia em
   * inglês por padrão; um quadro operável por teclado que fala outra
   * língua não é operável de fato.
   */
  const announcements: Announcements = {
    onDragStart({ active }) {
      const card = cardPorId.get(idNumerico(active.id));
      return card
        ? `Card ${card.title} levantado. Use as setas para mover, espaço para soltar, Esc para cancelar.`
        : "Item levantado.";
    },
    onDragOver({ active, over }) {
      if (!over) return undefined;
      const card = cardPorId.get(idNumerico(active.id));
      return card ? `Card ${card.title} sobre uma nova posição.` : undefined;
    },
    onDragEnd({ active, over }) {
      const card = cardPorId.get(idNumerico(active.id));
      if (!card) return "Movimento concluído.";
      return over
        ? `Card ${card.title} solto na nova posição.`
        : `Card ${card.title} devolvido à posição original.`;
    },
    onDragCancel({ active }) {
      const card = cardPorId.get(idNumerico(active.id));
      return card
        ? `Movimento do card ${card.title} cancelado.`
        : "Movimento cancelado.";
    },
  };

  function handleDragStart(evento: DragStartEvent) {
    const tipo = evento.active.data.current?.type;
    if (tipo === "card") {
      setCardArrastado(cardPorId.get(idNumerico(evento.active.id)) ?? null);
    }
  }

  function handleDragEnd(evento: DragEndEvent) {
    setCardArrastado(null);
    const { active, over } = evento;
    if (!over) return;

    const tipo = active.data.current?.type;

    if (tipo === "column" && columnHandlers) {
      const origem = idsDeColuna.indexOf(String(active.id));
      const destino = idsDeColuna.indexOf(String(over.id));
      if (origem < 0 || destino < 0 || origem === destino) return;
      columnHandlers.onMoveColumn(
        colunasVisiveis[origem],
        destino > origem ? 1 : -1,
      );
      return;
    }

    if (tipo !== "card" || !onMoveCard) return;

    const cardId = idNumerico(active.id);
    const alvo = String(over.id);

    // Soltou sobre a ÁREA vazia de uma coluna: vai para o fim dela.
    if (alvo.startsWith(PREFIXO_AREA)) {
      const colunaId = Number(alvo.slice(PREFIXO_AREA.length));
      const coluna = colunasVisiveis.find((c) => c.id === colunaId);
      if (!coluna || coluna.kind === "SECTION") return;
      const { prevCardId, nextCardId } = ancorasPorIndice(
        coluna.cards,
        cardId,
        coluna.cards.length,
      );
      onMoveCard({ cardId, columnId: coluna.id, prevCardId, nextCardId });
      return;
    }

    // Soltou sobre OUTRO card: assume a posição dele.
    if (alvo.startsWith(PREFIXO_CARD)) {
      const alvoId = Number(alvo.slice(PREFIXO_CARD.length));
      if (alvoId === cardId) return;
      const coluna = colunaDoCard(alvoId);
      if (!coluna || coluna.kind === "SECTION") return;
      const restantes = coluna.cards.filter((c) => c.id !== cardId);
      const indice = restantes.findIndex((c) => c.id === alvoId);
      const { prevCardId, nextCardId } = ancorasPorIndice(
        coluna.cards,
        cardId,
        indice < 0 ? restantes.length : indice,
      );
      onMoveCard({ cardId, columnId: coluna.id, prevCardId, nextCardId });
    }
  }

  const conteudo = (
    <div className="board-scroller" data-testid="board-scroller">
      {colunasVisiveis.length === 0 ? (
        <p className="text-sm text-zinc-600">
          Este quadro ainda não tem colunas.
        </p>
      ) : null}

      {colunasVisiveis.map((coluna, indice) => (
        <BoardColumn
          key={coluna.id}
          column={coluna}
          readOnly={readOnly}
          isFirst={indice === 0}
          isLast={indice === colunasVisiveis.length - 1}
          collapsed={collapsedColumns?.has(coluna.id) ?? false}
          onToggleCollapse={onToggleColumnCollapse}
          onToggleColumnSelection={onToggleColumnSelection}
          selectedCardId={selectedCardId}
          onSelectCard={onSelectCard}
          selectedCardIds={selectedCardIds}
          onToggleCardSelection={onToggleCardSelection}
          onMoveCard={onMoveCard}
          board={board}
          columnHandlers={columnHandlers}
          outdatedCardIds={outdatedCardIds}
          addCardSlot={addCardColumnId === coluna.id ? addCardSlot : null}
        />
      ))}

      {board.uncolumned.length > 0 ? (
        <section className="board-column" aria-label="Sem coluna">
          <header className="border-b border-(--color-neutral) px-3 py-2">
            <p className="text-sm font-semibold text-(--color-dark)">
              Sem coluna
            </p>
            <p className="text-xs text-zinc-500">
              {board.uncolumned.length} card(s) órfão(s) de uma coluna excluída
            </p>
          </header>
          <div className="board-column-body">
            {board.uncolumned.map((card) => (
              <BoardCard
                key={card.id}
                card={card}
                columnId={null}
                readOnly={readOnly}
                isSelected={card.id === selectedCardId}
                isChecked={selectedCardIds?.has(card.id) ?? false}
                onSelect={onSelectCard}
                onToggleSelection={onToggleCardSelection}
                onMoveCard={onMoveCard}
                board={board}
                isOutdated={
                  card.is_outdated || outdatedCardIds.includes(card.id)
                }
              />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );

  // CA-17: em modo leitura o `DndContext` NÃO é montado. Desabilitar
  // sensores não bastaria — o cliente não pode ver controle de edição
  // nenhum, e um contexto montado ainda registra ouvintes de ponteiro.
  if (readOnly) {
    return conteudo;
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      accessibility={{ announcements }}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragCancel={() => setCardArrastado(null)}
    >
      <SortableContext items={idsDeColuna} strategy={horizontalListSortingStrategy}>
        {conteudo}
      </SortableContext>

      <DragOverlay>
        {cardArrastado ? (
          <div className="board-card opacity-90 shadow-lg">
            <p className="text-xs text-zinc-500">
              Controle {cardArrastado.control_code ?? "—"}
            </p>
            <p className="text-sm font-medium text-(--color-dark)">
              {cardArrastado.title}
            </p>
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}

function idNumerico(id: string | number): number {
  const texto = String(id);
  const separador = texto.indexOf(":");
  return Number(separador >= 0 ? texto.slice(separador + 1) : texto);
}
```

---

#### `…/dashboard/_components/board-column.tsx`

##### 1. Ação Manual

Crie o arquivo `_components/board-column.tsx`.

##### 2. Código Fonte Completo

```tsx
"use client";

import type { ReactNode } from "react";
import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";

import type {
  Board as BoardData,
  BoardColumn as BoardColumnData,
} from "../actions";
import { BoardCard } from "./board-card";
import type { ColumnMenuHandlers, MoveIntent } from "./board";

type BoardColumnProps = {
  column: BoardColumnData;
  board: BoardData;
  readOnly: boolean;
  isFirst: boolean;
  isLast: boolean;
  collapsed: boolean;
  onToggleCollapse?: (columnId: number) => void;
  onToggleColumnSelection?: (column: BoardColumnData) => void;
  selectedCardId: number | null;
  onSelectCard: (cardId: number) => void;
  selectedCardIds?: Set<number>;
  onToggleCardSelection?: (cardId: number) => void;
  onMoveCard?: (intent: MoveIntent) => void;
  columnHandlers?: ColumnMenuHandlers;
  outdatedCardIds: number[];
  addCardSlot?: ReactNode;
};

export function BoardColumn({
  column,
  board,
  readOnly,
  isFirst,
  isLast,
  collapsed,
  onToggleCollapse,
  onToggleColumnSelection,
  selectedCardId,
  onSelectCard,
  selectedCardIds,
  onToggleCardSelection,
  onMoveCard,
  columnHandlers,
  outdatedCardIds,
  addCardSlot,
}: BoardColumnProps) {
  /*
   * CA-18: `SECTION` é o separador `>>` do Trello. Renderiza como
   * divisor vertical — SEM área de soltar (nenhum `useDroppable`) e SEM
   * contador de cards, porque por definição ela não tem nenhum. Um
   * `useDroppable` aqui faria o dnd-kit oferecer a seção como destino
   * válido, e o servidor recusaria com 422 depois do arrasto já ter
   * "acontecido" na tela.
   */
  if (column.kind === "SECTION") {
    return (
      <div
        className="board-section-divider"
        role="separator"
        aria-orientation="vertical"
        aria-label={`Seção ${column.name}`}
        data-testid={`section-${column.id}`}
      >
        <span className="text-xs font-semibold tracking-wide text-white [writing-mode:vertical-rl]">
          {column.name}
        </span>
      </div>
    );
  }

  return <ColunaComum
    column={column}
    board={board}
    readOnly={readOnly}
    isFirst={isFirst}
    isLast={isLast}
    collapsed={collapsed}
    onToggleCollapse={onToggleCollapse}
    onToggleColumnSelection={onToggleColumnSelection}
    selectedCardId={selectedCardId}
    onSelectCard={onSelectCard}
    selectedCardIds={selectedCardIds}
    onToggleCardSelection={onToggleCardSelection}
    onMoveCard={onMoveCard}
    columnHandlers={columnHandlers}
    outdatedCardIds={outdatedCardIds}
    addCardSlot={addCardSlot}
  />;
}

/**
 * Componente separado porque `useDroppable` é um hook: chamá-lo depois
 * de um `return` condicional violaria as regras de hooks. A `SECTION`
 * sai antes; só a coluna comum chega aqui.
 */
function ColunaComum({
  column,
  board,
  readOnly,
  isFirst,
  isLast,
  collapsed,
  onToggleCollapse,
  onToggleColumnSelection,
  selectedCardId,
  onSelectCard,
  selectedCardIds,
  onToggleCardSelection,
  onMoveCard,
  columnHandlers,
  outdatedCardIds,
  addCardSlot,
}: BoardColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: `column-drop:${column.id}`,
    disabled: readOnly,
  });

  const selecionadosNaColuna = column.cards.filter((card) =>
    selectedCardIds?.has(card.id),
  ).length;
  const todosSelecionados =
    column.cards.length > 0 && selecionadosNaColuna === column.cards.length;

  const acimaDoLimite =
    column.wip_limit !== null && column.cards.length > column.wip_limit;

  return (
    <section
      className="board-column"
      aria-label={`Coluna ${column.name}`}
      data-testid={`column-${column.id}`}
    >
      <header className="flex items-start gap-2 border-b border-(--color-neutral) px-3 py-2">
        {!readOnly && onToggleColumnSelection ? (
          <input
            type="checkbox"
            className="mt-1"
            aria-label={`Selecionar todos os cards de ${column.name}`}
            checked={todosSelecionados}
            ref={(node) => {
              if (node) {
                node.indeterminate =
                  selecionadosNaColuna > 0 && !todosSelecionados;
              }
            }}
            onChange={() => onToggleColumnSelection(column)}
          />
        ) : null}

        <button
          type="button"
          className="flex-1 text-left"
          aria-expanded={!collapsed}
          onClick={() => onToggleCollapse?.(column.id)}
        >
          <span className="text-sm font-semibold text-(--color-dark)">
            {collapsed ? "▸" : "▾"} {column.name}
          </span>
          <span
            className={`ml-2 text-xs ${acimaDoLimite ? "font-semibold text-red-600" : "text-zinc-500"}`}
          >
            {column.cards.length}
            {column.wip_limit !== null ? `/${column.wip_limit}` : ""} card(s)
          </span>
          {column.hidden ? (
            <span className="ml-2 rounded-full bg-zinc-200 px-2 py-0.5 text-[10px] text-zinc-700">
              arquivada
            </span>
          ) : null}
        </button>

        {!readOnly && columnHandlers ? (
          <div className="flex shrink-0 items-center gap-1">
            <button
              type="button"
              className="rounded px-1 text-xs text-zinc-600 hover:bg-zinc-200 disabled:opacity-30"
              aria-label={`Mover coluna ${column.name} para a esquerda`}
              disabled={isFirst}
              onClick={() => columnHandlers.onMoveColumn(column, -1)}
            >
              ←
            </button>
            <button
              type="button"
              className="rounded px-1 text-xs text-zinc-600 hover:bg-zinc-200 disabled:opacity-30"
              aria-label={`Mover coluna ${column.name} para a direita`}
              disabled={isLast}
              onClick={() => columnHandlers.onMoveColumn(column, 1)}
            >
              →
            </button>
            <details className="relative">
              <summary
                className="cursor-pointer list-none rounded px-1 text-sm text-zinc-600 hover:bg-zinc-200"
                aria-label={`Ações da coluna ${column.name}`}
              >
                ⋯
              </summary>
              <div className="absolute right-0 z-20 mt-1 w-44 rounded-lg border border-(--color-neutral) bg-white p-1 shadow-lg">
                <button
                  type="button"
                  className="block w-full rounded px-2 py-1 text-left text-sm hover:bg-zinc-100"
                  onClick={() => columnHandlers.onRenameColumn(column)}
                >
                  Renomear
                </button>
                <button
                  type="button"
                  className="block w-full rounded px-2 py-1 text-left text-sm hover:bg-zinc-100"
                  onClick={() => columnHandlers.onArchiveColumn(column)}
                >
                  {column.hidden ? "Reexibir" : "Arquivar"}
                </button>
                <button
                  type="button"
                  className="block w-full rounded px-2 py-1 text-left text-sm text-red-700 hover:bg-red-50"
                  onClick={() => columnHandlers.onDeleteColumn(column)}
                >
                  Excluir
                </button>
              </div>
            </details>
          </div>
        ) : null}
      </header>

      {collapsed ? null : (
        <div
          ref={setNodeRef}
          className={`board-column-body ${isOver ? "bg-(--color-primary)/5" : ""}`}
        >
          <SortableContext
            items={column.cards.map((card) => `card:${card.id}`)}
            strategy={verticalListSortingStrategy}
          >
            {column.cards.map((card) => (
              <BoardCard
                key={card.id}
                card={card}
                columnId={column.id}
                readOnly={readOnly}
                isSelected={card.id === selectedCardId}
                isChecked={selectedCardIds?.has(card.id) ?? false}
                onSelect={onSelectCard}
                onToggleSelection={onToggleCardSelection}
                onMoveCard={onMoveCard}
                board={board}
                isOutdated={
                  card.is_outdated || outdatedCardIds.includes(card.id)
                }
              />
            ))}
          </SortableContext>

          {column.cards.length === 0 ? (
            <p className="px-1 py-4 text-center text-xs text-zinc-400">
              Nenhum card nesta coluna.
            </p>
          ) : null}
        </div>
      )}

      {!readOnly && columnHandlers ? (
        <footer className="border-t border-(--color-neutral) p-2">
          {addCardSlot ?? (
            <button
              type="button"
              className="text-xs font-medium text-(--color-primary)"
              onClick={() => columnHandlers.onAddCard(column)}
            >
              + Adicionar card
            </button>
          )}
        </footer>
      ) : null}
    </section>
  );
}
```

---

#### `…/dashboard/_components/board-card.tsx`

##### 1. Ação Manual

Crie o arquivo `_components/board-card.tsx`.

##### 2. Código Fonte Completo

```tsx
"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import {
  controlStatusBadgeClass,
  controlStatusLabel,
} from "@/lib/control-status";
import { labelChipClass, labelChipStyle, sortLabels } from "@/lib/board-labels";
import type { Board as BoardData, BoardCard as BoardCardData } from "../actions";
import type { MoveIntent } from "./board";
import { MoveCardMenu } from "./move-card-menu";

type BoardCardProps = {
  card: BoardCardData;
  columnId: number | null;
  readOnly: boolean;
  isSelected: boolean;
  isChecked: boolean;
  onSelect: (cardId: number) => void;
  onToggleSelection?: (cardId: number) => void;
  onMoveCard?: (intent: MoveIntent) => void;
  board: BoardData;
  isOutdated: boolean;
};

export function BoardCard(props: BoardCardProps) {
  // Em modo leitura o card não é arrastável e nenhum hook de arrasto é
  // montado (CA-17). Dois componentes, e não um `disabled`: um
  // `useSortable` desabilitado ainda instala atributos e ouvintes.
  return props.readOnly ? <CardEstatico {...props} /> : <CardArrastavel {...props} />;
}

function ConteudoDoCard({
  card,
  isSelected,
  isChecked,
  onSelect,
  onToggleSelection,
  onMoveCard,
  board,
  isOutdated,
  readOnly,
  dragHandle,
}: BoardCardProps & { dragHandle?: React.ReactNode }) {
  return (
    <div
      className={`board-card ${isSelected ? "board-card-selected" : ""}`}
      data-testid={`card-${card.id}`}
    >
      <div className="flex items-start gap-2">
        {!readOnly && onToggleSelection ? (
          <input
            type="checkbox"
            className="mt-1"
            aria-label={`Selecionar ${card.title}`}
            checked={isChecked}
            onChange={() => onToggleSelection(card.id)}
          />
        ) : null}

        <button
          type="button"
          className="flex-1 text-left"
          onClick={() => onSelect(card.id)}
        >
          <p className="text-xs text-zinc-500">
            Controle {card.control_code ?? "—"}
          </p>
          <p className="text-sm font-medium text-(--color-dark)">{card.title}</p>
        </button>

        {dragHandle}
      </div>

      {card.labels.length > 0 ? (
        <div className="mt-1 flex flex-wrap gap-1">
          {sortLabels(card.labels).map((etiqueta) => (
            <span
              key={etiqueta.id}
              className={labelChipClass(etiqueta.color)}
              style={labelChipStyle(etiqueta.color)}
            >
              {etiqueta.name}
            </span>
          ))}
        </div>
      ) : null}

      <div className="mt-1 flex flex-wrap items-center gap-1">
        <span className={controlStatusBadgeClass(card.status)}>
          {controlStatusLabel(card.status)}
        </span>
        {card.origin_template_card_id === null ? (
          <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] text-zinc-600">
            custom
          </span>
        ) : null}
        {isOutdated ? (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] text-amber-800">
            ≠ template
          </span>
        ) : null}
        {card.hidden ? (
          <span className="rounded-full bg-zinc-200 px-2 py-0.5 text-[10px] text-zinc-700">
            oculto
          </span>
        ) : null}
      </div>

      {!readOnly && onMoveCard ? (
        <MoveCardMenu card={card} board={board} onMoveCard={onMoveCard} />
      ) : null}
    </div>
  );
}

function CardEstatico(props: BoardCardProps) {
  return <ConteudoDoCard {...props} />;
}

function CardArrastavel(props: BoardCardProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({
      id: `card:${props.card.id}`,
      data: { type: "card", columnId: props.columnId },
    });

  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.4 : 1,
      }}
    >
      <ConteudoDoCard
        {...props}
        dragHandle={
          <button
            type="button"
            className="shrink-0 cursor-grab rounded px-1 text-zinc-400 hover:bg-zinc-100"
            aria-label={`Arrastar o card ${props.card.title}`}
            {...attributes}
            {...listeners}
          >
            ⠿
          </button>
        }
      />
    </div>
  );
}
```

---

#### `…/dashboard/_components/move-card-menu.tsx`

##### 1. Ação Manual

Crie o arquivo `_components/move-card-menu.tsx`.

> **Este componente não é um extra — é requisito bloqueante (CA-15).** Ele cobre leitor de
> tela, tablet e o caso de o `@dnd-kit` falhar em carregar. É também o caminho que os testes
> de integração usam, já que jsdom não simula arrasto.

##### 2. Código Fonte Completo

```tsx
"use client";

import { useState } from "react";

import type { Board as BoardData, BoardCard as BoardCardData } from "../actions";
import { ancorasPorIndice, type MoveIntent } from "./board";

type MoveCardMenuProps = {
  card: BoardCardData;
  board: BoardData;
  onMoveCard: (intent: MoveIntent) => void;
};

export function MoveCardMenu({ card, board, onMoveCard }: MoveCardMenuProps) {
  // Colunas `SECTION` ficam fora da lista: elas não aceitam card, e
  // oferecê-las aqui só produziria um 422 depois do clique (CA-18).
  const colunasDestino = board.columns.filter(
    (coluna) => coluna.kind === "COLUMN",
  );

  const [colunaId, setColunaId] = useState<number | "">(card.column_id ?? "");
  const [indice, setIndice] = useState(0);

  const colunaEscolhida =
    colunaId === ""
      ? null
      : (colunasDestino.find((coluna) => coluna.id === colunaId) ?? null);

  const cardsDoDestino = colunaEscolhida
    ? colunaEscolhida.cards.filter((c) => c.id !== card.id)
    : [];

  function confirmar() {
    if (colunaEscolhida === null) return;
    const { prevCardId, nextCardId } = ancorasPorIndice(
      colunaEscolhida.cards,
      card.id,
      indice,
    );
    onMoveCard({
      cardId: card.id,
      columnId: colunaEscolhida.id,
      prevCardId,
      nextCardId,
    });
  }

  return (
    <details className="mt-2 border-t border-(--color-neutral) pt-1">
      <summary className="cursor-pointer list-none text-[11px] font-medium text-(--color-primary)">
        Mover para…
      </summary>

      <div className="mt-2 space-y-2">
        <label className="block text-[11px] text-zinc-600">
          Coluna
          <select
            className="field mt-0.5 text-xs"
            aria-label={`Coluna de destino para ${card.title}`}
            value={colunaId}
            onChange={(evento) => {
              setColunaId(evento.target.value ? Number(evento.target.value) : "");
              setIndice(0);
            }}
          >
            <option value="">Escolha a coluna…</option>
            {colunasDestino.map((coluna) => (
              <option key={coluna.id} value={coluna.id}>
                {coluna.name}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-[11px] text-zinc-600">
          Posição
          <select
            className="field mt-0.5 text-xs"
            aria-label={`Posição de destino para ${card.title}`}
            value={indice}
            onChange={(evento) => setIndice(Number(evento.target.value))}
          >
            {Array.from({ length: cardsDoDestino.length + 1 }, (_, i) => (
              <option key={i} value={i}>
                {i === 0
                  ? "No início"
                  : i === cardsDoDestino.length
                    ? "No fim"
                    : `Depois de: ${cardsDoDestino[i - 1].title}`}
              </option>
            ))}
          </select>
        </label>

        <button
          type="button"
          className="btn-primary w-full text-xs"
          disabled={colunaEscolhida === null}
          onClick={confirmar}
        >
          Mover
        </button>
      </div>
    </details>
  );
}
```

---

#### `…/dashboard/_components/card-detail-panel.tsx`

##### 1. Ação Manual

Crie o arquivo `_components/card-detail-panel.tsx`.

> **Extração pura — faça-a no PRIMEIRO commit, antes de trocar o agrupamento** (mitigação
> de R1). O conteúdo abaixo é o painel que hoje vive dentro de
> `company-dashboard-client.tsx` (linhas ~660-820 do JSX, mais `atualizarStatus` e
> `alternarChecklist`), sem mudança de comportamento — mais o campo `description`, que é
> novo. Commite a extração, rode `npm run test` e só então siga para o próximo arquivo.

##### 2. Código Fonte Completo

```tsx
"use client";

import { useMemo } from "react";

import {
  CONTROL_STATUS_ORDER,
  controlStatusBadgeClass,
  controlStatusButtonClass,
  controlStatusLabel,
} from "@/lib/control-status";
import { labelChipClass, labelChipStyle, sortLabels } from "@/lib/board-labels";
import type {
  CardStatus,
  DashboardCardDetail,
} from "@/app/private/admin/actions";
import type { BoardLabelRef, DashboardLabel } from "../actions";

type CardDetailPanelProps = {
  cardDetail: DashboardCardDetail | null;
  isLoading: boolean;
  isPending: boolean;
  readOnly?: boolean;
  labels?: DashboardLabel[];
  onChangeStatus?: (status: CardStatus) => void;
  onToggleChecklistItem?: (itemId: number) => void;
  onToggleLabel?: (labelId: number) => void;
};

export function CardDetailPanel({
  cardDetail,
  isLoading,
  isPending,
  readOnly = false,
  labels = [],
  onChangeStatus,
  onToggleChecklistItem,
  onToggleLabel,
}: CardDetailPanelProps) {
  const checkListInfo = useMemo(() => {
    if (!cardDetail) return { total: 0, concluidos: 0 };
    const total = cardDetail.checklist.length;
    const concluidos = cardDetail.checklist.filter((i) => i.done).length;
    return { total, concluidos };
  }, [cardDetail]);

  const percentual =
    checkListInfo.total === 0
      ? 0
      : Math.round((checkListInfo.concluidos / checkListInfo.total) * 100);

  const etiquetasDoCard: BoardLabelRef[] = cardDetail?.labels ?? [];
  const idsDoCard = new Set(etiquetasDoCard.map((e) => e.id));

  return (
    <section className="space-y-4">
      <article className="card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-lg font-semibold">
            {cardDetail
              ? `Controle ${cardDetail.control_code ?? "—"} - ${cardDetail.title}`
              : "Nenhum controle selecionado"}
          </h3>
          <span
            className={controlStatusBadgeClass(cardDetail?.status ?? "EM_ANALISE")}
          >
            {cardDetail ? controlStatusLabel(cardDetail.status) : "Sem status"}
          </span>
        </div>

        {isLoading ? (
          <p className="mt-3 text-sm text-zinc-500">Carregando detalhes...</p>
        ) : null}

        {etiquetasDoCard.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-1">
            {sortLabels(etiquetasDoCard).map((etiqueta) => (
              <span
                key={etiqueta.id}
                className={labelChipClass(etiqueta.color)}
                style={labelChipStyle(etiqueta.color)}
              >
                {etiqueta.name}
              </span>
            ))}
          </div>
        ) : null}

        {/*
          A descrição é o texto normativo do controle. Até esta entrega
          ela existia só em `DashboardTemplateCard` e era descartada na
          aplicação do template — o cliente nunca conseguia lê-la (U7).
        */}
        {cardDetail?.description ? (
          <div className="mt-4">
            <p className="mb-1 text-xs font-medium text-zinc-500">
              Descrição do controle
            </p>
            <p className="whitespace-pre-wrap rounded-lg bg-zinc-50 p-3 text-sm text-zinc-700">
              {cardDetail.description}
            </p>
          </div>
        ) : null}

        {!readOnly && onChangeStatus ? (
          <div className="mt-4">
            <p className="mb-2 text-xs font-medium text-zinc-500">
              Status do controle
            </p>
            <div
              role="group"
              aria-label="Status do controle"
              className="flex flex-wrap gap-2"
            >
              {CONTROL_STATUS_ORDER.map((status) => {
                const isActive = cardDetail?.status === status;
                return (
                  <button
                    key={status}
                    type="button"
                    className={controlStatusButtonClass(status, isActive)}
                    aria-pressed={isActive}
                    disabled={!cardDetail || isPending}
                    onClick={() => onChangeStatus(status)}
                  >
                    {controlStatusLabel(status)}
                  </button>
                );
              })}
            </div>
          </div>
        ) : null}

        {!readOnly && onToggleLabel && labels.length > 0 ? (
          <div className="mt-4">
            <p className="mb-2 text-xs font-medium text-zinc-500">
              Etiquetas de criticidade
            </p>
            <div className="flex flex-wrap gap-2">
              {sortLabels(labels).map((etiqueta) => {
                const ativa = idsDoCard.has(etiqueta.id);
                return (
                  <button
                    key={etiqueta.id}
                    type="button"
                    aria-pressed={ativa}
                    disabled={!cardDetail || isPending}
                    className={`${labelChipClass(etiqueta.color)} ${
                      ativa ? "ring-2 ring-(--color-dark)" : "opacity-50"
                    }`}
                    style={labelChipStyle(etiqueta.color)}
                    onClick={() => onToggleLabel(etiqueta.id)}
                  >
                    {etiqueta.name}
                  </button>
                );
              })}
            </div>
          </div>
        ) : null}

        {!readOnly ? (
          <div className="mt-4">
            <div className="mb-1 flex justify-between text-xs text-zinc-600">
              <span>Progresso</span>
              <span>{percentual}%</span>
            </div>
            <div className="h-2 w-full rounded-full bg-zinc-200">
              <div
                className="h-2 rounded-full bg-green-500 transition-all"
                style={{ width: `${percentual}%` }}
              ></div>
            </div>
          </div>
        ) : null}
      </article>

      {!readOnly ? (
        <article className="card">
          <h3 className="text-base font-semibold">Checklist de conformidade</h3>
          <p className="mt-1 text-sm text-zinc-600">
            {checkListInfo.concluidos} de {checkListInfo.total} itens concluídos
          </p>
          <ul className="mt-3 space-y-2">
            {(cardDetail?.checklist ?? []).map((item) => (
              <li
                key={item.id}
                className="flex items-center gap-2 rounded-lg bg-zinc-50 p-2"
              >
                <input
                  type="checkbox"
                  checked={item.done}
                  disabled={isPending}
                  onChange={() => onToggleChecklistItem?.(item.id)}
                />
                <span
                  className={`text-sm ${item.done ? "text-zinc-500 line-through" : ""}`}
                >
                  {item.title}
                </span>
              </li>
            ))}
          </ul>
        </article>
      ) : null}

      {!readOnly ? (
        <article className="card">
          <h3 className="text-base font-semibold">Histórico</h3>
          <ul className="mt-3 space-y-2">
            {(cardDetail?.history ?? []).map((evento, index) => {
              const isUltimo = index === (cardDetail?.history.length ?? 0) - 1;
              return (
                <li
                  key={evento.id}
                  className={`rounded-lg border px-3 py-2 text-sm ${
                    isUltimo
                      ? "border-green-300 bg-green-50 font-semibold"
                      : "border-(--color-neutral)"
                  }`}
                >
                  {evento.action}
                </li>
              );
            })}
          </ul>
        </article>
      ) : null}

      <article className="card">
        <h3 className="text-base font-semibold">Conversa com o cliente</h3>
        <ul className="mt-3 space-y-2">
          {(cardDetail?.chat ?? []).map((mensagem) => (
            <li
              key={mensagem.id}
              className={`rounded-lg px-3 py-2 text-sm ${
                mensagem.message_type === "QUESTION"
                  ? "bg-zinc-50"
                  : "bg-(--color-primary)/5"
              }`}
            >
              {mensagem.content}
            </li>
          ))}
          {(cardDetail?.chat ?? []).length === 0 ? (
            <li className="text-sm text-zinc-500">Nenhuma mensagem ainda.</li>
          ) : null}
        </ul>
      </article>
    </section>
  );
}
```

---

#### `…/dashboard/company-dashboard-client.tsx`

##### 1. Ação Manual

Abra `frontend/app/private/admin/empresas/[id]/dashboard/company-dashboard-client.tsx` e
substitua o conteúdo inteiro.

> **Refatoração maior 🔴 — faça em DOIS commits** (mitigação de R1, PRD §10):
>
> - **Commit A:** crie `_components/card-detail-panel.tsx` (arquivo anterior) e troque as
>   ~180 linhas de JSX do painel de detalhe pelo componente, sem mexer em mais nada. Rode
>   `npm run test` e `npx tsc --noEmit`. Comportamento idêntico.
> - **Commit B:** só então troque o agrupamento por categoria pelo `<Board>` — é o conteúdo
>   completo abaixo.
>
> O que **sai**: `UNCATEGORIZED_KEY`, `type CardGroup`, o `useMemo` de `groups` (38 linhas)
> e as ~245 linhas de JSX que renderizavam os grupos.
> O que **permanece**: busca, `showHidden`, seleção em massa, barra de ação em lote, aplicar
> template, criar categoria e criar card.

##### 2. Código Fonte Completo

```tsx
"use client";

import {
  useEffect,
  useMemo,
  useOptimistic,
  useRef,
  useState,
  useTransition,
} from "react";
import {
  getCardDetailAction,
  updateCardStatusAction,
  toggleChecklistItemAction,
  type CardStatus,
  type DashboardCardDetail,
} from "@/app/private/admin/actions";
import {
  applyTemplateToCompanyAction,
  bulkUpdateCardsAction,
  createCardForCompanyAction,
  createCategoryAction,
  createColumnAction,
  deleteColumnAction,
  getBoardAction,
  moveCardAction,
  moveColumnAction,
  setCardLabelsAction,
  updateColumnAction,
  type Board as BoardData,
  type BoardCard as BoardCardData,
  type BoardColumn as BoardColumnData,
  type DashboardCardCategory,
  type DashboardLabel,
  type DashboardTemplateOption,
} from "./actions";
import {
  Board,
  allCards,
  moveCardInBoard,
  type ColumnMenuHandlers,
  type MoveIntent,
} from "./_components/board";
import { CardDetailPanel } from "./_components/card-detail-panel";

type CompanyDashboardClientProps = {
  companyId: number;
  companyName: string;
  initialBoard: BoardData;
  initialCardDetail: DashboardCardDetail | null;
  categories: DashboardCardCategory[];
  labels: DashboardLabel[];
  templates: DashboardTemplateOption[];
};

export function CompanyDashboardClient({
  companyId,
  companyName,
  initialBoard,
  initialCardDetail,
  categories: initialCategories,
  labels,
  templates,
}: CompanyDashboardClientProps) {
  const [board, setBoard] = useState<BoardData>(initialBoard);
  /*
   * O arrasto reposiciona o card NA HORA e a Server Action confirma
   * depois (CA-16). Se a action falhar, o React descarta o estado
   * otimista sozinho ao fim da transição — não precisamos (nem devemos)
   * "desfazer" à mão: desfazer manualmente correria contra o descarte
   * automático e produziria um piscar duplo.
   */
  const [quadroOtimista, aplicarMovimentoOtimista] = useOptimistic(
    board,
    (estado: BoardData, intent: MoveIntent) => moveCardInBoard(estado, intent),
  );

  const [categories, setCategories] =
    useState<DashboardCardCategory[]>(initialCategories);
  const [cardSelecionadoId, setCardSelecionadoId] = useState<number | null>(
    allCards(initialBoard).find((card) => !card.hidden)?.id ?? null,
  );
  const [cardDetail, setCardDetail] = useState<DashboardCardDetail | null>(
    initialCardDetail,
  );
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const isFirstRender = useRef(true);

  const [busca, setBusca] = useState("");
  const [showHidden, setShowHidden] = useState(false);
  const [collapsedColumns, setCollapsedColumns] = useState<Set<number>>(
    new Set(),
  );
  const [selectedCardIds, setSelectedCardIds] = useState<Set<number>>(
    new Set(),
  );
  const [outdatedFromLastApply, setOutdatedFromLastApply] = useState<number[]>(
    [],
  );
  const [feedback, setFeedback] = useState("");
  const [isPending, startTransition] = useTransition();

  // Busca o detalhe do card sob demanda ao trocar de seleção — pula a
  // primeira renderização, pois o detalhe do card inicial já veio pronto
  // via props (initialCardDetail).
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    if (cardSelecionadoId === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setCardDetail(null);
      return;
    }

    let cancelado = false;
    setIsLoadingDetail(true);
    getCardDetailAction(cardSelecionadoId)
      .then((detail) => {
        if (!cancelado) setCardDetail(detail);
      })
      .catch(() => {
        if (!cancelado) setCardDetail(null);
      })
      .finally(() => {
        if (!cancelado) setIsLoadingDetail(false);
      });

    return () => {
      cancelado = true;
    };
  }, [cardSelecionadoId]);

  /*
   * O quadro chega do servidor JÁ AGRUPADO (D-5): o que sobra para o
   * cliente é só o FILTRO — busca, cards ocultos e colunas arquivadas.
   * As 38 linhas de `groups: CardGroup[]` que existiam aqui migraram
   * para `services/dashboard_board.py::get_board`.
   */
  const quadroVisivel: BoardData = useMemo(() => {
    const termo = busca.trim().toLocaleLowerCase();

    const passaNoFiltro = (card: BoardCardData) => {
      if (!showHidden && card.hidden) return false;
      if (!termo) return true;
      return (
        card.title.toLocaleLowerCase().includes(termo) ||
        (card.control_code ?? "").toLocaleLowerCase().includes(termo)
      );
    };

    return {
      ...quadroOtimista,
      columns: quadroOtimista.columns
        // CA-19: coluna arquivada só aparece com o toggle ligado — mesmo
        // comportamento que `showHidden` já tinha para cards.
        .filter((coluna) => showHidden || !coluna.hidden)
        .map((coluna) => {
          const cards = coluna.cards.filter(passaNoFiltro);
          return { ...coluna, cards, card_count: cards.length };
        }),
      uncolumned: quadroOtimista.uncolumned.filter(passaNoFiltro),
    };
  }, [quadroOtimista, busca, showHidden]);

  const todosOsCards = useMemo(() => allCards(quadroOtimista), [quadroOtimista]);
  const totalVisivel = todosOsCards.filter((card) => !card.hidden).length;
  const totalOculto = todosOsCards.length - totalVisivel;

  async function refreshBoard() {
    // `include_hidden=true` sempre: o filtro de ocultos é do cliente, e
    // recarregar sem eles faria o toggle "Mostrar ocultos" parar de
    // funcionar até o próximo F5.
    const fresco = await getBoardAction(companyId, true);
    setBoard(fresco);
    setSelectedCardIds(new Set());
  }

  function toggleColumnCollapse(columnId: number) {
    setCollapsedColumns((prev) => {
      const next = new Set(prev);
      if (next.has(columnId)) next.delete(columnId);
      else next.add(columnId);
      return next;
    });
  }

  function toggleCardSelection(cardId: number) {
    setSelectedCardIds((prev) => {
      const next = new Set(prev);
      if (next.has(cardId)) next.delete(cardId);
      else next.add(cardId);
      return next;
    });
  }

  function toggleColumnSelection(column: BoardColumnData) {
    const ids = column.cards.map((card) => card.id);
    const todosSelecionados = ids.every((id) => selectedCardIds.has(id));
    setSelectedCardIds((prev) => {
      const next = new Set(prev);
      for (const id of ids) {
        if (todosSelecionados) next.delete(id);
        else next.add(id);
      }
      return next;
    });
  }

  // ---- Mover card (arrasto e menu "Mover para…") ----
  function handleMoveCard(intent: MoveIntent) {
    setFeedback("");
    startTransition(async () => {
      aplicarMovimentoOtimista(intent);

      const resultado = await moveCardAction(
        intent.cardId,
        intent.columnId,
        intent.prevCardId,
        intent.nextCardId,
      );

      if (!resultado.ok) {
        // Não desfazemos à mão: ao fim desta transição o React descarta
        // o estado otimista e o quadro volta sozinho ao valor de `board`.
        setFeedback(`Não foi possível mover o card: ${resultado.message}`);
        return;
      }

      setBoard((anterior) => {
        const movido = moveCardInBoard(anterior, intent);
        // Reconcilia com a `position` que o SERVIDOR calculou — a nossa
        // era só ordem visual.
        return {
          ...movido,
          columns: movido.columns.map((coluna) => ({
            ...coluna,
            cards: coluna.cards.map((card) =>
              card.id === resultado.card.id ? resultado.card : card,
            ),
          })),
          uncolumned: movido.uncolumned.map((card) =>
            card.id === resultado.card.id ? resultado.card : card,
          ),
        };
      });
    });
  }

  // ---- Colunas ----
  const [novaColunaNome, setNovaColunaNome] = useState("");
  const [novaColunaKind, setNovaColunaKind] = useState<"COLUMN" | "SECTION">(
    "COLUMN",
  );

  function handleCriarColuna() {
    if (!novaColunaNome.trim()) return;
    setFeedback("");
    startTransition(async () => {
      const resultado = await createColumnAction(
        companyId,
        novaColunaNome.trim(),
        novaColunaKind,
        null,
      );
      if (!resultado.ok) {
        setFeedback(resultado.message);
        return;
      }
      setNovaColunaNome("");
      await refreshBoard();
      setFeedback("Coluna criada.");
    });
  }

  const columnHandlers: ColumnMenuHandlers = {
    onRenameColumn(column) {
      const nome = window.prompt("Novo nome da coluna:", column.name);
      if (!nome || !nome.trim()) return;
      startTransition(async () => {
        const resultado = await updateColumnAction(
          column.id,
          nome.trim(),
          column.hidden,
          column.wip_limit,
        );
        if (!resultado.ok) {
          setFeedback(resultado.message);
          return;
        }
        await refreshBoard();
      });
    },

    onArchiveColumn(column) {
      startTransition(async () => {
        const resultado = await updateColumnAction(
          column.id,
          column.name,
          !column.hidden,
          column.wip_limit,
        );
        if (!resultado.ok) {
          setFeedback(resultado.message);
          return;
        }
        await refreshBoard();
        setFeedback(column.hidden ? "Coluna reexibida." : "Coluna arquivada.");
      });
    },

    onDeleteColumn(column) {
      if (
        !window.confirm(
          `Excluir a coluna "${column.name}"? Os cards NÃO são apagados — eles ficam sem coluna até você movê-los.`,
        )
      ) {
        return;
      }
      startTransition(async () => {
        const resultado = await deleteColumnAction(column.id);
        if (!resultado.ok) {
          // 409 com card visível: a mensagem do backend diz quantos.
          setFeedback(resultado.message);
          return;
        }
        await refreshBoard();
        setFeedback("Coluna excluída.");
      });
    },

    onMoveColumn(column, direcao) {
      const visiveis = quadroVisivel.columns;
      const indice = visiveis.findIndex((c) => c.id === column.id);
      const destino = indice + direcao;
      if (indice < 0 || destino < 0 || destino >= visiveis.length) return;

      // Âncoras calculadas sobre a lista SEM a coluna movida — mandar a
      // própria coluna como âncora produziria 422 no servidor.
      const restantes = visiveis.filter((c) => c.id !== column.id);
      const prev = destino > 0 ? (restantes[destino - 1]?.id ?? null) : null;
      const next = restantes[destino]?.id ?? null;

      startTransition(async () => {
        const resultado = await moveColumnAction(column.id, prev, next);
        if (!resultado.ok) {
          setFeedback(resultado.message);
          return;
        }
        await refreshBoard();
      });
    },

    onAddCard(column) {
      setNewCardColumnId(column.id);
      setNewCardTitle("");
      setNewCardControlCode("");
      setNewCardCategoryId(categories[0]?.id ?? null);
    },
  };

  // ---- Ação em lote ----
  function runBulk(
    operation:
      | "hide"
      | "unhide"
      | "remove"
      | "set_category"
      | "set_column"
      | "restore_from_template",
    categoryId: number | null = null,
    columnId: number | null = null,
  ) {
    const ids = [...selectedCardIds];
    if (ids.length === 0) return;
    if (
      operation === "remove" &&
      !window.confirm(
        `Remover ${ids.length} card(s)? Histórico, checklist e conversa de cada um são apagados junto — ação irreversível.`,
      )
    ) {
      return;
    }

    setFeedback("");
    startTransition(async () => {
      const result = await bulkUpdateCardsAction(
        companyId,
        ids,
        operation,
        categoryId,
        columnId,
      );
      if (!result.ok) {
        setFeedback(result.message);
        return;
      }
      await refreshBoard();
      setFeedback(`${result.affected_count} card(s) atualizado(s).`);
    });
  }

  // ---- Aplicar template ----
  const [templateToApply, setTemplateToApply] = useState<number | "">("");

  function handleApplyTemplate() {
    if (templateToApply === "") return;
    setFeedback("");
    startTransition(async () => {
      const result = await applyTemplateToCompanyAction(
        companyId,
        Number(templateToApply),
      );
      if (!result.ok) {
        setFeedback(result.message);
        return;
      }
      await refreshBoard();
      setOutdatedFromLastApply(result.outdated_card_ids);
      // B-A24: sem `adopted_count` e `columns_created_count` visíveis,
      // aplicar um template numa empresa que já tem os cards mostraria
      // "0 criados" e o admin concluiria que nada aconteceu — quando na
      // verdade 25 colunas foram criadas.
      const partes = [
        `${result.created_count} card(s) criado(s)`,
        result.columns_created_count > 0
          ? `${result.columns_created_count} coluna(s) criada(s)`
          : null,
        result.adopted_count > 0
          ? `${result.adopted_count} card(s) existente(s) vinculado(s) ao template`
          : null,
        `${result.already_applied_count} já aplicado(s)`,
        result.outdated_card_ids.length > 0
          ? `${result.outdated_card_ids.length} divergente(s) do template (selecione e use "Restaurar do template")`
          : null,
      ].filter(Boolean);

      setFeedback(partes.join(" · "));
    });
  }

  // ---- Novo card (dentro de uma coluna) ----
  const [newCardColumnId, setNewCardColumnId] = useState<number | null>(null);
  const [newCardCategoryId, setNewCardCategoryId] = useState<number | null>(
    null,
  );
  const [newCardTitle, setNewCardTitle] = useState("");
  const [newCardControlCode, setNewCardControlCode] = useState("");

  function handleCreateCard() {
    if (newCardCategoryId === null || !newCardTitle.trim()) return;
    startTransition(async () => {
      const result = await createCardForCompanyAction(
        companyId,
        newCardTitle.trim(),
        newCardCategoryId,
        newCardControlCode.trim() || null,
        newCardColumnId,
        null,
      );
      if (!result.ok) {
        setFeedback(result.message);
        return;
      }
      setNewCardTitle("");
      setNewCardControlCode("");
      setNewCardColumnId(null);
      await refreshBoard();
    });
  }

  // ---- Nova categoria ----
  const [isNewCategoryOpen, setIsNewCategoryOpen] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState("");
  const [newCategoryColor, setNewCategoryColor] = useState("#788c5d");

  function handleCreateCategory() {
    if (!newCategoryName.trim()) return;
    startTransition(async () => {
      const result = await createCategoryAction(
        newCategoryName.trim(),
        newCategoryColor,
      );
      if (!result.ok) {
        setFeedback(result.message);
        return;
      }
      setCategories((prev) => [...prev, result.category]);
      setNewCategoryName("");
      setIsNewCategoryOpen(false);
    });
  }

  // ---- Mudar categoria / coluna em massa ----
  const [isChangeCategoryOpen, setIsChangeCategoryOpen] = useState(false);
  const [categoryToApply, setCategoryToApply] = useState<number | "">("");
  const [isChangeColumnOpen, setIsChangeColumnOpen] = useState(false);
  const [columnToApply, setColumnToApply] = useState<number | "">("");

  function confirmChangeCategory() {
    if (categoryToApply === "") return;
    setIsChangeCategoryOpen(false);
    runBulk("set_category", Number(categoryToApply));
    setCategoryToApply("");
  }

  function confirmChangeColumn() {
    if (columnToApply === "") return;
    setIsChangeColumnOpen(false);
    runBulk("set_column", null, Number(columnToApply));
    setColumnToApply("");
  }

  // ---- Detalhe do card selecionado ----
  function atualizarStatus(status: CardStatus) {
    if (!cardDetail) return;
    const cardId = cardDetail.id;
    startTransition(async () => {
      const result = await updateCardStatusAction(cardId, status);
      if (!result.ok) {
        setFeedback(result.message);
        return;
      }
      setCardDetail((prev) => (prev ? { ...prev, status: result.status } : prev));
      setBoard((prev) => mapCards(prev, cardId, (card) => ({
        ...card,
        status: result.status,
      })));
    });
  }

  function alternarChecklist(itemId: number) {
    startTransition(async () => {
      const result = await toggleChecklistItemAction(itemId);
      if (!result.ok) {
        setFeedback(result.message);
        return;
      }
      setCardDetail((prev) =>
        prev
          ? {
              ...prev,
              checklist: prev.checklist.map((item) =>
                item.id === itemId ? { ...item, done: result.done } : item,
              ),
            }
          : prev,
      );
    });
  }

  function alternarEtiqueta(labelId: number) {
    if (!cardDetail) return;
    const cardId = cardDetail.id;
    const atuais = cardDetail.labels.map((etiqueta) => etiqueta.id);
    const proximos = atuais.includes(labelId)
      ? atuais.filter((id) => id !== labelId)
      : [...atuais, labelId];

    startTransition(async () => {
      const result = await setCardLabelsAction(cardId, proximos);
      if (!result.ok) {
        setFeedback(result.message);
        return;
      }
      setCardDetail((prev) =>
        prev ? { ...prev, labels: result.labels } : prev,
      );
      setBoard((prev) =>
        mapCards(prev, cardId, (card) => ({ ...card, labels: result.labels })),
      );
    });
  }

  const selectionCount = selectedCardIds.size;

  const slotDeNovoCard =
    newCardColumnId === null ? null : (
      <div className="space-y-2">
        <input
          className="field text-sm"
          placeholder="Título do card"
          value={newCardTitle}
          onChange={(e) => setNewCardTitle(e.target.value)}
        />
        <input
          className="field text-sm"
          placeholder="Código do controle (opcional)"
          value={newCardControlCode}
          onChange={(e) => setNewCardControlCode(e.target.value)}
        />
        <select
          className="field text-sm"
          aria-label="Categoria do novo card"
          value={newCardCategoryId ?? ""}
          onChange={(e) =>
            setNewCardCategoryId(e.target.value ? Number(e.target.value) : null)
          }
        >
          <option value="">Escolha a categoria…</option>
          {categories.map((categoria) => (
            <option key={categoria.id} value={categoria.id}>
              {categoria.name}
            </option>
          ))}
        </select>
        <div className="flex gap-2">
          <button
            type="button"
            className="btn-primary text-xs"
            disabled={
              !newCardTitle.trim() || newCardCategoryId === null || isPending
            }
            onClick={handleCreateCard}
          >
            Criar
          </button>
          <button
            type="button"
            className="btn-secondary text-xs"
            onClick={() => setNewCardColumnId(null)}
          >
            Cancelar
          </button>
        </div>
      </div>
    );

  return (
    <main className="py-8 pb-28">
      <div className="container-page space-y-6">
        <section className="card">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-(--color-dark)">
                Quadro de {companyName}
              </h2>
              <p className="mt-1 text-sm text-zinc-600">
                {quadroOtimista.columns.length} coluna(s) · {totalVisivel}{" "}
                card(s) visível(is) · {totalOculto} oculto(s)
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <select
                className="field w-auto"
                aria-label="Template a aplicar"
                value={templateToApply}
                onChange={(e) =>
                  setTemplateToApply(
                    e.target.value ? Number(e.target.value) : "",
                  )
                }
              >
                <option value="">Aplicar template...</option>
                {templates.map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name} ({template.card_count} cards)
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="btn-primary"
                disabled={templateToApply === "" || isPending}
                onClick={handleApplyTemplate}
              >
                Aplicar
              </button>
            </div>
          </div>

          {feedback ? (
            <p
              role="status"
              className="mt-3 rounded-lg bg-zinc-50 p-2 text-sm text-zinc-700"
            >
              {feedback}
            </p>
          ) : null}
        </section>

        <section className="card space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <input
              type="text"
              placeholder="Buscar por título ou código..."
              aria-label="Buscar cards"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              className="w-full max-w-xs rounded-lg border border-zinc-300 px-3 py-2 text-sm"
            />

            <label className="flex items-center gap-2 text-sm text-zinc-700">
              <input
                type="checkbox"
                checked={showHidden}
                onChange={(e) => setShowHidden(e.target.checked)}
              />
              Mostrar cards e colunas arquivados
            </label>

            <div className="ml-auto flex flex-wrap items-center gap-2">
              <input
                className="field w-48 text-sm"
                placeholder="Nome da coluna nova"
                aria-label="Nome da coluna nova"
                value={novaColunaNome}
                onChange={(e) => setNovaColunaNome(e.target.value)}
              />
              <select
                className="field w-auto text-sm"
                aria-label="Tipo da coluna nova"
                value={novaColunaKind}
                onChange={(e) =>
                  setNovaColunaKind(e.target.value as "COLUMN" | "SECTION")
                }
              >
                <option value="COLUMN">Coluna</option>
                <option value="SECTION">Seção (separador)</option>
              </select>
              <button
                type="button"
                className="btn-secondary text-sm"
                disabled={!novaColunaNome.trim() || isPending}
                onClick={handleCriarColuna}
              >
                + Coluna
              </button>
            </div>
          </div>
        </section>

        <Board
          board={quadroVisivel}
          selectedCardId={cardSelecionadoId}
          onSelectCard={setCardSelecionadoId}
          selectedCardIds={selectedCardIds}
          onToggleCardSelection={toggleCardSelection}
          onToggleColumnSelection={toggleColumnSelection}
          collapsedColumns={collapsedColumns}
          onToggleColumnCollapse={toggleColumnCollapse}
          onMoveCard={handleMoveCard}
          columnHandlers={columnHandlers}
          outdatedCardIds={outdatedFromLastApply}
          addCardColumnId={newCardColumnId}
          addCardSlot={slotDeNovoCard}
        />

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-1">
            {isNewCategoryOpen ? (
              <div className="card space-y-2">
                <input
                  className="field text-sm"
                  placeholder="Nome da categoria"
                  aria-label="Nome da categoria"
                  value={newCategoryName}
                  onChange={(e) => setNewCategoryName(e.target.value)}
                />
                <input
                  type="color"
                  aria-label="Cor da categoria"
                  className="h-9 w-full rounded-lg border border-zinc-300"
                  value={newCategoryColor}
                  onChange={(e) => setNewCategoryColor(e.target.value)}
                />
                <div className="flex gap-2">
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={!newCategoryName.trim() || isPending}
                    onClick={handleCreateCategory}
                  >
                    Criar categoria
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setIsNewCategoryOpen(false)}
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            ) : (
              <button
                type="button"
                className="btn-secondary w-full"
                onClick={() => setIsNewCategoryOpen(true)}
              >
                + Nova categoria
              </button>
            )}
          </div>

          <div className="lg:col-span-2">
            <CardDetailPanel
              cardDetail={cardDetail}
              isLoading={isLoadingDetail}
              isPending={isPending}
              labels={labels}
              onChangeStatus={atualizarStatus}
              onToggleChecklistItem={alternarChecklist}
              onToggleLabel={alternarEtiqueta}
            />
          </div>
        </div>
      </div>

      {selectionCount > 0 ? (
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-(--color-neutral) bg-white/95 backdrop-blur">
          <div className="container-page flex flex-wrap items-center justify-between gap-3 py-3">
            <span className="text-sm font-medium text-(--color-dark)">
              {selectionCount} selecionado(s)
            </span>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-secondary"
                disabled={isPending}
                onClick={() => runBulk("hide")}
              >
                Ocultar
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={isPending}
                onClick={() => runBulk("unhide")}
              >
                Reexibir
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={isPending}
                onClick={() => setIsChangeColumnOpen(true)}
              >
                Mover para coluna
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={isPending}
                onClick={() => setIsChangeCategoryOpen(true)}
              >
                Mudar categoria
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={isPending}
                onClick={() => runBulk("restore_from_template")}
              >
                Restaurar do template
              </button>
              <button
                type="button"
                className="btn-danger-outline"
                disabled={isPending}
                onClick={() => runBulk("remove")}
              >
                Remover
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setSelectedCardIds(new Set())}
              >
                Limpar seleção
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {isChangeCategoryOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h3 className="text-base font-semibold">
              Mudar categoria de {selectionCount} card(s)
            </h3>
            <select
              className="field mt-4"
              aria-label="Categoria de destino"
              value={categoryToApply}
              onChange={(e) =>
                setCategoryToApply(e.target.value ? Number(e.target.value) : "")
              }
            >
              <option value="">Escolha a categoria...</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setIsChangeCategoryOpen(false)}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={categoryToApply === "" || isPending}
                onClick={confirmChangeCategory}
              >
                Aplicar
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {isChangeColumnOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h3 className="text-base font-semibold">
              Mover {selectionCount} card(s) para outra coluna
            </h3>
            <select
              className="field mt-4"
              aria-label="Coluna de destino"
              value={columnToApply}
              onChange={(e) =>
                setColumnToApply(e.target.value ? Number(e.target.value) : "")
              }
            >
              <option value="">Escolha a coluna...</option>
              {quadroOtimista.columns
                .filter((coluna) => coluna.kind === "COLUMN")
                .map((coluna) => (
                  <option key={coluna.id} value={coluna.id}>
                    {coluna.name}
                  </option>
                ))}
            </select>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setIsChangeColumnOpen(false)}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={columnToApply === "" || isPending}
                onClick={confirmChangeColumn}
              >
                Mover
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}

/** Aplica uma transformação a UM card, em qualquer coluna do quadro. */
function mapCards(
  board: BoardData,
  cardId: number,
  transformar: (card: BoardCardData) => BoardCardData,
): BoardData {
  const aplicar = (cards: BoardCardData[]) =>
    cards.map((card) => (card.id === cardId ? transformar(card) : card));

  return {
    ...board,
    columns: board.columns.map((coluna) => ({
      ...coluna,
      cards: aplicar(coluna.cards),
    })),
    uncolumned: aplicar(board.uncolumned),
  };
}
```

---

#### `…/dashboard/page.tsx`

##### 1. Ação Manual

Abra `frontend/app/private/admin/empresas/[id]/dashboard/page.tsx` e substitua o conteúdo
inteiro.

##### 2. Código Fonte Completo

```tsx
import { notFound } from "next/navigation";
import { getCompanyAdminDetailAction } from "@/app/private/admin/empresas/actions";
import { getCardDetailAction } from "@/app/private/admin/actions";
import {
  getBoardAction,
  listCategoriesAction,
  listLabelsAction,
  listTemplatesAction,
} from "./actions";
import { CompanyDashboardClient } from "./company-dashboard-client";

export default async function CompanyDashboardPage(
  props: PageProps<"/private/admin/empresas/[id]/dashboard">,
) {
  const { id } = await props.params;
  const companyId = Number(id);
  if (!Number.isFinite(companyId)) notFound();

  const [company, board, categories, labels, templates] = await Promise.all([
    getCompanyAdminDetailAction(companyId).catch(() => null),
    // `include_hidden=true`: o filtro de ocultos é do cliente (toggle
    // "Mostrar cards e colunas arquivados"), então o servidor entrega
    // tudo e a UI decide o que mostrar.
    getBoardAction(companyId, true),
    listCategoriesAction(),
    listLabelsAction(),
    listTemplatesAction(),
  ]);
  if (!company) notFound();

  const todosOsCards = [
    ...board.columns.flatMap((coluna) => coluna.cards),
    ...board.uncolumned,
  ];
  const firstVisibleCard = todosOsCards.find((card) => !card.hidden) ?? null;
  const initialCardDetail = firstVisibleCard
    ? await getCardDetailAction(firstVisibleCard.id)
    : null;

  return (
    <CompanyDashboardClient
      companyId={companyId}
      companyName={company.name}
      initialBoard={board}
      initialCardDetail={initialCardDetail}
      categories={categories}
      labels={labels}
      templates={templates}
    />
  );
}
```

---

#### `…/dashboard/_components/board.test.tsx`

##### 1. Ação Manual

Crie o arquivo `_components/board.test.tsx`.

> **jsdom não simula arrasto.** O que é testável aqui é (a) a função pura de reposicionamento
> (`moveCardInBoard`), que é o núcleo do otimismo, e (b) o comportamento de renderização:
> modo leitura, colunas arquivadas, busca e seleção em massa. O arrasto propriamente dito é
> verificado manualmente com leitor de tela (CA-14) e coberto funcionalmente pelo caminho do
> menu "Mover para…" (CA-15), que chama exatamente a mesma action.

##### 2. Código Fonte Completo

```tsx
// @vitest-environment jsdom

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  Board,
  allCards,
  ancorasPorIndice,
  moveCardInBoard,
  type MoveIntent,
} from "./board";
import type { Board as BoardData, BoardCard } from "../actions";

function card(id: number, titulo: string, colunaId: number | null): BoardCard {
  return {
    id,
    control_code: `5.${id}`,
    title: titulo,
    description: null,
    status: "EM_ANALISE",
    position: `a${id}`,
    column_id: colunaId,
    category_id: null,
    category_name: null,
    labels: [],
    hidden: false,
    origin_template_card_id: null,
    is_outdated: false,
  };
}

function quadro(): BoardData {
  return {
    dashboard_id: 1,
    company_id: 7,
    title: "Dashboard - Empresa",
    columns: [
      {
        id: 10,
        name: "A fazer",
        kind: "COLUMN",
        position: "a0",
        hidden: false,
        wip_limit: null,
        cards: [card(1, "Política de SI", 10), card(2, "Inventário", 10)],
        card_count: 2,
      },
      {
        id: 11,
        name: "ISO 27001:2022 >>",
        kind: "SECTION",
        position: "a1",
        hidden: false,
        wip_limit: null,
        cards: [],
        card_count: 0,
      },
      {
        id: 12,
        name: "Concluído",
        kind: "COLUMN",
        position: "a2",
        hidden: false,
        wip_limit: null,
        cards: [card(3, "Backup", 12)],
        card_count: 1,
      },
    ],
    uncolumned: [],
    labels: [],
  };
}

const propsBase = {
  selectedCardId: null,
  onSelectCard: vi.fn(),
};

describe("moveCardInBoard (núcleo do otimismo — CA-16)", () => {
  it("move o card para outra coluna, no fim", () => {
    const intent: MoveIntent = {
      cardId: 1,
      columnId: 12,
      prevCardId: 3,
      nextCardId: null,
    };

    const resultado = moveCardInBoard(quadro(), intent);

    expect(resultado.columns[0].cards.map((c) => c.id)).toEqual([2]);
    expect(resultado.columns[2].cards.map((c) => c.id)).toEqual([3, 1]);
    expect(resultado.columns[2].card_count).toBe(2);
  });

  it("move o card para o início da coluna de destino", () => {
    const resultado = moveCardInBoard(quadro(), {
      cardId: 1,
      columnId: 12,
      prevCardId: null,
      nextCardId: 3,
    });

    expect(resultado.columns[2].cards.map((c) => c.id)).toEqual([1, 3]);
  });

  it("reordena dentro da mesma coluna", () => {
    const resultado = moveCardInBoard(quadro(), {
      cardId: 1,
      columnId: 10,
      prevCardId: 2,
      nextCardId: null,
    });

    expect(resultado.columns[0].cards.map((c) => c.id)).toEqual([2, 1]);
  });

  it("não muta o quadro original", () => {
    const original = quadro();
    const antes = JSON.stringify(original);

    moveCardInBoard(original, {
      cardId: 1,
      columnId: 12,
      prevCardId: null,
      nextCardId: null,
    });

    expect(JSON.stringify(original)).toBe(antes);
  });

  it("devolve o mesmo quadro quando o card não existe", () => {
    const original = quadro();
    expect(
      moveCardInBoard(original, {
        cardId: 999,
        columnId: 12,
        prevCardId: null,
        nextCardId: null,
      }),
    ).toBe(original);
  });
});

describe("ancorasPorIndice", () => {
  it("no início devolve prev nulo", () => {
    const cards = quadro().columns[0].cards;
    expect(ancorasPorIndice(cards, 99, 0)).toEqual({
      prevCardId: null,
      nextCardId: 1,
    });
  });

  it("no fim devolve next nulo", () => {
    const cards = quadro().columns[0].cards;
    expect(ancorasPorIndice(cards, 99, 2)).toEqual({
      prevCardId: 2,
      nextCardId: null,
    });
  });

  it("ignora o próprio card ao calcular as âncoras", () => {
    const cards = quadro().columns[0].cards;
    expect(ancorasPorIndice(cards, 1, 0)).toEqual({
      prevCardId: null,
      nextCardId: 2,
    });
  });
});

describe("allCards", () => {
  it("inclui os cards sem coluna", () => {
    const comOrfao = { ...quadro(), uncolumned: [card(9, "Órfão", null)] };
    expect(allCards(comOrfao).map((c) => c.id)).toEqual([1, 2, 3, 9]);
  });
});

describe("<Board /> — renderização", () => {
  it("renderiza colunas e cards na ordem recebida (CA-05)", () => {
    render(<Board board={quadro()} {...propsBase} />);

    const colunaA = screen.getByTestId("column-10");
    expect(
      within(colunaA).getByText("Política de SI"),
    ).toBeInTheDocument();
    expect(within(colunaA).getByText(/2\s*card\(s\)/)).toBeInTheDocument();
  });

  it("readOnly esconde todo controle de edição (CA-17)", () => {
    render(<Board board={quadro()} readOnly {...propsBase} />);

    expect(screen.queryByText("Mover para…")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Arrastar o card/ }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("checkbox", { name: /Selecionar/ }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Ações da coluna/ }),
    ).not.toBeInTheDocument();
    // O conteúdo continua visível — é modo LEITURA, não tela vazia.
    expect(screen.getByText("Política de SI")).toBeInTheDocument();
  });

  it("mostra o balde de cards sem coluna", () => {
    const comOrfao = { ...quadro(), uncolumned: [card(9, "Órfão", null)] };
    render(<Board board={comOrfao} {...propsBase} />);

    expect(screen.getByText("Sem coluna")).toBeInTheDocument();
    expect(screen.getByText("Órfão")).toBeInTheDocument();
  });

  it("seleção em massa continua funcionando sobre o quadro (CA-21)", async () => {
    const usuario = userEvent.setup();
    const onToggleCardSelection = vi.fn();

    render(
      <Board
        board={quadro()}
        {...propsBase}
        selectedCardIds={new Set()}
        onToggleCardSelection={onToggleCardSelection}
      />,
    );

    await usuario.click(
      screen.getByRole("checkbox", { name: "Selecionar Política de SI" }),
    );

    expect(onToggleCardSelection).toHaveBeenCalledWith(1);
  });

  it("colapsar coluna esconde os cards dela (CA-21)", () => {
    render(
      <Board
        board={quadro()}
        {...propsBase}
        collapsedColumns={new Set([10])}
        onToggleColumnCollapse={vi.fn()}
      />,
    );

    expect(screen.queryByText("Política de SI")).not.toBeInTheDocument();
    expect(screen.getByText("Backup")).toBeInTheDocument();
  });

  it("quadro sem colunas mostra a mensagem de vazio", () => {
    render(
      <Board
        board={{ ...quadro(), columns: [] }}
        {...propsBase}
      />,
    );

    expect(
      screen.getByText("Este quadro ainda não tem colunas."),
    ).toBeInTheDocument();
  });
});
```

---

#### `…/dashboard/_components/board-column.test.tsx`

##### 1. Ação Manual

Crie o arquivo `_components/board-column.test.tsx`.

##### 2. Código Fonte Completo

```tsx
// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DndContext } from "@dnd-kit/core";

import { BoardColumn } from "./board-column";
import type {
  Board as BoardData,
  BoardCard as BoardCardData,
  BoardColumn as BoardColumnData,
} from "../actions";

function card(id: number, titulo: string): BoardCardData {
  return {
    id,
    control_code: null,
    title: titulo,
    description: null,
    status: "EM_ANALISE",
    position: `a${id}`,
    column_id: 10,
    category_id: null,
    category_name: null,
    labels: [],
    hidden: false,
    origin_template_card_id: 1,
    is_outdated: false,
  };
}

const colunaComum: BoardColumnData = {
  id: 10,
  name: "A fazer",
  kind: "COLUMN",
  position: "a0",
  hidden: false,
  wip_limit: null,
  cards: [card(1, "Política de SI")],
  card_count: 1,
};

const secao: BoardColumnData = {
  id: 11,
  name: "ISO 27001:2022 >>",
  kind: "SECTION",
  position: "a1",
  hidden: false,
  wip_limit: null,
  cards: [],
  card_count: 0,
};

const board: BoardData = {
  dashboard_id: 1,
  company_id: 7,
  title: "Dashboard",
  columns: [colunaComum, secao],
  uncolumned: [],
  labels: [],
};

const handlers = {
  onRenameColumn: vi.fn(),
  onArchiveColumn: vi.fn(),
  onDeleteColumn: vi.fn(),
  onMoveColumn: vi.fn(),
  onAddCard: vi.fn(),
};

function renderColuna(column: BoardColumnData, extras: Record<string, unknown> = {}) {
  return render(
    <DndContext>
      <BoardColumn
        column={column}
        board={board}
        readOnly={false}
        isFirst={false}
        isLast={false}
        collapsed={false}
        selectedCardId={null}
        onSelectCard={vi.fn()}
        outdatedCardIds={[]}
        columnHandlers={handlers}
        {...extras}
      />
    </DndContext>,
  );
}

describe("coluna do tipo SECTION (CA-18)", () => {
  it("renderiza como separador, sem contador de cards", () => {
    renderColuna(secao);

    const separador = screen.getByRole("separator", {
      name: "Seção ISO 27001:2022 >>",
    });
    expect(separador).toBeInTheDocument();
    expect(screen.queryByText(/card\(s\)/)).not.toBeInTheDocument();
  });

  it("não oferece área de soltar nem menu de coluna", () => {
    renderColuna(secao);

    expect(
      screen.queryByRole("button", { name: /Ações da coluna/ }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Adicionar card/ }),
    ).not.toBeInTheDocument();
  });
});

describe("coluna comum", () => {
  it("mostra nome e contador", () => {
    renderColuna(colunaComum);

    expect(screen.getByText(/A fazer/)).toBeInTheDocument();
    expect(screen.getByText(/1\s*card\(s\)/)).toBeInTheDocument();
  });

  it("mostra o limite de WIP e destaca quando estourado", () => {
    renderColuna({
      ...colunaComum,
      wip_limit: 1,
      cards: [card(1, "Política de SI"), card(2, "Inventário")],
      card_count: 2,
    });

    const contador = screen.getByText(/2\/1\s*card\(s\)/);
    expect(contador).toBeInTheDocument();
    expect(contador.className).toContain("text-red-600");
  });

  it("marca a coluna arquivada", () => {
    renderColuna({ ...colunaComum, hidden: true });

    expect(screen.getByText("arquivada")).toBeInTheDocument();
  });

  it("aciona o menu de renomear", async () => {
    const usuario = userEvent.setup();
    renderColuna(colunaComum);

    await usuario.click(
      screen.getByRole("button", { name: "Ações da coluna A fazer" }),
    );
    await usuario.click(screen.getByRole("button", { name: "Renomear" }));

    expect(handlers.onRenameColumn).toHaveBeenCalledWith(colunaComum);
  });

  it("desabilita a seta de mover na ponta do quadro", () => {
    renderColuna(colunaComum, { isFirst: true });

    expect(
      screen.getByRole("button", { name: "Mover coluna A fazer para a esquerda" }),
    ).toBeDisabled();
  });

  it("coluna vazia mostra a mensagem de vazio", () => {
    renderColuna({ ...colunaComum, cards: [], card_count: 0 });

    expect(screen.getByText("Nenhum card nesta coluna.")).toBeInTheDocument();
  });

  it("readOnly esconde o menu e o + Adicionar card (CA-17)", () => {
    render(
      <BoardColumn
        column={colunaComum}
        board={board}
        readOnly
        isFirst={false}
        isLast={false}
        collapsed={false}
        selectedCardId={null}
        onSelectCard={vi.fn()}
        outdatedCardIds={[]}
      />,
    );

    expect(
      screen.queryByRole("button", { name: /Ações da coluna/ }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Política de SI")).toBeInTheDocument();
  });
});
```

---

#### `…/dashboard/_components/move-card-menu.test.tsx`

##### 1. Ação Manual

Crie o arquivo `_components/move-card-menu.test.tsx`.

##### 2. Código Fonte Completo

```tsx
// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MoveCardMenu } from "./move-card-menu";
import type {
  Board as BoardData,
  BoardCard as BoardCardData,
} from "../actions";

function card(id: number, titulo: string, colunaId: number | null): BoardCardData {
  return {
    id,
    control_code: null,
    title: titulo,
    description: null,
    status: "EM_ANALISE",
    position: `a${id}`,
    column_id: colunaId,
    category_id: null,
    category_name: null,
    labels: [],
    hidden: false,
    origin_template_card_id: null,
    is_outdated: false,
  };
}

const board: BoardData = {
  dashboard_id: 1,
  company_id: 7,
  title: "Dashboard",
  columns: [
    {
      id: 10,
      name: "A fazer",
      kind: "COLUMN",
      position: "a0",
      hidden: false,
      wip_limit: null,
      cards: [card(1, "Política de SI", 10)],
      card_count: 1,
    },
    {
      id: 11,
      name: "ISO 27001:2022 >>",
      kind: "SECTION",
      position: "a1",
      hidden: false,
      wip_limit: null,
      cards: [],
      card_count: 0,
    },
    {
      id: 12,
      name: "Concluído",
      kind: "COLUMN",
      position: "a2",
      hidden: false,
      wip_limit: null,
      cards: [card(2, "Backup", 12), card(3, "Inventário", 12)],
      card_count: 2,
    },
  ],
  uncolumned: [],
  labels: [],
};

const onMoveCard = vi.fn();

beforeEach(() => {
  onMoveCard.mockReset();
});

describe("MoveCardMenu (CA-15 — mover sem arrasto nenhum)", () => {
  it("não oferece colunas do tipo SECTION como destino (CA-18)", async () => {
    const usuario = userEvent.setup();
    render(
      <MoveCardMenu
        card={card(1, "Política de SI", 10)}
        board={board}
        onMoveCard={onMoveCard}
      />,
    );
    await usuario.click(screen.getByText("Mover para…"));

    const seletor = screen.getByLabelText(
      "Coluna de destino para Política de SI",
    );
    const opcoes = Array.from(
      seletor.querySelectorAll("option"),
    ).map((o) => o.textContent);

    expect(opcoes).toContain("A fazer");
    expect(opcoes).toContain("Concluído");
    expect(opcoes).not.toContain("ISO 27001:2022 >>");
  });

  it("move para o início de outra coluna com as âncoras certas", async () => {
    const usuario = userEvent.setup();
    render(
      <MoveCardMenu
        card={card(1, "Política de SI", 10)}
        board={board}
        onMoveCard={onMoveCard}
      />,
    );
    await usuario.click(screen.getByText("Mover para…"));

    await usuario.selectOptions(
      screen.getByLabelText("Coluna de destino para Política de SI"),
      "12",
    );
    await usuario.selectOptions(
      screen.getByLabelText("Posição de destino para Política de SI"),
      "0",
    );
    await usuario.click(screen.getByRole("button", { name: "Mover" }));

    expect(onMoveCard).toHaveBeenCalledWith({
      cardId: 1,
      columnId: 12,
      prevCardId: null,
      nextCardId: 2,
    });
  });

  it("move para o fim de outra coluna", async () => {
    const usuario = userEvent.setup();
    render(
      <MoveCardMenu
        card={card(1, "Política de SI", 10)}
        board={board}
        onMoveCard={onMoveCard}
      />,
    );
    await usuario.click(screen.getByText("Mover para…"));

    await usuario.selectOptions(
      screen.getByLabelText("Coluna de destino para Política de SI"),
      "12",
    );
    await usuario.selectOptions(
      screen.getByLabelText("Posição de destino para Política de SI"),
      "2",
    );
    await usuario.click(screen.getByRole("button", { name: "Mover" }));

    expect(onMoveCard).toHaveBeenCalledWith({
      cardId: 1,
      columnId: 12,
      prevCardId: 3,
      nextCardId: null,
    });
  });

  it("reordena dentro da própria coluna sem se tomar como âncora", async () => {
    const usuario = userEvent.setup();
    render(
      <MoveCardMenu
        card={card(2, "Backup", 12)}
        board={board}
        onMoveCard={onMoveCard}
      />,
    );
    await usuario.click(screen.getByText("Mover para…"));

    await usuario.selectOptions(
      screen.getByLabelText("Posição de destino para Backup"),
      "1",
    );
    await usuario.click(screen.getByRole("button", { name: "Mover" }));

    expect(onMoveCard).toHaveBeenCalledWith({
      cardId: 2,
      columnId: 12,
      prevCardId: 3,
      nextCardId: null,
    });
  });

  it("o botão Mover fica desabilitado enquanto não houver coluna escolhida", async () => {
    const usuario = userEvent.setup();
    render(
      <MoveCardMenu
        card={card(9, "Órfão", null)}
        board={board}
        onMoveCard={onMoveCard}
      />,
    );
    await usuario.click(screen.getByText("Mover para…"));

    expect(screen.getByRole("button", { name: "Mover" })).toBeDisabled();
  });
});
```

---

#### `…/dashboard/actions.test.ts`

##### 1. Ação Manual

Acrescente ao **final** de
`frontend/app/private/admin/empresas/[id]/dashboard/actions.test.ts` o bloco abaixo, e
inclua as actions novas no `import` do topo do arquivo:

```typescript
import {
  applyTemplateToCompanyAction,
  bulkUpdateCardsAction,
  createCardForCompanyAction,
  createCategoryAction,
  createColumnAction,
  deleteColumnAction,
  getBoardAction,
  listCardsForCompanyAction,
  listCategoriesAction,
  listLabelsAction,
  listTemplatesAction,
  moveCardAction,
  moveColumnAction,
  setCardLabelsAction,
  updateCardAction,
  updateColumnAction,
} from "./actions";
```

##### 2. Código Fonte Completo (bloco a acrescentar ao final)

```typescript
describe("quadro (board)", () => {
  it("lê o quadro pela rota de board, com include_hidden e busca", async () => {
    backendMock.mockResolvedValue({ columns: [], uncolumned: [], labels: [] });

    await getBoardAction(4, true, "backup");

    expect(requireAdminMock).toHaveBeenCalled();
    expect(ultimaChamada()[0]).toBe(
      "/api/v1/dashboard/companies/4/board?include_hidden=true&search=backup",
    );
  });

  it("lista o vocabulário de etiquetas", async () => {
    backendMock.mockResolvedValue([]);

    await listLabelsAction();

    expect(ultimaChamada()[0]).toBe("/api/v1/admin/dashboard-labels");
  });
});

describe("colunas", () => {
  it("cria coluna pela rota da empresa", async () => {
    backendMock.mockResolvedValue({ id: 1, name: "Nova" });

    await createColumnAction(4, "Nova", "COLUMN", null);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/dashboard/companies/4/columns");
    expect(opcoes.method).toBe("POST");
    expect(opcoes.body).toMatchObject({
      name: "Nova",
      kind: "COLUMN",
      after_column_id: null,
    });
  });

  it("edita coluna com PATCH", async () => {
    backendMock.mockResolvedValue({ id: 1 });

    await updateColumnAction(1, "Renomeada", true, 5);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/dashboard/columns/1");
    expect(opcoes.method).toBe("PATCH");
    expect(opcoes.body).toMatchObject({
      name: "Renomeada",
      hidden: true,
      wip_limit: 5,
    });
  });

  it("move coluna mandando âncoras", async () => {
    backendMock.mockResolvedValue({ id: 1 });

    await moveColumnAction(1, 2, 3);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/dashboard/columns/1/move");
    expect(opcoes.body).toMatchObject({
      prev_column_id: 2,
      next_column_id: 3,
    });
  });

  it("devolve falha tratável quando o backend recusa a exclusão (409)", async () => {
    backendMock.mockRejectedValue(
      new Error("Coluna com 3 card(s) visível(is)."),
    );

    const resultado = await deleteColumnAction(1);

    expect(resultado.ok).toBe(false);
    if (!resultado.ok) {
      expect(resultado.message).toContain("card(s)");
    }
  });
});

describe("mover card", () => {
  it("manda ÂNCORAS, nunca a chave de ordenação", async () => {
    backendMock.mockResolvedValue({ id: 1, position: "a0V" });

    await moveCardAction(1, 12, 88, 91);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/dashboard/cards/1/move");
    expect(opcoes.method).toBe("PATCH");
    expect(opcoes.body).toEqual({
      column_id: 12,
      prev_card_id: 88,
      next_card_id: 91,
    });
    // O cliente nunca calcula `position` (§4.2 do PRD).
    expect(opcoes.body).not.toHaveProperty("position");
  });

  it("devolve falha tratável para o otimismo reverter (CA-16)", async () => {
    backendMock.mockRejectedValue(new Error("Coluna não encontrada"));

    const resultado = await moveCardAction(1, 999, null, null);

    expect(resultado.ok).toBe(false);
  });
});

describe("edição de card e etiquetas", () => {
  it("edita o texto do card sem tocar em status", async () => {
    backendMock.mockResolvedValue({ id: 1 });

    await updateCardAction(1, "Novo título", "Descrição", "5.1", 2);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/dashboard/cards/1");
    expect(opcoes.method).toBe("PATCH");
    expect(opcoes.body).not.toHaveProperty("status");
  });

  it("substitui o conjunto de etiquetas com PUT", async () => {
    backendMock.mockResolvedValue([]);

    await setCardLabelsAction(1, [2, 3]);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/dashboard/cards/1/labels");
    expect(opcoes.method).toBe("PUT");
    expect(opcoes.body).toMatchObject({ label_ids: [2, 3] });
  });
});

describe("edição em massa por coluna", () => {
  it("envia column_id em set_column", async () => {
    backendMock.mockResolvedValue({ affected_count: 3 });

    await bulkUpdateCardsAction(4, [1, 2, 3], "set_column", null, 12);

    const [, opcoes] = ultimaChamada();
    expect(opcoes.body).toMatchObject({
      operation: "set_column",
      column_id: 12,
    });
  });
});

describe("criação de card no quadro", () => {
  it("envia column_id e description", async () => {
    backendMock.mockResolvedValue({ id: 20 });

    await createCardForCompanyAction(4, "Card", 2, "5.1", 12, "Texto");

    const [, opcoes] = ultimaChamada();
    expect(opcoes.body).toMatchObject({
      column_id: 12,
      description: "Texto",
    });
  });
});
```

---

### Fase 8 — Quadro do cliente

> ⚠️ **Rota NOVA, não modificação de tela existente.** O PRD §5.4 listava
> `client-dashboard-client.tsx` como arquivo a alterar. Esse arquivo renderiza `AuditControl`
> vindo de `GET /api/v1/client/controls` — domínio de auditoria, não de dashboard. **O
> cliente hoje não tem nenhuma visão do quadro da própria empresa.** Entregar U6/U7 é criar
> a rota `/private/client/quadro`; `client-dashboard-client.tsx` fica **intocado**.
>
> **O backend não precisa de rota nova.** `GET /dashboard/companies/{id}/board` já usa
> `get_company_with_access`, que aceita `user` e `sub-user`, e `GET /api/v1/companies/me`
> (já existente, criada para a tela de mensagens do cliente) resolve o `company_id`.

---

#### `frontend/app/private/client/quadro/actions.ts`

##### 1. Ação Manual

Crie o diretório `frontend/app/private/client/quadro/` e, dentro dele, `actions.ts`.

```bash
mkdir -p frontend/app/private/client/quadro
```

##### 2. Código Fonte Completo

```typescript
"use server";

import { getAccessToken, requireClient } from "@/lib/session";
import { callBackend } from "@/lib/server-backend";
import type { Board } from "@/app/private/admin/empresas/[id]/dashboard/actions";
import type { DashboardCardDetail } from "@/app/private/admin/actions";

/**
 * Actions do quadro do CLIENTE — só leitura.
 *
 * Nenhuma action de escrita existe aqui de propósito. O quadro é leitura
 * para o cliente e escrita só para o auditor (PRD §4.4); o backend já
 * recusa qualquer escrita com 403, e não oferecer o caminho no frontend
 * é a segunda camada da mesma decisão — a barreira do frontend nunca
 * substitui a do backend, ela a duplica (F4).
 *
 * As três actions usam `requireClient()`, que redireciona um admin para
 * /private/admin. Um admin que queira ver este quadro usa a tela de
 * admin, que é a completa.
 */

export type MyCompany = {
  id: number;
  name: string;
};

/**
 * Empresa do usuário logado.
 * Backend: GET /api/v1/companies/me — já existia (foi criada para a tela
 * de mensagens do cliente), porque nenhum endpoint client-facing expõe
 * `company_id`: `GET /client/controls` devolve dados de auditoria, sem
 * referência nenhuma à empresa.
 */
export async function getMyCompanyAction(): Promise<MyCompany> {
  await requireClient();
  const token = await getAccessToken();
  return callBackend<MyCompany>("/api/v1/companies/me", {
    token: token ?? undefined,
  });
}

/**
 * Quadro da própria empresa, em modo leitura.
 * Backend: GET /api/v1/dashboard/companies/{id}/board.
 *
 * `include_hidden` é sempre `false`: card oculto e coluna arquivada são
 * decisão interna do auditor sobre o que ainda é trabalho em aberto —
 * mostrá-los ao cliente só produziria pergunta sobre algo que a
 * auditoria já tirou de cena.
 */
export async function getClientBoardAction(companyId: number): Promise<Board> {
  await requireClient();
  const token = await getAccessToken();
  return callBackend<Board>(
    `/api/v1/dashboard/companies/${companyId}/board?include_hidden=false&search=`,
    { token: token ?? undefined },
  );
}

/**
 * Detalhe de um card do próprio quadro.
 * Backend: GET /api/v1/dashboard/cards/{id}.
 *
 * Gêmea de `getCardDetailAction` de `admin/actions.ts`, com
 * `requireClient()` no lugar de `requireAdmin()`. O backend devolve
 * `checklist` e `history` VAZIOS para papel não-admin (B-A28) — não 403:
 * o card existe e o cliente tem direito de vê-lo, só não ao registro
 * interno do auditor sobre ele. `description` e `labels` vêm
 * preenchidos, porque são o que ele precisa para saber o que entregar
 * (U7).
 */
export async function getCardDetailAction(
  cardId: number,
): Promise<DashboardCardDetail> {
  await requireClient();
  const token = await getAccessToken();
  return callBackend<DashboardCardDetail>(`/api/v1/dashboard/cards/${cardId}`, {
    token: token ?? undefined,
  });
}
```

---

#### `frontend/app/private/client/quadro/page.tsx`

##### 1. Ação Manual

Crie o arquivo `page.tsx` no mesmo diretório.

##### 2. Código Fonte Completo

```tsx
import { requireClient } from "@/lib/session";
import {
  getCardDetailAction,
  getClientBoardAction,
  getMyCompanyAction,
} from "./actions";
import { ClientBoardClient } from "./client-board-client";

export default async function ClientBoardPage() {
  await requireClient();

  const company = await getMyCompanyAction();
  const board = await getClientBoardAction(company.id);

  const todosOsCards = [
    ...board.columns.flatMap((coluna) => coluna.cards),
    ...board.uncolumned,
  ];
  const primeiroCard = todosOsCards[0] ?? null;
  const initialCardDetail = primeiroCard
    ? await getCardDetailAction(primeiroCard.id)
    : null;

  return (
    <ClientBoardClient
      companyName={company.name}
      board={board}
      initialCardDetail={initialCardDetail}
    />
  );
}
```

---

#### `frontend/app/private/client/quadro/client-board-client.tsx`

##### 1. Ação Manual

Crie o arquivo `client-board-client.tsx`.

##### 2. Código Fonte Completo

```tsx
"use client";

import { useEffect, useRef, useState } from "react";

import { Board } from "@/app/private/admin/empresas/[id]/dashboard/_components/board";
import { CardDetailPanel } from "@/app/private/admin/empresas/[id]/dashboard/_components/card-detail-panel";
import type { Board as BoardData } from "@/app/private/admin/empresas/[id]/dashboard/actions";
import type { DashboardCardDetail } from "@/app/private/admin/actions";
import { getCardDetailAction } from "./actions";

type ClientBoardClientProps = {
  companyName: string;
  board: BoardData;
  initialCardDetail: DashboardCardDetail | null;
};

/**
 * Mesmo `<Board>` do admin, em modo leitura (CA-17).
 *
 * Reusar o componente — em vez de escrever uma versão "só de leitura" —
 * é o que garante que o cliente veja as colunas na MESMA ordem que o
 * auditor montou. Duas implementações divergiriam na primeira mudança de
 * ordenação, e a divergência apareceria numa reunião com o cliente, não
 * num teste.
 */
export function ClientBoardClient({
  companyName,
  board,
  initialCardDetail,
}: ClientBoardClientProps) {
  const [cardSelecionadoId, setCardSelecionadoId] = useState<number | null>(
    initialCardDetail?.id ?? null,
  );
  const [cardDetail, setCardDetail] = useState<DashboardCardDetail | null>(
    initialCardDetail,
  );
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const isFirstRender = useRef(true);

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    if (cardSelecionadoId === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setCardDetail(null);
      return;
    }

    let cancelado = false;
    setIsLoadingDetail(true);
    getCardDetailAction(cardSelecionadoId)
      .then((detail) => {
        if (!cancelado) setCardDetail(detail);
      })
      .catch(() => {
        if (!cancelado) setCardDetail(null);
      })
      .finally(() => {
        if (!cancelado) setIsLoadingDetail(false);
      });

    return () => {
      cancelado = true;
    };
  }, [cardSelecionadoId]);

  const totalDeCards =
    board.columns.reduce((soma, coluna) => soma + coluna.cards.length, 0) +
    board.uncolumned.length;

  return (
    <main className="min-h-screen bg-(--color-surface) py-8">
      <div className="container-page space-y-6">
        <header className="card">
          <h1 className="text-2xl font-semibold text-(--color-dark)">
            Quadro de {companyName}
          </h1>
          <p className="mt-1 text-sm text-zinc-600">
            {board.columns.length} coluna(s) · {totalDeCards} controle(s).
            Este é o andamento da due diligence como a equipe de auditoria o
            organizou. Clique num card para ler a descrição do controle e
            conversar sobre ele.
          </p>
        </header>

        {totalDeCards === 0 ? (
          <section className="card">
            <p className="text-sm text-zinc-600">
              A equipe de auditoria ainda não montou o quadro da sua empresa.
            </p>
          </section>
        ) : (
          <Board
            board={board}
            readOnly
            selectedCardId={cardSelecionadoId}
            onSelectCard={setCardSelecionadoId}
          />
        )}

        <CardDetailPanel
          cardDetail={cardDetail}
          isLoading={isLoadingDetail}
          isPending={false}
          readOnly
        />
      </div>
    </main>
  );
}
```

---

#### `frontend/app/private/client/quadro/loading.tsx`

##### 1. Ação Manual

Crie o arquivo `loading.tsx` (F2: toda rota tem `page` + `loading` + `error`).

##### 2. Código Fonte Completo

```tsx
export default function ClientBoardLoading() {
  return (
    <main className="min-h-screen bg-(--color-surface) py-8">
      <div className="container-page space-y-6">
        <div className="card animate-pulse">
          <div className="h-6 w-56 rounded bg-zinc-200" />
          <div className="mt-2 h-4 w-80 rounded bg-zinc-100" />
        </div>
        <div className="flex gap-4 overflow-hidden">
          <div className="card h-96 w-72 shrink-0 animate-pulse" />
          <div className="card h-96 w-72 shrink-0 animate-pulse" />
          <div className="card h-96 w-72 shrink-0 animate-pulse" />
        </div>
      </div>
    </main>
  );
}
```

---

#### `frontend/app/private/client/quadro/error.tsx`

##### 1. Ação Manual

Crie o arquivo `error.tsx`.

##### 2. Código Fonte Completo

```tsx
"use client";

import { useEffect } from "react";

export default function ClientBoardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[private/client/quadro] error ao carregar a página:", error);
  }, [error]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-(--color-surface) p-6">
      <div className="card max-w-md text-center">
        <h1 className="text-lg font-semibold text-(--color-dark)">
          Não foi possível carregar o quadro da sua empresa
        </h1>
        <p className="mt-2 text-sm text-zinc-600">
          {error.message || "Ocorreu um erro inesperado ao buscar os dados."}
        </p>
        <button
          type="button"
          className="btn-primary mt-4"
          onClick={() => reset()}
        >
          Tentar novamente
        </button>
      </div>
    </main>
  );
}
```

---

#### `frontend/app/private/client/quadro/actions.test.ts`

##### 1. Ação Manual

Crie o arquivo `actions.test.ts`.

##### 2. Código Fonte Completo

```typescript
import { beforeEach, describe, expect, it } from "vitest";
import { vi } from "vitest";

vi.mock("@/lib/server-backend");
vi.mock("@/lib/session");
vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));

import {
  backendMock,
  prepararSessao,
  requireClientMock,
  rotasChamadas,
  ultimaChamada,
} from "@/test/helpers/action-mocks";
import {
  getCardDetailAction,
  getClientBoardAction,
  getMyCompanyAction,
} from "./actions";

beforeEach(prepararSessao);

describe("quadro do cliente", () => {
  it("resolve a empresa pela rota /companies/me", async () => {
    backendMock.mockResolvedValue({ id: 7, name: "Empresa Teste" });

    const empresa = await getMyCompanyAction();

    expect(requireClientMock).toHaveBeenCalled();
    expect(ultimaChamada()[0]).toBe("/api/v1/companies/me");
    expect(empresa.id).toBe(7);
  });

  it("lê o quadro SEM cards ocultos", async () => {
    backendMock.mockResolvedValue({ columns: [], uncolumned: [], labels: [] });

    await getClientBoardAction(7);

    expect(ultimaChamada()[0]).toBe(
      "/api/v1/dashboard/companies/7/board?include_hidden=false&search=",
    );
  });

  it("usa requireClient, nunca requireAdmin", async () => {
    backendMock.mockResolvedValue({ columns: [], uncolumned: [], labels: [] });

    await getClientBoardAction(7);

    expect(requireClientMock).toHaveBeenCalled();
  });

  it("lê o detalhe do card pela mesma rota do admin", async () => {
    backendMock.mockResolvedValue({ id: 3, checklist: [], history: [] });

    await getCardDetailAction(3);

    expect(ultimaChamada()[0]).toBe("/api/v1/dashboard/cards/3");
  });

  it("não expõe nenhuma rota de escrita", async () => {
    backendMock.mockResolvedValue({ id: 7, name: "Empresa" });

    await getMyCompanyAction();

    for (const [, opcoes] of backendMock.mock.calls) {
      const metodo = (opcoes as { method?: string } | undefined)?.method;
      expect(metodo ?? "GET").toBe("GET");
    }
    expect(rotasChamadas().length).toBeGreaterThan(0);
  });
});
```

---

### Fase 9 — Tela de etiquetas

> Estrutura idêntica a `app/private/admin/templates/` (F2, F3): `page.tsx` +
> `actions.ts` + `*-client.tsx` + `loading.tsx` + `error.tsx` + `actions.test.ts`.

```bash
mkdir -p frontend/app/private/admin/dashboard-labels
```

---

#### `frontend/app/private/admin/dashboard-labels/actions.ts`

##### 2. Código Fonte Completo

```typescript
"use server";

import { requireAdmin, getAccessToken } from "@/lib/session";
import { callBackend } from "@/lib/server-backend";

export type DashboardLabelItem = {
  id: number;
  name: string;
  color: string;
  sort_order: number;
};

export type LabelMutationResult = { ok: true } | { ok: false; message: string };

/** Backend: GET /api/v1/admin/dashboard-labels. */
export async function listDashboardLabelsAction(): Promise<
  DashboardLabelItem[]
> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<DashboardLabelItem[]>("/api/v1/admin/dashboard-labels", {
    token: token ?? undefined,
  });
}

/** Backend: POST /api/v1/admin/dashboard-labels — 409 em nome duplicado. */
export async function createDashboardLabelAction(input: {
  name: string;
  color: string;
  sort_order: number;
}): Promise<LabelMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend("/api/v1/admin/dashboard-labels", {
      method: "POST",
      token: token ?? undefined,
      body: input,
    });
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao criar a etiqueta.";
    return { ok: false, message };
  }
}

/** Backend: PATCH /api/v1/admin/dashboard-labels/{id}. */
export async function updateDashboardLabelAction(
  labelId: number,
  input: { name: string; color: string; sort_order: number },
): Promise<LabelMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(`/api/v1/admin/dashboard-labels/${labelId}`, {
      method: "PATCH",
      token: token ?? undefined,
      body: input,
    });
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao editar a etiqueta.";
    return { ok: false, message };
  }
}

/**
 * Backend: DELETE /api/v1/admin/dashboard-labels/{id}.
 *
 * Devolve 409 (e não exclui) se a etiqueta estiver aplicada a algum
 * card — mesma regra de `CategoryInUseError`. A mensagem do backend traz
 * o número de cards, e é ela que a UI exibe: "em uso por 63 card(s)"
 * diz ao admin exatamente o que fazer antes de tentar de novo.
 */
export async function deleteDashboardLabelAction(
  labelId: number,
): Promise<LabelMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(`/api/v1/admin/dashboard-labels/${labelId}`, {
      method: "DELETE",
      token: token ?? undefined,
    });
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao excluir a etiqueta.";
    return { ok: false, message };
  }
}
```

---

#### `frontend/app/private/admin/dashboard-labels/page.tsx`

##### 2. Código Fonte Completo

```tsx
import { listDashboardLabelsAction } from "./actions";
import { DashboardLabelsClient } from "./dashboard-labels-client";

export default async function AdminDashboardLabelsPage() {
  const labels = await listDashboardLabelsAction();

  return <DashboardLabelsClient initialLabels={labels} />;
}
```

---

#### `frontend/app/private/admin/dashboard-labels/dashboard-labels-client.tsx`

##### 2. Código Fonte Completo

```tsx
"use client";

import { useState, useTransition } from "react";

import {
  labelChipClass,
  labelChipStyle,
  sortLabels,
  TRELLO_COLOR_MAP,
} from "@/lib/board-labels";
import {
  createDashboardLabelAction,
  deleteDashboardLabelAction,
  listDashboardLabelsAction,
  updateDashboardLabelAction,
  type DashboardLabelItem,
} from "./actions";

type DashboardLabelsClientProps = {
  initialLabels: DashboardLabelItem[];
};

const FORM_VAZIO = { name: "", color: "#788c5d", sort_order: 0 };

export function DashboardLabelsClient({
  initialLabels,
}: DashboardLabelsClientProps) {
  const [labels, setLabels] = useState<DashboardLabelItem[]>(initialLabels);
  const [form, setForm] = useState(FORM_VAZIO);
  const [editandoId, setEditandoId] = useState<number | null>(null);
  const [feedback, setFeedback] = useState("");
  const [isPending, startTransition] = useTransition();

  async function recarregar() {
    setLabels(await listDashboardLabelsAction());
  }

  function salvar() {
    if (!form.name.trim()) {
      setFeedback("Informe o nome da etiqueta.");
      return;
    }
    setFeedback("");
    startTransition(async () => {
      const entrada = {
        name: form.name.trim(),
        color: form.color,
        sort_order: form.sort_order,
      };
      const resultado =
        editandoId === null
          ? await createDashboardLabelAction(entrada)
          : await updateDashboardLabelAction(editandoId, entrada);

      if (!resultado.ok) {
        setFeedback(resultado.message);
        return;
      }
      setForm(FORM_VAZIO);
      setEditandoId(null);
      await recarregar();
      setFeedback("Etiqueta salva.");
    });
  }

  function editar(label: DashboardLabelItem) {
    setEditandoId(label.id);
    setForm({
      name: label.name,
      color: label.color,
      sort_order: label.sort_order,
    });
    setFeedback("");
  }

  function excluir(label: DashboardLabelItem) {
    if (!window.confirm(`Excluir a etiqueta "${label.name}"?`)) return;
    startTransition(async () => {
      const resultado = await deleteDashboardLabelAction(label.id);
      if (!resultado.ok) {
        // 409 com a contagem de cards em uso — a mensagem vem do backend.
        setFeedback(resultado.message);
        return;
      }
      await recarregar();
      setFeedback("Etiqueta excluída.");
    });
  }

  return (
    <main className="min-h-screen bg-(--color-surface) py-8">
      <div className="container-page space-y-6">
        <header className="card">
          <h1 className="text-2xl font-semibold text-(--color-dark)">
            Etiquetas de card
          </h1>
          <p className="mt-1 text-sm text-zinc-600">
            Vocabulário global de <strong>criticidade</strong>, aplicável aos
            cards de qualquer empresa. Etiqueta não declara conformidade — quem
            responde &quot;está conforme?&quot; é o <em>status</em> do card, e
            só a equipe de auditoria pode alterá-lo.
          </p>
          {feedback ? (
            <p
              role="status"
              className="mt-3 rounded-lg bg-zinc-50 p-2 text-sm text-zinc-700"
            >
              {feedback}
            </p>
          ) : null}
        </header>

        <div className="grid gap-6 lg:grid-cols-3">
          <section className="card space-y-3 lg:col-span-1">
            <h2 className="text-base font-semibold">
              {editandoId === null ? "Nova etiqueta" : "Editar etiqueta"}
            </h2>

            <label className="block text-sm text-zinc-700">
              Nome
              <input
                className="field mt-1"
                aria-label="Nome da etiqueta"
                value={form.name}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, name: e.target.value }))
                }
              />
            </label>

            <label className="block text-sm text-zinc-700">
              Cor
              <input
                type="color"
                aria-label="Cor da etiqueta"
                className="mt-1 h-9 w-full rounded-lg border border-zinc-300"
                value={form.color}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, color: e.target.value }))
                }
              />
            </label>

            <div className="flex flex-wrap gap-1">
              {Object.entries(TRELLO_COLOR_MAP).map(([nome, hex]) => (
                <button
                  key={nome}
                  type="button"
                  title={nome}
                  aria-label={`Usar a cor ${nome}`}
                  className="h-6 w-6 rounded border border-zinc-300"
                  style={{ backgroundColor: hex }}
                  onClick={() => setForm((prev) => ({ ...prev, color: hex }))}
                />
              ))}
            </div>

            <label className="block text-sm text-zinc-700">
              Ordem
              <input
                type="number"
                className="field mt-1"
                aria-label="Ordem da etiqueta"
                value={form.sort_order}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    sort_order: Number(e.target.value) || 0,
                  }))
                }
              />
            </label>

            <div className="flex gap-2">
              <button
                type="button"
                className="btn-primary"
                disabled={!form.name.trim() || isPending}
                onClick={salvar}
              >
                {editandoId === null ? "Criar etiqueta" : "Salvar"}
              </button>
              {editandoId !== null ? (
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setEditandoId(null);
                    setForm(FORM_VAZIO);
                  }}
                >
                  Cancelar
                </button>
              ) : null}
            </div>
          </section>

          <section className="card lg:col-span-2">
            <h2 className="text-base font-semibold">
              Etiquetas cadastradas ({labels.length})
            </h2>

            {labels.length === 0 ? (
              <p className="mt-3 text-sm text-zinc-600">
                Nenhuma etiqueta cadastrada ainda.
              </p>
            ) : (
              <ul className="mt-3 divide-y divide-(--color-neutral)">
                {sortLabels(labels).map((label) => (
                  <li
                    key={label.id}
                    className="flex flex-wrap items-center justify-between gap-3 py-3"
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className={labelChipClass(label.color)}
                        style={labelChipStyle(label.color)}
                      >
                        {label.name}
                      </span>
                      <span className="text-xs text-zinc-500">
                        ordem {label.sort_order} · {label.color}
                      </span>
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => editar(label)}
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        className="btn-danger-outline"
                        disabled={isPending}
                        onClick={() => excluir(label)}
                      >
                        Excluir
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
```

---

#### `frontend/app/private/admin/dashboard-labels/loading.tsx`

##### 2. Código Fonte Completo

```tsx
export default function DashboardLabelsLoading() {
  return (
    <main className="min-h-screen bg-(--color-surface) py-8">
      <div className="container-page space-y-6">
        <div className="card animate-pulse">
          <div className="h-6 w-48 rounded bg-zinc-200" />
          <div className="mt-2 h-4 w-72 rounded bg-zinc-100" />
        </div>
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="card h-80 animate-pulse lg:col-span-1" />
          <div className="card h-80 animate-pulse lg:col-span-2" />
        </div>
      </div>
    </main>
  );
}
```

---

#### `frontend/app/private/admin/dashboard-labels/error.tsx`

##### 2. Código Fonte Completo

```tsx
"use client";

import { useEffect } from "react";

export default function DashboardLabelsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(
      "[private/admin/dashboard-labels] error ao carregar a página:",
      error,
    );
  }, [error]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-(--color-surface) p-6">
      <div className="card max-w-md text-center">
        <h1 className="text-lg font-semibold text-(--color-dark)">
          Não foi possível carregar as etiquetas
        </h1>
        <p className="mt-2 text-sm text-zinc-600">
          {error.message || "Ocorreu um erro inesperado ao buscar os dados."}
        </p>
        <button
          type="button"
          className="btn-primary mt-4"
          onClick={() => reset()}
        >
          Tentar novamente
        </button>
      </div>
    </main>
  );
}
```

---

#### `frontend/app/private/admin/dashboard-labels/actions.test.ts`

##### 2. Código Fonte Completo

```typescript
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-backend");
vi.mock("@/lib/session");
vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));

import {
  backendMock,
  prepararSessao,
  requireAdminMock,
  ultimaChamada,
} from "@/test/helpers/action-mocks";
import {
  createDashboardLabelAction,
  deleteDashboardLabelAction,
  listDashboardLabelsAction,
  updateDashboardLabelAction,
} from "./actions";

beforeEach(prepararSessao);

describe("CRUD de etiquetas", () => {
  it("lista pela rota de dashboard-labels", async () => {
    backendMock.mockResolvedValue([]);

    await listDashboardLabelsAction();

    expect(requireAdminMock).toHaveBeenCalled();
    expect(ultimaChamada()[0]).toBe("/api/v1/admin/dashboard-labels");
  });

  it("cria com POST", async () => {
    backendMock.mockResolvedValue({ id: 1 });

    const resultado = await createDashboardLabelAction({
      name: "Item Critico",
      color: "#96311D",
      sort_order: 0,
    });

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/dashboard-labels");
    expect(opcoes.method).toBe("POST");
    expect(resultado.ok).toBe(true);
  });

  it("edita com PATCH", async () => {
    backendMock.mockResolvedValue({ id: 1 });

    await updateDashboardLabelAction(1, {
      name: "Crítico",
      color: "#000000",
      sort_order: 2,
    });

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/dashboard-labels/1");
    expect(opcoes.method).toBe("PATCH");
  });

  it("exclui com DELETE", async () => {
    backendMock.mockResolvedValue(null);

    await deleteDashboardLabelAction(1);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/dashboard-labels/1");
    expect(opcoes.method).toBe("DELETE");
  });

  it("devolve a mensagem do backend quando a etiqueta está em uso (409)", async () => {
    backendMock.mockRejectedValue(new Error("Etiqueta em uso por 63 card(s)"));

    const resultado = await deleteDashboardLabelAction(1);

    expect(resultado.ok).toBe(false);
    if (!resultado.ok) {
      expect(resultado.message).toContain("63 card(s)");
    }
  });

  it("devolve falha tratável em nome duplicado (409)", async () => {
    backendMock.mockRejectedValue(
      new Error("Já existe uma etiqueta com esse nome"),
    );

    const resultado = await createDashboardLabelAction({
      name: "Item Critico",
      color: "#96311D",
      sort_order: 0,
    });

    expect(resultado.ok).toBe(false);
  });
});
```

---

### Fase 10 — Colunas de template

---

#### `frontend/app/private/admin/templates/actions.ts`

##### 1. Ação Manual

Abra `frontend/app/private/admin/templates/actions.ts` e substitua o conteúdo inteiro. As
adições são: `template_column_id`/`position` em `TemplateCard`, `columns` em
`TemplateDetail` e quatro actions de coluna de template.

##### 2. Código Fonte Completo

```typescript
"use server";

import { requireAdmin, getAccessToken } from "@/lib/session";
import { callBackend } from "@/lib/server-backend";

export type TemplateListItem = {
  id: number;
  name: string;
  description: string | null;
  is_default: boolean;
  card_count: number;
};

export type TemplateColumnKind = "COLUMN" | "SECTION";

export type TemplateColumn = {
  id: number;
  name: string;
  kind: TemplateColumnKind;
  position: string;
  card_count: number;
};

export type TemplateCard = {
  id: number;
  title: string;
  description: string | null;
  category_id: number | null;
  category_name: string | null;
  template_column_id: number | null;
  position: string;
  sort_order: number;
};

export type TemplateDetail = TemplateListItem & {
  cards: TemplateCard[];
  columns: TemplateColumn[];
};

export type TemplateCategory = {
  id: number;
  name: string;
  color: string;
  sort_order: number;
};

/** Backend: GET /api/v1/admin/templates. */
export async function listTemplatesAction(): Promise<TemplateListItem[]> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<TemplateListItem[]>("/api/v1/admin/templates", {
    token: token ?? undefined,
  });
}

/** Backend: GET /api/v1/admin/templates/{id}. */
export async function getTemplateDetailAction(
  templateId: number,
): Promise<TemplateDetail> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<TemplateDetail>(`/api/v1/admin/templates/${templateId}`, {
    token: token ?? undefined,
  });
}

/** Backend: GET /api/v1/admin/dashboard-categories. */
export async function listTemplateCategoriesAction(): Promise<
  TemplateCategory[]
> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<TemplateCategory[]>("/api/v1/admin/dashboard-categories", {
    token: token ?? undefined,
  });
}

export type TemplateMutationResult =
  | { ok: true }
  | { ok: false; message: string };

/** Backend: POST /api/v1/admin/templates. */
export async function createTemplateAction(input: {
  name: string;
  description: string | null;
  is_default: boolean;
}): Promise<TemplateMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend("/api/v1/admin/templates", {
      method: "POST",
      token: token ?? undefined,
      body: input,
    });
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao criar o template.";
    return { ok: false, message };
  }
}

/** Backend: PATCH /api/v1/admin/templates/{id}. */
export async function updateTemplateAction(
  templateId: number,
  input: { name: string; description: string | null; is_default: boolean },
): Promise<TemplateMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(`/api/v1/admin/templates/${templateId}`, {
      method: "PATCH",
      token: token ?? undefined,
      body: input,
    });
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao editar o template.";
    return { ok: false, message };
  }
}

/** Backend: DELETE /api/v1/admin/templates/{id}. */
export async function deleteTemplateAction(
  templateId: number,
): Promise<TemplateMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(`/api/v1/admin/templates/${templateId}`, {
      method: "DELETE",
      token: token ?? undefined,
    });
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao excluir o template.";
    return { ok: false, message };
  }
}

// -------------------------------------------------- Colunas de template

/** Backend: POST /api/v1/admin/templates/{id}/columns. */
export async function createTemplateColumnAction(
  templateId: number,
  input: { name: string; kind: TemplateColumnKind },
): Promise<TemplateMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(`/api/v1/admin/templates/${templateId}/columns`, {
      method: "POST",
      token: token ?? undefined,
      body: input,
    });
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao criar a coluna.";
    return { ok: false, message };
  }
}

/** Backend: PATCH /api/v1/admin/templates/{id}/columns/{colId}. */
export async function updateTemplateColumnAction(
  templateId: number,
  columnId: number,
  input: { name: string; kind: TemplateColumnKind },
): Promise<TemplateMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(
      `/api/v1/admin/templates/${templateId}/columns/${columnId}`,
      { method: "PATCH", token: token ?? undefined, body: input },
    );
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao editar a coluna.";
    return { ok: false, message };
  }
}

/**
 * Backend: PATCH /api/v1/admin/templates/{id}/columns/{colId}/move.
 *
 * Manda ÂNCORAS (`prev_column_id`/`next_column_id`), nunca a chave de
 * ordenação — mesma regra do quadro (§4.2 do PRD): quem calcula a
 * `position` é o servidor, dentro da transação.
 */
export async function moveTemplateColumnAction(
  templateId: number,
  columnId: number,
  prevColumnId: number | null,
  nextColumnId: number | null,
): Promise<TemplateMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(
      `/api/v1/admin/templates/${templateId}/columns/${columnId}/move`,
      {
        method: "PATCH",
        token: token ?? undefined,
        body: { prev_column_id: prevColumnId, next_column_id: nextColumnId },
      },
    );
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao mover a coluna.";
    return { ok: false, message };
  }
}

/** Backend: DELETE /api/v1/admin/templates/{id}/columns/{colId} — 409 se em uso. */
export async function deleteTemplateColumnAction(
  templateId: number,
  columnId: number,
): Promise<TemplateMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(
      `/api/v1/admin/templates/${templateId}/columns/${columnId}`,
      { method: "DELETE", token: token ?? undefined },
    );
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao excluir a coluna.";
    return { ok: false, message };
  }
}

// ---------------------------------------------------- Cards de template

/** Backend: POST /api/v1/admin/templates/{id}/cards. */
export async function createTemplateCardAction(
  templateId: number,
  input: {
    title: string;
    description: string | null;
    category_id: number | null;
    template_column_id: number | null;
    sort_order: number;
  },
): Promise<TemplateMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(`/api/v1/admin/templates/${templateId}/cards`, {
      method: "POST",
      token: token ?? undefined,
      body: input,
    });
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao criar o card.";
    return { ok: false, message };
  }
}

/** Backend: PATCH /api/v1/admin/templates/template-cards/{id}. */
export async function updateTemplateCardAction(
  templateCardId: number,
  input: {
    title: string;
    description: string | null;
    category_id: number | null;
    template_column_id: number | null;
    sort_order: number;
  },
): Promise<TemplateMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(
      `/api/v1/admin/templates/template-cards/${templateCardId}`,
      { method: "PATCH", token: token ?? undefined, body: input },
    );
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao editar o card.";
    return { ok: false, message };
  }
}

/** Backend: DELETE /api/v1/admin/templates/template-cards/{id}. */
export async function deleteTemplateCardAction(
  templateCardId: number,
): Promise<TemplateMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(
      `/api/v1/admin/templates/template-cards/${templateCardId}`,
      { method: "DELETE", token: token ?? undefined },
    );
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao excluir o card.";
    return { ok: false, message };
  }
}
```

---

#### `frontend/app/private/admin/templates/templates-client.tsx`

##### 1. Ação Manual

Abra `frontend/app/private/admin/templates/templates-client.tsx` e substitua o conteúdo
inteiro. As adições são: `templateColumnId` em `CardFormState`, um seletor de coluna no
formulário de card, a coluna de origem exibida na lista de cards, e uma seção nova de
gestão de colunas do template.

##### 2. Código Fonte Completo

```tsx
"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import {
  createTemplateAction,
  createTemplateCardAction,
  createTemplateColumnAction,
  deleteTemplateAction,
  deleteTemplateCardAction,
  deleteTemplateColumnAction,
  getTemplateDetailAction,
  listTemplatesAction,
  moveTemplateColumnAction,
  TemplateCategory,
  TemplateColumn,
  TemplateColumnKind,
  TemplateDetail,
  TemplateListItem,
  updateTemplateAction,
  updateTemplateCardAction,
  updateTemplateColumnAction,
} from "./actions";

type TemplatesClientProps = {
  initialTemplates: TemplateListItem[];
  initialSelectedTemplateId: number | null;
  initialDetail: TemplateDetail | null;
  categories: TemplateCategory[];
};

type CardFormState = {
  title: string;
  description: string;
  categoryId: number | "";
  templateColumnId: number | "";
  sortOrder: number;
};

const EMPTY_CARD_FORM: CardFormState = {
  title: "",
  description: "",
  categoryId: "",
  templateColumnId: "",
  sortOrder: 0,
};

export function TemplatesClient({
  initialTemplates,
  initialSelectedTemplateId,
  initialDetail,
  categories,
}: TemplatesClientProps) {
  const [templates, setTemplates] =
    useState<TemplateListItem[]>(initialTemplates);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(
    initialSelectedTemplateId,
  );
  const [detail, setDetail] = useState<TemplateDetail | null>(initialDetail);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isPending, startTransition] = useTransition();
  const isFirstRender = useRef(true);

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    if (selectedTemplateId === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDetail(null);
      return;
    }

    let cancelado = false;
    setIsLoadingDetail(true);
    getTemplateDetailAction(selectedTemplateId)
      .then((data) => {
        if (!cancelado) setDetail(data);
      })
      .catch(() => {
        if (!cancelado) setDetail(null);
      })
      .finally(() => {
        if (!cancelado) setIsLoadingDetail(false);
      });

    return () => {
      cancelado = true;
    };
  }, [selectedTemplateId]);

  async function refreshAll(keepTemplateId: number | null) {
    const [freshTemplates, freshDetail] = await Promise.all([
      listTemplatesAction(),
      keepTemplateId
        ? getTemplateDetailAction(keepTemplateId).catch(() => null)
        : Promise.resolve(null),
    ]);
    setTemplates(freshTemplates);
    setSelectedTemplateId(
      freshDetail ? keepTemplateId : (freshTemplates[0]?.id ?? null),
    );
    setDetail(freshDetail);
  }

  // ---- Novo template ----
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newIsDefault, setNewIsDefault] = useState(false);
  const [createMsg, setCreateMsg] = useState("");

  function handleCreateTemplate() {
    if (!newName.trim()) {
      setCreateMsg("Informe o nome do template.");
      return;
    }
    setCreateMsg("");
    startTransition(async () => {
      const result = await createTemplateAction({
        name: newName.trim(),
        description: newDescription.trim() || null,
        is_default: newIsDefault,
      });
      if (!result.ok) {
        setCreateMsg(result.message);
        return;
      }
      setIsCreateOpen(false);
      setNewName("");
      setNewDescription("");
      setNewIsDefault(false);
      await refreshAll(selectedTemplateId);
    });
  }

  // ---- Edição do template selecionado ----
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editIsDefault, setEditIsDefault] = useState(false);
  const [editMsg, setEditMsg] = useState("");
  const [isEditOpen, setIsEditOpen] = useState(false);

  function openEdit() {
    if (!detail) return;
    setEditName(detail.name);
    setEditDescription(detail.description ?? "");
    setEditIsDefault(detail.is_default);
    setEditMsg("");
    setIsEditOpen(true);
  }

  function handleUpdateTemplate() {
    if (!detail) return;
    if (!editName.trim()) {
      setEditMsg("Informe o nome do template.");
      return;
    }
    startTransition(async () => {
      const result = await updateTemplateAction(detail.id, {
        name: editName.trim(),
        description: editDescription.trim() || null,
        is_default: editIsDefault,
      });
      if (!result.ok) {
        setEditMsg(result.message);
        return;
      }
      setIsEditOpen(false);
      await refreshAll(detail.id);
    });
  }

  function handleDeleteTemplate() {
    if (!detail) return;
    if (
      !window.confirm(
        `Excluir o template "${detail.name}"? Os cards já criados nas empresas a partir dele NÃO são removidos.`,
      )
    ) {
      return;
    }
    startTransition(async () => {
      const result = await deleteTemplateAction(detail.id);
      if (!result.ok) {
        window.alert(result.message);
        return;
      }
      await refreshAll(null);
    });
  }

  // ---- Colunas do template ----
  const [columnMsg, setColumnMsg] = useState("");
  const [newColumnName, setNewColumnName] = useState("");
  const [newColumnKind, setNewColumnKind] =
    useState<TemplateColumnKind>("COLUMN");

  function handleCreateColumn() {
    if (!detail || !newColumnName.trim()) return;
    setColumnMsg("");
    startTransition(async () => {
      const result = await createTemplateColumnAction(detail.id, {
        name: newColumnName.trim(),
        kind: newColumnKind,
      });
      if (!result.ok) {
        setColumnMsg(result.message);
        return;
      }
      setNewColumnName("");
      setNewColumnKind("COLUMN");
      await refreshAll(detail.id);
    });
  }

  function handleRenameColumn(column: TemplateColumn) {
    if (!detail) return;
    const nome = window.prompt("Novo nome da coluna:", column.name);
    if (!nome || !nome.trim()) return;
    setColumnMsg("");
    startTransition(async () => {
      const result = await updateTemplateColumnAction(detail.id, column.id, {
        name: nome.trim(),
        kind: column.kind,
      });
      if (!result.ok) {
        setColumnMsg(result.message);
        return;
      }
      await refreshAll(detail.id);
    });
  }

  function handleMoveColumn(column: TemplateColumn, direcao: -1 | 1) {
    if (!detail) return;
    const colunas = detail.columns;
    const indice = colunas.findIndex((c) => c.id === column.id);
    const destino = indice + direcao;
    if (indice < 0 || destino < 0 || destino >= colunas.length) return;

    // Âncoras calculadas sobre a lista SEM a coluna movida — mandar a
    // própria coluna como âncora produziria 422 no servidor.
    const restantes = colunas.filter((c) => c.id !== column.id);
    const prev = destino > 0 ? (restantes[destino - 1]?.id ?? null) : null;
    const next = restantes[destino]?.id ?? null;

    setColumnMsg("");
    startTransition(async () => {
      const result = await moveTemplateColumnAction(
        detail.id,
        column.id,
        prev,
        next,
      );
      if (!result.ok) {
        setColumnMsg(result.message);
        return;
      }
      await refreshAll(detail.id);
    });
  }

  function handleDeleteColumn(column: TemplateColumn) {
    if (!detail) return;
    if (!window.confirm(`Excluir a coluna "${column.name}" do template?`)) {
      return;
    }
    setColumnMsg("");
    startTransition(async () => {
      const result = await deleteTemplateColumnAction(detail.id, column.id);
      if (!result.ok) {
        // 409 quando há card de template vinculado — a mensagem do
        // backend diz quantos.
        setColumnMsg(result.message);
        return;
      }
      await refreshAll(detail.id);
    });
  }

  // ---- Cards do template ----
  const [cardForm, setCardForm] = useState<CardFormState>(EMPTY_CARD_FORM);
  const [editingCardId, setEditingCardId] = useState<number | null>(null);

  function startNewCard() {
    setEditingCardId(null);
    setCardForm({
      ...EMPTY_CARD_FORM,
      sortOrder: detail?.cards.length ?? 0,
    });
  }

  function startEditCard(cardId: number) {
    const card = detail?.cards.find((c) => c.id === cardId);
    if (!card) return;
    setEditingCardId(cardId);
    setCardForm({
      title: card.title,
      description: card.description ?? "",
      categoryId: card.category_id ?? "",
      templateColumnId: card.template_column_id ?? "",
      sortOrder: card.sort_order,
    });
  }

  function handleSaveCard() {
    if (!detail || !cardForm.title.trim()) return;
    const payload = {
      title: cardForm.title.trim(),
      description: cardForm.description.trim() || null,
      category_id: cardForm.categoryId === "" ? null : cardForm.categoryId,
      template_column_id:
        cardForm.templateColumnId === "" ? null : cardForm.templateColumnId,
      sort_order: cardForm.sortOrder,
    };

    startTransition(async () => {
      const result = editingCardId
        ? await updateTemplateCardAction(editingCardId, payload)
        : await createTemplateCardAction(detail.id, payload);
      if (!result.ok) {
        window.alert(result.message);
        return;
      }
      setCardForm(EMPTY_CARD_FORM);
      setEditingCardId(null);
      await refreshAll(detail.id);
    });
  }

  function handleDeleteCard(cardId: number) {
    if (!detail) return;
    if (!window.confirm("Excluir este card do template?")) return;
    startTransition(async () => {
      const result = await deleteTemplateCardAction(cardId);
      if (!result.ok) {
        window.alert(result.message);
        return;
      }
      await refreshAll(detail.id);
    });
  }

  const nomeDaColuna = (columnId: number | null): string => {
    if (columnId === null) return "Sem coluna";
    return (
      detail?.columns.find((coluna) => coluna.id === columnId)?.name ??
      "Sem coluna"
    );
  };

  return (
    <main className="min-h-screen bg-(--color-surface) py-8">
      <div className="container-page space-y-6">
        <header className="card">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold text-(--color-dark)">
                Templates de Dashboard
              </h1>
              <p className="mt-1 text-sm text-zinc-600">
                Definições reutilizáveis de <strong>coluna</strong> e{" "}
                <strong>card</strong>, aplicáveis a qualquer empresa — editar um
                template não altera automaticamente os quadros já criados; a
                empresa é atualizada por &quot;Aplicar template&quot; /
                &quot;Restaurar do template&quot;.
              </p>
            </div>
            <button
              type="button"
              className="btn-primary"
              onClick={() => {
                setIsCreateOpen(true);
                setCreateMsg("");
              }}
            >
              Novo template
            </button>
          </div>
        </header>

        <div className="grid gap-6 lg:grid-cols-3">
          <section className="space-y-2 lg:col-span-1">
            {templates.length === 0 ? (
              <p className="text-sm text-zinc-600">
                Nenhum template cadastrado ainda.
              </p>
            ) : (
              templates.map((template) => (
                <button
                  key={template.id}
                  type="button"
                  onClick={() => setSelectedTemplateId(template.id)}
                  className={`card w-full text-left transition ${
                    template.id === selectedTemplateId
                      ? "ring-2 ring-(--color-primary)"
                      : ""
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-semibold">
                      {template.name}
                    </span>
                    {template.is_default ? (
                      <span className="rounded-full bg-(--color-primary) px-2 py-0.5 text-[10px] font-semibold text-white">
                        padrão
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-1 text-xs text-zinc-500">
                    {template.card_count} card(s)
                  </p>
                </button>
              ))
            )}
          </section>

          <section className="space-y-4 lg:col-span-2">
            <article className="card">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-lg font-semibold">
                  {detail ? detail.name : "Nenhum template selecionado"}
                </h2>
                {detail ? (
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={openEdit}
                    >
                      Editar
                    </button>
                    <button
                      type="button"
                      className="btn-danger-outline"
                      disabled={isPending}
                      onClick={handleDeleteTemplate}
                    >
                      Excluir
                    </button>
                  </div>
                ) : null}
              </div>

              {detail?.description ? (
                <p className="mt-2 text-sm text-zinc-600">
                  {detail.description}
                </p>
              ) : null}

              {isLoadingDetail ? (
                <p className="mt-3 text-sm text-zinc-500">
                  Carregando template...
                </p>
              ) : null}
            </article>

            {detail ? (
              <article className="card">
                <h3 className="text-base font-semibold">
                  Colunas do template ({detail.columns.length})
                </h3>
                <p className="mt-1 text-sm text-zinc-600">
                  A ordem aqui é a ordem em que as colunas nascem no quadro da
                  empresa. Uma <strong>seção</strong> é um separador visual
                  (como <code>ISO 27001:2022 &gt;&gt;</code>) e não aceita
                  cards.
                </p>

                {columnMsg ? (
                  <p
                    role="status"
                    className="mt-3 rounded-lg bg-zinc-50 p-2 text-sm text-zinc-700"
                  >
                    {columnMsg}
                  </p>
                ) : null}

                <ul className="mt-3 divide-y divide-(--color-neutral)">
                  {detail.columns.map((column, indice) => (
                    <li
                      key={column.id}
                      className="flex flex-wrap items-center justify-between gap-3 py-2"
                    >
                      <div>
                        <p className="text-sm font-medium text-(--color-dark)">
                          {column.name}
                          {column.kind === "SECTION" ? (
                            <span className="ml-2 rounded-full bg-(--color-dark) px-2 py-0.5 text-[10px] text-white">
                              seção
                            </span>
                          ) : null}
                        </p>
                        <p className="text-xs text-zinc-500">
                          {column.card_count} card(s) nascem aqui
                        </p>
                      </div>
                      <div className="flex shrink-0 gap-2">
                        <button
                          type="button"
                          className="btn-secondary text-xs"
                          aria-label={`Mover a coluna ${column.name} para cima`}
                          disabled={indice === 0 || isPending}
                          onClick={() => handleMoveColumn(column, -1)}
                        >
                          ↑
                        </button>
                        <button
                          type="button"
                          className="btn-secondary text-xs"
                          aria-label={`Mover a coluna ${column.name} para baixo`}
                          disabled={
                            indice === detail.columns.length - 1 || isPending
                          }
                          onClick={() => handleMoveColumn(column, 1)}
                        >
                          ↓
                        </button>
                        <button
                          type="button"
                          className="btn-secondary text-xs"
                          onClick={() => handleRenameColumn(column)}
                        >
                          Renomear
                        </button>
                        <button
                          type="button"
                          className="btn-danger-outline text-xs"
                          disabled={isPending}
                          onClick={() => handleDeleteColumn(column)}
                        >
                          Excluir
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>

                {detail.columns.length === 0 ? (
                  <p className="mt-3 text-sm text-zinc-600">
                    Nenhuma coluna ainda — os cards deste template nascerão sem
                    coluna no quadro da empresa.
                  </p>
                ) : null}

                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <input
                    className="field w-56 text-sm"
                    placeholder="Nome da coluna"
                    aria-label="Nome da coluna nova"
                    value={newColumnName}
                    onChange={(e) => setNewColumnName(e.target.value)}
                  />
                  <select
                    className="field w-auto text-sm"
                    aria-label="Tipo da coluna nova"
                    value={newColumnKind}
                    onChange={(e) =>
                      setNewColumnKind(e.target.value as TemplateColumnKind)
                    }
                  >
                    <option value="COLUMN">Coluna</option>
                    <option value="SECTION">Seção (separador)</option>
                  </select>
                  <button
                    type="button"
                    className="btn-primary text-sm"
                    disabled={!newColumnName.trim() || isPending}
                    onClick={handleCreateColumn}
                  >
                    + Coluna
                  </button>
                </div>
              </article>
            ) : null}

            {detail ? (
              <article className="card">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-semibold">
                    Cards do template ({detail.cards.length})
                  </h3>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={startNewCard}
                  >
                    + Novo card
                  </button>
                </div>

                <ul className="mt-4 divide-y divide-(--color-neutral)">
                  {detail.cards.map((card) => (
                    <li
                      key={card.id}
                      className="flex items-start justify-between gap-3 py-3"
                    >
                      <div>
                        <p className="text-sm font-medium text-(--color-dark)">
                          {card.title}
                        </p>
                        {card.description ? (
                          <p className="mt-0.5 text-xs text-zinc-600">
                            {card.description}
                          </p>
                        ) : null}
                        <p className="mt-1 text-xs text-zinc-500">
                          Coluna: {nomeDaColuna(card.template_column_id)} ·
                          Categoria: {card.category_name ?? "Sem categoria"} ·
                          ordem {card.sort_order}
                        </p>
                      </div>
                      <div className="flex shrink-0 gap-2">
                        <button
                          type="button"
                          className="btn-secondary"
                          onClick={() => startEditCard(card.id)}
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          className="btn-danger-outline"
                          disabled={isPending}
                          onClick={() => handleDeleteCard(card.id)}
                        >
                          Excluir
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>

                {cardForm.title !== "" || editingCardId !== null ? (
                  <div className="mt-4 space-y-3 rounded-lg border border-(--color-neutral) p-3">
                    <p className="text-sm font-semibold">
                      {editingCardId ? "Editar card" : "Novo card"}
                    </p>
                    <input
                      className="field"
                      placeholder="Título do card"
                      aria-label="Título do card"
                      value={cardForm.title}
                      onChange={(e) =>
                        setCardForm((prev) => ({
                          ...prev,
                          title: e.target.value,
                        }))
                      }
                    />
                    <textarea
                      className="field"
                      rows={4}
                      placeholder="Descrição — texto normativo do controle (opcional)"
                      aria-label="Descrição do card"
                      value={cardForm.description}
                      onChange={(e) =>
                        setCardForm((prev) => ({
                          ...prev,
                          description: e.target.value,
                        }))
                      }
                    />
                    <select
                      className="field"
                      aria-label="Coluna do card"
                      value={cardForm.templateColumnId}
                      onChange={(e) =>
                        setCardForm((prev) => ({
                          ...prev,
                          templateColumnId: e.target.value
                            ? Number(e.target.value)
                            : "",
                        }))
                      }
                    >
                      <option value="">Sem coluna</option>
                      {detail.columns
                        .filter((coluna) => coluna.kind === "COLUMN")
                        .map((coluna) => (
                          <option key={coluna.id} value={coluna.id}>
                            {coluna.name}
                          </option>
                        ))}
                    </select>
                    <select
                      className="field"
                      aria-label="Categoria do card"
                      value={cardForm.categoryId}
                      onChange={(e) =>
                        setCardForm((prev) => ({
                          ...prev,
                          categoryId: e.target.value
                            ? Number(e.target.value)
                            : "",
                        }))
                      }
                    >
                      <option value="">Sem categoria</option>
                      {categories.map((category) => (
                        <option key={category.id} value={category.id}>
                          {category.name}
                        </option>
                      ))}
                    </select>
                    <input
                      className="field"
                      type="number"
                      placeholder="Ordem"
                      aria-label="Ordem do card"
                      value={cardForm.sortOrder}
                      onChange={(e) =>
                        setCardForm((prev) => ({
                          ...prev,
                          sortOrder: Number(e.target.value) || 0,
                        }))
                      }
                    />
                    <div className="flex gap-2">
                      <button
                        type="button"
                        className="btn-primary"
                        disabled={!cardForm.title.trim() || isPending}
                        onClick={handleSaveCard}
                      >
                        {editingCardId ? "Salvar card" : "Criar card"}
                      </button>
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => {
                          setCardForm(EMPTY_CARD_FORM);
                          setEditingCardId(null);
                        }}
                      >
                        Cancelar
                      </button>
                    </div>
                  </div>
                ) : null}
              </article>
            ) : null}
          </section>
        </div>

        {isCreateOpen ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
              <h3 className="text-base font-semibold">Novo template</h3>
              <div className="mt-4 space-y-3">
                <input
                  className="field"
                  placeholder="Nome do template"
                  aria-label="Nome do template"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                />
                <textarea
                  className="field"
                  rows={2}
                  placeholder="Descrição (opcional)"
                  aria-label="Descrição do template"
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                />
                <label className="flex items-center gap-2 text-sm text-zinc-700">
                  <input
                    type="checkbox"
                    checked={newIsDefault}
                    onChange={(e) => setNewIsDefault(e.target.checked)}
                  />
                  Definir como template padrão (usado em novos onboardings)
                </label>
                {createMsg ? (
                  <p className="text-sm text-red-600">{createMsg}</p>
                ) : null}
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setIsCreateOpen(false)}
                  >
                    Cancelar
                  </button>
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={isPending}
                    onClick={handleCreateTemplate}
                  >
                    Criar template
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : null}

        {isEditOpen && detail ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
              <h3 className="text-base font-semibold">Editar template</h3>
              <div className="mt-4 space-y-3">
                <input
                  className="field"
                  aria-label="Nome do template"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                />
                <textarea
                  className="field"
                  rows={2}
                  aria-label="Descrição do template"
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                />
                <label className="flex items-center gap-2 text-sm text-zinc-700">
                  <input
                    type="checkbox"
                    checked={editIsDefault}
                    onChange={(e) => setEditIsDefault(e.target.checked)}
                  />
                  Definir como template padrão
                </label>
                {editMsg ? (
                  <p className="text-sm text-red-600">{editMsg}</p>
                ) : null}
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setIsEditOpen(false)}
                  >
                    Cancelar
                  </button>
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={isPending}
                    onClick={handleUpdateTemplate}
                  >
                    Salvar
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </main>
  );
}
```

---

#### `frontend/app/private/admin/templates/actions.test.ts`

##### 1. Ação Manual

Acrescente ao **final** do arquivo o bloco abaixo, e inclua as quatro actions de coluna no
`import` do topo.

##### 2. Código Fonte Completo (bloco a acrescentar ao final)

```typescript
describe("colunas de template", () => {
  it("cria coluna pela rota do template", async () => {
    backendMock.mockResolvedValue({ id: 1 });

    await createTemplateColumnAction(3, {
      name: "Controle 5",
      kind: "COLUMN",
    });

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/templates/3/columns");
    expect(opcoes.method).toBe("POST");
    expect(opcoes.body).toMatchObject({ name: "Controle 5", kind: "COLUMN" });
  });

  it("cria coluna do tipo seção", async () => {
    backendMock.mockResolvedValue({ id: 2 });

    await createTemplateColumnAction(3, {
      name: "ISO 27001:2022 >>",
      kind: "SECTION",
    });

    const [, opcoes] = ultimaChamada();
    expect(opcoes.body).toMatchObject({ kind: "SECTION" });
  });

  it("edita coluna com PATCH", async () => {
    backendMock.mockResolvedValue({ id: 1 });

    await updateTemplateColumnAction(3, 1, {
      name: "Renomeada",
      kind: "COLUMN",
    });

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/templates/3/columns/1");
    expect(opcoes.method).toBe("PATCH");
  });

  it("move coluna mandando âncoras, nunca a posição", async () => {
    backendMock.mockResolvedValue({ id: 1 });

    await moveTemplateColumnAction(3, 1, 5, 6);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/templates/3/columns/1/move");
    expect(opcoes.body).toEqual({ prev_column_id: 5, next_column_id: 6 });
  });

  it("devolve falha tratável quando a coluna está em uso (409)", async () => {
    backendMock.mockRejectedValue(
      new Error("Coluna de template em uso por 12 card(s) de template."),
    );

    const resultado = await deleteTemplateColumnAction(3, 1);

    expect(resultado.ok).toBe(false);
    if (!resultado.ok) {
      expect(resultado.message).toContain("12 card(s)");
    }
  });
});

describe("cards de template com coluna", () => {
  it("envia template_column_id ao criar", async () => {
    backendMock.mockResolvedValue({ id: 9 });

    await createTemplateCardAction(3, {
      title: "Política de SI",
      description: "Texto normativo",
      category_id: 2,
      template_column_id: 1,
      sort_order: 0,
    });

    const [, opcoes] = ultimaChamada();
    expect(opcoes.body).toMatchObject({
      template_column_id: 1,
      description: "Texto normativo",
    });
  });

  it("envia template_column_id nulo quando o card não tem coluna", async () => {
    backendMock.mockResolvedValue({ id: 9 });

    await updateTemplateCardAction(9, {
      title: "Card",
      description: null,
      category_id: null,
      template_column_id: null,
      sort_order: 0,
    });

    const [, opcoes] = ultimaChamada();
    expect(opcoes.body).toMatchObject({ template_column_id: null });
  });
});
```

**Import necessário no topo do arquivo:**

```typescript
import {
  createTemplateAction,
  createTemplateCardAction,
  createTemplateColumnAction,
  deleteTemplateAction,
  deleteTemplateCardAction,
  deleteTemplateColumnAction,
  getTemplateDetailAction,
  listTemplateCategoriesAction,
  listTemplatesAction,
  moveTemplateColumnAction,
  updateTemplateAction,
  updateTemplateCardAction,
  updateTemplateColumnAction,
} from "./actions";
```

---

### Fase 11 — Importador do Trello e seed

---

#### `backend/scripts/import_trello_board.py`

##### 1. Ação Manual

Crie o arquivo `backend/scripts/import_trello_board.py`. Uso:

```bash
cd backend

# 1) SEMPRE o dry-run primeiro — ele não abre transação de escrita.
python -m scripts.import_trello_board \
       "../trello exemplo para ser implementado.json" \
       --template-name "[MODELO] Due Diligence - Pix Indireto" --dry-run

# 2) Só depois de revisar o plano:
python -m scripts.import_trello_board \
       "../trello exemplo para ser implementado.json" \
       --template-name "[MODELO] Due Diligence - Pix Indireto"
```

> ⚠️ **O arquivo do Trello NÃO entra no repositório** (CA-30, Fase 0). O importador lê do
> disco local do operador. Ele carrega 12 nomes completos de membros e o ID da organização.

**Números reais do export de referência, medidos** — use-os para conferir o `--dry-run`:

| Métrica | Valor medido |
|---|---|
| Listas no arquivo | 31 (**22 abertas**, 9 arquivadas) |
| Listas separadoras (`>>`) | 3 |
| Cards abertos | 213 |
| Cards abertos que estão em lista ARQUIVADA | **50** |
| Cards com descrição | 146 |
| Cards com prefixo de código (`5.1 `) | 144 |
| Cards com etiqueta | 178 |
| Descrições contendo `U+200C` | 87 |
| Etiquetas definidas no quadro | 11 (**8 aprovadas**) |
| Nomes de lista acima de 160 caracteres | **3** (máx. 264) |
| Títulos de card acima de 160 caracteres | **23** (máx. 471) |
| Descrição mais longa | 2 133 caracteres |

Rodando o `--dry-run` sobre esse arquivo, a saída esperada é exatamente:

```
Colunas a criar ........................ 22
  das quais seções (>>) ................ 3
  com nome truncado em 160 caracteres .. 3
Listas arquivadas ignoradas ............ 9

Cards a criar .......................... 213
  com descrição ........................ 152
  com control_code ..................... 144
  com etiqueta ......................... 178
  com título truncado .................. 23
  SEM COLUNA (vinham de lista arquivada) 50

Etiquetas a garantir ................... 8
Etiquetas NÃO importadas ............... 3

Descrições ainda com U+200C (tem de ser 0): 0
```

> **Por que 152 descrições e não 146.** 146 cards têm `desc` preenchida no arquivo. Os 23
> títulos truncados ganham o título completo no início da descrição, e 6 desses cards não
> tinham descrição nenhuma — 146 + 6 = 152. Nenhum texto é perdido, e é isso que o número
> a mais está dizendo.

##### 2. Código Fonte Completo

```python
from __future__ import annotations

"""
Importador one-shot do export JSON de um quadro do Trello para um
`DashboardTemplate`.

Script de uso pontual, no mesmo formato dos 8 seeds já existentes em
`backend/scripts/`. Roda com o banco configurado em `backend/.env`.

**Idempotente por nome de template.** Rodar duas vezes com o mesmo
`--template-name` não duplica coluna, card nem etiqueta: colunas casam
por nome dentro do template, cards casam por (coluna, título). O export
de referência não tem nenhum par (lista, título) repetido — foi
verificado — então esse casamento é exato.

O que é IGNORADO, e por quê: `actions[]` (527 eventos — histórico do
Trello não é histórico da plataforma, e importá-lo poluiria a trilha de
auditoria com atores que não existem aqui), `members[]`,
`memberships[]`, `prefs`, `limits`, `pluginData`, `checklists` (vazio no
export) e `customFields` (vazio).

Três decisões que o export real forçou, e que o PRD não previa:

1. **Listas arquivadas guardam 50 cards abertos.** O PRD supunha que as
   listas fechadas estivessem vazias ("6 listas, todas de fase
   encerrada"); no arquivo real são 9 listas fechadas com 50 cards
   abertos dentro. Ignorar as listas E os cards perderia 23 % do
   conteúdo em silêncio — o pior desfecho possível para um importador.
   A escolha: as listas fechadas NÃO viram coluna, e os cards delas
   entram com `template_column_id = NULL`, caindo no balde "Sem coluna"
   do quadro derivado, onde o auditor decide o destino. `--skip-archived-
   list-cards` descarta esses cards, se for essa a decisão — mas
   explicitamente, nunca por omissão.

2. **3 nomes de lista e 23 títulos de card estouram `String(160)`** (até
   264 e 471 caracteres). Sem tratamento, o INSERT falha no MySQL em
   modo estrito — e falharia só na metade da importação. Nomes de coluna
   são truncados. Títulos de card também, mas o título completo é
   PRESERVADO no início da `description`: o texto longo é a redação
   normativa do controle, e perdê-lo esvaziaria metade do valor do
   import.

3. **`pos` do Trello nunca é copiada.** O alfabeto é outro (float
   65 535 … 2 359 295 contra base-62 lexicográfica). A ordem RELATIVA é
   preservada e as chaves são regeradas com `n_keys_between`.
"""

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.company_dashboard import DashboardTemplate, DashboardTemplateCard
from app.models.dashboard_board import (
    DashboardColumnKind,
    DashboardLabel,
    DashboardTemplateColumn,
)
from app.services.fractional_index import n_keys_between

#: Espaçador invisível que o export usa entre parágrafos. Sobrevive a
#: qualquer `strip()` e aparece como caractere-fantasma na UI (CA-25).
ZERO_WIDTH_NON_JOINER = "‌"

#: `5.1 Política de SI` -> ("5.1", "Política de SI"). 144 dos 213 cards.
CONTROL_CODE_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+(.*)$", re.DOTALL)

#: Sufixo que marca a lista separadora do Trello (`ISO 27001:2022 >>`).
SECTION_SUFFIX = ">>"

MAX_NAME_LENGTH = 160
MAX_CONTROL_CODE_LENGTH = 40

#: As 8 etiquetas aprovadas em §2.1 do PRD, com o hex do tema
#: correspondente à cor nomeada do Trello. As três de fora, e o motivo:
#: `Concluído com evidência` é redundante com o status CONFORME (duas
#: fontes de verdade para "está conforme?" é exatamente o que B-A23
#: proíbe); `Não Aplicável` é status e não etiqueta (decisão D-2, no
#: backlog); `Entregue - Inove Educação` é específica de um cliente.
APPROVED_LABELS: dict[str, str] = {
    "Item Critico": "#96311D",
    "Alta Criticidade": "#C2410C",
    "Média Criticidade": "#A16207",
    "Baixa Criticidade": "#2C5A8C",
    "Aguardando empresa": "#0E7490",
    "Check-list": "#6D28D9",
    "Inserir doc atualizado no final do projeto": "#854D0E",
    "Final do projeto": "#1E3A8A",
}

REJECTED_LABELS = {
    "Concluído com evidência",
    "Não Aplicável",
    "Entregue - Inove Educação",
}


# ------------------------------------------------------------ Modelo


@dataclass
class ParsedColumn:
    trello_id: str
    name: str
    kind: DashboardColumnKind
    pos: float
    name_was_truncated: bool = False


@dataclass
class ParsedCard:
    trello_list_id: str | None
    control_code: str | None
    title: str
    description: str | None
    label_names: list[str]
    pos: float
    title_was_truncated: bool = False


@dataclass
class ParsedBoard:
    board_name: str
    columns: list[ParsedColumn] = field(default_factory=list)
    cards: list[ParsedCard] = field(default_factory=list)
    label_names: list[str] = field(default_factory=list)
    rejected_label_names: list[str] = field(default_factory=list)
    ignored_closed_lists: int = 0
    cards_from_closed_lists: int = 0


# ------------------------------------------------------------ Parsing


def normalize_whitespace(text: str) -> str:
    """
    Colapsa quebras de linha e espaços repetidos.

    Um nome de lista do export real tem `\\n` no meio ("Segurança de QR
    Codes dinâmicos -\\n A seção 4 …"). Sem isso, o nome da coluna
    quebraria a linha no meio do cabeçalho do quadro.
    """
    return re.sub(r"\s+", " ", text).strip()


def clean_description(desc: str | None) -> str | None:
    """
    Remove o `U+200C` (CA-25) e normaliza a pontuação Unicode do texto.

    87 das 146 descrições do export carregam esse caractere invisível
    como espaçador de parágrafo. `strip()` não o remove — ele não é
    espaço em branco para o Python — e ele viaja até o `<p>` da UI, onde
    aparece como um retângulo vazio em algumas fontes.

    O Markdown é preservado como texto: os `**Controle**` do export são o
    texto normativo, e reescrevê-los seria alterar a redação do controle.
    """
    if desc is None:
        return None
    texto = desc.replace(ZERO_WIDTH_NON_JOINER, "")
    # NFC junta acentos decompostos — o export mistura as duas formas, e
    # a comparação de idempotência por título depende de uma forma só.
    texto = unicodedata.normalize("NFC", texto)
    texto = texto.strip()
    return texto or None


def is_section(list_name: str) -> bool:
    """`ISO 27001:2022 >>` é separador, não coluna de trabalho."""
    return normalize_whitespace(list_name).endswith(SECTION_SUFFIX)


def split_control_code(name: str) -> tuple[str | None, str]:
    """
    Separa o prefixo numérico do título: `5.1 Política` -> ("5.1",
    "Política"). 144 dos 213 cards do export têm esse prefixo.

    Devolve `(None, nome)` quando não há prefixo — e é o comportamento
    correto: inventar um código para os outros 69 cards seria pior que
    deixá-los sem código.
    """
    limpo = normalize_whitespace(name)
    correspondencia = CONTROL_CODE_RE.match(limpo)
    if not correspondencia:
        return None, limpo

    codigo, titulo = correspondencia.group(1), correspondencia.group(2).strip()
    if not titulo or len(codigo) > MAX_CONTROL_CODE_LENGTH:
        # Card cujo nome é SÓ um número, ou código absurdamente longo:
        # melhor manter o nome inteiro como título.
        return None, limpo
    return codigo, titulo


def truncate(text: str, limit: int = MAX_NAME_LENGTH) -> tuple[str, bool]:
    """Trunca preservando um marcador visível de que houve corte."""
    if len(text) <= limit:
        return text, False
    return text[: limit - 1].rstrip() + "…", True


def parse_board(raw: dict) -> ParsedBoard:
    """
    Converte o JSON bruto em `ParsedBoard`. **Função pura** — nenhuma
    sessão de banco, nenhum I/O — é o que torna o `--dry-run` uma
    execução completa da lógica de conversão, e não uma simulação
    parecida com ela.
    """
    parsed = ParsedBoard(board_name=normalize_whitespace(raw.get("name", "")))

    listas_abertas = [lista for lista in raw.get("lists", []) if not lista.get("closed")]
    parsed.ignored_closed_lists = len(raw.get("lists", [])) - len(listas_abertas)

    ids_de_coluna: set[str] = set()
    for lista in sorted(listas_abertas, key=lambda item: item.get("pos", 0)):
        nome_normalizado = normalize_whitespace(lista.get("name", ""))
        nome, truncado = truncate(nome_normalizado)
        parsed.columns.append(
            ParsedColumn(
                trello_id=lista["id"],
                name=nome,
                kind=(
                    DashboardColumnKind.SECTION
                    if is_section(nome_normalizado)
                    else DashboardColumnKind.COLUMN
                ),
                pos=float(lista.get("pos", 0)),
                name_was_truncated=truncado,
            )
        )
        ids_de_coluna.add(lista["id"])

    etiquetas_por_id = {
        etiqueta["id"]: normalize_whitespace(etiqueta.get("name", ""))
        for etiqueta in raw.get("labels", [])
    }
    nomes_de_etiqueta = {
        nome for nome in etiquetas_por_id.values() if nome in APPROVED_LABELS
    }
    parsed.label_names = sorted(nomes_de_etiqueta)
    parsed.rejected_label_names = sorted(
        {
            nome
            for nome in etiquetas_por_id.values()
            if nome and nome not in APPROVED_LABELS
        }
    )

    for card in raw.get("cards", []):
        if card.get("closed"):
            continue

        id_da_lista = card.get("idList")
        de_lista_fechada = id_da_lista not in ids_de_coluna
        if de_lista_fechada:
            parsed.cards_from_closed_lists += 1

        codigo, titulo_completo = split_control_code(card.get("name", ""))
        titulo, titulo_truncado = truncate(titulo_completo)

        descricao = clean_description(card.get("desc"))
        if titulo_truncado:
            # O título longo É a redação do controle. Truncá-lo sem
            # preservá-lo em lugar nenhum perderia o conteúdo.
            prefixo = f"**{titulo_completo}**"
            descricao = f"{prefixo}\n\n{descricao}" if descricao else prefixo

        parsed.cards.append(
            ParsedCard(
                trello_list_id=None if de_lista_fechada else id_da_lista,
                control_code=codigo,
                title=titulo,
                description=descricao,
                label_names=[
                    etiquetas_por_id[label_id]
                    for label_id in card.get("idLabels", [])
                    if etiquetas_por_id.get(label_id) in APPROVED_LABELS
                ],
                pos=float(card.get("pos", 0)),
                title_was_truncated=titulo_truncado,
            )
        )

    parsed.cards.sort(key=lambda item: item.pos)
    return parsed


# ------------------------------------------------------------ Relatório


def render_plan(parsed: ParsedBoard) -> str:
    """Plano legível do que SERIA escrito — a saída do `--dry-run`."""
    secoes = [c for c in parsed.columns if c.kind == DashboardColumnKind.SECTION]
    com_descricao = [c for c in parsed.cards if c.description]
    com_codigo = [c for c in parsed.cards if c.control_code]
    com_etiqueta = [c for c in parsed.cards if c.label_names]
    titulos_truncados = [c for c in parsed.cards if c.title_was_truncated]
    nomes_truncados = [c for c in parsed.columns if c.name_was_truncated]
    sem_coluna = [c for c in parsed.cards if c.trello_list_id is None]

    linhas: list[str] = [
        f"Quadro de origem: {parsed.board_name}",
        "",
        f"Colunas a criar ........................ {len(parsed.columns)}",
        f"  das quais seções (>>) ................ {len(secoes)}",
        f"  com nome truncado em 160 caracteres .. {len(nomes_truncados)}",
        f"Listas arquivadas ignoradas ............ {parsed.ignored_closed_lists}",
        "",
        f"Cards a criar .......................... {len(parsed.cards)}",
        f"  com descrição ........................ {len(com_descricao)}",
        f"  com control_code ..................... {len(com_codigo)}",
        f"  com etiqueta ......................... {len(com_etiqueta)}",
        f"  com título truncado (texto preservado",
        f"  no início da descrição) .............. {len(titulos_truncados)}",
        f"  SEM COLUNA (vinham de lista arquivada) {len(sem_coluna)}",
        "",
        f"Etiquetas a garantir ................... {len(parsed.label_names)}",
        f"  {', '.join(parsed.label_names)}",
        f"Etiquetas NÃO importadas ............... {len(parsed.rejected_label_names)}",
        f"  {', '.join(parsed.rejected_label_names)}",
        "",
        "Colunas, na ordem:",
    ]

    contagem_por_lista: dict[str, int] = {}
    for card in parsed.cards:
        if card.trello_list_id is not None:
            contagem_por_lista[card.trello_list_id] = (
                contagem_por_lista.get(card.trello_list_id, 0) + 1
            )

    for indice, coluna in enumerate(parsed.columns, start=1):
        marca = "§" if coluna.kind == DashboardColumnKind.SECTION else " "
        total = contagem_por_lista.get(coluna.trello_id, 0)
        linhas.append(f"  {indice:2d}. {marca} [{total:3d} cards] {coluna.name}")

    if sem_coluna:
        linhas += [
            "",
            "ATENÇÃO: os cards abaixo vinham de listas ARQUIVADAS no Trello e",
            "entrarão sem coluna (balde 'Sem coluna' do quadro). Use",
            "--skip-archived-list-cards para descartá-los em vez de importá-los.",
        ]
        for card in sem_coluna[:10]:
            linhas.append(f"  - {card.title[:90]}")
        if len(sem_coluna) > 10:
            linhas.append(f"  … e mais {len(sem_coluna) - 10}")

    # CA-25: nenhum U+200C pode sobreviver.
    residuos = sum(
        1 for card in parsed.cards if ZERO_WIDTH_NON_JOINER in (card.description or "")
    )
    linhas += ["", f"Descrições ainda com U+200C (tem de ser 0): {residuos}"]

    return "\n".join(linhas)


# ------------------------------------------------------------ Persistência


def ensure_labels(db: Session, nomes: list[str]) -> None:
    """Garante o vocabulário de etiquetas — sem duplicar o que já existe
    (a migration c8f1a3e57b90 já semeou as 8)."""
    existentes = {
        label.name
        for label in db.scalars(
            select(DashboardLabel).where(DashboardLabel.name.in_(nomes))
        ).all()
    }
    for ordem, nome in enumerate(nomes):
        if nome in existentes:
            continue
        db.add(
            DashboardLabel(
                name=nome, color=APPROVED_LABELS[nome], sort_order=ordem
            )
        )
    db.flush()


def persist(
    db: Session,
    parsed: ParsedBoard,
    template_name: str,
    *,
    skip_archived_list_cards: bool = False,
) -> dict[str, int]:
    """
    Escreve o template, as colunas e os cards. Idempotente por nome de
    template: uma segunda execução não cria nada.

    Não faz `commit` — quem controla a transação é `main()`, no mesmo
    padrão de camadas do resto do backend (B4).
    """
    contadores = {
        "template_criado": 0,
        "colunas_criadas": 0,
        "colunas_existentes": 0,
        "cards_criados": 0,
        "cards_existentes": 0,
        "cards_descartados": 0,
    }

    template = db.scalar(
        select(DashboardTemplate).where(DashboardTemplate.name == template_name)
    )
    if template is None:
        template = DashboardTemplate(
            name=template_name,
            description=f"Importado do quadro Trello '{parsed.board_name}'",
            is_default=False,
        )
        db.add(template)
        db.flush()
        contadores["template_criado"] = 1

    ensure_labels(db, parsed.label_names)

    # ---- Colunas ----
    colunas_existentes = {
        coluna.name: coluna
        for coluna in db.scalars(
            select(DashboardTemplateColumn).where(
                DashboardTemplateColumn.template_id == template.id
            )
        ).all()
    }

    faltantes = [c for c in parsed.columns if c.name not in colunas_existentes]
    coluna_por_trello_id: dict[str, DashboardTemplateColumn] = {}
    if faltantes:
        ultima = max(
            (c.position for c in colunas_existentes.values()), default=None
        )
        for coluna_parseada, position in zip(
            faltantes, n_keys_between(ultima, None, len(faltantes))
        ):
            nova = DashboardTemplateColumn(
                template_id=template.id,
                name=coluna_parseada.name,
                kind=coluna_parseada.kind,
                position=position,
            )
            db.add(nova)
            colunas_existentes[coluna_parseada.name] = nova
            contadores["colunas_criadas"] += 1
        db.flush()

    for coluna_parseada in parsed.columns:
        coluna_por_trello_id[coluna_parseada.trello_id] = colunas_existentes[
            coluna_parseada.name
        ]
    contadores["colunas_existentes"] = len(parsed.columns) - contadores["colunas_criadas"]

    # ---- Cards ----
    # Idempotência por (coluna, título). O export de referência não tem
    # nenhum par repetido — verificado antes de escolher esta chave.
    ja_existentes = {
        (card.template_column_id, card.title)
        for card in db.scalars(
            select(DashboardTemplateCard).where(
                DashboardTemplateCard.template_id == template.id
            )
        ).all()
    }

    a_criar: list[tuple[ParsedCard, int | None]] = []
    for card in parsed.cards:
        if card.trello_list_id is None:
            if skip_archived_list_cards:
                contadores["cards_descartados"] += 1
                continue
            column_id = None
        else:
            coluna = coluna_por_trello_id.get(card.trello_list_id)
            if coluna is None or coluna.kind == DashboardColumnKind.SECTION:
                # Card numa seção não deveria existir (o export tem zero),
                # mas se existir ele vai para o balde, nunca para dentro
                # de um separador.
                column_id = None
            else:
                column_id = coluna.id

        if (column_id, card.title) in ja_existentes:
            contadores["cards_existentes"] += 1
            continue
        ja_existentes.add((column_id, card.title))
        a_criar.append((card, column_id))

    # `position` regenerada POR COLUNA, na ordem relativa do `pos` do
    # Trello — nunca copiada (o alfabeto é outro).
    por_coluna: dict[int | None, list[tuple[ParsedCard, int | None]]] = {}
    for item in a_criar:
        por_coluna.setdefault(item[1], []).append(item)

    for column_id, itens in por_coluna.items():
        for ordem, ((card, _), position) in enumerate(
            zip(itens, n_keys_between(None, None, len(itens)))
        ):
            db.add(
                DashboardTemplateCard(
                    template_id=template.id,
                    title=card.title,
                    description=card.description,
                    tag="Sem categoria",
                    category_id=None,
                    template_column_id=column_id,
                    sort_order=ordem,
                    position=position,
                )
            )
            contadores["cards_criados"] += 1

    db.flush()
    return contadores


# ------------------------------------------------------------ CLI


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Importa um export JSON de quadro do Trello como template de "
            "dashboard. Idempotente por nome de template."
        )
    )
    parser.add_argument("arquivo", help="Caminho do export JSON do Trello")
    parser.add_argument(
        "--template-name",
        required=True,
        help="Nome do DashboardTemplate a criar/reaproveitar",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Imprime o plano e NÃO escreve nada no banco",
    )
    parser.add_argument(
        "--skip-archived-list-cards",
        action="store_true",
        help=(
            "Descarta os cards que vinham de listas arquivadas no Trello, em "
            "vez de importá-los sem coluna"
        ),
    )
    args = parser.parse_args()

    caminho = Path(args.arquivo)
    if not caminho.is_file():
        print(f"Arquivo não encontrado: {caminho}", file=sys.stderr)
        return 2

    raw = json.loads(caminho.read_text(encoding="utf-8"))
    parsed = parse_board(raw)

    print(render_plan(parsed))
    print()

    if args.dry_run:
        print("--dry-run: nada foi escrito no banco.")
        return 0

    with SessionLocal() as db:
        contadores = persist(
            db,
            parsed,
            args.template_name,
            skip_archived_list_cards=args.skip_archived_list_cards,
        )
        db.commit()

    print(f"Template '{args.template_name}':")
    for chave, valor in contadores.items():
        print(f"  {chave:.<26} {valor}")
    print("Importação concluída.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

---

#### `backend/scripts/seed_dashboard_templates.py`

##### 1. Ação Manual

Abra `backend/scripts/seed_dashboard_templates.py` e substitua o conteúdo inteiro.

> **Sem esta alteração, todo ambiente novo nasce com template SEM COLUNA** — e todo
> dashboard criado no onboarding nasce com os cards no balde "Sem coluna".

##### 2. Código Fonte Completo

```python
from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.company_dashboard import (
    DashboardCardCategory,
    DashboardTemplate,
    DashboardTemplateCard,
)
from app.models.dashboard_board import DashboardColumnKind, DashboardTemplateColumn
from app.services.fractional_index import n_keys_between


def _resolve_category_id(db, name: str) -> int | None:
    category = db.scalar(
        select(DashboardCardCategory).where(DashboardCardCategory.name == name)
    )
    return category.id if category else None


def main() -> None:
    # (título, categoria/tag, ordem, nome da coluna em que o card nasce)
    templates = [
        {
            "name": "Template 1",
            "description": "Template de dashboard padrão",
            "is_default": True,
            "columns": ["A fazer", "Em análise", "Concluído"],
            "cards": [
                ("Card 1", "Financeiro", 0, "A fazer"),
                ("Card 2", "Operacional", 1, "A fazer"),
                ("Card 3", "Vendas", 2, "Em análise"),
            ],
        },
        {
            "name": "Template 2",
            "description": "Template de dashboard de exemplo",
            "is_default": False,
            "columns": ["A fazer", "Em análise", "Concluído"],
            "cards": [
                ("Card 1", "Financeiro", 0, "A fazer"),
                ("Card 2", "Operacional", 1, "A fazer"),
                ("Card 3", "Vendas", 2, "Em análise"),
            ],
        },
    ]

    with SessionLocal() as db:
        for tp1 in templates:
            existing = db.scalar(
                select(DashboardTemplate).where(DashboardTemplate.name == tp1["name"])
            )
            if existing:
                # Mantém o flag de default sincronizado se o template já existir
                existing.is_default = tp1["is_default"]
                continue

            template = DashboardTemplate(
                name=tp1["name"],
                description=tp1["description"],
                is_default=tp1["is_default"],
            )
            db.add(template)
            db.flush()

            # As colunas vêm ANTES dos cards: o card precisa do
            # `template_column_id` no momento do insert.
            coluna_por_nome: dict[str, DashboardTemplateColumn] = {}
            posicoes = n_keys_between(None, None, len(tp1["columns"]))
            for nome_da_coluna, position in zip(tp1["columns"], posicoes):
                coluna = DashboardTemplateColumn(
                    template_id=template.id,
                    name=nome_da_coluna,
                    kind=DashboardColumnKind.COLUMN,
                    position=position,
                )
                db.add(coluna)
                coluna_por_nome[nome_da_coluna] = coluna
            db.flush()

            posicoes_de_card = n_keys_between(None, None, len(tp1["cards"]))
            for (title, tag, order, nome_da_coluna), position in zip(
                tp1["cards"], posicoes_de_card
            ):
                db.add(
                    DashboardTemplateCard(
                        template_id=template.id,
                        title=title,
                        tag=tag,
                        category_id=_resolve_category_id(db, tag),
                        template_column_id=coluna_por_nome[nome_da_coluna].id,
                        sort_order=order,
                        position=position,
                    )
                )

        db.commit()
        print("Templates de dashboard carregados com sucesso.")


if __name__ == "__main__":
    main()
```

---

### Fase 12 — Documentação

---

#### `docs/backlog.md` · `docs/roadmap.md` · `docs/relatorio_funcionalidades.md` · `docs/index.md`

##### 1. Ação Manual

Registre a entrega e abra os dois itens que o PRD deixou explicitamente fora de escopo
(CA-31). Acrescente aos arquivos existentes, sem reescrevê-los.

##### 2. Conteúdo a acrescentar

**`docs/backlog.md`** — dois itens novos:

```markdown
### D-2 — `NAO_APLICAVEL` como 5º valor de `DashboardCardStatus`

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

---

### D-4 — Anexos em card de dashboard

**Origem:** decisão D-4 do PRD do Quadro Kanban (2026-08-27).

**Problema.** `Evidence` existe, mas é `FK → audit_controls.id`. Ligar anexo a
`DashboardCard` exige uma segunda FK opcional (`evidences.dashboard_card_id`) e
revisar `storage.py`, `test_storage_path_guard.py` e o download autenticado do
frontend.

**Por que não entrou em v1.** O export de referência tem **0 anexos** — não há
requisito comprovado. Entrar sem requisito significaria projetar a regra de posse do
arquivo (quem pode baixar o anexo de um card?) sem nenhum caso real para validá-la.
```

**`docs/roadmap.md`** — a entrega, no formato das Sprints já registradas:

```markdown
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
```

**`docs/relatorio_funcionalidades.md`** — a funcionalidade, no formato das existentes:

```markdown
## Quadro Kanban do dashboard da empresa

| Item | Valor |
|---|---|
| **Rotas de admin** | `/private/admin/empresas/[id]/dashboard` · `/private/admin/dashboard-labels` · `/private/admin/templates` |
| **Rota de cliente** | `/private/client/quadro` (somente leitura) |
| **Endpoints** | `GET /dashboard/companies/{id}/board` · `POST /dashboard/companies/{id}/columns` · `PATCH|DELETE /dashboard/columns/{id}` · `PATCH /dashboard/columns/{id}/move` · `PATCH /dashboard/cards/{id}/move` · `PATCH /dashboard/cards/{id}` · `PUT /dashboard/cards/{id}/labels` · CRUD `/admin/dashboard-labels` · CRUD `/admin/templates/{id}/columns` |
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
```

**`docs/index.md`** — as três entradas novas:

```markdown
- [PRD — Quadro Kanban de Colunas e Cards](PRD.md) — requisito de produto, decisões de
  modelagem (D-1 a D-5), critérios de aceite (CA-01 a CA-31) e riscos.
- [Spec — Quadro Kanban de Colunas e Cards](Spec.md) — tradução técnica do PRD: árvore
  de arquivos, contrato de cada símbolo novo e o que muda em cada arquivo existente.
- [Code — Guia de Implementação Manual](Code.md) — o passo a passo, com o código
  completo de cada arquivo, na ordem em que ele compila.
```

---

## 4. Checklist final de verificação

### 4.1 Ordem de commits sugerida

Cada commit fica verde no CI antes do seguinte. É a sequência do PRD §9, com o
desdobramento de R1 (a refatoração do cliente do dashboard em dois passos):

| # | Commit | Fases | Verificação local |
|---|---|---|---|
| 1 | `chore(board): ignorar exports do Trello` | 0 | `git check-ignore -v "trello*.json"` |
| 2 | `feat(board): índice fracionário` | 1 | `pytest tests/test_fractional_index.py` |
| 3 | `feat(board): colunas, etiquetas e descrição no modelo` | 2 | `pytest tests/test_migration_board_backfill.py tests/test_migrations_smoke.py` + `alembic upgrade/downgrade/upgrade` |
| 4 | `feat(board): serviços e API de quadro` | 3, 4, 5 | `ruff check app && pytest --cov=app` |
| 5 | `refactor(dashboard): extrair painel de detalhe do card` | 7 (commit A) | `npm run test && npx tsc --noEmit` |
| 6 | `feat(board): quadro arrastável no admin` | 6, 7 (commit B) | `npm run lint && npm run test && npm run build` |
| 7 | `feat(board): quadro do cliente, etiquetas e colunas de template` | 8, 9, 10 | idem |
| 8 | `chore(board): importador do quadro Trello` | 11 | `--dry-run` sobre o export real |
| 9 | `docs: registrar a entrega do quadro` | 12 | — |

### 4.2 Portões do CI

Os quatro jobs de `.github/workflows/ci.yml` cobrem esta entrega **sem alteração no
workflow**. Rode-os localmente antes de abrir o PR:

```bash
# --- job `backend` ---
cd backend
ruff check app                                   # CA-26
pip-audit -r requirements.txt --ignore-vuln PYSEC-2026-1325
pytest --cov=app --cov-report=term-missing       # CA-28

# --- job `migrations` (exige o MySQL 8.4 no ar) ---
docker compose up -d
alembic upgrade head                             # CA-01
alembic downgrade base
alembic upgrade head
test "$(alembic heads | wc -l)" -eq 1

# --- job `frontend` ---
cd ../frontend
npm ci
npm run lint                                     # CA-27
npx next typegen && npx tsc --noEmit
npm run test                                     # CA-29
npm run build
npm audit --omit=dev                             # R4

# --- job `secrets` ---
git ls-files | grep -i "trello.*\.json" && echo "FALHA: export do Trello rastreado" || echo "OK"
```

### 4.3 Critérios de aceite — onde cada um é verificado

| CA | Verificado por |
|---|---|
| **CA-01** | Job `migrations` do CI (`upgrade → downgrade base → upgrade`) |
| **CA-02** | `test_migration_board_backfill.py::test_nenhum_card_fica_sem_coluna` e `::test_ordem_por_position_reproduz_a_ordem_por_sort_order` |
| **CA-03** | `test_migration_board_backfill.py::test_descricao_e_propagada_do_card_de_template_de_origem` |
| **CA-04** | `test_fractional_index.py` (19 testes) |
| **CA-05** | `test_dashboard_board.py::test_board_devolve_colunas_e_cards_ordenados_por_position` |
| **CA-06** | `test_dashboard_board.py::test_mover_card_executa_exatamente_um_update` + `test_query_budget.py::test_mover_card_nao_reescreve_a_coluna_inteira` |
| **CA-07** | `test_dashboard_board.py::test_mover_card_para_coluna_de_outra_empresa_devolve_404` |
| **CA-08** | `test_dashboard_board.py::test_excluir_coluna_com_card_visivel_devolve_409` / `::test_excluir_coluna_vazia_devolve_204` |
| **CA-09** | `test_dashboard_templates.py::test_aplicar_template_com_colunas_duas_vezes_e_idempotente` |
| **CA-10** | `test_dashboard_templates.py::test_aplicar_template_copia_a_descricao_para_o_card_da_empresa` |
| **CA-11** | `test_authorization_matrix.py` (8 rotas de escrita + `test_board_read_is_allowed_for_every_role`) |
| **CA-12** | `test_dashboard_labels.py::test_etiquetar_nao_altera_o_status_do_card` |
| **CA-13** | `test_query_budget.py::test_board_tem_custo_constante_em_queries` (5 e 20 colunas) |
| **CA-14** | `announcements` em pt-BR + `KeyboardSensor` em `board.tsx`; **verificação manual com leitor de tela** (ver §4.4) |
| **CA-15** | `move-card-menu.test.tsx` (5 testes) |
| **CA-16** | `board.test.tsx` (`moveCardInBoard`) + `actions.test.ts::devolve falha tratável para o otimismo reverter` |
| **CA-17** | `board.test.tsx::readOnly esconde todo controle de edição` + `board-column.test.tsx` |
| **CA-18** | `board-column.test.tsx` (coluna `SECTION`) + `move-card-menu.test.tsx::não oferece colunas do tipo SECTION` |
| **CA-19** | Filtro `showHidden` em `company-dashboard-client.tsx` + `test_dashboard_board.py::test_coluna_arquivada_so_aparece_com_include_hidden` |
| **CA-20** | `.board-scroller` / `.board-column-body` no `globals.css`; **verificação manual em 1280 px e 375 px** |
| **CA-21** | `board.test.tsx` (seleção em massa, colapsar coluna) |
| **CA-22 a CA-25** | `--dry-run` do importador sobre o export real (§ Fase 11) |
| **CA-26 a CA-29** | Os 4 jobs do CI |
| **CA-30** | `.gitignore` (Fase 0) |
| **CA-31** | Fase 12 |

### 4.4 Verificações que NÃO são automáticas

Três critérios exigem inspeção humana. Não delegue ao CI o que ele não mede:

1. **CA-14 — teclado e leitor de tela.** Com o quadro aberto: `Tab` até um card, `Espaço`
   para levantar, setas para mover, `Espaço` para soltar, `Esc` para cancelar. Cada passo
   tem de ser **anunciado em português** (é o que `announcements` em `board.tsx` produz).
   Teste com NVDA (Windows) ou VoiceOver (macOS).
2. **CA-20 — rolagem.** Abra o quadro com 22 colunas em **1280 px** e em **375 px**. O
   `body` não pode rolar horizontalmente; a rolagem lateral é do `.board-scroller` e a
   vertical é de dentro de cada `.board-column-body`.
3. **CA-22 a CA-25 — importação.** Rode o `--dry-run` e compare com a tabela de números
   medidos da Fase 11. `Descrições ainda com U+200C` tem de ser **0**.

### 4.5 Ensaio obrigatório antes do deploy (R3)

O backfill da migration é a parte irreversível desta entrega. Antes de aplicar em
produção:

```bash
# 1. Restaure uma CÓPIA do banco de produção num MySQL local.
# 2. Rode o upgrade contra a cópia:
cd backend
DATABASE_URL="mysql+pymysql://user:senha@127.0.0.1:3307/copia_producao" alembic upgrade head

# 3. Confira, na cópia, que nenhum quadro ficou vazio:
#    (o resultado das duas queries tem de ser 0)
```

```sql
-- Cards sem coluna em quadros que TINHAM cards:
SELECT COUNT(*) FROM dashboard_cards WHERE column_id IS NULL;

-- Cards sem position (o ALTER NOT NULL teria falhado, mas confirme):
SELECT COUNT(*) FROM dashboard_cards WHERE position IS NULL OR position = '';
```

```sql
-- E que a ordem visível não mudou, para um dashboard de amostra:
SELECT id, title, sort_order, position
  FROM dashboard_cards
 WHERE dashboard_id = <um id real>
 ORDER BY position ASC;
-- Compare com: ORDER BY sort_order ASC, id ASC
```

---

## 5. Divergências assumidas em relação à Spec

Estas são as decisões que este guia toma **diferente** do que a `Spec.md` descreve, cada
uma com o motivo. Nenhuma delas é preferência de estilo: todas vieram de ler o código ou
os dados reais.

### 5.1 `_card_is_outdated` não compara `column_id` com `template_column_id`

**Spec §3.2:** *"Passa a comparar também `column_id` vs `origin.template_column_id`"*.

Esses dois números vivem em **tabelas diferentes** — `dashboard_columns.id` e
`dashboard_template_columns.id`. Compará-los diretamente marcaria praticamente **todo**
card como desatualizado, e o selo "≠ template" perderia o significado no primeiro dia.

**O que este guia faz:** compara a **origem** da coluna atual do card
(`card.column.origin_template_column_id`) com `origin.template_column_id`. Semanticamente
é a pergunta certa — *"o card ainda está na coluna que o template manda?"* — e funciona
para card em coluna criada à mão (origem `NULL` ≠ coluna de template ⇒ desatualizado,
corretamente).

### 5.2 CA-04: 1 000 inserções no mesmo ponto **não** cabem em `String(64)`

**Spec §2.5:** *"1 000 inserções consecutivas no mesmo par mantêm ordem lexicográfica
estrita e não estouram `String(64)`"*.

As duas metades da frase não podem ser verdadeiras ao mesmo tempo, e o número foi
**medido**: no pior padrão (sempre inserir logo depois da mesma âncora) a chave cresce
~1 caractere a cada 5 inserções, e `String(64)` comporta exatamente **310**. A ordem
estrita, essa sim, vale para 1 000 e para qualquer número.

**O que este guia faz:** mantém `String(64)` como a Spec fixa, e desdobra CA-04 em quatro
testes que afirmam apenas o que é verdade — ordem estrita em 1 000 inserções no mesmo
ponto; comprimento ≤ 64 nos padrões reais (1 000 acréscimos no fim → 3 caracteres; 1 000
arrastos para posições variadas → 7); e uma barreira explícita em 300 inserções no pior
caso, com o limite documentado no módulo. Se algum dia for atingido, a correção é alargar
a coluna, não trocar o algoritmo.

### 5.3 `get_board` recebe o objeto `Dashboard`, não o `dashboard_id`

**Spec §2.2:** `get_board(db, dashboard_id, ...)`.

O router precisa de `dashboard.title` e `dashboard.company_id` para montar o `BoardOut`, e
já tem o objeto em mãos depois de resolver a empresa. Receber o id forçaria uma segunda
consulta ao mesmo registro — dentro de uma função cujo contrato é justamente custo
constante de queries (CA-13).

### 5.4 O export do Trello tem **22** listas abertas, não 25 — e 50 cards em listas arquivadas

**PRD §2 / CA-22:** *"25 abertas, 6 arquivadas"*, *"reporta 25 colunas"*.

Medido no arquivo real: **31 listas = 22 abertas + 9 arquivadas**. E, mais importante, as
listas arquivadas **não estão vazias**: guardam **50 dos 213 cards abertos** (23 % do
conteúdo). Ignorar listas e cards, como o PRD supunha, perderia esses 50 em silêncio.

**O que este guia faz:** listas arquivadas não viram coluna; os cards delas entram com
`template_column_id = NULL` e caem no balde "Sem coluna", contados e listados
explicitamente no `--dry-run`. `--skip-archived-list-cards` descarta-os — mas só por
decisão explícita do operador.

### 5.5 3 nomes de lista e 23 títulos de card estouram `String(160)`

Não previsto em nenhum dos dois documentos, e fatal para o importador: o INSERT falharia
no MySQL em modo estrito, no meio da importação. Medido: nome de lista até **264**
caracteres, título de card até **471**.

**O que este guia faz:** trunca em 160 com reticência visível e, para o card, **preserva o
título completo no início da `description`** — o texto longo é a redação normativa do
controle, e perdê-lo esvaziaria metade do valor do import. O `--dry-run` reporta quantos
foram truncados.

### 5.6 O teto de queries de `GET …/cards` sobe de 8 para 12

`list_cards_by_company` ganhou dois `selectinload` (`labels`, que é M:N, e `column`, lida
por `_card_is_outdated`). Cada um custa **uma** query fixa a mais — não uma por card. O
teto antigo reprovaria a rota por um custo que continua constante.

O teto novo continua sendo uma barreira real: um N+1 de verdade com 20 cards passaria de
40 queries.

### 5.7 `CompanyDeletionSummary` ganha `deleted_dashboard_columns`

**Spec §3.3** pede para *"conferir e acrescentar a contagem de colunas se for o caso"*. É
o caso: o resumo enumera o que foi removido, e uma entidade removida que não aparece nele
é uma exclusão silenciosa. O campo é aditivo (`= 0` por default), então nenhum consumidor
existente quebra.

### 5.8 Reordenação de coluna tem dois caminhos, não um

A Spec descreve o arrasto horizontal de colunas via `SortableContext`. Este guia entrega
**os dois**: o arrasto (com `restrictToHorizontalAxis` disponível em `@dnd-kit/modifiers`)
e um par de botões `←` / `→` no cabeçalho de cada coluna, com `aria-label` explícito.

O motivo é o mesmo de CA-15 para cards: um quadro cuja única forma de reordenar é o
arrasto não é operável por teclado nem em tablet. Os dois caminhos chamam exatamente a
mesma `moveColumnAction`.

### 5.9 `frontend/app/private/client/client-dashboard-client.tsx` fica intocado

Já registrado como divergência na própria `Spec.md` (§2.4.3), e repetido aqui porque é a
diferença mais fácil de esquecer na hora de codar: aquele arquivo renderiza `AuditControl`
vindo de `GET /api/v1/client/controls` — domínio de auditoria. A visão de quadro do
cliente é a **rota nova** `/private/client/quadro`.

---

## Encerramento

Ao terminar as 12 fases você terá:

| | Backend | Frontend |
|---|---|---|
| **Arquivos novos** | 9 (2 models/serviços, 2 schemas, 2 routers, 1 migration, 1 script, 4 testes) | 18 (5 componentes, 3 testes de componente, 2 rotas completas, 1 lib + teste) |
| **Arquivos modificados** | 14 | 8 |
| **Endpoints novos** | 13 | — |
| **Dependências novas** | 0 | 3 (`@dnd-kit`, versão fixa) |
| **Testes novos** | ~70 | ~45 |

E as quatro coisas que o quadro-modelo real exigia e a plataforma não tinha: **coluna**
por quadro, **posição** manual com um `UPDATE` por arrasto, **descrição** normativa do
controle e **etiqueta** de criticidade — sem que nenhuma rota existente mude de contrato,
e sem que nenhum teste existente precise ser removido ou marcado `skip`.
