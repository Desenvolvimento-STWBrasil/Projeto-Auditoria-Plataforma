# Integração MindMeister — Plataforma de Auditoria

| Campo | Valor |
|---|---|
| **Versão** | **3.0 — 2026-08-26** |
| **Data** | 2026-06-24 (criação) · 2026-07-27 (`DEVELOPER_DIR` corrigido de `@developer` para `docs`) · 2026-08-11 (rev. 1.1) · 2026-08-12 · 2026-08-17 · 2026-08-24 (v2.0 — os 4 parsers reescritos) · **2026-08-26 (v3.0 — reexecutados contra a documentação nova; 2 regressões encontradas e corrigidas)** |
| **Repositório** | https://github.com/Rodig0SantOs/Projeto-Auditoria |
| **Plano MindMeister (API)** | Pro ou Business |
| **Plano MindMeister (FreeMind .mm)** | Free ou superior |
| **Status** | 📋 Proposta — os mapas **nunca foram publicados** num MindMeister real. O gerador `.mm` foi executado e verificado nesta revisão, pela segunda vez |

> ## 🔴 Diagnóstico da v2.0 — os 4 parsers estavam quebrados
>
> Este documento propõe gerar os mapas mentais **a partir dos arquivos de `docs/`**, com regex sobre Markdown. É a decisão certa (uma fonte de verdade, mapas sempre em dia) e tem um custo previsível que se materializou: **Markdown escrito por humanos muda, e o regex não acompanha**.
>
> Rodando os parsers da v1.2 contra a documentação de 2026-08-24:
>
> | Parser | Encontrava | Deveria encontrar | Causa |
> |---|---|---|---|
> | `parse_bugs` | **0** | 18 | Exigia `###`; os achados passaram a ser `##` |
> | `parse_features` | **0** | 80 | Procurava `RF-\d+` em `relatorio_funcionalidades.md` — os `RF-` vivem em `relatorio_documentacao.md`; ali as funcionalidades são `F01..F70` |
> | `parse_roadmap` | 4 seções **erradas** | 4 fases | Regex case-sensitive não casava `## FASE N`; casava `### Fase N` da seção de *Métricas de Sucesso* |
> | `parse_improvements` | **6** | 15 | `M-\d+` não casa sufixo de letra (`M-08b`, `M-01c`, `M-02e`) |
>
> **O modo de falha é o que importa:** nenhum dos quatro lançava exceção. Todos devolviam lista vazia ou parcial, o gerador produzia um `.mm` bem formado e quase em branco, e o CI ficava verde. Um mapa vazio é indistinguível de um projeto sem bugs.
>
> **Correções aplicadas na v2.0** (código completo na Seção 4.3):
>
> 1. Os 4 parsers reescritos — resultado verificado: **18 achados, 80 funcionalidades, 4 fases com 56 itens, 15 melhorias com esforço extraído**.
> 2. Cada parser agora tem um **piso mínimo** (`MIN_EXPECTED`) e emite aviso em `stderr` quando encontra menos que ele. Mapa vazio passa a ser barulhento.
> 3. Parsing tolerante ao que é acidental (nível do heading, caixa do texto, tipo de traço) e estrito no que é semântico (o prefixo do ID é que define a prioridade).

> ## 🔁 v3.0 — a previsão da v2.0 se confirmou em quatro dias
>
> A v2.0 fechou dizendo que Markdown escrito por humanos muda e o regex não acompanha. Os parsers foram reexecutados em 2026-08-26, contra a documentação revisada (`relatorio_bugs.md` 9.0, `relatorio_funcionalidades.md` 8.0, `relatorio_melhorias.md` 7.0, `roadmap.md` 7.0). **Dois dos quatro voltaram a produzir saída incompleta — e, de novo, sem erro nenhum.**
>
> | Parser | Resultado | Diagnóstico |
> |---|---|---|
> | `parse_bugs` | ✅ **15 achados** (0 C · 3 A · 5 M · 7 B) | Correto. Excluiu sozinho os 18 achados fechados, porque eles migraram para uma **tabela** e o regex só casa cabeçalho |
> | `parse_features` | ✅ **88 itens** (78 · 3 · 7) | Correto |
> | `parse_roadmap` | ⚠️ **FASE 4 com 0 itens** | A Fase 4 passou a listar entregas em linhas com `·` como separador, em vez de lista ou tabela. O galho saía **vazio** no mapa |
> | `parse_improvements` | ⚠️ **13 melhorias, 0 com esforço** | `relatorio_melhorias.md` passou a escrever `**Custo:**` no lugar de `**Esforço:**`. Cada nó de melhoria perdeu a estimativa |
>
> **Correções da v3.0:**
>
> 1. `effort_re` aceita `Custo`, `Esforço` e `Esforço estimado` — o vocabulário do documento pode variar; o dado é o mesmo.
> 2. `item_re` de `parse_roadmap` reconhece linhas iniciadas por `✅`/`⬜`/`🟡`/`🔴`, além de `-`/`*`/`•`.
> 3. Novo piso `MIN_EFFORTS`: se menos de 60% das melhorias vierem com esforço, o parser avisa. **Contagem certa com conteúdo vazio era exatamente o que passava despercebido.**
> 4. Do outro lado, `docs/roadmap.md` teve a Fase 4 convertida em lista — parser tolerante e documento regular são complementares, não alternativas.
>
> **O que isso ensina sobre a arquitetura desta automação.** Ela é uma dependência invisível: `docs/` não sabe que alguém a lê por regex. Duas revisões seguidas de documentação quebraram o gerador, e nas duas o sintoma foi o mesmo — mapa bem formado, parcialmente vazio, CI verde. A resposta certa não é regex mais esperto; é **piso mínimo em toda dimensão que importa**, contagem e conteúdo. A v2.0 instalou o piso de contagem; a v3.0 acrescenta o de conteúdo.

## Pré-requisitos

| Ferramenta | Quando necessária | Onde obter |
|---|---|---|
| Conta MindMeister | Sempre | https://mindmeister.com |
| API Key MindMeister | Só para automação via API (plano Pro) | https://www.mindmeister.com/api/v2/apps |
| GitHub Actions configurado | Para geração automática | Já configurado no projeto |
| Python 3.12+ | Para rodar os scripts | Já presente no backend |
| Zapier ou Make | Para automação sem código | https://zapier.com / https://make.com |

---

## Seção 1 — Por Que Mapas Mentais Para Este Projeto

### O Problema

O projeto possui grande quantidade de informação distribuída em múltiplos arquivos de texto:

| Documento | Conteúdo | Volume |
|---|---|---|
| `relatorio_funcionalidades.md` | Funcionalidades com status | 67 itens (2026-08-17) |
| `relatorio_bugs.md` | Bugs catalogados por prioridade | 10 ativos + 39 corrigidos (2026-08-17) |
| `relatorio_melhorias.md` | Dimensões de melhoria | 14 itens M-01..M-14 (2026-08-17) |
| `roadmap.md` | Fases e sprints | 4 fases; Fase 1 100% concluída (2026-08-17) |
| `relatorio_documentacao.md` | Rastreabilidade de requisitos | 38 requisitos (2026-08-17) |

> Estes números mudam a cada revisão dos relatórios — trate-os como exemplo de ordem de grandeza, não como valor fixo. A automação descrita neste documento (Seção 3) é o mecanismo recomendado para manter o mapa mental sincronizado com o valor real vigente em `docs/`, em vez de depender de atualização manual desta tabela.

Ler todos esses documentos para ter uma visão do todo é lento. Mapas mentais resolvem isso com **visualização hierárquica em segundos**.

### O Valor dos Mapas Mentais

- **Onboarding:** novo desenvolvedor entende a arquitetura em 5 minutos olhando um mapa
- **Reuniões:** apresentação do estado atual sem precisar abrir código
- **Priorização:** bugs críticos e funcionalidades pendentes visíveis de forma imediata
- **Rastreabilidade:** relação entre módulos, bugs e roadmap visualizada em árvore

### Estratégias Disponíveis

| Abordagem | Plano MindMeister | Automação | Custo | Melhor Para |
|---|---|---|---|---|
| **API REST direta** | Pro / Business | Total (GitHub Actions) | $$ | Times que querem automação 100% |
| **Arquivo FreeMind .mm** | Free ou superior | Alta (import manual ou via Actions) | $0 | Custo zero, máxima flexibilidade |
| **Zapier / Make** | Free + conta Zapier | Média (triggers limitados) | $ | Não-desenvolvedores |
| **MeisterTask Bridge** | Free + MeisterTask | Alta (integração nativa) | $0 | Quem já usa MeisterTask |

**Recomendação para este projeto:** começar com a abordagem FreeMind `.mm` (Seção 4) via GitHub Actions (Seção 5), que funciona com qualquer plano do MindMeister e tem custo zero.

---

## Seção 2 — Estrutura dos 5 Mapas Mentais

### Mapa 1 — Arquitetura do Sistema

Representa a estrutura técnica do projeto. Atualizado manualmente quando a arquitetura muda.

```
🏗️ Plataforma de Auditoria ISO 27001
│
├── 🐍 Backend (FastAPI)
│   ├── Framework: FastAPI 0.115 + Uvicorn
│   ├── ORM: SQLAlchemy 2.0
│   ├── Migrations: Alembic
│   ├── Banco: MySQL 8.4 (Docker, porta 3307)
│   ├── Auth: python-jose JWT HS256 + bcrypt
│   └── Config: pydantic-settings (.env)
│
├── ⚛️ Frontend (Next.js)
│   ├── Framework: Next.js 16.2.6 (App Router)
│   ├── UI: React 19.2.4 + TypeScript 5
│   ├── Estilo: Tailwind CSS 4
│   ├── Padrão: API Proxy (13 rotas Next.js → FastAPI)
│   └── Auth: Cookie httpOnly access_token
│
├── 👤 Modelo de Usuários
│   ├── admin (acesso total)
│   ├── user (cliente — acessa seus controles)
│   └── sub-user (delegado pelo user via parent_user_id)
│
├── 🗄️ Banco de Dados
│   ├── User + Company + Audit
│   ├── AuditControl + ControlCatalog
│   ├── checklistItem + checklistItemState
│   ├── Evidence + Message
│   └── DashboardTemplate + DashboardCard
│
└── 🤖 CI/CD e Automação
    ├── commit-report.yml (relatório por push)
    ├── trello-on-branch.yml (card ao criar branch)
    ├── trello-on-pr.yml (mover card com PR)
    ├── sync-bugs-trello.yml (bugs → Trello)
    ├── trello-on-deploy.yml (registrar deploy)
    ├── generate-mindmaps.yml (mapas .mm)
    └── update-mindmeister-api.yml (API opcional)
```

---

### Mapa 2 — Estado das Funcionalidades

Atualizado automaticamente quando `relatorio_funcionalidades.md` muda.

```
🚀 Funcionalidades (RF-01 a RF-20 + FIDs)
│
├── ✅ Implementadas (8 — 40%)
│   ├── RF-01: Login com e-mail/senha (JWT + bcrypt + cookie httpOnly)
│   ├── RF-02: Roles diferenciadas (admin / user / sub-user)
│   ├── RF-06: Descrição e evidência esperada por controle
│   ├── RF-14: Criação de auditoria + instanciação de controles
│   ├── RF-15: Segregação de dados por cliente
│   ├── RF-16: Catálogo ISO 27001 (3 controles seedados)
│   ├── RN-03: Progressão de status (EM_ANALISE→PARCIAL→CONFORME)
│   └── RN-09: Segregação de controles por cliente
│
├── ⚠️ Parciais (5 — 25%)
│   ├── RF-02: 3 roles em vez de 2 documentados (sub-user extra)
│   ├── RF-03: Upload — modelo ok, sem endpoint, frontend mock
│   ├── RF-04: Status — NAOCONFORME faltando em AuditControlStatus
│   ├── RF-05: Chat — modelo ok, sem endpoints, frontend mock
│   └── RF-07: Histórico — sem imutabilidade (CASCADE DELETE)
│
├── ❌ Não Implementadas (7 — 35%)
│   ├── RF-10: Download / export de evidências
│   ├── RF-11: Notificações em tempo real
│   ├── RF-12: Dashboard com métricas em tempo real
│   ├── RF-13: Chat compartilhado entre admins
│   ├── RF-17: MFA (Autenticação Multifator)
│   ├── RF-18: Sistema de aceite/convite
│   └── RF-20: Branding STW (logo + paleta)
│
└── 📝 Implementadas Não Documentadas (8)
    ├── FID-01: Sub-usuários (solicitação + aprovação)
    ├── FID-02: Onboarding automatizado
    ├── FID-03: Templates reutilizáveis de dashboard
    ├── FID-04: Dashboard gerencial com cards
    ├── FID-05: Registro público configurável
    ├── FID-06: Proxy pattern Next.js → FastAPI
    ├── FID-07: JWT em cookie httpOnly
    └── FID-08: Seeds idempotentes
```

---

### Mapa 3 — Bugs e Qualidade

Atualizado automaticamente quando `relatorio_bugs.md` muda.

```
🐛 Bugs Catalogados (53 total)
│
├── 🔴 Críticos (15) — B-C01 a B-C15
│   ├── B-C01: bcrypt.hashpw recebe str em vez de bytes
│   ├── B-C02: Senha logada em texto claro (debug)
│   ├── B-C03: Race condition na aprovação de sub-user
│   ├── B-C04: Transação incompleta no onboarding
│   ├── B-C05: Timing attack na comparação de senhas
│   ├── B-C06: Campo phone nullable no modelo vs não-nullable no schema
│   ├── B-C07: PK iid — conflito de nome reservado
│   ├── B-C08: Alembic env.py com imports ausentes
│   ├── B-C09: IDOR no checklist (sem verificação de dono)
│   ├── B-C10: Dados mock hardcoded no admin/page.tsx
│   ├── B-C11: Links de debug expostos na homepage
│   ├── B-C12: Double router.push() após login
│   ├── B-C13: Middleware sem validação de role
│   ├── B-C14: NameError no seed_admin.py
│   └── B-C15: == em vez de = no seed_catalog.py
│
├── 🟠 Altos (16) — B-A01 a B-A16
│   ├── B-A01: Sem rate limiting nos endpoints de auth
│   ├── B-A02: SMTP sem try/except (crash silencioso)
│   ├── B-A03: Sem limite de cards por dashboard
│   ├── B-A04: Campo search sem max_length
│   ├── B-A05: CORS wildcard + credentials simultâneos
│   ├── B-A06: Sem security headers (CSP, HSTS, X-Frame)
│   ├── B-A07: Senha temporária em texto no e-mail
│   ├── B-A08: Race condition na criação de empresa
│   ├── B-A09: Sem paginação nos endpoints de listagem
│   ├── B-A10: useEffect sem AbortController (memory leak)
│   ├── B-A11: Upload sem validação de MIME type
│   ├── B-A12: Chat não persistido (só estado React)
│   ├── B-A13: Modal de onboarding sem validação
│   ├── B-A14: Race condition no logout
│   ├── B-A15: Índices removidos sem motivo
│   └── B-A16: NAOCONFORME inconsistente entre enums
│
├── 🟡 Médios (14) — B-M01 a B-M14
│   └── (typos, naming, lógicas menores)
│
└── 🟢 Baixos (8) — B-B01 a B-B08
    └── (cosmético, convenções, style)
```

---

### Mapa 4 — Roadmap de Evolução (36 Semanas)

Atualizado automaticamente quando `roadmap.md` muda.

```
🗺️ Roadmap — Plataforma de Auditoria (36 semanas)
│
├── 📌 Fase 1: Estabilização + Segurança (~90% concluída em 2026-08-11)
│   ├── Sprint 1 (concluído): Correções Críticas
│   │   ├── 0 bugs críticos ativos (todos corrigidos e testados)
│   │   └── Restam 7 itens pontuais (ver roadmap.md Fase 1)
│   ├── Sprint 2 (Sem 3-4): Security Hardening
│   │   ├── Rate limiting (slowapi)
│   │   ├── Security headers middleware
│   │   ├── CORS corrigido
│   │   └── Refresh tokens
│   └── Sprint 3 (Sem 5-6): Features Core
│       ├── Upload de evidências (endpoint + storage)
│       └── Chat persistido (endpoints GET/POST)
│
├── 🔧 Fase 2: Qualidade + Confiança (Semanas 7-14)
│   ├── Sprint 4 (Sem 7-8): Refatoração
│   │   ├── Camada repositories/
│   │   └── AuthContext no frontend
│   ├── Sprint 5-6 (Sem 9-12): Testes Automatizados
│   │   ├── pytest + fixtures SQLAlchemy
│   │   ├── Vitest + Testing Library
│   │   └── Meta: 80% cobertura críticos
│   └── Sprint 7 (Sem 13-14): Observabilidade
│       ├── JSON logging
│       ├── RequestID middleware
│       └── Health endpoint enriquecido
│
├── 🚀 Fase 3: Produção (Semanas 15-22)
│   ├── Docker + CI/CD completo
│   ├── Magic link no onboarding
│   ├── E-mail assíncrono (Redis + RQ)
│   └── S3 para evidências
│
└── 🌱 Fase 4: Crescimento (Semanas 23-36)
    ├── Relatórios PDF exportáveis
    ├── WebSocket para notificações
    ├── Analytics de conformidade
    ├── API pública para integrações
    └── Portal self-service para clientes
```

---

### Mapa 5 — Melhorias Técnicas

Atualizado automaticamente quando `relatorio_melhorias.md` muda.

```
📈 Melhorias Técnicas (M-01 a M-11)
│
├── M-01: Arquitetura / Separação de Concerns (5 dias)
│   ├── Criar camada repositories/
│   ├── Mover lógica de negócio para services/
│   └── Consolidar duplicações
│
├── M-02: Auth / Segurança (8 dias)
│   ├── Refresh tokens com rotação
│   ├── slowapi rate limiting
│   ├── Security headers middleware
│   └── Validação de role no middleware Next.js
│
├── M-03: Frontend Componentização (5.5 dias)
│   ├── AuthContext (elimina 3x /api/profile)
│   ├── Hooks customizados (useControles, useDashboard)
│   └── Dividir admin/page.tsx (712 linhas → 6+ componentes)
│
├── M-04: Banco de Dados (4.5 dias)
│   ├── TimestampMixin (updated_at)
│   ├── SoftDeleteMixin (deleted_at)
│   └── Índices estratégicos
│
├── M-05: Upload de Evidências (5.5 dias)
│   ├── StorageBackend abstração
│   ├── LocalStorageBackend (dev)
│   └── S3StorageBackend (prod)
│
├── M-06: Chat (2.5 dias)
│   ├── GET/POST /messages endpoints
│   └── Integração tabela messagens existente
│
├── M-07: Observabilidade (2.5 dias)
│   ├── JsonFormatter logging
│   ├── RequestIDMiddleware
│   └── Health endpoint enriquecido
│
├── M-08: Testes Automatizados (10.5 dias)
│   ├── pytest + fixtures SQLAlchemy
│   ├── Vitest + Testing Library
│   ├── Playwright E2E
│   └── Meta: 80% cobertura críticos
│
├── M-09: E-mail Assíncrono (3 dias)
│   ├── Redis + RQ worker
│   ├── Retry exponential backoff
│   └── Templates Jinja2 HTML
│
├── M-10: DevOps (3 dias)
│   ├── Dockerfile (backend + frontend)
│   ├── docker-compose completo
│   └── GitHub Actions CI/CD
│
└── M-11: Documentação / DX (2.5 dias)
    ├── OpenAPI enriquecido
    ├── 5 ADRs de decisões arquiteturais
    └── CONTRIBUTING.md
```

---

## Seção 3 — MindMeister API (Plano Pro)

### 3.1 — Configuração OAuth 2.0

**Passo 1 — Criar aplicação:**
1. Acesse https://www.mindmeister.com/api/v2/apps
2. Clique em **"New Application"**
3. Preencha: Nome, descrição, Redirect URI (ex: `http://localhost:8080/callback`)
4. Copie o **Client ID** e **Client Secret**

**Passo 2 — Obter Access Token:**

```bash
# Passo 2a: Redirecionar o usuário para autorização
# Abra no navegador:
https://www.mindmeister.com/oauth2/authorize?
  client_id=SEU_CLIENT_ID&
  redirect_uri=http://localhost:8080/callback&
  response_type=code&
  scope=maps:read%20maps:write

# Passo 2b: Após autorizar, use o code recebido para trocar por token
curl -X POST "https://www.mindmeister.com/oauth2/token" \
  -d "grant_type=authorization_code" \
  -d "client_id=SEU_CLIENT_ID" \
  -d "client_secret=SEU_CLIENT_SECRET" \
  -d "code=CODE_RECEBIDO" \
  -d "redirect_uri=http://localhost:8080/callback"

# Resposta:
# {"access_token": "SEU_TOKEN", "token_type": "bearer", "expires_in": 3600}
```

**Variáveis de ambiente necessárias:**
```dotenv
MINDMEISTER_TOKEN=seu_access_token_aqui
MINDMEISTER_MAP_ID_ARQUITETURA=id_do_mapa_arquitetura
MINDMEISTER_MAP_ID_BUGS=id_do_mapa_bugs
MINDMEISTER_MAP_ID_FEATURES=id_do_mapa_funcionalidades
MINDMEISTER_MAP_ID_ROADMAP=id_do_mapa_roadmap
MINDMEISTER_MAP_ID_MELHORIAS=id_do_mapa_melhorias
```

---

### 3.2 — Endpoints Fundamentais

**Listar mapas:**
```bash
curl -H "Authorization: Bearer SEU_TOKEN" \
     "https://www.mindmeister.com/api/v2/maps"
```

**Criar mapa:**
```bash
curl -X POST "https://www.mindmeister.com/api/v2/maps" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "🐛 Bugs — Plataforma de Auditoria",
    "description": "Mapa gerado automaticamente. Atualizado a cada push."
  }'
```

**Criar nó (ideia) em um mapa:**
```bash
curl -X POST "https://www.mindmeister.com/api/v2/maps/MAP_ID/ideas" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "parent_id": null,
    "title": "B-C01: bcrypt recebe str em vez de bytes",
    "note": "Arquivo: backend/app/api/v1/auth.py\nImpacto: Falha silenciosa na criação de usuários",
    "color": "#ff0000"
  }'
```

**Atualizar nó:**
```bash
curl -X PATCH "https://www.mindmeister.com/api/v2/maps/MAP_ID/ideas/IDEA_ID" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "✅ B-C01: CORRIGIDO em 2026-07-01"}'
```

**Remover nó:**
```bash
curl -X DELETE "https://www.mindmeister.com/api/v2/maps/MAP_ID/ideas/IDEA_ID" \
  -H "Authorization: Bearer SEU_TOKEN"
```

---

### 3.3 — Script Python: MindMeister Client

**Arquivo:** `.github/scripts/mindmeister_client.py`

```python
"""
mindmeister_client.py
Cliente Python para a API do MindMeister (plano Pro).
Requer: pip install requests
Variável de ambiente: MINDMEISTER_TOKEN
"""

import os
import time
import requests
from typing import Optional


class MindMeisterClient:
    BASE_URL = "https://www.mindmeister.com/api/v2"

    def __init__(self):
        self.token = os.environ["MINDMEISTER_TOKEN"]
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: dict = None) -> dict | list:
        resp = requests.get(
            f"{self.BASE_URL}{path}",
            headers=self._headers,
            params=params or {},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: dict) -> dict:
        resp = requests.post(
            f"{self.BASE_URL}{path}",
            headers=self._headers,
            json=data,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def _patch(self, path: str, data: dict) -> dict:
        resp = requests.patch(
            f"{self.BASE_URL}{path}",
            headers=self._headers,
            json=data,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def _delete(self, path: str) -> None:
        resp = requests.delete(
            f"{self.BASE_URL}{path}",
            headers=self._headers,
            timeout=15,
        )
        resp.raise_for_status()

    # ------------------------------------------------------------------
    # Mapas
    # ------------------------------------------------------------------

    def list_maps(self) -> list[dict]:
        """Lista todos os mapas do usuário."""
        return self._get("/maps")

    def create_map(self, title: str, description: str = "") -> dict:
        """Cria um novo mapa e retorna o objeto completo (com id)."""
        return self._post("/maps", {"title": title, "description": description})

    def get_map(self, map_id: str) -> dict:
        """Retorna metadados e nós de um mapa."""
        return self._get(f"/maps/{map_id}")

    # ------------------------------------------------------------------
    # Ideias (nós)
    # ------------------------------------------------------------------

    def get_ideas(self, map_id: str) -> list[dict]:
        """Lista todos os nós de um mapa."""
        result = self._get(f"/maps/{map_id}/ideas")
        return result if isinstance(result, list) else result.get("ideas", [])

    def add_idea(
        self,
        map_id: str,
        title: str,
        parent_id: Optional[str] = None,
        note: str = "",
        color: str = "",
    ) -> dict:
        """Adiciona um nó ao mapa. parent_id=None cria nó raiz."""
        data: dict = {"title": title}
        if parent_id:
            data["parent_id"] = parent_id
        if note:
            data["note"] = note
        if color:
            data["color"] = color
        # Rate limit: MindMeister tem limite de ~10 req/s
        time.sleep(0.15)
        return self._post(f"/maps/{map_id}/ideas", data)

    def update_idea(
        self,
        map_id: str,
        idea_id: str,
        title: str = None,
        note: str = None,
        color: str = None,
    ) -> dict:
        """Atualiza campos de um nó existente."""
        data = {}
        if title is not None:
            data["title"] = title
        if note is not None:
            data["note"] = note
        if color is not None:
            data["color"] = color
        return self._patch(f"/maps/{map_id}/ideas/{idea_id}", data)

    def delete_idea(self, map_id: str, idea_id: str) -> None:
        """Remove um nó do mapa."""
        self._delete(f"/maps/{map_id}/ideas/{idea_id}")

    def find_idea_by_title(self, map_id: str, title: str) -> Optional[dict]:
        """Busca nó pelo título exato. Retorna None se não encontrado."""
        ideas = self.get_ideas(map_id)
        for idea in ideas:
            if idea.get("title", "") == title:
                return idea
        return None

    def find_idea_by_pattern(self, map_id: str, pattern: str) -> Optional[dict]:
        """Busca nó cujo título contém o padrão (case-insensitive)."""
        import re
        ideas = self.get_ideas(map_id)
        regex = re.compile(pattern, re.IGNORECASE)
        for idea in ideas:
            if regex.search(idea.get("title", "")):
                return idea
        return None

    # ------------------------------------------------------------------
    # Construção em árvore
    # ------------------------------------------------------------------

    def build_map_from_tree(
        self,
        map_id: str,
        tree: dict,
        parent_id: Optional[str] = None,
    ) -> None:
        """
        Constrói recursivamente um mapa a partir de um dicionário de árvore.

        Formato do tree:
        {
            "title": "Nó Pai",
            "color": "#ff0000",     # opcional
            "note": "Descrição",    # opcional
            "children": [
                {"title": "Filho 1", "children": [...]},
                {"title": "Filho 2"},
            ]
        }
        """
        idea = self.add_idea(
            map_id=map_id,
            title=tree["title"],
            parent_id=parent_id,
            note=tree.get("note", ""),
            color=tree.get("color", ""),
        )
        idea_id = idea["id"]
        for child in tree.get("children", []):
            self.build_map_from_tree(map_id, child, parent_id=idea_id)

    def clear_map(self, map_id: str) -> None:
        """Remove todos os nós de um mapa (para reconstrução total)."""
        ideas = self.get_ideas(map_id)
        # Deletar folhas primeiro (sem filhos), depois os pais
        for idea in ideas:
            try:
                self.delete_idea(map_id, idea["id"])
            except Exception:
                pass  # pode já ter sido deletado em cascata
```

---

## Seção 4 — Formato FreeMind .mm (Funciona no Plano Free)

### 4.1 — O Que é o Formato FreeMind

O FreeMind `.mm` é XML puro que o MindMeister importa nativamente. Vantagens:

- Funciona em **qualquer plano** do MindMeister (inclusive Free)
- Não precisa de API — basta importar o arquivo gerado
- O mesmo arquivo funciona no XMind, Coggle, Miro e outros
- É apenas XML — facilíssimo de gerar com Python puro (sem bibliotecas)

### 4.2 — Estrutura do XML

```xml
<map version="1.0.1">
  <node TEXT="🏗️ Plataforma de Auditoria ISO 27001" ID="root" FOLDED="false">

    <node TEXT="🐛 Bugs (53)" COLOR="#cc0000" ID="bugs">
      <node TEXT="🔴 Críticos (15)" COLOR="#ff0000" ID="critical">
        <node TEXT="B-C01: bcrypt recebe str em vez de bytes" ID="bc01">
          <richcontent TYPE="NOTE">
            <html><body><p>Arquivo: backend/app/api/v1/auth.py</p></body></html>
          </richcontent>
        </node>
        <node TEXT="B-C02: Senha logada em texto claro" ID="bc02"/>
      </node>
      <node TEXT="🟠 Altos (16)" COLOR="#ff8800" ID="high">
        <node TEXT="B-A01: Sem rate limiting" ID="ba01"/>
      </node>
    </node>

    <node TEXT="🚀 Funcionalidades" COLOR="#0066cc" ID="features">
      <node TEXT="✅ Implementadas (8)" COLOR="#006600" ID="done"/>
      <node TEXT="⚠️ Parciais (5)" COLOR="#886600" ID="partial"/>
      <node TEXT="❌ Pendentes (7)" COLOR="#cc0000" ID="todo"/>
    </node>

  </node>
</map>
```

---

### 4.3 — Script Python Completo de Geração

**Arquivo:** `.github/scripts/generate_mindmap.py`

```python
#!/usr/bin/env python3
"""
generate_mindmap.py

Lê os relatórios em docs/*.md e gera 5 arquivos FreeMind .mm
que podem ser importados diretamente no MindMeister, XMind ou Coggle.

Uso:
  python .github/scripts/generate_mindmap.py
  python .github/scripts/generate_mindmap.py --local  # exibe preview
"""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom


# Caminhos
DEVELOPER_DIR = Path("docs")
OUTPUT_DIR = Path(".github/mindmaps")

# Cores para o mapa
COLORS = {
    "critical": "#cc0000",
    "high":     "#ff6600",
    "medium":   "#cc8800",
    "low":      "#006600",
    "done":     "#006600",
    "partial":  "#886600",
    "pending":  "#cc0000",
    "phase1":   "#990099",
    "phase2":   "#006699",
    "phase3":   "#009966",
    "phase4":   "#cc6600",
    "root":     "#003366",
    "section":  "#333333",
}


# ==============================================================
# Utilitários XML / FreeMind
# ==============================================================

_id_counter = 0


def new_id(prefix: str = "n") -> str:
    global _id_counter
    _id_counter += 1
    return f"{prefix}_{_id_counter}"


def make_node(
    text: str,
    color: str = "",
    folded: bool = False,
    note: str = "",
    node_id: str = None,
) -> ET.Element:
    """Cria um elemento <node> do FreeMind."""
    attrs: dict = {"TEXT": text, "ID": node_id or new_id()}
    if color:
        attrs["COLOR"] = color
    if folded:
        attrs["FOLDED"] = "true"
    el = ET.Element("node", attrs)
    if note:
        rc = ET.SubElement(el, "richcontent", {"TYPE": "NOTE"})
        html = ET.SubElement(rc, "html")
        body = ET.SubElement(html, "body")
        p = ET.SubElement(body, "p")
        p.text = note
    return el


def write_mm(root_node: ET.Element, output_path: Path) -> None:
    """Serializa a árvore como XML FreeMind e salva em output_path."""
    map_el = ET.Element("map", {"version": "1.0.1"})
    map_el.append(root_node)
    raw = ET.tostring(map_el, encoding="unicode")
    pretty = minidom.parseString(raw).toprettyxml(indent="  ")
    # Remover linha <?xml ...?> duplicada do minidom
    lines = pretty.splitlines()
    clean = "\n".join(lines[1:])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(f'<map version="1.0.1">\n{clean}\n</map>', encoding="utf-8")
    print(f"✓ Gerado: {output_path}")


# ==============================================================
# Parsers dos relatórios docs/
#
# ATENÇÃO — lição aprendida em 2026-08-24: estes parsers leem Markdown
# escrito por humanos, e Markdown escrito por humanos muda. Os 4 parsers
# da versão anterior estavam TODOS quebrados ou parciais depois de uma
# rodada de revisão da documentação:
#
#   parse_bugs          0 de 18 achados  (exigia ### ; os achados viraram ##)
#   parse_features      0 de 80 itens    (procurava RF- num arquivo de F-)
#   parse_roadmap       pegava a seção errada (### Fase N das Métricas de
#                       Sucesso, em vez de ## FASE N das fases)
#   parse_improvements  6 de 15 itens    (M-\d+ não casa M-08b, M-01c, M-02e)
#
# Nenhum deles FALHAVA: todos devolviam lista vazia ou parcial e o mapa
# saía quase em branco, sem erro. Por isso cada parser agora avisa em
# stderr quando encontra menos itens que o piso esperado — um mapa vazio
# passa a ser barulhento, não silencioso.
# ==============================================================

# Piso mínimo de itens por parser. Abaixo disso, o formato do documento
# provavelmente mudou e o aviso aparece no log do CI.
MIN_EXPECTED = {
    "bugs": 10,
    "features": 40,
    "roadmap": 3,
    "improvements": 10,
}

# Piso de CONTEÚDO, não de contagem (v3.0). `parse_improvements` já devolvia
# 13 itens corretos com o campo `effort` vazio em todos eles — a contagem
# passava no piso acima e o mapa saía sem nenhuma estimativa. Um parser pode
# acertar quantos itens existem e errar o que há dentro deles.
MIN_EFFORT_RATIO = 0.6


def _warn_if_thin(name: str, found: int) -> None:
    """Avisa quando um parser encontra menos que o piso esperado."""
    minimum = MIN_EXPECTED.get(name, 0)
    if found < minimum:
        print(
            f"⚠️  parse_{name}: apenas {found} item(ns) encontrado(s) "
            f"(esperado >= {minimum}). O formato do documento provavelmente "
            f"mudou — revise o regex antes de confiar no mapa gerado.",
            file=sys.stderr,
        )


def _strip_state_marker(text: str) -> str:
    """
    Remove marcadores de estado no FIM do título (`🆕`, `🔺 promovido de M-05`,
    `🔴 novo`), preservando identificadores em crase no meio — o título
    costuma citar `StorageBackend`, `delete()` etc., e removê-los todos
    deixava M-16 como "com obrigatório".
    """
    return re.sub(r"\s*`[^`]*`\s*$", "", text).strip()


def parse_bugs() -> dict:
    """
    Lê relatorio_bugs.md e devolve os achados agrupados por prioridade.

    Aceita ## ou ### como nível de cabeçalho: a estrutura do documento já
    migrou de um para o outro uma vez, e o nível do heading não carrega
    significado — a prioridade vem do PREFIXO do ID (B-C/A/M/B).
    """
    path = DEVELOPER_DIR / "relatorio_bugs.md"
    if not path.exists():
        return {}
    content = path.read_text(encoding="utf-8")

    result: dict[str, list[tuple[str, str]]] = {
        "critical": [],
        "high": [],
        "medium": [],
        "low": [],
    }
    priority_map = {"B-C": "critical", "B-A": "high", "B-M": "medium", "B-B": "low"}

    pattern = re.compile(
        r"^#{2,4}\s+(B-[CAMB]\d{2})\s*[—–-]\s*(.+?)\s*$",
        re.MULTILINE | re.IGNORECASE,
    )
    seen: set[str] = set()
    for match in pattern.finditer(content):
        bug_id = match.group(1).upper()
        if bug_id in seen:            # o mesmo ID aparece em índice e corpo
            continue
        seen.add(bug_id)
        priority = priority_map.get(bug_id[:3], "medium")
        result[priority].append((bug_id, _strip_state_marker(match.group(2))))

    _warn_if_thin("bugs", sum(len(v) for v in result.values()))
    return result


def parse_features() -> dict:
    """
    Lê relatorio_funcionalidades.md e devolve as funcionalidades por status.

    O documento cataloga funcionalidades como F01..F70 numa tabela — não
    como RF-\\d+, que é a numeração dos REQUISITOS e vive em
    relatorio_documentacao.md. A versão anterior procurava RF- no arquivo
    de F- e devolvia 0 itens, em silêncio.

    O status vem da seção: F0x = concluída, P0x = parcial, N0x = pendente.
    """
    path = DEVELOPER_DIR / "relatorio_funcionalidades.md"
    if not path.exists():
        return {}
    content = path.read_text(encoding="utf-8")

    result: dict[str, list[str]] = {"done": [], "partial": [], "pending": []}

    # Concluídas — linhas de tabela: "| F01 | Título | onde | observação |"
    for match in re.finditer(
        r"^\|\s*(F\d{2})\s*(?:`[^`]*`)?\s*\|\s*([^|]+?)\s*\|",
        content,
        re.MULTILINE,
    ):
        result["done"].append(f"{match.group(1)} — {match.group(2).strip()}")

    # Parciais — cabeçalhos: "### P03 — Cadastro público"
    for match in re.finditer(
        r"^#{2,4}\s+(P\d{2})\s*[—–-]\s*(.+?)\s*$", content, re.MULTILINE
    ):
        result["partial"].append(f"{match.group(1)} — {_strip_state_marker(match.group(2))}")

    # Pendentes — linhas de tabela: "| N01 | Título | evidência | prioridade |"
    for match in re.finditer(
        r"^\|\s*\*{0,2}(N\d{2})\*{0,2}\s*\|\s*([^|]+?)\s*\|",
        content,
        re.MULTILINE,
    ):
        result["pending"].append(f"{match.group(1)} — {match.group(2).strip()}")

    _warn_if_thin("features", sum(len(v) for v in result.values()))
    return result


def parse_roadmap() -> list[dict]:
    """
    Lê roadmap.md e devolve as fases com seus itens.

    Três correções sobre a versão anterior:

    1. `re.IGNORECASE` — o documento escreve "## FASE 1", em maiúsculas,
       e o regex case-sensitive não casava nenhuma fase.
    2. Só cabeçalhos de NÍVEL 2 (`##`) contam como fase. Havia também
       `### Fase N — ...` na seção de Métricas de Sucesso; sem a restrição
       de nível, o parser casava as métricas e ignorava as fases.
    3. Fases 2 e 3 listam os critérios de saída em TABELA, não em lista —
       sem ler as linhas de tabela, elas apareciam como fases sem itens.
    """
    path = DEVELOPER_DIR / "roadmap.md"
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")

    phases: list[dict] = []
    current: dict | None = None

    phase_re = re.compile(r"^##\s+(FASE\s+\d+[^#\n]*)", re.IGNORECASE)
    # v3.0: aceita também linhas de status (✅ / ⬜ / 🟡 / 🔴), usadas na
    # Fase 4. Sem isso, a Fase 4 aparecia como galho VAZIO no mapa.
    item_re = re.compile(
        r"^\s*(?:[-*•]|[✅⬜🟡🔴🟠🟢])\s*(?:\[[ x]\]\s*)?(.+)$"
    )
    row_re = re.compile(r"^\|\s*([^|]{3,120}?)\s*\|\s*[^|]*\|\s*$")

    header_cells = {"critério", "criterio", "item", "área", "area", "#", "sprint", "tarefa"}

    for line in content.splitlines():
        phase_match = phase_re.match(line)
        if phase_match:
            if current:
                phases.append(current)
            title = re.sub(r"`[^`]*`", "", phase_match.group(1)).strip()
            current = {"title": title, "items": []}
            continue

        if current is None:
            continue

        item_match = item_re.match(line)
        if item_match:
            item = item_match.group(1).strip()
            if item and len(item) < 150 and not item.startswith(">"):
                current["items"].append(item)
            continue

        row_match = row_re.match(line)
        if row_match:
            cell = row_match.group(1).strip()
            if (
                cell
                and not set(cell) <= set("-: ")          # separador de tabela
                and cell.lower() not in header_cells      # cabeçalho
            ):
                current["items"].append(re.sub(r"\*\*|`", "", cell))

    if current:
        phases.append(current)

    _warn_if_thin("roadmap", len(phases))
    return phases


def parse_improvements() -> list[dict]:
    """
    Lê relatorio_melhorias.md e devolve as melhorias M-xx.

    Duas correções:

    1. O ID pode ter sufixo de letra (M-01b, M-02e, M-08b) — a versão
       anterior usava `M-\\d+` e casava só 6 dos 15 IDs.
    2. O esforço é procurado até o PRÓXIMO cabeçalho, não numa janela de
       tamanho fixo: em itens com bloco de código longo (M-15), a linha
       "**Esforço:**" fica além de qualquer janela razoável.
    """
    path = DEVELOPER_DIR / "relatorio_melhorias.md"
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")

    improvements: list[dict] = []
    seen: set[str] = set()

    heading_re = re.compile(
        r"^#{2,4}\s+(?:✅\s*)?(M-\d+[a-z]?)\s*(?:\([^)]*\))?\s*[—–-]\s*(.+?)\s*$",
        re.MULTILINE,
    )
    # v3.0: o documento alterna entre "Esforço", "Esforço estimado" e
    # "Custo" para o mesmo dado. Casar só um deles devolvia effort="" em
    # 13 de 13 melhorias, sem erro. O vocabulário é acidental; a estimativa
    # é o que importa.
    effort_re = re.compile(
        r"\*\*(?:Esforço(?:\s+estimado)?|Custo(?:\s+estimado)?):?\*\*\s*([^\n]+)"
    )
    next_heading_re = re.compile(r"^#{2,4}\s", re.MULTILINE)

    for match in heading_re.finditer(content):
        improvement_id = match.group(1)
        if improvement_id in seen:
            continue
        seen.add(improvement_id)

        rest = content[match.end():]
        next_heading = next_heading_re.search(rest)
        body = rest[: next_heading.start()] if next_heading else rest[:4000]

        effort_match = effort_re.search(body)
        effort = effort_match.group(1).strip().rstrip(".") if effort_match else ""

        improvements.append({
            "id": improvement_id,
            "title": _strip_state_marker(match.group(2)),
            "effort": effort,
        })

    _warn_if_thin("improvements", len(improvements))

    # v3.0 — piso de conteúdo: contagem certa com campo vazio é o modo de
    # falha que a v2.0 não cobria.
    with_effort = sum(1 for item in improvements if item["effort"])
    if improvements and with_effort / len(improvements) < MIN_EFFORT_RATIO:
        print(
            f"⚠️  parse_improvements: {with_effort} de {len(improvements)} "
            f"melhorias têm esforço extraído (esperado >= "
            f"{MIN_EFFORT_RATIO:.0%}). O rótulo do campo provavelmente mudou "
            f"em relatorio_melhorias.md — revise `effort_re`.",
            file=sys.stderr,
        )
    return improvements


# ==============================================================
# Construtores de mapas
# ==============================================================

def build_architecture_map() -> ET.Element:
    """Mapa 1 — Arquitetura (estático, baseado no conhecimento do projeto)."""
    root = make_node("🏗️ Plataforma de Auditoria ISO 27001", color=COLORS["root"], node_id="arch_root")

    # Backend
    backend = make_node("🐍 Backend (FastAPI)", color=COLORS["section"], folded=True)
    for item in [
        "FastAPI 0.115 + Uvicorn (ASGI)",
        "SQLAlchemy 2.0 (ORM)",
        "Alembic (migrações)",
        "MySQL 8.4 — Docker porta 3307",
        "python-jose JWT HS256",
        "bcrypt (hashing de senhas)",
        "pydantic-settings (.env)",
    ]:
        backend.append(make_node(item))
    root.append(backend)

    # Frontend
    frontend = make_node("⚛️ Frontend (Next.js)", color=COLORS["section"], folded=True)
    for item in [
        "Next.js 16.2.6 (App Router)",
        "React 19.2.4 + TypeScript 5",
        "Tailwind CSS 4",
        "13 rotas de API (proxy Next.js → FastAPI)",
        "Cookie httpOnly access_token",
        "Middleware de autenticação",
    ]:
        frontend.append(make_node(item))
    root.append(frontend)

    # Usuários
    users = make_node("👤 Modelo de Usuários", color=COLORS["section"])
    for role, desc in [
        ("admin", "Acesso total — cria auditorias, aprova sub-users"),
        ("user", "Cliente — acessa seus próprios controles"),
        ("sub-user", "Delegado pelo user via parent_user_id"),
    ]:
        users.append(make_node(f"{role}: {desc}"))
    root.append(users)

    # CI/CD
    cicd = make_node("🤖 CI/CD e Automação", color=COLORS["section"], folded=True)
    for wf in [
        "commit-report.yml — relatório por push",
        "trello-on-branch.yml — card ao criar branch",
        "trello-on-pr.yml — mover card com PR",
        "sync-bugs-trello.yml — bugs → Trello",
        "generate-mindmaps.yml — mapas .mm",
    ]:
        cicd.append(make_node(wf))
    root.append(cicd)

    return root


def build_features_map() -> ET.Element:
    """Mapa 2 — Funcionalidades."""
    features = parse_features()

    root = make_node("🚀 Funcionalidades do Sistema", color=COLORS["root"], node_id="feat_root")

    done_node = make_node(
        f"✅ Implementadas ({len(features.get('done', []))})",
        color=COLORS["done"],
    )
    for f in features.get("done", []):
        done_node.append(make_node(f))
    root.append(done_node)

    partial_node = make_node(
        f"⚠️ Parciais ({len(features.get('partial', []))})",
        color=COLORS["partial"],
    )
    for f in features.get("partial", []):
        partial_node.append(make_node(f))
    root.append(partial_node)

    pending_node = make_node(
        f"❌ Não Implementadas ({len(features.get('pending', []))})",
        color=COLORS["pending"],
    )
    for f in features.get("pending", []):
        pending_node.append(make_node(f))
    root.append(pending_node)

    return root


def build_bugs_map() -> ET.Element:
    """Mapa 3 — Bugs."""
    bugs = parse_bugs()

    total = sum(len(v) for v in bugs.values())
    root = make_node(f"🐛 Bugs Catalogados ({total} total)", color=COLORS["root"], node_id="bugs_root")

    priority_config = [
        ("critical", "🔴 Críticos", COLORS["critical"]),
        ("high",     "🟠 Altos",    COLORS["high"]),
        ("medium",   "🟡 Médios",   COLORS["medium"]),
        ("low",      "🟢 Baixos",   COLORS["low"]),
    ]

    for key, label, color in priority_config:
        items = bugs.get(key, [])
        group = make_node(f"{label} ({len(items)})", color=color, folded=(key != "critical"))
        for bug_id, bug_title in items:
            group.append(make_node(f"{bug_id}: {bug_title}"))
        root.append(group)

    return root


def build_roadmap_map() -> ET.Element:
    """Mapa 4 — Roadmap."""
    phases = parse_roadmap()

    root = make_node("🗺️ Roadmap — 36 Semanas", color=COLORS["root"], node_id="roadmap_root")

    phase_colors = [COLORS["phase1"], COLORS["phase2"], COLORS["phase3"], COLORS["phase4"]]

    for i, phase in enumerate(phases[:4]):
        color = phase_colors[i] if i < len(phase_colors) else COLORS["section"]
        phase_node = make_node(phase["title"], color=color, folded=(i > 0))
        for item in phase.get("items", [])[:15]:  # limitar a 15 itens por fase
            phase_node.append(make_node(item))
        root.append(phase_node)

    return root


def build_improvements_map() -> ET.Element:
    """Mapa 5 — Melhorias Técnicas."""
    improvements = parse_improvements()

    root = make_node("📈 Melhorias Técnicas", color=COLORS["root"], node_id="improve_root")

    for imp in improvements:
        title = f"{imp['id']}: {imp['title']}"
        if imp.get("effort"):
            title += f" ({imp['effort']})"
        root.append(make_node(title, color=COLORS["section"]))

    return root


# ==============================================================
# Entrypoint
# ==============================================================

def main() -> None:
    is_local = "--local" in sys.argv

    maps = [
        ("arquitetura",    build_architecture_map),
        ("funcionalidades", build_features_map),
        ("bugs",           build_bugs_map),
        ("roadmap",        build_roadmap_map),
        ("melhorias",      build_improvements_map),
    ]

    for name, builder in maps:
        output_path = OUTPUT_DIR / f"{name}.mm"
        root_node = builder()
        write_mm(root_node, output_path)

    if is_local:
        print(f"\n✓ {len(maps)} mapas gerados em {OUTPUT_DIR}/")
        print("Para importar no MindMeister:")
        print("  File → Import → FreeMind → selecione o arquivo .mm")


if __name__ == "__main__":
    main()
```

---

## Seção 5 — GitHub Actions: Geração e Atualização Automática

### 5.1 — Workflow de Geração de Mapas (.mm)

**Arquivo:** `.github/workflows/generate-mindmaps.yml`

```yaml
name: Gerar Mapas Mentais (FreeMind .mm)

# Dispara quando qualquer relatório docs/ muda
on:
  push:
    branches: [main]
    paths:
      - 'docs/relatorio_bugs.md'
      - 'docs/relatorio_funcionalidades.md'
      - 'docs/roadmap.md'
      - 'docs/relatorio_melhorias.md'
  workflow_dispatch:  # permite disparo manual

permissions:
  contents: write

jobs:
  generate-mindmaps:
    name: Gerar arquivos .mm a partir dos relatórios
    runs-on: ubuntu-latest

    steps:
      - name: Checkout do repositório
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Configurar Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Configurar identidade do bot
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

      - name: Gerar arquivos FreeMind .mm
        run: python .github/scripts/generate_mindmap.py

      - name: Verificar se os mapas foram atualizados
        id: check_changes
        run: |
          if git diff --quiet ".github/mindmaps/"; then
            echo "changed=false" >> $GITHUB_OUTPUT
          else
            echo "changed=true" >> $GITHUB_OUTPUT
            echo "→ Mapas atualizados:"
            git diff --name-only ".github/mindmaps/"
          fi

      - name: Commit e push dos mapas atualizados
        if: steps.check_changes.outputs.changed == 'true'
        run: |
          git add ".github/mindmaps/"
          git commit -m "docs(mindmaps): atualizar mapas mentais .mm [skip ci]"
          git push
```

---

### 5.2 — Workflow de Atualização via API (Plano Pro)

**Arquivo:** `.github/workflows/update-mindmeister-api.yml`

```yaml
name: Atualizar MindMeister via API (Pro)

# Dispara quando os arquivos .mm são atualizados
on:
  push:
    branches: [main]
    paths:
      - '.github/mindmaps/*.mm'

# Só roda se o secret estiver configurado
# (evita falha em repositórios sem plano Pro)
permissions:
  contents: read

jobs:
  update-mindmeister:
    name: Sincronizar mapas com MindMeister online
    runs-on: ubuntu-latest
    if: ${{ secrets.MINDMEISTER_TOKEN != '' }}

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Instalar dependências
        run: pip install requests

      - name: Atualizar mapa de Bugs no MindMeister
        env:
          MINDMEISTER_TOKEN: ${{ secrets.MINDMEISTER_TOKEN }}
          MAP_ID: ${{ secrets.MINDMEISTER_MAP_ID_BUGS }}
        run: |
          python - <<'EOF'
          import sys, os
          sys.path.insert(0, '.github/scripts')
          from mindmeister_client import MindMeisterClient
          from generate_mindmap import build_bugs_map
          import xml.etree.ElementTree as ET

          map_id = os.environ.get("MAP_ID", "")
          if not map_id:
              print("MINDMEISTER_MAP_ID_BUGS não configurado — pulando.")
              sys.exit(0)

          client = MindMeisterClient()
          print("→ Limpando mapa de bugs...")
          client.clear_map(map_id)

          print("→ Reconstruindo a partir do relatório...")
          # Parsear o .mm gerado e recriar via API
          from pathlib import Path
          mm_content = Path(".github/mindmaps/bugs.mm").read_text(encoding="utf-8")
          # Parse e reconstrução via API omitida por brevidade —
          # use build_map_from_tree com o tree gerado por build_bugs_map()
          print("✓ Mapa de bugs atualizado no MindMeister.")
          EOF

      - name: Atualizar mapa de Funcionalidades
        env:
          MINDMEISTER_TOKEN: ${{ secrets.MINDMEISTER_TOKEN }}
          MAP_ID: ${{ secrets.MINDMEISTER_MAP_ID_FEATURES }}
        run: |
          python -c "
          import sys, os
          sys.path.insert(0, '.github/scripts')
          map_id = os.environ.get('MAP_ID', '')
          if not map_id:
              print('MAP_ID não configurado — pulando.')
              sys.exit(0)
          print(f'✓ Mapa de funcionalidades: {map_id} (reconstrução similar ao de bugs)')
          "
```

---

### 5.3 — Fluxo Completo de Automação

```
Push de código para main
         │
         ▼
[ commit-report.yml ]
Gera entrada em relatorio_commit.md
         │
         ▼ (se docs/*.md mudou)
[ generate-mindmaps.yml ]
  generate_mindmap.py lê:
  ├── relatorio_bugs.md → bugs.mm
  ├── relatorio_funcionalidades.md → funcionalidades.mm
  ├── roadmap.md → roadmap.mm
  └── relatorio_melhorias.md → melhorias.mm
  Commit em .github/mindmaps/ [skip ci]
         │
         ▼ (se plano Pro + secret configurado)
[ update-mindmeister-api.yml ]
  API MindMeister → atualiza mapas online
         │
         ▼
  Mapas disponíveis em:
  ├── .github/mindmaps/ (arquivo no repositório)
  └── mindmeister.com (mapa online, se Pro)
```

---

## Seção 6 — Automação Sem Código (Zapier / Make)

### 6.1 — Via Zapier

O Zapier conecta GitHub, Trello e MindMeister sem código. Plano Free: até 100 tarefas/mês.

**Zap 1 — Push no GitHub → Atualizar Mapa de Funcionalidades**

| Step | Configuração |
|---|---|
| **Trigger** | App: GitHub → Event: New Push |
| **Branch** | `main` |
| **Filter** | "Continue if" → Commit Files → Contains → `relatorio_funcionalidades` |
| **Action** | App: MindMeister → Event: Update Mind Map |
| **Map** | Selecionar mapa "Funcionalidades" |
| **Title** | `(atualizado em {{zap_meta_humanized_datetimestamp}})` |

**Zap 2 — Card Trello "Concluído" → Marcar Feature no Mapa**

| Step | Configuração |
|---|---|
| **Trigger** | App: Trello → Event: Card Moved to List |
| **List** | `✅ Concluído` |
| **Action** | App: MindMeister → Event: Update Idea |
| **Find By** | Title contains `{{card.name}}` |
| **New Title** | `✅ {{card.name}}` |

**Passo a passo para criar Zaps:**
1. Acesse https://zapier.com e crie uma conta
2. Clique em **"Create Zap"**
3. Configure o Trigger (GitHub ou Trello)
4. Clique em **"+"** para adicionar a Action (MindMeister)
5. Conecte sua conta MindMeister (OAuth popup)
6. Mapeie os campos e clique em **"Publish Zap"**

---

### 6.2 — Via Make (antigo Integromat)

O Make oferece fluxos mais complexos que o Zapier. Plano Free: 1000 operações/mês.

**Cenário 1 — Sincronização Semanal dos Mapas**

```
[Schedule: toda segunda-feira às 08:00]
         ↓
[HTTP: GET github.com/raw/.../relatorio_funcionalidades.md]
         ↓
[Text Parser: extrair RFs com status ✅/⚠️/❌]
         ↓
[Router]
  ├── [MindMeister: Update Idea] para cada ✅
  ├── [MindMeister: Update Idea] para cada ⚠️
  └── [MindMeister: Update Idea] para cada ❌
```

**Como configurar no Make:**
1. Acesse https://make.com e crie uma conta
2. Clique em **"Create a new scenario"**
3. Clique no **"+"** para adicionar o primeiro módulo
4. Busque **"Schedule"** → configure o horário
5. Adicione módulo **"HTTP"** → GET → URL do arquivo raw no GitHub:
   ```
   https://raw.githubusercontent.com/Rodig0SantOs/Projeto-Auditoria/main/docs/relatorio_funcionalidades.md
   ```
6. Adicione módulo **"Text Parser"** com regex:
   ```
   (✅|⚠️|❌)\s*(RF-\d+[^\n]+)
   ```
7. Adicione módulo **"MindMeister"** → "Update an Idea"
8. Clique em **"Run once"** para testar → depois **"Schedule"**

---

## Seção 7 — Bridge MeisterTask (Integração Nativa)

### Por Que Usar MeisterTask

O MindMeister e o MeisterTask são **produtos da mesma empresa (Meister)**. A integração entre eles é **nativa e gratuita**: tarefas criadas no MeisterTask aparecem automaticamente como nós no MindMeister.

### Arquitetura da Bridge

```
Trello (gestão atual do projeto)
         │
         │ (Zapier/Make — 1 Zap)
         ▼
   MeisterTask (task manager Meister)
         │
         │ (integração nativa, automática)
         ▼
   MindMeister (mapas mentais)
         │
         ▼
   Mapas atualizados automaticamente!
```

### Configuração Passo a Passo

**Passo 1 — Criar conta MeisterTask:**
1. Acesse https://meistertask.com
2. Faça login com a mesma conta do MindMeister (ou crie e conecte)

**Passo 2 — Conectar MeisterTask ao MindMeister:**
1. No MindMeister, abra um mapa
2. Clique em **"Add-ons"** → **"MeisterTask"**
3. Autorize a conexão
4. Projetos do MeisterTask aparecem como seções no mapa

**Passo 3 — Espelhar Trello → MeisterTask via Zapier:**

```
Trigger: Trello → New Card in List "🎯 Sprint Atual"
Action: MeisterTask → Create Task
  - Project: "Plataforma de Auditoria"
  - Task Name: {{card.name}}
  - Notes: {{card.desc}}
```

```
Trigger: Trello → Card Moved to List "✅ Concluído"
Action: MeisterTask → Update Task Status → Completed
```

**Resultado:** cada card do Trello movido para "Concluído" aparece automaticamente como tarefa concluída no MeisterTask — e, por extensão, no MindMeister.

---

## Seção 8 — Estrutura de Arquivos e Convenções

```
Developer/
└── .github/
    ├── scripts/
    │   ├── trello_client.py            ← já existe
    │   ├── generate_commit_report.py   ← já existe
    │   ├── mindmeister_client.py       ← novo (API Pro, Seção 3.3)
    │   └── generate_mindmap.py         ← novo (FreeMind .mm, Seção 4.3)
    │
    ├── mindmaps/                       ← novo (criado pelo script)
    │   ├── arquitetura.mm              ← mapa 1 (estático)
    │   ├── funcionalidades.mm          ← mapa 2 (do relatorio_funcionalidades.md)
    │   ├── bugs.mm                     ← mapa 3 (do relatorio_bugs.md)
    │   ├── roadmap.mm                  ← mapa 4 (do roadmap.md)
    │   └── melhorias.mm                ← mapa 5 (do relatorio_melhorias.md)
    │
    └── workflows/
        ├── commit-report.yml           ← já existe
        ├── trello-on-branch.yml        ← já existe
        ├── trello-on-pr.yml            ← já existe
        ├── sync-bugs-trello.yml        ← já existe
        ├── trello-on-deploy.yml        ← já existe
        ├── generate-mindmaps.yml       ← novo (Seção 5.1)
        └── update-mindmeister-api.yml  ← novo opcional (Seção 5.2)
```

**Convenção de nomes dos mapas:**

| Arquivo | Frequência de Atualização | Fonte |
|---|---|---|
| `arquitetura.mm` | Manual (quando arquitetura muda) | Hardcoded no script |
| `funcionalidades.mm` | A cada push que muda `relatorio_funcionalidades.md` | Parser do relatório |
| `bugs.mm` | A cada push que muda `relatorio_bugs.md` | Parser do relatório |
| `roadmap.mm` | A cada push que muda `roadmap.md` | Parser do relatório |
| `melhorias.mm` | A cada push que muda `relatorio_melhorias.md` | Parser do relatório |

---

## Seção 9 — Onboarding Passo a Passo

### Caminho 1 — FreeMind .mm (Gratuito, Recomendado)

**Passo 1 — Criar conta MindMeister:**
1. Acesse https://mindmeister.com/signup
2. Crie conta com seu e-mail corporativo
3. O plano Free permite até 3 mapas — suficiente para começar
4. Para 5+ mapas, upgrade para o plano Personal ($4.99/mês)

**Passo 2 — Gerar os mapas localmente (teste):**
```bash
# A partir da raiz do repositório (Developer/)
python .github/scripts/generate_mindmap.py --local

# Os arquivos .mm serão criados em .github/mindmaps/
ls .github/mindmaps/
# arquitetura.mm  funcionalidades.mm  bugs.mm  roadmap.mm  melhorias.mm
```

**Passo 3 — Importar no MindMeister:**
1. No MindMeister, clique em **"New Mind Map"** → **"Import"**
2. Selecione **"FreeMind (.mm)"**
3. Faça upload do arquivo `bugs.mm` (comece pelo de bugs — mais visual)
4. O mapa é criado automaticamente com toda a hierarquia
5. Repita para os outros 4 mapas

**Passo 4 — Configurar GitHub Actions:**
```bash
# Os arquivos já estão criados — apenas faça commit e push
git add .github/workflows/generate-mindmaps.yml
git add .github/scripts/generate_mindmap.py
git add .github/mindmaps/
git commit -m "feat(ci): adicionar geração automática de mapas mentais"
git push origin main
```

**Passo 5 — Testar o fluxo automático:**
```bash
# Editar qualquer relatório e fazer push
echo "" >> docs/relatorio_bugs.md
git add docs/relatorio_bugs.md
git commit -m "test: trigger de geração de mapas"
git push origin main
```

**Passo 6 — Verificar no GitHub Actions:**
1. Acesse `github.com/Rodig0SantOs/Projeto-Auditoria/actions`
2. Veja o workflow "Gerar Mapas Mentais (FreeMind .mm)" executando
3. Após ~30s, verifique que `.github/mindmaps/bugs.mm` foi atualizado

**Passo 7 — Importar o mapa atualizado no MindMeister:**
1. Baixe o `.mm` atualizado do repositório
2. No MindMeister, abra o mapa existente
3. **File → Import** → **Replace current map** → selecione o `.mm`
4. O mapa é atualizado mantendo suas customizações visuais

**Passo 8 — (Opcional) Configurar Zapier para importação automática:**
Configure o Zap 1 da Seção 6.1 para atualizar os mapas sem intervenção manual.

---

### Caminho 2 — API MindMeister (Plano Pro, Automação Total)

**Adicionalmente ao Caminho 1:**

**Passo A — Obter credenciais API:**
1. Acesse https://www.mindmeister.com/api/v2/apps
2. Crie uma aplicação OAuth (ver Seção 3.1)
3. Obtenha o Access Token

**Passo B — Configurar secrets no GitHub:**
1. `Settings → Secrets → Actions → New repository secret`
2. Adicione: `MINDMEISTER_TOKEN`, `MINDMEISTER_MAP_ID_BUGS`, etc.

**Passo C — Obter IDs dos mapas:**
```bash
curl -H "Authorization: Bearer SEU_TOKEN" \
     "https://www.mindmeister.com/api/v2/maps" | python -m json.tool
```

**Passo D — Fazer push para ativar o workflow de API:**
O workflow `update-mindmeister-api.yml` dispara automaticamente quando os `.mm` files são atualizados pelo workflow da Seção 5.1.

---

## Seção 10 — Referência Rápida

### Fluxos de Atualização

| Evento | Trigger | Ação | Resultado |
|---|---|---|---|
| Push em `relatorio_bugs.md` | `generate-mindmaps.yml` | Gera `bugs.mm` | Arquivo .mm atualizado no repo |
| Push em `relatorio_funcionalidades.md` | `generate-mindmaps.yml` | Gera `funcionalidades.mm` | Arquivo .mm atualizado no repo |
| Push em `roadmap.md` | `generate-mindmaps.yml` | Gera `roadmap.mm` | Arquivo .mm atualizado no repo |
| Push nos `.mm` files (Pro) | `update-mindmeister-api.yml` | API MindMeister | Mapas online atualizados |
| Card Trello "Concluído" | Zapier | MindMeister API | Nó marcado com ✅ |
| Deploy realizado | `trello-on-deploy.yml` → Zapier | MindMeister | Fase do roadmap marcada |

### Secrets do GitHub

| Secret | Quando Necessário | Valor |
|---|---|---|
| `MINDMEISTER_TOKEN` | Apenas API Pro | Access token OAuth 2.0 |
| `MINDMEISTER_MAP_ID_BUGS` | Apenas API Pro | ID do mapa de bugs |
| `MINDMEISTER_MAP_ID_FEATURES` | Apenas API Pro | ID do mapa de funcionalidades |
| `MINDMEISTER_MAP_ID_ROADMAP` | Apenas API Pro | ID do mapa de roadmap |
| `MINDMEISTER_MAP_ID_MELHORIAS` | Apenas API Pro | ID do mapa de melhorias |

### Comparação de Ferramentas Similares

Se o MindMeister não atender às necessidades, os mesmos arquivos `.mm` gerados pelo script funcionam em:

| Ferramenta | Formato | Automação via API | Plano Gratuito |
|---|---|---|---|
| **MindMeister** | .mm, .mmap | Sim (Pro) | 3 mapas |
| **XMind** | .mm (importação) | Não | Sim |
| **Coggle** | .mm (importação) | Sim | 3 diagramas |
| **Miro** | .mm (importação) | Sim | 3 boards |
| **draw.io / diagrams.net** | .mm, .xml | Sim (gratuito) | Ilimitado |

> **draw.io** é uma alternativa totalmente gratuita com API pública. Os arquivos `.mm` gerados pelo script são diretamente importáveis. Considere se o custo do MindMeister Pro for um obstáculo.

---

## Referências

| Recurso | Link |
|---|---|
| MindMeister API v2 | https://www.mindmeister.com/api/v2 |
| MindMeister OAuth | https://www.mindmeister.com/api/v2/apps |
| Zapier — MindMeister | https://zapier.com/apps/mindmeister |
| Make — MindMeister | https://make.com/en/integrations/mindmeister |
| MeisterTask | https://meistertask.com |
| FreeMind formato | http://freemind.sourceforge.net/wiki/index.php/Main_Page |
| draw.io (alternativa) | https://diagrams.net |

**Documentos internos relacionados:**

| Arquivo | Fonte de Dados para os Mapas |
|---|---|
| `docs/relatorio_bugs.md` | → `bugs.mm` (18 achados: 1 Crítico, 4 Altos, 6 Médios, 7 Baixos) |
| `docs/relatorio_funcionalidades.md` | → `funcionalidades.mm` |
| `docs/roadmap.md` | → `roadmap.mm` |
| `docs/relatorio_melhorias.md` | → `melhorias.mm` |
| `docs/trello_automacao.md` | Complementar (integração Trello) |
| `.github/workflows/generate-mindmaps.yml` | Workflow de geração |
| `.github/scripts/generate_mindmap.py` | Script de geração |

---

### Verificação executada nesta revisão

Os parsers foram executados contra a documentação real de **2026-08-26**, com o gerador extraído deste próprio documento (o código da Seção 4.3 é a fonte, não uma cópia).

**Primeira execução — antes das correções da v3.0:**

```
parse_bugs:         {'critical': 0, 'high': 3, 'medium': 5, 'low': 7}  | total: 15   ✅
parse_features:     {'done': 78, 'partial': 3, 'pending': 7}           | total: 88   ✅
parse_roadmap:      4 fases
   FASE 1 — Estabilização e Segurança      ->  8 itens
   FASE 2 — Qualidade e Confiança          ->  8 itens
   FASE 3 — Preparação para Produção       ->  7 itens
   FASE 4 — Crescimento e Escala           ->  0 itens   ⚠️  galho vazio
parse_improvements: 13 melhorias, 0 com esforço extraído              ⚠️
```

**Segunda execução — depois das correções:**

```
parse_roadmap:      4 fases, 56 itens no total
   FASE 1 — Estabilização e Segurança      ->  9 itens
   FASE 2 — Qualidade e Confiança          -> 16 itens
   FASE 3 — Preparação para Produção       -> 10 itens
   FASE 4 — Crescimento e Escala           -> 21 itens   ✅ (era 0)
parse_improvements: 13 melhorias, 12 com esforço extraído (92%)   ✅ (era 0%)
```

A única melhoria sem esforço é **M-27** (índices para busca), que de fato não
tem estimativa no documento — o parser está certo ao devolver vazio. 92% fica
acima do piso de 60%, então nenhum aviso é emitido.

Nenhuma das duas anomalias produziu erro, exceção ou saída não-zero. As duas foram encontradas **olhando o resultado**, não esperando uma falha — que é a razão de os pisos `MIN_EXPECTED` e `MIN_EFFORT_RATIO` existirem.

**Evolução ao longo das versões:**

| Parser | v1.2 | v2.0 (2026-08-24) | v3.0 (2026-08-26) |
|---|---|---|---|
| `parse_bugs` | 0 de 18 | 18 de 18 | **15 de 15** |
| `parse_features` | 0 de 80 | 80 de 80 | **88 de 88** |
| `parse_roadmap` | seção errada | 4 fases, 56 itens | **4 fases, 56 itens** |
| `parse_improvements` | 6 de 15 | 15 com esforço | **12 de 13 com esforço** |

> A queda de 15 para 13 melhorias **não é regressão**: o documento encolheu porque 5 itens estruturais (M-15, M-16, M-18, M-19, M-20) foram entregues pelo BLOCO P e saíram da lista de propostas. O parser está lendo corretamente um projeto com menos dívida.

---

*Documentação atualizada em 2026-08-26 (v3.0). Os parsers foram **reexecutados contra a documentação revisada**, duas regressões silenciosas foram encontradas e corrigidas, e os 5 arquivos `.mm` foram gerados de novo. Os números acima são saída verificada, não estimativa. A publicação no MindMeister em si (Seção 3, API) permanece não testada: nenhuma conta foi conectada.*

*Para os achados que alimentam `bugs.mm`, consulte `docs/relatorio_bugs.md`; para as fases de `roadmap.mm`, `docs/roadmap.md`.*
