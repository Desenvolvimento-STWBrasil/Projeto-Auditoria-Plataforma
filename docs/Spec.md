# Spec — Implantação Unificada (Docker + CI/CD) da Plataforma de Auditoria

| Campo | Valor |
|---|---|
| **Data** | 2026-09-10 |
| **Versão** | v1.0 |
| **Autor** | Rodrigo Santos + Claude Code (DevSecOps) |
| **Origem** | Transcreve para execução as decisões já tomadas em [`docs/prd_deploy_producao.md`](prd_deploy_producao.md) — este documento não reabre nenhuma decisão de arquitetura do PRD, só a detalha em nível de arquivo/linha de comando |
| **Audiência** | Quem for efetivamente escrever/aplicar os arquivos (dev sênior, DevOps) |
| **Status** | 🟡 Pronto para implementação — nenhum arquivo listado abaixo existe ainda no repositório |
| **Convenção de nomes** | O pedido original citava `Dockerfile.frontend`/`Dockerfile.backend`/`docker-compose.yml` como exemplos ilustrativos. Esta spec mantém os caminhos que **já existem e são usados** pelo projeto (`backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml` de dev na raiz) e cria o arquivo de produção com nome distinto (`docker-compose.prod.yml`) para não colidir com o fluxo de desenvolvimento já documentado no `README.md` raiz — ver justificativa em [2](#2-matriz-de-arquivos-criar--modificar) |

---

## 1. Resumo Executivo da Especificação

Esta spec traduz o PRD em uma lista fechada de **4 arquivos novos** e **4 arquivos existentes a modificar**, mais a criação de um diretório (`nginx/`). Não há nenhuma mudança de código de aplicação (`backend/app/**`, `frontend/app/**`, `frontend/lib/**`) — todo o trabalho é em camada de infraestrutura/configuração/CI.

**O que entra em produção, resumido:**

1. `backend/Dockerfile` e `frontend/Dockerfile` passam a rodar como usuário não-root e ganham `HEALTHCHECK` nativo.
2. Um novo `docker-compose.prod.yml` na raiz adiciona o serviço `nginx` e para de publicar as portas `8000`/`3000` diretamente no host (só o Nginx fica exposto).
3. Um novo `nginx/nginx.conf` termina TLS e roteia `/` para o frontend (rota obrigatória) e `/health`, `/docs`, `/openapi.json` para o backend (rotas opcionais, só operação).
4. Um novo `.github/workflows/deploy.yml` roda testes de backend (pytest) e frontend (vitest + build) em paralelo a cada `push`/`pull_request` na `main`, e só faz deploy via SSH quando o evento é `push` direto na `main` e os dois jobs de teste passaram.
5. Um novo `.env.prod.example` na raiz documenta, sem valores reais, todas as variáveis que `.env.prod` (só no servidor, nunca no Git) precisa ter.
6. `.gitignore` ganha uma entrada explícita para `.env.prod` — **gap real encontrado nesta spec**: o padrão atual (`.env`, `.env.local`, `.env.*.local`) não cobre `.env.prod`, e o plano do PRD coloca esse arquivo dentro do próprio diretório do clone Git no servidor (seção 4.4).
7. `README.md` ganha uma seção curta apontando para o PRD e para esta spec, seguindo o padrão que o próprio README já usa para apontar para `backend/README.md`.

**O que não muda:** `docker-compose.yml` (dev), `backend/docker-compose.yml` (dev), `backend/docker-entrypoint.sh`, `backend/requirements.txt`, `frontend/package.json`, `next.config.ts`, e todo o código de aplicação. Cada um desses itens já atende ao requisito correspondente do PRD sem alteração (ver PRD, seção 2.1).

---

## 2. Matriz de Arquivos (Criar / Modificar)

### 2.1 Arquivos novos

| # | Arquivo | Camada | Depende de |
|---|---|---|---|
| N1 | `.github/workflows/deploy.yml` | CI/CD | N4 já em produção antes de habilitar o job `deploy` (ver ordem de rollout em [5.4](#54-ordem-de-implementação-e-rollout)) |
| N2 | `docker-compose.prod.yml` (raiz) | Orquestração | M1, M2, N3 |
| N3 | `nginx/nginx.conf` (novo diretório `nginx/`) | Borda/TLS | Domínio real + certificado emitido (seção 4) |
| N4 | `.env.prod.example` (raiz) | Configuração | — |

### 2.2 Arquivos existentes a modificar

| # | Arquivo | Tipo de alteração | Risco de regressão |
|---|---|---|---|
| M1 | `backend/Dockerfile` | Reescrita completa (single-stage → multi-stage) | Baixo — `docker-entrypoint.sh` e o `CMD` continuam compatíveis; validar com build local antes do primeiro deploy |
| M2 | `frontend/Dockerfile` | Edição pontual (usuário não-root + `HEALTHCHECK`); estrutura multi-stage já existente **não muda** | Muito baixo |
| M3 | `.gitignore` | Adição de uma linha (`.env.prod`) | Nenhum |
| M4 | `README.md` | Adição de uma seção curta ("Deploy em Produção") | Nenhum |

### 2.3 Explicitamente fora da matriz (decisão, não omissão)

| Arquivo | Por que não entra |
|---|---|
| `docker-compose.yml` (raiz, dev) | Continua servindo só o ambiente de desenvolvimento local; `docker-compose.prod.yml` é um arquivo **irmão**, não uma substituição — os dois convivem, selecionados por `-f` na linha de comando |
| `backend/docker-compose.yml` | Continua só subindo o MySQL para desenvolvimento fora de container (uso descrito no `README.md`, seção "Opção B") |
| `backend/docker-entrypoint.sh` | Já faz exatamente o que o deploy precisa (`alembic upgrade head` + seed idempotente do admin) — PRD seção 2.1 |
| `backend/requirements.txt` | `ruff` já está listado; nenhuma dependência nova é necessária para CI/CD |
| `frontend/package.json` | `lint`, `test`, `build` já existem com o comportamento exato que o workflow precisa (`vitest run` sem watch, `next build` compila e type-checa) |
| `next.config.ts` | `output: "standalone"` já configurado |
| `backend/app/**`, `frontend/app/**`, `frontend/lib/**` | Fora de escopo — esta spec é só infraestrutura/CI |

---

## 3. Detalhamento Técnico por Arquivo

### 3.1 `backend/Dockerfile` (M1 — reescrita completa)

**Ação:** substituir o conteúdo integral do arquivo atual (single-stage, 12 linhas) pela versão multi-stage já definida no PRD, seção 4.1, sem alterações em relação ao que está lá. Resumo do que muda e por quê, linha a linha:

| Elemento | Antes (atual) | Depois (spec) | Motivo |
|---|---|---|---|
| Estágios | 1 (`python:3.12-slim`) | 2 (`builder` → `runtime`) | Imagem final não carrega `gcc`/toolchain de compilação |
| Instalação de deps | `pip install -r requirements.txt` direto na imagem final | `pip install --user` no `builder`, depois `COPY --from=builder /root/.local` | Mesma técnica de cache por camada já usada hoje (`COPY requirements.txt .` antes de `COPY . .`), preservada e reforçada |
| Usuário | root (implícito) | `appuser` (`groupadd`/`useradd -r`) | Redução de superfície — processo da aplicação não roda como root dentro do container |
| `HEALTHCHECK` | Ausente | `curl -fsS http://localhost:8000/health` | Usa o endpoint que já existe e já testa o banco (`backend/app/api/health.py`) — nenhum endpoint novo necessário |
| `CMD` | Sem `--workers` explícito | `--workers 1` explícito | Documenta em código a limitação real descrita no PRD 2.4 (uploads em disco local + rate limit em memória de processo) |
| `ENTRYPOINT`/`docker-entrypoint.sh` | Mantido | Mantido, sem alteração | Já é idempotente e já roda migrations + seed do admin |

**Validação local antes de subir:**
```bash
cd backend
docker build -t auditoria-backend:test .
docker run --rm -e DATABASE_URL=sqlite:////tmp/x.db -e JWT_SECRET=test_only -p 8000:8000 auditoria-backend:test
curl -f http://localhost:8000/health   # esperado: {"status":"Ok",...}
docker inspect --format='{{.Config.User}}' auditoria-backend:test   # esperado: "appuser", nunca vazio/"root"
```
Código completo: PRD seção 4.1.

### 3.2 `frontend/Dockerfile` (M2 — edição pontual)

**Ação:** o arquivo já é multi-stage (`deps` → `builder` → `runner`) e já usa `output: "standalone"`. Não reestruturar — só adicionar, dentro do estágio `runner` existente:

1. Um usuário/grupo de sistema não-root (`nodejs`/`nextjs`), antes dos `COPY --from=builder`.
2. `--chown=nextjs:nodejs` em cada um dos três `COPY --from=builder` já existentes (hoje sem `--chown`).
3. `USER nextjs` logo antes do `EXPOSE 3000`.
4. Uma instrução `HEALTHCHECK` usando `node -e "fetch(...)"` (não `curl`/`wget`, ausentes em `node:20-slim`).

**Validação local:**
```bash
cd frontend
docker build -t auditoria-frontend:test .
docker run --rm -e BACKEND_API_URL=http://localhost:8000 -e JWT_SECRET=test_only -p 3000:3000 auditoria-frontend:test
curl -I http://localhost:3000/     # esperado: HTTP/1.1 200
docker inspect --format='{{.Config.User}}' auditoria-frontend:test   # esperado: "nextjs"
```
Código completo: PRD seção 4.2.

### 3.3 `docker-compose.prod.yml` (N2 — novo, raiz)

**Ação:** criar arquivo novo na raiz, **ao lado** do `docker-compose.yml` de dev (não o substitui). Reaproveita a topologia de 3 serviços do compose de dev (`mysql`, `backend`, `frontend`) e adiciona um 4º serviço (`nginx`). Diferenças estruturais em relação ao compose de dev, todas com propósito de produção:

| Aspecto | Compose de dev (mantido) | Compose de prod (novo) |
|---|---|---|
| Portas do `backend` | `8000:8000` publicada no host | **Sem `ports:`** — só acessível via rede interna `auditoria-net` |
| Portas do `frontend` | `3000:3000` publicada no host | **Sem `ports:`** — idem |
| Portas do `mysql` | Sem `ports:` (já correto hoje) | Sem `ports:` (mantido) |
| `CORS_ALLOWED_ORIGINS` | Fixo em `http://localhost:3000` | Lido de `${CORS_ALLOWED_ORIGINS:?...}` — obrigatório, sem default, força declarar o domínio real |
| Serviço `nginx` | Não existe | Novo — único serviço com `ports: ["80:80", "443:443"]` |
| `logging` (driver/rotação) | Não declarado (default do Docker, sem limite) | `json-file` com `max-size: 10m`, `max-file: 3` em todos os serviços de app |
| Arquivo de variáveis | `.env` na raiz (dev) | `.env.prod` no servidor, passado via `--env-file` |

**Rede:** um único bridge network nomeado `auditoria-net`; todos os 4 serviços entram nela. Nenhuma outra rede é criada.

**Volumes:** os dois nomeados já existentes (`mysql_data`, `backend_uploads`) são recriados neste arquivo (compose não compartilha volumes entre arquivos `-f` diferentes automaticamente a menos que o nome — e portanto os dados — coincidam; como o objetivo é produção rodando isolada da stack de dev, isso é o comportamento correto, não um bug).

**Validação antes do primeiro deploy:**
```bash
docker compose -f docker-compose.prod.yml config   # valida sintaxe e interpolação de variáveis sem subir nada
docker compose -f docker-compose.prod.yml --env-file .env.prod config | grep -A2 'ports:'
# esperado: só o serviço nginx aparece com "80:80"/"443:443"; backend/frontend/mysql sem bloco ports
```
Código completo: PRD seção 4.3.

### 3.4 `nginx/nginx.conf` (N3 — novo diretório + arquivo)

**Ação:** criar o diretório `nginx/` na raiz e o arquivo `nginx/nginx.conf` dentro dele, montado como bind mount somente-leitura pelo serviço `nginx` do `docker-compose.prod.yml` (`./nginx/nginx.conf:/etc/nginx/nginx.conf:ro`).

**Dois `server{}` obrigatórios:**
- `:80` — só existe para (a) responder o desafio HTTP-01 do Let's Encrypt em `/.well-known/acme-challenge/` e (b) redirecionar todo o resto para `https://`.
- `:443` — termina TLS (`ssl_certificate`/`ssl_certificate_key` apontando para `/etc/letsencrypt/live/<domínio>/`), aplica os 4 headers de segurança (`HSTS`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`), e define as `location`s.

**Locations e por que cada uma existe:**

| Location | Upstream | Obrigatória? |
|---|---|---|
| `/` | `frontend:3000` | **Sim** — é como o usuário final acessa o sistema (ver PRD 2.3: o navegador nunca fala com o backend diretamente) |
| `/health` | `backend:8000/health` | Opcional — só para monitoramento externo (ex.: script de uptime batendo em `https://dominio/health` de fora) |
| `/docs` | `backend:8000/docs` | Opcional — Swagger; **recomenda-se `allow`/`deny` por IP** antes de abrir ao público, ou remover a location inteira em ambientes mais sensíveis |
| `/openapi.json` | `backend:8000/openapi.json` | Opcional, mesmo racional de `/docs` |

**Placeholder a substituir antes do deploy:** toda ocorrência de `SEU_DOMINIO_AQUI` (3 ocorrências: `server_name` × 2 e o caminho do certificado) pelo domínio real definido antes de gerar o certificado (seção 4 desta spec).

**Validação:**
```bash
docker compose -f docker-compose.prod.yml exec nginx nginx -t
# esperado: "syntax is ok" / "test is successful"
```
Código completo: PRD seção 4.4.

### 3.5 `.github/workflows/deploy.yml` (N1 — novo)

**Ação:** criar `.github/workflows/` (diretório inexistente hoje) e o arquivo `deploy.yml` dentro dele, com 3 jobs.

**Job `backend-tests`** (roda sempre — push e pull_request):
- `actions/setup-python@v5`, Python `3.12` (mesma versão do `backend/Dockerfile`), cache de pip chaveado por `backend/requirements.txt`.
- `pip install -r requirements.txt` (instala `ruff` e `pytest` junto, já estão no arquivo).
- `ruff check .` — usa o `backend/ruff.toml` já existente sem modificação.
- `pytest -v` com três variáveis de ambiente **dummy**, só para satisfazer `Settings` na importação do app (`DATABASE_URL`, `JWT_SECRET`, `CORS_ALLOWED_ORIGINS`) — **nenhum serviço de banco é declarado no workflow**, porque `backend/tests/conftest.py` já substitui a engine por SQLite em memória antes de qualquer teste rodar.

**Job `frontend-tests`** (roda sempre, em paralelo ao anterior):
- `actions/setup-node@v4`, Node `20` (mesma versão do `frontend/Dockerfile`), cache de npm chaveado por `frontend/package-lock.json`.
- `npm ci` (nunca `npm install`, para respeitar o lockfile de forma determinística).
- `npm run lint` (ESLint 9, config já existente).
- `npm test` (`vitest run` — já roda uma vez e sai, não é o modo watch).
- `npm run build` — roda por último porque é o mais caro; falha aqui também pega erro de tipo/compilação que o Vitest não cobre (os testes de contrato mockam `callBackend`, não fazem type-check do projeto inteiro).

**Job `deploy`** (só push na `main`, só se os dois jobs acima passarem):
- `needs: [backend-tests, frontend-tests]` + `if: github.event_name == 'push' && github.ref == 'refs/heads/main'`.
- Usa `appleboy/ssh-action@v1.0.3` para rodar, dentro do servidor: `git fetch`/`git reset --hard origin/main` → `docker compose -f docker-compose.prod.yml --env-file .env.prod build` → `up -d` → *smoke test* em loop (até 15 tentativas de 2s) batendo em `/health` **de dentro do container** via `docker compose exec` → `docker image prune -f`.
- Se o smoke test não retornar `200` em nenhuma das 15 tentativas, o step termina com `exit 1` e o job (logo o workflow) é marcado como falho — isso não desfaz o `up -d` automaticamente (não há rollback automático nesta versão; rollback é o procedimento manual do PRD, seção "Atualizações e Rollback" do guia antigo, reaproveitável se necessário).

**Reforço de segurança recomendado (opcional, não bloqueante):** associar o job `deploy` a um GitHub Environment chamado `production` (`environment: production` no job), com *required reviewers* configurado em Settings → Environments. Isso insere um gate manual de aprovação entre "testes passaram" e "SSH no servidor" sem mudar nada na lógica do workflow — só adiciona a chave `environment: production` ao job.

Código completo: PRD seção 4.5.

### 3.6 `.env.prod.example` (N4 — novo, raiz)

**Ação:** criar um arquivo de exemplo na raiz, no mesmo espírito do já existente `backend/.env.example`, listando **todas** as chaves que `.env.prod` precisa ter no servidor, com placeholders (nunca valores reais) e o comando de geração ao lado de cada segredo:

```dotenv
# Copie para .env.prod DIRETAMENTE NO SERVIDOR (nunca dentro do Git).
# Gere cada segredo com o comando indicado — nunca reutilize um valor de dev.

MYSQL_ROOT_PASSWORD=          # python3 -c "import secrets;print(secrets.token_urlsafe(24))"
MYSQL_PASSWORD=               # idem, valor DIFERENTE do root

JWT_SECRET=                   # python3 -c "import secrets;print(secrets.token_hex(32))"
JWT_EXPIRES_MINUTES=15
JWT_REFRESH_EXPIRES_DAYS=7

CORS_ALLOWED_ORIGINS=         # https://SEU_DOMINIO_AQUI — sem localhost, sem barra final

ADMIN_EMAIL=
ADMIN_FULL_NAME=Administrador
ADMIN_PASSWORD=               # senha forte, só para o primeiro acesso

# Opcional — sem isso, onboarding de cliente novo não recebe a senha
# temporária por e-mail (vira log estruturado em vez de e-mail real).
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_USE_TLS=true
```

Este arquivo **é versionado** (só contém placeholders); `.env.prod` (com valores reais) **nunca é versionado** — daí a necessidade do item M3 abaixo.

### 3.7 `.gitignore` (M3 — adição de uma linha)

**Achado desta spec (gap real, não coberto pelo PRD explicitamente):** o bloco atual de segredos no `.gitignore` é:
```gitignore
.env
.env.local
.env.local.bak
.env.*.local
!.env.example
```
Nenhum desses quatro padrões casa com o nome de arquivo `.env.prod` — `.env` só ignora o arquivo exatamente chamado `.env`; `.env.*.local` só ignora nomes terminados em `.local`. Como o plano do PRD (seção 5.4) cria `.env.prod` **dentro do próprio diretório do clone Git no servidor** (`/opt/auditoria/.env.prod`), esse arquivo hoje ficaria visível para `git status`/`git add -A` sem nenhum aviso do Git.

**Ação:** adicionar uma linha ao bloco existente:
```gitignore
.env
.env.local
.env.local.bak
.env.*.local
.env.prod
!.env.example
!.env.prod.example
```
(a segunda exceção, `!.env.prod.example`, garante que o novo arquivo N4 — que É para ser versionado — não seja acidentalmente varrido por uma regra futura mais ampla como `.env.*`).

### 3.8 `README.md` (M4 — adição de seção)

**Ação:** adicionar uma seção curta após "Como Executar" (ou no índice, como um novo item), no mesmo estilo dos links já existentes para `backend/README.md`:

```markdown
## Deploy em Produção

O processo de implantação em produção (Docker + Nginx + CI/CD via GitHub Actions)
está documentado em [`docs/prd_deploy_producao.md`](docs/prd_deploy_producao.md)
(arquitetura e decisões) e [`docs/Spec.md`](docs/Spec.md) (especificação de
execução, arquivo por arquivo).
```

Não há necessidade de duplicar conteúdo técnico no `README.md` — só o ponteiro, seguindo o padrão já usado pelo próprio arquivo para `backend/README.md` (linha 187 do README atual).

---

## 4. Pré-requisitos do Servidor e GitHub Secrets

### 4.1 Servidor

| Requisito | Valor |
|---|---|
| SO | Ubuntu 22.04/24.04 LTS |
| CPU / RAM / Disco | 2 vCPUs / 2 GB / 20 GB (mínimo) — 4 vCPUs / 4 GB / 50 GB SSD (recomendado) |
| Software obrigatório | Docker Engine + plugin `docker compose`, `git`, `certbot` (no host, só para emitir/renovar o certificado — o Nginx em si roda em container) |
| Usuário de deploy | Usuário de sistema dedicado (`deploy`), **não root**, no grupo `docker` |
| Diretório do clone | `/opt/auditoria`, dono `deploy:deploy` |
| Firewall (`ufw`) | Libera só `22/tcp` (SSH), `80/tcp`, `443/tcp` — todo o resto fechado, incluindo `3306`, `8000` e `3000` (não devem ser alcançáveis de fora mesmo por engano, já que `docker-compose.prod.yml` não os publica) |
| Chave SSH | Par dedicado só ao deploy (`ssh-keygen -t ed25519 -C "github-actions-deploy"`), chave pública em `~deploy/.ssh/authorized_keys`, chave privada só no secret `PROD_SSH_KEY` |
| Certificado TLS | Let's Encrypt via `certbot certonly --standalone -d <domínio>`, renovação automatizada via `cron`/timer chamando `docker exec auditoria-nginx nginx -s reload` como post-hook |
| `.env.prod` | Criado manualmente uma única vez em `/opt/auditoria/.env.prod`, `chmod 600`, com base em `.env.prod.example` (item N4) |

Passo a passo completo (comandos prontos para copiar): PRD, seção 5.1–5.5.

### 4.2 GitHub Secrets (Settings → Secrets and variables → Actions → Repository secrets)

| Secret | Obrigatório | Conteúdo | Usado em |
|---|---|---|---|
| `PROD_HOST` | Sim | IP ou hostname do servidor de produção | Job `deploy`, `with.host` |
| `PROD_USER` | Sim | Nome do usuário SSH de deploy (`deploy`) | Job `deploy`, `with.username` |
| `PROD_SSH_KEY` | Sim | Conteúdo integral da chave **privada** SSH dedicada (gerada em 4.1) | Job `deploy`, `with.key` |
| `PROD_SSH_PORT` | Não (default `22`) | Porta SSH, só se diferente da padrão | Job `deploy`, `with.port` |

**Nunca viram secret do GitHub:** `JWT_SECRET`, senhas do MySQL, `ADMIN_PASSWORD`, credenciais SMTP — todos vivem exclusivamente em `.env.prod`, no servidor, lidos pelo `docker compose --env-file` no momento do `up -d`. O workflow do GitHub Actions nunca lê nem transporta esses valores; ele só abre uma sessão SSH e manda o servidor reconstruir a partir do que já está lá.

### 4.3 Variáveis usadas só dentro do CI (não são secrets — não são sensíveis)

| Variável | Job | Valor | Por quê não é secret |
|---|---|---|---|
| `DATABASE_URL` | `backend-tests` | `sqlite:///:memory:` | Nunca toca um banco real; existe só para `Settings` não falhar ao importar `app.main` |
| `JWT_SECRET` (CI) | `backend-tests` e `frontend-tests` | `ci_only_dummy_secret_not_for_production` | Mesmo motivo — string fixa, documentada como não-produção no próprio valor |
| `CORS_ALLOWED_ORIGINS` (CI) | `backend-tests` | `http://localhost:3000` | Não expõe nada; é o mesmo default de dev |
| `BACKEND_API_URL` (CI) | `frontend-tests` (step `build`) | `http://backend:8000` | Não é resolvido de fato durante `next build` (build estático), só precisa existir para a leitura de env não falhar |

### 4.4 Ordem de implementação e rollout

Para nunca ligar o deploy automático contra um servidor não testado:

1. M1 + M2 (Dockerfiles) — validar com build local (comandos nas seções 3.1/3.2).
2. N1 (`deploy.yml`) **sem o job `deploy`** — só os dois jobs de teste, validados em um Pull Request real.
3. Provisionar o servidor (4.1) e rodar o **primeiro deploy manual** (PRD, seção 5.6) usando N2+N3 diretamente por SSH, sem passar pelo GitHub Actions ainda.
4. Só depois do passo 3 confirmado (`docker compose ps` com os 4 serviços `healthy`, `curl /health` retornando 200), adicionar o job `deploy` ao workflow e cadastrar os 3–4 secrets (4.2).
5. M3 (`.gitignore`) e M4 (`README.md`) podem ser feitos a qualquer momento, sem dependência dos demais.

---

## 5. Critérios de Aceite e Testes de Validação do Pipeline

### 5.1 Critérios de aceite (rastreados aos objetivos do PRD, seção 1.4)

| # | Critério | Como comprovar |
|---|---|---|
| A1 | Um `push` na `main` com testes verdes atualiza produção sem intervenção manual | Ver teste T4 abaixo |
| A2 | Um PR na `main` roda os testes e **nunca** aciona SSH/deploy | Ver teste T3 abaixo |
| A3 | Um deploy de rotina (sem mudar `requirements.txt`/`package-lock.json`) não reinstala dependências do zero | Ver teste T5 abaixo |
| A4 | Nenhum segredo aparece versionado no Git, em nenhum momento | Ver teste T6 abaixo |
| A5 | Backend nunca roda com mais de 1 worker/réplica | Inspeção do `CMD` do `backend/Dockerfile` (`--workers 1`) e do `docker-compose.prod.yml` (nenhum `deploy.replicas`/serviço `backend` duplicado) |
| A6 | Só o Nginx fica exposto publicamente (`80`/`443`) | `docker compose -f docker-compose.prod.yml config` não deve listar `ports:` para `mysql`, `backend` ou `frontend` |

### 5.2 Testes de validação do pipeline (executar nesta ordem)

**T1 — Build local isolado de cada imagem** *(antes de qualquer PR)*
```bash
cd backend  && docker build -t auditoria-backend:test .
cd ../frontend && docker build -t auditoria-frontend:test .
```
✅ Esperado: os dois builds terminam sem erro; `docker inspect --format='{{.Config.User}}'` retorna um usuário não-root nos dois.

**T2 — Sintaxe e comportamento do Compose de produção**
```bash
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
docker compose -f docker-compose.prod.yml ps
```
✅ Esperado: `config` não gera erro de interpolação (variáveis com `:?` acusam erro claro se `.env.prod` estiver incompleto, em vez de subir com valor vazio); `ps` mostra os 4 serviços em estado `healthy` (não só `running`) após o `start_period` de cada `HEALTHCHECK`.

**T3 — Pull Request não aciona deploy** *(prova do critério A2)*
1. Abrir um PR de teste contra `main` (pode ser um commit trivial, ex. um comentário).
2. Observar a aba **Actions** do GitHub.

✅ Esperado: `backend-tests` e `frontend-tests` aparecem e rodam; o job `deploy` aparece como **pulado** (`skipped`), nunca como executado — confirmando que a condição `if: github.event_name == 'push' && github.ref == 'refs/heads/main'` funciona mesmo com `pull_request` também disparando o `on:` do workflow.

**T4 — Push na `main` executa o ciclo completo** *(prova do critério A1)*
1. Fazer merge do PR do teste T3 (ou um push direto controlado).
2. Acompanhar os 3 jobs na aba Actions.

✅ Esperado: `deploy` executa depois dos dois jobs de teste, conecta via SSH, e o step de *smoke test* encontra `200` em `/health` dentro do limite de 15 tentativas (30s). `curl https://<domínio>/` e `curl https://<domínio>/health` de fora do servidor retornam 200 logo em seguida.

**T5 — Cache de camadas é efetivo em deploys consecutivos** *(prova do critério A3)*
1. Rodar um deploy sem alterar `requirements.txt`/`package-lock.json` (só um `README.md`, por exemplo).
2. Olhar o log do step de build no servidor (via SSH manual ou no output do Actions).

✅ Esperado: as camadas de `pip install`/`npm ci` aparecem como `CACHED` (Docker BuildKit) ou executam em uma fração do tempo do primeiro build; só as camadas de `COPY . .` em diante são reconstruídas.

**T6 — Nenhum segredo versionado** *(prova do critério A4)*
```bash
# No servidor, dentro de /opt/auditoria:
git status                       # .env.prod NÃO deve aparecer, nem como "untracked"
git log --all -p | grep -i "MYSQL_PASSWORD\|JWT_SECRET" # não deve retornar valor real algum
```
✅ Esperado: `git status` limpo (confirma que M3 — `.gitignore` — está correto); nenhuma senha real jamais aparece no histórico de commits.

**T7 — Falha de teste bloqueia o deploy**
1. Em uma branch de PR, quebrar propositalmente um teste (ex. `assert False` temporário em um teste do backend).
2. Abrir o PR e, opcionalmente, tentar fazer merge mesmo assim (ou simular um push direto).

✅ Esperado: o job `backend-tests` falha; o job `deploy` nunca inicia (`needs:` com dependência falha impede a execução, independentemente da condição `if:`).

**T8 — Nginx e TLS**
```bash
curl -I http://<domínio>/          # esperado: 301 → https
echo | openssl s_client -connect <domínio>:443 -servername <domínio> 2>/dev/null | openssl x509 -noout -dates
docker compose -f docker-compose.prod.yml exec nginx nginx -t
```
✅ Esperado: redirecionamento HTTP→HTTPS confirmado; certificado válido (`notAfter` no futuro); `nginx -t` sem erro de sintaxe.

**T9 — Rollback manual ensaiado pelo menos uma vez**
```bash
git log --oneline -5
git checkout <commit-anterior-estável>
docker compose -f docker-compose.prod.yml --env-file .env.prod build
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
curl https://<domínio>/health
```
✅ Esperado: aplicação volta a responder na versão anterior sem exigir nenhum passo manual além destes 4 comandos.

### 5.3 Definição de "pronto"

A implementação desta spec é considerada concluída quando **T1 a T9 tiverem sido executados pelo menos uma vez com resultado ✅**, não apenas quando os arquivos existirem no repositório — replicando a lição já registrada no PRD (seção de contexto): um guia de deploy nunca executado de ponta a ponta não é, na prática, um deploy pronto.
