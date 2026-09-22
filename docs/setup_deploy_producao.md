# Setup completo do deploy em produção (GitHub Actions + SSH + Docker)

> Runbook derivado da configuração real de produção deste projeto (repositório
> `Desenvolvimento-STWBrasil/Projeto-Auditoria-Plataforma`, servidor
> `stwbrasil-audit-back`, Debian 13 "trixie"). Documenta a **ordem exata** em
> que cada etapa precisa ser aplicada — projeto → servidor (SO/Docker) →
> GitHub (secrets) → validação — incluindo todos os arquivos criados/alterados
> e cada erro real que apareceu no processo, com a causa e a correção.
>
> Use este guia tanto para reconfigurar este projeto do zero (ex: servidor
> novo) quanto como referência para configurar deploy via SSH em outro
> projeto.

---

## Visão geral do pipeline

```
push/PR na main
   ├─ job: backend-tests   (lint ruff + pytest)
   ├─ job: frontend-tests  (lint eslint + vitest + next build)
   └─ job: deploy          (só em push na main, depende dos dois acima)
         └─ appleboy/ssh-action conecta no servidor e roda:
              git fetch/reset --hard origin/main
              docker compose -f docker-compose.prod.yml --env-file .env.prod build
              docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
              smoke test em /health (curl dentro do container backend)
              docker image prune -f
```

Arquivo do workflow: `.github/workflows/deploy.yml`.
Stack de produção: `docker-compose.prod.yml` (mysql, backend, frontend, nginx).

---

## Pré-requisitos

- Servidor Linux com acesso SSH e um usuário com `sudo` (testado em Debian 13).
- Repositório no GitHub com Actions habilitado.
- `gh` CLI autenticado localmente (`gh auth status`) — facilita muito cadastrar
  e conferir secrets sem depender só da UI.
- O repositório ser **público**, ou ter um método de autenticação para clonar
  em privado (token ou deploy key) — ver nota na Fase 3.

---

## Fase 1 — Configuração do projeto (arquivos do repositório)

Tudo nesta fase é feito localmente e commitado — nenhuma dependência do
servidor ou do GitHub ainda.

### 1.1 Workflow `.github/workflows/deploy.yml`

Precisa referenciar 3 secrets obrigatórios + 1 opcional:

| Secret | Obrigatório | Valor |
|---|---|---|
| `PROD_HOST` | sim | IP ou domínio do servidor |
| `PROD_USER` | sim | usuário SSH usado para conectar |
| `PROD_SSH_KEY` | sim | conteúdo completo da chave **privada** SSH |
| `PROD_SSH_PORT` | não | porta SSH — só criar se não for a 22 (o workflow já tem fallback `secrets.PROD_SSH_PORT || 22`) |

```yaml
  deploy:
    needs: [backend-tests, frontend-tests]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.PROD_SSH_KEY }}
          port: ${{ secrets.PROD_SSH_PORT || 22 }}
          script: |
            set -e
            cd /opt/auditoria
            git fetch origin main
            git reset --hard origin/main
            docker compose -f docker-compose.prod.yml --env-file .env.prod build
            docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
            for i in $(seq 1 15); do
              STATUS=$(docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T backend \
                curl -fsS -o /dev/null -w '%{http_code}' http://localhost:8000/health || echo "000")
              [ "$STATUS" = "200" ] && break
              sleep 2
            done
            if [ "$STATUS" != "200" ]; then
              echo "Deploy falhou: /health não respondeu 200 após rebuild" >&2
              exit 1
            fi
            docker image prune -f
```

> O aviso do VS Code/editor "Context access might be invalid: PROD_HOST" (ou
> similar) para esses nomes normalmente só significa que **os secrets ainda
> não existem no repositório** — confirme com `gh secret list` antes de
> assumir que é falso positivo do linter (ver Fase 4).

#### ⚠️ Erro real 1 — Workflow falha em 0s, sem nenhum job listado

**Sintoma:** `gh run list` mostra runs com duração `0s` e conclusão
`failure`; `gh run view <id>` mostra "This run likely failed because of a
workflow file issue." e `--jobs` retorna `[]`. Isso **não é falha de um
step** — é o GitHub Actions rejeitando o parsing do próprio YAML antes de
agendar qualquer job.

**Causa:** valor de `env:` sem aspas terminando em `:` (dois-pontos), que o
parser YAML interpreta como início de um mapeamento aninhado:

```yaml
# quebra o parser — "memory:" no final é lido como início de uma chave
env:
  DATABASE_URL: sqlite:///:memory:
```

Erro exato do parser (`mapping values are not allowed here`, na linha e
coluna do `:` final).

**Correção:** valor entre aspas, e no caso deste projeto, também trocado
para o DSN mysql (o valor aqui só precisa satisfazer a validação do
`app/core/config.py`, os testes reais usam SQLite via
`backend/tests/conftest.py`):

```yaml
env:
  DATABASE_URL: "mysql+pymysql:///:memory:"
```

**Regra prática:** qualquer valor de `env`/`with` que contenha `://` ou
termine em `:` deve ir entre aspas.

**Validar o YAML antes de cada push** (evita descobrir isso só depois de
vários runs falhando):

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml', encoding='utf-8'))" && echo "YAML OK"
```

#### ⚠️ Erro real 2 — Smoke test falha mesmo com o backend saudável

**Sintoma:** o job `deploy` chega até o passo de smoke test, mas falha
depois de ~15 tentativas com `Deploy falhou: /health não respondeu 200`,
mesmo com os containers todos `healthy`.

**Causa:** o `docker compose exec` do smoke test estava **sem**
`--env-file .env.prod`. Sem essa flag, o Compose não interpola as variáveis
obrigatórias do `docker-compose.prod.yml` (`MYSQL_PASSWORD`, `JWT_SECRET`,
`ADMIN_EMAIL`, etc. — todas com `${VAR:?mensagem}`) e o comando falha antes
de sequer rodar o `curl`:

```
error while interpolating services.backend.environment.JWT_SECRET: required variable JWT_SECRET is missing a value: defina no .env.prod
```

**Correção:** adicionar `--env-file .env.prod` também no `exec` do smoke
test (já incluído no bloco YAML da seção 1.1 acima). Essa flag precisa
estar em **todo** comando `docker compose` que toque nesse arquivo —
`build`, `up`, `exec`, `ps`, `logs` etc.

### 1.2 `docker-compose.prod.yml`

Define os 4 serviços (`mysql`, `backend`, `frontend`, `nginx`) e as
variáveis obrigatórias via `${VAR:?defina no .env.prod}`. Nenhuma alteração
foi necessária aqui — só usado para saber quais variáveis o `.env.prod`
precisa ter (ver Fase 3.4).

### 1.3 `.env.prod.example`

Template versionado no git com todas as chaves esperadas, sem valores. É a
base para criar o `.env.prod` real no servidor (nunca commitado — está no
`.gitignore`).

### 1.4 `nginx/nginx.conf`

Tem o placeholder `SEU_DOMINIO_AQUI` em 3 lugares (`server_name` x2 e os
caminhos do certificado `/etc/letsencrypt/live/SEU_DOMINIO_AQUI/...`).
**Pendência conhecida deste projeto:** enquanto não há domínio/TLS
definidos, o container `nginx` fica em `Restarting` (ver Fase 5) — isso não
bloqueia o restante do pipeline porque o smoke test fala direto com o
container `backend`, sem passar pelo nginx. Quando o domínio estiver
definido, ver a seção "Pendências" no final deste guia.

---

## Fase 2 — Configuração do servidor: sistema operacional, git e Docker

Aqui é onde normalmente aparecem os erros mais inesperados, porque um
servidor "novo" costuma não ter nada instalado além do SO básico.

### 2.1 Confirmar a distribuição real do servidor

**Não assuma Ubuntu por padrão.** Confirme antes de configurar qualquer
repositório apt:

```bash
cat /etc/os-release
```

#### ⚠️ Erro real 3 — Repositório Docker 404 por assumir a distro errada

Ao tentar configurar o repo oficial da Docker assumindo Ubuntu num servidor
que na verdade era **Debian 13 (trixie)**:

```
Err:9 https://download.docker.com/linux/ubuntu trixie Release
  404  Not Found
E: The repository '...' does not have a Release file.
```

E, como consequência, a instalação falhava com "no installation candidate"
para todos os pacotes docker.

**Correção:** usar a URL certa para a distro (`linux/ubuntu` vs
`linux/debian`) — ver comandos completos na seção 2.3.

### 2.2 Instalar o `git` (se necessário)

Verifique nos dois contextos — sessão interativa **e** sessão SSH não
interativa (a que o GitHub Actions realmente usa) — porque o `PATH` pode
diferir entre elas:

```bash
which git                                             # sessão atual
ssh -i ~/.ssh/deploy_key usuario@localhost 'which git' # sessão não interativa (depois da Fase 3.1)
type -a git
```

#### ⚠️ Erro real 4 — `git: command not found` no job de deploy

**Sintoma:** o job `deploy` conecta via SSH com sucesso, mas falha logo no
início do script:

```
err: bash: line 3: git: command not found
2026/09/22 13:09:03 Process exited with status 127
```

**Causa:** `git` simplesmente não estava instalado no servidor (confirmado
com `type -a git` retornando `not found` tanto na sessão interativa quanto
na não interativa — não era um problema de `PATH` restrito, como se poderia
suspeitar à primeira vista).

**Correção (Debian/Ubuntu):**

```bash
sudo apt update
sudo apt install -y git
which git   # deve mostrar /usr/bin/git
```

### 2.3 Instalar Docker Engine + plugin `docker compose`

Use sempre o repositório oficial da Docker (não o pacote `docker.io` do
Ubuntu/Debian, que costuma estar desatualizado), com a URL certa para a
distro confirmada no passo 2.1.

```bash
# 1. Remover pacotes conflitantes antigos, se existirem
sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# 2. Chave GPG oficial
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 3. Repositório — troque "debian" por "ubuntu" se for o caso, e confirme
#    o VERSION_CODENAME real do passo 2.1
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
```

> Se o `apt-get update` der 404 para o codename (distro muito recente, ainda
> sem build do Docker), refaça o passo 3 forçando um codename estável
> anterior compatível (ex: `bookworm` no lugar de `trixie`) — os pacotes do
> Docker costumam funcionar sem problema numa versão de Debian um pouco mais
> nova que a testada oficialmente. Neste projeto, `trixie` acabou sendo
> suportado diretamente, então esse fallback não foi necessário.

```bash
# 4. Instalar
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 5. Permitir rodar docker sem sudo (essencial — o script do workflow não usa sudo)
sudo usermod -aG docker $(whoami)
```

#### ⚠️ Erro real 5 — `permission denied ... docker.sock` mesmo depois do `usermod`

**Sintoma:** rodando `docker compose build` na mesma sessão de terminal
onde o `usermod -aG docker` acabou de ser executado:

```
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
```

**Causa:** o grupo novo só é aplicado em **sessões novas** — a sessão atual
já estava aberta antes do `usermod` e não relê `/etc/group` sozinha.

**Correção:** rodar `newgrp docker` na sessão atual (aplica o grupo sem
precisar desconectar), ou simplesmente abrir uma conexão SSH nova:

```bash
newgrp docker
docker compose -f docker-compose.prod.yml --env-file .env.prod build
```

> Uma sessão SSH **nova** (como a que o `appleboy/ssh-action` abre a cada
> execução) já nasce com o grupo atualizado — não precisa de `newgrp` nesse
> caso, só na sessão interativa onde você rodou o `usermod`.

### 2.4 Validar Docker no mesmo contexto que o GitHub Actions vai usar

Depois da Fase 3.1 (chave SSH pronta), sempre valide via uma sessão SSH
**não interativa** — é exatamente esse contexto que o workflow usa:

```bash
ssh -i ~/.ssh/deploy_key usuario@localhost 'docker compose version'
```

---

## Fase 3 — Configuração do servidor: chave SSH, permissões e clone do repositório

### 3.1 Gerar o par de chaves SSH dedicado ao deploy

Nunca reutilize uma chave pessoal — gere uma chave nova, só para CI/CD, sem
passphrase (obrigatório para uso automatizado).

**Direto no servidor, como o usuário que o workflow vai usar** (mais
simples, a pública já nasce no lugar certo):

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/deploy_key -N ""

mkdir -p ~/.ssh
cat ~/.ssh/deploy_key.pub >> ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

Teste **usando o usuário real** (não um placeholder) e o formato correto
`usuario@host` — sem repetir o hostname:

```bash
ssh -i ~/.ssh/deploy_key -o StrictHostKeyChecking=no usuario_real@localhost echo ok
```

#### ⚠️ Erro real 6 — Confusão ao testar a chave (usuário placeholder / hostname duplicado)

Dois erros de digitação comuns nesse teste:

1. Usar literalmente `PROD_USER` como usuário em vez do usuário real do
   servidor — o SSH tenta autenticação por senha para um usuário que não
   existe:
   ```
   PROD_USER@localhost's password:
   ```
2. Copiar o prompt do terminal inteiro (`usuario@hostname`) como se fosse
   só o usuário:
   ```bash
   ssh -i ~/.ssh/deploy_key usuario@hostname@localhost echo ok   # errado
   ssh -i ~/.ssh/deploy_key usuario@localhost echo ok            # correto
   ```

**Correção:** sempre `usuario@host`, com o usuário real (o mesmo que vai
para o secret `PROD_USER`).

### 3.2 Exibir a chave privada para copiar

```bash
cat ~/.ssh/deploy_key
```

Copie **toda** a saída, incluindo as linhas
`-----BEGIN OPENSSH PRIVATE KEY-----` e `-----END OPENSSH PRIVATE KEY-----`
— vai para o secret `PROD_SSH_KEY` na Fase 4.

#### ⚠️ Erro real 7 — `ssh.ParsePrivateKey: ssh: no key found` no job de deploy

**Sintoma:** job `deploy` conecta, mas falha no handshake SSH:

```
2026/09/22 12:39:56 ssh.ParsePrivateKey: ssh: no key found
...
2026/09/22 12:39:57 ssh: handshake failed: ssh: unable to authenticate, attempted methods [none], no supported methods remain
```

**Causa:** o conteúdo salvo em `PROD_SSH_KEY` não foi reconhecido como
chave privada válida. Causas mais comuns ao colar na UI do GitHub:

- faltou o cabeçalho `BEGIN`/rodapé `END`;
- quebras de linha achatadas em uma linha só pelo copiar/colar;
- colada a chave **pública** (`.pub`) por engano;
- chave em formato PuTTY (`.ppk`), que o `appleboy/ssh-action` não entende.

**Correção:** recadastrar o secret. Como não dá pra inspecionar o valor de
um secret já salvo, a forma mais segura é `gh secret set PROD_SSH_KEY <
arquivo` (evita erro de copiar/colar manual) — ver Fase 4.2.

### 3.3 Ajustar o dono da pasta de deploy

Se a pasta onde o repositório vai ser clonado (`/opt/auditoria` neste
projeto) já existir com outro dono, corrija antes de clonar:

```bash
ls -la /opt/auditoria   # confira o dono atual
```

#### ⚠️ Erro real 8 — Pasta de deploy com dono errado / sem permissão de escrita

**Sintoma:** `/opt/auditoria` existia mas pertencia a `deploy:deploy`, não
ao usuário usado pelo workflow (`rodrigo.pedroso`). Com permissões `755`,
só o dono tem escrita.

**Correção — passo a passo completo** (o pai `/opt` também só tem escrita
para `root`, então **precisa de `sudo` para criar/remover**, mesmo depois
de ajustar o dono):

```bash
sudo chown -R usuario_real:usuario_real /opt/auditoria
```

Se a pasta precisar ser recriada do zero (ex: estava vazia e o `git clone`
precisa de uma pasta que ele mesmo controle):

```bash
sudo rmdir /opt/auditoria            # rmdir sem sudo dá "Permission denied" aqui
sudo mkdir -p /opt/auditoria
sudo chown usuario_real:usuario_real /opt/auditoria
```

### 3.4 Clonar o repositório

```bash
git clone https://github.com/<org>/<repo>.git /opt/auditoria
cd /opt/auditoria
git log -1   # confirma que está na main mais recente
```

> Repositório público → clone HTTPS sem autenticação, e o `git fetch` do
> script de deploy também funciona sem token. Se o repositório for
> **privado**, use um Personal Access Token na URL de clone ou configure uma
> Deploy Key (SSH) específica do GitHub para esse repositório — não confundir
> com a chave SSH do servidor (Fase 3.1), que é para o GitHub Actions entrar
> *no servidor*, não para o servidor entrar *no GitHub*.

### 3.5 Criar o `.env.prod`

```bash
cd /opt/auditoria
cp .env.prod.example .env.prod

# gerar um segredo por vez (rodar várias vezes, um valor por variável)
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

nano .env.prod
```

Preencher no arquivo (nunca cole senhas/segredos no chat ou em qualquer
lugar fora do próprio arquivo do servidor):

- `MYSQL_ROOT_PASSWORD` — um segredo gerado acima
- `MYSQL_PASSWORD` — outro segredo, diferente do root
- `JWT_SECRET` — outro segredo
- `CORS_ALLOWED_ORIGINS` — domínio real de produção (ou um valor temporário
  como `http://localhost` enquanto o domínio não está definido — trocar
  depois, ver "Pendências")
- `ADMIN_EMAIL` / `ADMIN_PASSWORD` — credenciais do admin inicial
- Bloco `SMTP_*` — pode ficar em branco (desabilita envio de e-mail); é o
  único bloco com valores opcionais

Conferir que só os campos opcionais ficaram vazios, sem expor os valores
reais (mostra só os *nomes* das variáveis vazias):

```bash
grep '=$' .env.prod
```

Deve listar exatamente as 4 variáveis de SMTP (`SMTP_HOST`, `SMTP_USER`,
`SMTP_PASSWORD`, `SMTP_FROM`) — qualquer outra aparecendo aqui precisa ser
preenchida antes de continuar.

---

## Fase 4 — Configuração do GitHub (secrets)

Só depois de ter, do servidor: usuário SSH definido, chave privada gerada
(Fase 3.1/3.2) e IP/domínio do servidor.

### 4.1 Cadastrar pela UI

1. Acesse `https://github.com/<org>/<repo>/settings/secrets/actions` (ou:
   repositório → **Settings** → **Secrets and variables** → **Actions**).
2. Aba **Secrets** → sub-aba **Repository secrets** → **New repository
   secret**.
3. Repita para cada um, com o **Name** exatamente igual ao esperado pelo
   workflow:

| Name | Value |
|---|---|
| `PROD_HOST` | IP ou domínio do servidor |
| `PROD_USER` | usuário SSH real (ex: `rodrigo.pedroso`) |
| `PROD_SSH_KEY` | conteúdo completo de `cat ~/.ssh/deploy_key`, com `BEGIN`/`END` |
| `PROD_SSH_PORT` | só se a porta não for 22 |

### 4.2 Cadastrar via `gh` CLI (mais seguro para a chave)

Evita erro de copiar/colar manual — lê o valor direto de um arquivo:

```bash
gh secret set PROD_HOST --body "IP_OU_DOMINIO"
gh secret set PROD_USER --body "usuario_real"
gh secret set PROD_SSH_KEY < caminho/para/deploy_key
gh secret set PROD_SSH_PORT --body "22"   # só se necessário
```

### 4.3 Confirmar o cadastro

```bash
gh secret list
```

Mostra nomes e data de atualização (nunca os valores). Depois de qualquer
atualização, **confira o `updated_at` mudou de fato**:

```bash
gh api repos/<org>/<repo>/actions/secrets/PROD_USER
```

#### ⚠️ Erro real 9 — Atualização de secret pela UI "não salva"

**Sintoma:** atualizou um secret pela UI, mas `gh secret list` (ou a
chamada de API acima) continua mostrando o `updated_at` antigo.

**Causa observada:** o clique em "Update secret" não foi concluído /
confirmado na UI (ex: fechou a aba antes de terminar).

**Correção:** refazer o fluxo completo — **Settings → Secrets and
variables → Actions → nome do secret → Update secret → colar o valor →
clicar em "Update secret" até a página confirmar** — e validar de novo com
o comando de API acima antes de seguir.

---

## Fase 5 — Validação manual no servidor (antes de confiar no CI)

Sempre teste o `docker compose` manualmente no servidor antes de depender
só do GitHub Actions — os logs são muito mais fáceis de ler aqui do que via
CI.

```bash
cd /opt/auditoria
docker compose -f docker-compose.prod.yml --env-file .env.prod build
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
docker compose -f docker-compose.prod.yml --env-file .env.prod ps
```

Esperado: `mysql`, `backend` e `frontend` com status `healthy`/`running`.
`nginx` pode aparecer em `Restarting` se o certificado TLS ainda não existe
— ver "Pendências" no final. Isso **não** impede o restante do fluxo.

#### ⚠️ Erro real 10 — "required variable ... is missing a value" ao rodar `ps`/`exec` sem `--env-file`

**Sintoma:**

```
WARN[0000] The "MYSQL_ROOT_PASSWORD" variable is not set. Defaulting to a blank string.
error while interpolating services.backend.environment.JWT_SECRET: required variable JWT_SECRET is missing a value: defina no .env.prod
```

**Causa:** **qualquer** comando `docker compose` que referencie
`docker-compose.prod.yml` precisa de `--env-file .env.prod` — sem a flag,
ele procura um `.env` padrão (que não existe) e todas as variáveis
obrigatórias somem, mesmo que o `.env.prod` esteja perfeitamente
preenchido. Foi exatamente esse esquecimento que causou o Erro real 2 (Fase
1.1), dentro do próprio workflow.

**Correção:** sempre incluir a flag, em todo comando:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod <comando>
```

Teste final do smoke test (mesmo comando que o workflow roda):

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T backend \
  curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost:8000/health
```

Esperado: `200`.

---

## Fase 6 — Primeira execução real via GitHub Actions

Com projeto, servidor e secrets prontos:

```bash
git push origin main          # ou:
gh run rerun <run_id> --failed
gh run watch <run_id> --exit-status
```

Se falhar, o log completo do step que quebrou:

```bash
gh run view <run_id> --log-failed
```

Runs que terminam em `0s` sem nenhum job listado → é erro de parsing do
YAML (Erro real 1, Fase 1.1), não falha de um step — `gh run view <id>
--jobs` retorna `[]` nesse caso.

---

## Checklist rápido (projeto novo, do zero)

1. [ ] `.github/workflows/deploy.yml` referencia `secrets.PROD_HOST`,
       `PROD_USER`, `PROD_SSH_KEY` (e `PROD_SSH_PORT` se a porta não for
       22), com `--env-file .env.prod` em **todo** comando `docker compose`.
2. [ ] YAML validado localmente antes do push
       (`python3 -c "import yaml; yaml.safe_load(...)"`).
3. [ ] Confirmada a distribuição real do servidor (`cat /etc/os-release`)
       antes de configurar qualquer repositório apt.
4. [ ] `git` instalado no servidor (`which git` funcionando).
5. [ ] Docker Engine + `docker-compose-plugin` instalados via repositório
       oficial da distro correta; usuário no grupo `docker`
       (`usermod -aG docker`).
6. [ ] Docker validado numa sessão SSH **não interativa**
       (`ssh -i chave usuario@host 'docker compose version'`), não só na
       sessão interativa.
7. [ ] Chave SSH dedicada gerada (`ssh-keygen -t ed25519 ... -N ""`), sem
       passphrase, pública em `authorized_keys`.
8. [ ] Chave testada com `usuario_real@host` (não um placeholder, sem
       duplicar o hostname) antes de cadastrar no GitHub.
9. [ ] Pasta de deploy com o dono certo (`chown` para o usuário do
       workflow) e repositório clonado dentro dela.
10. [ ] `.env.prod` criado a partir do `.env.prod.example`, com todos os
        campos obrigatórios preenchidos (só SMTP pode ficar em branco).
11. [ ] Secrets cadastrados no GitHub e confirmados
        (`gh secret list` / `gh api .../actions/secrets/<nome>`).
12. [ ] `docker compose build && up -d` testado manualmente no servidor,
        com `--env-file .env.prod` em todos os comandos.
13. [ ] Smoke test manual retornando `200`.
14. [ ] Push/re-run pelo GitHub Actions, acompanhado com `gh run watch`.

---

## Pendências conhecidas (a resolver quando o domínio estiver definido)

- `nginx/nginx.conf` ainda tem o placeholder `SEU_DOMINIO_AQUI` (3
  ocorrências) — trocar pelo domínio real.
- Certificado TLS (Let's Encrypt/certbot) precisa ser emitido para esse
  domínio e disponibilizado em `/etc/letsencrypt/live/<dominio>/` no
  servidor — sem isso o container `nginx` fica em `Restarting` (o
  `ssl_certificate`/`ssl_certificate_key` apontam para arquivos que não
  existem).
- `CORS_ALLOWED_ORIGINS` no `.env.prod` do servidor precisa ser atualizado
  do valor temporário (ex: `http://localhost`) para o domínio real em
  produção.

## Arquivos tocados neste processo (referência)

| Arquivo | O que mudou | Onde |
|---|---|---|
| `.github/workflows/deploy.yml` | Aspas no `DATABASE_URL` (Erro real 1) + `--env-file` no smoke test (Erro real 2) | commitado no repositório |
| `docs/setup_deploy_producao.md` | Este guia | commitado no repositório |
| `~/.ssh/deploy_key` / `deploy_key.pub` | Par de chaves dedicado ao deploy | servidor, fora do git |
| `~/.ssh/authorized_keys` | Chave pública autorizada | servidor, fora do git |
| `/etc/apt/keyrings/docker.gpg`, `/etc/apt/sources.list.d/docker.list` | Repositório oficial Docker | servidor, fora do git |
| `/opt/auditoria/` | Dono corrigido + repositório clonado | servidor, fora do git |
| `/opt/auditoria/.env.prod` | Segredos de produção | servidor, fora do git (`.gitignore`) |
| Secrets do GitHub (`PROD_HOST`, `PROD_USER`, `PROD_SSH_KEY`) | Cadastrados/corrigidos | configuração do repositório no GitHub, não é arquivo |
