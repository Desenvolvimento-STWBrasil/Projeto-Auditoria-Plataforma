# Relatório de Bugs e Auditoria Técnica — Plataforma de Auditoria

| Campo | Valor |
|---|---|
| **Data da Análise** | 2026-06-24 (criação) · 2026-07-27 (rev. 2.0) · 2026-08-11 (rev. 3.0) · 2026-08-12 (rev. 4.0) · 2026-08-17 (rev. 5.0) · 2026-08-17 (rev. 6.0) · 2026-08-24 (rev. 7.0) · 2026-08-24 (rev. 8.0) · **2026-08-26 (rev. 9.0 — esta revisão)** |
| **Versão** | 10.0 |
| **Branch / HEAD** | `main` · `c769526` (a branch de trabalho foi mergeada nos PRs #1 e #2) |
| **Metodologia** | Leitura integral do código-fonte + **verificação empírica**: `pytest -q` (**202 passed**), `ruff check app scripts tests` (limpo), `npx tsc --noEmit` (exit 0), `npx eslint` (exit 0), `alembic heads` (head único `b7c02e91d4a5`), enumeração de rotas via `app.openapi()` (64 operações) e **13 sondas executáveis** escritas especificamente para confirmar ou refutar cada hipótese de defeito — incluindo contagem de queries SQL por requisição |
| **Relatórios Consultados** | `docs/relatorio_geral.md` (rev. 9.0), `docs/relatorio_funcionalidades.md` (rev. 9.0), `docs/plano_implementacao.md` (BLOCOS O a S) |
| **Escopo** | Backend Python/FastAPI, Frontend Next.js/TypeScript, MySQL, migrações Alembic, scripts de seed, automação GitHub Actions, documentação operacional versionada |

---

## ✅ Estado em 2026-08-26 (fim do dia) — 19 achados levantados, 19 corrigidos

> **Rev. 10.0.** Os 15 achados da auditoria de leitura/sonda foram corrigidos (BLOCOS Q e R), e a
> **primeira execução real do `ci.yml`** revelou outros **4** — `B-A30`, `B-A31`, `B-M30` e
> `B-M31`, detalhados na seção seguinte. Os 4 também estão corrigidos, e o CI está **verde nos 4
> jobs** em `main`.

### Os 15 achados da auditoria de 2026-08-26

Os achados abaixo foram **levantados e corrigidos no mesmo dia**. O BLOCO Q
(`docs/plano_implementacao.md`) aplicou Q.1–Q.5 e a suíte foi de **202 para 250 testes**.

| Faixa | Levantados | Corrigidos | Em aberto |
|---|---|---|---|
| 🔴 Crítica | 0 | — | **0** |
| 🟠 Alta | 3 | **3** (B-A27, B-A28, B-A29) | **0** |
| 🟡 Média | 5 | **5** (B-M25, B-M26, B-M27, B-M28, B-M29) | **0** |
| 🟢 Baixa | 7 | **7** (B-B17..B-B23) | **0** |

**Os 15 achados estão fechados.** **B-M26** foi o último, corrigido no **BLOCO R** junto com
**M-25**, e na ordem que o plano exigia: a barreira primeiro. Ela reprovou o código antigo com
**38 queries para 5 empresas e 143 para 20** — linear — e passou a aprovar **8 queries
constantes** para 5, 20 e 50.

> **Sobre a aplicação.** Ela não foi limpa: **6 defeitos** apareceram na verificação, três deles
> da mesma família registrada em P.7 (*código correto no lugar errado*) — incluindo um que
> impedia a aplicação de inicializar, e um em que a correção de B-M28, na primeira versão,
> deixou a resolução de caminho **mais permissiva** do que o código que vinha corrigir. O
> relatório completo está em **Q.7** do plano de implementação.
>
> As 5 barreiras foram verificadas **por reversão** — cada correção desfeita individualmente
> para confirmar que o teste correspondente falha sem ela. Uma delas (B-M28) passava nas duas
> versões, porque o caminho malicioso do teste não existia nesta máquina: a barreira media o
> sistema de arquivos, não a guarda. Foi reescrita.

---

## 🔬 Rev. 10.0 — os 4 defeitos que só a execução real do CI revelou

Esta seção é diferente de todas as anteriores. Os achados abaixo **não foram encontrados por
leitura, nem por sonda escrita à mão**. Eles apareceram quando o `ci.yml` executou pela primeira
vez, em 2026-08-26, depois do merge do PR #1 — o que registrou o workflow no branch padrão.

Dos 4 jobs, **3 reprovaram**. Cada reprovação era um defeito real.

| ID | Achado | Job | Despercebido por |
|---|---|---|---|
| 🟠 **B-A30** | **A cadeia de `alembic downgrade` nunca funcionou** — 6 migrations, 3 causas | `migrations` | até **3 meses** |
| 🟠 **B-A31** | **9 CVEs**, sendo **7 no `python-multipart`** — o parser do upload de evidências | `backend` | desde que a versão foi fixada |
| 🟡 **B-M30** | O job `backend` **não tinha variáveis de ambiente** — morria antes do 1º teste | `backend` | **2 meses e meio** |
| 🟡 **B-M31** | `tsc --noEmit` reprovava código correto por falta dos tipos gerados pelo Next | `frontend` | desde sempre |

### Por que nenhuma verificação local os alcançava

Este é o ponto que dá sentido à seção inteira: **cada conveniência do ambiente local escondia um
defeito.**

| Conveniência local | O que ela escondia |
|---|---|
| A suíte usa SQLite com `Base.metadata.create_all` | O SQLite não impõe a restrição de FK do MySQL — nenhum teste exercitava `alembic downgrade` |
| `backend/.env` existe na máquina do dev | O job de CI não tem `.env` (é gitignored), e `Settings` exige `DATABASE_URL` e `JWT_SECRET` |
| `.next/` sobra de builds anteriores | Os tipos `PageProps`/`LayoutProps`/`RouteContext` são **gerados**; num runner limpo não existem |
| `pip-audit` nunca havia rodado | 9 CVEs acumuladas sem ninguém olhar |

Nenhum desses é descuido de quem escreveu o código. São **diferenças estruturais entre a máquina
de desenvolvimento e o ambiente de destino** — que é exatamente o que um CI existe para expor, e
exatamente o que ele não pode expor enquanto não roda.

---

## B-A30 — A cadeia de `alembic downgrade` nunca funcionou `✅ corrigido`

**Categoria:** Data Integrity · Improper Rollback (**CWE-1265**)

### Sintoma

```
sqlalchemy.exc.OperationalError: (pymysql.err.OperationalError)
(1553, "Cannot drop index 'ix_dashboard_cards_origin_template_card_id':
        needed in a foreign key constraint")
```

`alembic downgrade base` parava na primeira migration com esse padrão. Corrigida ela, parava na
seguinte. **Seis migrations afetadas, por três causas distintas** — mais um defeito pré-existente
independente.

### As três causas

| # | Causa | Onde |
|---|---|---|
| **1** | `DROP INDEX` **antes** de `DROP CONSTRAINT`. O MySQL exige um índice para cada FK e recusa removê-lo enquanto a constraint existir | `4f2b8e6a91d3` |
| **2** | `drop_index` **redundante** antes de `drop_table` — o `drop_table` já remove os índices, e os explícitos só quebravam a cadeia | `9d5a3c1b2e77`, `bf7239a52df8` |
| **3** | Índices que **sustentam FK** sendo removidos (e recriados) em downgrades | `447a4e1de59d`, `56d322bbd83a`, `86f95e525db1`, `d5c4d7cd6687`, `d60f999c1fca`, `eafa65e9df05` |

### E um quarto defeito, independente e mais antigo

`447a4e1de59d` (21/05/2026) trazia, no downgrade:

```python
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'users', type_='foreignkey')
```

O autogenerate escreveu `None` no lugar do nome da constraint, com o comentário *"please
adjust!"* — e ninguém ajustou. O resultado é `AssertionError: name is not None`, tornando a
migration **irreversível desde que foi escrita**.

O nome real (`users_ibfk_1`) é atribuído pelo MySQL e **varia entre bancos** conforme a ordem de
criação, então não pode ser fixado no código.

### Impacto

Um rollback de schema em produção — o procedimento de emergência para uma migration que dá
errado — **não funcionava**. E ninguém sabia, porque a única coisa que exercita esse caminho é
executar `alembic downgrade` contra um MySQL de verdade.

### Correção

Guardas **autocontidas** em cada migration, resolvidas via `information_schema`:

```python
def _index_backs_foreign_key(conn, index_name: str, table_name: str) -> bool:
    """True se alguma FOREIGN KEY desta tabela depende deste índice."""
    return (
        conn.execute(
            _sa_text(
                "SELECT COUNT(*) "
                "FROM information_schema.key_column_usage kcu "
                "JOIN information_schema.statistics s "
                "  ON s.table_schema = kcu.table_schema "
                " AND s.table_name   = kcu.table_name "
                " AND s.column_name  = kcu.column_name "
                "WHERE kcu.table_schema = DATABASE() "
                "  AND kcu.table_name = :tbl "
                "  AND kcu.referenced_table_name IS NOT NULL "
                "  AND s.index_name = :idx"
            ),
            {"tbl": table_name, "idx": index_name},
        ).scalar()
        or 0
    ) > 0


def _drop_index_if_safe(index_name: str, table_name: str) -> None:
    """Remove o índice só se ele existir e nenhuma FK depender dele."""
    conn = op.get_bind()
    if not _index_exists_fkguard(conn, index_name, table_name):
        return
    if _index_backs_foreign_key(conn, index_name, table_name):
        return
    op.drop_index(index_name, table_name=table_name)


def _create_index_if_absent(index_name, table_name, columns, **kw) -> None:
    """Par simétrico: quando a remoção é pulada, a recriação
    correspondente encontraria o índice já lá e falharia com
    (1061, "Duplicate key name '...'")."""
    conn = op.get_bind()
    if _index_exists_fkguard(conn, index_name, table_name):
        return
    op.create_index(index_name, table_name, columns, **kw)
```

E, para o `drop_constraint(None, ...)`:

```python
def _drop_foreign_key_on_column(table_name: str, column_name: str) -> None:
    """Remove a FK que incide sobre a coluna, qualquer que seja o nome.

    Nomes auto-atribuídos pelo MySQL (`<tabela>_ibfk_N`) dependem da ordem
    de criação e variam entre bancos. Resolver pelo information_schema é a
    única forma correta de escrever isto num downgrade que precisa rodar em
    qualquer instalação."""
    conn = op.get_bind()
    for (nome,) in conn.execute(
        _sa_text(
            "SELECT DISTINCT constraint_name "
            "FROM information_schema.key_column_usage "
            "WHERE table_schema = DATABASE() AND table_name = :tbl "
            "  AND column_name = :col AND referenced_table_name IS NOT NULL"
        ),
        {"tbl": table_name, "col": column_name},
    ).all():
        op.drop_constraint(nome, table_name, type_="foreignkey")
```

> **Por que autocontidas e não num módulo compartilhado.** Migrations são **artefatos
> históricos**: precisam continuar rodando anos depois, mesmo que um helper comum mude ou seja
> removido. A duplicação aqui é deliberada e é a prática correta para este tipo de arquivo.

### Verificação

Executada contra **MySQL 8.4 real**, num banco descartável (`auditoria_downgrade_test`), com a
sequência exata do job de CI — o banco de desenvolvimento não foi tocado:

```
1) alembic upgrade head    OK
2) alembic downgrade base  OK
3) alembic upgrade head    OK
4) head único              OK
```

Confirmada depois no próprio CI: job `migrations` **verde**.

---

## B-A31 — 9 CVEs, sete delas no parser de upload `✅ corrigido`

**Categoria:** Vulnerable and Outdated Components (**A06:2021**)

### Localização

`backend/requirements.txt` — primeira execução real do `pip-audit`:

```
Found 9 known vulnerabilities in 3 packages
Name             Version ID              Fix Versions
---------------- ------- --------------- ------------
python-multipart 0.0.9   PYSEC-2026-1852 0.0.22
python-multipart 0.0.9   PYSEC-2026-1851 0.0.18
python-multipart 0.0.9   PYSEC-2026-3038 0.0.26
python-multipart 0.0.9   PYSEC-2026-3037 0.0.30
python-multipart 0.0.9   PYSEC-2026-3036 0.0.30
python-multipart 0.0.9   PYSEC-2026-3040 0.0.31
python-multipart 0.0.9   PYSEC-2026-3039 0.0.27
pytest           8.2.0   PYSEC-2026-1845 9.0.3
ecdsa            0.19.2  PYSEC-2026-1325
```

### Impacto

`python-multipart` é o parser de `multipart/form-data` — **exatamente o caminho do upload de
evidências**, que recebe arquivo de usuário autenticado mas não confiável. Sete CVEs acumuladas
numa dependência nessa posição não é um detalhe de higiene.

### Correção

| Pacote | De | Para | Nota |
|---|---|---|---|
| `python-multipart` | `==0.0.9` | `>=0.0.31` | Instalado: 0.0.32 |
| `pytest` | `==8.2.0` | `>=9.0.3` | Instalado: 9.1.1 — a suíte segue verde nos 258 testes |
| `ecdsa` | 0.19.2 | — | **Sem correção publicada** — ver abaixo |

### A CVE sem correção

`PYSEC-2026-1325` (ecdsa 0.19.2) **não tem versão de correção**. A `ecdsa` entra como dependência
transitiva de `python-jose[cryptography]`, e a vulnerabilidade é um ataque de canal lateral sobre
assinatura **ECDSA**. Este projeto assina com **HS256 (HMAC)** — o caminho vulnerável não é
exercitado.

Ignorada explicitamente, com a justificativa **ao lado da exceção**, não num arquivo separado:

```yaml
      # PYSEC-2026-1325 (ecdsa 0.19.2) NAO tem versao de correcao publicada.
      # A ecdsa entra como dependencia transitiva de python-jose[cryptography]
      # e a vulnerabilidade e um ataque de canal lateral sobre assinatura
      # ECDSA. Este projeto assina com HS256 (HMAC), entao o caminho
      # vulneravel nao e exercitado.
      #
      # Reavaliar se: (a) sair uma versao corrigida da ecdsa, ou (b) o
      # projeto passar a usar algoritmo de curva eliptica (ES256 etc.).
      - name: Auditoria de dependencias (pip-audit)
        run: |
          pip install pip-audit
          pip-audit -r requirements.txt --ignore-vuln PYSEC-2026-1325
```

Resultado: `No known vulnerabilities found, 1 ignored`.

---

## B-M30 — O job `backend` nunca poderia ter passado `✅ corrigido`

**Categoria:** Security Misconfiguration (**A05:2021**) · Barreira inoperante

### Sintoma

```
ImportError while loading conftest '.../backend/tests/conftest.py'
pydantic_core.ValidationError: 2 validation errors for Settings
  DATABASE_URL   Field required
  JWT_SECRET     Field required
```

### Causa

`Settings` (`app/core/config.py`) exige `DATABASE_URL` e `JWT_SECRET` **sem default** — de
propósito, e essa decisão está registrada em **B-M25**/**M-24**: um banco silenciosamente errado
ou um segredo previsível são piores que a aplicação recusar-se a subir.

Localmente esses valores vêm de `backend/.env`, que é **gitignored** e não existe no runner.

### O que isso significa

O job de testes do backend foi escrito no **BLOCO H, em 2026-08-11**. Ele nunca poderia ter
passado. Ficou **dois meses e meio** no repositório como barreira de qualidade, citado em
documento e em checklist, sem jamais ter sido capaz de executar um único teste.

### Correção

```yaml
    env:
      DATABASE_URL: "sqlite:///:memory:"
      JWT_SECRET: "ci-secret-descartavel-nao-usado-para-nada-real"
```

Valores descartáveis: a suíte usa SQLite em memória via `conftest.py` e sobrescreve `get_db`, então
a `DATABASE_URL` nunca é conectada.

### O defeito colateral, no teste desta própria auditoria

`test_database_url_e_jwt_secret_sao_obrigatorios` (escrito em Q.4, para **B-M25**) passou a falhar
assim que o job ganhou as variáveis — porque ele isolava do arquivo `.env` mas **não do ambiente do
processo**. Sem isso ele não media o default do código: media a máquina onde rodava.

Corrigido com uma fixture `autouse` que limpa as 18 variáveis que `Settings` consulta, e uma
asserção que verifica **quais** campos faltam:

```python
@pytest.fixture(autouse=True)
def _ambiente_limpo(monkeypatch):
    for nome in VARIAVEIS_DE_SETTINGS:
        monkeypatch.delenv(nome, raising=False)


def test_database_url_e_jwt_secret_sao_obrigatorios():
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)
    faltando = {e["loc"][0] for e in exc.value.errors()}
    assert faltando == {"DATABASE_URL", "JWT_SECRET"}
```

É a mesma classe de fragilidade da fixture de rate limit do BLOCO Q: **um teste que depende de
ordem ou de ambiente aponta para o lugar errado quando falha.**

---

## B-M31 — `tsc` reprovava código correto `✅ corrigido`

**Categoria:** Barreira inoperante

### Sintoma

```
error TS2304: Cannot find name 'RouteContext'.
error TS2304: Cannot find name 'PageProps'.
error TS2304: Cannot find name 'LayoutProps'.
```

Nove erros, em 9 arquivos — todos em código **correto**.

### Causa

`PageProps`, `LayoutProps` e `RouteContext` são tipos **gerados** pelo Next.js (em `.next/types`),
não escritos à mão. Localmente eles existem porque há um `.next` de builds anteriores; num runner
limpo, não.

> A observação **já estava registrada** na checklist de O.1 do plano de implementação, desde o
> BLOCO O: *"`next typegen` precisa rodar antes de interpretar a saída do `tsc` em qualquer fase
> que crie rota nova — 10 dos 12 erros da primeira execução eram falso positivo por tipos de rota
> ainda não gerados."*
>
> O que faltava não era o conhecimento. Era ele chegar ao workflow.

### Correção

```yaml
      - name: Gerar tipos de rota do Next
        run: npx next typegen

      - name: Checagem de tipos
        run: npx tsc --noEmit
```

Reproduzido localmente antes de aplicar: `rm -rf .next && npx next typegen && npx tsc --noEmit` →
0 erros.

---

## 📌 Uma previsão errada, registrada

O PR #1 previa, com destaque, que o job `secrets` **falharia** — porque o histórico do git contém
as credenciais antigas (já rotacionadas).

**Ele passou.** O `gitleaks` não acusou nada.

O **GitGuardian**, que já está integrado ao repositório, acusou **14 segredos nos mesmos 39
commits** e reprovou o PR. Os dois scanners discordam sobre o mesmo histórico.

Isso não fecha nem reabre B-C23 — as credenciais estão rotacionadas e verificadas. Mas registra
que **a ferramenta escolhida define o que é encontrado**, e que a decisão sobre o histórico
(`.gitleaksignore` documentado × purgar com `git filter-repo`) continua em aberto.

---

## ⚠️ Sumário do levantamento (auditoria de 2026-08-26)

A rev. 8.0 registrou uma auditoria adversarial com 1 achado Crítico e 4 Altos. **Todos foram fechados pelo BLOCO P** (`4fd576f`) e pela correção do CSP (`34f8444`) — verificado item a item nesta revisão, ver seção *Achados fechados desde a rev. 8.0*.

Esta revisão (9.0) faz a auditoria seguinte, sobre o código já corrigido. **Resultado: 3 achados de prioridade Alta, 5 Médios e 7 Baixos**, todos confirmados por execução — nenhum por leitura.

O padrão dominante mudou de natureza. Na rev. 8.0 os achados eram de **autorização**: quem podia fazer o quê. Agora são de **borda**: o que acontece quando a entrada sai do formato esperado, quando um serviço externo não responde, ou quando o volume cresce.

| ID | Achado | Prioridade | Confirmado por |
|---|---|---|---|
| **B-A27** | `POST /auth/login` e `/auth/register` estouram exceção não tratada (HTTP 500) com qualquer senha acima de 72 bytes — **sem autenticação** | 🟠 Alta | Sonda: `ValueError: password cannot be longer than 72 bytes` |
| **B-A28** | O cliente auditado **lê** o checklist interno e o histórico do auditor — o BLOCO P fechou a escrita, não a leitura | 🟠 Alta | Sonda HTTP: `200` como `user` e como `sub-user`, com o conteúdo interno no corpo |
| **B-A29** | A senha temporária do onboarding **não existe em lugar nenhum** sem SMTP configurado — o cliente é criado sem forma de acessar | 🟠 Alta | Sonda: `201`, corpo sem senha; log de dev: *"senha enviada por email em produção"* |
| **B-M25** | `ALLOW_PUBLIC_REGISTRATION` tem default **`True`** — ausência da variável abre o cadastro público | 🟡 Média | Sonda: `Settings(...).ALLOW_PUBLIC_REGISTRATION == True` |
| **B-M26** | `GET /admin/companies` faz **7 queries por empresa** (73 para 10 empresas) | 🟡 Média | Sonda com contador de `before_cursor_execute` |
| **B-M27** | Todo cliente principal recebe um e-mail dizendo que é **sub-usuário** de sua própria empresa | 🟡 Média | Leitura + saída real do log de dev |
| **B-M28** | A guarda de path traversal de P.2 ficou só em `delete_files()`; o **download** não a tem | 🟡 Média | Leitura comparada de `storage.py:25` × `storage.py:55` |
| **B-M29** | Default de `JWT_EXPIRES_MINUTES` diverge: **15** no backend, **60** no frontend | 🟡 Média | Sonda + leitura de `proxy.ts:30` e `login/route.ts:12` |
| **B-B17..B-B23** | 7 achados Baixos — duplicação, typos herdados, dependência sem pin, mixin morto | 🟢 Baixa | Leitura + `grep` |

> ### 📌 O achado que mais importa
>
> **B-A27** é o único explorável **sem nenhuma credencial**. Um `POST /api/v1/auth/login` com um campo `password` de 100 caracteres derruba a requisição com exceção não tratada. Não é um bug de lógica de negócio: é a biblioteca de hash recusando entrada fora do contrato, e o código nunca tendo perguntado qual era o contrato. `requirements.txt` declara `bcrypt>=4.0.0`; o ambiente resolve para **5.0.0**, onde o comportamento é levantar `ValueError` — em versões anteriores da mesma família, truncar em silêncio. **As duas alternativas são ruins**, e a correção precisa tratar o limite explicitamente, não depender de qual delas a versão instalada escolheu.

---

## Resumo Quantitativo

| Prioridade | Backend | Frontend | Banco/Migrations | Infra/Repo | Total |
|---|---|---|---|---|---|
| **Crítica** | 0 | 0 | 0 | 0 | **0** ✅ |
| **Alta** | 3 | 0 | 0 | 0 | **3** |
| **Média** | 4 | 1 | 0 | 0 | **5** |
| **Baixa** | 5 | 2 | 0 | 0 | **7** |
| **Total ativo** | **12** | **3** | **0** | **0** | **15** |
| Corrigidos e confirmados (histórico acumulado) | — | — | — | — | **65** (51 até a rev. 8.0 + 13 defeitos do BLOCO P + defeito #14 do CSP) |

### Distribuição por categoria OWASP

| Categoria | Achados |
|---|---|
| A01:2021 — Broken Access Control | B-A28 |
| A04:2021 — Insecure Design | B-A29, B-M28 |
| A05:2021 — Security Misconfiguration | B-M25, B-M29 |
| A06:2021 — Vulnerable and Outdated Components | B-B20 |
| Robustez / disponibilidade | B-A27 |
| Performance | B-M26 |
| Qualidade / manutenibilidade | B-M27, B-B17..B-B23 |

---

# PRIORIDADE ALTA

---

## B-A27 — Senha acima de 72 bytes derruba `/auth/login` e `/auth/register` com exceção não tratada `🔴 novo`

**Categoria:** Improper Input Validation (**CWE-20**) · Uncaught Exception (**CWE-248**) · Denial of Service (**CWE-400**)

### Localização

| Arquivo | Linha | O quê |
|---|---|---|
| `backend/app/core/security.py` | **11** | `bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())` — sem checagem de tamanho |
| `backend/app/core/security.py` | **19** | `bcrypt.checkpw(plain_password.encode("utf-8"), ...)` — idem |
| `backend/app/schemas/auth.py` | **9–21** | `UserCreate.password_strength` valida mínimo (8), maiúscula e dígito — **não valida máximo** |
| `backend/app/schemas/auth.py` | **23–25** | `UserLogin.password: str` — sem restrição alguma |

### Impacto e consequências

`bcrypt` opera sobre no máximo **72 bytes**. A partir da versão 4.0 a biblioteca deixou de truncar em silêncio e passou a levantar `ValueError`. O ambiente resolve `bcrypt>=4.0.0` para **5.0.0**:

```
ValueError: password cannot be longer than 72 bytes, truncate manually if
necessary (e.g. my_password[:72])
```

Nenhuma das duas camadas que recebem a senha trata essa exceção. O resultado:

| Rota | Autenticação exigida | Resultado com senha > 72 bytes |
|---|---|---|
| `POST /api/v1/auth/login` | **nenhuma** | Exceção não tratada → **HTTP 500** |
| `POST /api/v1/auth/register` | nenhuma (se a flag estiver ligada — ver **B-M25**) | Exceção não tratada → **HTTP 500** |
| `POST /api/v1/onboarding/principal-user` | admin | Não afetado (senha gerada internamente, 12 caracteres) |

Três consequências, em ordem de gravidade:

1. **Superfície de erro não autenticada.** Qualquer pessoa na internet consegue produzir um 500 no endpoint de login sem credencial nenhuma. Não derruba o processo (o ASGI isola a requisição), mas polui o log de erro, dispara alarme falso em qualquer monitoramento futuro e serve de sinal claro de que a validação de entrada é incompleta.
2. **Usuário legítimo com gerenciador de senhas fica travado.** Gerenciadores geram passphrases longas com frequência. Um cliente que escolha uma senha de 80 caracteres no cadastro recebe um erro 500 genérico, sem nenhuma indicação do que fazer.
3. **Risco silencioso se a versão mudar.** Se algum dia o ambiente resolver para uma versão que trunca em vez de levantar, o efeito muda de "erro visível" para "duas senhas diferentes que compartilham os primeiros 72 bytes autenticam a mesma conta". Esse é o modo de falha realmente perigoso, e o código atual está a um `pip install` de distância dele.

### Reprodução (confirmada)

```python
# backend/tests/ — sonda executada em 2026-08-26
def test_probe_login_long_password_crashes(client, principal_user):
    long_pw = "A1" + ("x" * 100)          # 102 bytes
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "cliente@test.com", "password": long_pw},
    )
```

Saída:

```
[SONDA] POST /auth/login  ESTOUROU: ValueError: password cannot be longer
        than 72 bytes, truncate manually if necessary
[SONDA] POST /auth/register ESTOUROU: ValueError: password cannot be longer
        than 72 bytes, truncate manually if necessary
[SONDA] bcrypt 5.0.0
```

### Estratégia de correção

Três camadas, nesta ordem — cada uma cobre o que a anterior não alcança:

1. **Contrato explícito no módulo de hash.** `security.py` passa a conhecer o limite de 72 bytes e a tratá-lo, em vez de deixar a biblioteca decidir. `hash_password` levanta uma exceção de domínio (`PasswordTooLongError`); `verify_password` **devolve `False`**, porque nenhum hash válido pode ter nascido de uma senha longa demais — e devolver `False` evita criar um oráculo que distinga "senha longa" de "senha errada".
2. **Validação no schema**, para que o cadastro devolva **422 com mensagem útil** em vez de erro genérico.
3. **Tratamento no router de onboarding**, cobrindo o caso em que a senha vem de outro caminho no futuro.

### Código de correção completo

**1. `backend/app/core/security.py` — arquivo completo:**

```python
from __future__ import annotations

import bcrypt

# bcrypt opera sobre no máximo 72 bytes. Até a versão 3.x a biblioteca
# truncava em silêncio; a partir da 4.0 levanta ValueError. Nenhum dos dois
# comportamentos é aceitável implicitamente (B-A27): truncar faz duas senhas
# distintas autenticarem a mesma conta; levantar produz HTTP 500 numa rota
# não autenticada. O limite passa a ser tratado aqui, explicitamente, e o
# código deixa de depender de qual versão está instalada.
MAX_PASSWORD_BYTES = 72


class PasswordTooLongError(ValueError):
    """Senha excede o limite físico do bcrypt (72 bytes em UTF-8).

    Levantada só por `hash_password` (caminho de CRIAÇÃO de senha), onde a
    resposta correta é recusar com 422 e explicar o limite ao usuário.
    `verify_password` NÃO a levanta — ver docstring lá.
    """


def _password_bytes(plain_password: str) -> bytes:
    """UTF-8 da senha. Atenção: o limite é em BYTES, não em caracteres —
    'ç' ocupa 2 bytes e um emoji ocupa 4, então uma senha de 40 caracteres
    pode ultrapassar 72 bytes."""
    return plain_password.encode("utf-8")


def hash_password(plain_password: str) -> str:
    """
    Recebe senha em texto puro e devolve hash seguro (bcrypt).
    Nunca salve a senha pura no banco.

    Levanta `PasswordTooLongError` se a senha ultrapassar 72 bytes — quem
    chama converte para 422. Recusar é a única opção correta aqui:
    truncar aceitaria a senha e depois autenticaria qualquer variante que
    compartilhasse os primeiros 72 bytes.
    """
    encoded = _password_bytes(plain_password)
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise PasswordTooLongError(
            f"Senha não pode ultrapassar {MAX_PASSWORD_BYTES} bytes "
            f"(recebida com {len(encoded)})"
        )
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """
    Compara a senha digitada com o hash salvo no banco.
    Retorna True se bater, False caso contrário.

    Uma senha acima de 72 bytes devolve `False`, não exceção: nenhum hash
    armazenado pode ter sido gerado a partir dela (hash_password recusa),
    então ela está necessariamente errada. Devolver False — em vez de 422
    ou 500 — também evita construir um oráculo que diferencie "senha longa
    demais" de "senha incorreta" para quem sonda o endpoint de login.

    O `except ValueError` final é defensivo contra hash corrompido/truncado
    no banco (`checkpw` levanta ValueError quando o salt é inválido); sem
    ele, um único registro ruim derruba o login com 500 em vez de negar.
    """
    encoded = _password_bytes(plain_password)
    if len(encoded) > MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))
    except ValueError:
        return False
```

**2. `backend/app/schemas/auth.py` — arquivo completo:**

```python
from __future__ import annotations

import re

from pydantic import BaseModel, EmailStr, field_validator

from app.core.security import MAX_PASSWORD_BYTES


def _validate_password_length(value: str) -> None:
    """Limite em BYTES (não caracteres) — é o que o bcrypt mede (B-A27)."""
    encoded = value.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Senha não pode ultrapassar {MAX_PASSWORD_BYTES} bytes. "
            "Acentos contam 2 bytes e emojis contam 4, então uma senha "
            "com menos de 72 caracteres ainda pode exceder o limite."
        )


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Senha deve ter ao menos 8 caracteres")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Senha deve ter ao menos uma letra maiúscula")
        if not re.search(r"[0-9]", v):
            raise ValueError("Senha deve ter ao menos um número")
        _validate_password_length(v)
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_within_bcrypt_limit(cls, v: str) -> str:
        """
        No LOGIN o limite não é validado como erro de formulário — uma senha
        longa demais simplesmente não pode estar correta, e `verify_password`
        já devolve False para ela. Este validador existe apenas como corte
        de custo: evita carregar uma string arbitrariamente grande até o
        bcrypt. O corte é generoso de propósito (10x o limite), para não
        virar um oráculo de tamanho.
        """
        if len(v.encode("utf-8")) > MAX_PASSWORD_BYTES * 10:
            raise ValueError("Credenciais inválidas")
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserPublic(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str
```

**3. `backend/app/api/v1/auth.py` — tratamento no `register` (substituir o bloco de criação):**

```python
from app.core.security import PasswordTooLongError   # junto dos outros imports

# ... dentro de register(), substituindo o bloco `user = create_user(...)`:

    try:
        user = create_user(
            db,
            full_name=payload.full_name,
            email=payload.email,
            password=payload.password,
            role="user",
        )
    except PasswordTooLongError as exc:
        # Rede de segurança: o validador do schema já barra este caso.
        # Mantida porque create_user() é chamada também por outros caminhos.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )

    db.commit()
    db.refresh(user)
```

### Teste de barreira

```python
# backend/tests/test_password_limits.py
"""B-A27: o limite de 72 bytes do bcrypt é tratado, não herdado."""
from __future__ import annotations

import pytest

from app.core.config import settings
from app.core.security import (
    MAX_PASSWORD_BYTES,
    PasswordTooLongError,
    hash_password,
    verify_password,
)

SENHA_LONGA = "A1" + ("x" * 100)          # 102 bytes
SENHA_LIMITE = "A1" + ("x" * 70)          # exatamente 72 bytes


def test_hash_password_recusa_acima_do_limite():
    with pytest.raises(PasswordTooLongError):
        hash_password(SENHA_LONGA)


def test_hash_password_aceita_exatamente_no_limite():
    assert len(SENHA_LIMITE.encode("utf-8")) == MAX_PASSWORD_BYTES
    assert verify_password(SENHA_LIMITE, hash_password(SENHA_LIMITE))


def test_verify_password_devolve_false_sem_levantar():
    hash_valido = hash_password("Senha1234")
    assert verify_password(SENHA_LONGA, hash_valido) is False


def test_verify_password_nao_confunde_prefixo_de_72_bytes():
    """O modo de falha do truncamento silencioso: duas senhas diferentes
    com o mesmo prefixo de 72 bytes NÃO podem autenticar a mesma conta."""
    hash_valido = hash_password(SENHA_LIMITE)
    assert verify_password(SENHA_LIMITE + "SUFIXO-DIFERENTE", hash_valido) is False


def test_verify_password_com_hash_corrompido_nao_estoura():
    assert verify_password("Senha1234", "isto-nao-e-um-hash-bcrypt") is False


def test_login_com_senha_longa_responde_401_e_nao_500(client, principal_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "cliente@test.com", "password": SENHA_LONGA},
    )
    assert resp.status_code == 401, (
        f"esperado 401 (credencial inválida), veio {resp.status_code} — "
        "o limite do bcrypt voltou a vazar como erro de servidor"
    )


def test_register_com_senha_longa_responde_422_e_nao_500(client, monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_PUBLIC_REGISTRATION", True)
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Teste Longo",
            "email": "longo@test.com",
            "password": SENHA_LONGA,
        },
    )
    assert resp.status_code == 422
    assert "72" in resp.text


def test_acentos_contam_como_dois_bytes(client):
    """36 'ç' = 72 bytes. O limite é de bytes, não de caracteres."""
    senha = "A1" + ("ç" * 36)              # 2 + 72 = 74 bytes
    assert len(senha) < MAX_PASSWORD_BYTES          # 38 caracteres
    assert len(senha.encode("utf-8")) > MAX_PASSWORD_BYTES
    with pytest.raises(PasswordTooLongError):
        hash_password(senha)
```

### Checklist de validação

- [ ] `pytest tests/test_password_limits.py -q` → 8 passed
- [ ] `pytest -q` → 210 passed (202 + 8)
- [ ] `POST /auth/login` com senha de 100 caracteres → **401**, sem entrada de erro no log
- [ ] `POST /auth/register` com senha de 100 caracteres → **422** com a mensagem sobre bytes
- [ ] Login de um usuário existente continua funcionando (não houve mudança de algoritmo)

---

## B-A28 — O cliente auditado lê o checklist interno e o histórico do auditor `🔴 novo`

**Categoria:** Broken Access Control (**A01:2021**) · Exposure of Sensitive Information to an Unauthorized Actor (**CWE-200**)

### Localização

| Arquivo | Linha | O quê |
|---|---|---|
| `backend/app/api/v1/dashboard_cards.py` | **352–354** | `@router.get("/cards/{card_id}")` com `Depends(get_current_user)` — qualquer papel autenticado |
| `backend/app/api/v1/dashboard_cards.py` | **358–375** | Carrega `DashboardCardchecklistItem` e `DashboardCardHistoryEntry` sem filtrar por papel |
| `backend/app/api/v1/dashboard_cards.py` | **412–431** | Devolve `checklist` e `history` completos no corpo da resposta |

### Impacto e consequências

O BLOCO P (P.1) fechou a **escrita** desses dois recursos com precisão cirúrgica:

| Recurso | Escrita | Leitura |
|---|---|---|
| Status do card | `require_admin` ✅ | aberta (correto — o cliente precisa ver seu status) |
| Item de checklist | `require_admin` ✅ | 🔴 **aberta** |
| Entrada de histórico | recusa não-admin ✅ | 🔴 **aberta** |
| Nota interna do card | `require_admin` ✅ | `require_admin` ✅ |

A inconsistência é evidente quando se comparam os dois registros internos: **notas** de card são protegidas na leitura (`GET /cards/{id}/notes` → 403 para cliente, confirmado por sonda), mas **checklist e histórico** — que a própria docstring de `toggle_checklist_item` descreve como *"checklist interno da equipe de auditoria"* — voltam abertos no detalhe do card.

O conteúdo exposto é exatamente o trabalho interno do auditor: o que ele ainda precisa conferir, o que já conferiu, e cada mudança de avaliação com nome e horário. Numa plataforma de auditoria, isso vira:

- **Vantagem informacional para o auditado.** Saber que o auditor ainda não conferiu determinado item, ou que mudou uma classificação, altera o comportamento de quem está sendo auditado.
- **Exposição de identidade do auditor.** `actor_user` traz `id` e `full_name` de quem executou cada ação.
- **Contradição com a decisão de projeto já tomada.** Se o cliente pode ler tudo, restringir a escrita protege a integridade do registro, mas não sua confidencialidade — e a documentação afirma as duas coisas.

A UI do cliente **não** renderiza esses campos (`grep` por `checklist`/`history` em `client-dashboard-client.tsx`: zero ocorrências). A única barreira, de novo, é o frontend — que foi exatamente a conclusão de B-A23 na rev. 8.0.

### Reprodução (confirmada)

```python
def test_probe_client_reads_internal_checklist_and_history(
    client, db, admin_user, principal_user, user_token, sub_user_token, dashboard_card
):
    db.add(DashboardCardchecklistItem(
        card_id=dashboard_card.id,
        title="INTERNO: conferir contrato de confidencialidade do fornecedor",
        done=True,
    ))
    db.add(DashboardCardHistoryEntry(
        card_id=dashboard_card.id,
        action="INTERNO: auditor marcou como NAOCONFORME apos revisao",
        actor_user_id=admin_user.id,
    ))
    db.commit()

    for label, token in (("user", user_token), ("sub-user", sub_user_token)):
        resp = client.get(f"/api/v1/dashboard/cards/{dashboard_card.id}",
                          headers={"Authorization": f"Bearer {token}"})
```

Saída:

```
[SONDA] GET /dashboard/cards/{id} como user: 200
[SONDA]   checklist devolvido: [{'id': 1, 'title': 'INTERNO: conferir contrato de
          confidencialidade do fornecedor', 'done': True}]
[SONDA]   history devolvido:   [{'id': 1, 'action': 'INTERNO: auditor marcou como
          NAOCONFORME apos revisao', 'created_at': '...',
          'actor_user': {'id': 1, 'full_name': 'Admin Teste'}}]
[SONDA] GET /dashboard/cards/{id} como sub-user: 200   (idêntico)
[SONDA] GET /cards/{id}/notes como user: 403           ◀── a assimetria
```

### Estratégia de correção

Não remover o endpoint nem criar um segundo: o cliente **precisa** do detalhe do card (título, status e chat). A correção é **omitir as coleções internas quando quem chama não é admin**, mantendo o mesmo contrato de resposta com listas vazias — assim nenhum consumidor quebra, e a semântica fica correta ("você não tem checklist a ver aqui", não "este card não tem checklist").

Isso também exige registrar a decisão em `core/policy.py`, para que a próxima leitura sensível não repita a omissão: o enum ganha `READ_CARD_INTERNALS`, e a regra passa a ser consultável.

### Código de correção completo

**1. `backend/app/core/policy.py` — acrescentar a ação de leitura:**

```python
class Action(str, enum.Enum):
    """
    Ações cujo direito NÃO decorre de posse. Existe porque posse e
    permissão são coisas diferentes numa plataforma de auditoria: o
    cliente é dono dos próprios cards e evidências, mas quem declara
    conformidade é o auditor (ver B-A23 em docs/relatorio_bugs.md).

    Desde B-A28 o enum cobre também LEITURA: o registro interno do
    auditor (checklist e histórico) é confidencial em relação ao
    auditado, do mesmo modo que a escrita é privativa dele.
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
}
```

**2. `backend/app/api/v1/dashboard_cards.py` — substituir `get_card_details` inteira:**

```python
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
        checklist=[
            DashboardchecklistItem(id=item.id, title=item.title, done=item.done)
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
```

**3. `backend/app/api/v1/dashboard_cards.py` — ajustar o import (linha 49):**

```python
from app.core.policy import Action, assert_can, can
```

### Teste de barreira

```python
# backend/tests/test_card_internals_visibility.py
"""B-A28: checklist e histórico são registro interno do auditor."""
from __future__ import annotations

from app.models.company_dashboard import (
    DashboardCardchecklistItem,
    DashboardCardHistoryEntry,
    DashboardCardMessage,
    DashboardMessageType,
)


def _semear_interno(db, card, admin_user, principal_user):
    db.add(DashboardCardchecklistItem(
        card_id=card.id, title="INTERNO: conferir contrato", done=True))
    db.add(DashboardCardHistoryEntry(
        card_id=card.id, action="INTERNO: mudou para NAOCONFORME",
        actor_user_id=admin_user.id))
    db.add(DashboardCardMessage(
        card_id=card.id, author_user_id=principal_user.id,
        message_type=DashboardMessageType.QUESTION, content="Duvida do cliente"))
    db.commit()


def test_admin_ve_checklist_e_historico(
    client, db, admin_user, principal_user, admin_token, dashboard_card
):
    _semear_interno(db, dashboard_card, admin_user, principal_user)
    body = client.get(
        f"/api/v1/dashboard/cards/{dashboard_card.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()
    assert len(body["checklist"]) == 1
    assert len(body["history"]) == 1
    assert len(body["chat"]) == 1


def test_cliente_nao_ve_checklist_nem_historico(
    client, db, admin_user, principal_user, user_token, dashboard_card
):
    _semear_interno(db, dashboard_card, admin_user, principal_user)
    resp = client.get(
        f"/api/v1/dashboard/cards/{dashboard_card.id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200, "o cliente continua tendo acesso ao card"
    body = resp.json()
    assert body["checklist"] == [], "checklist interno vazou para o cliente"
    assert body["history"] == [], "histórico interno vazou para o cliente"
    assert len(body["chat"]) == 1, "o chat é bilateral e não pode sumir"
    assert "INTERNO" not in resp.text


def test_sub_user_nao_ve_checklist_nem_historico(
    client, db, admin_user, principal_user, sub_user_token, dashboard_card
):
    _semear_interno(db, dashboard_card, admin_user, principal_user)
    resp = client.get(
        f"/api/v1/dashboard/cards/{dashboard_card.id}",
        headers={"Authorization": f"Bearer {sub_user_token}"},
    )
    assert resp.json()["checklist"] == []
    assert resp.json()["history"] == []
    assert "INTERNO" not in resp.text
```

### Checklist de validação

- [ ] `pytest tests/test_card_internals_visibility.py -q` → 3 passed
- [ ] `pytest -q` → toda a suíte verde (nenhum teste existente depende do vazamento)
- [ ] Tela do admin (`/private/admin/empresas/[id]/dashboard`) continua exibindo checklist e histórico
- [ ] Tela do cliente (`/private/client`) continua funcionando — ela nunca consumiu esses campos

---

## B-A29 — A senha temporária do onboarding não existe em lugar nenhum sem SMTP `🔴 novo`

**Categoria:** Insecure Design (**A04:2021**) · Improper Handling of Exceptional Conditions (**CWE-703**)

### Localização

| Arquivo | Linha | O quê |
|---|---|---|
| `backend/app/api/v1/admin_onboarding.py` | **88** | `initial_password = generate_temporary_password()` |
| `backend/app/api/v1/admin_onboarding.py` | **126–131** | `send_sub_user_credentials_email(...)` — único destino da senha |
| `backend/app/api/v1/admin_onboarding.py` | **133–138** | Resposta **sem** a senha |
| `backend/app/schemas/admin_onboarding.py` | **15–19** | `PrincipalUserOnboardingResponse` — 4 campos, nenhum é a credencial |
| `backend/app/services/email_sender.py` | **20–29** | Sem `SMTP_HOST`: imprime *"senha enviada por email em produção"* e **descarta a senha** |

### Impacto e consequências

O fluxo tem uma única saída para a credencial recém-criada, e essa saída pode não existir:

```
generate_temporary_password()  ──▶  hash_password()  ──▶  banco
                               └──▶  send_sub_user_credentials_email()
                                      │
                                      ├── SMTP_HOST configurado ──▶ e-mail ✅
                                      └── SMTP_HOST ausente ──────▶ print() SEM a senha
                                                                     └──▶ senha perdida 🔴
```

Consequências, por ambiente:

| Ambiente | O que acontece |
|---|---|
| **Dev / homologação** (sem SMTP, o caso padrão do `.env.example`) | O cliente é criado, a empresa é criada, o dashboard é criado — e **ninguém consegue entrar na conta**. Não há tela de "reenviar credenciais", não há reset de senha, não há endpoint de troca. A única saída é apagar a empresa e recomeçar, ou alterar o hash direto no banco |
| **Produção com SMTP intermitente** | Pior: `send_sub_user_credentials_email` é chamada **depois** do `db.commit()` e **fora** de qualquer `try`. Uma falha de SMTP levanta a exceção para o FastAPI → **HTTP 500 para o admin**, com o usuário já criado e committado. O admin vê "erro", conclui que falhou, tenta de novo e recebe **409 "E-mail já cadastrado"** — o registro existe, inacessível |
| **Produção com SMTP saudável** | Funciona |

O mesmo padrão existe em `sub_users.py::approve_request` (linhas 165–186): senha gerada, enviada por e-mail, ausente da resposta.

E não há rede de segurança a jusante: o projeto **não tem** recuperação de senha (`grep` por `reset`/`forgot`/`recuperar` no backend: zero endpoints), e **não tem** troca de senha obrigatória no primeiro login (N01, ainda planejado).

### Reprodução (confirmada)

```python
def test_probe_onboarding_temp_password_visible(client, admin_token, db):
    db.add(DashboardTemplate(name="Padrao", description=None, is_default=True))
    db.commit()
    resp = client.post("/api/v1/onboarding/principal-user",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"full_name": "Novo Cliente", "email": "novo@test.com",
              "company_name": "Nova Empresa"})
```

Saída:

```
[DEV-EMAIL] Sub_user criado: Novo Cliente <novo@test.com>(principal: Nova
            Empresa) - senha enviada por email em produção
[SONDA] POST /onboarding/principal-user -> 201
[SONDA] corpo: {'user_id': 2, 'company_id': 1, 'dashboard_id': 1,
                'dashboard_cards_created': 0}
```

A senha gerada não aparece na resposta nem no log. Foi hasheada e esquecida.

### Estratégia de correção

Três mudanças, todas necessárias:

1. **`send_..._credentials_email` passa a devolver se entregou** (`bool`), em vez de sempre parecer ter entregue, e a **capturar suas próprias falhas de SMTP** — enviar credencial nunca deve derrubar uma transação já committada.
2. **A resposta da API devolve a senha temporária ao admin quando o e-mail não foi entregue.** O admin já é a autoridade que criou a conta; entregar a ele a credencial que ele mesmo acabou de gerar não amplia privilégio nenhum. Devolver **sempre** seria pior (ela ficaria em log de acesso e histórico de rede sem necessidade), então o campo só é preenchido quando o e-mail falhou ou não foi tentado.
3. **O frontend exibe a senha com aviso claro** quando ela vem preenchida.

### Código de correção completo

**1. `backend/app/services/email_sender.py` — arquivo completo:**

```python
from __future__ import annotations

import smtplib
from email.message import EmailMessage

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


def _enviar(msg: EmailMessage) -> bool:
    """Entrega via SMTP. Devolve False (em vez de propagar) se falhar:
    quem chama já committou a transação e não pode desfazê-la por causa
    de um servidor de e-mail — mesmo princípio de storage.delete_files()
    (B-A26). A falha vira log estruturado e um sinal de retorno."""
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        logger.warning(
            "credentials_email_failed", to_email=msg["To"], error=str(exc)
        )
        return False

    logger.info("credentials_email_sent", to_email=msg["To"])
    return True


def send_sub_user_credentials_email(
    *, to_email: str, sub_user_name: str, principal_name: str, temporary_password: str
) -> bool:
    """
    Credenciais de um SUB-USUÁRIO, criado a pedido do usuário principal.

    Devolve True se o e-mail foi entregue, False caso contrário (SMTP não
    configurado ou falha de entrega). Quem chama usa esse retorno para
    decidir se precisa devolver a senha ao admin (B-A29). A senha NUNCA
    entra em log, com ou sem SMTP.
    """
    if not settings.SMTP_HOST:
        logger.info(
            "credentials_email_skipped_no_smtp",
            to_email=to_email,
            recipient_kind="sub-user",
        )
        return False

    msg = EmailMessage()
    msg["Subject"] = "Acesso de sub-usuário — Plataforma de Auditoria"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.set_content(
        f"Olá, {sub_user_name}.\n\n"
        f"Você foi adicionado como sub-usuário de {principal_name}.\n\n"
        f"Use as seguintes credenciais para acessar o sistema:\n\n"
        f"E-mail: {to_email}\n"
        f"Senha temporária: {temporary_password}\n\n"
        f"Recomendamos alterar sua senha no primeiro acesso.\n\n"
        f"Atenciosamente,\nEquipe de Auditoria"
    )
    return _enviar(msg)


def send_principal_user_credentials_email(
    *, to_email: str, full_name: str, company_name: str, temporary_password: str
) -> bool:
    """
    Credenciais do USUÁRIO PRINCIPAL de uma empresa recém-onboardada.

    Função própria, e não reuso de `send_sub_user_credentials_email`
    (B-M27): reusar fazia todo cliente principal receber um e-mail com o
    assunto "Acesso de sub-usuário" dizendo que ele fora "adicionado como
    sub-usuário" da própria empresa.
    """
    if not settings.SMTP_HOST:
        logger.info(
            "credentials_email_skipped_no_smtp",
            to_email=to_email,
            recipient_kind="principal-user",
        )
        return False

    msg = EmailMessage()
    msg["Subject"] = "Seu acesso — Plataforma de Auditoria"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.set_content(
        f"Olá, {full_name}.\n\n"
        f"A conta da empresa {company_name} foi criada na Plataforma de "
        f"Auditoria e você é o usuário responsável.\n\n"
        f"Use as seguintes credenciais para o primeiro acesso:\n\n"
        f"E-mail: {to_email}\n"
        f"Senha temporária: {temporary_password}\n\n"
        f"Altere sua senha no primeiro acesso.\n\n"
        f"Atenciosamente,\nEquipe de Auditoria"
    )
    return _enviar(msg)
```

**2. `backend/app/schemas/admin_onboarding.py` — a resposta ganha 2 campos:**

```python
class PrincipalUserOnboardingResponse(BaseModel):
    user_id: int
    company_id: int
    dashboard_id: int
    dashboard_cards_created: int

    # B-A29: quando o e-mail de credenciais NÃO foi entregue (SMTP ausente
    # ou falha de envio), a senha temporária volta aqui para o admin —
    # senão ela seria gerada, hasheada e esquecida, deixando um cliente
    # criado e inacessível. Fica `None` quando o e-mail foi entregue, para
    # não trafegar credencial sem necessidade.
    email_delivered: bool
    temporary_password: str | None = None
```

**3. `backend/app/api/v1/admin_onboarding.py` — substituir o trecho final da rota:**

```python
from app.services.email_sender import send_principal_user_credentials_email

# ... substituindo o bloco `send_sub_user_credentials_email(...)` e o return:

    email_delivered = send_principal_user_credentials_email(
        to_email=principal_user.email,
        full_name=principal_user.full_name,
        company_name=company.name,
        temporary_password=initial_password,
    )

    return PrincipalUserOnboardingResponse(
        user_id=principal_user.id,
        company_id=company.id,
        dashboard_id=dashboard.id,
        dashboard_cards_created=cards_created,
        email_delivered=email_delivered,
        temporary_password=None if email_delivered else initial_password,
    )
```

**4. `backend/app/schemas/sub_user.py` — o mesmo para a aprovação de sub-usuário:**

```python
class SubUserApproveResponse(BaseModel):
    request_id: int
    sub_user_id: int
    sub_user_email: EmailStr
    # B-A29 — mesmo raciocínio do onboarding de principal.
    email_delivered: bool
    temporary_password: str | None = None
```

**5. `backend/app/api/v1/sub_users.py` — no fim de `approve_request`:**

```python
    email_delivered = send_sub_user_credentials_email(
        to_email=new_sub_user.email,
        sub_user_name=new_sub_user.full_name,
        principal_name=principal.full_name,
        temporary_password=temp_password,
    )

    return SubUserApproveResponse(
        request_id=request.id,
        sub_user_id=new_sub_user.id,
        sub_user_email=new_sub_user.email,
        email_delivered=email_delivered,
        temporary_password=None if email_delivered else temp_password,
    )
```

**6. `frontend/app/private/admin/actions.ts` — o tipo de retorno acompanha:**

```typescript
export type OnboardingResult =
  | {
      ok: true;
      userId: number;
      companyId: number;
      dashboardId: number;
      cardsCreated: number;
      /** true = credenciais entregues por e-mail; false = exiba a senha abaixo */
      emailDelivered: boolean;
      /** Preenchida SOMENTE quando emailDelivered === false (B-A29). */
      temporaryPassword: string | null;
    }
  | { ok: false; message: string };
```

E o componente que consome exibe, quando `emailDelivered === false`:

```tsx
{!result.emailDelivered && result.temporaryPassword && (
  <div
    role="alert"
    className="mt-4 rounded-md border border-amber-400 bg-amber-50 p-4
               text-sm text-amber-900"
  >
    <p className="font-semibold">
      O e-mail de credenciais não foi enviado.
    </p>
    <p className="mt-1">
      Anote a senha temporária agora — ela não será exibida novamente e não
      há recuperação de senha na plataforma.
    </p>
    <p className="mt-2 font-mono text-base tracking-wider">
      {result.temporaryPassword}
    </p>
  </div>
)}
```

### Teste de barreira

```python
# backend/tests/test_credentials_delivery.py
"""B-A29: a senha temporária nunca pode se perder."""
from __future__ import annotations

import smtplib

from app.core.config import settings
from app.models.company_dashboard import DashboardTemplate


def _template_padrao(db):
    db.add(DashboardTemplate(name="Padrao", description=None, is_default=True))
    db.commit()


def test_sem_smtp_a_senha_volta_na_resposta(client, db, admin_token, monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", None)
    _template_padrao(db)
    body = client.post(
        "/api/v1/onboarding/principal-user",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"full_name": "Novo Cliente", "email": "novo@test.com",
              "company_name": "Nova Empresa"},
    ).json()
    assert body["email_delivered"] is False
    assert body["temporary_password"], "senha perdida: cliente criado e inacessível"
    assert len(body["temporary_password"]) == 12


def test_a_senha_devolvida_realmente_autentica(client, db, admin_token, monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", None)
    _template_padrao(db)
    body = client.post(
        "/api/v1/onboarding/principal-user",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"full_name": "Novo Cliente", "email": "novo@test.com",
              "company_name": "Nova Empresa"},
    ).json()
    login = client.post("/api/v1/auth/login", json={
        "email": "novo@test.com", "password": body["temporary_password"]})
    assert login.status_code == 200


def test_com_smtp_ok_a_senha_nao_trafega(client, db, admin_token, monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.exemplo.local")
    monkeypatch.setattr("app.services.email_sender._enviar", lambda msg: True)
    _template_padrao(db)
    body = client.post(
        "/api/v1/onboarding/principal-user",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"full_name": "Novo Cliente", "email": "novo@test.com",
              "company_name": "Nova Empresa"},
    ).json()
    assert body["email_delivered"] is True
    assert body["temporary_password"] is None


def test_falha_de_smtp_nao_derruba_o_onboarding(client, db, admin_token, monkeypatch):
    """O usuário já foi committado — uma falha de SMTP não pode virar 500."""
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.inexistente.local")

    def _explode(*a, **k):
        raise smtplib.SMTPException("servidor indisponível")

    monkeypatch.setattr(smtplib, "SMTP", _explode)
    _template_padrao(db)
    resp = client.post(
        "/api/v1/onboarding/principal-user",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"full_name": "Novo Cliente", "email": "novo@test.com",
              "company_name": "Nova Empresa"},
    )
    assert resp.status_code == 201, "falha de SMTP virou erro de servidor"
    assert resp.json()["email_delivered"] is False
    assert resp.json()["temporary_password"]
```

### Checklist de validação

- [ ] `pytest tests/test_credentials_delivery.py -q` → 4 passed
- [ ] Onboarding em dev (sem SMTP) → a tela do admin exibe a senha com o aviso âmbar
- [ ] O login com a senha exibida funciona
- [ ] Onboarding com SMTP simulado → `temporary_password: null` na resposta
- [ ] Nenhum log contém a senha em texto claro (`grep` na saída de `pytest -s`)

---

# PRIORIDADE MÉDIA

---

## B-M25 — `ALLOW_PUBLIC_REGISTRATION` tem default `True` `🔴 novo`

**Categoria:** Security Misconfiguration (**A05:2021**) · Insecure Default (**CWE-1188**)

### Localização

`backend/app/core/config.py:24` — `ALLOW_PUBLIC_REGISTRATION: bool = True`

### Impacto

O `.env.example` e o `docker-compose.yml` da raiz definem `false`, e o comentário no exemplo é explícito: *"Mantenha false em produção"*. Mas o **default do código é `True`**. Um deploy que esqueça a variável — container novo, plataforma de PaaS com variáveis definidas à mão, `.env` incompleto — abre `POST /api/v1/auth/register` para qualquer pessoa, criando usuários com papel `user`.

O impacto de um cadastro público não autorizado é limitado (o usuário nasce sem empresa, então `GET /companies/me` devolve 404 e o dashboard fica vazio), mas: cria registros não auditáveis na tabela `users`, permite enumeração de e-mails já cadastrados via 409, e contradiz a postura de segurança que o restante do projeto adota.

**Princípio violado:** o default deve ser o estado seguro. Quem quer abrir o cadastro deve ter de dizê-lo.

### Correção

```python
# backend/app/core/config.py

    # Configuração de registro público.
    # Default FECHADO (B-M25): esquecer a variável não pode abrir o
    # cadastro. Clientes entram por POST /onboarding/principal-user, e
    # abrir o registro público é uma decisão que precisa ser declarada.
    ALLOW_PUBLIC_REGISTRATION: bool = False
```

Se algum ambiente depender do cadastro público, declare `ALLOW_PUBLIC_REGISTRATION=true` explicitamente no `.env` dele.

### Teste de barreira

```python
# backend/tests/test_config_defaults.py
"""B-M25 / B-M29: defaults inseguros ou divergentes não podem voltar."""
from __future__ import annotations

from app.core.config import Settings


def _settings_sem_env() -> Settings:
    """Ignora o .env local — queremos o default do CÓDIGO."""
    return Settings(DATABASE_URL="sqlite://", JWT_SECRET="x" * 32, _env_file=None)


def test_registro_publico_fechado_por_default():
    assert _settings_sem_env().ALLOW_PUBLIC_REGISTRATION is False


def test_debug_desligado_por_default():
    assert _settings_sem_env().IS_DEBUG is False


def test_access_token_curto_por_default():
    """15 min. Se este número mudar, frontend/proxy.ts e
    frontend/app/api/auth/login/route.ts precisam mudar junto (B-M29)."""
    assert _settings_sem_env().JWT_EXPIRES_MINUTES == 15
```

---

## B-M26 — `GET /admin/companies` executa 7 queries por empresa `🔴 novo`

**Categoria:** Performance / N+1 Query (**CWE-1050**)

### Localização

| Arquivo | Linha | O quê |
|---|---|---|
| `backend/app/services/company_admin.py` | **163** | `return [_load_admin_data(db, company) for company in companies], total` |
| `backend/app/services/company_admin.py` | **72–125** | `_load_admin_data` — 6 a 7 queries por empresa |

### Impacto (medido)

Sonda com contador em `before_cursor_execute`:

```
[SONDA] GET /admin/companies com 10 empresas -> 200
[SONDA]   queries executadas: 73
[SONDA]   queries por empresa: 7.0
```

Cada iteração de `_load_admin_data` dispara:

| # | Query | Observação |
|---|---|---|
| 1 | `db.get(User, company.principal_user_id)` | Pode acertar o identity map, mas normalmente não |
| 2 | `member_user_ids(...)` — sub-usuários por `parent_user_id` | **Redundante** com a query 3 |
| 3 | `sub_user_emails` — os mesmos sub-usuários, agora pelo e-mail | Mesma linha, segunda leitura |
| 4 | `count(Audit)` | |
| 5 | Lazy load de `company.dashboard` | |
| 6 | `count(DashboardCard)` | |
| 7 | `count(CompanyMessage)` | |

Com o `limit` padrão de 20, são **~143 queries por página**. Não é um problema hoje (o banco de dev tem 5 empresas), mas cresce linearmente com a base de clientes — exatamente a dimensão em que a plataforma deve crescer. Com 200 clientes e paginação de 50, uma única abertura de tela dispara ~350 queries.

Nota adicional: `member_user_ids` e `sub_user_emails` leem **a mesma linha de `users` duas vezes** com projeções diferentes. Isso não é otimização prematura a corrigir — é trabalho duplicado literal.

> **O que NÃO é N+1 aqui:** `GET /companies/{id}/messages` foi medido na mesma sonda e faz **4 queries para 12 mensagens** — o lazy load de `author_user` é resolvido pelo identity map, porque uma conversa tem poucos autores distintos. Reportar aquilo como N+1 seria falso.

### Estratégia de correção

Trocar as contagens por empresa por **três queries agregadas** para a página inteira, indexadas por `company_id` em memória. `_load_admin_data` continua existindo para o **detalhe** de uma empresa (`GET /admin/companies/{id}`), onde uma consulta por empresa é o comportamento correto.

### Código de correção completo

Substituir, em `backend/app/services/company_admin.py`, a função `list_companies_admin` e acrescentar o helper de lote:

```python
def _bulk_admin_data(db: Session, companies: list[Company]) -> list[CompanyAdminData]:
    """
    Monta o CompanyAdminData de VÁRIAS empresas com um número constante de
    queries (B-M26). `_load_admin_data` continua sendo o caminho certo para
    UMA empresa (detalhe); para uma página de listagem, ela custava ~7
    queries por linha — 143 numa página de 20.
    """
    if not companies:
        return []

    company_ids = [c.id for c in companies]
    principal_ids = [c.principal_user_id for c in companies]

    # 1 query: usuários principais + sub-usuários, de uma vez só.
    users = db.scalars(
        select(User).where(
            or_(User.id.in_(principal_ids), User.parent_user_id.in_(principal_ids))
        )
    ).all()

    principal_by_id: dict[int, User] = {}
    subs_by_parent: dict[int, list[User]] = {}
    for user in users:
        if user.parent_user_id is not None:
            subs_by_parent.setdefault(user.parent_user_id, []).append(user)
        if user.id in principal_ids:
            principal_by_id[user.id] = user

    # member_ids por principal, sem nenhuma query adicional.
    members_by_principal: dict[int, list[int]] = {
        pid: [pid, *[s.id for s in subs_by_parent.get(pid, [])]]
        for pid in principal_ids
    }
    member_to_principal: dict[int, int] = {
        member_id: pid
        for pid, members in members_by_principal.items()
        for member_id in members
    }

    # 2 queries: dashboards da página e contagem de cards por dashboard.
    dashboards = db.execute(
        select(Dashboard.id, Dashboard.company_id).where(
            Dashboard.company_id.in_(company_ids)
        )
    ).all()
    dashboard_to_company = {d_id: c_id for d_id, c_id in dashboards}

    cards_by_company: dict[int, int] = {}
    if dashboard_to_company:
        rows = db.execute(
            select(DashboardCard.dashboard_id, func.count(DashboardCard.id))
            .where(DashboardCard.dashboard_id.in_(dashboard_to_company.keys()))
            .group_by(DashboardCard.dashboard_id)
        ).all()
        for dashboard_id, count in rows:
            cards_by_company[dashboard_to_company[dashboard_id]] = count

    # 1 query: auditorias por membro, reagrupadas por empresa.
    audits_by_company: dict[int, int] = {}
    if member_to_principal:
        rows = db.execute(
            select(Audit.client_user_id, func.count(Audit.id))
            .where(Audit.client_user_id.in_(member_to_principal.keys()))
            .group_by(Audit.client_user_id)
        ).all()
        principal_to_company = {c.principal_user_id: c.id for c in companies}
        for client_user_id, count in rows:
            principal_id = member_to_principal[client_user_id]
            company_id = principal_to_company[principal_id]
            audits_by_company[company_id] = audits_by_company.get(company_id, 0) + count

    # 1 query: mensagens gerais por empresa.
    messages_by_company: dict[int, int] = dict(
        db.execute(
            select(CompanyMessage.company_id, func.count(CompanyMessage.id))
            .where(CompanyMessage.company_id.in_(company_ids))
            .group_by(CompanyMessage.company_id)
        ).all()
    )

    resultado: list[CompanyAdminData] = []
    for company in companies:
        principal = principal_by_id.get(company.principal_user_id)
        if principal is None:
            # FK RESTRICT garante que não acontece; defensivo, e coerente
            # com o comportamento de _load_admin_data.
            raise CompanyNotFoundError("Usuário principal da empresa não encontrado")

        subs = sorted(
            subs_by_parent.get(company.principal_user_id, []),
            key=lambda u: u.email,
        )
        resultado.append(
            CompanyAdminData(
                company=company,
                principal_full_name=principal.full_name,
                principal_email=principal.email,
                sub_user_count=len(subs),
                sub_user_emails=[s.email for s in subs],
                audit_count=audits_by_company.get(company.id, 0),
                dashboard_card_count=cards_by_company.get(company.id, 0),
                company_message_count=messages_by_company.get(company.id, 0),
            )
        )
    return resultado


def list_companies_admin(
    db: Session, *, search: str | None, skip: int, limit: int
) -> tuple[list[CompanyAdminData], int]:
    """Lista paginada de empresas para a tela "Lista de Empresas",
    com busca por nome/e-mail da empresa OU nome/e-mail do usuário
    principal (o admin normalmente lembra de um dos dois, não
    necessariamente do nome exato da empresa).

    Custo: constante em número de queries (B-M26) — 2 para a página
    (contagem + linhas) + 5 agregadas, independentemente de `limit`."""

    base_query = select(Company).join(User, User.id == Company.principal_user_id)

    if search:
        term = f"%{search.strip()}%"
        base_query = base_query.where(
            or_(
                Company.name.ilike(term),
                Company.email.ilike(term),
                User.full_name.ilike(term),
                User.email.ilike(term),
            )
        )

    total = (
        db.scalar(
            select(func.count()).select_from(
                base_query.with_only_columns(Company.id).subquery()
            )
        )
        or 0
    )

    companies = list(
        db.scalars(
            base_query.order_by(Company.name.asc()).offset(skip).limit(limit)
        ).all()
    )

    return _bulk_admin_data(db, companies), total
```

Acrescentar ao bloco de imports do arquivo:

```python
from app.models.company_dashboard import Company, Dashboard, DashboardCard
```

### Teste de barreira

```python
# backend/tests/test_query_budget.py
"""B-M26: a listagem de empresas tem custo constante em queries."""
from __future__ import annotations

import pytest
from sqlalchemy import event

from app.core.security import hash_password
from app.models.company_dashboard import Company, Dashboard, DashboardCard
from app.models.user import User
from tests.conftest import engine


class ContadorDeQueries:
    def __init__(self):
        self.count = 0

    def __enter__(self):
        event.listen(engine, "before_cursor_execute", self._on)
        return self

    def __exit__(self, *exc):
        event.remove(engine, "before_cursor_execute", self._on)

    def _on(self, conn, cursor, statement, params, context, executemany):
        self.count += 1


def _semear_empresas(db, quantidade: int) -> None:
    for i in range(quantidade):
        user = User(
            full_name=f"Cliente {i}",
            email=f"cliente{i}@test.com",
            password_hash=hash_password("Cliente123!"),
            role="user",
        )
        db.add(user)
        db.flush()
        company = Company(
            name=f"Empresa {i}",
            email=f"empresa{i}@test.com",
            principal_user_id=user.id,
        )
        db.add(company)
        db.flush()
        dashboard = Dashboard(company_id=company.id, title=f"Dash {i}")
        db.add(dashboard)
        db.flush()
        db.add(DashboardCard(dashboard_id=dashboard.id, title=f"Card {i}", tag="x"))
    db.commit()


@pytest.mark.parametrize("quantidade", [5, 20])
def test_custo_da_listagem_nao_cresce_com_o_numero_de_empresas(
    client, db, admin_token, quantidade
):
    _semear_empresas(db, quantidade)
    with ContadorDeQueries() as contador:
        resp = client.get(
            f"/api/v1/admin/companies?limit={quantidade}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == quantidade
    assert contador.count <= 15, (
        f"{contador.count} queries para {quantidade} empresas — o N+1 de "
        "B-M26 voltou (o custo deve ser constante, não linear)"
    )


def test_a_listagem_devolve_os_mesmos_numeros_do_detalhe(client, db, admin_token):
    """A otimização não pode mudar o resultado."""
    _semear_empresas(db, 3)
    lista = client.get(
        "/api/v1/admin/companies",
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()["items"]
    for item in lista:
        detalhe = client.get(
            f"/api/v1/admin/companies/{item['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        ).json()
        assert item["sub_user_count"] == detalhe["sub_user_count"]
        assert item["sub_user_emails"] == detalhe["sub_user_emails"]
        assert item["principal_email"] == detalhe["principal_email"]
```

---

## B-M27 — Todo cliente principal recebe um e-mail dizendo que é sub-usuário `🔴 novo`

**Categoria:** Qualidade / Comunicação com o usuário

### Localização

| Arquivo | Linha | O quê |
|---|---|---|
| `backend/app/api/v1/admin_onboarding.py` | **125–131** | Comentário assumido: *"Reuso da infraestrutura de email"* — chama `send_sub_user_credentials_email` para o usuário **principal** |
| `backend/app/services/email_sender.py` | **32** | `msg["Subject"] = "Acesso de sub-usuário - Plataforma de Auditoria"` |
| `backend/app/services/email_sender.py` | **37** | `f"Você foi adicionado como sub-usuário de {principal_name}.\n\n"` |

### Impacto

A chamada passa `sub_user_name=principal_user.full_name` e `principal_name=company.name`. O e-mail que chega ao **primeiro contato** de cada novo cliente da plataforma diz, literalmente:

> **Assunto:** Acesso de sub-usuário - Plataforma de Auditoria
>
> OláMaria Silva,
>
> Você foi adicionado como sub-usuário de **Construtora Alfa Ltda**.

Três problemas de uma vez: o cliente é o **responsável** pela conta, não sub-usuário; ele foi adicionado à **própria empresa**, não subordinado a ela; e falta o espaço depois de "Olá" (ver **B-B22**).

É a primeira impressão da plataforma junto ao cliente pagante, e ela está errada em três frases de quatro.

Confirmado na saída real do log de dev:

```
[DEV-EMAIL] Sub_user criado: Novo Cliente <novo@test.com>(principal: Nova Empresa)
```

### Correção

Já contemplada em **B-A29**: a função `send_principal_user_credentials_email` criada lá substitui o reuso, com assunto e corpo próprios. As duas correções devem ser aplicadas juntas — são o mesmo arquivo.

### Teste de barreira

```python
# backend/tests/test_email_content.py
"""B-M27: cada papel recebe o e-mail que corresponde ao seu papel."""
from __future__ import annotations

from email.message import EmailMessage

import pytest

from app.core.config import settings
from app.services import email_sender


@pytest.fixture
def capturar_emails(monkeypatch) -> list[EmailMessage]:
    enviados: list[EmailMessage] = []
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.exemplo.local")
    monkeypatch.setattr(settings, "SMTP_FROM", "nao-responda@exemplo.local")
    monkeypatch.setattr(
        email_sender, "_enviar", lambda msg: (enviados.append(msg), True)[1]
    )
    return enviados


def test_email_do_principal_nao_diz_sub_usuario(capturar_emails):
    email_sender.send_principal_user_credentials_email(
        to_email="maria@cliente.com",
        full_name="Maria Silva",
        company_name="Construtora Alfa Ltda",
        temporary_password="Senha-Temp-12",
    )
    msg = capturar_emails[0]
    corpo = msg.get_content()
    assert "sub-usuário" not in msg["Subject"].lower()
    assert "sub-usuário" not in corpo.lower()
    assert "Construtora Alfa Ltda" in corpo
    assert "Olá, Maria Silva" in corpo          # B-B22: com espaço e vírgula
    assert "Senha-Temp-12" in corpo


def test_email_do_sub_usuario_continua_dizendo_sub_usuario(capturar_emails):
    email_sender.send_sub_user_credentials_email(
        to_email="joao@cliente.com",
        sub_user_name="João Souza",
        principal_name="Maria Silva",
        temporary_password="Senha-Temp-34",
    )
    corpo = capturar_emails[0].get_content()
    assert "sub-usuário de Maria Silva" in corpo
    assert "Olá, João Souza" in corpo


def test_sem_smtp_nenhuma_senha_vai_para_o_log(capturar_emails, monkeypatch, caplog):
    monkeypatch.setattr(settings, "SMTP_HOST", None)
    entregue = email_sender.send_principal_user_credentials_email(
        to_email="maria@cliente.com",
        full_name="Maria Silva",
        company_name="Alfa",
        temporary_password="SENHA-SECRETA-99",
    )
    assert entregue is False
    assert "SENHA-SECRETA-99" not in caplog.text
```

---

## B-M28 — A guarda de path traversal ficou só na exclusão; o download não a tem `🔴 novo`

**Categoria:** Insecure Design (**A04:2021**) · Defesa em profundidade incompleta

### Localização

| Arquivo | Linha | Estado |
|---|---|---|
| `backend/app/services/storage.py` | **25–34** | `get_absolute_path()` — `return Path(storage_key)`, **sem guarda** |
| `backend/app/services/storage.py` | **55–65** | `delete_files()` — resolve e valida `relative_to(upload_root)` ✅ |
| `backend/app/api/v1/admin.py` | **307** | `file_path = get_absolute_path(evidence.storage_key)` → `FileResponse` |

### Impacto

O BLOCO P (P.2) acrescentou a guarda correta — *"recusa `storage_key` que resolva para fora de `uploads/`"* — mas a colocou **dentro de `delete_files()`**, não no ponto único por onde toda resolução de caminho passa. `get_absolute_path()` é a função que o **download** usa, e ela continua devolvendo `Path(storage_key)` sem verificar nada.

**Não é explorável hoje.** `storage_key` é gravado exclusivamente por `save_file()`, que gera `uuid4().hex` + extensão validada contra uma allowlist. Não há nenhum caminho pelo qual entrada do usuário chegue a esse campo.

O problema é de **projeto**, e é exatamente da mesma família de B-A26: a garantia existe num lugar e não no outro, e nada no código informa que ela deveria existir nos dois. Basta que uma futura importação de dados, um script de migração de storage, ou um backend S3 grave um `storage_key` de outra forma para que o download passe a servir arquivos arbitrários do sistema de arquivos ao admin.

A correção move a guarda para onde ela cobre **todos** os consumidores presentes e futuros.

### Código de correção completo

Substituir, em `backend/app/services/storage.py`, `get_absolute_path` e `delete_files`:

```python
class StorageKeyOutsideUploadDirError(ValueError):
    """`storage_key` resolve para fora de uploads/ — recusado (B-M28)."""


def _resolver_dentro_do_upload_dir(storage_key: str) -> Path:
    """
    Resolve `storage_key` e garante que o caminho final está dentro de
    UPLOAD_DIR. Ponto ÚNICO de verificação: a guarda introduzida em P.2
    vivia só em delete_files(), então o download (admin.py::
    download_evidence) resolvia sem ela — mesma classe de assimetria que
    causou B-A26, onde o storage sabia gravar e ler mas não apagar.
    """
    upload_root = UPLOAD_DIR.resolve()
    caminho = (UPLOAD_DIR / Path(storage_key).name).resolve()

    # `Path(storage_key).name` já descarta qualquer componente de diretório
    # ("../../etc/passwd" vira "passwd"). A verificação abaixo é a segunda
    # barreira, para o caso de o nome conter algo que o SO resolva de forma
    # inesperada (symlink, nome reservado do Windows).
    try:
        caminho.relative_to(upload_root)
    except ValueError:
        raise StorageKeyOutsideUploadDirError(
            f"storage_key resolve para fora de uploads/: {storage_key!r}"
        )
    return caminho


def get_absolute_path(storage_key: str) -> Path:
    """
    Resolve o caminho físico de um arquivo já salvo, a partir do
    `storage_key` gravado em Evidence.storage_key por save_file().

    Ponto único de mudança se o backend de armazenamento evoluir para
    S3/Azure Blob (ver services/storage_backend.py). Levanta
    `StorageKeyOutsideUploadDirError` para qualquer chave que escape do
    diretório de uploads — quem chama converte para 404, nunca para 500
    e nunca servindo o arquivo.
    """
    return _resolver_dentro_do_upload_dir(storage_key)


def delete_files(storage_keys: list[str]) -> int:
    """
    Apaga do disco os arquivos de `storage_keys` e devolve quantos foram
    de fato removidos (B-A26).

    Deve ser chamada SOMENTE depois de o commit da transação que apagou
    os registros correspondentes ter tido sucesso: apagar antes deixaria
    registro órfão apontando para arquivo inexistente em caso de rollback.

    Nunca levanta exceção — a transação de banco já está committada e não
    pode ser desfeita por causa de um arquivo. Cada falha vira log
    estruturado, para varredura posterior de órfãos
    (scripts/prune_orphan_uploads.py).
    """
    removed = 0
    for storage_key in storage_keys:
        try:
            path = get_absolute_path(storage_key)
        except StorageKeyOutsideUploadDirError:
            logger.warning(
                "evidence_file_delete_outside_upload_dir", storage_key=storage_key
            )
            continue

        try:
            path.unlink(missing_ok=True)
            removed += 1
        except OSError as exc:
            logger.warning(
                "evidence_file_delete_failed", storage_key=storage_key, error=str(exc)
            )
    return removed
```

E, em `backend/app/api/v1/admin.py::download_evidence`, tratar a exceção:

```python
from app.services.storage import (
    StorageKeyOutsideUploadDirError,
    get_absolute_path,
)

# ... dentro de download_evidence(), substituindo o bloco de resolução:

    try:
        file_path = get_absolute_path(evidence.storage_key)
    except StorageKeyOutsideUploadDirError:
        # Registro apontando para fora do storage: nunca serve o arquivo.
        # 404 (e não 500) para não revelar a existência do caminho.
        logger.warning(
            "evidence_download_outside_upload_dir",
            evidence_id=evidence.id,
            storage_key=evidence.storage_key,
        )
        raise HTTPException(status_code=404, detail="Evidência não encontrada")

    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail="Arquivo não encontrado no armazenamento"
        )
```

### Teste de barreira

```python
# backend/tests/test_storage_path_guard.py
"""B-M28: a guarda de path traversal vale para TODOS os consumidores."""
from __future__ import annotations

import pytest

from app.services.storage import (
    StorageKeyOutsideUploadDirError,
    delete_files,
    get_absolute_path,
)

CHAVES_MALICIOSAS = [
    "../../../etc/passwd",
    "..\\..\\..\\Windows\\System32\\config\\SAM",
    "/etc/shadow",
    "uploads/../../segredo.env",
]


@pytest.mark.parametrize("chave", CHAVES_MALICIOSAS)
def test_get_absolute_path_recusa_ou_confina(chave):
    """Ou levanta, ou devolve um caminho dentro de uploads/ — nunca um
    caminho arbitrário do sistema de arquivos."""
    from app.services.storage import UPLOAD_DIR

    try:
        resolvido = get_absolute_path(chave)
    except StorageKeyOutsideUploadDirError:
        return
    resolvido.relative_to(UPLOAD_DIR.resolve())


@pytest.mark.parametrize("chave", CHAVES_MALICIOSAS)
def test_delete_files_nunca_toca_fora_de_uploads(chave, tmp_path):
    alvo = tmp_path / "nao-me-apague.txt"
    alvo.write_text("conteudo importante", encoding="utf-8")
    delete_files([chave])
    assert alvo.exists(), "delete_files apagou um arquivo fora de uploads/"


def test_download_de_evidencia_com_chave_invalida_da_404(
    client, db, admin_token, audit_with_control, principal_user
):
    from app.models.evidence import Evidence

    _, audit_control = audit_with_control
    evidencia = Evidence(
        audit_control_id=audit_control.id,
        uploaded_by_id=principal_user.id,
        file_name="passwd",
        storage_key="../../../etc/passwd",
        mime_type="text/plain",
        size_bytes=10,
    )
    db.add(evidencia)
    db.commit()

    resp = client.get(
        f"/api/v1/admin/evidences/{evidencia.id}/download",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404
```

---

## B-M29 — Default de `JWT_EXPIRES_MINUTES` diverge entre backend (15) e frontend (60) `🔴 novo`

**Categoria:** Security Misconfiguration (**A05:2021**)

### Localização

| Arquivo | Linha | Default |
|---|---|---|
| `backend/app/core/config.py` | **28** | `JWT_EXPIRES_MINUTES: int = 15` |
| `frontend/proxy.ts` | **30** | `Number(process.env.JWT_EXPIRES_MINUTES ?? 60) * 60` |
| `frontend/app/api/auth/login/route.ts` | **12** | `Number(process.env.JWT_EXPIRES_MINUTES ?? 60) * 60` |

### Impacto

Se `JWT_EXPIRES_MINUTES` não estiver definida em `frontend/.env.local`, o cookie `access_token` recebe `maxAge` de **3600 s**, enquanto o JWT dentro dele expira em **900 s**. Durante 45 minutos o navegador carrega um cookie que o backend recusa.

O `proxy.ts` compensa: detecta o token expirado e renova via `refresh_token`. Então o usuário não percebe. Mas a consequência é real:

- **Cada navegação após 15 minutos dispara um round-trip extra** ao backend (`POST /auth/refresh`) que não seria necessário se os dois números coincidissem.
- **O `maxAge` deixa de significar o que promete.** Quem lê `proxy.ts` para entender a vida da sessão encontra 60 minutos; a resposta certa é 15.
- **A divergência é silenciosa e assimétrica.** Ninguém percebe até investigar por que o `/auth/refresh` aparece com uma frequência inesperada no log.

Os `.env` reais do projeto definem a variável, então o efeito não aparece hoje. É o mesmo tipo de armadilha de B-M25: o default só se manifesta quando alguém esquece algo — que é exatamente quando não se quer uma surpresa.

### Correção

**1. `frontend/proxy.ts:29-33`:**

```typescript
/**
 * Os defaults abaixo espelham os de backend/app/core/config.py
 * (JWT_EXPIRES_MINUTES = 15, JWT_REFRESH_EXPIRES_DAYS = 7). Divergir
 * fazia o cookie sobreviver 45 min ao token que ele carrega (B-M29):
 * o proxy renovava em silêncio, escondendo a inconsistência atrás de um
 * round-trip extra a cada navegação.
 */
const ACCESS_TOKEN_MAX_AGE_SECONDS =
  Number(process.env.JWT_EXPIRES_MINUTES ?? 15) * 60;

const REFRESH_TOKEN_MAX_AGE_SECONDS =
  Number(process.env.JWT_REFRESH_EXPIRES_DAYS ?? 7) * 24 * 60 * 60;
```

**2. `frontend/app/api/auth/login/route.ts:11-14`:**

```typescript
// Espelha backend/app/core/config.py — ver B-M29.
const ACCESS_TOKEN_MAX_AGE_SECONDS =
  Number(process.env.JWT_EXPIRES_MINUTES ?? 15) * 60;
const REFRESH_TOKEN_MAX_AGE_SECONDS =
  Number(process.env.JWT_REFRESH_EXPIRES_DAYS ?? 7) * 24 * 60 * 60;
```

**3.** O teste `test_access_token_curto_por_default` de **B-M25** já protege o lado do backend: se alguém mudar o 15, o teste falha e a mensagem aponta os dois arquivos de frontend a atualizar junto.

---

# PRIORIDADE BAIXA

---

## B-B17 — Bloco de validação de extensão duplicado no upload `🔴 novo`

**Localização:** `backend/app/api/v1/client.py:180-194`

O mesmo `if ext not in ALLOWED_EXTENSIONS: raise HTTPException(415, ...)` aparece **duas vezes seguidas**, precedido de dois comentários diferentes (`# Validar extensão` e `# Validar extensão ANTES de ler qualquer byte`) e de duas atribuições idênticas de `filename` e `ext`. Resquício da correção de B-M22: o bloco novo foi acrescentado sem remover o antigo.

Sem impacto funcional — a segunda checagem é sempre redundante. Mas quem for alterar a regra de extensão vai alterar uma das duas cópias.

**Correção — substituir as linhas 180 a 194 por:**

```python
    # Validar extensão ANTES de ler qualquer byte (B-M22): recusar um
    # arquivo de 2 GB pelo nome custa nada; recusá-lo depois de lê-lo
    # custa 2 GB de RAM.
    filename = file.filename or "upload.bin"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415, detail=f"Tipo de arquivo não permitido: {ext}"
        )
```

---

## B-B18 — Typo `TimestampMixim` desde o primeiro commit `🔴 novo`

**Localização:** `backend/app/db/mixins.py:9` — `class TimestampMixim:` (deveria ser `TimestampMixin`)

Presente desde `456e10f` e propagado para `models/user.py:9`, `models/audit.py:18` e `models/audit_control.py:23`. Não tem efeito em runtime nem no schema (o nome da classe Python não vai para o banco) — é ruído de leitura que já sobreviveu a 50 commits.

**Correção:** renomear a classe e as 3 importações. Nenhuma migration é necessária.

```python
# backend/app/db/mixins.py
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

```bash
# nos 3 modelos que herdam
cd backend
grep -rl "TimestampMixim" app/ | xargs sed -i 's/TimestampMixim/TimestampMixin/g'
python -m pytest -q          # deve continuar 202 passed
python -m ruff check app     # deve continuar limpo
```

---

## B-B19 — `SoftDeleteMixin` declarado e nunca consultado `🔴 novo`

**Localização:** `backend/app/db/mixins.py:22-30`, aplicado a `User`, `Audit`, `AuditControl`

A coluna `deleted_at` existe nas três tabelas (migration `5e977e8b49da`) e a propriedade `is_deleted` existe no modelo. **Nenhuma query do backend filtra por ela** — `grep -rn "deleted_at" backend/app --include=*.py` fora de `mixins.py` retorna **zero** ocorrências.

Isso é pior do que não ter soft delete: o schema anuncia uma capacidade que o código não honra. Um desenvolvedor que veja `deleted_at` e assuma que exclusões são lógicas vai escrever código errado — e um registro marcado como excluído continuaria aparecendo em toda listagem.

Há uma tensão real a resolver antes de decidir: **M.1 entregou exclusão de empresa em cascata física e transacional, e o BLOCO P a estendeu ao disco (F73)**. Adotar soft delete exigiria revisitar as duas e responder o que acontece com o **arquivo** de uma evidência logicamente excluída — a resposta errada reabre B-A26.

**Correção:** decisão de produto (N11 em `relatorio_funcionalidades.md`), não patch. Enquanto ela não vier, registrar a limitação no próprio código:

```python
class SoftDeleteMixin:
    """
    ⚠️ NÃO IMPLEMENTADO (B-B19). A coluna existe (migration 5e977e8b49da)
    mas NENHUMA query do backend filtra por ela — todas as exclusões são
    FÍSICAS, incluindo a cascata de empresa (services/company_admin.py) e
    os arquivos em disco (services/storage.py::delete_files).

    Não assuma que gravar `deleted_at` esconde um registro: não esconde.
    Antes de ativar o soft delete é preciso decidir o que acontece com o
    ARQUIVO de uma evidência logicamente excluída — a resposta errada
    reabre B-A26 (LGPD). Ver N11 em docs/relatorio_funcionalidades.md.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
```

---

## B-B20 — `structlog` sem versão fixada `🔴 novo`

**Localização:** `backend/requirements.txt:17` — `structlog` (sem `==` nem `>=`)

É a **única** dependência do arquivo sem qualquer restrição de versão. Todas as outras têm piso (`fastapi>=0.115.0`) ou pin exato (`slowapi==0.1.9`). Um `pip install -r requirements.txt` em duas datas diferentes pode instalar versões incompatíveis, e `configure_logging()` depende diretamente da API de processadores do structlog, que já mudou entre majors.

**Correção:**

```
# backend/requirements.txt
structlog>=24.1.0,<26.0.0
```

O piso garante a API de processadores usada em `core/logging.py`; o teto evita que um major novo entre sem revisão. Depois: `pip install -r requirements.txt && python -m pytest -q`.

---

## B-B21 — Typos herdados em identificadores e mensagens ao usuário `🔴 novo`

| Arquivo | Linha | Atual | Correto |
|---|---|---|---|
| `backend/app/api/v1/company_messages.py` | 37 | `"sub-user sem vísculo com usuário principal"` | `vínculo` |
| `backend/app/api/v1/company_messages.py` | 55–56 | `ower_user_id` | `owner_user_id` |
| `backend/app/api/v1/company_messages.py` | 103 | `"Empresa não encontrada paa este usuário"` | `para` |
| `frontend/proxy.ts` | 32, 96 | `REFREH_TOKEN_MAX_AGE_SECONDS` | `REFRESH_...` |
| `frontend/proxy.ts` | 80, 151, 159, 164 | `setSessionCoookies` | `setSessionCookies` |
| `frontend/proxy.ts` | 87 | `process.env.NODE_ENV == "production"` | `===` (a linha 94, idêntica em propósito, usa `===`) |

As duas mensagens de erro são **visíveis ao usuário final** — chegam à tela pelo `detail` da resposta HTTP.

**Correção (comandos):**

```bash
cd backend
sed -i 's/vísculo/vínculo/; s/ower_user_id/owner_user_id/g; s/encontrada paa este/encontrada para este/' \
  app/api/v1/company_messages.py
python -m ruff check app && python -m pytest -q

cd ../frontend
sed -i 's/REFREH_TOKEN_MAX_AGE_SECONDS/REFRESH_TOKEN_MAX_AGE_SECONDS/g; s/setSessionCoookies/setSessionCookies/g; s/NODE_ENV == "production"/NODE_ENV === "production"/' \
  proxy.ts
npx tsc --noEmit && npx eslint
```

---

## B-B22 — `Olá{nome}` sem espaço no e-mail de credenciais `🔴 novo`

**Localização:** `backend/app/services/email_sender.py:36` — `f"Olá{sub_user_name},\n\n"`

Produz `OláMaria Silva,`. É a primeira linha do primeiro e-mail que qualquer usuário recebe da plataforma.

**Correção:** já contemplada nos arquivos completos de **B-A29**/**B-M27** (`f"Olá, {full_name}.\n\n"`), e coberta pelo teste `test_email_do_principal_nao_diz_sub_usuario`, que afirma `"Olá, Maria Silva" in corpo`.

---

## B-B23 — `403` em vez de `404` revela a existência de `company_id` alheio `🔴 novo`

**Localização:**
- `backend/app/api/v1/company_messages.py:57-59`
- `backend/app/api/v1/dashboard_cards.py:73-77` e `192-196`

Ao pedir uma empresa de outro cliente, a API responde **403 "Acesso restrito à empresa"**; ao pedir um `company_id` inexistente, responde **404**. A diferença permite enumerar quais IDs de empresa existem na plataforma — um cliente consegue descobrir quantas empresas a auditoria atende e em que faixa de IDs.

Confirmado por sonda: cliente lendo card de outra empresa → `403`; listando cards de outra empresa → `403`.

Impacto real baixo (nenhum dado da outra empresa vaza, só a existência do ID), e a decisão de responder 403 é defensável — mas o restante do projeto já adota a convenção oposta: `client.py::get_my_audit` devolve **404** com a mensagem *"Auditoria não encontrada ou sem acesso"*, deliberadamente ambígua.

**Correção — uniformizar em 404** nos três pontos:

```python
# backend/app/api/v1/company_messages.py::_get_company_with_access
def _get_company_with_access(
    db: Session, company_id: int, current_user: User
) -> Company:
    """
    Devolve 404 — e não 403 — quando a empresa existe mas não é do
    chamador (B-B23). Distinguir "não existe" de "existe e não é sua"
    permite enumerar os company_id da plataforma. Mesma convenção já
    usada em client.py::get_my_audit ("não encontrada ou sem acesso").
    """
    company = db.get(Company, company_id)

    if company is not None and current_user.role == "admin":
        return company

    if company is not None:
        owner_user_id = _resolve_owner_user_id(current_user)
        if company.principal_user_id == owner_user_id:
            return company

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Empresa não encontrada ou sem acesso",
    )
```

Aplicar o mesmo padrão a `dashboard_cards.py::_get_company_with_access` e `::_get_card_with_access` (mensagens *"Empresa não encontrada ou sem acesso"* e *"Card não encontrado ou sem acesso"*).

> ⚠️ **Atenção ao aplicar:** `tests/test_authorization_matrix.py` e `tests/test_company_messages.py` afirmam `403` em alguns casos. Atualize as asserções junto — e prefira uma constante compartilhada nos testes a repetir o número, para que a próxima mudança de convenção seja de uma linha só.

---

# Achados fechados desde a rev. 8.0

Verificado item a item nesta revisão, por execução e por `grep`:

| ID | Achado (rev. 8.0) | Fechado em | Verificação nesta revisão |
|---|---|---|---|
| 🔴 **B-C23** | Credenciais reais versionadas e publicadas | `4fd576f` (P.0) | ✅ `git log --all -S` com a senha atual do `.env`: **nenhum commit**. `db_auditoria.sql` removido; `.env.example` com 21 placeholders; gitleaks no pre-commit da **raiz** e no job `secrets` do CI |
| 🟠 **B-A23** | Cliente declarava a própria conformidade | `4fd576f` (P.1) | ✅ `require_admin` em `/cards/{id}/status` e `/checklist-items/{id}/toggle`; `ADMIN_ONLY_ENTRY_TYPES` recusa `CHECKLIST`/`HISTORY`/`CHAT_ANSWER`; `core/policy.py` existe. **Ressalva: só a escrita — ver B-A28** |
| 🟠 **B-A24** | `apply-template` duplicava cards pré-O.3 | `4fd576f` (P.3) | ✅ Migration `a3d81f4c7b02` (backfill por título não-ambíguo) + `b7c02e91d4a5` (`UniqueConstraint`); `apply_template_to_company` adota órfãos por título e reporta `adopted_count` |
| 🟠 **B-A25** | Excluir template em uso destruía o vínculo | `4fd576f` (P.3) | ✅ `TemplateInUseError` → 409 em `delete_template` e `delete_template_card`; rota `POST /admin/templates/{id}/cards` restaurada |
| 🟠 **B-A26** | Evidências nunca apagadas do disco | `4fd576f` (P.2) | ✅ `storage.delete_files()` chamada após o commit em `companies.py:222`; `storage_key` coletados antes da cascata; `deleted_evidence_files` no resumo; `scripts/prune_orphan_uploads.py` existe |
| 🟡 **B-M21** | CSP e HSTS ausentes | `4fd576f` + `34f8444` | ✅ 7 headers; CSP duplo (`API_CSP` × `DOCS_CSP`); HSTS sob HTTPS; `tests/test_security_headers.py` varre o HTML real de `/docs` |
| 🟡 **B-M22** | Upload lia o arquivo inteiro em memória | `4fd576f` | ✅ `_read_limited()` lê em blocos de 1 MB e aborta com 413 ao ultrapassar |
| 🟡 **B-M23** | `affected_count` contava cards não afetados | `4fd576f` (P.3.6) | ✅ `bulk_update_cards` só incrementa quando a operação de fato alterou o card; `restore_from_template` ignora card sem origem |
| 🟡 **B-M24** | N+1 na listagem de templates | `4fd576f` | ✅ `list_templates` usa `outerjoin` + `group_by` numa query só |
| 🟡 **B-M15** | Typo `decore_token` | `4fd576f` (P.4) | ✅ `grep decore_token backend/` → **0 ocorrências** |
| 🟡 **B-M18** | `require_main_user` não validava `parent_user_id` | `4fd576f` (P.4) | ✅ `deps.py:62` — `if current_user.role != "user" or current_user.parent_user_id is not None` |
| 🟢 **B-B09** | Typo no nome do pacote | `4fd576f` | ✅ `plataforma-auditoria-frontend` |
| 🟢 **B-B10** | Rota morta `GET /api/v1/Monitoring` | `4fd576f` | ✅ `grep Monitoring backend/app` → **0** |
| 🟢 **B-B11** | Atalhos de dev na home pública | `4fd576f` | ✅ `app/page.tsx:90` — `process.env.NODE_ENV === "development" && (` |
| 🟢 **B-B13** | `python-jose` sem monitoramento de CVE | `4fd576f` | ✅ `pip-audit -r requirements.txt` no job `backend` do CI |
| 🟢 **B-B14** | `db_auditoria.sql` legado | `4fd576f` | ✅ Removido do índice (`git log` confirma) |
| 🟢 **B-B15** | Schema `DashboardCardListItem` órfão | `4fd576f` | ✅ `grep DashboardCardListItem backend/app` → **0** |
| 🟢 **B-B16** | `python-dotenv` não declarado | `4fd576f` | ✅ `requirements.txt:7` — `python-dotenv>=1.0.0` |

**18 de 18 achados da rev. 8.0 fechados.**

---

# Plano de correção sugerido

| Ordem | Achado | Por quê nesta posição | Esforço |
|---|---|---|---|
| 1 | **B-A27** | Único explorável sem credencial, e a correção é isolada (2 arquivos, sem migration) | 1 h |
| 2 | **B-A29 + B-M27** | Mesmo arquivo (`email_sender.py`), mesma entrega. B-A29 é o único achado que já pode ter produzido dano — contas inacessíveis criadas em dev | 3 h |
| 3 | **B-A28** | Fecha a metade que faltava de B-A23; precisa acompanhar `policy.py` | 2 h |
| 4 | **B-M25 + B-M29** | Dois defaults, um teste (`test_config_defaults.py`) que protege os dois | 30 min |
| 5 | **B-M28** | Move a guarda de P.2 para o ponto único — pré-requisito de qualquer storage novo | 1 h 30 |
| 6 | **B-M26** | Sem urgência operacional hoje, mas é a correção mais delicada (muda um caminho já testado) — melhor depois das outras estarem verdes | 3 h |
| 7 | **B-B17 … B-B23** | Limpeza em lote, num commit próprio | 2 h |
| | **Total** | | **~13 h** |

> **Sequência importa em dois pontos:** B-A29 e B-M27 tocam o mesmo arquivo e devem sair juntos; B-M28 deve preceder qualquer implementação de `StorageBackend` para S3/Azure, senão a guarda nasce ausente no backend novo — a mesma lacuna que produziu B-A26.

---

*Auditoria conduzida em 2026-08-26 sobre `34f8444`. Todos os 15 achados foram confirmados por execução — 13 sondas escritas para esta revisão, incluindo contagem de queries SQL por requisição. Duas hipóteses foram **refutadas** pelas sondas e não constam do relatório: o N+1 suspeito em `GET /companies/{id}/messages` (4 queries para 12 mensagens — o identity map resolve) e a diferença de tempo entre login com e-mail existente e inexistente (razão 0,9x — sem oráculo de enumeração). As sondas foram removidas do repositório ao fim da análise; os testes de barreira propostos acima são a versão permanente delas.*
