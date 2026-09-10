from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.access import (
    get_column_with_access,
    get_company_with_access,
    resolve_owner_user_id,
)
from app.core.policy import Action, assert_can
from app.db.session import get_db
from app.models.company_dashboard import (
    Company,
    Dashboard,
    DashboardCard,
    DashboardCardCategory,
)
from app.models.dashboard_board import (
    DashboardColumn,
    DashboardColumnKind,
    DashboardLabel,
)
from app.models.user import User
from app.schemas.dashboard_board import (
    BoardCardOut,
    BoardColumnOut,
    BoardOut,
    CardLabelsIn,
    CardMoveIn,
    CardUpdateIn,
    ColumnCreateIn,
    ColumnMoveIn,
    ColumnOut,
    ColumnUpdateIn,
    LabelRef,
)
from app.services import dashboard_card_history as history
from app.services.dashboard_board import (
    AnchorMismatchError,
    BoardData,
    ColumnKindError,
    ColumnNotEmptyError,
    ColumnNotFoundError,
    LabelNotFoundError,
    create_column,
    delete_column,
    get_board,
    move_card,
    move_column,
    set_card_labels,
    update_column,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard Board"])


def _get_card_with_access(
    db: Session, card_id: int, current_user: User
) -> DashboardCard:
    row = db.execute(
        select(DashboardCard, Company)
        .join(Dashboard, Dashboard.id == DashboardCard.dashboard_id)
        .join(Company, Company.id == Dashboard.company_id)
        .where(DashboardCard.id == card_id)
    ).first()
    if row is not None:
        card, company = row
        if current_user.role == "admin":
            return card
        if company.principal_user_id == resolve_owner_user_id(current_user):
            return card

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Card não encontrado ou sem acesso",
    )


def _label_refs(labels: list[DashboardLabel]) -> list[LabelRef]:
    return [
        LabelRef(id=label.id, name=label.name, color=label.color) for label in labels
    ]


def _card_out(card: DashboardCard, *, is_outdated: bool) -> BoardCardOut:
    return BoardCardOut(
        id=card.id,
        control_code=card.control_code,
        title=card.title,
        description=card.description,
        status=card.status.value,
        position=card.position,
        column_id=card.column_id,
        category_id=card.category_id,
        category_name=card.category.name if card.category else None,
        labels=_label_refs(card.labels),
        hidden=card.hidden,
        origin_template_card_id=card.origin_template_card_id,
        is_outdated=is_outdated,
    )


def _board_out(board: BoardData, company: Company) -> BoardOut:
    return BoardOut(
        dashboard_id=board.dashboard.id,
        company_id=company.id,
        title=board.dashboard.title,
        columns=[
            BoardColumnOut(
                id=grupo.column.id,
                name=grupo.column.name,
                kind=grupo.column.kind.value,
                position=grupo.column.position,
                hidden=grupo.column.hidden,
                wip_limit=grupo.column.wip_limit,
                cards=[
                    _card_out(card, is_outdated=card.id in board.outdated_card_ids)
                    for card in grupo.cards
                ],
                card_count=len(grupo.cards),
            )
            for grupo in board.columns
        ],
        uncolumned=[
            _card_out(card, is_outdated=card.id in board.outdated_card_ids)
            for card in board.uncolumned
        ],
        labels=_label_refs(board.labels),
    )


def _column_out(column: DashboardColumn) -> ColumnOut:
    return ColumnOut(
        id=column.id,
        name=column.name,
        kind=column.kind.value,
        position=column.position,
        hidden=column.hidden,
        wip_limit=column.wip_limit,
    )


# ------------------------------------------------------------- Leitura
@router.get("/companies/{company_id}/board", response_model=BoardOut)
def get_company_board(
    company_id: int,
    include_hidden: bool = Query(default=False),
    search: str = Query(default=""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BoardOut:
    """
    Quadro completo da empresa.

    Leitura permitida a **admin, user e sub-user** — é a mesma decisão de
    `list_cards_by_company`: o cliente tem direito de ver o quadro da
    própria empresa (U6/U7), só não de rearranjá-lo. Por isso a rota usa
    `get_company_with_access` e NÃO `require_admin`.

    Empresa sem dashboard devolve um quadro vazio, não 404: uma empresa
    antiga criada à mão pode não ter dashboard, e 404 aqui faria a tela do
    cliente quebrar em vez de mostrar "nada ainda".
    """
    company = get_company_with_access(db, company_id, current_user)

    dashboard = db.scalar(select(Dashboard).where(Dashboard.company_id == company.id))
    if dashboard is None:
        return BoardOut(
            dashboard_id=0,
            company_id=company.id,
            title=f"Dashboard - {company.name}",
            columns=[],
            uncolumned=[],
            labels=[],
        )

    board = get_board(db, dashboard, include_hidden=include_hidden, search=search)
    return _board_out(board, company)


# -------------------------------------------------------------- Colunas
@router.post(
    "/companies/{company_id}/columns",
    response_model=ColumnOut,
    status_code=status.HTTP_201_CREATED,
)
def create_board_column(
    company_id: int,
    payload: ColumnCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ColumnOut:
    assert_can(Action.MANAGE_COLUMN, current_user.role)
    # Chamada por efeito colateral: valida existência da empresa (404) e o
    # acesso do usuário a ela (403) antes de qualquer escrita.
    get_company_with_access(db, company_id, current_user)

    dashboard = db.scalar(select(Dashboard).where(Dashboard.company_id == company_id))
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Empresa sem dashboard")

    try:
        column = create_column(
            db,
            dashboard,
            name=payload.name,
            kind=DashboardColumnKind(payload.kind),
            after_column_id=payload.after_column_id,
        )
        db.commit()
    except ColumnNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))

    db.refresh(column)
    return _column_out(column)


@router.patch("/columns/{column_id}", response_model=ColumnOut)
def update_board_column(
    column_id: int,
    payload: ColumnUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ColumnOut:
    assert_can(Action.MANAGE_COLUMN, current_user.role)
    column = get_column_with_access(db, column_id, current_user)

    update_column(
        db,
        column,
        name=payload.name,
        hidden=payload.hidden,
        wip_limit=payload.wip_limit,
    )
    db.commit()
    db.refresh(column)
    return _column_out(column)


@router.patch("/columns/{column_id}/move", response_model=ColumnOut)
def move_board_column(
    column_id: int,
    payload: ColumnMoveIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ColumnOut:
    assert_can(Action.MANAGE_COLUMN, current_user.role)
    column = get_column_with_access(db, column_id, current_user)

    try:
        move_column(
            db,
            column,
            prev_column_id=payload.prev_column_id,
            next_column_id=payload.next_column_id,
        )
        db.commit()
    except AnchorMismatchError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))

    db.refresh(column)
    return _column_out(column)


@router.delete("/columns/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_board_column(
    column_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    assert_can(Action.MANAGE_COLUMN, current_user.role)
    column = get_column_with_access(db, column_id, current_user)

    try:
        delete_column(db, column)
        db.commit()
    except ColumnNotEmptyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


# -------------------------------------------------------------- Cards
@router.patch("/cards/{card_id}/move", response_model=BoardCardOut)
def move_board_card(
    card_id: int,
    payload: CardMoveIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> BoardCardOut:
    assert_can(Action.MOVE_CARD, current_user.role)
    card = _get_card_with_access(db, card_id, current_user)

    try:
        move_card(
            db,
            card,
            column_id=payload.column_id,
            prev_card_id=payload.prev_card_id,
            next_card_id=payload.next_card_id,
            actor=current_user,
        )
        db.commit()
    except ColumnNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
    except ColumnKindError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except AnchorMismatchError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))

    db.refresh(card)
    return _card_out(card, is_outdated=False)


@router.patch("/cards/{card_id}", response_model=BoardCardOut)
def update_board_card(
    card_id: int,
    payload: CardUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> BoardCardOut:
    assert_can(Action.EDIT_CARD, current_user.role)
    card = _get_card_with_access(db, card_id, current_user)

    categoria_nova: str | None = None
    if payload.category_id is not None:
        category = db.get(DashboardCardCategory, payload.category_id)
        if category is None:
            raise HTTPException(status_code=404, detail="Categoria não encontrada")
        card.tag = category.name
        categoria_nova = category.name

    # O estado anterior é lido ANTES das atribuições: o histórico registra
    # "de X para Y", e depois da atribuição o X não existe mais em lugar
    # nenhum. A categoria entra por NOME e não por id — "Categoria
    # alterada de 7 para 8" não diz nada a quem audita.
    #
    # O nome da categoria NOVA vem do objeto já buscado acima, e não de
    # `card.category` depois do flush: atribuir a FK (`card.category_id`)
    # não reatualiza a relação carregada, então ler `card.category` ali
    # devolveria o valor ANTIGO e a mudança de categoria passaria em
    # branco no histórico.
    anterior = {
        "Título": (card.title, payload.title),
        "Código do controle": (card.control_code, payload.control_code),
        "Descrição": (card.description, payload.description),
    }
    categoria_anterior = card.category.name if card.category else None

    card.title = payload.title
    card.description = payload.description
    card.control_code = payload.control_code
    card.category_id = payload.category_id
    db.flush()

    mudancas = [
        history.describe_change(campo, de, para)
        for campo, (de, para) in anterior.items()
        if (de or "") != (para or "")
    ]
    if categoria_anterior != categoria_nova:
        mudancas.append(
            history.category_changed(categoria_anterior, categoria_nova)
        )
    # PATCH que não mudou nada não é movimentação: salvar o formulário sem
    # editar campo nenhum não deve poluir o histórico.
    if mudancas:
        history.record(
            db, card.id, history.fields_changed(mudancas), current_user
        )

    db.commit()
    db.refresh(card)
    return _card_out(card, is_outdated=False)


@router.put("/cards/{card_id}/labels", response_model=list[LabelRef])
def replace_card_labels(
    card_id: int,
    payload: CardLabelsIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[LabelRef]:
    assert_can(Action.MANAGE_LABEL, current_user.role)
    card = _get_card_with_access(db, card_id, current_user)

    try:
        labels = set_card_labels(db, card, payload.label_ids)
        history.record(
            db,
            card.id,
            history.labels_changed([label.name for label in labels]),
            current_user,
        )
        db.commit()
    except LabelNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))

    return _label_refs(labels)
