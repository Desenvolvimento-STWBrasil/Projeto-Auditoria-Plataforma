# Execução, Administração e Operação — Plataforma de Auditoria

| Campo | Valor |
|---|---|
| **Versão** | **7.0 — 2026-08-26** |
| **Branch / HEAD** | `fix/audit-repository-refactor-and-regressions` · `34f8444` |
| **Objetivo** | Guia operacional: executar, administrar e validar o sistema no dia a dia |
| **Público-alvo** | Assume que a pessoa nunca teve contato com o projeto |
| **Documento irmão** | [`setup_completo.md`](setup_completo.md) cobre a instalação inicial com mais detalhe explicativo; este foca em **operação contínua** |
| **Verificado em** | MySQL 8.4 real (19 tabelas, head `b7c02e91d4a5`) · `pytest -q` → **258 passed** · `npm run test` → **114 passed** · **CI verde nos 4 jobs** |

---

> ## 🔴 Regra de ouro deste documento — nunca escreva senha na linha de comando
>
> As versões anteriores deste guia traziam comandos como `mysql -uauditoria_app -pSUA_SENHA`. Esse padrão é exatamente o que produziu o achado **B-C23**: uma senha real acabou copiada de uma sessão de terminal para o `backend/README.md`, foi commitada e publicada.
>
> **B-C23 foi fechado em 2026-08-25** — as credenciais foram rotacionadas e verificadas (nenhum valor do `.env` atual aparece em commit algum do histórico). A regra continua valendo: ela é o que impede o próximo.
>
> Todo comando aqui usa uma destas duas formas seguras:
>
> ```bash
> # (a) -p SEM valor: o cliente pede a senha interativamente
> docker exec -it auditoria-mysql mysql -uauditoria_app -p -D auditoria
>
> # (b) MYSQL_PWD via variável de ambiente, para scripts não interativos
> docker exec -e MYSQL_PWD="$MYSQL_PASSWORD" -i auditoria-mysql \
>   mysql -uauditoria_app auditoria
> ```
>
> A forma (a) não deixa rastro no histórico do shell. A forma (b) deixa a senha no ambiente do processo, não no comando — aceitável em script, nunca em documentação.

---

## Sumário

1. [Primeiros Passos para Novos Desenvolvedores](#1-primeiros-passos-para-novos-desenvolvedores)
2. [Configurar o Ambiente](#2-configurar-o-ambiente)
3. [Migrations e Seeds](#3-migrations-e-seeds)
4. [Iniciar Backend, Frontend e Banco](#4-iniciar-backend-frontend-e-banco)
5. [Banco de Dados — Acesso e Administração](#5-banco-de-dados--acesso-e-administração)
6. [Containers Docker e Logs](#6-containers-docker-e-logs)
7. [Executar Testes](#7-executar-testes)
8. [Consultas de Diagnóstico dos Achados Abertos](#8-consultas-de-diagnóstico-dos-achados-abertos)
9. [Atualizar Dependências](#9-atualizar-dependências)
10. [Validar o Funcionamento Completo](#10-validar-o-funcionamento-completo)
11. [Reiniciar Serviços](#11-reiniciar-serviços)
12. [Avisos Operacionais](#12-avisos-operacionais)

---

## 1. Primeiros Passos para Novos Desenvolvedores

Checklist sequencial pós-clone. Cada passo tem uma verificação — não avance sem ela.

| # | Passo | Comando | Verificação |
|---|---|---|---|
| 1 | Clonar | `git clone https://github.com/Rodig0SantOs/Projeto-Auditoria.git` | `cd Projeto-Auditoria && ls` mostra `backend/`, `frontend/`, `docs/` |
| 2 | Ler o essencial | — | [`index.md`](index.md) → [`relatorio_geral.md`](relatorio_geral.md) (arquitetura) |
| 3 | Confirmar as ferramentas | `python --version && node --version && docker ps` | Python ≥ 3.12 · Node ≥ 20 · Docker respondendo |
| 4 | Criar e ativar o venv | `cd backend && python -m venv venv && source venv/Scripts/activate` | prompt mostra `(venv)` |
| 5 | Instalar dependências (backend) | `pip install -r requirements.txt` | sem erro |
| 6 | Criar `backend/.env` | `cp .env.example .env` e **trocar todos os valores** | ⚠️ ver aviso de segredos abaixo |
| 7 | Gerar o `JWT_SECRET` | `python -c "import secrets; print(secrets.token_hex(32))"` | 64 caracteres hex |
| 8 | Subir o banco | `docker compose up -d` (em `backend/`) | `docker ps` mostra `auditoria-mysql` `Up` |
| 9 | Testar a conexão | `python scripts/check_db.py` | `Conexão OK` |
| 10 | Aplicar migrations | `python -m alembic upgrade head` | `alembic current` → `b7c02e91d4a5` · `alembic heads` com **1 linha** |
| 11 | Rodar os seeds | ver [Seção 3](#3-migrations-e-seeds) | **na ordem** — a ordem importa |
| 12 | Rodar os testes | `python -m pytest -q` | **`250 passed`** |
| 13 | Subir o backend | `uvicorn app.main:app --reload` | `curl localhost:8000/health` → `"db_status":"Ok"` |
| 14 | Instalar dependências (frontend) | `cd ../frontend && npm install` | sem erro |
| 15 | Criar `frontend/.env.local` | ver [Seção 2](#2-configurar-o-ambiente) | `JWT_SECRET` **idêntico** ao do backend |
| 16 | Subir o frontend | `npm run dev` | `http://localhost:3000` carrega |
| 17 | Logar | navegador | login com o admin do passo 11 leva a `/private/admin` |
| 18 | Instalar o hook de segredo | na **raiz**: `pip install pre-commit && pre-commit install` | `.pre-commit-config.yaml` está na raiz, não em `backend/` |
| 19 | Ler os avisos | — | [Seção 12](#12-avisos-operacionais) — há 4 armadilhas conhecidas |

> ⚠️ **Passo 6.** `backend/.env.example` traz as **21 variáveis em placeholder** — todas precisam de valor real no seu `.env`. O arquivo de exemplo **é versionado**: nunca escreva um valor real de volta nele. O hook do passo 18 (gitleaks) existe para pegar isso antes do commit.
>
> ⚠️ **Passo 11.** `seed_dashboard_templates.py` é **obrigatório**, não opcional: sem um template marcado como `is_default`, o onboarding de cliente falha com *"Nenhum template padrão configurado"*.
>
> ⚠️ **Antes do passo 17**, leia o aviso sobre onboarding sem SMTP na [Seção 12](#12-avisos-operacionais). Criar um cliente pela interface sem SMTP configurado gera uma conta que **ninguém consegue acessar**.

---

## 2. Configurar o Ambiente

### Backend — `backend/.env`

As 17 variáveis que `app/core/config.py` declara. O conteúdo completo, comentado, está em [`setup_completo.md`](setup_completo.md) § 3.3. As que mais causam confusão:

| Variável | Observação |
|---|---|
| `DATABASE_URL` | Porta **3307** (host), não 3306. Senha com caractere especial precisa de URL-encoding (`@` → `%40`) |
| `MYSQL_PASSWORD` | Tem de ser **exatamente** a senha usada na `DATABASE_URL` — o `docker-compose.yml` a lê ao criar o container |
| `JWT_SECRET` | **Idêntico** ao de `frontend/.env.local`, senão o login entra em loop |
| `JWT_EXPIRES_MINUTES` | 480 em dev (comodidade); 15 no `docker-compose.yml` da raiz |
| `ALLOW_PUBLIC_REGISTRATION` | `false` — clientes entram por onboarding do admin |

### Frontend — `frontend/.env.local`

```bash
BACKEND_API_URL=http://127.0.0.1:8000
JWT_SECRET=<mesmo valor de backend/.env>
JWT_ALGORITHM=HS256
JWT_EXPIRES_MINUTES=480
JWT_REFRESH_EXPIRES_DAYS=7
```

> **O erro nº 1 deste projeto** é `JWT_SECRET` divergente entre os dois arquivos. O sintoma engana: o login *parece* funcionar (o backend emite o token), mas toda navegação para `/private/*` devolve você a `/public/login`, porque o `proxy.ts` não consegue verificar a assinatura.

---

## 3. Migrations e Seeds

### Migrations

```bash
cd backend
python -m alembic upgrade head      # aplica todas as pendentes
python -m alembic current           # deve mostrar b7c02e91d4a5
python -m alembic heads             # deve mostrar exatamente 1 linha
python -m alembic history --verbose # histórico completo (19 revisões)
python -m alembic downgrade -1      # reverte a última (raro, use com cuidado)
```

### Seeds — a ordem importa

```bash
python scripts/seed_catalog.py             # 9 controles ISO 27001:2022
python scripts/seed_dashboard_templates.py # Template 1 (padrão) e Template 2
ADMIN_EMAIL=admin@auditoria.local ADMIN_PASSWORD='SenhaForte!123' \
  python scripts/seed_admin.py             # usuário admin
```

Opcionais, para popular a aplicação com dados realistas:

```bash
python scripts/seed_demo_companies.py   # 5 empresas fictícias com dashboard
python scripts/seed_demo_audits.py      # auditorias, evidências em PDF, mensagens
```

Todos são **idempotentes** — rodar de novo não duplica.

> **Duas dependências de ordem que quebram o setup se invertidas:**
>
> 1. `alembic upgrade head` **antes** de `seed_dashboard_templates.py`. A migration `4f2b8e6a91d3` semeia as 4 categorias canônicas; sem elas, os templates nascem com `category_id = NULL` e a aba "Dashboard & Template" fica sem categorias para filtrar.
> 2. `seed_dashboard_templates.py` é **obrigatório**. Sem um template com `is_default=True`, o onboarding de cliente falha com *"Nenhum template padrão configurado"*.

### Scripts utilitários

| Script | Para quê |
|---|---|
| `scripts/check_db.py` | Testa a conexão com o banco, mascarando a senha na saída |
| `scripts/backfill_company_cliente01.py` | Correção pontual de dados (N.1) |

---

## 4. Iniciar Backend, Frontend e Banco

```bash
# Terminal 1 — Banco (sobe uma vez e fica)
cd backend && docker compose up -d

# Terminal 2 — Backend
cd backend && source venv/Scripts/activate && uvicorn app.main:app --reload

# Terminal 3 — Frontend
cd frontend && npm run dev
```

### Portas

| Serviço | Porta | URL |
|---|---|---|
| Frontend | 3000 | http://localhost:3000 |
| Backend | 8000 | http://localhost:8000 · Swagger em `/docs` |
| MySQL | **3307** | `127.0.0.1:3307` (o container escuta em 3306) |

### Rotas da aplicação

| Rota | Papel | Conteúdo |
|---|---|---|
| `/` | público | Landing (⚠️ expõe atalhos de dev — **B-B11**) |
| `/public/login` · `/public/cadastro` | público | Autenticação |
| `/private/admin` | admin | **Home**: 4 KPIs, fila de sub-usuários, prévia de mensagens, empresas |
| `/private/admin/empresas` | admin | CRUD de empresas com busca e paginação |
| `/private/admin/empresas/[id]/perfil` | admin | Aba Perfil (a raiz `[id]` redireciona para cá) |
| `/private/admin/empresas/[id]/dashboard` | admin | Aba Dashboard & Template — cards, categorias, bulk |
| `/private/admin/empresas/[id]/usuarios` | admin | Aba Usuários — principal e sub-usuários |
| `/private/admin/empresas/[id]/auditoria` | admin | Aba Auditoria — auditorias da empresa |
| `/private/admin/templates` | admin | Editor de templates e categorias |
| `/private/admin/auditorias` | admin | Status de controle, PDF, conversa, download |
| `/private/admin/mensagens` | admin | Canal geral por empresa |
| `/private/client` | cliente | Controles, evidências, chat, sub-usuários |
| `/private/client/mensagens` | cliente | Canal geral com a auditoria |

---

## 5. Banco de Dados — Acesso e Administração

### 5.1 — Dados de acesso

| Campo | Valor |
|---|---|
| **Host** | `127.0.0.1` (fora do container) |
| **Porta** | `3307` |
| **Banco** | `auditoria` |
| **Usuário da aplicação** | `auditoria_app` (senha = `MYSQL_PASSWORD` do `.env`) |
| **Usuário root** | `root` (senha = `MYSQL_ROOT_PASSWORD`) |
| **Configuração** | `backend/docker-compose.yml`, `backend/.env` |

### 5.2 — Conectar via terminal

```bash
# Interativo — o -p sem valor faz o cliente pedir a senha
docker exec -it auditoria-mysql mysql -uauditoria_app -p -D auditoria
```

Para scripts não interativos, use `MYSQL_PWD` em vez de embutir a senha:

```bash
docker exec -e MYSQL_PWD="$MYSQL_PASSWORD" -i auditoria-mysql \
  mysql -uauditoria_app auditoria -e "SELECT COUNT(*) FROM users;"
```

### 5.3 — Conectar via ferramenta gráfica

MySQL Workbench, DBeaver, TablePlus:

| Campo | Valor |
|---|---|
| Host | `127.0.0.1` |
| Porta | `3307` |
| Usuário | `auditoria_app` |
| Senha | a de `MYSQL_PASSWORD` |
| Banco | `auditoria` |

### 5.4 — Estrutura

```sql
SHOW DATABASES;
USE auditoria;
SHOW TABLES;
DESCRIBE users;
DESCRIBE dashboard_cards;
```

**19 tabelas** no schema atual (18 de domínio + `alembic_version`; **19 migrations**, head `b7c02e91d4a5`) — conferido no MySQL real nesta revisão:

```
alembic_version            control_catalog                 dashboard_templates
audits                     dashboard_card_categories 🆕    dashboards
audit_controls             dashboard_card_checklist_items  evidences
companies                  dashboard_card_history_entries  messages
company_messages           dashboard_card_messages         sub_user_requests
                           dashboard_card_notes            users
                           dashboard_cards
                           dashboard_template_cards
```

Três tabelas modelam **chat**, e a distinção importa:

| Tabela | Escopo | Origem |
|---|---|---|
| `messages` | Conversa por **controle de auditoria** | Schema base; `read_at` desde M.2 |
| `dashboard_card_messages` | Q&A por **card de dashboard** | Migration `9d5a3c1b2e77` |
| `company_messages` | Canal **geral por empresa** | Migration `bf7239a52df8` (L.1) |

> `dashboard_card_categories` é nova (migration `4f2b8e6a91d3`, BLOCO O.3): vocabulário fechado de categorias de card, no mesmo papel que `control_catalog` cumpre para `audit_controls`.
>
> As tabelas `checklist_items` e `checklist_item_state` **não existem mais** — removidas pela migration `0ba953b10f8b` em 2026-08-12. Documentação antiga (incluindo `backend/README.md`) ainda as menciona; ver **RD-02** em [`relatorio_documentacao.md`](relatorio_documentacao.md).

### 5.5 — Consultas de administração

```sql
-- Panorama: contagem em todas as tabelas de domínio
SELECT 'users' AS tabela, COUNT(*) AS total FROM users
UNION ALL SELECT 'companies',                 COUNT(*) FROM companies
UNION ALL SELECT 'audits',                    COUNT(*) FROM audits
UNION ALL SELECT 'audit_controls',            COUNT(*) FROM audit_controls
UNION ALL SELECT 'control_catalog',           COUNT(*) FROM control_catalog
UNION ALL SELECT 'evidences',                 COUNT(*) FROM evidences
UNION ALL SELECT 'messages',                  COUNT(*) FROM messages
UNION ALL SELECT 'company_messages',          COUNT(*) FROM company_messages
UNION ALL SELECT 'dashboards',                COUNT(*) FROM dashboards
UNION ALL SELECT 'dashboard_cards',           COUNT(*) FROM dashboard_cards
UNION ALL SELECT 'dashboard_card_categories', COUNT(*) FROM dashboard_card_categories
UNION ALL SELECT 'dashboard_templates',       COUNT(*) FROM dashboard_templates
UNION ALL SELECT 'sub_user_requests',         COUNT(*) FROM sub_user_requests;

-- Versão de migration aplicada (deve ser b7c02e91d4a5)
SELECT * FROM alembic_version;

-- Usuários por papel
SELECT role, COUNT(*) FROM users GROUP BY role;

-- Empresas com seu usuário principal e contagem de cards
SELECT c.id, c.name, u.email AS principal,
       (SELECT COUNT(*) FROM dashboard_cards dc
         JOIN dashboards d ON d.id = dc.dashboard_id
        WHERE d.company_id = c.id) AS cards
FROM companies c
JOIN users u ON u.id = c.principal_user_id
ORDER BY c.id;

-- Auditorias por status
SELECT status, COUNT(*) FROM audits GROUP BY status;

-- Cards por status (o mesmo que GET /dashboard/status-summary calcula)
SELECT status, COUNT(*) FROM dashboard_cards
 WHERE hidden = 0 GROUP BY status;

-- Controles pendentes de um cliente (troque o e-mail)
SELECT ac.id, cc.code, cc.title, ac.status
  FROM audit_controls ac
  JOIN audits a          ON a.id  = ac.audit_id
  JOIN control_catalog cc ON cc.id = ac.control_id
  JOIN users u           ON u.id  = a.client_user_id
 WHERE u.email = 'cliente@exemplo.com' AND ac.status <> 'CONFORME';

-- Solicitações de sub-usuário pendentes, com a empresa de origem
SELECT sur.id, sur.requested_email, sur.status, c.name AS empresa
  FROM sub_user_requests sur
  LEFT JOIN companies c ON c.principal_user_id = sur.principal_user_id
 WHERE sur.status = 'PENDING';
```

### 5.6 — Apagar dados (com cautela)

```sql
-- ⚠️ NÃO funciona: companies.principal_user_id e audits.client_user_id são
-- ON DELETE RESTRICT. Este DELETE falha em qualquer banco com dados.
-- DELETE FROM users;
```

O caminho correto para remover um cliente é o endpoint `DELETE /api/v1/admin/companies/{id}`, que apaga na ordem certa numa única transação. Para zerar tudo, use o reset completo da [Seção 11](#11-reiniciar-serviços).

> ⚠️ **A exclusão em cascata NÃO apaga os arquivos de evidência do disco** (**B-A26**). Antes de excluir uma empresa, registre os caminhos:
>
> ```sql
> SELECT e.storage_key
>   FROM evidences e
>   JOIN audit_controls ac ON ac.id = e.audit_control_id
>   JOIN audits a          ON a.id  = ac.audit_id
>   JOIN users u           ON u.id  = a.client_user_id
>   JOIN companies c       ON c.principal_user_id = u.id
>  WHERE c.id = <ID_DA_EMPRESA>;
> ```
>
> Depois de excluir pela API, apague os arquivos listados à mão em `backend/uploads/`.

### 5.7 — Backup e restauração

**Backup completo:**

```bash
docker exec -e MYSQL_PWD="$MYSQL_PASSWORD" auditoria-mysql \
  mysqldump -uauditoria_app --single-transaction --routines auditoria \
  > "backup_auditoria_$(date +%Y%m%d_%H%M%S).sql"
```

`--single-transaction` faz o dump sem travar as tabelas (InnoDB), então a aplicação continua respondendo durante o backup.

**Backup só do schema:**

```bash
docker exec -e MYSQL_PWD="$MYSQL_PASSWORD" auditoria-mysql \
  mysqldump -uauditoria_app --no-data auditoria > schema_auditoria.sql
```

**⚠️ O banco não é tudo.** Um backup completo do sistema precisa de **duas** partes:

```bash
# 1. Banco
docker exec -e MYSQL_PWD="$MYSQL_PASSWORD" auditoria-mysql \
  mysqldump -uauditoria_app --single-transaction auditoria > backup_db.sql

# 2. Arquivos de evidência — NÃO estão no banco, só o caminho está
tar -czf backup_uploads_$(date +%Y%m%d).tar.gz backend/uploads/
```

Restaurar só o banco deixa `evidences.storage_key` apontando para arquivos inexistentes, e todo download de evidência devolve 404.

**Restaurar:**

```bash
docker exec -e MYSQL_PWD="$MYSQL_PASSWORD" -i auditoria-mysql \
  mysql -uauditoria_app auditoria < backup_auditoria_20260824_120000.sql

tar -xzf backup_uploads_20260824.tar.gz
```

**Verificar a integridade depois de restaurar:**

```bash
cd backend
./venv/Scripts/python.exe -c "
from pathlib import Path
from sqlalchemy import create_engine, text
from app.core.config import settings
with create_engine(settings.DATABASE_URL).connect() as c:
    keys = [r[0] for r in c.execute(text('SELECT storage_key FROM evidences'))]
print('registros em evidences:', len(keys))
print('sem arquivo em disco :', sum(1 for k in keys if not Path(k).exists()))
files = {p.name for p in Path('uploads').iterdir() if p.is_file()}
print('arquivos orfaos      :', len(files - {Path(k).name for k in keys}))
"
```

Os três números devem ser: total, **0**, **0**.

> Não existe rotina de backup automatizada. Ver [`deploy_producao.md`](deploy_producao.md) e o **Sprint D2** em [`roadmap.md`](roadmap.md).

---

## 6. Containers Docker e Logs

```bash
docker ps                                # containers rodando
docker logs -f auditoria-mysql           # logs do banco (Ctrl+C para sair)
docker exec -it auditoria-mysql bash     # shell dentro do container
docker stats auditoria-mysql             # CPU/memória em tempo real
docker inspect auditoria-mysql           # configuração completa
docker volume ls                         # volumes (mysql_data)
```

### Logs da aplicação

O backend emite **JSON estruturado** (`structlog`), com `request_id` correlacionando as linhas de uma mesma requisição. Em desenvolvimento, saem no terminal do `uvicorn`.

```bash
# Salvar em arquivo e acompanhar
uvicorn app.main:app --reload 2>&1 | tee backend.log

# Filtrar por request_id
grep '"request_id": "abc-123"' backend.log | python -m json.tool

# Só erros
grep '"level": "error"' backend.log
```

O frontend loga no terminal do `npm run dev`. Erros de Server Component aparecem no **servidor**, não no console do navegador — se uma página quebrar sem mensagem no browser, olhe o terminal 3.

---

## 7. Executar Testes

```bash
cd backend
python -m pytest -q                        # 250 passed
python -m pytest -v                        # verboso, teste a teste
python -m pytest tests/test_auth.py -v     # um arquivo
python -m pytest -k "categoria" -v         # por padrão no nome
python -m pytest --cov=app --cov-report=term-missing   # cobertura
python -m pytest --cov=app --cov-report=html           # relatório em htmlcov/
```

Os testes usam **SQLite em memória** (`tests/conftest.py`) — não precisam do MySQL e não tocam no seu banco.

**Frontend:**

```bash
cd frontend
npx tsc --noEmit    # checagem de tipos
npx eslint          # lint
npm run build       # build de produção
```

> ⚠️ **Duas lacunas conhecidas na suíte:**
>
> - **Migrations não são exercitadas** — `conftest.py` monta o schema com `Base.metadata.create_all`, nunca com `alembic upgrade`. Um erro numa migration passa por uma suíte verde. Já aconteceu duas vezes. Depois de escrever uma migration, **rode `alembic upgrade head` à mão** (**M-18**).
> - **Autorização negativa não é testada** — nenhum teste tenta o que o achado **B-A23** explora: um cliente exercendo, no próprio recurso, uma escrita que deveria ser exclusiva do auditor (**M-20**).

---

## 8. Consultas de Diagnóstico dos Achados Abertos

Consultas para medir, no seu ambiente, a exposição a cada achado ativo — e para **confirmar** que os achados fechados continuam fechados.

### 8.1 — Achados ativos (rev. 9.0)

#### B-A29 — há clientes criados sem senha recuperável?

O sintoma é silencioso: a empresa existe, o dashboard existe, e ninguém consegue entrar.

```sql
-- Usuários principais que NUNCA fizeram login não são detectáveis pelo banco
-- (não há coluna last_login_at). O sinal indireto é: empresa criada, zero
-- atividade de qualquer membro.
SELECT c.id, c.name AS empresa, u.email AS usuario_principal, c.created_at,
       (SELECT COUNT(*) FROM company_messages cm WHERE cm.company_id = c.id) AS mensagens,
       (SELECT COUNT(*) FROM audits a WHERE a.client_user_id = u.id)          AS auditorias
  FROM companies c
  JOIN users u ON u.id = c.principal_user_id
 ORDER BY c.created_at DESC;
```

Empresa antiga com **zero mensagens e zero auditorias** é candidata a conta inacessível. Confirme com o cliente antes de concluir — e, enquanto B-A29 não for corrigido, prefira `seed_demo_companies.py` em dev.

#### B-A28 — o registro interno do auditor está exposto?

```bash
# Substitua <TOKEN_DE_CLIENTE> por um access_token de papel "user".
# Se a resposta trouxer checklist ou history preenchidos, o achado está ativo.
curl -s -H "Authorization: Bearer <TOKEN_DE_CLIENTE>" \
  http://localhost:8000/api/v1/dashboard/cards/1 | python -m json.tool
```

Depois da correção, `checklist` e `history` voltam como `[]` para papel não-admin, e o `chat` continua preenchido.

#### B-A27 — o limite do bcrypt está tratado?

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST \
  http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@auditoria.local","password":"'"$(python -c 'print("A1"+"x"*100)')"'"}'
```

**401** = tratado. **500** = achado ativo.

#### B-M26 — quanto custa a listagem de empresas?

```sql
-- Estimativa do custo: ~7 queries por empresa retornada na página.
SELECT COUNT(*) AS empresas,
       COUNT(*) * 7 + 3 AS queries_estimadas_por_pagina
  FROM companies;
```

#### B-M25 — o registro público está aberto?

```bash
# 403 = fechado (correto). 201 ou 409 = ABERTO.
curl -s -o /dev/null -w "%{http_code}\n" -X POST \
  http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Teste Sonda","email":"sonda@exemplo.local","password":"Senha1234"}'
```

### 8.2 — Confirmar que os achados fechados continuam fechados

#### B-A24 — a idempotência de "Aplicar template" está garantida?

```sql
-- (a) Cards sem vínculo de origem: o backfill de a3d81f4c7b02 deve ter zerado
--     ou reduzido ao mínimo (títulos ambíguos ficam de fora, por projeto).
SELECT c.name AS empresa,
       COUNT(dc.id) AS cards,
       SUM(dc.origin_template_card_id IS NULL) AS sem_vinculo_de_origem
  FROM companies c
  JOIN dashboards d            ON d.company_id = c.id
  LEFT JOIN dashboard_cards dc ON dc.dashboard_id = d.id
 GROUP BY c.id
 ORDER BY sem_vinculo_de_origem DESC;

-- (b) A constraint que sustenta a invariante existe?
SHOW INDEX FROM dashboard_cards
 WHERE Key_name = 'uq_dashboard_card_origin_per_dashboard';
```

Se (b) não retornar nada, a migration `b7c02e91d4a5` não foi aplicada neste banco.

#### B-A26 — há arquivos de evidência órfãos?

```bash
cd backend
python scripts/prune_orphan_uploads.py            # só relata
python scripts/prune_orphan_uploads.py --apply    # remove de fato
```

Órfãos remanescentes são de exclusões **anteriores** à correção. A partir do BLOCO P, a cascata apaga o arquivo junto.

#### B-A25 — a exclusão de template em uso está bloqueada?

```sql
SELECT t.id, t.name, t.is_default,
       COUNT(dc.id) AS cards_derivados
  FROM dashboard_templates t
  LEFT JOIN dashboard_template_cards tc ON tc.template_id = t.id
  LEFT JOIN dashboard_cards dc          ON dc.origin_template_card_id = tc.id
 GROUP BY t.id
 ORDER BY cards_derivados DESC;
```

Template com `cards_derivados > 0` agora responde **409** ao `DELETE`. Antes respondia 204 e apagava o vínculo em silêncio.

#### B-C23 — a rotação foi mesmo feita?

```bash
# 1. A senha ANTIGA ainda é aceita? (deve FALHAR)
docker exec -it auditoria-mysql mysql -uauditoria_app -p -D auditoria -e "SELECT 1;"

# 2. Algum valor do .env atual aparece no histórico do git? (deve ser vazio)
cd backend
python - <<'EOF'
import re, subprocess
env = open('.env', encoding='utf-8').read()
for chave in ('MYSQL_PASSWORD', 'ADMIN_PASSWORD', 'JWT_SECRET'):
    m = re.search(rf'{chave}=(\S+)', env)
    if not m:
        continue
    saida = subprocess.run(
        ['git', 'log', '--all', '-S', m.group(1), '--oneline'],
        capture_output=True, text=True, errors='ignore', cwd='..',
    ).stdout.strip()
    print(f'{chave}: {saida if saida else "nenhum commit — OK"}')
EOF
```

### 8.3 — Integridade geral do schema

```sql
-- Head do Alembic aplicado neste banco
SELECT version_num FROM alembic_version;   -- esperado: b7c02e91d4a5

-- Cards com tag preenchida mas sem categoria (o backfill de O.3 deve ter zerado)
SELECT COUNT(*) FROM dashboard_cards
 WHERE tag IS NOT NULL AND tag <> '' AND category_id IS NULL;

-- Cards apontando para categoria inexistente (não deve acontecer: FK SET NULL)
SELECT COUNT(*) FROM dashboard_cards dc
  LEFT JOIN dashboard_card_categories cat ON cat.id = dc.category_id
 WHERE dc.category_id IS NOT NULL AND cat.id IS NULL;

-- Deve haver exatamente 0 ou 1 template padrão
SELECT COUNT(*) FROM dashboard_templates WHERE is_default = 1;

-- Evidências cujo arquivo não existe mais no disco (o inverso do órfão)
SELECT COUNT(*) AS registros_de_evidencia FROM evidences;
-- Compare com: ls backend/uploads | wc -l
```

---

## 9. Atualizar Dependências

### Backend

```bash
cd backend && source venv/Scripts/activate
pip list --outdated
pip install --upgrade <pacote>
pip freeze > requirements.lock.txt   # snapshot do que está instalado
python -m pytest -q                  # 250 passed ANTES de commitar
```

> `requirements.txt` usa `>=` para a maior parte dos pacotes. Isso facilita atualizar e significa que dois ambientes podem ter versões diferentes. Antes de investigar um bug que "só acontece na minha máquina", compare `pip freeze` dos dois.

### Frontend

```bash
cd frontend
npm outdated
npm update
npm audit
npm audit fix          # ⚠️ pode introduzir breaking change; revise o diff
npx tsc --noEmit && npx eslint && npm run build
```

> ⚠️ **Next.js 16 tem breaking changes** frente ao conhecimento convencional (`middleware.ts` → `proxy.ts`, tipos `PageProps<"/rota">`). Antes de subir a versão major, leia `frontend/AGENTS.md` e a documentação em `node_modules/next/dist/docs/`.

---

## 10. Validar o Funcionamento Completo

```bash
# 1. Banco respondendo
docker exec auditoria-mysql mysqladmin ping -h localhost
# Esperado: "mysqld is alive"

# 2. Backend respondendo COM o banco
curl -s http://localhost:8000/health
# Esperado: {"status":"Ok","db_status":"Ok","timestamp":"..."}

# 3. Schema na versão certa
cd backend && python -m alembic current
# Esperado: b7c02e91d4a5 (head)

# 4. Suíte de testes
python -m pytest -q
# Esperado: 250 passed

# 5. Frontend servindo
curl -sI http://localhost:3000 | head -1
# Esperado: HTTP/1.1 200 OK

# 6. Qualidade do frontend
cd ../frontend && npx tsc --noEmit && npx eslint
# Esperado: ambos sem saída (exit 0)
```

### Smoke test das telas (2 minutos)

Logado como admin, confirme que carregam: `/private/admin` (4 KPIs), `/private/admin/empresas`, `/private/admin/empresas/1/perfil`, `.../dashboard`, `.../usuarios`, `.../auditoria`, `/private/admin/templates`, `/private/admin/auditorias`, `/private/admin/mensagens`.

Logado como cliente: `/private/client` e `/private/client/mensagens`.

> Use `/health`, não `/api/v1/Monitoring` — o segundo devolve `{"status":"ok"}` estático **sem tocar no banco**, e reportaria "ok" com o MySQL fora do ar (**B-B10**).

---

## 11. Reiniciar Serviços

```bash
# Banco (mantém os dados)
cd backend && docker compose restart

# Backend — Ctrl+C no terminal do uvicorn, depois:
uvicorn app.main:app --reload

# Frontend — Ctrl+C no terminal do npm, depois:
npm run dev

# Tudo, mantendo os dados do banco:
cd backend && docker compose down && docker compose up -d
# (reabrir os terminais de backend e frontend normalmente)
```

### Reset completo — apaga todos os dados

```bash
cd backend
docker compose down -v          # ⚠️ apaga o volume mysql_data
rm -rf uploads/*                # ⚠️ apaga as evidências em disco
docker compose up -d
# aguardar ~30s: docker logs -f auditoria-mysql
python -m alembic upgrade head
python scripts/seed_catalog.py
python scripts/seed_dashboard_templates.py
ADMIN_EMAIL=admin@auditoria.local ADMIN_PASSWORD='SenhaForte!123' python scripts/seed_admin.py
python scripts/seed_demo_companies.py   # opcional
python scripts/seed_demo_audits.py      # opcional
```

> O `rm -rf uploads/*` é intencional: sem ele, o banco zera mas os arquivos ficam, e você acumula órfãos a cada reset — o mesmo efeito de **B-A26**, por outro caminho.

---

## 12. Avisos Operacionais

Quatro armadilhas conhecidas. Todas têm correção especificada em [`relatorio_bugs.md`](relatorio_bugs.md); até lá, conviva com elas conscientemente.

| ⚠️ | O quê | Por quê | Como conviver |
|---|---|---|---|
| **Senha temporária** | Ao cadastrar cliente sem SMTP, **anote a senha exibida na tela** | O backend guarda só o hash e a plataforma não tem recuperação de senha | A senha aparece num aviso âmbar após o cadastro (B-A29, corrigido). Perdida, só excluindo a empresa ou alterando o hash no banco |
| **B-M26** | `GET /admin/companies` faz 7 queries por empresa | Uma função de detalhe reusada numa listagem | Sem impacto com a base atual; corrigir no Sprint C, junto com o orçamento de queries (M-25) |
| **Escala** | Não rode o backend com mais de 1 worker/réplica | Evidências em volume local + rate limit em memória de processo | 1 worker até o Sprint D2 |

### Armadilhas de documentação

| ⚠️ | O quê |
|---|---|
| **RD-04** | O `backend/README.md` indica `http://localhost:8000/api/v1/Monitoring` como health check. **Essa rota foi removida** e responde 404. O health check real é **`GET /health`**, que executa `SELECT 1`. Um orquestrador configurado pelo README reinicia a aplicação em laço |
| **RD-02/03** | O `backend/README.md` traz consultas a `checklist_items`, `checklist_item_state` e `messagens` — as três **não existem mais** no schema |
| **RD-11** | O `backend/README.md` sugere `DELETE FROM users;` como reset. Com as FKs `ON DELETE RESTRICT`, esse comando **falha**. O reset real é `docker compose down -v` |

### Não são erro — comportamento esperado

| Comportamento | Explicação |
|---|---|
| Checklist e histórico vazios para o cliente | ✅ Correto, **após a correção de B-A28** — são registro interno do auditor |
| Nenhum e-mail chega em dev | Sem `SMTP_HOST`, o envio é apenas registrado no log |
| `/public/cadastro` existe mas não cria conta | `ALLOW_PUBLIC_REGISTRATION=false` — decisão de produto |
| Badges de mensagens demoram a atualizar | Polling de 45 s, não é tempo real |
| `docker compose down` não apaga os dados | Correto. Use `-v` para apagar o volume |

---

## Referências

| Precisa de… | Leia |
|---|---|
| Instalar do zero, com explicação | [`setup_completo.md`](setup_completo.md) |
| Entender a arquitetura | [`relatorio_geral.md`](relatorio_geral.md) |
| Corrigir os achados abertos | [`relatorio_bugs.md`](relatorio_bugs.md) |
| Planejar o próximo ciclo | [`roadmap.md`](roadmap.md) · [`backlog.md`](backlog.md) |
| Fazer deploy | [`deploy_producao.md`](deploy_producao.md) |
| Navegar por tudo | [`index.md`](index.md) |

---

*Manual atualizado em 2026-08-26 (v6.0). O head da migration (`b7c02e91d4a5`), a contagem de testes (`250 passed`) e as consultas de diagnóstico foram conferidos contra o código e a suíte reais em `34f8444`. A Seção 8 foi dividida em duas: achados **ativos** e confirmação de que os **fechados** continuam fechados — o segundo grupo importa tanto quanto o primeiro, porque é o que detecta uma regressão silenciosa. Todos os comandos de banco continuam sem embutir senha na linha de comando, o padrão que originou B-C23.*
