# Relatório de Rastreabilidade: Documentação vs. Implementação

| Campo | Valor |
|---|---|
| **Data da Análise** | 2026-06-24 (criação) · 2026-07-27 (rev. 1.1) · 2026-08-11 (rev. 2.0) · 2026-08-12 (rev. 3.0) · 2026-08-17 (rev. 4.0) · 2026-08-17 (rev. 5.0) · 2026-08-24 (rev. 6.0) · **2026-08-26 (rev. 7.0 — esta revisão)** |
| **Versão** | 7.1 |
| **Branch / HEAD** | `fix/audit-repository-refactor-and-regressions` · `34f8444` |
| **Metodologia** | Leitura integral dos documentos de requisitos de `Arquivo/` (inalterados desde a v1.0) + **reauditoria linha a linha do `backend/README.md`** contra o código executável, com enumeração real de rotas (`app.openapi()`), execução da suíte (`202 passed` no levantamento; **250** após o BLOCO Q) e verificação do head do Alembic |
| **Documentos Analisados** | 5 arquivos de requisitos em `Arquivo/` + `backend/README.md` (223 linhas) + `frontend/README.md` + `frontend/AGENTS.md`/`CLAUDE.md` + `backend/.env.example` + `INSTRUCTIONS.md` |
| **Relatórios `docs/` Consultados** | `relatorio_geral.md` (8.0), `relatorio_funcionalidades.md` (8.0), `relatorio_bugs.md` (9.0), `relatorio_melhorias.md` (7.0), `roadmap.md` (7.0) |

> **Sobre o escopo pedido no Bloco 5.** A instrução original pede a leitura de "todos os documentos dentro da pasta `backend/README`". Confirmado de novo: **essa pasta não existe** — existe o arquivo `backend/README.md`. Ele é auditado aqui como documento de primeira classe desde a rev. 6.0.

---

## ⚠️ O achado desta revisão — a correção cirúrgica que não corrigiu o documento

A rev. 6.0 listou **9 divergências** entre `backend/README.md` e o código (RD-01 a RD-09), uma delas Crítica. O BLOCO P (`4fd576f`) tratou a Crítica: a senha em texto claro saiu da linha de comando do README.

**As outras oito continuam exatamente como estavam.** E uma delas **piorou** por efeito colateral da própria correção:

> **RD-04.** O README manda usar `http://localhost:8000/api/v1/Monitoring` como health check. Na rev. 6.0, esse endpoint existia e devolvia `{"status":"ok"}` estático — o problema era que ele não tocava no banco, então um orquestrador configurado assim consideraria saudável uma instância com o banco fora do ar.
>
> O BLOCO P **removeu a rota** (achado B-B10, "rota morta e redundante com `/health`"). Correto do ponto de vista do código. Mas o README continua indicando o endereço, que agora responde **404**. A instrução saiu de "enganosa" para "quebrada".

Isso é o assunto deste relatório em forma condensada: **quando o código e a documentação são duas fontes de verdade separadas, corrigir um lado pode piorar o outro.** O achado B-B10 foi avaliado só contra o código; ninguém perguntou quem apontava para aquela rota.

**Recomendação estrutural (mantida da rev. 6.0, agora com evidência):** `backend/README.md` deve deixar de duplicar procedimento e passar a **apontar** para `docs/setup_completo.md` e `docs/executar_projeto.md`. Duas fontes de verdade para o mesmo comando produziram RD-02, RD-03 e RD-04 — e produzirão os próximos.

---

## Resumo Executivo

| Categoria | Total | Implementado ✅ | Parcial ⚠️ | Não Implementado ❌ |
|---|---|---|---|---|
| Requisitos Funcionais (RF) | 20 | **11** | 4 | 5 |
| Requisitos Não-Funcionais (RNF) | 8 | **4** | 2 | 2 |
| Regras de Negócio (RN) | 10 | **6** | 1 | 3 |
| **Total** | **38** | **21** | **7** | **10** |

> **Atualização de 2026-08-26 (rev. 7.1).** A tabela já reflete a correção de **B-A28**,
> aplicada no mesmo dia pelo BLOCO Q: **RNF-03 volta a ✅**. Foi o único requisito formal
> que a auditoria derrubou — e o único que a implementação recuperou na mesma janela.

### Indicadores de Divergência

| Indicador | rev. 6.0 | rev. 7.0 | Δ |
|---|---|---|---|
| Requisitos com implementação total ou parcial | 27/38 (71%) | **28/38 (74%)** | 🔼 +1 |
| Requisitos **plenamente** atendidos | — | **21/38 (55%)** | recontagem + B-A28 corrigido |
| Divergências `Arquivo/` × código, ativas | 6 | **5** | 🔽 −1 (D-09 e D-10 fechadas, D-10 no mesmo dia) |
| Divergências `README.md` × código, ativas | 9 | **8** | 🔽 −1 |
| Funcionalidades implementadas sem documentação | 22 | **30** | 🔺 +8 |
| Funcionalidades documentadas sem implementação | 11 | **11** | — |

> **Por que "funcionalidades sem documentação" subiu 8 numa revisão sem funcionalidade nova de produto.** As oito entregas do BLOCO P (F71–F78) são todas **decisões estruturais** — uma camada de política de autorização, um contrato de storage, uma constraint de unicidade que sustenta uma invariante de negócio, uma política de CSP por rota. Cada uma dessas decisões vive hoje **apenas em docstring**. Docstring é o melhor lugar para explicar *como* uma função funciona e o pior lugar para registrar *por que* uma regra de negócio existe: ela não é encontrável por quem não sabe onde procurar, e desaparece na primeira refatoração.

### Conclusão Executiva

A plataforma **excede** o escopo dos documentos de requisitos originais em profundidade técnica e **fica aquém** em três eixos específicos, todos inalterados desde a v1.0: **automação de estados** (RN-05, RN-07, RN-10), **imutabilidade da trilha de auditoria** (RNF-02) e **identidade visual** (RNF-08).

A novidade do levantamento foi uma regressão de conformidade vinda de um achado, não de código novo: **RNF-03 (segregação de visão por perfil)** caiu de ✅ para ⚠️, porque `GET /dashboard/cards/{id}` devolvia o checklist interno e o histórico do auditor ao cliente auditado (**B-A28**).

**Ela durou algumas horas.** O BLOCO Q corrigiu B-A28 no mesmo dia: as duas coleções voltam vazias para papel não-admin, o chat continua bilateral, e a decisão passou a viver em `core/policy.py` como `Action.READ_CARD_INTERNALS`, com barreira dedicada e uma seção de **leitura** na matriz de autorização. **RNF-03 está ✅ de novo.**

---

## Inventário dos Documentos Analisados

### Documentos de requisitos (`Arquivo/`) — inalterados desde a v1.0

| ID | Documento | Natureza |
|---|---|---|
| **D1** | Escopo funcional da plataforma | Requisitos funcionais macro |
| **D2** | Apresentação do produto | Visão, telas propostas, branding |
| **D3** | Regras de negócio e políticas | RN-01 a RN-10, política de senha, trilha |
| **D4** | Requisitos de segurança e administração | MFA, CRUD de catálogo, branding |
| **D5** | Fluxos de evidência | Upload, download, ciclo de vida |

Nenhum foi atualizado desde o início do projeto. **Toda decisão de produto tomada desde então — sub-usuários, onboarding transacional, templates, categorias, canal de mensagens gerais, política de autorização — está fora deles.**

### Documentação operacional do repositório

| Documento | Linhas | Estado |
|---|---|---|
| `backend/README.md` | 223 | 🔴 **8 divergências ativas** — ver Seção 0 |
| `backend/.env.example` | 41 | ✅ Sincronizado — 21 variáveis, todas em placeholder |
| `frontend/AGENTS.md` / `CLAUDE.md` | — | ✅ Corretos e úteis (avisam sobre os breaking changes do Next.js 16) |
| `INSTRUCTIONS.md` | 122 | ✅ Consolidou os dois `Prompt_*.txt` em `9e3076f` |
| `docs/` (17 arquivos) | 41.592 | ✅ Sincronizada nesta revisão |

---

## Seção 0 — Auditoria do `backend/README.md` × Código Executável

Reauditado linha a linha em 2026-08-26 contra `34f8444`.

| ID | Divergência | README diz | Código faz | Severidade | Estado |
|---|---|---|---|---|---|
| ~~**RD-01**~~ | ~~Credencial em texto claro~~ | ~~`mysql -uauditoria_app -p<SENHA>`~~ | Linha 118 agora é `mysql -uauditoria_app -p -D auditoria` (senha solicitada interativamente) | 🔴 Crítica | ✅ **Fechada em `4fd576f`** |
| **RD-04** | **Health check inexistente** | "Health check: `http://localhost:8000/api/v1/Monitoring`" (linha 106) | A rota foi **removida** em `4fd576f` (B-B10). Responde **404**. O health check real é `GET /health`, que executa `SELECT 1` | 🔴 **Alta** `🔺 agravada` | 🔴 Ativa |
| **RD-02** | Tabelas inexistentes | `DESCRIBE checklist_items;`, `SELECT * FROM checklist_items`, `COUNT(*) FROM checklist_item_state` (linhas 128–150) | Removidas pela migration `0ba953b10f8b` (2026-08-12). Os comandos falham com `Table doesn't exist` | 🔴 Alta | 🔴 Ativa |
| **RD-03** | Tabela renomeada | `COUNT(*) FROM messagens` (linha 150) | Renomeada para `messages` pela migration `83cf1e14efa8`. O comando falha | 🔴 Alta | 🔴 Ativa |
| **RD-05** | Setup incompleto — seeds | Só `seed_admin.py` e `seed_catalog.py` (passo 5, marcado "opcional") | **`seed_dashboard_templates.py` é obrigatório**: sem ele o onboarding falha com "Nenhum template padrão configurado" (`dashboard_builder.py::resolve_template`). Faltam ainda 5 scripts (`seed_demo_companies`, `seed_demo_audits`, `check_db`, `backfill_company_cliente01`, `prune_orphan_uploads`) | 🔴 Alta | 🔴 Ativa |
| **RD-06** | `.env` incompleto | Lista 8 variáveis (linhas 40–50) e afirma "(já configurado)" | `core/config.py` declara **21**. Faltam: `ALLOW_PUBLIC_REGISTRATION`, `JWT_REFRESH_EXPIRES_DAYS`, `ADMIN_EMAIL`, `ADMIN_FULL_NAME`, `ADMIN_PASSWORD`, `MYSQL_ROOT_PASSWORD`, `MYSQL_PASSWORD` e as 6 `SMTP_*` | 🟡 Média | 🔴 Ativa |
| **RD-07** | Versão de Python | "Python 3.11+" | `Dockerfile` e `ci.yml` fixam **3.12**; o ambiente de dev roda **3.14**. A 3.11 nunca foi validada | 🟡 Média | 🔴 Ativa |
| **RD-08** | Estrutura desatualizada | Lista `api/v1`, `core`, `db`, `models`, `schemas`, `services` | Faltam **`middleware/`**, **`repositories/`** e **`tests/`** — três diretórios inteiros, incluindo os 202 testes | 🟡 Média | 🔴 Ativa |
| **RD-09** | Sem instrução de teste | — | Nenhuma menção a `pytest`, `pytest.ini`, `ruff.toml`, `.pre-commit-config.yaml` ou `ci.yml`. Um dev novo não descobre pelo README que existe suíte de testes, lint ou hook de segredo | 🟡 Média | 🔴 Ativa |
| **RD-10** `🆕` | `JWT_EXPIRES_MINUTES` com três valores | `JWT_EXPIRES_MINUTES=60` (linha 50) | `core/config.py` default **15**; `docker-compose.yml` da raiz **15**; `frontend/proxy.ts` default **60** (**B-M29**). Quatro fontes, dois valores, nenhuma explicação | 🟡 Média | 🔴 Ativa |
| **RD-11** `🆕` | Procedimento de reset que falha | `DELETE FROM users;` + `ALTER TABLE users AUTO_INCREMENT = 1;` (linhas 168–180) | Com as FKs `ON DELETE RESTRICT` de `Company.principal_user_id` e `Audit.client_user_id`, esse `DELETE` **falha** em qualquer banco com dados. O reset real é `docker compose down -v`, que o próprio README documenta corretamente mais abaixo | 🟡 Média | 🔴 Ativa |

### Correção proposta

Reescrever `backend/README.md` como um **índice curto** (≈ 40 linhas) que aponta para os documentos que já existem e são mantidos:

```markdown
# Auditoria API — Backend

API REST em **FastAPI + SQLAlchemy 2.0 + MySQL 8.4**.

## Onde está cada coisa

| Você quer… | Leia |
|---|---|
| Subir o projeto do zero | [`../docs/setup_completo.md`](../docs/setup_completo.md) |
| Operar o banco, backup, logs, Docker | [`../docs/executar_projeto.md`](../docs/executar_projeto.md) |
| Entender a arquitetura | [`../docs/relatorio_geral.md`](../docs/relatorio_geral.md) |
| Fazer deploy | [`../docs/deploy_producao.md`](../docs/deploy_producao.md) |
| Saber o que está quebrado | [`../docs/relatorio_bugs.md`](../docs/relatorio_bugs.md) |

## Início rápido

```bash
docker compose up -d                      # MySQL 8.4 na porta 3307
python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env                      # preencha TODAS as 21 variáveis
alembic upgrade head
python scripts/seed_admin.py              # usuário admin
python scripts/seed_catalog.py            # catálogo de controles
python scripts/seed_dashboard_templates.py   # OBRIGATÓRIO: sem template
                                             # padrão o onboarding falha
uvicorn app.main:app --reload
```

## Verificação

| O quê | Comando / URL |
|---|---|
| Health check (executa `SELECT 1`) | http://localhost:8000/health |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Testes | `python -m pytest -q` → **250 passed** |
| Lint | `python -m ruff check app scripts tests` |
| Hook de segredo | `pre-commit install` (config na **raiz** do repositório) |

## Estrutura

```
app/
├── api/{deps.py,health.py,v1/}   # 11 routers, 62 operações
├── core/                          # config, jwt, security, policy, logging
├── db/                            # base, session, mixins
├── middleware/                    # request_id, security_headers
├── models/                        # 18 classes ORM em 9 arquivos
├── repositories/                  # UserRepository, AuditRepository
├── schemas/                       # 10 arquivos Pydantic
└── services/                      # 9 serviços de domínio
alembic/versions/                  # 19 migrations (head b7c02e91d4a5)
scripts/                           # 8 scripts (seeds + manutenção)
tests/                             # 18 arquivos, 202 casos
```
```

**Esforço:** 1 h. **Impacto:** fecha 8 divergências de uma vez e elimina a fonte que as gerou.

---

## Seção 1 — Requisitos Funcionais

### RF-01 — Autenticação por Login e Senha `✅ Implementado`
`POST /auth/login` + `POST /auth/refresh` (`auth.py`), cookies httpOnly setados por `app/api/auth/login/route.ts`, guarda em `proxy.ts`. Rate limit `5/min` e `10/min` — **verificado por sonda nesta revisão** (6º login → 429). Testado (`test_auth.py`, 9 funções).
> ⚠️ **B-A27:** uma senha acima de 72 bytes derruba o endpoint com exceção não tratada. O requisito é atendido no caminho normal, não nas bordas.

### RF-02 — Acesso Diferenciado por Perfil `✅⚠️ Implementado (com extensão)`
`admin` / `user` / `sub-user` em `user.py` + `deps.py`. Os documentos preveem **2** perfis; o código tem **3** (divergência **D-01**, deliberada e nunca formalizada). Desde o BLOCO P, a diferenciação tem fonte única em `core/policy.py`.

### RF-03 — Upload de Evidências por Controle `✅ Implementado`
`POST /client/controls/{id}/evidences` — extensão validada **antes** de ler bytes, leitura com teto de memória (`_read_limited`), persistência em `uploads/<uuid><ext>`. Testado (`test_evidence_upload.py`, 6 funções).

### RF-04 — Sistema de Status por Controle `⚠️ Parcialmente Implementado`
Os quatro status existem e são unificados entre `AuditControlStatus` e `DashboardCardStatus` desde N.1. **Falta o percentual** que D1/D2 pedem ("Parcial (50%)") — divergência **D-02**.
> ✅ **D-09 fechada:** a definição de status voltou a ser exclusiva do auditor (`require_admin` em `PATCH /dashboard/cards/{id}/status`, B-A23).

### RF-05 — Chat por Controle `✅ Implementado`
`GET`/`POST /client/controls/{id}/messages` (cliente) e `POST /admin/audit-controls/{id}/messages` + `PATCH .../messages/read` (admin), com `read_at` e contadores de não lidas.

### RF-06 — Descrição e Evidência Esperada do Controle `✅ Implementado`
`ControlCatalog.description` e `.expected_evidence`, expostos em `GET /client/controls`.

### RF-07 — Histórico de Modificações por Controle `⚠️ Parcialmente Implementado`
`DashboardCardHistoryEntry` registra ação e autor, e desde B-A23 **só o admin escreve**. Continua parcial por dois motivos: cobre o domínio de *card*, não o de `AuditControl`; e não é imutável (ver RNF-02).
> 🔴 **Agravado por B-A28:** o histórico é **legível pelo auditado**, o que contraria a natureza de registro interno.

### RF-08 — Checklist de Conformidade por Controle `⚠️ Parcialmente Implementado`
`DashboardCardchecklistItem` com toggle restrito a admin. Falta a **máquina de estados** que D3 pede (checklist completo → status automático) — **FNI-05**.
> 🔴 **B-A28:** o checklist interno também é legível pelo auditado.

### RF-09 — Board de Visualização para Auditores `✅ Implementado`
`/private/admin` (Home com 4 KPIs) + `/private/admin/empresas/[id]/dashboard` (grade completa com filtro, ocultação e edição em massa).

### RF-10 — Download de Arquivos de Evidência `✅ Implementado`
`GET /admin/evidences/{id}/download` + proxy autenticado no Next.js.
> ⚠️ **B-M28:** sem guarda de path traversal em `get_absolute_path()` — não explorável hoje, mas assimétrico em relação a `delete_files()`.

### RF-11 — Notificações em Tempo Real `❌ Não Implementado`
Não há WebSocket, SSE nem push. As telas usam polling de 45 s para os badges de não lidas.

### RF-12 — Dashboard com Métricas de Progresso `✅ Implementado (O.1)`
`GET /dashboard/status-summary` — os 4 KPIs numa única query agrupada, ignorando cards ocultos. Falta a **visualização gráfica** que D2/D4 propõem (**FNI-12**).

### RF-13 — Chat Compartilhado Entre Admins `❌ Não Implementado`
Os três canais existentes são admin↔cliente. Não há canal admin↔admin.

### RF-14 — Criação de Auditoria e Instanciação de Controles `✅ Implementado`
`POST /admin/audits` via `AuditRepository.create_with_controls`, com `UniqueConstraint(audit_id, control_id)`.

### RF-15 — Segregação de Dados por Cliente `✅ Implementado`
`_get_company_with_access` / `_resolve_owner_user_id` em 3 routers + filtro por `dashboard_id` no bulk. **Confirmado por sonda:** cliente lendo card de outra empresa → 403; listando cards de outra empresa → 403.

### RF-16 — Catálogo de Controles ISO 27001 `✅⚠️ Implementado (parcial)`
A estrutura está completa e o CRUD por UI existe para categorias e templates. O **conteúdo** do catálogo ISO segue parcial (**FNI-17**).

### RF-17 — MFA `❌ Não Implementado`
Sem segundo fator. Agravante contextual: também não há troca obrigatória de senha, recuperação de senha nem revogação de sessão.

### RF-18 — Sistema de Aceite para Controle de Acesso ao Link `❌ Não Implementado`
Sem fluxo de aceite de termos.

### RF-19 — Controle de Permissão para CRUD de Controles `⚠️ Parcialmente Implementado`
CRUD por interface existe para **categorias** e **templates de dashboard**, com permissão consistente (`require_admin` + `MANAGE_CATEGORY`/`MANAGE_TEMPLATE` em `policy.py`). Não existe para o **`ControlCatalog`** — o catálogo ISO continua sendo populado só por seed (**FNI-15**).

### RF-20 — Branding STW na Homepage `❌ Não Implementado`
A landing page é genérica. Sem logo, paleta ou nome da STW.

---

## Seção 2 — Requisitos Não-Funcionais

### RNF-01 — Autenticação Segura com Política de Senha Forte `⚠️ Parcialmente Implementado`
`UserCreate.password_strength` exige 8 caracteres, uma maiúscula e um dígito. D3 pede **10 caracteres + especial + maiúscula + minúscula + número** (**D-03**).

Duas ressalvas que a rev. 7.0 acrescenta:
1. **A validação só existe no caminho desativado.** `POST /auth/register` está atrás de `ALLOW_PUBLIC_REGISTRATION`, e o onboarding real (`POST /onboarding/principal-user`) gera senha aleatória de 12 caracteres — sem passar por `UserCreate`. Na prática, a política **nunca é exercida sobre uma senha escolhida por humano**.
2. **O limite superior não é modelado** (**B-A27** / M-21): não é uma falha de política de senha, é a ausência do contrato com a biblioteca de hash.

### RNF-02 — Trilha de Auditoria Imutável `❌ Não Implementado` `🔼 mitigação parcial`
Continua não implementado, mas com **mitigação real** desde o BLOCO P: `dashboard_card_history_entries` agora só aceita escrita de admin (B-A23), e o cliente não pode mais forjar entradas.

O que falta para o requisito: a tabela é `CASCADE DELETE` a partir do card (**D-07**), é `UPDATE`/`DELETE`-ável por qualquer acesso ao banco, e cobre apenas eventos de card — não login, não upload/download de evidência, não encerramento de auditoria, não exclusão de empresa. Especificação completa em `relatorio_melhorias.md` → **M-07c**.

### RNF-03 — Segregação de Visão por Perfil `✅ Implementado` `🔁 rebaixado e recuperado nesta revisão`
A segregação **por empresa** sempre foi sólida e testada. A segregação **por natureza do dado** não era — e passou a ser:

| Recurso interno do auditor | Cliente pode escrever? | Cliente pode ler? |
|---|---|---|
| Nota de card | ❌ (correto) | ❌ (correto) |
| Item de checklist | ❌ (desde B-A23) | ❌ **(desde B-A28)** |
| Entrada de histórico | ❌ (desde B-A23) | ❌ **(desde B-A28)** |

O levantamento confirmou por sonda que `GET /dashboard/cards/{id}` devolvia **200** com o conteúdo interno completo a `user` e `sub-user`, incluindo o nome do auditor de cada ação. O BLOCO Q fechou isso no mesmo dia: as duas coleções voltam **vazias** para papel não-admin — não 403, porque o cliente tem direito ao card, apenas não ao trabalho interno do auditor sobre ele.

A decisão deixou de ser implícita: `Action.READ_CARD_INTERNALS` em `core/policy.py`, com `test_card_internals_visibility.py` (5 testes) e uma seção de **leitura** na matriz de autorização — que até então só cobria escrita, e é por isso que B-A28 passou por ela sem ser notado.

### RNF-04 — Segurança de Arquivos `✅ Implementado`
Allowlist de extensões, teto de 10 MB verificado em streaming, nomes gerados por UUID, download exclusivo de admin via proxy autenticado. **E, desde o BLOCO P, exclusão real do disco** na cascata de empresa — o que fecha a lacuna de retenção que existia desde M.1.

### RNF-05 — Interface Intuitiva para o Cliente `✅ Implementado`
Tela do cliente com cards, upload e chat; canal de mensagens gerais separado.

### RNF-06 — Auditabilidade Técnica `✅ Implementado`
Relatório consolidado em PDF (`services/audit_reporting.py` + `report_generator.py`), com proxy autenticado no frontend.

### RNF-07 — Performance: Dashboard em Tempo Real `❌ Não Implementado`
Não há tempo real. Há polling de 45 s.
> ⚠️ Nota de performance relacionada: `GET /admin/companies` executa **7 queries por empresa** (**B-M26**), medido por sonda.

### RNF-08 — Branding e Identidade Visual `⚠️ Parcialmente Implementado`
Design system consistente (CSS vars + Tailwind 4), mas sem a identidade STW que D2/D4 especificam.

---

## Seção 3 — Regras de Negócio

| RN | Descrição | Status | Nota |
|---|---|---|---|
| **RN-01** | Formatos de arquivo permitidos | ✅ | `ALLOWED_EXTENSIONS` — validado antes de ler bytes |
| **RN-02** | Tamanho máximo 10 MB | ✅ | `_read_limited` aborta em streaming (B-M22 fechado) |
| **RN-03** | Progressão de status | ✅ | `NAOCONFORME` nos dois domínios desde N.1 |
| **RN-04** | Bloqueio de acesso cruzado entre clientes | ✅ | Confirmado por sonda (403 nos dois sentidos) |
| **RN-05** | Máquina de estados do checklist | ❌ | Toggle manual apenas (**FNI-05**) |
| **RN-06** | Imutabilidade dos logs | ❌ | Ver RNF-02 — mitigado, não resolvido |
| **RN-07** | Upload → status `EM_ANALISE` automático | ❌ | Sem gatilho (**FNI-09**) |
| **RN-08** | Complexidade de senha | ⚠️ | Ver RNF-01 — na prática, nunca exercida |
| **RN-09** | Segregação de visão de controles | ✅ | Por empresa **e** por natureza do dado (B-A28 corrigido) |
| **RN-10** | Identificação completa do controle | ✅ | Código, título, descrição, evidência esperada |

---

## Seção 4 — Divergências Identificadas

### Divergências entre `Arquivo/` e o código

| ID | Divergência | Status |
|---|---|---|
| **D-01** | Doc prevê 2 perfis; código implementa 3 (`admin`/`user`/`sub-user`) | 🔴 Ativa — decisão deliberada, nunca formalizada |
| **D-02** | Doc pede status com percentual ("Parcial (50%)"); código usa rótulo textual | 🔴 Ativa |
| **D-03** | Doc pede 10 chars + especial + maiúscula + minúscula + número; código valida 8 + maiúscula + número, e só no caminho desativado | 🟡 Parcial |
| ~~**D-06**~~ | ~~`NAOCONFORME` ausente em `AuditControlStatus`~~ | ✅ Resolvida por N.1 |
| **D-07** | Histórico sem imutabilidade (`CASCADE DELETE` a partir do card) | 🔴 Ativa — parcialmente mitigada por B-A23 |
| **D-08** | Homepage sem branding STW | 🔴 Ativa |
| ~~**D-09**~~ | ~~Doc atribui a definição de status ao auditor; a API permitia que o auditado a definisse~~ | ✅ **Resolvida por B-A23 (BLOCO P.1)** |
| ~~**D-10**~~ | ~~Doc trata checklist e histórico como registro interno do auditor; a API os devolve ao auditado na leitura~~ | ✅ **Resolvida em 2026-08-26** (B-A28 / BLOCO Q) |

### Divergências entre `backend/README.md` e o código

Ver **Seção 0** — RD-02 a RD-11 (8 ativas; RD-01 fechada).

---

## Seção 5 — Funcionalidades Documentadas Não Implementadas

| ID | Funcionalidade | Fonte | Status 2026-08-26 | Prioridade | Esforço |
|---|---|---|---|---|---|
| ~~FNI-02~~ | ~~Download de evidências~~ | D1, D5 | ✅ Resolvido (L.4) | — | — |
| ~~FNI-04~~ | ~~`NAOCONFORME` em `AuditControlStatus`~~ | D2 | ✅ Resolvido (N.1) | — | — |
| ~~FNI-11~~ | ~~Dashboard com % de conformidade~~ | D1, D2 | ✅ Resolvido (O.1) | — | — |
| **FNI-05** | Máquina de estados automática (checklist → status) | D3 | 🔴 Aberto | Alta | 2 dias |
| **FNI-07** | Complexidade de senha completa + aplicar no caminho real | D3 | 🟡 Parcial | Média | 4 h |
| **FNI-08** | Logs imutáveis (append-only, sem `CASCADE`) | D3 | 🔴 Aberto | **Alta** | 1,5 dia (**M-07c**) |
| **FNI-09** | Gatilho automático: upload → status `EM_ANALISE` | D3 | 🔴 Aberto | Média | 2 h |
| **FNI-10** | Regra: "Parcial" obriga comentário | D3 | 🔴 Aberto | Média | 1 dia |
| **FNI-12** | Gráficos de progresso no dashboard admin | D2, D4 | 🟡 Parcial — os números existem, falta a visualização | Média | 2 dias |
| **FNI-13** | Notificações em tempo real | D1, D2 | 🔴 Aberto | Média | 2 semanas |
| **FNI-14** | MFA | D2, D4 | 🔴 Aberto | Média | 1 semana |
| **FNI-15** | CRUD do `ControlCatalog` via interface | D4 | 🟡 Parcial — existe para categorias e templates, não para o catálogo ISO | Baixa | 2 dias |
| **FNI-16** | Branding STW (logo + paleta + nome) | D2, D4 | 🔴 Aberto | Baixa | 2 h |
| **FNI-17** | Catálogo ISO 27001 completo | D3 | 🔴 Aberto | Média | 2 dias (conteúdo) |

---

## Seção 6 — Funcionalidades Implementadas Não Documentadas

| ID | Funcionalidade | Arquivo(s) | Impacto | Recomendação |
|---|---|---|---|---|
| **FID-01** | Sub-usuários (solicitação + aprovação + recusa) | `sub_users.py` | Alto | Formalizar como RF em D3 |
| **FID-02** | Onboarding automatizado transacional | `admin_onboarding.py`, `dashboard_builder.py` | Alto | Formalizar como RF |
| **FID-03** | Templates reutilizáveis de dashboard | `company_dashboard.py` | Médio | Documentar como RF de suporte |
| **FID-04** | Dashboard gerencial paralelo ao formulário ISO | `dashboard_cards.py` | **Alto** | **Clarificar a relação com `AuditControl`** — dois domínios de "status de conformidade" convivem sem documento que diga qual é a fonte de verdade |
| **FID-05** | Registro público configurável | `core/config.py` | Baixo | Documentar — e ver **B-M25** (default `True`) |
| **FID-06** | Padrão de acesso ao backend | `frontend/app/api/**`, `lib/server-backend.ts` | Baixo | ADR |
| **FID-07** | JWT em cookies httpOnly (access + refresh) | `login/route.ts`, `core/jwt.py` | Médio | ADR de segurança |
| **FID-08** | Seeds idempotentes | `scripts/seed_*.py` | Baixo | Documentar em `setup_completo.md` |
| **FID-09** | Repository pattern | `app/repositories/` | Médio | ADR de arquitetura |
| **FID-10** | Refresh token + renovação silenciosa | `core/jwt.py`, `proxy.ts` | Médio | ADR do fluxo de autenticação |
| **FID-11** | Server Components/Actions; `proxy.ts` no lugar de `middleware.ts` | `frontend/app/private/**` | Alto | Documentar a mudança de padrão |
| **FID-12** | Observabilidade (structlog + RequestID + `/health` real) | `core/logging.py`, `middleware/` | Baixo | Já em `relatorio_geral.md` |
| **FID-13** | Suíte de 202 testes (pytest + SQLite em memória) | `backend/tests/` | Médio | Criar `TESTING.md` |
| **FID-14** | Notas internas de card | `dashboard_cards.py` | Baixo | Sem UI |
| **FID-15** | Listagem por papel + "minhas auditorias" | `admin.py`, `client.py` | Médio | `GET /admin/users?role=` segue sem UI |
| **FID-16** | Chat/mensagens gerais admin↔cliente | `company_messages.py` | Médio | Formalizar como RF |
| **FID-17** | Encerramento formal de auditoria | `admin.py` | Alto | Formalizar como RF |
| **FID-18** | Exportação de relatório em PDF | `services/report_generator.py` | Alto | Fecha RNF-06 |
| **FID-19** | Categoria de card como entidade + CRUD com 409 | `dashboard_categories.py` | **Alto** | Decisão de modelagem sem registro; `tag` mantida como campo duplicado, com a razão só em docstring |
| **FID-20** | Editor de templates por UI | `dashboard_templates.py` | **Alto** | Muda **quem** controla a planta do trabalho: antes o desenvolvedor (via seed), agora o admin |
| **FID-21** | Aplicação idempotente de template + `is_outdated` | `dashboard_template_admin.py` | **Alto** | A regra "nunca sobrescrever, só sinalizar" vive só em docstring |
| **FID-22** | Edição em massa de cards (5 operações) | `bulk_update_cards` | Médio | Documentar a semântica de `restore_from_template` |
| **FID-23** `🆕` | **Política de autorização como dado** (`Action` × `ALLOWED_ROLES`) | `core/policy.py` | **Alto** | É a **regra de negócio central** da plataforma — *quem declara conformidade* — expressa em 13 linhas de código e em nenhum documento de requisito. Deveria ser um anexo formal de D3 |
| **FID-24** `🆕` | **Retenção de arquivo na exclusão** (pós-commit, com guarda de caminho) | `storage.py`, `company_admin.py` | **Alto** | Tem implicação de **LGPD** e nenhuma política escrita: hoje a regra de fato é "exclusão imediata e irreversível", que precisa ser uma decisão declarada, não um efeito de implementação |
| **FID-25** `🆕` | **Contrato de storage** (`StorageBackend` Protocol) | `storage_backend.py` | Médio | ADR — define o que qualquer backend futuro precisa saber fazer, `delete` incluído |
| **FID-26** `🆕` | **Integridade template↔card** (409 + backfill + `UniqueConstraint`) | `dashboard_templates.py`, migrations `a3d81f4c7b02`/`b7c02e91d4a5` | **Alto** | É uma **invariante de negócio** ("um card por card de template por dashboard") que agora vive no banco; nenhum documento a enuncia |
| **FID-27** `🆕` | **Barreiras de CI** (gitleaks, pip-audit, migrations contra MySQL real) | `.github/workflows/ci.yml` | Médio | Documentar como política de qualidade — o que **deve** reprovar um PR |
| **FID-28** `🆕` | **CSP por rota** (API × documentação) | `middleware/security_headers.py` | Médio | ADR de segurança; a premissa falsa que causou o defeito nº 14 merece registro para não voltar |
| **FID-29** `🆕` | **Varredura de evidências órfãs** | `scripts/prune_orphan_uploads.py` | Baixo | Procedimento operacional — mover para `executar_projeto.md` |
| **FID-30** `🆕` | **Matriz de autorização automatizada** | `tests/test_authorization_matrix.py` | Médio | É a especificação executável de RF-02/RNF-03. Desde a correção de B-A28 cobre **escrita e leitura** — a seção de leitura foi acrescentada em 2026-08-26 |

### Legenda

| Símbolo | Significado |
|---|---|
| ✅ | Implementado conforme documentado |
| ⚠️ | Parcialmente implementado ou com divergência |
| ❌ | Documentado mas não implementado |
| 🔺/🔻 | Prioridade ou avaliação subiu/desceu nesta revisão |

---

## Seção 7 — Matriz de Rastreabilidade

| Requisito | Descrição | Status | Implementação | Observações |
|---|---|---|---|---|
| **RF-01** | Login com e-mail/senha | ✅ | `auth.py`, `login-form.tsx`, `proxy.ts` | Rate limit verificado por sonda; ver **B-A27** |
| **RF-02** | Perfis: cliente vs. auditor | ✅⚠️ | `user.py`, `deps.py`, `core/policy.py` | 3 perfis em vez de 2 (**D-01**) |
| **RF-03** | Upload de evidências | ✅ | `client.py`, `services/storage.py` | Testado; ver **B-B17** (bloco duplicado) |
| **RF-04** | Status de conformidade | ⚠️ | `audit_control.py`, `company_dashboard.py` | **D-09 resolvida**; **D-02** ativa |
| **RF-05** | Chat por controle | ✅ | `client.py`, `admin.py`, `message.py` | `read_at` + contadores |
| **RF-06** | Descrição/evidência esperada | ✅ | `control_catalog.py` | — |
| **RF-07** | Histórico por controle | ⚠️ | `DashboardCardHistoryEntry` | Só admin escreve; **B-A28** na leitura |
| **RF-08** | Checklist por controle | ⚠️ | `DashboardCardchecklistItem` | Sem máquina de estados (**FNI-05**); **B-A28** |
| **RF-09** | Board para auditores | ✅ | `/private/admin` + `/empresas/[id]/dashboard` | Ampliado por O.2/O.4 |
| **RF-10** | Download de evidências | ✅ | `admin.py`, `storage.py` | Ver **B-M28** |
| **RF-11** | Notificações em tempo real | ❌ | — | Polling de 45 s |
| **RF-12** | Métricas de progresso | ✅ | `GET /dashboard/status-summary` | Falta gráfico (**FNI-12**) |
| **RF-13** | Chat entre admins | ❌ | — | — |
| **RF-14** | Criação de auditoria | ✅ | `AuditRepository.create_with_controls` | `UniqueConstraint` |
| **RF-15** | Segregação por cliente | ✅ | 3 routers + bulk | Confirmado por sonda |
| **RF-16** | Catálogo ISO 27001 | ✅⚠️ | `control_catalog.py`, `seed_catalog.py` | Conteúdo parcial (**FNI-17**) |
| **RF-17** | MFA | ❌ | — | — |
| **RF-18** | Aceite de termos | ❌ | — | — |
| **RF-19** | CRUD de controles por permissão | ⚠️ | `dashboard_categories.py`, `dashboard_templates.py` | Falta o `ControlCatalog` (**FNI-15**) |
| **RF-20** | Branding STW | ❌ | — | **D-08** |
| **RNF-01** | Senha forte | ⚠️ | `schemas/auth.py` | **D-03**; nunca exercida; **B-A27** |
| **RNF-02** | Trilha imutável | ❌ | — | Mitigado por B-A23; ver **M-07c** |
| **RNF-03** | Segregação de visão | ✅ 🔁 | `policy.py`, `_get_*_with_access` | Por empresa ✅; por natureza do dado ✅ desde a correção de **B-A28** |
| **RNF-04** | Segurança de arquivos | ✅ | `storage.py`, `client.py`, `admin.py` | Inclui exclusão real do disco |
| **RNF-05** | Interface intuitiva | ✅ | `client-dashboard-client.tsx` | — |
| **RNF-06** | Auditabilidade técnica | ✅ | `audit_reporting.py`, `report_generator.py` | PDF |
| **RNF-07** | Performance tempo real | ❌ | — | Ver **B-M26** |
| **RNF-08** | Identidade visual | ⚠️ | `globals.css` | Sem branding STW |
| **RN-01..RN-10** | Regras de negócio | 6 ✅ · 1 ⚠️ · 3 ❌ | ver Seção 3 | — |

---

## Seção 8 — Consistência interna da pasta `docs/`

Verificado nesta revisão: **nenhuma contradição interna ativa**.

As três contradições registradas na rev. 6.0 foram corrigidas, e a mais relevante delas merece registro histórico porque explica por que esta seção existe:

> `relatorio_geral.md` e `relatorio_funcionalidades.md` afirmavam que a exclusão em cascata de empresa removia "evidências (registro **+ arquivo em disco**)". O código não removia o arquivo. **A documentação descrevia o comportamento correto de um código que não o tinha** — e por isso ninguém procurou o bug até a auditoria adversarial da rev. 8.0.

Os números desta revisão foram recalculados por execução, não herdados:

| Número | Fonte de verificação |
|---|---|
| 202 testes | `python -m pytest -q` |
| 19 migrations, head `b7c02e91d4a5` | `alembic heads` + `ls alembic/versions` |
| 62 operações em `/api/v1` (64 no total) | `app.openapi()` |
| 18 classes ORM / 18 tabelas | `grep __tablename__` |
| 7.811 LOC de frontend | `wc -l` |
| 21 variáveis em `.env.example` | leitura do arquivo |

---

## Recomendações Prioritárias

### Ação imediata

1. **Reescrever `backend/README.md` como índice** (1 h). Fecha 8 divergências e elimina a duplicação que as gerou. RD-04 é urgente: a instrução de health check aponta para uma rota que **responde 404**, e um orquestrador configurado conforme o README reinicia a aplicação em laço.

2. ~~**Corrigir B-A28**~~ ✅ **Feito em 2026-08-26** (BLOCO Q, Q.3). Era o único achado que rebaixava um requisito formal; RNF-03 voltou a ✅.

### Documentação a criar

3. **`docs/ADR/` — registro de decisões arquiteturais.** As oito entregas do BLOCO P (FID-23 a FID-30) são decisões estruturais que hoje vivem só em docstring. Três merecem ADR próprio:
   - **ADR-01: Posse não é permissão** — por que `core/policy.py` existe, e a regra de que toda ação de escrita (e, depois de B-A28, toda leitura sensível) passa por ele.
   - **ADR-02: Retenção de evidência** — a política de fato hoje é exclusão imediata e irreversível junto com a empresa. Tem implicação de LGPD e precisa ser uma decisão declarada, não um efeito de implementação (**FID-24**).
   - **ADR-03: Dois domínios de conformidade** — `AuditControl` e `DashboardCard` mantêm status paralelos com o mesmo vocabulário. **Qual é a fonte de verdade?** É a pergunta mais antiga em aberto neste relatório (**FID-04**), e a que mais confunde quem chega ao projeto.

4. **`docs/TESTING.md`** — como rodar, como escrever, o que a suíte cobre (e o que não cobre: frontend, custo de query, leitura sensível).

### Formalização de requisitos

5. **Atualizar `Arquivo/` ou criar `docs/requisitos_v2.md`.** Os documentos originais não mencionam sub-usuários, onboarding transacional, templates, categorias, canal de mensagens gerais nem política de autorização — **78 funcionalidades implementadas contra 38 requisitos formais**. A rastreabilidade está perdendo utilidade não porque o código divergiu, mas porque o produto cresceu e a especificação não acompanhou.

6. **Formalizar as três invariantes de negócio que hoje só o banco conhece:**
   - Um card por card de template por dashboard (`UniqueConstraint`, **FID-26**).
   - Um controle por auditoria (`UniqueConstraint(audit_id, control_id)`).
   - Uma empresa por usuário principal (`unique=True` em `principal_user_id`).

   As três são decisões de produto expressas apenas como constraints. Quando **B-A24** duplicou 45 cards, não havia especificação contra a qual julgar se aquilo era um bug ou o comportamento pretendido — a discussão precisou ser reconstruída a partir do código.

---

*Relatório gerado em 2026-08-26 (rev. 7.0). Todos os números foram verificados por execução em `34f8444`; as 9 divergências do `backend/README.md` registradas na rev. 6.0 foram reauditadas uma a uma contra o arquivo atual.*
