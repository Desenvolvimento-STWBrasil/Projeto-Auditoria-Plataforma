# Relatório de Melhorias e Escalabilidade — Plataforma de Auditoria

| Campo | Valor |
|---|---|
| **Data** | 2026-06-24 (criação) · 2026-07-27 (rev. 1.1) · 2026-08-11 (rev. 2.0) · 2026-08-12 (rev. 3.0) · 2026-08-17 (rev. 4.0) · 2026-08-17 (rev. 5.0) · 2026-08-24 (rev. 6.0) · 2026-08-26 (rev. 7.0) · **2026-08-26 (rev. 8.0 — esta revisão)** |
| **Versão** | 8.0 |
| **Branch / HEAD** | `main` · `c769526` |
| **Relatórios Base** | `docs/relatorio_geral.md` (rev. 9.0), `docs/relatorio_funcionalidades.md` (rev. 9.0), `docs/relatorio_bugs.md` (rev. 10.0) |
| **Escopo** | Separação de responsabilidades, padrões, reuso, qualidade, observabilidade, testes, performance, segurança e escalabilidade |

---

## Leitura desta revisão

A rev. 6.0 propôs **cinco barreiras estruturais** (M-15, M-16, M-18, M-19, M-20) para as causas dos achados da auditoria adversarial. **As cinco foram implementadas** no BLOCO P (`4fd576f`) e verificadas nesta revisão. Este relatório registra o encerramento delas e trata da causa estrutural da geração seguinte de achados (rev. 9.0 de `relatorio_bugs.md`).

O padrão mudou, e a mudança é informativa. Na rev. 6.0 as causas eram sobre **quem pode o quê** — modelo de autorização ausente, invariantes vivendo só no código Python. Agora as causas são sobre **o que acontece nas bordas**:

| Achado (bugs, rev. 9.0) | Causa estrutural (aqui) |
|---|---|
| **B-A27** — senha > 72 bytes derruba `/auth/login` com 500 | **M-21** — a validação de entrada modela regras de negócio, nunca os limites físicos das bibliotecas que consomem essa entrada |
| **B-A29 / B-M27** — senha temporária perdida; e-mail com papel errado | **M-22** — o envio de e-mail é um efeito colateral externo dentro do caminho de resposta, sem contrato de falha e sem tipo próprio por destinatário |
| **B-A28** — cliente lê o checklist interno do auditor | **M-23** — `policy.py` modela **ações de escrita**; leitura sensível ficou fora do vocabulário |
| **B-M25 / B-M29** — defaults inseguros e divergentes | **M-24** — nenhum teste afirma qual é o default do código, então o default é o que sobrar |
| **B-M26** — 7 queries por empresa na listagem | **M-25** — o custo em queries de uma rota não é medido por nenhum teste |
| **B-M28** — guarda de path traversal só na exclusão | **M-16b** — a barreira de M-16 foi instalada no *consumidor*, não no *ponto único* |

Há uma lição transversal, e ela é a mesma que o defeito nº 14 (CSP) ensinou: **uma barreira instalada no lugar errado passa no teste e não protege**. M-16 pediu um contrato de storage com `delete` obrigatório; o contrato foi criado, mas a guarda de caminho que o acompanha foi parar dentro de `delete_files()` em vez de `get_absolute_path()` — e o download ficou de fora. M-20 pediu uma matriz de autorização; a matriz foi criada, cobrindo escrita, e a leitura ficou de fora.

Não é falha de execução. É a diferença entre corrigir um caso e cobrir a superfície onde o caso vive.

---

## O que já foi entregue (acompanhamento dos itens M-xx)

| Item | Status em 2026-08-26 | Verificação |
|---|---|---|
| M-01 (Repository pattern) | ✅ Concluído | 100% conectado a consumidores reais |
| **M-01c** (Extrair checagem de posse) | ✅ **Entregue no BLOCO R** | `app/core/access.py` — de 4 implementações para **1**, verificado por `grep` |
| M-02 (Refresh token + rate limit) | ✅ Concluído | Sonda: 5 logins → 401, 6º → **429** |
| M-03 (Componentização) | 🔄 Pivotou para Server Components + DAL | ver **M-17** — maior arquivo em **890 LOC** |
| M-04 (updated_at / soft delete / paginação) | 🟡 Parcial | Mixins aplicados; **soft delete com 0 consultas** (B-B19); paginação em `GET /audits` e `GET /admin/companies` |
| M-05 (Storage abstrato) | 🟡 Parcial → ver **M-16** | `Protocol` existe; nenhuma implementação além do disco local |
| M-06 (Chat integrado) | ✅ Concluído | Por controle, por card e geral por empresa |
| M-07 (Observabilidade) | 🟡 Parcial | `structlog` + `RequestIDMiddleware` + `/health` reais; sem métricas/tracing |
| M-08 (Testes backend) | 🟢 **258 testes, 100% verdes** | 24 arquivos · +48 no BLOCO Q, +8 no BLOCO R |
| **M-08b** (Testes frontend) | ✅ **Entregue no BLOCO R** | **114 testes**, 81% de statements e 93,5% de funções · job no CI |
| M-08c (CI rodando a suíte) | ✅ **Executado em 2026-08-26** | 4 jobs verdes em `main`. A 1ª execução revelou 4 defeitos — ver **M-30** |
| M-09 (E-mail assíncrono) | ❌ Pendente → agravado por **M-22** | `email_sender.py` síncrono e **sem tratamento de falha** |
| M-10 (Docker/CI) | ✅ Concluído estaticamente | Falta `docker build`/`docker run` reais |
| M-11 (Documentação) | ✅ Concluído | `docs/` sincronizada nesta revisão |
| M-12 (Unificar checklist) | ✅ Concluído | — |
| M-13 (Rotas Next.js órfãs) | ✅ Concluído | 5 rotas, todas com consumidor |
| M-14 (Código morto) | ✅ Concluído | `Monitoring`, `DashboardCardListItem`, `db_auditoria.sql` removidos |
| **M-15** (Camada de política) | ✅ **Entregue no BLOCO P.1** | `app/core/policy.py` — 13 ações, `can()`/`assert_can()` · ver **M-23** |
| **M-16** (Storage com `delete`) | ✅ **Entregue no BLOCO P.2** | `storage_backend.py::StorageBackend` Protocol · ver **M-16b** |
| M-17 (Decompor > 500 LOC) | 🔴 Pendente | **4 arquivos**: 890 / 649 / 594 / 518 |
| **M-18** (Migrations no CI) | ✅ **Entregue no BLOCO P.4** | `test_migrations_smoke.py` + job `migrations` contra MySQL 8.4 real |
| **M-19** (Constraint de unicidade) | ✅ **Entregue no BLOCO P.3** | `UniqueConstraint(dashboard_id, origin_template_card_id)`, migration `b7c02e91d4a5` |
| **M-20** (Matriz de autorização) | ✅ **Entregue no BLOCO P.1** | `test_authorization_matrix.py` · cobre escrita, **não leitura** — ver **M-23** |

**Placar da rev. 6.0: 5 barreiras propostas, 5 entregues.** É o melhor índice de conversão de qualquer revisão deste documento.

---

## 0. A causa estrutural que estava acima de todas as outras `🆕 rev. 8.0`

### M-30 — Uma barreira que nunca executou não é uma barreira

**Origem:** B-A30, B-A31, B-M30, B-M31 — os quatro defeitos que a **primeira execução real do
`ci.yml`** revelou, em 2026-08-26.

Este item vem antes dos demais porque **explica por que os demais existiram**.

#### O que aconteceu

O `ci.yml` foi escrito no BLOCO H, em 2026-08-11. Entre essa data e 2026-08-26, ele foi:

- citado como garantia em `roadmap.md`, `dashboard_projeto.md` e `deploy_producao.md`;
- ampliado de 2 para 4 jobs no BLOCO P, com `gitleaks`, `pip-audit` e um job de migrations contra
  MySQL real;
- usado como critério de saída da **Fase 1** do roadmap;
- contado como "DevOps 85%" no semáforo.

E nunca executou. Nem uma vez.

Quando finalmente rodou, **3 dos 4 jobs reprovaram** — e um deles (`backend`) **nunca poderia ter
passado**, porque faltavam as variáveis de ambiente sem as quais `Settings` não instancia.

#### O padrão, nomeado

Este projeto já tinha registrado duas variações do mesmo erro:

| Ocorrência | Forma |
|---|---|
| **Defeito #14** (P.7) | O teste de CSP existia e passava, e a página renderizava em branco. Perguntava *"o header está presente?"* em vez de *"a página funciona sob ele?"* |
| **Defeito #6** (Q.7) | O teste de path traversal passava **com e sem** a correção, porque o caminho malicioso não existia naquela máquina |
| **M-30** (aqui) | A barreira inteira nunca executou |

São três degraus da mesma escada:

```
  o teste mede a coisa errada
    → o teste não discrimina
      → o teste nunca roda
```

O terceiro é o mais perigoso, porque é o mais fácil de não notar: **um job que nunca roda não
aparece vermelho.** Ele simplesmente não aparece.

#### A regra que este item instala

> **Uma barreira só conta como barreira depois que executou no ambiente de destino e reprovou
> alguma coisa pelo menos uma vez.** Antes disso, ela é uma intenção documentada — e deve ser
> descrita assim nos documentos que a citam.

Consequência prática para este projeto, aplicada na rev. 10.0 de `relatorio_bugs.md` e na rev. 9.0
de `dashboard_projeto.md`: nenhum semáforo conta uma automação como verde enquanto não houver uma
execução real registrada.

#### O que ainda não executou

A honestidade exige a lista. Hoje, mesmo com o CI verde:

| Automação | Executou de verdade? |
|---|---|
| `ci.yml` — 4 jobs | ✅ Sim, em `main`, 2026-08-26 |
| `commit-report.yml` | ✅ Sim — 44 → 46 entradas, com push de volta |
| `docker build` / `docker compose up` | 🔴 **Não** — Sprint D |
| Restore de backup | 🔴 **Não** — Sprint D |
| Quadro do Trello (`trello_automacao.md`) | 🔴 **Não** — quadro não criado |
| Publicação no MindMeister | 🔴 **Não** — nenhuma conta conectada |
| Deploy em produção | 🔴 **Não** |

Os cinco últimos continuam sendo intenções documentadas. **O gerador de mapas mentais é o caso
mais instrutivo:** o script `.mm` foi executado e verificado duas vezes, e nas duas encontrou
regressões silenciosas — mas a **publicação** no MindMeister, que é a metade que interage com o
mundo, nunca foi exercitada.

#### Esforço

Zero de código. É uma regra de leitura dos próprios documentos — e a manutenção da tabela acima.

---

## 1. Validação de entrada: as regras de negócio estão modeladas, os limites físicos não

### M-21 — Todo limite de biblioteca precisa virar contrato explícito `🆕 prioridade máxima`

**Origem:** B-A27 (senha > 72 bytes derruba `/auth/login` com exceção não tratada)

**O problema estrutural.** `UserCreate.password_strength` valida três regras: mínimo de 8 caracteres, uma maiúscula, um dígito. Todas são **regras de negócio** — decisões de produto sobre o que é uma senha aceitável. Nenhuma é um **limite físico** — restrição imposta pela biblioteca que vai consumir o valor.

O bcrypt tem um limite físico de 72 bytes. Ninguém o modelou, porque ele não é uma decisão de produto: é um fato sobre a ferramenta. E como não foi modelado, o comportamento no limite passou a ser "o que a versão instalada da biblioteca decidir fazer" — truncar em silêncio até a 3.x, levantar `ValueError` a partir da 4.0.

**Por que isso volta a acontecer.** O projeto tem outros limites físicos igualmente não modelados:

| Limite | Onde vive hoje | O que acontece se for ultrapassado |
|---|---|---|
| `users.email VARCHAR(255)` | Só no schema do banco | `EmailStr` não impõe máximo → `DataError` do MySQL → 500 |
| `companies.name VARCHAR(160)` | Só no banco (o schema Pydantic tem `max_length=160` ✅) | Coberto |
| `dashboard_cards.title VARCHAR(160)` | Só no banco | Card criado pela API com título de 200 caracteres → 500 |
| `evidences.storage_key VARCHAR(500)` | Só no banco | Não alcançável hoje (UUID de tamanho fixo) |
| `MAX_UPLOAD_BYTES` | Constante em `client.py` ✅ | Coberto por `_read_limited` |

**A melhoria.** Adotar a regra: *toda coluna `String(n)` do ORM tem um `max_length=n` correspondente no schema Pydantic de entrada, e todo limite de biblioteca externa vira uma constante nomeada no módulo que a encapsula.*

Passo 1 — a constante no lugar certo (já detalhado em B-A27):

```python
# backend/app/core/security.py
MAX_PASSWORD_BYTES = 72   # limite físico do bcrypt, não decisão de produto
```

Passo 2 — o teste que impede a divergência entre ORM e schema voltar:

```python
# backend/tests/test_schema_length_parity.py
"""M-21: todo String(n) do ORM tem max_length correspondente na entrada.

Este teste não verifica um bug conhecido — ele varre a superfície onde a
classe de bug vive. Uma coluna nova sem max_length no schema falha aqui,
não em produção com DataError e HTTP 500.
"""
from __future__ import annotations

import pytest
from sqlalchemy import String, inspect

import app.models  # noqa: F401 — registra todos os models
from app.db.base import Base

# Campos de entrada que a API aceita, mapeados para (tabela, coluna).
# Acrescente uma linha ao criar um endpoint de escrita novo.
CAMPOS_DE_ENTRADA = [
    ("app.schemas.auth", "UserCreate", "full_name", "users", "full_name"),
    ("app.schemas.auth", "UserCreate", "email", "users", "email"),
    ("app.schemas.admin_onboarding", "PrincipalUserOnboardingRequest",
     "company_name", "companies", "name"),
    ("app.schemas.company_admin", "CompanyUpdateRequest", "name",
     "companies", "name"),
    ("app.schemas.company_admin", "CompanyUpdateRequest", "email",
     "companies", "email"),
    ("app.schemas.dashboard_runtime", "DashboardCardCreate", "title",
     "dashboard_cards", "title"),
]


def _limite_da_coluna(tabela: str, coluna: str) -> int | None:
    modelo = next(
        m for m in Base.registry.mappers if m.class_.__tablename__ == tabela
    )
    col = inspect(modelo.class_).columns[coluna]
    return col.type.length if isinstance(col.type, String) else None


@pytest.mark.parametrize(
    "modulo,classe,campo,tabela,coluna", CAMPOS_DE_ENTRADA
)
def test_schema_respeita_o_limite_da_coluna(modulo, classe, campo, tabela, coluna):
    import importlib

    schema = getattr(importlib.import_module(modulo), classe)
    limite_banco = _limite_da_coluna(tabela, coluna)
    assert limite_banco is not None

    info = schema.model_fields[campo]
    limite_schema = next(
        (getattr(m, "max_length", None) for m in info.metadata
         if getattr(m, "max_length", None) is not None),
        None,
    )
    assert limite_schema is not None, (
        f"{classe}.{campo} não tem max_length; {tabela}.{coluna} é "
        f"String({limite_banco}) — uma entrada maior vira HTTP 500 (M-21)"
    )
    assert limite_schema <= limite_banco, (
        f"{classe}.{campo} aceita {limite_schema} caracteres, mas "
        f"{tabela}.{coluna} só guarda {limite_banco}"
    )
```

**Custo:** 3 h (constante + `max_length` nos schemas + o teste). **Impacto:** fecha uma classe inteira de 500 por entrada fora do formato esperado.

---

## 2. Efeitos colaterais externos dentro do caminho de resposta

### M-22 — Toda integração externa precisa de contrato de falha e de tipo por destinatário `🆕`

**Origem:** B-A29 (senha temporária perdida sem SMTP), B-M27 (cliente principal recebe e-mail de sub-usuário), B-A29 (falha de SMTP vira 500 após o commit)

**O problema estrutural.** `send_sub_user_credentials_email` faz três coisas erradas ao mesmo tempo, e as três decorrem da mesma ausência: **não existe um contrato sobre o que significa "enviar um e-mail" quando o envio pode falhar.**

1. **Retorna `None`.** Quem chama não tem como saber se a mensagem saiu. O código de onboarding, então, assume que saiu — e descarta a única cópia da senha temporária.
2. **Propaga exceções de SMTP.** É chamada **depois** do `db.commit()` e **fora** de qualquer `try`. Um servidor de e-mail indisponível vira HTTP 500 para o admin, com o usuário já criado e committado. O admin tenta de novo e recebe 409.
3. **É reusada para um destinatário que não é o dela.** O onboarding do usuário principal chama a função de sub-usuário, com um comentário que declara a intenção — *"Reuso da infraestrutura de email"* — sem notar que o assunto e o corpo são específicos do outro papel.

O item 3 merece atenção porque é o mais fácil de repetir. Reuso de **infraestrutura** (conexão SMTP, TLS, autenticação, tratamento de erro) é correto e desejável. Reuso de **conteúdo** endereçado a um papel específico não é reuso: é o destinatário errado recebendo a mensagem de outro.

**A melhoria.** Separar as duas camadas explicitamente:

```
email_sender.py
├── _enviar(msg) -> bool          ◀── INFRAESTRUTURA: reusável, captura falha,
│                                     nunca propaga, sempre devolve sinal
├── send_principal_user_credentials_email(...)  ◀── CONTEÚDO por papel
└── send_sub_user_credentials_email(...)        ◀── CONTEÚDO por papel
```

O código completo das três funções está em **B-A29** de `relatorio_bugs.md`. O que importa aqui é a **regra que ele instala**:

> Toda função que fala com um sistema externo devolve um sinal de sucesso e **nunca** propaga a falha do sistema externo para uma transação já committada. Se o efeito colateral é a única saída de um dado que não pode se perder, quem chama precisa de um plano B.

Esse é o mesmo princípio que `storage.delete_files()` já aplica corretamente desde o BLOCO P.2 — *"nunca levanta exceção: a transação já está committada e não pode ser desfeita por causa de um arquivo"*. O e-mail simplesmente não recebeu o mesmo tratamento.

**Extensão natural (M-09).** Com o contrato de falha no lugar, mover o envio para uma fila assíncrona deixa de ser refatoração arriscada: o chamador já sabe lidar com "não entregue agora".

**Custo:** 3 h (junto com B-A29/B-M27). **Impacto:** elimina a perda de credencial, o 500 pós-commit e o e-mail com papel errado, e destrava M-09.

---

## 3. Autorização: o vocabulário cobre escrita, não leitura

### M-23 — Estender `policy.py` às leituras sensíveis `🆕`

**Origem:** B-A28 (cliente lê o checklist interno e o histórico do auditor)

**O problema estrutural.** M-15 foi entregue com precisão: `app/core/policy.py` existe, tem 13 ações, `ALLOWED_ROLES` como fonte única, `can()` e `assert_can()`. E M-20 entregou a matriz que exercita cada endpoint de escrita com cada papel que não deveria poder executá-lo.

Só que **as 13 ações são todas de escrita**. O enum nasceu de uma pergunta — *"quem pode declarar conformidade?"* — e respondeu só a ela. Leitura ficou fora do vocabulário, então cada endpoint de leitura decide sozinho, e a decisão de `get_card_details` foi não decidir.

O resultado é uma assimetria observável dentro do mesmo arquivo:

| Recurso interno do auditor | Escrita | Leitura |
|---|---|---|
| Nota de card (`DashboardCardNote`) | `require_admin` | `require_admin` ✅ |
| Item de checklist | `require_admin` | 🔴 aberta ao cliente |
| Entrada de histórico | recusa não-admin | 🔴 aberta ao cliente |

Nota está certo. Checklist e histórico estão errados. Nada no código explica por que os três, que são igualmente internos, receberam tratamentos diferentes — porque a diferença não foi decidida, foi herdada.

**A melhoria.** Duas mudanças pequenas e uma regra:

1. `Action.READ_CARD_INTERNALS` entra no enum (código completo em B-A28).
2. `test_authorization_matrix.py` ganha uma seção de **leitura**, no mesmo formato da de escrita.
3. **Regra:** ao acrescentar um campo a um `response_model` que já serve a mais de um papel, a pergunta *"este campo pode ser visto por todos os papéis que chamam este endpoint?"* precisa de uma resposta em `policy.py`, não no julgamento de quem escreveu a linha.

```python
# backend/tests/test_authorization_matrix.py — seção nova

# (rota, papéis que NÃO podem ver, campos que não podem aparecer)
LEITURAS_RESTRITAS = [
    ("/api/v1/dashboard/cards/{card_id}", ["user", "sub-user"],
     ["checklist", "history"]),
    ("/api/v1/dashboard/cards/{card_id}/notes", ["user", "sub-user"], None),
]


@pytest.mark.parametrize("rota,papeis,campos_vedados", LEITURAS_RESTRITAS)
def test_leitura_restrita_por_papel(
    client, tokens_por_papel, card_semeado, rota, papeis, campos_vedados
):
    """M-23: leitura sensível também é decisão de política.

    `campos_vedados = None` significa "a rota inteira é vedada" (403).
    Uma lista de campos significa "a rota é permitida, mas estes campos
    voltam vazios" — o cliente tem direito ao card, não ao trabalho
    interno do auditor sobre ele.
    """
    url = rota.format(card_id=card_semeado.id)
    for papel in papeis:
        resp = client.get(
            url, headers={"Authorization": f"Bearer {tokens_por_papel[papel]}"}
        )
        if campos_vedados is None:
            assert resp.status_code == 403, f"{papel} acessou {rota}"
        else:
            assert resp.status_code == 200
            corpo = resp.json()
            for campo in campos_vedados:
                assert corpo[campo] == [], (
                    f"{papel} recebeu '{campo}' preenchido em {rota}"
                )
```

**Custo:** 2 h. **Impacto:** fecha B-A28 e dá à próxima leitura sensível um lugar onde ser decidida.

---

## 4. Configuração: o default é o que sobrar

### M-24 — Testar o contrato de configuração `🆕`

**Origem:** B-M25 (`ALLOW_PUBLIC_REGISTRATION` default `True`), B-M29 (`JWT_EXPIRES_MINUTES` 15 no backend, 60 no frontend)

**O problema estrutural.** `Settings` tem 21 campos, dos quais 19 têm default. Nenhum teste afirma qual deveria ser. Consequência direta: **o default de um campo de segurança é aquele que a pessoa que escreveu a linha achou conveniente na hora**, e ninguém revisita.

`ALLOW_PUBLIC_REGISTRATION: bool = True` é o exemplo puro. O `.env.example` diz *"Mantenha false em produção"*; o `docker-compose.yml` define `false`; e o código, sozinho, diz `True`. Três fontes, duas concordando, e a que vale é a terceira.

`JWT_EXPIRES_MINUTES` é a variação com duas linguagens: 15 no Python, 60 no TypeScript, em dois arquivos.

**A melhoria.** Um arquivo de teste curto que declara os defaults que importam — e que serve de documentação executável para quem for mudá-los. O código está em **B-M25** (`tests/test_config_defaults.py`).

A regra que ele instala:

> Todo default que afeta segurança, sessão ou exposição de dados tem uma asserção. Mudar o valor exige mudar o teste — o que força a mudança a passar por revisão em vez de escorregar num commit de outra coisa.

Vale registrar também a **assimetria de espelhamento**: `JWT_EXPIRES_MINUTES` e `JWT_REFRESH_EXPIRES_DAYS` existem em Python e em TypeScript, e nada os liga. A solução completa seria gerar as constantes do frontend a partir das do backend; a solução proporcional ao tamanho do projeto é o comentário `// Espelha backend/app/core/config.py` mais a mensagem do teste apontando os dois arquivos. Adotada a segunda.

**Custo:** 30 min. **Impacto:** desproporcional ao custo — dois achados fechados e uma classe inteira contida.

---

## 5. Performance: o custo de uma rota não é medido

### M-25 — Orçamento de queries por rota `✅ Entregue no BLOCO R`

**Origem:** B-M26 (`GET /admin/companies` — 7 queries por empresa)

**O problema estrutural.** A suíte tem 202 testes e nenhum deles mede **custo**. Um endpoint que responde certo em 3 queries e um que responde certo em 300 são indistinguíveis para a suíte inteira.

Isso não é hipotético neste projeto: B-M24 (N+1 na listagem de templates) foi corrigido no BLOCO P, e a correção foi verificada **por leitura**. Nada impede que a próxima alteração em `list_templates` reintroduza o N+1 com todos os testes verdes — foi exatamente o que aconteceu com `_load_admin_data`, que nasceu correta para uma empresa e foi reusada num laço.

O padrão é reconhecível: **uma função de detalhe reusada numa listagem**. É a forma mais comum de N+1 em código bem organizado, porque a função de detalhe está certa.

**A melhoria.** Um `conftest` fixture de contagem de queries e um teto por rota de listagem. O código completo está em **B-M26** (`tests/test_query_budget.py`); o essencial é o formato do teto:

```python
@pytest.mark.parametrize("quantidade", [5, 20])
def test_custo_da_listagem_nao_cresce_com_o_numero_de_empresas(...):
    ...
    assert contador.count <= 15, (
        f"{contador.count} queries para {quantidade} empresas — o N+1 de "
        "B-M26 voltou (o custo deve ser constante, não linear)"
    )
```

Parametrizar por **duas** quantidades é o detalhe que faz o teste funcionar: um teto absoluto com uma quantidade só pode ser satisfeito por acaso; com 5 e 20 no mesmo teto, só passa se o custo for de fato constante.

**Rotas que merecem orçamento** (em ordem de risco):

| Rota | Custo hoje | Teto sugerido |
|---|---|---|
| `GET /admin/companies` | 7·N + 3 | ≤ 15 |
| `GET /admin/audits` | a medir | ≤ 10 |
| `GET /dashboard/companies/{id}/cards` | 3 (já usa `selectinload`) ✅ | ≤ 8 |
| `GET /admin/templates` | 1 (corrigido em B-M24) ✅ | ≤ 5 |
| `GET /companies/{id}/messages` | 4 para 12 mensagens ✅ | ≤ 8 |

**Custo:** 4 h (fixture + 5 rotas). **Impacto:** transforma performance de "algo que se descobre em produção" em "algo que quebra o CI".

---

## 6. Ciclo de vida de arquivo: a barreira no lugar errado

### M-16b — A guarda pertence ao ponto único, não ao consumidor `🔺 continuação de M-16`

**Origem:** B-M28 (guarda de path traversal só em `delete_files`)

M-16 foi entregue: `StorageBackend` existe como `Protocol`, com `delete` obrigatório e uma docstring que explica exatamente por quê. A implementação de `delete_files()` inclui a guarda correta de path traversal.

Mas `get_absolute_path()` — a função que o **download** usa, e o ponto único por onde toda resolução de caminho deveria passar — continua sendo `return Path(storage_key)`.

**Por que isso importa mais do que parece.** Não é explorável hoje: `storage_key` só é gravado por `save_file()`, que gera UUID. A gravidade não está no risco atual, está no que a assimetria comunica. Um desenvolvedor que leia `delete_files()` conclui, corretamente, que o projeto se preocupa com path traversal em storage. Ao implementar o `StorageBackend` para S3, ele vai portar `save`, `resolve`, `delete` e `exists` — e a guarda, que está dentro de `delete_files` em vez de dentro de `resolve`, não será portada.

É a mesma forma do defeito nº 14 (CSP): a proteção existe, o teste passa, e o caminho que importa não está coberto.

**A melhoria** (código completo em B-M28): mover a verificação para `_resolver_dentro_do_upload_dir()`, chamada por `get_absolute_path()`, e fazer `delete_files()` consumi-la. O teste parametrizado `test_get_absolute_path_recusa_ou_confina` cobre os dois consumidores de uma vez.

**Custo:** 1 h 30. **Impacto:** a garantia passa a acompanhar qualquer backend de storage futuro.

---

## 7. Reuso e tamanho de arquivo

### M-01c — Unificar a checagem de posse `✅ Entregue no BLOCO R — 4 implementações viraram 1`

Quatro cópias do mesmo conceito:

| Arquivo | Linha | Forma |
|---|---|---|
| `app/api/v1/client.py` | 52 | `_resolve_owner_user_id` |
| `app/api/v1/dashboard_cards.py` | 56 | `_resolve_owner_user_id` (idêntica) |
| `app/api/v1/company_messages.py` | 24 | `_resolve_owner_user_id` (idêntica, com typo `vísculo` — B-B21) |
| `app/services/company_admin.py` | 66 | `member_user_ids` (direção inversa) |

O comentário em `company_messages.py` reconhece a duplicação e a justifica por consistência com o padrão já estabelecido. Era uma justificativa razoável com duas cópias. Com quatro, e com uma delas carregando um typo que as outras não têm, ela deixou de ser.

**Custo de não fazer, medido:** B-B21 corrige um typo numa das quatro; as outras três seguem certas por acaso. B-B23 (403 × 404) precisa ser aplicado em **três** arquivos, e o risco de esquecer um é real — a nota de atenção em B-B23 existe por isso.

**A melhoria:**

```python
# backend/app/core/access.py
"""
Posse de recurso por usuário — ponto único (M-01c).

Existia em 4 cópias (client.py, dashboard_cards.py, company_messages.py e,
na direção inversa, company_admin.py::member_user_ids). Quatro cópias de
uma regra de acesso significam quatro lugares para corrigir quando a regra
muda — e três lugares para esquecer.
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company_dashboard import Company
from app.models.user import User


def resolve_owner_user_id(current_user: User) -> int:
    """ID do usuário "dono" dos dados: o próprio, ou o principal de quem
    ele é sub-usuário. Sub-usuários não têm dados próprios — têm acesso
    aos do principal ao qual estão vinculados."""
    if current_user.role == "sub-user":
        if current_user.parent_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sub-usuário sem vínculo com usuário principal",
            )
        return current_user.parent_user_id
    return current_user.id


def member_user_ids(db: Session, principal_user_id: int) -> list[int]:
    """A relação inversa: principal + todos os seus sub-usuários. Usada
    onde é preciso partir da empresa para achar os usuários (filtro de
    auditoria por empresa, exclusão em cascata)."""
    sub_user_ids = db.scalars(
        select(User.id).where(User.parent_user_id == principal_user_id)
    ).all()
    return [principal_user_id, *sub_user_ids]


def get_company_with_access(
    db: Session, company_id: int, current_user: User
) -> Company:
    """Empresa acessível pelo chamador, ou 404.

    404 — e não 403 — quando a empresa existe mas não é do chamador
    (B-B23): distinguir "não existe" de "existe e não é sua" permite
    enumerar os company_id da plataforma.
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
```

Os quatro arquivos passam a importar de `app.core.access`. **Custo:** 3 h, incluindo a atualização dos testes que hoje afirmam 403.

---

### M-17 — Decompor os Client Components acima de 500 LOC `🔴 pendente, 4 arquivos`

| Arquivo | LOC | Responsabilidades misturadas |
|---|---|---|
| `admin/empresas/[id]/dashboard/company-dashboard-client.tsx` | **890** | Listagem, filtro, seleção múltipla, barra de ação em massa, modal de card, aplicação de template, criação de card |
| `admin/empresas/empresas-client.tsx` | **649** | Tabela, busca, paginação, formulário de criação, modal de exclusão com resumo de impacto |
| `admin/templates/templates-client.tsx` | **594** | Lista de templates, editor de template, editor de card de template, reordenação |
| `client/client-dashboard-client.tsx` | **518** | Cards, upload de evidência, chat por controle, estado de envio |

**A dependência que trava.** Decompor sem teste é reescrever no escuro — e são exatamente os arquivos com **zero** cobertura. A ordem correta é **M-08b antes de M-17**, e é por isso que M-08b passa a ser a prioridade máxima deste documento.

**Direção sugerida** (para o maior deles):

```
company-dashboard-client.tsx  (890)
├── use-card-selection.ts          ← hook: seleção múltipla + limpar
├── use-card-filters.ts            ← hook: busca, include_hidden, categoria
├── card-grid.tsx                  ← apresentação: grade + estado vazio
├── bulk-action-bar.tsx            ← as 5 operações em massa
├── apply-template-dialog.tsx      ← escolha de template + resultado
└── card-detail-dialog.tsx         ← detalhe, status, chat
```

**Custo:** 3 dias, **depois** de M-08b.

---

## 8. Testes: a lacuna que sobrou

### M-08b — Testes de frontend `✅ Entregue no BLOCO R — 114 testes`

**7.811 LOC. 15 páginas. 9 grupos de Server Actions. 5 route handlers. Zero testes.**

A justificativa deixou de ser teórica há duas revisões:

| Evidência | O que mostra |
|---|---|
| 5 dos 12 defeitos do BLOCO O eram de frontend | Só apareceram por execução manual |
| 13 defeitos do BLOCO P, 11 pegos pela própria suíte | O backend tem rede; o frontend não |
| Defeito nº 14 (CSP) | `tsc` e `eslint` passavam; a página renderizava em branco |
| Os 3 achados Alta da rev. 9.0 | Todos de backend — porque a sonda **existe** para o backend |

Esse último ponto é o mais importante e o menos óbvio: **a auditoria adversarial só encontra achados onde consegue sondar.** Três revisões seguidas produziram achados quase exclusivamente de backend. Não é porque o frontend está mais correto — é porque não há como exercitá-lo programaticamente.

**Entrada sugerida** (em ordem de retorno):

| Ordem | Alvo | Por quê primeiro |
|---|---|---|
| 1 | **Server Actions** (`actions.ts` × 9) | São funções puras de I/O — testáveis com `vi.mock` de `callBackend`, sem DOM. Cobrem o contrato com o backend |
| 2 | `lib/session.ts` e `lib/safe-redirect.ts` | Lógica de autorização e anti-open-redirect, pequena e crítica |
| 3 | `proxy.ts` | O guardião de rota; testável com `NextRequest` sintético |
| 4 | Os 4 componentes > 500 LOC | Habilita M-17 |

```jsonc
// frontend/package.json — devDependencies a acrescentar
{
  "devDependencies": {
    "vitest": "^2.1.0",
    "@vitejs/plugin-react": "^4.3.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.5.0",
    "jsdom": "^25.0.0"
  },
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest"
  }
}
```

```typescript
// frontend/vitest.config.ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
  },
  resolve: {
    alias: { "@": resolve(__dirname, ".") },
  },
});
```

```typescript
// frontend/app/private/client/actions.test.ts — o primeiro teste
import { describe, expect, it, vi, beforeEach } from "vitest";

vi.mock("@/lib/session", () => ({
  requireClient: vi.fn().mockResolvedValue({ id: 1, role: "user" }),
  getAccessToken: vi.fn().mockResolvedValue("token-de-teste"),
}));

const callBackend = vi.fn();
vi.mock("@/lib/server-backend", () => ({
  callBackend: (...args: unknown[]) => callBackend(...args),
}));

describe("uploadEvidenceAction", () => {
  beforeEach(() => callBackend.mockReset());

  it("envia o FormData ao endpoint do controle e devolve o nome do arquivo", async () => {
    const { uploadEvidenceAction } = await import("./actions");
    callBackend.mockResolvedValue({ id: 7, file_path: "uploads/x.pdf", filename: "politica.pdf" });

    const fd = new FormData();
    fd.append("file", new File(["conteudo"], "politica.pdf"));
    const resultado = await uploadEvidenceAction(42, fd);

    expect(callBackend).toHaveBeenCalledWith(
      "/api/v1/client/controls/42/evidences",
      expect.objectContaining({ method: "POST", token: "token-de-teste" }),
    );
    expect(resultado).toEqual({ ok: true, fileName: "politica.pdf" });
  });

  it("converte erro do backend em resultado tratável, sem lançar", async () => {
    const { uploadEvidenceAction } = await import("./actions");
    callBackend.mockRejectedValue(new Error("Tipo de arquivo não permitido: .exe"));

    const resultado = await uploadEvidenceAction(42, new FormData());

    expect(resultado).toEqual({
      ok: false,
      message: "Tipo de arquivo não permitido: .exe",
    });
  });
});
```

E o job de CI que fecha o ciclo:

```yaml
# .github/workflows/ci.yml — acrescentar ao job `frontend`, após "Checagem de tipos"
      - name: Testes (Vitest)
        run: npm run test
```

**Custo:** 2–3 dias para a base + os Server Actions. **Impacto:** o maior de todos os itens deste documento.

---

## 9. Observabilidade

### M-07b — Métricas e alerting básico `🟡 sem mudança`

Existe: `structlog` em JSON, `X-Request-ID` por requisição, `GET /health` com `SELECT 1` real.
Falta: contadores (requisições por rota/status), histograma de latência, alerta.

Com `prometheus-fastapi-instrumentator` (uma dependência, ~5 linhas em `main.py`), o projeto ganha `/metrics` e a base para responder "está lento?" sem adivinhar. **Custo:** 4 h.

### M-07c — Log de auditoria imutável `🟡 parcialmente mitigado pelo BLOCO P`

RNF-02 pede trilha de auditoria. Hoje ela vive em `dashboard_card_history_entries`, que — depois de B-A23 — **só o admin escreve**. A mitigação é real e importante, mas incompleta: a tabela continua sendo `UPDATE`/`DELETE`-ável por qualquer coisa com acesso ao banco, e cobre apenas eventos de card.

Uma trilha de auditoria de verdade é **append-only** e cobre os eventos que importam para uma auditoria: login, mudança de status de controle, upload e download de evidência, encerramento de auditoria, exclusão de empresa, aprovação de sub-usuário.

```python
# backend/app/models/audit_log.py
class AuditLog(Base):
    """
    Trilha append-only (RNF-02). Sem UPDATE, sem DELETE, sem soft delete:
    um registro de auditoria que pode ser alterado não é registro de
    auditoria. `actor_user_id` é ON DELETE SET NULL — a exclusão de um
    usuário não pode apagar o rastro do que ele fez.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
```

`actor_email` é redundante com a FK **de propósito**: a FK é `SET NULL`, então sem a cópia do e-mail a trilha perde o autor quando o usuário é excluído — e a exclusão de usuário é exatamente um dos eventos que a trilha precisa registrar.

**Custo:** 1–2 dias (modelo + migration + `record_event()` + chamada nos ~8 pontos + retenção).

---

## 10. Performance e escalabilidade

### M-26 — O backend não roda com mais de uma réplica `🔺 promovido a bloqueador de produção`

Dois estados vivem no processo:

| Estado | Onde | O que quebra com 2 réplicas |
|---|---|---|
| Evidências | `backend/uploads/` (volume local) | Upload cai na réplica A; download pede à réplica B → 404 |
| Rate limit | Memória de `slowapi` | O limite de 5 logins/min vira 5 × número de réplicas |

O `StorageBackend` Protocol (M-16) já é o ponto de extensão do primeiro. Faltam a implementação e a troca do rate limit:

```python
# backend/app/services/storage_s3.py — esqueleto que satisfaz o Protocol
class S3StorageBackend:
    """Implementação de StorageBackend sobre S3/MinIO (M-26).

    Satisfaz o Protocol por completo — inclusive `delete`, que é
    obrigatório justamente para que a lacuna de B-A26 não possa nascer
    de novo num backend novo.
    """

    def __init__(self, bucket: str, client) -> None:
        self._bucket = bucket
        self._client = client

    async def save(self, content: bytes, original_filename: str) -> str:
        key = f"evidences/{uuid.uuid4().hex}{Path(original_filename).suffix.lower()}"
        self._client.put_object(Bucket=self._bucket, Key=key, Body=content)
        return key

    def resolve(self, storage_key: str) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": storage_key},
            ExpiresIn=300,
        )

    def delete(self, storage_key: str) -> bool:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=storage_key)
            return True
        except ClientError:
            return False

    def exists(self, storage_key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=storage_key)
            return True
        except ClientError:
            return False
```

```python
# backend/app/main.py — rate limit compartilhado
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.RATE_LIMIT_STORAGE_URI,   # "redis://..." em prod,
                                                  # "memory://" em dev
)
```

**Custo:** 2–3 dias. **Impacto:** é o que separa "roda" de "roda em produção com mais de um nó".

### M-27 — Índices para os filtros que a UI oferece `🆕 baixa`

`GET /admin/companies?search=` faz `ILIKE '%termo%'` em quatro colunas. Prefixo curinga impede uso de índice B-tree — irrelevante com dezenas de empresas, mensurável com milhares. Registrar como conhecido; revisitar com FULLTEXT quando a base justificar.

---

## 11. Segurança estrutural

| Item | Estado | Ação |
|---|---|---|
| **M-02b** — Troca de senha no 1º login | ❌ Pendente | Coluna `must_change_password`; agravado por B-A29 (senha temporária sem prazo e sem recuperação) |
| **M-02c** — CSP e HSTS | ✅ **Entregue** | CSP duplo (API × docs) + HSTS sob HTTPS + `test_security_headers.py` |
| **M-02d** — Validação por conteúdo, não por extensão | ❌ Pendente | `python-magic` ou verificação de assinatura; hoje um `.exe` renomeado para `.pdf` passa |
| **M-02e** — Rotação de segredo | ✅ **Entregue** | Verificado: nenhum valor do `.env` atual aparece no histórico |
| **M-28** — Revogação de sessão `🆕` | ❌ Pendente | Tokens stateless sem blocklist: logout é client-side, `refresh_token` vazado vale 7 dias |
| **M-29** — Recuperação de senha `🆕` | ❌ Pendente | Não existe nenhum endpoint de reset. Junto com B-A29, um cliente sem acesso não tem saída |

**M-28 e M-29 são novos nesta revisão** e vieram da mesma observação: o projeto tem um ciclo de vida de credencial **sem volta**. A senha é gerada uma vez, enviada uma vez e nunca mais pode ser trocada, recuperada ou revogada. B-A29 é a manifestação aguda disso; M-02b, M-28 e M-29 são o tratamento completo.

```python
# backend/app/core/config.py — campos a acrescentar (M-26/M-28)
    RATE_LIMIT_STORAGE_URI: str = "memory://"
    STORAGE_BACKEND: str = "local"          # local | s3
    S3_BUCKET: str | None = None
    S3_ENDPOINT_URL: str | None = None
```

---

## 12. Plano de melhorias — curto / médio / longo prazo

### Curto prazo (próximas 2 semanas)

| # | Item | Origem | Esforço | Impacto |
|---|---|---|---|---|
| 1 | **1ª execução real do `ci.yml`** num PR | M-08c | **1 h** | 🔺🔺🔺 Valida as 5 barreiras do BLOCO P de uma vez |
| 2 | **M-21** — limites físicos como contrato | B-A27 | 3 h | 🔺🔺🔺 Fecha o único achado explorável sem credencial |
| 3 | **M-22** — contrato de falha no e-mail | B-A29, B-M27 | 3 h | 🔺🔺🔺 Elimina perda de credencial e 500 pós-commit |
| 4 | **M-23** — política nas leituras | B-A28 | 2 h | 🔺🔺 Fecha a metade que faltava de M-15 |
| 5 | **M-24** — testar defaults de config | B-M25, B-M29 | 30 min | 🔺🔺 Melhor relação custo/benefício do documento |
| 6 | **M-16b** — guarda no ponto único | B-M28 | 1 h 30 | 🔺🔺 Pré-requisito de M-26 |
| 7 | **M-08b** — base de testes de frontend | — | **2–3 dias** | 🔺🔺🔺 O maior gap do projeto |

**Total: ~4 dias.**

### Médio prazo (próximo mês)

| # | Item | Esforço | Impacto |
|---|---|---|---|
| ~~8~~ | ~~**M-25** — orçamento de queries + **B-M26**~~ | ✅ feito | Listagem de empresas: 7·N+3 → **8 queries constantes** |
| 9 | **M-01c** — unificar posse em `core/access.py` | 3 h | 🔺🔺 De 4 cópias para 1 |
| 10 | **M-26** — storage trocável + rate limit em Redis | 2–3 dias | 🔺🔺🔺 Destrava escala horizontal |
| 11 | **M-17** — decompor os 4 arquivos > 500 LOC | 3 dias | 🔺🔺 Depende de M-08b |
| 12 | **M-02b + M-29** — troca obrigatória + recuperação de senha | 2 dias | 🔺🔺 Fecha o ciclo de vida da credencial |
| 13 | **M-07b** — métricas Prometheus | 4 h | 🔺 Responde "está lento?" com dado |
| 14 | Achados Baixos **B-B17..B-B23** | 2 h | 🔺 Limpeza acumulada |

### Longo prazo (próximo trimestre)

| # | Item | Esforço | Impacto |
|---|---|---|---|
| 15 | **M-07c** — `audit_log` append-only (RNF-02) | 1–2 dias | 🔺🔺 Requisito formal ainda aberto |
| 16 | **M-28** — revogação de sessão | 1 dia | 🔺🔺 Logout com significado no servidor |
| 17 | **M-09** — e-mail assíncrono (destravado por M-22) | 1 dia | 🔺 |
| 18 | **M-02d** — validação por conteúdo | 1 dia | 🔺 |
| 19 | **N11** — decidir o destino do soft delete | 1 dia | 🔺 Resolve a contradição com a cascata física |
| 20 | **M-27** — índices/FULLTEXT para busca | 4 h | 🔺 Só quando a base justificar |

---

## 13. Resumo — o que muda a trajetória do projeto

Três frases:

1. **Uma hora resolve mais do que qualquer outra coisa neste documento.** Cinco barreiras estruturais foram construídas no BLOCO P e nenhuma jamais executou no ambiente para o qual foi escrita. Abrir um PR e deixar o `ci.yml` rodar converte cinco suposições em cinco garantias.

2. **O frontend é o ponto cego, e o ponto cego é demonstrável.** Três auditorias adversariais seguidas produziram achados quase só de backend — não porque o frontend esteja mais correto, mas porque não há como sondá-lo. M-08b não é sobre cobertura: é sobre tornar 7.811 linhas **auditáveis**.

3. **A próxima geração de achados já tem endereço.** As causas desta revisão — limites físicos não modelados (M-21), efeito externo sem contrato de falha (M-22), política que só fala de escrita (M-23), defaults sem teste (M-24), custo sem medição (M-25) — são todas da mesma família: **superfícies onde o projeto não faz pergunta nenhuma**. Corrigir os seis achados custa ~13 h; instalar as cinco barreiras custa ~13 h a mais, e é o que decide se a rev. 10.0 vai encontrar a mesma classe de coisa.

---

*Relatório gerado em 2026-08-26 (rev. 7.0) a partir de leitura direta do código em `34f8444` e das sondas executáveis da rev. 9.0 de `docs/relatorio_bugs.md`. Os 5 itens estruturais propostos na rev. 6.0 (M-15, M-16, M-18, M-19, M-20) foram verificados como entregues, um a um.*
