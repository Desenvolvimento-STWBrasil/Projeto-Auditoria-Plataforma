# Automação de Relatório de Commits — GitHub Actions

| Campo | Valor |
|---|---|
| **Versão** | 4.0 — **2026-08-26** |
| **Status** | ✅ Implementada e corrigida · ✅ **executou de verdade em 2026-08-26** — dois pushes em `main`, 44 → **46 entradas**, com commit e push de volta e `[skip ci]` funcionando |
| **Arquivos** | `.github/workflows/commit-report.yml` · `.github/scripts/generate_commit_report.py` · `docs/relatorio_commit.md` (gerado) |
| **Dependências** | Nenhuma. O script usa só a stdlib do Python (`re`, `subprocess`, `sys`, `pathlib`) |

---

## O problema que esta automação resolve

Uma mensagem de commit descreve **o que o autor pretendia**. O relatório descreve **o que o commit efetivamente tocou** — quais arquivos, quais funcionalidades, quantas linhas, que achados de bug foram citados, que `TODO` foram introduzidos. Os dois divergem com frequência, e a divergência é justamente onde mora o problema.

O relatório é **derivado do git**, nunca escrito à mão. Isso o torna verificável: qualquer afirmação nele pode ser conferida com `git show`.

---

## 🔴 O que estava errado até esta revisão

A automação existia desde 2026-08-11 e **quase não rodou**. Diagnóstico feito nesta revisão:

| # | Problema | Evidência | Consequência |
|---|---|---|---|
| 1 | **O gatilho não cobre onde o trabalho acontece** | O workflow dispara em `push: branches: [main]`, mas todo o desenvolvimento vive em `fix/audit-repository-refactor-and-regressions` | **19 commits sem entrada** entre `6b4f0a3` (2026-08-11) e `66578f0` (2026-08-24), incluindo o BLOCO O inteiro |
| 2 | **Não havia como reprocessar** | O script só lia `HEAD` | Um commit perdido estava perdido para sempre |
| 3 | **`_split_entries` fragmentava o arquivo** | Dividia por `"\n---\n"`, que também casa com régua horizontal **dentro** de uma entrada | A contagem de `MAX_ENTRIES` ficava distorcida; entradas longas podiam ser cortadas ao meio |
| 4 | **N subprocessos git por commit** | `find_new_todos` rodava `git show <ref> -- <file>` **por arquivo** | No commit do BLOCO O (54 arquivos, +15.076 linhas), 54 diffs completos relidos do zero |
| 5 | **Merge commits eram ignorados** | `git diff-tree` sem `-m` devolve saída vazia num merge | Todo merge produzia "nenhum arquivo alterado" e era pulado |
| 6 | **Quebrava no Windows** | Mensagens com `→` e emoji contra console cp1252 | `UnicodeEncodeError` antes de fazer qualquer trabalho — impedia teste local |
| 7 | **`push` sem `pull --rebase`** | Push direto após o commit | Um push concorrente na `main` fazia o job falhar e a entrada se perder |
| 8 | **`FEATURE_MAP` defasado** | Sem `dashboard_categories.py`, `dashboard_templates.py`, `companies.py`, `company_messages.py`, `empresas/`, `templates/`; com prefixos mortos (`frontend/middleware.ts`, `app/api/sub-users/`, `/client/`, `/profile/` — removidos em I.2) | Módulos novos caíam em "Outro / Não Categorizado" |

**Todos os 8 foram corrigidos**, e o backfill dos 19 commits foi executado: `docs/relatorio_commit.md` passou de **22** para **41** entradas, sem duplicatas e em ordem cronológica decrescente.

---

## Arquitetura

```
┌────────────────────────────────────────────────────────────────┐
│  push na main            OU        workflow_dispatch           │
│  (paths-ignore:                    (com backfill_range          │
│   docs/relatorio_commit.md)         opcional)                   │
└───────────────────────────┬────────────────────────────────────┘
                            ▼
              ┌─────────────────────────────┐
              │ actions/checkout@v4         │
              │ fetch-depth: 0  ← histórico │
              └─────────────┬───────────────┘
                            ▼
              ┌─────────────────────────────┐
              │ generate_commit_report.py   │
              │                             │
              │  git log -1     → metadados │
              │  git diff-tree  → arquivos  │
              │  git show       → TODOs     │
              │  git show       → +/− linhas│
              │        │                    │
              │        ▼                    │
              │  FEATURE_MAP  → funcionalid.│
              │  COMMIT_TYPES → tipo/emoji  │
              │  PATH_ALERTS  → verificações│
              │        │                    │
              │        ▼                    │
              │  prepend em relatorio_commit│
              └─────────────┬───────────────┘
                            ▼
              ┌─────────────────────────────┐
              │ git diff --quiet ?          │
              │  não mudou → termina        │
              │  mudou     → commit + push  │
              │              [skip ci]      │
              └─────────────────────────────┘
```

### Proteção contra loop infinito — três camadas

O bot faz commit de um arquivo que está no próprio repositório. Sem cuidado, isso dispara o workflow de novo, indefinidamente.

1. **`paths-ignore: docs/relatorio_commit.md`** — se o push só tocou o relatório, o workflow nem começa.
2. **`[skip ci]` na mensagem de commit** — convenção reconhecida pelo GitHub Actions, que pula a execução.
3. **`concurrency` com `cancel-in-progress: false`** — duas execuções não fazem push concorrente no mesmo arquivo. Não cancela a anterior de propósito: ela precisa terminar o push, senão a entrada se perde.

A camada 1 basta; as outras duas existem porque o custo de um loop infinito num repositório é alto e o custo de três linhas de YAML é zero.

---

## Código: `.github/workflows/commit-report.yml`

```yaml
name: Relatório de Commits

# Dispara a cada push na branch main.
#
# paths-ignore impede loop infinito: quando o próprio bot atualiza o
# relatório, o commit gerado não redispara este workflow.
#
# workflow_dispatch permite rodar sob demanda, inclusive em modo backfill —
# necessário porque todo trabalho feito em branch de feature fica sem entrada
# até o merge na main (foi assim que 19 commits acumularam sem registro entre
# 2026-08-11 e 2026-08-24).
on:
  push:
    branches: [main]
    paths-ignore:
      - "docs/relatorio_commit.md"
  workflow_dispatch:
    inputs:
      backfill_range:
        description: 'Intervalo git para backfill (ex.: "abc1234..HEAD"). Vazio = só o HEAD.'
        required: false
        default: ""

# Permissão de escrita para que o bot possa dar push do relatório
permissions:
  contents: write

# Duas execuções simultâneas fariam push concorrente no mesmo arquivo.
# Serializa por branch; não cancela a anterior (ela precisa terminar o push).
concurrency:
  group: commit-report-${{ github.ref }}
  cancel-in-progress: false

jobs:
  generate-commit-report:
    name: Gerar Entrada no Relatório de Commits
    runs-on: ubuntu-latest

    steps:
      # fetch-depth: 0 — o script usa git log/diff-tree/show sobre o histórico
      - name: Checkout do repositório (histórico completo)
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{ secrets.GITHUB_TOKEN }}

      # Python 3.12 — o script usa apenas a stdlib (re, subprocess, pathlib)
      - name: Configurar Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Configurar identidade do bot no Git
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

      # Modo normal (push): processa só o HEAD.
      - name: Gerar entrada do commit atual
        if: github.event_name == 'push' || inputs.backfill_range == ''
        run: python .github/scripts/generate_commit_report.py

      # Modo backfill (workflow_dispatch com intervalo): reconstrói o histórico.
      # O script pula commits que já têm entrada, então é seguro repetir.
      - name: Backfill do intervalo informado
        if: github.event_name == 'workflow_dispatch' && inputs.backfill_range != ''
        run: python .github/scripts/generate_commit_report.py --backfill "${{ inputs.backfill_range }}"

      - name: Verificar se o relatório foi atualizado
        id: check_changes
        run: |
          if git diff --quiet "docs/relatorio_commit.md"; then
            echo "changed=false" >> "$GITHUB_OUTPUT"
            echo "-> Nenhuma alteração no relatório."
          else
            echo "changed=true" >> "$GITHUB_OUTPUT"
            echo "-> Relatório atualizado, realizando commit."
          fi

      # `pull --rebase` antes do push: entre o checkout e este passo alguém
      # pode ter feito push na main. Sem isso, o push falha e a entrada é
      # perdida silenciosamente (o job fica vermelho, mas ninguém reprocessa).
      # [skip ci] é a segunda camada contra loop, além do paths-ignore.
      - name: Commit e push do relatório atualizado
        if: steps.check_changes.outputs.changed == 'true'
        run: |
          git add "docs/relatorio_commit.md"
          git commit -m "docs(report): atualizar relatorio_commit.md para ${{ github.sha }} [skip ci]"
          git pull --rebase --autostash origin "${GITHUB_REF_NAME}"
          git push origin "HEAD:${GITHUB_REF_NAME}"
```

---

## Código: `.github/scripts/generate_commit_report.py`

O arquivo completo está no repositório. As partes que carregam decisão de projeto:

### Guarda de encoding (correção nº 6)

```python
# O console do Windows usa cp1252 por padrão, que não codifica as setas e
# emojis usados nas mensagens de progresso — sem isto, rodar o script
# localmente no Windows morre com UnicodeEncodeError antes de fazer
# qualquer trabalho. No runner Linux do GitHub Actions já é UTF-8.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
```

Sem isso, a automação **não pode ser testada localmente na máquina onde o projeto é desenvolvido** — o que explica boa parte de por que os outros 7 defeitos sobreviveram tanto tempo.

### Merge commits (correção nº 5)

```python
def get_changed_files(ref: str = "HEAD") -> list[tuple[str, str]]:
    """
    Retorna [(status, filepath)]. Status: A/M/D/R.

    `-m --first-parent` faz merge commits reportarem o diff contra o primeiro
    pai em vez de não reportarem nada (o padrão de `diff-tree` num merge é
    saída vazia, o que fazia a Action pular merges silenciosamente).
    """
    raw = git([
        "diff-tree", "--no-commit-id", "-r", "-m", "--first-parent",
        "--name-status", ref,
    ])
    ...
```

`-m` faz o diff-tree emitir um diff por pai; `--first-parent` restringe ao pai da branch de destino — que é o que interessa num merge de PR. O `seen` set evita listar o mesmo arquivo duas vezes.

### Um único `git show` (correção nº 4)

```python
def find_new_todos(ref: str, changed_files: list[tuple[str, str]]) -> list[str]:
    """
    Linhas +TODO/+FIXME/+HACK/+XXX adicionadas neste commit.

    Faz UM único `git show` e atribui cada linha ao arquivo corrente do diff.
    A versão anterior rodava um subprocesso git POR ARQUIVO — num commit como
    o do BLOCO O (54 arquivos, +15.076 linhas) isso significava 54 diffs
    completos, cada um relido do zero.
    """
    interesting = {
        fp for st, fp in changed_files
        if st != "D" and Path(fp).suffix.lower() in TEXT_EXTENSIONS
    }
    if not interesting:
        return []

    diff = git(["show", "--unified=0", "--format=", ref])
    todos: list[str] = []
    current: str | None = None

    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:].strip()
            continue
        ...
```

`--unified=0` elimina as linhas de contexto: só as adicionadas de fato chegam ao parser.

### Separação correta de entradas (correção nº 3)

```python
ENTRY_SPLIT = re.compile(r"^---\n\n(?=## Commit `)", re.MULTILINE)


def _split_entries(body: str) -> list[str]:
    """
    Separa as entradas existentes.

    Cada entrada começa com "---\n\n## Commit `<sha>`". A versão anterior
    dividia por "\n---\n", que também casa com qualquer régua horizontal
    DENTRO de uma entrada (o corpo de um commit pode ter uma), fragmentando
    entradas e distorcendo a contagem de MAX_ENTRIES.
    """
    parts = ENTRY_SPLIT.split(body)
    return [p for p in (part.strip() for part in parts) if p.startswith("## Commit `")]
```

O *lookahead* `(?=## Commit \`)` é o que amarra a régua ao cabeçalho da entrada, em vez de tratar qualquer `---` como separador.

### Idempotência do backfill (correção nº 2)

```python
def entry_exists(short_hash: str) -> bool:
    """True se já existe uma entrada para este commit (evita duplicar no backfill)."""
    if not REPORT_PATH.exists():
        return False
    return f"## Commit `{short_hash}`" in REPORT_PATH.read_text(encoding="utf-8")
```

E, no laço de backfill, a ordem importa:

```python
        # `git log` sai do mais novo para o mais antigo. Processamos do mais
        # ANTIGO para o mais novo porque cada entrada é inserida no topo —
        # assim o resultado final fica em ordem cronológica decrescente.
        revs = git(["log", "--format=%H", "--reverse", backfill_range]).splitlines()
```

### Alertas por caminho tocado `🆕`

Novo nesta versão. Cada entrada agora traz uma seção **"Verificações Recomendadas"**, disparada pelos caminhos que o commit tocou. São lembretes de verificações que a suíte de testes **não** faz:

```python
PATH_ALERTS: dict[str, str] = {
    "backend/alembic/versions/": (
        "⚠️ **Migration alterada.** A suíte usa `Base.metadata.create_all` e **não** "
        "executa migrations (ver M-18 em `docs/relatorio_melhorias.md`) — uma suíte verde "
        "não prova que a migration roda. Execute `alembic upgrade head` contra o MySQL real "
        "e confirme `alembic heads` com um único head."
    ),
    "backend/app/api/": (
        "⚠️ **Endpoint alterado.** Confirme a dependência de autorização: posse "
        "(`_get_*_with_access`) não é permissão. Ver **B-A23** em `docs/relatorio_bugs.md`."
    ),
    "backend/.env.example": (
        "🔴 **Arquivo de configuração versionado.** Nenhum valor real pode entrar aqui — "
        "ver **B-C23** em `docs/relatorio_bugs.md`."
    ),
    "backend/README.md": (
        "🔴 **Documentação versionada.** Nenhuma credencial em texto claro — ver **B-C23**."
    ),
}
```

Cada alerta nasceu de um incidente real deste projeto. Não são boas práticas genéricas: são as formas específicas pelas quais este repositório já foi mordido.

### ⚠️ Manutenção pendente do `PATH_ALERTS` `🆕 v3.0`

Os alertas acima citam **B-A23** e **B-C23**, e os dois foram **fechados** pelo BLOCO P. O texto continua correto como orientação (posse não é permissão; nada de valor real no `.env.example`), mas apontar para um achado encerrado envelhece mal: quem seguir o link encontra um item riscado.

Mais importante, faltam alertas para as classes de defeito que a auditoria da rev. 9.0 encontrou. Proposta de atualização:

```python
PATH_ALERTS: dict[str, str] = {
    "backend/alembic/versions/": (
        "⚠️ **Migration alterada.** A suíte usa `Base.metadata.create_all` e **não** "
        "executa migrations pelo caminho normal. O job `migrations` do CI cobre isso "
        "(M-18) — confirme que ele passou e que `alembic heads` tem um head único."
    ),
    "backend/app/api/": (
        "⚠️ **Endpoint alterado.** Duas perguntas: (1) a **escrita** passa por "
        "`core/policy.py`? (2) a **leitura** devolve algum campo que este papel não "
        "deveria ver? A segunda é B-A28 — a matriz de autorização cobre escrita, "
        "não leitura."
    ),
    "backend/app/core/policy.py": (
        "🔴 **Política de autorização alterada.** É a regra de negócio central da "
        "plataforma (quem declara conformidade). Toda mudança aqui precisa de uma "
        "linha correspondente em `tests/test_authorization_matrix.py`."
    ),
    "backend/app/core/security.py": (
        "⚠️ **Hash de senha alterado.** O bcrypt recusa entrada acima de 72 bytes "
        "(B-A27). Confirme que o limite continua tratado explicitamente e que "
        "`tests/test_password_limits.py` passa."
    ),
    "backend/app/services/email_sender.py": (
        "⚠️ **Envio de e-mail alterado.** Nenhuma falha de SMTP pode propagar para "
        "uma transação já committada, e a senha temporária não pode ser a única "
        "cópia de uma credencial (B-A29). Verifique o retorno booleano."
    ),
    "backend/app/services/storage.py": (
        "⚠️ **Storage alterado.** A guarda de path traversal pertence a "
        "`get_absolute_path()`, o ponto único — não ao consumidor (B-M28)."
    ),
    "backend/app/middleware/security_headers.py": (
        "⚠️ **Cabeçalhos de segurança alterados.** `tests/test_security_headers.py` "
        "varre o HTML real de /docs e /redoc. Se o teste passar mas a página "
        "renderizar em branco, o teste está fazendo a pergunta errada (defeito #14)."
    ),
    "backend/app/core/config.py": (
        "⚠️ **Configuração alterada.** Default novo é decisão de segurança: acrescente "
        "a asserção em `tests/test_config_defaults.py` (B-M25/B-M29). Se a variável "
        "também existe no frontend, os dois defaults precisam coincidir."
    ),
    "backend/.env.example": (
        "🔴 **Arquivo de configuração versionado.** Nenhum valor real pode entrar aqui. "
        "O job `secrets` do CI roda gitleaks — mas confirme antes de commitar."
    ),
    "backend/README.md": (
        "🔴 **Documentação versionada.** Nenhuma credencial em texto claro. E confira "
        "se a alteração não diverge de `docs/setup_completo.md` — duas fontes de "
        "verdade para o mesmo procedimento produziram RD-02, RD-03 e RD-04."
    ),
}
```

**Esforço:** 20 min. **Impacto:** o alerta é a única parte desta automação que fala diretamente com quem revisa o PR — mantê-lo alinhado com os achados atuais é o que o torna útil em vez de ruído.

---

## Estrutura da entrada gerada

Cada commit vira um bloco com esta forma exata (exemplo real, do commit do BLOCO O):

```markdown
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
### Descrição
### Arquivos Modificados (54 arquivo(s))
### Funcionalidades Impactadas
### Correções Realizadas
### Verificações Recomendadas
### Pendências Identificadas
### Próximos Passos Recomendados
```

| Seção | Origem do dado |
|---|---|
| **Cabeçalho** | `git log -1 --format=%H%h%an%ae%cd%s%b` |
| **Linhas +/−** | `git show --numstat` |
| **Arquivos Modificados** | `git diff-tree --name-status -m --first-parent`, com status traduzido (A/M/D/R → Adicionado/Modificado/Removido/Renomeado) |
| **Funcionalidades Impactadas** | Cada caminho passa por `FEATURE_MAP` (prefixo mais longo vence) e o conjunto é deduplicado |
| **Correções Realizadas** | Regex `B-[CAMB]\d{2}` e `RD-\d{2}` sobre título + corpo do commit |
| **Verificações Recomendadas** | `PATH_ALERTS`, disparado pelos prefixos tocados |
| **Pendências Identificadas** | Linhas `+TODO/FIXME/HACK/XXX` do diff + seção `Pendências:` do corpo do commit |
| **Próximos Passos** | `NEXT_STEPS_BY_TYPE`, indexado pelo tipo do Conventional Commit |

### Tipos de commit reconhecidos

| Prefixo | Label | Emoji |
|---|---|---|
| `feat` | Nova Funcionalidade | 🚀 |
| `fix` | Correção de Bug | 🐛 |
| `docs` | Documentação | 📝 |
| `refactor` | Refatoração | ♻️ |
| `chore` | Manutenção / Configuração | 🔧 |
| `test` | Testes | ✅ |
| `perf` | Melhoria de Performance | ⚡ |
| `style` | Estilo / Formatação | 🎨 |
| `ci` | CI/CD | 🤖 |
| `build` | Build / Dependências | 📦 |
| `revert` | Reversão de Commit | ⏪ |
| *(outro)* | Alteração Geral | 📌 |

Um commit que não siga Conventional Commits vira "Alteração Geral" — não é erro, só perde a granularidade de "Próximos Passos".

---

## Como usar

### Rodar localmente (teste, antes de confiar no CI)

```bash
# Entrada do HEAD, com preview no terminal
python .github/scripts/generate_commit_report.py --local

# Um commit específico
python .github/scripts/generate_commit_report.py --ref 94873ec

# Backfill de um intervalo (idempotente — pula o que já tem entrada)
python .github/scripts/generate_commit_report.py --backfill 6b4f0a3..HEAD
```

> ⚠️ O script **escreve** em `docs/relatorio_commit.md`. Rodar localmente altera o arquivo — revise com `git diff` antes de commitar. Se algo der errado, `git checkout docs/relatorio_commit.md` desfaz.

### Rodar sob demanda no GitHub

**Actions → Relatório de Commits → Run workflow**, e opcionalmente preencher `backfill_range` (ex.: `6b4f0a3..HEAD`).

### Ao adicionar um módulo novo ao projeto

Acrescente uma linha ao `FEATURE_MAP`. É o único ponto de manutenção do script:

```python
FEATURE_MAP: dict[str, str] = {
    ...
    "backend/app/api/v1/meu_modulo_novo.py": "Nome Legível da Funcionalidade",
}
```

Sem isso, o arquivo cai em "Outro / Não Categorizado" — funciona, mas o relatório perde a informação mais útil que ele tem.

---

## Limitações conhecidas

| Limitação | Impacto | Contorno |
|---|---|---|
| **Só dispara na `main`** | Trabalho em branch de feature não gera entrada até o merge | Rodar `workflow_dispatch` com backfill depois do merge |
| **`MAX_ENTRIES = 50`** | Entradas além da 50ª são descartadas | O histórico completo está no git; o relatório é uma janela recente. Aumentar o limite se necessário |
| ~~**Nunca executou de verdade**~~ | ✅ **Resolvido em 2026-08-26.** O workflow rodou em dois pushes na `main`, gerou as entradas dos merges dos PRs #1 e #2, e fez push de volta sem disparar a si mesmo | — |
| **`PATH_ALERTS` cita achados já fechados** | Quem seguir o link encontra item encerrado | Aplicar a atualização proposta na seção "Manutenção pendente" |
| **`FEATURE_MAP` é manual** | Módulo novo sem entrada vira "Não Categorizado" | Um teste que falhe quando um arquivo em `backend/app/api/v1/*.py` não estiver mapeado resolveria — não implementado |
| **Não valida a mensagem de commit** | Commit fora do padrão perde granularidade | Um hook `commit-msg` com `commitlint` seria o complemento natural |

---

## Estado atual do relatório gerado

| Métrica | v1.0 | v2.0 (2026-08-24) | **v3.0 (2026-08-26)** |
|---|---|---|---|
| Entradas em `docs/relatorio_commit.md` | 22 | 41 | **44** |
| Commit mais recente coberto | `df7cd65` | `66578f0` | **`34f8444`** |
| Commits do histórico sem entrada | 19 | 0 | **0** |
| Linhas do arquivo | — | 4.733 | **5.136** |
| Duplicatas | — | 0 | **0** |

O backfill desta revisão cobriu os três commits que entraram desde a v2.0 —
`4fd576f` (BLOCO P), `9e3076f` (docs rev. 8.0) e `34f8444` (correção do CSP):

```bash
python .github/scripts/generate_commit_report.py --backfill 66578f0..HEAD
```

Saída real:

```
-> Backfill de 3 commit(s) em '66578f0..HEAD'
-> 4fd576f |  36 arquivo(s) | fix(security): BLOCO P - autorizacao, retencao de arquivo, v
-> 9e3076f |  21 arquivo(s) | docs: auditoria adversarial rev. 8.0 e sincronizacao da past
-> 34f8444 |   3 arquivo(s) | fix(api): CSP uniforme deixava o Swagger em branco (B-M21, d
OK Backfill concluido: 3 entrada(s) nova(s).
```

Verificação executada após o backfill:

```bash
grep -c "^## Commit " docs/relatorio_commit.md                 # 44
grep "^## Commit " docs/relatorio_commit.md | sort | uniq -d   # vazio
```

> **Observação sobre o modo backfill.** Rodá-lo uma segunda vez no mesmo
> intervalo devolve `0 entrada(s) nova(s)` — a guarda de idempotência
> (`entry_exists`, correção nº 2 da v2.0) foi exercitada de novo nesta
> revisão e funcionou. É a única parte desta automação verificada por
> execução repetida.

---

## Relação com os outros documentos

| Documento | Relação |
|---|---|
| `docs/relatorio_commit.md` | **Saída** desta automação — gerado, não editado à mão |
| `docs/relatorio_bugs.md` | Fonte dos IDs `B-X00`/`RD-00` que a seção "Correções Realizadas" detecta |
| `docs/relatorio_melhorias.md` | Origem dos alertas de `PATH_ALERTS` (M-18) |
| `docs/trello_automacao.md` | Automação irmã — move cards a partir dos mesmos eventos de commit/PR |
| `.github/workflows/ci.yml` | Workflow separado (lint + testes + build); compartilha só o gatilho |

---

*Documento atualizado em 2026-08-26 (v3.0). O backfill de `66578f0..HEAD` foi executado nesta revisão e verificado: **44 entradas, 0 duplicatas, commit mais recente `34f8444`**. A guarda de idempotência foi exercitada rodando o backfill duas vezes no mesmo intervalo. O workflow em si segue sem execução real contra um push na `main` — é o **Sprint A5** do `roadmap.md`: uma hora de trabalho que valida esta automação e as outras quatro barreiras do BLOCO P de uma vez.*
