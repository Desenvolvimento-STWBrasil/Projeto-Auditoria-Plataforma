# Automação do Trello — Plataforma de Auditoria

| Campo | Valor |
|---|---|
| **Versão** | **3.1 — 2026-08-26** |
| **Data** | 2026-06-24 (criação) · 2026-07-27 / 2026-08-11 / 2026-08-12 / 2026-08-17 (revisões sem alteração de conteúdo) · 2026-08-24 (v2.0 — Seção 0: seed do quadro) · **2026-08-26 (v3.0 — catálogo reescrito para a rev. 9.0)** |
| **Repositório** | https://github.com/Rodig0SantOs/Projeto-Auditoria |
| **Stack** | FastAPI + Next.js 16 + MySQL (Docker) |
| **Status** | 📋 Proposta — o quadro ainda **não foi criado**. Todo o código deste documento é executável, mas nenhuma parte dele rodou contra um Trello real |

> ### O que mudou na v3.0
>
> A v2.0 acrescentou a **Seção 0** — um script idempotente que semeia o quadro a partir dos achados reais, em vez de deixar o documento ensinando estrutura vazia. Essa foi a mudança conceitual; esta revisão é a **manutenção que ela passou a exigir**.
>
> O catálogo da v2.0 apontava para os achados da rev. 8.0 de `relatorio_bugs.md`. **Os 18 foram fechados** pelo BLOCO P (`4fd576f`) e pela correção do CSP (`34f8444`). Semear o quadro com aquele catálogo hoje criaria 18 cards de trabalho já feito.
>
> O catálogo foi reescrito para o estado real em `34f8444`: **17 cards** — 1 barreira não validada (a primeira execução do CI), 3 achados Alta, 4 Médios, 8 itens estruturais e 1 lote de Baixos.
>
> **A lição que este documento passou a carregar:** um seed derivado do estado do projeto **envelhece junto com o projeto**. Um catálogo desatualizado é pior que catálogo nenhum — ele parece autoritativo. A Seção 0.5 (nova) registra como manter isso vivo sem depender de memória.

## Pré-requisitos Rápidos

| Ferramenta | Onde obter |
|---|---|
| Conta Trello | https://trello.com/signup |
| API Key + Token | https://trello.com/power-ups/admin |
| GitHub Secrets | `github.com/Rodig0SantOs/Projeto-Auditoria` → Settings → Secrets → Actions |
| Python 3.12+ | Já presente no backend do projeto |

---

---

## Seção 0 — Semear o Quadro com o Estado Real do Projeto `🆕 2026-08-24`

As seções seguintes ensinam a montar a estrutura do zero. Esta seção faz a ponte com **o que está em aberto hoje**: um script que cria, de uma vez, os cards de todos os achados ativos, com etiqueta de prioridade, checklist de validação e link para o documento de origem.

Rode-a **depois** dos Passos 1 a 6 da Seção 6 (quadro, listas, etiquetas e credenciais prontos).

### 0.1 — O que será criado

Derivado de `docs/relatorio_bugs.md` (rev. 9.0), `docs/relatorio_melhorias.md` (rev. 7.0) e `docs/roadmap.md` (rev. 7.0):

| Lista | Cards | Origem |
|---|---|---|
| 🎯 **Sprint Atual** | 1 barreira + 3 achados Alta | **A5** (1ª execução do CI) · B-A27, B-A29, B-A28 |
| 📋 **Backlog** | 4 achados Médios | B-M25+B-M29, B-M26+M-25, B-M27, B-M28 |
| 📋 **Backlog** | 8 itens estruturais | M-08b, M-21, M-22, M-23, M-01c, M-26, M-07c, Sprint E |
| 📋 **Backlog** | 2 lotes de menor prioridade | B-B17..B-B23 · Sprint D (validar Docker) |

**Total: 17 cards.**

> ⚠️ **Nota da v3.1 (2026-08-26).** O card **[A5]** foi **executado** no mesmo dia, e o resultado justificou a prioridade: a primeira execução do CI reprovou **3 dos 4 jobs** e revelou 4 defeitos (**B-A30**, **B-A31**, **B-M30**, **B-M31**), incluindo uma cadeia de `alembic downgrade` que nunca funcionara. Ao semear o quadro hoje, **substitua [A5]** por um card de acompanhamento das pendências que sobraram: a decisão sobre o histórico do git, e as automações que continuam sem execução real (Docker, restore de backup, Trello, MindMeister) — ver **M-30** em `relatorio_melhorias.md`.

O card **[A5]** entrava na **primeira posição** da Sprint Atual, com vencimento para **hoje**. Não era um achado — era o oposto: cinco barreiras já construídas que nunca haviam executado no ambiente para o qual foram escritas.

Três agrupamentos são deliberados, e a ordem entre eles importa:

| Card agrupado | Por quê |
|---|---|
| **B-A29 + B-M27** | Tocam o mesmo arquivo (`email_sender.py`). Entregar separado significa editar a mesma função duas vezes |
| **B-M25 + B-M29** | Dois defaults, um único arquivo de teste (`test_config_defaults.py`) cobre os dois |
| **B-M26 + M-25** | A barreira (orçamento de queries) precisa vir **antes** da correção — ela tem de reprovar o código atual para provar que funciona |

### 0.2 — Script de seed

```python
#!/usr/bin/env python3
"""
seed_trello_board.py

Cria no Trello os cards correspondentes aos achados ativos do projeto,
a partir do estado documentado em docs/relatorio_bugs.md (rev. 9.0),
docs/relatorio_melhorias.md (rev. 7.0) e docs/roadmap.md (rev. 7.0).

Idempotente: um card cujo título já exista no quadro é pulado, então
rodar duas vezes não duplica nada.

Uso:
    export TRELLO_API_KEY=...
    export TRELLO_TOKEN=...
    export TRELLO_BOARD_ID=...
    python scripts/seed_trello_board.py            # simula, não escreve
    python scripts/seed_trello_board.py --apply    # cria de fato
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta

import requests

API = "https://api.trello.com/1"
TIMEOUT = 20


# ---------------------------------------------------------------- modelo

@dataclass
class CardSpec:
    title: str
    description: str
    list_name: str
    labels: list[str] = field(default_factory=list)
    checklist: list[str] = field(default_factory=list)
    due_in_days: int | None = None
    position: str = "bottom"          # "top" | "bottom"


# ---------------------------------------------------------------- catálogo

DOC = "https://github.com/Rodig0SantOs/Projeto-Auditoria/blob/main/docs"

CARDS: list[CardSpec] = [
    # ------------------------------------------------ BARREIRA NÃO VALIDADA
    CardSpec(
        title="[A5] Primeira execução real do ci.yml num PR",
        description=(
            "**Prioridade: MÁXIMA** · Esforço: 1 h\n\n"
            "O BLOCO P instalou 5 barreiras estruturais e o CI passou de 2 para "
            "4 jobs. **Nenhum deles jamais executou no GitHub Actions.** Uma "
            "barreira validada só por leitura é uma suposição sobre uma "
            "barreira.\n\n"
            "Nenhum outro card deste quadro tem essa relação entre custo e o "
            "que esclarece.\n\n"
            "⚠️ **Previsão explícita:** o job `secrets` (gitleaks com "
            "`fetch-depth: 0`) provavelmente **falha**, porque o histórico "
            "realmente contém as credenciais antigas — já rotacionadas, mas "
            "presentes. Falhar é o resultado esperado; o que este card entrega "
            "é a **decisão** sobre o que fazer com isso.\n\n"
            f"Detalhe: {DOC}/roadmap.md (Sprint A5)"
        ),
        list_name="🎯 Sprint Atual",
        labels=["🔴 Crítico", "🤖 CI/CD"],
        checklist=[
            "git push da branch para origin",
            "Abrir PR contra main",
            "Job `backend`: ruff + pip-audit + pytest --cov",
            "Job `frontend`: npm ci + lint + tsc + build",
            "Job `secrets`: gitleaks sobre o histórico completo",
            "Job `migrations`: upgrade head -> downgrade base -> upgrade head",
            "DECIDIR: .gitleaksignore com as revisões conhecidas OU purgar o histórico",
            "Registrar o resultado de cada job em docs/automacao_commits.md",
        ],
        due_in_days=0,
        position="top",
    ),

    # ------------------------------------------------------------- ALTA
    CardSpec(
        title="[B-A27] Senha acima de 72 bytes derruba /auth/login com HTTP 500",
        description=(
            "**Prioridade: ALTA** · Esforço: 1 h 30\n\n"
            "O bcrypt opera sobre no máximo 72 bytes e, desde a versão 4.0, "
            "levanta `ValueError` em vez de truncar. O ambiente resolve para "
            "**bcrypt 5.0.0**, e nem `security.py` nem os schemas tratam o "
            "limite.\n\n"
            "**É o único achado explorável sem nenhuma credencial:** um "
            "`POST /api/v1/auth/login` com `password` de 100 caracteres produz "
            "exceção não tratada.\n\n"
            "Confirmado por sonda:\n"
            "```\n"
            "ValueError: password cannot be longer than 72 bytes\n"
            "```\n\n"
            "Correção: o limite vira contrato explícito em `core/security.py` "
            "(`MAX_PASSWORD_BYTES`), `hash_password` recusa com exceção de "
            "domínio, `verify_password` devolve `False` (sem criar oráculo).\n\n"
            f"Código completo: {DOC}/relatorio_bugs.md (B-A27)"
        ),
        list_name="🎯 Sprint Atual",
        labels=["🟠 Alto", "🔒 Segurança", "⚙️ Backend"],
        checklist=[
            "MAX_PASSWORD_BYTES + PasswordTooLongError em core/security.py",
            "verify_password devolve False (não levanta) acima do limite",
            "except ValueError defensivo para hash corrompido no banco",
            "Validador de max_length em UserCreate e UserLogin",
            "Tratamento de PasswordTooLongError em auth.py::register (422)",
            "tests/test_password_limits.py — 8 testes",
            "Validar: POST /auth/login com 100 chars responde 401, não 500",
            "Validar: acentos contam 2 bytes (36 'ç' = 72 bytes)",
        ],
        due_in_days=2,
    ),
    CardSpec(
        title="[B-A29] Senha temporária do onboarding se perde sem SMTP",
        description=(
            "**Prioridade: ALTA** · Esforço: 3 h (junto com B-M27)\n\n"
            "A senha temporária é gerada, hasheada e enviada **só** por e-mail. "
            "Sem `SMTP_HOST`, o e-mail não sai e a senha **não existe em lugar "
            "nenhum** — nem na resposta da API, nem no log. O cliente é criado "
            "com empresa e dashboard, e ninguém consegue entrar na conta.\n\n"
            "Não há recuperação de senha na plataforma.\n\n"
            "Pior em produção: `send_sub_user_credentials_email` é chamada "
            "**depois** do commit e **fora** de qualquer try. Uma falha de SMTP "
            "vira HTTP 500 com o usuário já criado; o admin tenta de novo e "
            "recebe 409.\n\n"
            "Confirmado por sonda: `201` com corpo sem senha; log de dev diz "
            "'senha enviada por email em producao'.\n\n"
            f"Código completo: {DOC}/relatorio_bugs.md (B-A29)"
        ),
        list_name="🎯 Sprint Atual",
        labels=["🟠 Alto", "⚙️ Backend", "🎨 Frontend"],
        checklist=[
            "_enviar(msg) -> bool captura SMTPException/OSError e nunca propaga",
            "send_principal_user_credentials_email (função própria, B-M27)",
            "email_delivered + temporary_password em PrincipalUserOnboardingResponse",
            "Mesmo tratamento em SubUserApproveResponse",
            "Frontend exibe a senha com aviso âmbar quando emailDelivered=false",
            "tests/test_credentials_delivery.py — 4 testes",
            "Validar: a senha devolvida realmente autentica",
            "Validar: falha de SMTP não vira 500 (o usuário já foi committado)",
        ],
        due_in_days=2,
    ),
    CardSpec(
        title="[B-A28] Cliente auditado lê o checklist interno e o histórico do auditor",
        description=(
            "**Prioridade: ALTA** · Esforço: 2 h\n\n"
            "O BLOCO P fechou a **escrita** de checklist e histórico "
            "(`require_admin`), mas `GET /dashboard/cards/{id}` devolve as duas "
            "coleções completas a `user` e `sub-user`.\n\n"
            "A assimetria é visível dentro do mesmo arquivo: **notas** de card "
            "são protegidas na leitura (403 confirmado por sonda); checklist e "
            "histórico não são.\n\n"
            "O conteúdo exposto é o trabalho interno do auditor — o que ainda "
            "falta conferir, o que mudou de avaliação, e o **nome** de quem fez "
            "cada ação.\n\n"
            "**Rebaixa o requisito formal RNF-03** (segregação de visão por "
            "perfil) de ✅ para ⚠️.\n\n"
            "Confirmado por sonda: `200` como user e como sub-user, com o "
            "conteúdo interno no corpo.\n\n"
            f"Código completo: {DOC}/relatorio_bugs.md (B-A28)"
        ),
        list_name="🎯 Sprint Atual",
        labels=["🟠 Alto", "🔒 Segurança", "⚙️ Backend"],
        checklist=[
            "Action.READ_CARD_INTERNALS em core/policy.py",
            "get_card_details filtra checklist e history para não-admin",
            "Listas VAZIAS (não 403) — o cliente tem direito ao card",
            "O chat continua bilateral e visível",
            "tests/test_card_internals_visibility.py — 3 testes",
            "Seção de LEITURA em tests/test_authorization_matrix.py (M-23)",
            "Validar: 'INTERNO' não aparece no corpo da resposta ao cliente",
            "Validar: a tela do admin não muda",
        ],
        due_in_days=2,
    ),

    # ------------------------------------------------------------- MÉDIA
    CardSpec(
        title="[B-M25 + B-M29] Defaults inseguros e divergentes de configuração",
        description=(
            "**Prioridade: MÉDIA** · Esforço: 30 min\n\n"
            "Dois defaults, um teste cobre os dois.\n\n"
            "**B-M25:** `ALLOW_PUBLIC_REGISTRATION` tem default `True` em "
            "`core/config.py:24`. O `.env.example` diz 'Mantenha false em "
            "produção' e o compose define `false` — mas quem vale é o código. "
            "Esquecer a variável abre o cadastro público.\n\n"
            "**B-M29:** `JWT_EXPIRES_MINUTES` é **15** no backend e **60** no "
            "frontend (`proxy.ts:30` e `login/route.ts:12`). O cookie sobrevive "
            "45 min ao token que carrega; o proxy renova em silêncio e esconde "
            "a inconsistência atrás de um round-trip extra.\n\n"
            f"Código completo: {DOC}/relatorio_bugs.md (B-M25, B-M29)"
        ),
        list_name="📋 Backlog",
        labels=["🟡 Médio", "🔒 Segurança", "⚙️ Backend", "🎨 Frontend"],
        checklist=[
            "ALLOW_PUBLIC_REGISTRATION: bool = False",
            "proxy.ts: JWT_EXPIRES_MINUTES ?? 15",
            "login/route.ts: JWT_EXPIRES_MINUTES ?? 15",
            "Comentário // Espelha backend/app/core/config.py nos dois",
            "tests/test_config_defaults.py — 3 asserções (M-24)",
        ],
        due_in_days=7,
    ),
    CardSpec(
        title="[B-M28] Guarda de path traversal ficou só na exclusão, não no download",
        description=(
            "**Prioridade: MÉDIA** · Esforço: 1 h 30\n\n"
            "P.2 acrescentou a guarda correta — mas **dentro de "
            "`delete_files()`**, não em `get_absolute_path()`, que é o ponto "
            "único por onde toda resolução passa. O **download** "
            "(`admin.py:307`) resolve sem verificação.\n\n"
            "Não é explorável hoje (`storage_key` só é gravado por `save_file`, "
            "que gera UUID). O problema é de projeto: quem portar o "
            "`StorageBackend` para S3 vai portar `save`, `resolve`, `delete` e "
            "`exists` — e a guarda, por estar no consumidor, não vai junto.\n\n"
            "**Pré-requisito do Sprint D2** (escala horizontal).\n\n"
            f"Código completo: {DOC}/relatorio_bugs.md (B-M28)"
        ),
        list_name="📋 Backlog",
        labels=["🟡 Médio", "🔒 Segurança", "⚙️ Backend"],
        checklist=[
            "_resolver_dentro_do_upload_dir() como ponto único",
            "get_absolute_path() passa a usá-lo",
            "delete_files() consome get_absolute_path()",
            "StorageKeyOutsideUploadDirError tratada em download_evidence (404)",
            "tests/test_storage_path_guard.py — parametrizado com 4 chaves",
            "Validar: nenhum arquivo fora de uploads/ é tocado",
        ],
        due_in_days=10,
    ),
    CardSpec(
        title="[B-M26 + M-25] N+1: GET /admin/companies faz 7 queries por empresa",
        description=(
            "**Prioridade: MÉDIA** · Esforço: 3 h + 4 h da barreira\n\n"
            "Medido por sonda com contador em `before_cursor_execute`: **73 "
            "queries para 10 empresas**. Com o limit padrão de 20, são ~143 por "
            "página.\n\n"
            "O padrão é reconhecível: **uma função de detalhe reusada numa "
            "listagem**. `_load_admin_data` está correta para uma empresa.\n\n"
            "Duas dessas 7 queries leem **a mesma linha de `users` duas vezes** "
            "(`member_user_ids` e `sub_user_emails`).\n\n"
            "⚠️ **Ordem obrigatória:** M-25 (orçamento de queries) **antes** da "
            "correção — a barreira precisa reprovar o código atual para provar "
            "que funciona.\n\n"
            f"Código completo: {DOC}/relatorio_bugs.md (B-M26)"
        ),
        list_name="📋 Backlog",
        labels=["🟡 Médio", "⚡ Performance", "⚙️ Backend"],
        checklist=[
            "Fixture ContadorDeQueries em tests/",
            "tests/test_query_budget.py parametrizado com 5 e 20 empresas",
            "Confirmar que o teste REPROVA o código atual",
            "_bulk_admin_data() com 5 queries agregadas",
            "list_companies_admin usa _bulk_admin_data",
            "Validar: listagem e detalhe devolvem os MESMOS números",
            "Estender o orçamento a GET /admin/audits",
        ],
        due_in_days=14,
    ),
    CardSpec(
        title="[B-M27] Todo cliente principal recebe e-mail dizendo que é sub-usuário",
        description=(
            "**Prioridade: MÉDIA** · Esforço: incluído em B-A29\n\n"
            "O onboarding reusa `send_sub_user_credentials_email`. O e-mail que "
            "chega ao **primeiro contato** de cada cliente novo diz:\n\n"
            "> **Assunto:** Acesso de sub-usuário - Plataforma de Auditoria\n"
            "> OláMaria Silva,\n"
            "> Você foi adicionado como sub-usuário de **Construtora Alfa Ltda**.\n\n"
            "Três erros em quatro frases: o cliente é o responsável (não "
            "sub-usuário); foi adicionado à própria empresa (não subordinado a "
            "ela); e falta o espaço depois de 'Olá' (B-B22).\n\n"
            "Reuso de **infraestrutura** (SMTP, TLS, erro) é correto. Reuso de "
            "**conteúdo endereçado a um papel** não é reuso — é o destinatário "
            "errado recebendo a mensagem de outro.\n\n"
            f"Código completo: {DOC}/relatorio_bugs.md (B-M27)"
        ),
        list_name="📋 Backlog",
        labels=["🟡 Médio", "⚙️ Backend"],
        checklist=[
            "send_principal_user_credentials_email com assunto e corpo próprios",
            "Corrigir 'Olá{nome}' -> 'Olá, {nome}.' (B-B22)",
            "tests/test_email_content.py — 3 testes",
            "Validar: nenhuma senha vai para o log com ou sem SMTP",
        ],
        due_in_days=7,
    ),

    # -------------------------------------------------------- ESTRUTURAIS
    CardSpec(
        title="[M-08b] Testes automatizados de frontend (Vitest + Testing Library)",
        description=(
            "**Prioridade: ALTA (estrutural)** · Esforço: 2–3 dias\n\n"
            "**7.811 LOC. 15 páginas. 9 grupos de Server Actions. 5 route "
            "handlers. Zero testes.**\n\n"
            "A justificativa deixou de ser teórica:\n"
            "- 5 dos 12 defeitos do BLOCO O eram de frontend, e só apareceram "
            "por execução manual;\n"
            "- 11 dos 13 defeitos do BLOCO P foram pegos pela suíte — o backend "
            "tem rede, o frontend não;\n"
            "- o defeito #14 passou por `tsc` e `eslint` e a página renderizava "
            "em branco.\n\n"
            "**O argumento decisivo:** três auditorias adversariais seguidas "
            "produziram achados quase só de backend. Não porque o frontend "
            "esteja mais correto — porque não há como sondá-lo.\n\n"
            "**Desbloqueia M-17** (decompor os 4 arquivos > 500 LOC): "
            "decompor sem teste é reescrever no escuro.\n\n"
            f"Plano de entrada: {DOC}/relatorio_melhorias.md (M-08b)"
        ),
        list_name="📋 Backlog",
        labels=["🟠 Alto", "🧪 Testes", "🎨 Frontend"],
        checklist=[
            "vitest + @vitejs/plugin-react + @testing-library/react + jsdom",
            "vitest.config.ts com alias @ e environment jsdom",
            "npm run test no job `frontend` do ci.yml",
            "Testes dos 9 grupos de Server Actions (callBackend mockado)",
            "Testes de lib/session.ts e lib/safe-redirect.ts",
            "Testes de proxy.ts com NextRequest sintético",
            "Meta: >= 60% de cobertura em actions e lib/",
        ],
        due_in_days=14,
    ),
    CardSpec(
        title="[M-21] Limites físicos de biblioteca como contrato explícito",
        description=(
            "**Prioridade: ALTA (estrutural)** · Esforço: 3 h\n\n"
            "Causa estrutural de **B-A27**. Os schemas validam **regras de "
            "negócio** (mínimo 8 chars, uma maiúscula, um dígito) e nunca "
            "**limites físicos** das bibliotecas que consomem o valor.\n\n"
            "O projeto tem outros limites não modelados: `users.email "
            "VARCHAR(255)` e `dashboard_cards.title VARCHAR(160)` só existem no "
            "banco — uma entrada maior vira `DataError` e HTTP 500.\n\n"
            "**Regra a instalar:** toda coluna `String(n)` do ORM tem um "
            "`max_length=n` correspondente no schema de entrada.\n\n"
            f"Código completo: {DOC}/relatorio_melhorias.md (M-21)"
        ),
        list_name="📋 Backlog",
        labels=["🟠 Alto", "🏗️ Arquitetura", "⚙️ Backend"],
        checklist=[
            "MAX_PASSWORD_BYTES em core/security.py",
            "max_length nos schemas de entrada que faltam",
            "tests/test_schema_length_parity.py varrendo ORM x schema",
            "Validar: coluna nova sem max_length falha o teste",
        ],
        due_in_days=14,
    ),
    CardSpec(
        title="[M-22] Contrato de falha para integrações externas (e-mail)",
        description=(
            "**Prioridade: ALTA (estrutural)** · Esforço: incluído em B-A29\n\n"
            "Causa estrutural de **B-A29** e **B-M27**. Não existe contrato "
            "sobre o que significa 'enviar um e-mail' quando o envio pode "
            "falhar: a função devolve `None`, propaga exceção de SMTP e é "
            "reusada para um destinatário que não é o dela.\n\n"
            "**Regra a instalar:** toda função que fala com sistema externo "
            "devolve sinal de sucesso e **nunca** propaga a falha para uma "
            "transação já committada. É o mesmo princípio que "
            "`storage.delete_files()` já aplica corretamente.\n\n"
            "**Destrava M-09** (e-mail assíncrono).\n\n"
            f"Código completo: {DOC}/relatorio_melhorias.md (M-22)"
        ),
        list_name="📋 Backlog",
        labels=["🟠 Alto", "🏗️ Arquitetura", "⚙️ Backend"],
        checklist=[
            "Separar infraestrutura (_enviar) de conteúdo (send_*)",
            "Retorno booleano em toda função de envio",
            "Nenhuma exceção de SMTP propaga",
            "Documentar a regra em docs/ADR/",
        ],
        due_in_days=7,
    ),
    CardSpec(
        title="[M-23] Estender core/policy.py às leituras sensíveis",
        description=(
            "**Prioridade: MÉDIA (estrutural)** · Esforço: incluído em B-A28\n\n"
            "Causa estrutural de **B-A28**. `policy.py` foi entregue com "
            "precisão, mas as 13 ações são **todas de escrita** — o enum nasceu "
            "da pergunta 'quem pode declarar conformidade?' e respondeu só a "
            "ela. Leitura ficou fora do vocabulário, então cada endpoint decide "
            "sozinho, e `get_card_details` decidiu não decidir.\n\n"
            "**Regra a instalar:** ao acrescentar campo a um `response_model` "
            "que serve a mais de um papel, a pergunta 'este campo pode ser "
            "visto por todos eles?' precisa de resposta em `policy.py`, não no "
            "julgamento de quem escreveu a linha.\n\n"
            f"Código completo: {DOC}/relatorio_melhorias.md (M-23)"
        ),
        list_name="📋 Backlog",
        labels=["🟡 Médio", "🏗️ Arquitetura", "🔒 Segurança"],
        checklist=[
            "Action.READ_CARD_INTERNALS",
            "LEITURAS_RESTRITAS em test_authorization_matrix.py",
            "Documentar a regra em docs/ADR/ADR-01",
        ],
        due_in_days=10,
    ),
    CardSpec(
        title="[M-01c] Unificar as 4 implementações de checagem de posse",
        description=(
            "**Prioridade: MÉDIA (estrutural)** · Esforço: 3 h\n\n"
            "Quatro cópias do mesmo conceito: `client.py:52`, "
            "`dashboard_cards.py:56`, `company_messages.py:24` (com typo "
            "'vísculo' que as outras não têm) e `company_admin.py::"
            "member_user_ids`.\n\n"
            "**Custo já medido:** B-B21 corrige um typo em uma das quatro; "
            "B-B23 (403 -> 404) precisa ser aplicado em **três** arquivos, e o "
            "risco de esquecer um é real.\n\n"
            "Criar `app/core/access.py` como ponto único, carregando a decisão "
            "de B-B23 junto.\n\n"
            f"Código completo: {DOC}/relatorio_melhorias.md (M-01c)"
        ),
        list_name="📋 Backlog",
        labels=["🟡 Médio", "🏗️ Arquitetura", "⚙️ Backend"],
        checklist=[
            "app/core/access.py com resolve_owner_user_id / member_user_ids / get_company_with_access",
            "Os 4 arquivos passam a importar de core.access",
            "404 (não 403) para empresa de outro cliente (B-B23)",
            "Atualizar as asserções de 403 nos testes existentes",
        ],
        due_in_days=21,
    ),
    CardSpec(
        title="[M-26] Escala horizontal: storage remoto + rate limit compartilhado",
        description=(
            "**Prioridade: MÉDIA (estrutural)** · Esforço: 2–3 dias\n\n"
            "Dois estados vivem no processo:\n"
            "- **Evidências** em `backend/uploads/` (volume local): upload cai "
            "na réplica A, download pede à B -> 404;\n"
            "- **Rate limit** na memória do `slowapi`: o limite de 5 logins/min "
            "vira 5 x número de réplicas.\n\n"
            "O `StorageBackend` Protocol já é o ponto de extensão, e obriga a "
            "implementar `delete` — a lacuna que causou B-A26 não pode nascer "
            "de novo num backend novo.\n\n"
            "⚠️ **Depende de B-M28.** Se o S3StorageBackend nascer antes, nasce "
            "sem a guarda de caminho.\n\n"
            "⚠️ **Até este card fechar: não rode o backend com mais de um "
            "worker ou réplica.**\n\n"
            f"Código completo: {DOC}/relatorio_melhorias.md (M-26)"
        ),
        list_name="📋 Backlog",
        labels=["🟡 Médio", "🏗️ Arquitetura", "🤖 CI/CD"],
        checklist=[
            "B-M28 aplicado ANTES (guarda no ponto único)",
            "S3StorageBackend satisfazendo o Protocol (save/resolve/delete/exists)",
            "STORAGE_BACKEND, S3_BUCKET, S3_ENDPOINT_URL em Settings",
            "Migração dos arquivos existentes",
            "RATE_LIMIT_STORAGE_URI (Redis em prod, memory:// em dev)",
            "Validar com 2 réplicas: upload numa, download na outra",
            "Validar: 5 logins/min no CONJUNTO, não por réplica",
        ],
        due_in_days=30,
    ),
    CardSpec(
        title="[M-07c] Trilha de auditoria append-only (RNF-02)",
        description=(
            "**Prioridade: MÉDIA (estrutural)** · Esforço: 1–2 dias\n\n"
            "Requisito formal **RNF-02** ainda em aberto. Mitigado — mas não "
            "resolvido — por B-A23: o histórico de card agora só o admin "
            "escreve.\n\n"
            "O que falta: a tabela é `CASCADE DELETE` a partir do card, é "
            "`UPDATE`/`DELETE`-ável por qualquer acesso ao banco, e cobre "
            "apenas eventos de card — não login, não upload/download de "
            "evidência, não encerramento de auditoria, não exclusão de "
            "empresa.\n\n"
            "Detalhe de projeto: `actor_email` é redundante com a FK **de "
            "propósito** — a FK é `SET NULL`, e a exclusão de usuário é "
            "justamente um dos eventos que a trilha precisa registrar.\n\n"
            f"Modelo completo: {DOC}/relatorio_melhorias.md (M-07c)"
        ),
        list_name="📋 Backlog",
        labels=["🟡 Médio", "🔒 Segurança", "⚙️ Backend"],
        checklist=[
            "models/audit_log.py (sem UPDATE, sem DELETE, sem soft delete)",
            "Migration da tabela audit_log",
            "record_event() em core/",
            "Chamada nos ~8 pontos sensíveis",
            "Política de retenção definida",
        ],
        due_in_days=45,
    ),
    CardSpec(
        title="[Sprint E] Ciclo de vida da credencial: troca, recuperação e revogação",
        description=(
            "**Prioridade: MÉDIA** · Esforço: 2 dias\n\n"
            "Os três itens são o mesmo problema visto de ângulos diferentes: "
            "**a credencial do cliente não tem volta.**\n\n"
            "- **M-02b** — não há troca obrigatória no primeiro login; a senha "
            "temporária pode viver indefinidamente;\n"
            "- **M-29** — não existe nenhum endpoint de recuperação de senha;\n"
            "- **M-28** — tokens stateless sem blocklist: logout é client-side "
            "e um `refresh_token` vazado vale 7 dias.\n\n"
            "**B-A29 é a manifestação aguda disso.** Este card é o tratamento "
            "completo.\n\n"
            f"Detalhe: {DOC}/roadmap.md (Sprint E)"
        ),
        list_name="📋 Backlog",
        labels=["🟡 Médio", "🔒 Segurança", "⚙️ Backend", "🎨 Frontend"],
        checklist=[
            "Coluna must_change_password + bloqueio de rota até a troca",
            "Recuperação de senha (token de uso único, expiração curta)",
            "Blocklist de jti ou tabela de sessões",
            "E-mail assíncrono (destravado por M-22)",
        ],
        due_in_days=45,
    ),

    # ------------------------------------------------------------- BAIXA
    CardSpec(
        title="[B-B17..B-B23] Limpeza: duplicação, typos e dependência sem pin",
        description=(
            "**Prioridade: BAIXA** · Esforço: 2 h (lote único)\n\n"
            "Sete achados Baixos, todos de leitura e `grep`:\n\n"
            "| ID | O quê |\n"
            "|---|---|\n"
            "| B-B17 | Bloco de validação de extensão **duplicado** em `client.py:180-194` |\n"
            "| B-B18 | Typo `TimestampMixim` desde o primeiro commit (4 arquivos) |\n"
            "| B-B19 | `SoftDeleteMixin` declarado e **nunca consultado** (0 queries) |\n"
            "| B-B20 | `structlog` sem pin — única dependência sem restrição |\n"
            "| B-B21 | Typos em mensagens **visíveis ao usuário** (`vísculo`, `paa`) e em `proxy.ts` |\n"
            "| B-B22 | `Olá{nome}` sem espaço no e-mail (incluído em B-M27) |\n"
            "| B-B23 | 403 em vez de 404 revela a existência de `company_id` alheio |\n\n"
            "⚠️ **B-B23 toca 3 arquivos** e as asserções de teste que hoje "
            "afirmam 403. Aplicar junto com M-01c, que unifica os três.\n\n"
            f"Comandos prontos: {DOC}/relatorio_bugs.md (B-B17..B-B23)"
        ),
        list_name="📋 Backlog",
        labels=["🟢 Baixo", "🧹 Limpeza"],
        checklist=[
            "B-B17: remover o bloco duplicado em client.py",
            "B-B18: TimestampMixim -> TimestampMixin (4 arquivos)",
            "B-B19: docstring de aviso no SoftDeleteMixin",
            "B-B20: structlog>=24.1.0,<26.0.0",
            "B-B21: sed nos typos de company_messages.py e proxy.ts",
            "B-B23: 404 nos 3 pontos + atualizar as asserções dos testes",
            "Validar: pytest, ruff, tsc e eslint limpos",
        ],
        due_in_days=30,
    ),
    CardSpec(
        title="[Sprint D] Validar docker build e docker run de verdade",
        description=(
            "**Prioridade: BAIXA** · Esforço: 3 h\n\n"
            "Dockerfiles e compose foram escritos e revisados, mas "
            "**`docker build` e `docker run` nunca foram executados** neste "
            "projeto.\n\n"
            "Item de checklist que quase se esquece: abrir `GET /docs` **dentro "
            "do container**. O defeito #14 (Swagger em branco por CSP) só "
            "aparece no navegador, nunca no log do servidor.\n\n"
            f"Detalhe: {DOC}/roadmap.md (Sprint D)"
        ),
        list_name="📋 Backlog",
        labels=["🟢 Baixo", "🤖 CI/CD"],
        checklist=[
            "docker compose build na raiz",
            "docker compose up -d com .env de teste",
            "MySQL saudável + alembic upgrade head no entrypoint",
            "GET /health respondendo Ok",
            "GET /docs RENDERIZANDO dentro do container",
            "Frontend em :3000",
            "Registrar o resultado em docs/deploy_producao.md",
        ],
        due_in_days=30,
    ),
]



# ---------------------------------------------------------------- API

def _auth() -> dict[str, str]:
    key = os.environ.get("TRELLO_API_KEY")
    token = os.environ.get("TRELLO_TOKEN")
    if not key or not token:
        sys.exit("✗ Defina TRELLO_API_KEY e TRELLO_TOKEN no ambiente.")
    return {"key": key, "token": token}


def _board_id() -> str:
    board = os.environ.get("TRELLO_BOARD_ID")
    if not board:
        sys.exit("✗ Defina TRELLO_BOARD_ID no ambiente.")
    return board


def fetch_lists(board: str, auth: dict) -> dict[str, str]:
    """{nome_da_lista: id}"""
    resp = requests.get(f"{API}/boards/{board}/lists", params=auth, timeout=TIMEOUT)
    resp.raise_for_status()
    return {item["name"]: item["id"] for item in resp.json()}


def fetch_labels(board: str, auth: dict) -> dict[str, str]:
    """{nome_da_etiqueta: id}"""
    resp = requests.get(f"{API}/boards/{board}/labels", params=auth, timeout=TIMEOUT)
    resp.raise_for_status()
    return {item["name"]: item["id"] for item in resp.json() if item["name"]}


def fetch_existing_card_titles(board: str, auth: dict) -> set[str]:
    """Títulos já presentes — a base da idempotência."""
    resp = requests.get(
        f"{API}/boards/{board}/cards",
        params={**auth, "fields": "name"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return {item["name"] for item in resp.json()}


def create_card(spec: CardSpec, list_id: str, label_ids: list[str], auth: dict) -> str:
    payload = {
        **auth,
        "idList": list_id,
        "name": spec.title,
        "desc": spec.description,
        "pos": spec.position,
    }
    if label_ids:
        payload["idLabels"] = ",".join(label_ids)
    if spec.due_in_days is not None:
        payload["due"] = (date.today() + timedelta(days=spec.due_in_days)).isoformat()

    resp = requests.post(f"{API}/cards", params=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()["id"]


def add_checklist(card_id: str, items: list[str], auth: dict) -> None:
    resp = requests.post(
        f"{API}/checklists",
        params={**auth, "idCard": card_id, "name": "Validação"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    checklist_id = resp.json()["id"]
    for item in items:
        requests.post(
            f"{API}/checklists/{checklist_id}/checkItems",
            params={**auth, "name": item, "pos": "bottom"},
            timeout=TIMEOUT,
        ).raise_for_status()


# ---------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="cria os cards de fato (sem esta flag, apenas simula)",
    )
    args = parser.parse_args()

    auth = _auth()
    board = _board_id()

    lists = fetch_lists(board, auth)
    labels = fetch_labels(board, auth)
    existing = fetch_existing_card_titles(board, auth)

    print(f"Quadro {board}: {len(lists)} lista(s), {len(labels)} etiqueta(s), "
          f"{len(existing)} card(s) existente(s)\n")

    created = skipped = 0
    for spec in CARDS:
        if spec.title in existing:
            print(f"  = já existe : {spec.title}")
            skipped += 1
            continue

        if spec.list_name not in lists:
            print(f"  ✗ lista ausente '{spec.list_name}' para: {spec.title}")
            continue

        missing_labels = [name for name in spec.labels if name not in labels]
        if missing_labels:
            print(f"  ! etiquetas ausentes {missing_labels} — card criado sem elas")
        label_ids = [labels[name] for name in spec.labels if name in labels]

        if not args.apply:
            print(f"  + [simulação] {spec.title}")
            created += 1
            continue

        card_id = create_card(spec, lists[spec.list_name], label_ids, auth)
        if spec.checklist:
            add_checklist(card_id, spec.checklist, auth)
        print(f"  + criado    : {spec.title}")
        created += 1

    verb = "seriam criados" if not args.apply else "criados"
    print(f"\n{created} card(s) {verb}, {skipped} pulado(s).")
    if not args.apply:
        print("Nada foi escrito. Rode com --apply para criar de fato.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### 0.3 — Executar

```bash
# 1. Descobrir o ID do quadro
curl -s "https://api.trello.com/1/members/me/boards?key=$TRELLO_API_KEY&token=$TRELLO_TOKEN&fields=name" | python -m json.tool

# 2. Exportar as credenciais
export TRELLO_API_KEY="sua_key"
export TRELLO_TOKEN="seu_token"
export TRELLO_BOARD_ID="id_do_quadro_principal"

# 3. Simular primeiro — nada é escrito
python scripts/seed_trello_board.py

# 4. Criar de fato
python scripts/seed_trello_board.py --apply
```

A simulação é o passo que importa: ela lista o que seria criado, avisa se alguma lista ou etiqueta esperada não existe no quadro, e não escreve nada. Só rode `--apply` depois que a simulação estiver limpa.

### 0.4 — Etiquetas esperadas pelo script

O script pula silenciosamente etiquetas que não existam no quadro (o card é criado sem elas, com aviso). Para cobertura completa, crie estas antes — a Seção 1.3 detalha cores e uso:

```
🔴 Crítico   🟠 Alto   🟡 Médio   🟢 Baixo
⚙️ Backend   🎨 Frontend   🗄️ Banco de Dados
🔒 Segurança   ⚡ Performance   🧪 Testes
🤖 CI/CD   🏗️ Arquitetura   📝 Documentação   🧹 Limpeza
```

> **Nota sobre a etiqueta 🔴 Crítico.** Em 2026-08-26 o projeto voltou a ter **zero achados críticos** — B-C23 foi fechado. A etiqueta segue no quadro, aplicada a um único card: **[A5]**, a primeira execução do CI. Não é um defeito; é a única coisa capaz de dizer se as barreiras que fecharam os defeitos anteriores realmente funcionam.
>
> Manter a etiqueta mesmo com a faixa vazia é intencional: uma faixa de prioridade que não existe no quadro é uma faixa que ninguém usa quando precisa.

### 0.5 — Como manter o catálogo vivo `🆕 v3.0`

Este é o segundo ciclo em que o catálogo precisa ser reescrito, e a razão é estrutural: **ele é derivado de documentos que mudam a cada auditoria**. A v2.0 nasceu apontando para a rev. 8.0 de `relatorio_bugs.md`; quatro dias depois, os 18 achados estavam fechados.

Duas formas de tratar isso, em ordem crescente de esforço:

**(a) Regra de processo — adotar agora, custo zero.**
Toda revisão de `docs/relatorio_bugs.md` que mude a lista de achados ativos exige uma passagem por este catálogo, na mesma sessão. É o que foi feito aqui.

**(b) Gerar o catálogo a partir do documento — a solução de verdade.**
`relatorio_bugs.md` tem estrutura regular o bastante para ser lido por máquina: cada achado é um `## B-XNN — título`, seguido de uma tabela de localização e de seções nomeadas. Um parser converteria isso em `CardSpec` diretamente, e o catálogo deixaria de ser uma cópia.

```python
# scripts/build_trello_catalog.py — esqueleto
import re
from pathlib import Path

PADRAO_ACHADO = re.compile(
    r"^## (B-[CAMB]\d+) — (.+?)(?:\s+`.*`)?$", re.MULTILINE
)
PRIORIDADE_POR_PREFIXO = {
    "B-C": ("🔴 Crítico", "🎯 Sprint Atual", 0),
    "B-A": ("🟠 Alto", "🎯 Sprint Atual", 2),
    "B-M": ("🟡 Médio", "📋 Backlog", 14),
    "B-B": ("🟢 Baixo", "📋 Backlog", 30),
}


def extrair_achados(caminho: Path) -> list[dict]:
    """Lê relatorio_bugs.md e devolve os achados ATIVOS.

    Achados fechados aparecem na seção "Achados fechados desde a rev. X"
    e com o título riscado (~~B-XNN~~) — os dois marcadores são usados
    para excluí-los, porque nenhum dos dois é infalível sozinho.
    """
    texto = caminho.read_text(encoding="utf-8")
    corpo = texto.split("# Achados fechados")[0]
    return [
        {"id": m.group(1), "titulo": m.group(2)}
        for m in PADRAO_ACHADO.finditer(corpo)
        if not m.group(2).startswith("~~")
    ]
```

O gerador dos mapas mentais (`docs/mindmeister_automacao.md`) já enfrentou e resolveu exatamente este problema — os quatro parsers dele lêem `docs/` e produzem a estrutura. **Reaproveitar aqueles parsers é o caminho mais curto**, e evita ter duas implementações do mesmo entendimento sobre o formato de `docs/`.

**Esforço da opção (b):** 4 h. **Impacto:** o catálogo deixa de ser dívida recorrente a cada auditoria.

---

## Seção 1 — Estrutura Ideal dos Quadros

### 1.1 — Quadro Principal: "Plataforma de Auditoria — Dev"

Este é o quadro principal de desenvolvimento. As colunas seguem o fluxo de trabalho de ponta a ponta:

```
📋 Backlog → 🎯 Sprint Atual → 🔨 Em Desenvolvimento → 👀 Em Revisão → 🧪 Em Teste → ✅ Concluído
                                                                                         ↑
                                                                               🚫 Bloqueado (lateral)
```

**Como criar o quadro:**
1. Acesse https://trello.com e clique em **"Criar quadro"**
2. Nome: `Plataforma de Auditoria — Dev`
3. Cor de fundo: azul escuro ou cor da marca STW
4. Visibilidade: **Privado** (apenas membros convidados)

**Criando as listas (em ordem):**

| # | Nome da Lista | Emoji | Propósito |
|---|---|---|---|
| 1 | `📋 Backlog` | 📋 | Tarefas identificadas, ainda não priorizadas. Alimentado por bugs do relatorio_bugs.md e itens do roadmap. |
| 2 | `🎯 Sprint Atual` | 🎯 | Tarefas comprometidas para o sprint/semana corrente. Máximo recomendado: 5 cards por desenvolvedor. |
| 3 | `🔨 Em Desenvolvimento` | 🔨 | Branch criada, desenvolvimento em andamento. O GitHub Actions move cards aqui automaticamente. |
| 4 | `👀 Em Revisão` | 👀 | PR aberto no GitHub. Aguardando code review. GitHub Actions move aqui ao abrir PR. |
| 5 | `🧪 Em Teste` | 🧪 | PR mergeado para main. Aguardando QA ou validação do cliente. |
| 6 | `✅ Concluído` | ✅ | Deploy realizado em produção. Feature ou bug encerrado. |
| 7 | `🚫 Bloqueado` | 🚫 | Tarefas impedidas por dependência externa, aguardando decisão ou informação. |

> **Dica:** Crie as listas nessa ordem exata. O Butler e os scripts Python referenciam as listas pelo nome.

---

### 1.2 — Quadro Secundário: "Bugs & Incidentes"

Quadro dedicado ao rastreamento de bugs — espelha os IDs do `docs/relatorio_bugs.md`.

**Listas do quadro de bugs:**

| Lista | Descrição |
|---|---|
| `🔴 Reportado` | Bug identificado, ainda não confirmado em ambiente real |
| `🟠 Confirmado` | Bug reproduzido e confirmado — aguardando priorização |
| `🟡 Em Correção` | Branch de fix criada, desenvolvedor trabalhando |
| `🟢 Resolvido` | Fix mergeado para main, aguardando validação |
| `⚫ Fechado` | Bug validado como resolvido em produção |

**Nomenclatura dos cards de bug:**

Use o formato `[ID] Título`:
```
[B-C01] bcrypt.hashpw recebe str em vez de bytes
[B-A05] CORS: wildcard + credentials simultâneos
[B-M03] Typo: "controless" em client.py linha 24
```

Isso permite que os scripts de automação identifiquem e sincronizem bugs pelo ID.

---

### 1.3 — Etiquetas (Labels)

Configure estas etiquetas em **ambos os quadros** com as mesmas cores para consistência visual:

**Etiquetas de Prioridade / Severidade:**

| Cor Trello | Label | IDs Correspondentes |
|---|---|---|
| 🔴 Vermelho | `CRÍTICO` | B-C01 a B-C15 — falhas de segurança, crashes, dados perdidos |
| 🟠 Laranja | `ALTO` | B-A01 a B-A16 — funcionalidades comprometidas, sem workaround fácil |
| 🟡 Amarelo | `MÉDIO` | B-M01 a B-M14 — funcionalidade degradada, workaround disponível |
| 🟢 Verde | `BAIXO` | B-B01 a B-B08 — cosmético, convenções, não afeta funcionamento |

**Etiquetas de Tipo:**

| Cor Trello | Label | Quando usar |
|---|---|---|
| 🔵 Azul | `FEATURE` | Nova funcionalidade (`feat:` no commit) |
| 🟣 Roxo | `REFACTOR` | Refatoração de código existente (`refactor:`) |
| 🩵 Ciano | `DOC` | Documentação (`docs:`) |
| 🩷 Rosa | `CI/CD` | Workflows, scripts, automações |
| 🌿 Verde-escuro | `BACKEND` | Afeta FastAPI, banco de dados, modelos |
| 🌊 Azul-marinho | `FRONTEND` | Afeta Next.js, componentes, páginas |

**Como criar etiquetas no Trello:**
1. Abra qualquer card → clique em **"Etiquetas"** no painel lateral
2. Clique no ícone de lápis ao lado de cada cor
3. Digite o nome e salve
4. As etiquetas ficam disponíveis para todos os cards do quadro

---

### 1.4 — Checklists Padrão por Tipo de Card

Use estes templates ao criar novos cards. O Butler pode adicionar automaticamente (ver Seção 2).

**Card de Feature (nova funcionalidade):**
```
Definition of Done — Feature
─────────────────────────────
[ ] Endpoint backend criado e documentado no Swagger (/docs)
[ ] Schema Pydantic de request/response validando corretamente
[ ] Migration Alembic criada (se houver mudança de modelo)
[ ] Componente frontend conectado à API real (sem dados mock)
[ ] Testes adicionados (mínimo: happy path)
[ ] docs/relatorio_funcionalidades.md atualizado
[ ] Code review aprovado
[ ] Deploy realizado e validado
```

**Card de Bug:**
```
Checklist de Correção de Bug
─────────────────────────────
[ ] Bug reproduzido em ambiente local
[ ] Root cause identificada e documentada no card
[ ] Fix implementado no código
[ ] Teste de regressão adicionado
[ ] docs/relatorio_bugs.md atualizado (marcar como corrigido)
[ ] PR criado com referência ao ID do bug (ex: "fix(B-C01):")
[ ] Code review aprovado
[ ] Deploy e validação em produção
```

**Card de Deploy:**
```
Checklist de Deploy
─────────────────────────────
[ ] Branch mergeada para main
[ ] alembic upgrade head executado no servidor
[ ] Seeds verificados (seed_catalog, seed_admin)
[ ] Variáveis de ambiente verificadas (.env no servidor)
[ ] Docker Compose reiniciado (docker compose up -d)
[ ] Teste de fumaça: login de admin funcionando
[ ] Teste de fumaça: interface do cliente funcionando
[ ] Rollback planejado e testado (se aplicável)
[ ] Equipe notificada do deploy
```

---

## Seção 2 — Butler: Automações Sem Código

O **Butler** é o mecanismo de automação nativo do Trello. No plano **Free**, você tem até 10 regras ativas. No **Standard**, são ilimitadas. Para configurar:

1. Abra o quadro → clique em **"Automatizar"** no menu superior direito
2. Selecione **"Regras"** → **"Criar Regra"**

---

### Regra 1 — Data de Vencimento ao Entrar no Sprint

**O que faz:** Quando um card entra na lista "Sprint Atual", define automaticamente a data de vencimento para 7 dias à frente.

**Configuração na UI:**
```
Gatilho: "quando um cartão é movido para a lista '🎯 Sprint Atual'"
Ação:    "definir a data de vencimento do cartão para {7} dias a partir de agora"
```

**Sintaxe Butler (modo texto):**
```
when a card is moved into list "🎯 Sprint Atual",
set due date to 7 days from now
```

---

### Regra 2 — Checklist Automática para Novas Features

**O que faz:** Quando um card com a etiqueta FEATURE é adicionado à lista "Sprint Atual", adiciona automaticamente a checklist "Definition of Done".

**Configuração na UI:**
```
Gatilho: "quando um cartão com etiqueta 'FEATURE' é movido para '🎯 Sprint Atual'"
Ação 1:  "adicionar checklist 'Definition of Done — Feature' ao cartão"
Ação 2:  "adicionar item 'Endpoint backend criado e documentado no Swagger' à checklist"
Ação 3:  "adicionar item 'Schema Pydantic de request/response' à checklist"
... (repetir para cada item)
```

**Sintaxe Butler (modo texto):**
```
when a card with label "FEATURE" is moved into list "🎯 Sprint Atual",
create checklist "Definition of Done — Feature" on the card,
add checklist item "Endpoint backend criado e documentado no Swagger (/docs)" to checklist "Definition of Done — Feature",
add checklist item "Schema Pydantic de request/response validando corretamente" to checklist "Definition of Done — Feature",
add checklist item "Migration Alembic criada (se houver mudança de modelo)" to checklist "Definition of Done — Feature",
add checklist item "Componente frontend conectado à API real (sem mock)" to checklist "Definition of Done — Feature",
add checklist item "Testes adicionados" to checklist "Definition of Done — Feature",
add checklist item "docs/relatorio_funcionalidades.md atualizado" to checklist "Definition of Done — Feature"
```

---

### Regra 3 — Card Concluído Automaticamente

**O que faz:** Quando todos os itens de checklist de um card são marcados, move o card para "Concluído".

**Configuração na UI:**
```
Gatilho: "quando todos os itens de checklist de um cartão são marcados"
Ação:    "mover o cartão para o topo da lista '✅ Concluído'"
```

**Sintaxe Butler:**
```
when all checklist items on a card are checked,
move the card to the top of list "✅ Concluído"
```

---

### Regra 4 — Bug Crítico Sobe ao Topo

**O que faz:** Quando a etiqueta "CRÍTICO" é adicionada a qualquer card, move o card para o topo da lista atual e notifica todos os membros do quadro.

**Configuração na UI:**
```
Gatilho: "quando a etiqueta 'CRÍTICO' é adicionada a um cartão"
Ação 1:  "mover o cartão para o topo da lista"
Ação 2:  "notificar todos os membros do quadro sobre o cartão"
Ação 3:  "adicionar comentário '@all ⚠️ Bug CRÍTICO adicionado — prioridade máxima'"
```

**Sintaxe Butler:**
```
when the label "CRÍTICO" is added to a card,
move the card to the top of the list,
notify all members of the board about the card,
post comment "@all ⚠️ Bug CRÍTICO identificado — prioridade máxima. Verificar docs/relatorio_bugs.md para detalhes."
```

---

### Regra 5 — Alerta de Card Parado

**O que faz:** Quando um card fica 3 dias sem atividade na lista "Em Desenvolvimento", adiciona um comentário de alerta.

> Esta regra usa **Comandos Agendados** (Schedule) no Butler, disponível no plano Standard.

**Configuração:**
```
Gatilho: "todo dia às 09:00"
Condição: "se um cartão na lista '🔨 Em Desenvolvimento' não teve atividade nos últimos 3 dias"
Ação 1:  "adicionar comentário '⚠️ Este card está parado há 3 dias. Está bloqueado?'"
Ação 2:  "notificar os membros do cartão"
```

**Sintaxe Butler:**
```
every day at 9:00 AM,
for each card in list "🔨 Em Desenvolvimento",
if the card has had no activity in the past 3 days,
post comment "⚠️ Card parado há 3 dias. Se estiver bloqueado, mova para '🚫 Bloqueado' e explique o motivo.",
notify the members of the card
```

---

### Regra 6 — Arquivamento Automático de Cards Antigos em Concluído

**O que faz:** Cards na lista "Concluído" há mais de 30 dias são arquivados automaticamente para manter o quadro limpo.

**Configuração:**
```
Gatilho: "todo domingo às 23:00"
Condição: "se um cartão na lista '✅ Concluído' foi movido para esta lista há mais de 30 dias"
Ação: "arquivar o cartão"
```

**Sintaxe Butler:**
```
every sunday at 11:00 PM,
for each card in list "✅ Concluído",
if the card was moved to the current list more than 30 days ago,
archive the card
```

---

## Seção 3 — API do Trello

### 3.1 — Obtendo as Credenciais

**Passo 1 — Obter API Key:**
1. Acesse https://trello.com/power-ups/admin (faça login se necessário)
2. Clique em **"New"** → preencha nome (ex: "Auditoria Automação") e selecione o workspace
3. Na página do Power-Up criado, vá em **"API Key"**
4. Copie a **API Key** (string de 32 caracteres)

**Passo 2 — Gerar Token:**
1. Na mesma página da API Key, clique em **"Token"** (link no texto)
2. Autorize a aplicação para o workspace
3. Copie o **Token** (string de 64 caracteres)

**Passo 3 — Obter IDs do Quadro e Listas:**
```bash
# Listar todos os quadros do usuário autenticado
curl "https://api.trello.com/1/members/me/boards?fields=name,id&key=SUA_API_KEY&token=SEU_TOKEN"

# Listar todas as listas de um quadro
curl "https://api.trello.com/1/boards/SEU_BOARD_ID/lists?key=SUA_API_KEY&token=SEU_TOKEN"

# Listar todas as etiquetas de um quadro
curl "https://api.trello.com/1/boards/SEU_BOARD_ID/labels?key=SUA_API_KEY&token=SEU_TOKEN"
```

---

### 3.2 — Endpoints Fundamentais

**Criar um card:**
```bash
curl -X POST "https://api.trello.com/1/cards" \
  -H "Content-Type: application/json" \
  -d '{
    "idList": "ID_DA_LISTA_BACKLOG",
    "name": "feat(upload): implementar upload de evidências",
    "desc": "## Contexto\nRF-03 do relatorio_documentacao.md\n\n## Critérios de Aceite\n- Endpoint POST /controls/{id}/evidence\n- Suporte a PDF, PNG, JPG (máx 10MB)\n- Integração com storage (local dev / S3 prod)",
    "due": "2026-07-01T23:59:59.000Z",
    "idLabels": ["ID_LABEL_FEATURE", "ID_LABEL_BACKEND"]
  }' \
  "?key=SUA_API_KEY&token=SEU_TOKEN"
```

**Mover um card para outra lista:**
```bash
curl -X PUT "https://api.trello.com/1/cards/ID_DO_CARD" \
  -H "Content-Type: application/json" \
  -d '{"idList": "ID_DA_NOVA_LISTA"}' \
  "?key=SUA_API_KEY&token=SEU_TOKEN"
```

**Adicionar comentário a um card:**
```bash
curl -X POST "https://api.trello.com/1/cards/ID_DO_CARD/actions/comments" \
  -H "Content-Type: application/json" \
  -d '{"text": "🔀 PR #42 aberto: https://github.com/Rodig0SantOs/Projeto-Auditoria/pull/42"}' \
  "?key=SUA_API_KEY&token=SEU_TOKEN"
```

**Criar checklist em um card:**
```bash
# 1. Criar a checklist
curl -X POST "https://api.trello.com/1/checklists" \
  -H "Content-Type: application/json" \
  -d '{"idCard": "ID_DO_CARD", "name": "Definition of Done"}' \
  "?key=SUA_API_KEY&token=SEU_TOKEN"

# Resposta retorna o ID da checklist criada
# 2. Adicionar itens
curl -X POST "https://api.trello.com/1/checklists/ID_DA_CHECKLIST/checkItems" \
  -H "Content-Type: application/json" \
  -d '{"name": "Endpoint criado e documentado no Swagger", "checked": false}' \
  "?key=SUA_API_KEY&token=SEU_TOKEN"
```

**Buscar card pelo nome:**
```bash
curl "https://api.trello.com/1/boards/SEU_BOARD_ID/cards/open?fields=id,name,idList&key=SUA_API_KEY&token=SEU_TOKEN"
```

---

### 3.3 — Script Python Reutilizável

Salve este arquivo em `.github/scripts/trello_client.py`. Todos os workflows de integração o importam:

```python
"""
trello_client.py
Cliente Python para a API do Trello.
Usado pelos workflows de GitHub Actions de integração Trello ↔ GitHub.
"""

import os
import re
import requests
from typing import Optional


class TrelloClient:
    BASE_URL = "https://api.trello.com/1"

    def __init__(self):
        self.api_key = os.environ["TRELLO_API_KEY"]
        self.token = os.environ["TRELLO_TOKEN"]
        self.board_id = os.environ["TRELLO_BOARD_ID"]
        self._auth = {"key": self.api_key, "token": self.token}
        self._list_cache: dict[str, str] = {}  # nome → id
        self._label_cache: dict[str, str] = {}  # nome → id

    # ------------------------------------------------------------------ #
    # Internos
    # ------------------------------------------------------------------ #

    def _get(self, path: str, params: dict = None) -> dict | list:
        resp = requests.get(
            f"{self.BASE_URL}{path}",
            params={**(params or {}), **self._auth},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: dict) -> dict:
        resp = requests.post(
            f"{self.BASE_URL}{path}",
            json=data,
            params=self._auth,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def _put(self, path: str, data: dict) -> dict:
        resp = requests.put(
            f"{self.BASE_URL}{path}",
            json=data,
            params=self._auth,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------ #
    # Listas
    # ------------------------------------------------------------------ #

    def get_lists(self) -> dict[str, str]:
        """Retorna dicionário {nome_da_lista: id} para o quadro configurado."""
        if not self._list_cache:
            lists = self._get(f"/boards/{self.board_id}/lists")
            self._list_cache = {lst["name"]: lst["id"] for lst in lists}
        return self._list_cache

    def get_list_id(self, list_name: str) -> str:
        """Retorna o ID de uma lista pelo nome. Levanta KeyError se não encontrada."""
        lists = self.get_lists()
        if list_name not in lists:
            available = ", ".join(f'"{n}"' for n in lists)
            raise KeyError(
                f'Lista "{list_name}" não encontrada. Disponíveis: {available}'
            )
        return lists[list_name]

    # ------------------------------------------------------------------ #
    # Etiquetas
    # ------------------------------------------------------------------ #

    def get_labels(self) -> dict[str, str]:
        """Retorna dicionário {nome_da_etiqueta: id}."""
        if not self._label_cache:
            labels = self._get(f"/boards/{self.board_id}/labels")
            self._label_cache = {
                lbl["name"]: lbl["id"] for lbl in labels if lbl.get("name")
            }
        return self._label_cache

    def get_label_ids(self, label_names: list[str]) -> list[str]:
        """Converte lista de nomes de etiquetas em lista de IDs."""
        labels = self.get_labels()
        return [labels[name] for name in label_names if name in labels]

    # ------------------------------------------------------------------ #
    # Cards
    # ------------------------------------------------------------------ #

    def get_all_cards(self) -> list[dict]:
        """Retorna todos os cards abertos do quadro."""
        return self._get(
            f"/boards/{self.board_id}/cards/open",
            params={"fields": "id,name,idList,desc"},
        )

    def find_card_by_name(self, name: str) -> Optional[dict]:
        """Busca um card pelo nome exato. Retorna None se não encontrado."""
        cards = self.get_all_cards()
        for card in cards:
            if card["name"] == name:
                return card
        return None

    def find_card_by_pattern(self, pattern: str) -> Optional[dict]:
        """Busca um card cujo nome contém o padrão (case-insensitive)."""
        cards = self.get_all_cards()
        regex = re.compile(pattern, re.IGNORECASE)
        for card in cards:
            if regex.search(card["name"]):
                return card
        return None

    def create_card(
        self,
        list_name: str,
        title: str,
        desc: str = "",
        label_names: list[str] = None,
        due: str = None,
    ) -> dict:
        """
        Cria um novo card na lista especificada.
        Retorna o card criado (com id, shortUrl, etc.).
        """
        data: dict = {
            "idList": self.get_list_id(list_name),
            "name": title,
            "desc": desc,
        }
        if label_names:
            data["idLabels"] = self.get_label_ids(label_names)
        if due:
            data["due"] = due
        return self._post("/cards", data)

    def move_card(self, card_id: str, list_name: str) -> dict:
        """Move um card para a lista especificada pelo nome."""
        return self._put(f"/cards/{card_id}", {"idList": self.get_list_id(list_name)})

    def add_comment(self, card_id: str, text: str) -> dict:
        """Adiciona um comentário ao card."""
        return self._post(f"/cards/{card_id}/actions/comments", {"text": text})

    def add_checklist(self, card_id: str, name: str, items: list[str]) -> dict:
        """Cria uma checklist no card e adiciona todos os itens."""
        checklist = self._post("/checklists", {"idCard": card_id, "name": name})
        checklist_id = checklist["id"]
        for item in items:
            self._post(
                f"/checklists/{checklist_id}/checkItems",
                {"name": item, "checked": False},
            )
        return checklist

    def get_cards_in_list(self, list_name: str) -> list[dict]:
        """Retorna todos os cards de uma lista específica."""
        list_id = self.get_list_id(list_name)
        all_cards = self.get_all_cards()
        return [c for c in all_cards if c["idList"] == list_id]

    def move_all_cards_in_list(self, from_list: str, to_list: str) -> list[dict]:
        """Move todos os cards de uma lista para outra. Útil no deploy."""
        cards = self.get_cards_in_list(from_list)
        moved = []
        for card in cards:
            moved.append(self.move_card(card["id"], to_list))
            print(f"  → Movido: {card['name']}")
        return moved
```

---

## Seção 4 — Webhooks do Trello

Os webhooks permitem que o Trello notifique seu backend FastAPI em tempo real quando eventos acontecem no quadro. É a abordagem inversa: em vez de o GitHub notificar o Trello, o Trello notifica o seu servidor.

### 4.1 — Como Criar um Webhook

```bash
# Substitua os valores pelos seus
curl -X POST "https://api.trello.com/1/webhooks" \
  -H "Content-Type: application/json" \
  -d '{
    "callbackURL": "https://seudominio.com/api/v1/webhooks/trello",
    "idModel": "SEU_BOARD_ID",
    "description": "Webhook do quadro Plataforma de Auditoria Dev"
  }' \
  "?key=SUA_API_KEY&token=SEU_TOKEN"
```

> **Atenção:** O Trello faz uma requisição HEAD para a `callbackURL` ao criar o webhook. Sua URL deve estar acessível e retornar HTTP 200. Em desenvolvimento local, use **ngrok** ou **cloudflare tunnel** para expor a porta 8000.

**Listar webhooks existentes:**
```bash
curl "https://api.trello.com/1/tokens/SEU_TOKEN/webhooks?key=SUA_API_KEY&token=SEU_TOKEN"
```

**Deletar webhook:**
```bash
curl -X DELETE "https://api.trello.com/1/webhooks/ID_DO_WEBHOOK?key=SUA_API_KEY&token=SEU_TOKEN"
```

---

### 4.2 — Tipos de Eventos Disponíveis

| `action.type` | Quando dispara |
|---|---|
| `createCard` | Card criado |
| `updateCard` | Card modificado (movido, título alterado, data alterada) |
| `commentCard` | Comentário adicionado |
| `addLabelToCard` | Etiqueta adicionada |
| `removeLabelFromCard` | Etiqueta removida |
| `updateCheckItemStateOnCard` | Item de checklist marcado/desmarcado |
| `addMemberToCard` | Membro adicionado ao card |
| `archiveCard` | Card arquivado |

---

### 4.3 — Payload de Exemplo (Card Movido)

Quando um card é movido de "Em Desenvolvimento" para "Em Revisão":

```json
{
  "model": {
    "id": "BOARD_ID",
    "name": "Plataforma de Auditoria — Dev"
  },
  "action": {
    "id": "action_id",
    "type": "updateCard",
    "date": "2026-06-24T15:30:22.000Z",
    "data": {
      "card": {
        "id": "card_id",
        "name": "feat(upload): implementar upload de evidências",
        "idShort": 42,
        "shortLink": "abc123"
      },
      "listBefore": {
        "id": "list_id_dev",
        "name": "🔨 Em Desenvolvimento"
      },
      "listAfter": {
        "id": "list_id_review",
        "name": "👀 Em Revisão"
      },
      "board": {
        "id": "BOARD_ID",
        "name": "Plataforma de Auditoria — Dev",
        "shortLink": "xyz789"
      }
    },
    "memberCreator": {
      "id": "member_id",
      "username": "rodrigo_santos",
      "fullName": "Rodrigo Santos"
    }
  }
}
```

---

### 4.4 — Receptor de Webhook no FastAPI

Adicione este endpoint ao backend do projeto:

```python
# backend/app/api/v1/trello_webhook.py

from fastapi import APIRouter, Request, HTTPException
import hmac
import hashlib
import base64
import os

router = APIRouter()

TRELLO_WEBHOOK_SECRET = os.getenv("TRELLO_API_KEY", "")


def verify_trello_signature(body: bytes, signature: str) -> bool:
    """
    Verifica a assinatura HMAC-SHA1 enviada pelo Trello.
    Opcional mas recomendado em produção.
    """
    expected = base64.b64encode(
        hmac.new(
            TRELLO_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha1,
        ).digest()
    ).decode()
    return hmac.compare_digest(expected, signature)


@router.head("/webhooks/trello")
async def trello_webhook_verify():
    """
    Trello faz HEAD ao criar o webhook para verificar que a URL existe.
    Deve retornar 200 OK.
    """
    return {}


@router.post("/webhooks/trello")
async def trello_webhook(request: Request):
    """
    Receptor de eventos do Trello.
    Reage a movimentações de cards, comentários e etiquetas.
    """
    body = await request.body()
    payload = await request.json()

    action = payload.get("action", {})
    action_type = action.get("type")
    data = action.get("data", {})
    card = data.get("card", {})
    list_after = data.get("listAfter", {})
    member = action.get("memberCreator", {})

    card_name = card.get("name", "")
    list_name = list_after.get("name", "")

    # Card movido para "Concluído" → log
    if action_type == "updateCard" and "✅ Concluído" in list_name:
        print(f"✓ Card concluído: '{card_name}' por {member.get('fullName')}")
        # Aqui você pode: enviar e-mail, criar registro no banco, etc.

    # Card movido para "Bloqueado" → enviar e-mail de alerta
    if action_type == "updateCard" and "🚫 Bloqueado" in list_name:
        # Reutiliza o email_sender.py já existente no projeto
        from app.services.email_sender import send_email
        # send_email(to=..., subject="Card bloqueado no Trello", body=...)
        print(f"⚠️ Card bloqueado: '{card_name}'")

    # Comentário com "#deploy" → disparar lógica de deploy
    if action_type == "commentCard":
        comment_text = data.get("text", "")
        if "#deploy" in comment_text.lower():
            print(f"🚀 Deploy acionado via comentário no card '{card_name}'")
            # Aqui você pode: disparar GitHub Actions via API, etc.

    return {"status": "ok"}
```

**Registrar o router no main.py:**
```python
# backend/app/main.py — adicionar após os imports existentes
from app.api.v1.trello_webhook import router as trello_router

app.include_router(trello_router, prefix=settings.API_PREFIX_V1)
```

---

### 4.5 — Testando Localmente com ngrok

Para testar o webhook em desenvolvimento local sem um servidor público:

```bash
# Instalar ngrok: https://ngrok.com/download
# Iniciar túnel para a porta do backend
ngrok http 8000

# ngrok vai exibir uma URL pública, exemplo:
# Forwarding  https://abc123.ngrok.io → http://localhost:8000

# Use essa URL ao criar o webhook:
# callbackURL: "https://abc123.ngrok.io/api/v1/webhooks/trello"
```

---

## Seção 5 — GitHub Actions + Trello

Esta é a **integração principal**: o GitHub Events (branch criada, PR aberto, PR mergeado, deploy) movem cards no Trello automaticamente.

### 5.1 — Workflow: Criar Card ao Criar Branch

**Arquivo:** `.github/workflows/trello-on-branch.yml`

```yaml
name: Trello — Criar Card ao Criar Branch

on:
  create:
    # Dispara quando qualquer branch é criada

permissions:
  contents: read

jobs:
  create-trello-card:
    # Só processa branches feat/*, fix/*, refactor/*, docs/*
    if: |
      github.ref_type == 'branch' &&
      (startsWith(github.ref, 'refs/heads/feat/') ||
       startsWith(github.ref, 'refs/heads/fix/') ||
       startsWith(github.ref, 'refs/heads/refactor/') ||
       startsWith(github.ref, 'refs/heads/docs/'))
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Instalar dependências
        run: pip install requests

      - name: Criar card no Trello
        env:
          TRELLO_API_KEY: ${{ secrets.TRELLO_API_KEY }}
          TRELLO_TOKEN: ${{ secrets.TRELLO_TOKEN }}
          TRELLO_BOARD_ID: ${{ secrets.TRELLO_BOARD_ID }}
          BRANCH_NAME: ${{ github.ref_name }}
          ACTOR: ${{ github.actor }}
          REPO_URL: ${{ github.server_url }}/${{ github.repository }}
        run: |
          python - <<'EOF'
          import sys
          sys.path.insert(0, '.github/scripts')
          from trello_client import TrelloClient
          import os
          import re

          branch = os.environ["BRANCH_NAME"]
          actor = os.environ["ACTOR"]
          repo_url = os.environ["REPO_URL"]

          # Determinar tipo e lista de destino
          if branch.startswith("feat/"):
              list_name = "🔨 Em Desenvolvimento"
              label_names = ["FEATURE"]
              type_emoji = "🚀"
          elif branch.startswith("fix/"):
              list_name = "🔨 Em Desenvolvimento"
              label_names = ["CRÍTICO"] if "critical" in branch else ["ALTO"]
              type_emoji = "🐛"
          elif branch.startswith("refactor/"):
              list_name = "🔨 Em Desenvolvimento"
              label_names = ["REFACTOR"]
              type_emoji = "♻️"
          else:
              list_name = "🔨 Em Desenvolvimento"
              label_names = ["DOC"]
              type_emoji = "📝"

          # Formatar título: "feat/upload-evidencias" → "feat: upload evidencias"
          slug = re.sub(r'^(feat|fix|refactor|docs)/', r'\1: ', branch)
          slug = slug.replace("-", " ")
          title = f"{type_emoji} {slug}"

          desc = f"""## Branch
          `{branch}`

          ## GitHub
          [Ver branch]({repo_url}/tree/{branch})

          ## Criado por
          @{actor}

          ## Notas
          _Adicione contexto, critérios de aceite e referências aqui._
          """

          client = TrelloClient()

          # Verificar se card já existe para evitar duplicatas
          existing = client.find_card_by_pattern(re.escape(branch))
          if existing:
              print(f"Card já existe: {existing['name']}")
          else:
              card = client.create_card(
                  list_name=list_name,
                  title=title,
                  desc=desc,
                  label_names=label_names,
              )
              print(f"✓ Card criado: {card['name']} → {card['shortUrl']}")
          EOF
```

---

### 5.2 — Workflow: Mover Card ao Abrir ou Mergear PR

**Arquivo:** `.github/workflows/trello-on-pr.yml`

```yaml
name: Trello — Sincronizar Card com PR

on:
  pull_request:
    types: [opened, reopened, closed]

permissions:
  contents: read
  pull-requests: read

jobs:
  sync-trello-card:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Instalar dependências
        run: pip install requests

      - name: Sincronizar card no Trello
        env:
          TRELLO_API_KEY: ${{ secrets.TRELLO_API_KEY }}
          TRELLO_TOKEN: ${{ secrets.TRELLO_TOKEN }}
          TRELLO_BOARD_ID: ${{ secrets.TRELLO_BOARD_ID }}
          PR_TITLE: ${{ github.event.pull_request.title }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
          PR_URL: ${{ github.event.pull_request.html_url }}
          PR_BRANCH: ${{ github.event.pull_request.head.ref }}
          PR_ACTION: ${{ github.event.action }}
          PR_MERGED: ${{ github.event.pull_request.merged }}
          COMMIT_SHA: ${{ github.event.pull_request.merge_commit_sha }}
          REPO_URL: ${{ github.server_url }}/${{ github.repository }}
        run: |
          python - <<'EOF'
          import sys, os, re
          sys.path.insert(0, '.github/scripts')
          from trello_client import TrelloClient

          pr_title  = os.environ["PR_TITLE"]
          pr_number = os.environ["PR_NUMBER"]
          pr_url    = os.environ["PR_URL"]
          pr_branch = os.environ["PR_BRANCH"]
          action    = os.environ["PR_ACTION"]
          merged    = os.environ["PR_MERGED"] == "true"
          sha       = os.environ.get("COMMIT_SHA", "")[:7]

          client = TrelloClient()

          # Encontrar card pela branch ou pelo título do PR
          card = (
              client.find_card_by_pattern(re.escape(pr_branch)) or
              client.find_card_by_pattern(re.escape(pr_title[:40]))
          )

          if not card:
              print(f"Nenhum card encontrado para a branch '{pr_branch}' ou título '{pr_title}'")
              print("Crie o card manualmente ou use a convenção de nomes de branch.")
              sys.exit(0)

          card_id = card["id"]
          print(f"Card encontrado: {card['name']}")

          if action in ("opened", "reopened"):
              # PR aberto → mover para Em Revisão
              client.move_card(card_id, "👀 Em Revisão")
              client.add_comment(
                  card_id,
                  f"🔀 **PR #{pr_number} aberto** — aguardando code review\n\n"
                  f"[Ver Pull Request]({pr_url})"
              )
              print(f"✓ Card movido para '👀 Em Revisão'")

          elif action == "closed" and merged:
              # PR mergeado → mover para Em Teste
              client.move_card(card_id, "🧪 Em Teste")
              client.add_comment(
                  card_id,
                  f"✅ **PR #{pr_number} mergeado** para `main`\n\n"
                  f"Commit: `{sha}`\n"
                  f"Aguardando validação em ambiente de teste.\n\n"
                  f"[Ver PR]({pr_url})"
              )
              print(f"✓ Card movido para '🧪 Em Teste'")

          elif action == "closed" and not merged:
              # PR fechado sem merge → mover de volta para Backlog
              client.move_card(card_id, "📋 Backlog")
              client.add_comment(
                  card_id,
                  f"❌ **PR #{pr_number} fechado sem merge**\n\n"
                  f"Card retornado ao Backlog. Verifique os motivos no PR.\n\n"
                  f"[Ver PR]({pr_url})"
              )
              print(f"Card movido para '📋 Backlog' (PR fechado sem merge)")
          EOF
```

---

### 5.3 — Workflow: Sincronizar Bugs do relatorio_bugs.md

Este workflow lê o `docs/relatorio_bugs.md` e cria cards no quadro "Bugs & Incidentes" para cada bug ainda não criado.

**Arquivo:** `.github/workflows/sync-bugs-trello.yml`

```yaml
name: Trello — Sincronizar Bugs

on:
  push:
    branches: [main]
    paths:
      - 'docs/relatorio_bugs.md'
  workflow_dispatch:  # permite disparo manual

permissions:
  contents: read

jobs:
  sync-bugs:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Instalar dependências
        run: pip install requests

      - name: Sincronizar bugs com Trello
        env:
          TRELLO_API_KEY: ${{ secrets.TRELLO_API_KEY }}
          TRELLO_TOKEN: ${{ secrets.TRELLO_TOKEN }}
          TRELLO_BOARD_ID: ${{ secrets.TRELLO_BOARD_ID_BUGS }}
        run: |
          python - <<'EOF'
          import sys, re
          sys.path.insert(0, '.github/scripts')
          from trello_client import TrelloClient
          from pathlib import Path

          REPORT_PATH = Path("docs/relatorio_bugs.md")

          # Mapear prioridade → label e lista inicial
          PRIORITY_MAP = {
              "B-C": ("CRÍTICO",  "🔴 Reportado"),
              "B-A": ("ALTO",     "🔴 Reportado"),
              "B-M": ("MÉDIO",    "🟠 Confirmado"),
              "B-B": ("BAIXO",    "🟡 Em Correção"),
          }

          # Extrair bugs do relatório (padrão: ### B-C01 — Título)
          content = REPORT_PATH.read_text(encoding="utf-8")
          bugs = re.findall(
              r'###\s+(B-[CAMBcamb]\d{2})\s+[—–-]\s+(.+)',
              content
          )

          client = TrelloClient()
          existing_cards = client.get_all_cards()
          existing_names = {c["name"] for c in existing_cards}

          created = 0
          skipped = 0

          for bug_id, bug_title in bugs:
              bug_id = bug_id.upper()
              card_name = f"[{bug_id}] {bug_title.strip()}"

              # Verificar se card já existe
              if any(bug_id in name for name in existing_names):
                  print(f"  → Já existe: {card_name}")
                  skipped += 1
                  continue

              # Determinar prioridade
              prefix = bug_id[:3]
              label_name, list_name = PRIORITY_MAP.get(prefix, ("MÉDIO", "🔴 Reportado"))

              # Criar card
              desc = (
                  f"## ID\n`{bug_id}`\n\n"
                  f"## Referência\n"
                  f"Consulte `docs/relatorio_bugs.md` → seção `{bug_id}`\n\n"
                  f"## Checklist\n"
                  f"- [ ] Bug reproduzido em ambiente local\n"
                  f"- [ ] Root cause identificada\n"
                  f"- [ ] Fix implementado\n"
                  f"- [ ] Teste de regressão adicionado\n"
                  f"- [ ] relatorio_bugs.md atualizado\n"
                  f"- [ ] Deploy e validação"
              )

              card = client.create_card(
                  list_name=list_name,
                  title=card_name,
                  desc=desc,
                  label_names=[label_name],
              )
              print(f"  ✓ Criado: {card_name}")
              created += 1

          print(f"\nResumo: {created} criados, {skipped} já existiam.")
          EOF
```

---

### 5.4 — Workflow: Registrar Deploy no Trello

**Arquivo:** `.github/workflows/trello-on-deploy.yml`

```yaml
name: Trello — Registrar Deploy

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Ambiente de deploy'
        required: true
        type: choice
        options: [staging, production]
      notes:
        description: 'Notas do deploy (opcional)'
        required: false
        default: ''

permissions:
  contents: read

jobs:
  register-deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Instalar dependências
        run: pip install requests

      - name: Registrar deploy no Trello
        env:
          TRELLO_API_KEY: ${{ secrets.TRELLO_API_KEY }}
          TRELLO_TOKEN: ${{ secrets.TRELLO_TOKEN }}
          TRELLO_BOARD_ID: ${{ secrets.TRELLO_BOARD_ID }}
          ENVIRONMENT: ${{ github.event.inputs.environment }}
          NOTES: ${{ github.event.inputs.notes }}
          ACTOR: ${{ github.actor }}
          SHA: ${{ github.sha }}
          REPO_URL: ${{ github.server_url }}/${{ github.repository }}
        run: |
          python - <<'EOF'
          import sys, os
          from datetime import datetime
          sys.path.insert(0, '.github/scripts')
          from trello_client import TrelloClient

          env       = os.environ["ENVIRONMENT"]
          notes     = os.environ["NOTES"]
          actor     = os.environ["ACTOR"]
          sha       = os.environ["SHA"][:7]
          repo_url  = os.environ["REPO_URL"]
          now       = datetime.now().strftime("%Y-%m-%d %H:%M")

          emoji = "🚀" if env == "production" else "🧪"
          client = TrelloClient()

          # 1. Mover todos os cards de "Em Teste" para "Concluído"
          print(f"Movendo cards de '🧪 Em Teste' para '✅ Concluído'...")
          moved = client.move_all_cards_in_list("🧪 Em Teste", "✅ Concluído")

          # 2. Adicionar comentário de deploy em cada card movido
          deploy_comment = (
              f"{emoji} **Deploy para {env.upper()}** — {now}\n\n"
              f"Commit: `{sha}`\n"
              f"Responsável: @{actor}\n"
              + (f"Notas: {notes}\n" if notes else "")
              + f"\n[Ver histórico de commits]({repo_url}/commits/main)"
          )

          for card in moved:
              card_id = card.get("id") or card.get("cards", [{}])[0].get("id")
              if card_id:
                  client.add_comment(card_id, deploy_comment)

          # 3. Criar card de registro do deploy no Concluído
          deploy_card = client.create_card(
              list_name="✅ Concluído",
              title=f"{emoji} Deploy {env.upper()} — {now} ({sha})",
              desc=(
                  f"## Detalhes do Deploy\n\n"
                  f"- **Ambiente:** {env}\n"
                  f"- **Data/Hora:** {now}\n"
                  f"- **Commit:** `{sha}`\n"
                  f"- **Responsável:** @{actor}\n"
                  + (f"- **Notas:** {notes}\n" if notes else "")
                  + f"\n## Cards incluídos neste deploy\n"
                  + "\n".join(f"- {c.get('name', 'card')}" for c in moved)
              ),
              label_names=["CI/CD"],
          )

          print(f"\n✓ Deploy registrado: {deploy_card['name']}")
          print(f"✓ {len(moved)} card(s) movido(s) para '✅ Concluído'")
          EOF
```

---

### 5.5 — Secrets Necessários no GitHub

Configure estes secrets em `github.com/Rodig0SantOs/Projeto-Auditoria` → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Valor | Onde obter |
|---|---|---|
| `TRELLO_API_KEY` | API Key de 32 chars | https://trello.com/power-ups/admin |
| `TRELLO_TOKEN` | Token de 64 chars | Link "Token" na página da API Key |
| `TRELLO_BOARD_ID` | ID do quadro principal | `curl .../members/me/boards` |
| `TRELLO_BOARD_ID_BUGS` | ID do quadro de bugs | Mesmo endpoint, segundo quadro |

**Como obter o BOARD_ID:**
```bash
# Substitua com sua API Key e Token
curl "https://api.trello.com/1/members/me/boards?fields=id,name&key=SUA_API_KEY&token=SEU_TOKEN"

# Saída exemplo:
# [{"id":"abc123def456","name":"Plataforma de Auditoria — Dev"},
#  {"id":"xyz789ghi012","name":"Bugs & Incidentes"}]
```

---

## Seção 6 — Configuração Completa Passo a Passo

Siga esta sequência para configurar tudo do zero em uma nova conta Trello:

### Passo 1 — Criar Conta e Workspace

1. Acesse https://trello.com/signup
2. Crie um workspace com o nome da organização (ex: "STW Brasil")
3. Convide os membros da equipe pelo e-mail

### Passo 2 — Criar o Quadro Principal

1. No workspace, clique em **"Criar um quadro"**
2. Nome: `Plataforma de Auditoria — Dev`
3. Visibilidade: Privado
4. Crie as 7 listas **nessa ordem exata**:
   - `📋 Backlog`
   - `🎯 Sprint Atual`
   - `🔨 Em Desenvolvimento`
   - `👀 Em Revisão`
   - `🧪 Em Teste`
   - `✅ Concluído`
   - `🚫 Bloqueado`

### Passo 3 — Criar o Quadro de Bugs

1. Crie um segundo quadro: `Bugs & Incidentes`
2. Crie as 5 listas:
   - `🔴 Reportado`
   - `🟠 Confirmado`
   - `🟡 Em Correção`
   - `🟢 Resolvido`
   - `⚫ Fechado`

### Passo 4 — Criar as Etiquetas

Nos dois quadros, crie as etiquetas com as cores descritas na Seção 1.3:

1. Abra qualquer card → clique em **"Etiquetas"** no painel lateral
2. Clique no ícone **✏️** ao lado de cada cor padrão
3. Digite o nome (CRÍTICO, ALTO, MÉDIO, etc.) e salve
4. Repita para todas as etiquetas e nos dois quadros

### Passo 5 — Obter Credenciais da API do Trello

1. Acesse https://trello.com/power-ups/admin
2. Clique em **"New"** → nome: "Automação GitHub" → workspace selecionado
3. Acesse o Power-Up criado → aba **"API Key"**
4. Copie a **API Key**
5. Clique no link **"Token"** no texto → autorize → copie o **Token**
6. Obtenha os IDs dos quadros com o curl da Seção 5.5

### Passo 6 — Configurar Secrets no GitHub

1. Acesse `github.com/Rodig0SantOs/Projeto-Auditoria/settings/secrets/actions`
2. Adicione os 4 secrets: `TRELLO_API_KEY`, `TRELLO_TOKEN`, `TRELLO_BOARD_ID`, `TRELLO_BOARD_ID_BUGS`

### Passo 7 — Adicionar o Script Python ao Repositório

Copie o conteúdo da Seção 3.3 (classe `TrelloClient`) para:
```
.github/scripts/trello_client.py
```

### Passo 8 — Criar os Workflows de Integração

Crie os 4 arquivos de workflow em `.github/workflows/`:
- `trello-on-branch.yml` (Seção 5.1)
- `trello-on-pr.yml` (Seção 5.2)
- `sync-bugs-trello.yml` (Seção 5.3)
- `trello-on-deploy.yml` (Seção 5.4)

Faça commit e push de tudo para `main`.

### Passo 9 — Configurar as Regras do Butler

No quadro principal, configure as 6 regras da Seção 2 (uma por uma, na UI do Trello).

### Passo 10 — Testar a Integração

```bash
# Criar uma branch de feature para testar
git checkout -b feat/teste-integracao-trello
git commit --allow-empty -m "test: branch de teste para verificar integração Trello"
git push origin feat/teste-integracao-trello
```

**Verificar no GitHub Actions:**
1. Acesse `github.com/Rodig0SantOs/Projeto-Auditoria/actions`
2. Procure o workflow "Trello — Criar Card ao Criar Branch"
3. Aguarde ~30 segundos

**Verificar no Trello:**
1. Acesse o quadro "Plataforma de Auditoria — Dev"
2. Na lista "🔨 Em Desenvolvimento", deve aparecer o novo card
3. Abra um PR no GitHub e verifique se o card move para "👀 Em Revisão"

**Limpar o teste:**
```bash
git checkout main
git branch -d feat/teste-integracao-trello
git push origin --delete feat/teste-integracao-trello
```

---

## Seção 7 — Tabela de Referência Rápida

### Eventos e Ações Automatizadas

| Evento GitHub | Workflow | Ação no Trello |
|---|---|---|
| Branch `feat/*` criada | `trello-on-branch.yml` | Card criado em "🔨 Em Desenvolvimento" com label FEATURE |
| Branch `fix/*` criada | `trello-on-branch.yml` | Card criado em "🔨 Em Desenvolvimento" com label ALTO/CRÍTICO |
| PR aberto | `trello-on-pr.yml` | Card movido para "👀 Em Revisão" + comentário com link do PR |
| PR mergeado para main | `trello-on-pr.yml` | Card movido para "🧪 Em Teste" + comentário com hash |
| PR fechado sem merge | `trello-on-pr.yml` | Card voltado para "📋 Backlog" + comentário explicativo |
| Push em `relatorio_bugs.md` | `sync-bugs-trello.yml` | Cards de bugs criados no quadro "Bugs & Incidentes" |
| Deploy manual disparado | `trello-on-deploy.yml` | Cards de "🧪 Em Teste" movidos para "✅ Concluído" + card de registro |

### Butler Rules Configuradas

| Regra | Gatilho | Ação |
|---|---|---|
| Data de vencimento | Card entra em "Sprint Atual" | Due date = hoje + 7 dias |
| Checklist de feature | Card FEATURE entra em "Sprint Atual" | Adiciona "Definition of Done" com 6 itens |
| Conclusão automática | Todos os itens da checklist marcados | Move para "✅ Concluído" |
| Bug crítico ao topo | Label "CRÍTICO" adicionada | Sobe ao topo + notifica todos |
| Alerta de parado | Card sem atividade há 3 dias em "Em Desenvolvimento" | Comentário de alerta + notificação |
| Arquivamento | Card em "Concluído" há 30 dias | Arquiva automaticamente |

### Secrets do GitHub Necessários

| Secret | Origem |
|---|---|
| `TRELLO_API_KEY` | https://trello.com/power-ups/admin |
| `TRELLO_TOKEN` | Link "Token" na página da API Key |
| `TRELLO_BOARD_ID` | `curl .../members/me/boards` |
| `TRELLO_BOARD_ID_BUGS` | Mesmo endpoint, quadro de bugs |

### Endpoints da API Mais Usados

| Operação | Método | Endpoint |
|---|---|---|
| Listar quadros | GET | `/1/members/me/boards` |
| Listar listas | GET | `/1/boards/{id}/lists` |
| Listar cards | GET | `/1/boards/{id}/cards/open` |
| Criar card | POST | `/1/cards` |
| Mover card | PUT | `/1/cards/{id}` body: `{idList}` |
| Comentar | POST | `/1/cards/{id}/actions/comments` |
| Criar checklist | POST | `/1/checklists` |
| Adicionar item | POST | `/1/checklists/{id}/checkItems` |
| Criar webhook | POST | `/1/webhooks` |

---

## Referências

| Recurso | Link |
|---|---|
| Documentação da API do Trello | https://developer.atlassian.com/cloud/trello/rest/api-group-actions |
| Trello Power-Ups Admin | https://trello.com/power-ups/admin |
| Documentação do Butler | https://support.atlassian.com/trello/docs/what-is-butler |
| GitHub Actions — eventos disponíveis | https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows |
| ngrok (testes locais de webhook) | https://ngrok.com/download |

**Documentos internos relacionados:**

| Arquivo | Conteúdo |
|---|---|
| `docs/relatorio_bugs.md` | Achados catalogados (rev. 9.0 — IDs `B-A27..B-A29`, `B-M25..B-M29`, `B-B17..B-B23`). **Fonte do catálogo da Seção 0** — ver 0.5 |
| `docs/roadmap.md` | Fases e sprints para popular o Backlog (rev. 6.0 — Sprint A0 e A3) |
| `docs/relatorio_melhorias.md` | Melhorias estruturais M-15..M-20 usadas nos cards da Seção 0 |
| `docs/relatorio_funcionalidades.md` | Features para criação de cards |
| `docs/backlog.md` | Backlog consolidado — fonte alternativa para popular o quadro |
| `docs/automacao_commits.md` | Automação de relatório de commits (GitHub Actions) |
| `.github/workflows/commit-report.yml` | Workflow existente que gera relatorio_commit.md |
| `.github/scripts/generate_commit_report.py` | Script Python existente de relatório |

---

*Documentação atualizada em 2026-08-26 (v3.0). O catálogo da Seção 0 foi reescrito para o estado real em `34f8444` — 17 cards, contra os 18 da v2.0, todos fechados desde então. As Seções 1 a 7 foram revisadas e permanecem válidas. **Nenhuma parte deste documento foi executada contra um Trello real** — o quadro ainda não existe. Antes de confiar nos scripts, rode-os em modo de simulação (sem `--apply`) contra um quadro de teste.*

*Para o sequenciamento das fases, consulte `docs/roadmap.md`; para os achados que alimentam os cards, `docs/relatorio_bugs.md`.*
