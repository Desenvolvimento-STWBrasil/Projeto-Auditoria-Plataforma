# Configurar deploy via SSH no GitHub Actions (secrets + chave)

> Guia genérico para qualquer projeto que faça deploy via `appleboy/ssh-action`
> (ou similar) a partir de um workflow do GitHub Actions. Cobre a geração da
> chave, o cadastro dos secrets e os dois erros mais comuns que já vimos
> acontecer nesse tipo de setup.

---

## Pré-requisito: secrets esperados pelo workflow

Um job de deploy típico usa algo assim:

```yaml
  deploy:
    steps:
      - uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.PROD_SSH_KEY }}
          port: ${{ secrets.PROD_SSH_PORT || 22 }}
          script: |
            ...
```

Ou seja, precisa de 3 secrets obrigatórios + 1 opcional:

| Secret | Obrigatório | Valor |
|---|---|---|
| `PROD_HOST` | sim | IP ou domínio do servidor |
| `PROD_USER` | sim | usuário SSH usado para conectar |
| `PROD_SSH_KEY` | sim | conteúdo completo da chave **privada** SSH |
| `PROD_SSH_PORT` | não | porta SSH, só precisa criar se não for a 22 |

O aviso do VS Code/editor "Context access might be invalid: PROD_HOST" (ou
similar) para esses nomes normalmente significa que **os secrets ainda não
existem no repositório** — vale confirmar com `gh secret list` antes de
assumir que é falso positivo do linter.

---

## Parte 1 — Gerar o par de chaves SSH dedicado ao deploy

Nunca reutilize sua chave pessoal para isso — gere uma chave nova, só para
CI/CD, sem passphrase (obrigatório para uso automatizado).

### Opção A — gerar direto no servidor de produção (recomendado)

Mais simples porque a chave pública já nasce no lugar certo.

```bash
ssh usuario_atual@host_do_servidor
```

Já dentro do servidor, como o usuário que o workflow vai usar (`PROD_USER`):

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/deploy_key -N ""

mkdir -p ~/.ssh
cat ~/.ssh/deploy_key.pub >> ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys

cat ~/.ssh/deploy_key   # copie essa saída inteira — vai para o secret PROD_SSH_KEY
```

Teste antes de sair do servidor:

```bash
ssh -i ~/.ssh/deploy_key -o StrictHostKeyChecking=no PROD_USER@localhost echo ok
```

### Opção B — gerar localmente e copiar a pública para o servidor

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/deploy_key -N ""
ssh-copy-id -i ~/deploy_key.pub usuario@host
```

A chave gerada fica **fora da pasta do projeto** (nunca commitar chave
privada no git). A privada (`deploy_key`, sem `.pub`) é o que vai no secret;
a pública vai para `authorized_keys` do servidor.

---

## Parte 2 — Cadastrar os secrets no GitHub

1. Acesse `https://github.com/<org>/<repo>/settings/secrets/actions`
   (ou: repositório → **Settings** → **Secrets and variables** → **Actions**).
2. Aba **Secrets**, sub-aba **Repository secrets** → **New repository secret**.
3. Repita para cada um:
   - **Name**: exatamente `PROD_HOST`, `PROD_USER`, `PROD_SSH_KEY`, `PROD_SSH_PORT`.
   - **Value**: o valor correspondente. Para `PROD_SSH_KEY`, cole o conteúdo
     **completo** do `cat ~/.ssh/deploy_key`, incluindo as linhas
     `-----BEGIN OPENSSH PRIVATE KEY-----` e `-----END OPENSSH PRIVATE KEY-----`.

Ou via `gh` CLI, lendo direto do arquivo (evita erro de colar):

```bash
gh secret set PROD_HOST --body "123.45.67.89"
gh secret set PROD_USER --body "deploy"
gh secret set PROD_SSH_KEY < caminho/para/deploy_key
gh secret set PROD_SSH_PORT --body "22"   # só se não for a porta padrão
```

Confirmar o que foi cadastrado (não mostra valores, só nomes/datas):

```bash
gh secret list
```

---

## Parte 3 — Erros comuns e como diagnosticar

### 3.1 `ssh.ParsePrivateKey: ssh: no key found` / `handshake failed`

O conteúdo salvo em `PROD_SSH_KEY` não foi reconhecido como chave privada
válida. Causas mais comuns ao colar na UI do GitHub:

- faltou o cabeçalho `-----BEGIN ... PRIVATE KEY-----` ou o rodapé `-----END ... PRIVATE KEY-----`;
- as quebras de linha foram achatadas em uma linha só pelo copiar/colar;
- foi colada a chave **pública** (`.pub`) por engano;
- a chave está em formato PuTTY (`.ppk`), que o `appleboy/ssh-action` não entende.

Como não dá pra inspecionar o valor de um secret depois de salvo, a correção
é sempre recadastrar (`gh secret set PROD_SSH_KEY < arquivo` é mais seguro
que colar na UI, porque não depende de copiar/colar manual).

### 3.2 Workflow falha em 0s, sem nenhum job listado

Sintoma: `gh run list` mostra runs com duração `0s` e conclusão `failure`, e
`gh run view <id> --jobs` retorna `"jobs": []`. Isso **não é** falha de um
step — é o GitHub Actions rejeitando o parsing do próprio arquivo YAML antes
de agendar qualquer job. `gh run view <id>` normalmente mostra a mensagem
"This run likely failed because of a workflow file issue.".

Causa típica: algum valor de `env:` sem aspas terminando em `:` (dois-pontos),
que o parser YAML interpreta como início de um mapeamento aninhado. Exemplo
real que já quebrou um workflow:

```yaml
# quebra o parser — "memory:" no final é lido como chave, não como texto
env:
  DATABASE_URL: sqlite:///:memory:
```

```yaml
# correto — valor entre aspas
env:
  DATABASE_URL: "sqlite:///:memory:"
```

Regra prática: **qualquer valor de `env`/`with` que contenha `://` ou termine
em `:` deve ir entre aspas.**

Para validar o YAML antes de fazer push (evita descobrir isso só depois de
3 runs falhando):

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml', encoding='utf-8'))" && echo "YAML OK"
```

---

## Checklist rápido para um projeto novo

1. [ ] Workflow referencia `secrets.PROD_HOST`, `PROD_USER`, `PROD_SSH_KEY` (e `PROD_SSH_PORT` se a porta não for 22).
2. [ ] Validar o YAML localmente (`python3 -c "import yaml; yaml.safe_load(...)"`) antes do push.
3. [ ] Gerar chave dedicada (`ssh-keygen -t ed25519 ... -N ""`), sem passphrase.
4. [ ] Pública em `authorized_keys` do `PROD_USER` no servidor.
5. [ ] Testar a chave localmente com `ssh -i deploy_key usuario@host echo ok` antes de cadastrar no GitHub.
6. [ ] Cadastrar os secrets (`gh secret set` ou UI) e confirmar com `gh secret list`.
7. [ ] Push/re-run e acompanhar com `gh run watch <id>` — se falhar, `gh run view <id> --log-failed`.
