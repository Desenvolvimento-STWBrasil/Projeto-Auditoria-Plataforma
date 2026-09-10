from __future__ import annotations

"""
Regra de negócio do quadro: montar, criar/mover/arquivar coluna, mover
card e etiquetar.

Segue as camadas já praticadas na base (B4): este módulo chama
`db.flush()` e **nunca** `db.commit()` — quem controla a transação é o
router, que é também quem traduz as exceções de domínio daqui para
status HTTP. Cada exceção existe para uma regra, e a docstring dela
explica a decisão, não a mecânica (B5).
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.company_dashboard import Dashboard, DashboardCard
from app.models.user import User
from app.services import dashboard_card_history as history
from app.models.dashboard_board import (
    DashboardColumn,
    DashboardColumnKind,
    DashboardLabel,
)
from app.services.fractional_index import key_between


class ColumnNotFoundError(Exception):
    """
    Coluna inexistente, ou de outro quadro — o router converte para 404
    nos dois casos.

    Não são dois erros diferentes de propósito: distinguir "não existe" de
    "existe e não é sua" permitiria enumerar as colunas da plataforma
    inteira (B-B23).
    """


class ColumnNotEmptyError(Exception):
    """
    Tentativa de excluir coluna que ainda tem card não-oculto — o router
    converte para 409.

    Regra deliberadamente simples, a mesma de `CategoryInUseError`:
    exclusão **bloqueada**, não em cascata. Perder a posição (e, com a FK
    `SET NULL`, o agrupamento) de dezenas de cards por um clique errado é
    pior que exigir um passo a mais do admin — mover os cards para outra
    coluna antes de excluir a antiga.

    Cards OCULTOS não contam. Um card oculto já não é trabalho em aberto
    aos olhos do resumo (mesma decisão de O.4 em
    `get_dashboard_status_summary`), e exigir reexibir 30 cards
    arquivados só para poder apagar uma coluna vazia seria burocracia sem
    ganho.
    """


class ColumnKindError(Exception):
    """
    Tentativa de soltar um card numa coluna `SECTION` — o router converte
    para 422.

    `SECTION` é a lista separadora do Trello (`ISO 27001:2022 >>`):
    existe para dividir o quadro em blocos normativos e, por definição,
    não tem cards. Aceitar o card aqui produziria um card invisível, já
    que a UI renderiza `SECTION` como divisor e não como área de soltar.
    """


class AnchorMismatchError(Exception):
    """
    Âncora (`prev_card_id` / `next_card_id`) que não pertence à coluna de
    destino, ou que está fora de ordem — o router converte para 422.

    Fecha a classe inteira de bugs em que o cliente manda âncoras
    inconsistentes e o servidor gera, em silêncio, uma chave fora de
    ordem — o pior tipo de defeito desta funcionalidade, porque não
    produz erro nenhum na hora: o card só aparece no lugar errado na
    próxima leitura do quadro.
    """


class LabelNotFoundError(Exception):
    """Etiqueta inexistente — o router converte para 404."""


class LabelInUseError(Exception):
    """
    Etiqueta ainda vinculada a algum card — o router converte para 409.
    Mesma regra e mesma razão de `CategoryInUseError`.
    """


@dataclass
class BoardColumnData:
    """Uma coluna do quadro com os cards que caem dentro dela."""

    column: DashboardColumn
    cards: list[DashboardCard]


@dataclass
class BoardData:
    """
    Quadro pronto para serialização: colunas ordenadas, cards agrupados,
    balde dos cards sem coluna e o vocabulário de etiquetas.

    `outdated_card_ids` vem calculado daqui porque a comparação com o
    template precisa saber de que coluna de template a coluna atual
    nasceu — informação que já está carregada aqui e que o router teria
    de reconsultar.
    """

    dashboard: Dashboard
    columns: list[BoardColumnData]
    uncolumned: list[DashboardCard]
    labels: list[DashboardLabel]
    outdated_card_ids: set[int]


# ------------------------------------------------------------- Leitura


def _card_is_outdated(
    card: DashboardCard, origin_column_by_column_id: dict[int, int | None]
) -> bool:
    """
    O card divergiu da definição de template da qual nasceu?

    Compara título, categoria, descrição e **coluna**. A comparação de
    coluna não é `card.column_id != origin.template_column_id` — esses
    dois números vivem em tabelas diferentes (`dashboard_columns` e
    `dashboard_template_columns`) e compará-los diretamente daria
    "desatualizado" para todo card. O que se compara é a ORIGEM da coluna
    atual do card com a coluna de template declarada no card de template.
    """
    if card.origin_template_card_id is None or card.origin_template_card is None:
        return False
    origin = card.origin_template_card

    coluna_de_origem = (
        origin_column_by_column_id.get(card.column_id)
        if card.column_id is not None
        else None
    )

    return (
        card.title != origin.title
        or card.category_id != origin.category_id
        or (card.description or "") != (origin.description or "")
        or coluna_de_origem != origin.template_column_id
    )


def get_board(
    db: Session,
    dashboard: Dashboard,
    *,
    include_hidden: bool = False,
    search: str = "",
) -> BoardData:
    """
    Monta o quadro inteiro num número CONSTANTE de queries (CA-13),
    independentemente de quantas colunas o quadro tem: uma para as
    colunas, uma para os cards, três `selectinload` (etiquetas,
    categoria, card de template de origem) e uma para o vocabulário de
    etiquetas. O agrupamento é feito em memória.

    Foi para isto que a montagem migrou do cliente React para o servidor
    (D-5 do PRD): com colunas persistidas, repetir a lógica de ordenação
    em dois lugares garantiria que os dois divergissem.

    Cards com `column_id IS NULL` — órfãos de uma coluna excluída, pela FK
    `SET NULL` — vão para `uncolumned` em vez de sumir do quadro.
    """
    colunas_stmt = select(DashboardColumn).where(
        DashboardColumn.dashboard_id == dashboard.id
    )
    if not include_hidden:
        colunas_stmt = colunas_stmt.where(DashboardColumn.hidden.is_(False))
    colunas = list(
        db.scalars(
            colunas_stmt.order_by(
                DashboardColumn.position.asc(), DashboardColumn.id.asc()
            )
        ).all()
    )

    cards_stmt = select(DashboardCard).where(DashboardCard.dashboard_id == dashboard.id)
    if not include_hidden:
        cards_stmt = cards_stmt.where(DashboardCard.hidden.is_(False))
    termo = search.strip()
    if termo:
        padrao = f"%{termo}%"
        cards_stmt = cards_stmt.where(
            (DashboardCard.title.ilike(padrao))
            | (DashboardCard.control_code.ilike(padrao))
        )

    cards = list(
        db.scalars(
            cards_stmt.options(
                # Sem estes três, o quadro real (215 cards) faria 645
                # queries extras (B9).
                selectinload(DashboardCard.labels),
                selectinload(DashboardCard.category),
                selectinload(DashboardCard.origin_template_card),
            ).order_by(DashboardCard.position.asc(), DashboardCard.id.asc())
        ).all()
    )

    etiquetas = list(
        db.scalars(
            select(DashboardLabel).order_by(
                DashboardLabel.sort_order.asc(), DashboardLabel.name.asc()
            )
        ).all()
    )

    por_coluna: dict[int, list[DashboardCard]] = {coluna.id: [] for coluna in colunas}
    sem_coluna: list[DashboardCard] = []
    for card in cards:
        destino = por_coluna.get(card.column_id) if card.column_id is not None else None
        if destino is None:
            # column_id NULL, ou coluna arquivada e não pedida: o card
            # não pode simplesmente desaparecer do quadro.
            sem_coluna.append(card)
        else:
            destino.append(card)

    origem_por_coluna = {
        coluna.id: coluna.origin_template_column_id for coluna in colunas
    }
    desatualizados = {
        card.id for card in cards if _card_is_outdated(card, origem_por_coluna)
    }

    return BoardData(
        dashboard=dashboard,
        columns=[
            BoardColumnData(column=coluna, cards=por_coluna[coluna.id])
            for coluna in colunas
        ],
        uncolumned=sem_coluna,
        labels=etiquetas,
        outdated_card_ids=desatualizados,
    )


# -------------------------------------------------------------- Colunas


def _column_of_dashboard(
    db: Session, column_id: int, dashboard_id: int
) -> DashboardColumn:
    coluna = db.get(DashboardColumn, column_id)
    if coluna is None or coluna.dashboard_id != dashboard_id:
        raise ColumnNotFoundError("Coluna não encontrada")
    return coluna


def create_column(
    db: Session,
    dashboard: Dashboard,
    *,
    name: str,
    kind: DashboardColumnKind = DashboardColumnKind.COLUMN,
    after_column_id: int | None = None,
) -> DashboardColumn:
    """
    Cria uma coluna depois de `after_column_id`, ou no fim do quadro se
    ele for `None`.
    """
    colunas = list(
        db.scalars(
            select(DashboardColumn)
            .where(DashboardColumn.dashboard_id == dashboard.id)
            .order_by(DashboardColumn.position.asc(), DashboardColumn.id.asc())
        ).all()
    )

    if after_column_id is None:
        anterior = colunas[-1].position if colunas else None
        seguinte = None
    else:
        indices = [i for i, c in enumerate(colunas) if c.id == after_column_id]
        if not indices:
            raise ColumnNotFoundError("Coluna de referência não encontrada")
        indice = indices[0]
        anterior = colunas[indice].position
        seguinte = colunas[indice + 1].position if indice + 1 < len(colunas) else None

    coluna = DashboardColumn(
        dashboard_id=dashboard.id,
        name=name,
        kind=kind,
        position=key_between(anterior, seguinte),
    )
    db.add(coluna)
    db.flush()
    return coluna


def update_column(
    db: Session,
    column: DashboardColumn,
    *,
    name: str,
    hidden: bool,
    wip_limit: int | None,
) -> DashboardColumn:
    """Renomear / arquivar / limitar WIP. Não mexe em `position`."""
    column.name = name
    column.hidden = hidden
    column.wip_limit = wip_limit
    db.flush()
    return column


def move_column(
    db: Session,
    column: DashboardColumn,
    *,
    prev_column_id: int | None,
    next_column_id: int | None,
) -> DashboardColumn:
    """
    Reordena a coluna. As âncoras são lidas DENTRO da transação e a chave
    é calculada aqui — o cliente nunca inventa chave (§4.2 do PRD).
    """
    anterior = _column_anchor_position(db, prev_column_id, column)
    seguinte = _column_anchor_position(db, next_column_id, column)

    try:
        column.position = key_between(anterior, seguinte)
    except ValueError as exc:
        raise AnchorMismatchError(
            "Âncoras de posição de coluna inconsistentes"
        ) from exc

    db.flush()
    return column


def _column_anchor_position(
    db: Session, anchor_id: int | None, column: DashboardColumn
) -> str | None:
    if anchor_id is None:
        return None
    ancora = db.get(DashboardColumn, anchor_id)
    if (
        ancora is None
        or ancora.dashboard_id != column.dashboard_id
        or ancora.id == column.id
    ):
        raise AnchorMismatchError("Âncora de coluna não pertence a este quadro")
    return ancora.position


def delete_column(db: Session, column: DashboardColumn) -> None:
    em_uso = (
        db.scalar(
            select(func.count(DashboardCard.id)).where(
                DashboardCard.column_id == column.id,
                DashboardCard.hidden.is_(False),
            )
        )
        or 0
    )
    if em_uso > 0:
        raise ColumnNotEmptyError(
            f"Coluna com {em_uso} card(s) visível(is). Mova-os para outra coluna "
            "antes de excluir esta."
        )

    db.delete(column)
    db.flush()


# ---------------------------------------------------------- Mover card


def _card_anchor_position(
    db: Session,
    anchor_id: int | None,
    card: DashboardCard,
    destino_column_id: int | None,
) -> str | None:
    if anchor_id is None:
        return None
    ancora = db.get(DashboardCard, anchor_id)
    if (
        ancora is None
        or ancora.id == card.id
        or ancora.dashboard_id != card.dashboard_id
        or ancora.column_id != destino_column_id
    ):
        raise AnchorMismatchError("Âncora de posição não pertence à coluna de destino")
    return ancora.position


def move_card(
    db: Session,
    card: DashboardCard,
    *,
    column_id: int | None,
    prev_card_id: int | None,
    next_card_id: int | None,
    actor: User | None = None,
) -> DashboardCard:
    """
    O núcleo da funcionalidade. Valida três coisas, nesta ordem, e depois
    faz **exatamente um UPDATE** (CA-06):

    1. A coluna de destino é do MESMO quadro do card (senão 404 — nunca
       403, nunca 200 silencioso).
    2. A coluna de destino não é `SECTION`.
    3. As duas âncoras pertencem à coluna de destino e estão em ordem.

    Nenhum outro card é reescrito — é a propriedade que justifica o
    índice fracionário existir.
    """
    coluna: DashboardColumn | None = None
    if column_id is not None:
        coluna = _column_of_dashboard(db, column_id, card.dashboard_id)
        if coluna.kind == DashboardColumnKind.SECTION:
            raise ColumnKindError(
                "Coluna do tipo seção não aceita cards — ela é um separador visual"
            )

    destino_id = coluna.id if coluna is not None else None

    anterior = _card_anchor_position(db, prev_card_id, card, destino_id)
    seguinte = _card_anchor_position(db, next_card_id, card, destino_id)

    try:
        nova_position = key_between(anterior, seguinte)
    except ValueError as exc:
        raise AnchorMismatchError("Âncoras de posição inconsistentes") from exc

    # Nome da coluna de origem lido ANTES da atribuição, pelo mesmo motivo
    # de sempre: depois dela, "de onde veio" não existe mais.
    origem_id = card.column_id
    nome_de_origem = card.column.name if card.column is not None else None
    nome_de_destino = coluna.name if coluna is not None else None

    card.column_id = destino_id
    card.position = nova_position
    db.flush()

    # Trocar de coluna e reordenar dentro dela são movimentações
    # diferentes aos olhos de quem audita: a primeira muda o andamento do
    # controle, a segunda é só arrumação visual. Registrar as duas com o
    # mesmo texto ("Card movido") tornaria o histórico do quadro real
    # ilegível, porque arrastar é a interação mais frequente que existe
    # aqui.
    if origem_id != destino_id:
        history.record(
            db,
            card.id,
            history.column_changed(nome_de_origem, nome_de_destino),
            actor,
        )
    else:
        history.record(
            db,
            card.id,
            history.reordered_within_column(nome_de_destino),
            actor,
        )
    return card


# ------------------------------------------------------------ Etiquetas


def set_card_labels(
    db: Session, card: DashboardCard, label_ids: list[int]
) -> list[DashboardLabel]:
    """
    Substitui o CONJUNTO inteiro de etiquetas do card — semântica de
    `PUT`, não de `PATCH`.

    Todos os ids são validados ANTES de tocar no vínculo: uma lista com
    um id inválido no meio não pode deixar o card com metade das
    etiquetas aplicadas.

    Não toca em `status` sob nenhuma circunstância (CA-12). Etiqueta é
    criticidade; status é a declaração do auditor sobre conformidade
    (B-A23). São eixos ortogonais e continuam sendo.
    """
    unicos = list(dict.fromkeys(label_ids))
    if not unicos:
        card.labels = []
        db.flush()
        return []

    etiquetas = list(
        db.scalars(select(DashboardLabel).where(DashboardLabel.id.in_(unicos))).all()
    )
    encontrados = {etiqueta.id for etiqueta in etiquetas}
    faltando = [label_id for label_id in unicos if label_id not in encontrados]
    if faltando:
        raise LabelNotFoundError(
            f"Etiqueta(s) não encontrada(s): {', '.join(str(i) for i in faltando)}"
        )

    ordenadas = sorted(etiquetas, key=lambda e: (e.sort_order, e.name))
    card.labels = ordenadas
    db.flush()
    return ordenadas


def list_labels(db: Session) -> list[DashboardLabel]:
    return list(
        db.scalars(
            select(DashboardLabel).order_by(
                DashboardLabel.sort_order.asc(), DashboardLabel.name.asc()
            )
        ).all()
    )


def create_label(
    db: Session, *, name: str, color: str, sort_order: int
) -> DashboardLabel:
    label = DashboardLabel(name=name, color=color, sort_order=sort_order)
    db.add(label)
    db.flush()
    return label


def update_label(
    db: Session, label_id: int, *, name: str, color: str, sort_order: int
) -> DashboardLabel:
    label = db.get(DashboardLabel, label_id)
    if label is None:
        raise LabelNotFoundError("Etiqueta não encontrada")
    label.name = name
    label.color = color
    label.sort_order = sort_order
    db.flush()
    return label


def delete_label(db: Session, label_id: int) -> None:
    label = db.get(DashboardLabel, label_id)
    if label is None:
        raise LabelNotFoundError("Etiqueta não encontrada")

    em_uso = (
        db.scalar(
            select(func.count(DashboardCard.id))
            .select_from(DashboardCard)
            .join(DashboardCard.labels)
            .where(DashboardLabel.id == label_id)
        )
        or 0
    )
    if em_uso > 0:
        raise LabelInUseError(f"Etiqueta em uso por {em_uso} card(s)")

    db.delete(label)
    db.flush()
