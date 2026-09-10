from __future__ import annotations

"""
Importador one-shot do export JSON de um quadro do Trello para um
`DashboardTemplate`.

Script de uso pontual, no mesmo formato dos 8 seeds já existentes em
`backend/scripts/`. Roda com o banco configurado em `backend/.env`.

**Idempotente por nome de template.** Rodar duas vezes com o mesmo
`--template-name` não duplica coluna, card nem etiqueta: colunas casam
por nome dentro do template, cards casam por (coluna, título). O export
de referência não tem nenhum par (lista, título) repetido — foi
verificado — então esse casamento é exato.

O que é IGNORADO, e por quê: `actions[]` (527 eventos — histórico do
Trello não é histórico da plataforma, e importá-lo poluiria a trilha de
auditoria com atores que não existem aqui), `members[]`,
`memberships[]`, `prefs`, `limits`, `pluginData`, `checklists` (vazio no
export) e `customFields` (vazio).

Três decisões que o export real forçou, e que o PRD não previa:

1. **Listas arquivadas guardam 50 cards abertos.** O PRD supunha que as
   listas fechadas estivessem vazias ("6 listas, todas de fase
   encerrada"); no arquivo real são 9 listas fechadas com 50 cards
   abertos dentro. Ignorar as listas E os cards perderia 23 % do
   conteúdo em silêncio — o pior desfecho possível para um importador.
   A escolha: as listas fechadas NÃO viram coluna, e os cards delas
   entram com `template_column_id = NULL`, caindo no balde "Sem coluna"
   do quadro derivado, onde o auditor decide o destino. `--skip-archived-
   list-cards` descarta esses cards, se for essa a decisão — mas
   explicitamente, nunca por omissão.

2. **3 nomes de lista e 23 títulos de card estouram `String(160)`** (até
   264 e 471 caracteres). Sem tratamento, o INSERT falha no MySQL em
   modo estrito — e falharia só na metade da importação. Nomes de coluna
   são truncados. Títulos de card também, mas o título completo é
   PRESERVADO no início da `description`: o texto longo é a redação
   normativa do controle, e perdê-lo esvaziaria metade do valor do
   import.

3. **`pos` do Trello nunca é copiada.** O alfabeto é outro (float
   65 535 … 2 359 295 contra base-62 lexicográfica). A ordem RELATIVA é
   preservada e as chaves são regeradas com `n_keys_between`.
"""

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.company_dashboard import DashboardTemplate, DashboardTemplateCard
from app.models.dashboard_board import (
    DashboardColumnKind,
    DashboardLabel,
    DashboardTemplateColumn,
)
from app.services.fractional_index import n_keys_between

#: Espaçador invisível que o export usa entre parágrafos. Sobrevive a
#: qualquer `strip()` e aparece como caractere-fantasma na UI (CA-25).
ZERO_WIDTH_NON_JOINER = "‌"

#: `5.1 Política de SI` -> ("5.1", "Política de SI"). 144 dos 213 cards.
CONTROL_CODE_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+(.*)$", re.DOTALL)

#: Sufixo que marca a lista separadora do Trello (`ISO 27001:2022 >>`).
SECTION_SUFFIX = ">>"

MAX_NAME_LENGTH = 160
MAX_CONTROL_CODE_LENGTH = 40

#: As 8 etiquetas aprovadas em §2.1 do PRD, com o hex do tema
#: correspondente à cor nomeada do Trello. As três de fora, e o motivo:
#: `Concluído com evidência` é redundante com o status CONFORME (duas
#: fontes de verdade para "está conforme?" é exatamente o que B-A23
#: proíbe); `Não Aplicável` é status e não etiqueta (decisão D-2, no
#: backlog); `Entregue - Inove Educação` é específica de um cliente.
APPROVED_LABELS: dict[str, str] = {
    "Item Critico": "#96311D",
    "Alta Criticidade": "#C2410C",
    "Média Criticidade": "#A16207",
    "Baixa Criticidade": "#2C5A8C",
    "Aguardando empresa": "#0E7490",
    "Check-list": "#6D28D9",
    "Inserir doc atualizado no final do projeto": "#854D0E",
    "Final do projeto": "#1E3A8A",
}

REJECTED_LABELS = {
    "Concluído com evidência",
    "Não Aplicável",
    "Entregue - Inove Educação",
}


# ------------------------------------------------------------ Modelo


@dataclass
class ParsedColumn:
    trello_id: str
    name: str
    kind: DashboardColumnKind
    pos: float
    name_was_truncated: bool = False


@dataclass
class ParsedCard:
    trello_list_id: str | None
    control_code: str | None
    title: str
    description: str | None
    label_names: list[str]
    pos: float
    title_was_truncated: bool = False


@dataclass
class ParsedBoard:
    board_name: str
    columns: list[ParsedColumn] = field(default_factory=list)
    cards: list[ParsedCard] = field(default_factory=list)
    label_names: list[str] = field(default_factory=list)
    rejected_label_names: list[str] = field(default_factory=list)
    ignored_closed_lists: int = 0
    cards_from_closed_lists: int = 0


# ------------------------------------------------------------ Parsing


def normalize_whitespace(text: str) -> str:
    """
    Colapsa quebras de linha e espaços repetidos.

    Um nome de lista do export real tem `\\n` no meio ("Segurança de QR
    Codes dinâmicos -\\n A seção 4 …"). Sem isso, o nome da coluna
    quebraria a linha no meio do cabeçalho do quadro.
    """
    return re.sub(r"\s+", " ", text).strip()


def clean_description(desc: str | None) -> str | None:
    """
    Remove o `U+200C` (CA-25) e normaliza a pontuação Unicode do texto.

    87 das 146 descrições do export carregam esse caractere invisível
    como espaçador de parágrafo. `strip()` não o remove — ele não é
    espaço em branco para o Python — e ele viaja até o `<p>` da UI, onde
    aparece como um retângulo vazio em algumas fontes.

    O Markdown é preservado como texto: os `**Controle**` do export são o
    texto normativo, e reescrevê-los seria alterar a redação do controle.
    """
    if desc is None:
        return None
    texto = desc.replace(ZERO_WIDTH_NON_JOINER, "")
    # NFC junta acentos decompostos — o export mistura as duas formas, e
    # a comparação de idempotência por título depende de uma forma só.
    texto = unicodedata.normalize("NFC", texto)
    texto = texto.strip()
    return texto or None


def is_section(list_name: str) -> bool:
    """`ISO 27001:2022 >>` é separador, não coluna de trabalho."""
    return normalize_whitespace(list_name).endswith(SECTION_SUFFIX)


def split_control_code(name: str) -> tuple[str | None, str]:
    """
    Separa o prefixo numérico do título: `5.1 Política` -> ("5.1",
    "Política"). 144 dos 213 cards do export têm esse prefixo.

    Devolve `(None, nome)` quando não há prefixo — e é o comportamento
    correto: inventar um código para os outros 69 cards seria pior que
    deixá-los sem código.
    """
    limpo = normalize_whitespace(name)
    correspondencia = CONTROL_CODE_RE.match(limpo)
    if not correspondencia:
        return None, limpo

    codigo, titulo = correspondencia.group(1), correspondencia.group(2).strip()
    if not titulo or len(codigo) > MAX_CONTROL_CODE_LENGTH:
        # Card cujo nome é SÓ um número, ou código absurdamente longo:
        # melhor manter o nome inteiro como título.
        return None, limpo
    return codigo, titulo


def truncate(text: str, limit: int = MAX_NAME_LENGTH) -> tuple[str, bool]:
    """Trunca preservando um marcador visível de que houve corte."""
    if len(text) <= limit:
        return text, False
    return text[: limit - 1].rstrip() + "…", True


def parse_board(raw: dict) -> ParsedBoard:
    """
    Converte o JSON bruto em `ParsedBoard`. **Função pura** — nenhuma
    sessão de banco, nenhum I/O — é o que torna o `--dry-run` uma
    execução completa da lógica de conversão, e não uma simulação
    parecida com ela.
    """
    parsed = ParsedBoard(board_name=normalize_whitespace(raw.get("name", "")))

    listas_abertas = [lista for lista in raw.get("lists", []) if not lista.get("closed")]
    parsed.ignored_closed_lists = len(raw.get("lists", [])) - len(listas_abertas)

    ids_de_coluna: set[str] = set()
    for lista in sorted(listas_abertas, key=lambda item: item.get("pos", 0)):
        nome_normalizado = normalize_whitespace(lista.get("name", ""))
        nome, truncado = truncate(nome_normalizado)
        parsed.columns.append(
            ParsedColumn(
                trello_id=lista["id"],
                name=nome,
                kind=(
                    DashboardColumnKind.SECTION
                    if is_section(nome_normalizado)
                    else DashboardColumnKind.COLUMN
                ),
                pos=float(lista.get("pos", 0)),
                name_was_truncated=truncado,
            )
        )
        ids_de_coluna.add(lista["id"])

    etiquetas_por_id = {
        etiqueta["id"]: normalize_whitespace(etiqueta.get("name", ""))
        for etiqueta in raw.get("labels", [])
    }
    nomes_de_etiqueta = {
        nome for nome in etiquetas_por_id.values() if nome in APPROVED_LABELS
    }
    parsed.label_names = sorted(nomes_de_etiqueta)
    parsed.rejected_label_names = sorted(
        {
            nome
            for nome in etiquetas_por_id.values()
            if nome and nome not in APPROVED_LABELS
        }
    )

    for card in raw.get("cards", []):
        if card.get("closed"):
            continue

        id_da_lista = card.get("idList")
        de_lista_fechada = id_da_lista not in ids_de_coluna
        if de_lista_fechada:
            parsed.cards_from_closed_lists += 1

        codigo, titulo_completo = split_control_code(card.get("name", ""))
        titulo, titulo_truncado = truncate(titulo_completo)

        descricao = clean_description(card.get("desc"))
        if titulo_truncado:
            # O título longo É a redação do controle. Truncá-lo sem
            # preservá-lo em lugar nenhum perderia o conteúdo.
            prefixo = f"**{titulo_completo}**"
            descricao = f"{prefixo}\n\n{descricao}" if descricao else prefixo

        parsed.cards.append(
            ParsedCard(
                trello_list_id=None if de_lista_fechada else id_da_lista,
                control_code=codigo,
                title=titulo,
                description=descricao,
                label_names=[
                    etiquetas_por_id[label_id]
                    for label_id in card.get("idLabels", [])
                    if etiquetas_por_id.get(label_id) in APPROVED_LABELS
                ],
                pos=float(card.get("pos", 0)),
                title_was_truncated=titulo_truncado,
            )
        )

    parsed.cards.sort(key=lambda item: item.pos)
    return parsed


# ------------------------------------------------------------ Relatório


def render_plan(parsed: ParsedBoard) -> str:
    """Plano legível do que SERIA escrito — a saída do `--dry-run`."""
    secoes = [c for c in parsed.columns if c.kind == DashboardColumnKind.SECTION]
    com_descricao = [c for c in parsed.cards if c.description]
    com_codigo = [c for c in parsed.cards if c.control_code]
    com_etiqueta = [c for c in parsed.cards if c.label_names]
    titulos_truncados = [c for c in parsed.cards if c.title_was_truncated]
    nomes_truncados = [c for c in parsed.columns if c.name_was_truncated]
    sem_coluna = [c for c in parsed.cards if c.trello_list_id is None]

    linhas: list[str] = [
        f"Quadro de origem: {parsed.board_name}",
        "",
        f"Colunas a criar ........................ {len(parsed.columns)}",
        f"  das quais seções (>>) ................ {len(secoes)}",
        f"  com nome truncado em 160 caracteres .. {len(nomes_truncados)}",
        f"Listas arquivadas ignoradas ............ {parsed.ignored_closed_lists}",
        "",
        f"Cards a criar .......................... {len(parsed.cards)}",
        f"  com descrição ........................ {len(com_descricao)}",
        f"  com control_code ..................... {len(com_codigo)}",
        f"  com etiqueta ......................... {len(com_etiqueta)}",
        "  com título truncado (texto preservado",
        f"  no início da descrição) .............. {len(titulos_truncados)}",
        f"  SEM COLUNA (vinham de lista arquivada) {len(sem_coluna)}",
        "",
        f"Etiquetas a garantir ................... {len(parsed.label_names)}",
        f"  {', '.join(parsed.label_names)}",
        f"Etiquetas NÃO importadas ............... {len(parsed.rejected_label_names)}",
        f"  {', '.join(parsed.rejected_label_names)}",
        "",
        "Colunas, na ordem:",
    ]

    contagem_por_lista: dict[str, int] = {}
    for card in parsed.cards:
        if card.trello_list_id is not None:
            contagem_por_lista[card.trello_list_id] = (
                contagem_por_lista.get(card.trello_list_id, 0) + 1
            )

    for indice, coluna in enumerate(parsed.columns, start=1):
        marca = "§" if coluna.kind == DashboardColumnKind.SECTION else " "
        total = contagem_por_lista.get(coluna.trello_id, 0)
        linhas.append(f"  {indice:2d}. {marca} [{total:3d} cards] {coluna.name}")

    if sem_coluna:
        linhas += [
            "",
            "ATENÇÃO: os cards abaixo vinham de listas ARQUIVADAS no Trello e",
            "entrarão sem coluna (balde 'Sem coluna' do quadro). Use",
            "--skip-archived-list-cards para descartá-los em vez de importá-los.",
        ]
        for card in sem_coluna[:10]:
            linhas.append(f"  - {card.title[:90]}")
        if len(sem_coluna) > 10:
            linhas.append(f"  … e mais {len(sem_coluna) - 10}")

    # CA-25: nenhum U+200C pode sobreviver.
    residuos = sum(
        1 for card in parsed.cards if ZERO_WIDTH_NON_JOINER in (card.description or "")
    )
    linhas += ["", f"Descrições ainda com U+200C (tem de ser 0): {residuos}"]

    return "\n".join(linhas)


# ------------------------------------------------------------ Persistência


def ensure_labels(db: Session, nomes: list[str]) -> None:
    """Garante o vocabulário de etiquetas — sem duplicar o que já existe
    (a migration c8f1a3e57b90 já semeou as 8)."""
    existentes = {
        label.name
        for label in db.scalars(
            select(DashboardLabel).where(DashboardLabel.name.in_(nomes))
        ).all()
    }
    for ordem, nome in enumerate(nomes):
        if nome in existentes:
            continue
        db.add(
            DashboardLabel(
                name=nome, color=APPROVED_LABELS[nome], sort_order=ordem
            )
        )
    db.flush()


def persist(
    db: Session,
    parsed: ParsedBoard,
    template_name: str,
    *,
    skip_archived_list_cards: bool = False,
) -> dict[str, int]:
    """
    Escreve o template, as colunas e os cards. Idempotente por nome de
    template: uma segunda execução não cria nada.

    Não faz `commit` — quem controla a transação é `main()`, no mesmo
    padrão de camadas do resto do backend (B4).
    """
    contadores = {
        "template_criado": 0,
        "colunas_criadas": 0,
        "colunas_existentes": 0,
        "cards_criados": 0,
        "cards_existentes": 0,
        "cards_descartados": 0,
    }

    template = db.scalar(
        select(DashboardTemplate).where(DashboardTemplate.name == template_name)
    )
    if template is None:
        template = DashboardTemplate(
            name=template_name,
            description=f"Importado do quadro Trello '{parsed.board_name}'",
            is_default=False,
        )
        db.add(template)
        db.flush()
        contadores["template_criado"] = 1

    ensure_labels(db, parsed.label_names)

    # ---- Colunas ----
    colunas_existentes = {
        coluna.name: coluna
        for coluna in db.scalars(
            select(DashboardTemplateColumn).where(
                DashboardTemplateColumn.template_id == template.id
            )
        ).all()
    }

    faltantes = [c for c in parsed.columns if c.name not in colunas_existentes]
    coluna_por_trello_id: dict[str, DashboardTemplateColumn] = {}
    if faltantes:
        ultima = max(
            (c.position for c in colunas_existentes.values()), default=None
        )
        for coluna_parseada, position in zip(
            faltantes, n_keys_between(ultima, None, len(faltantes))
        ):
            nova = DashboardTemplateColumn(
                template_id=template.id,
                name=coluna_parseada.name,
                kind=coluna_parseada.kind,
                position=position,
            )
            db.add(nova)
            colunas_existentes[coluna_parseada.name] = nova
            contadores["colunas_criadas"] += 1
        db.flush()

    for coluna_parseada in parsed.columns:
        coluna_por_trello_id[coluna_parseada.trello_id] = colunas_existentes[
            coluna_parseada.name
        ]
    contadores["colunas_existentes"] = len(parsed.columns) - contadores["colunas_criadas"]

    # ---- Cards ----
    # Idempotência por (coluna, título). O export de referência não tem
    # nenhum par repetido — verificado antes de escolher esta chave.
    ja_existentes = {
        (card.template_column_id, card.title)
        for card in db.scalars(
            select(DashboardTemplateCard).where(
                DashboardTemplateCard.template_id == template.id
            )
        ).all()
    }

    a_criar: list[tuple[ParsedCard, int | None]] = []
    for card in parsed.cards:
        if card.trello_list_id is None:
            if skip_archived_list_cards:
                contadores["cards_descartados"] += 1
                continue
            column_id = None
        else:
            coluna = coluna_por_trello_id.get(card.trello_list_id)
            if coluna is None or coluna.kind == DashboardColumnKind.SECTION:
                # Card numa seção não deveria existir (o export tem zero),
                # mas se existir ele vai para o balde, nunca para dentro
                # de um separador.
                column_id = None
            else:
                column_id = coluna.id

        if (column_id, card.title) in ja_existentes:
            contadores["cards_existentes"] += 1
            continue
        ja_existentes.add((column_id, card.title))
        a_criar.append((card, column_id))

    # `position` regenerada POR COLUNA, na ordem relativa do `pos` do
    # Trello — nunca copiada (o alfabeto é outro).
    por_coluna: dict[int | None, list[tuple[ParsedCard, int | None]]] = {}
    for item in a_criar:
        por_coluna.setdefault(item[1], []).append(item)

    for column_id, itens in por_coluna.items():
        for ordem, ((card, _), position) in enumerate(
            zip(itens, n_keys_between(None, None, len(itens)))
        ):
            db.add(
                DashboardTemplateCard(
                    template_id=template.id,
                    title=card.title,
                    description=card.description,
                    tag="Sem categoria",
                    category_id=None,
                    template_column_id=column_id,
                    sort_order=ordem,
                    position=position,
                )
            )
            contadores["cards_criados"] += 1

    db.flush()
    return contadores


# ------------------------------------------------------------ CLI


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Importa um export JSON de quadro do Trello como template de "
            "dashboard. Idempotente por nome de template."
        )
    )
    parser.add_argument("arquivo", help="Caminho do export JSON do Trello")
    parser.add_argument(
        "--template-name",
        required=True,
        help="Nome do DashboardTemplate a criar/reaproveitar",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Imprime o plano e NÃO escreve nada no banco",
    )
    parser.add_argument(
        "--skip-archived-list-cards",
        action="store_true",
        help=(
            "Descarta os cards que vinham de listas arquivadas no Trello, em "
            "vez de importá-los sem coluna"
        ),
    )
    args = parser.parse_args()

    caminho = Path(args.arquivo)
    if not caminho.is_file():
        print(f"Arquivo não encontrado: {caminho}", file=sys.stderr)
        return 2

    raw = json.loads(caminho.read_text(encoding="utf-8"))
    parsed = parse_board(raw)

    print(render_plan(parsed))
    print()

    if args.dry_run:
        print("--dry-run: nada foi escrito no banco.")
        return 0

    with SessionLocal() as db:
        contadores = persist(
            db,
            parsed,
            args.template_name,
            skip_archived_list_cards=args.skip_archived_list_cards,
        )
        db.commit()

    print(f"Template '{args.template_name}':")
    for chave, valor in contadores.items():
        print(f"  {chave:.<26} {valor}")
    print("Importação concluída.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
