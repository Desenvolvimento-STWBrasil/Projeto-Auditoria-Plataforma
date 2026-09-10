from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.policy import Action, assert_can
from app.db.session import get_db
from app.models.company_dashboard import DashboardTemplateCard
from app.models.dashboard_board import DashboardColumnKind, DashboardTemplateColumn
from app.models.user import User
from app.schemas.dashboard_templates import (
    DashboardTemplateCardCreate,
    DashboardTemplateCardOut,
    DashboardTemplateCardUpdate,
    DashboardTemplateColumnCreate,
    DashboardTemplateColumnMove,
    DashboardTemplateColumnOut,
    DashboardTemplateColumnUpdate,
    DashboardTemplateCreate,
    DashboardTemplateDetailOut,
    DashboardTemplateOut,
    DashboardTemplateUpdate,
)
from app.services.dashboard_template_admin import (
    CategoryNotFoundError,
    DefaultTemplateDeletionError,
    TemplateCardNotFoundError,
    TemplateColumnInUseError,
    TemplateColumnNotFoundError,
    TemplateInUseError,
    TemplateNotFoundError,
    add_template_card,
    add_template_column,
    create_template,
    delete_template,
    delete_template_card,
    delete_template_column,
    get_template_detail,
    list_template_columns,
    list_templates,
    move_template_column,
    update_template,
    update_template_card,
    update_template_column,
)

router = APIRouter(prefix="/admin/templates", tags=["Admin — Templates de Dashboard"])


def _card_to_out(card: DashboardTemplateCard) -> DashboardTemplateCardOut:
    return DashboardTemplateCardOut(
        id=card.id,
        title=card.title,
        description=card.description,
        category_id=card.category_id,
        category_name=card.category.name if card.category else None,
        template_column_id=card.template_column_id,
        position=card.position,
        sort_order=card.sort_order,
    )


def _column_to_out(
    column: DashboardTemplateColumn, card_count: int
) -> DashboardTemplateColumnOut:
    return DashboardTemplateColumnOut(
        id=column.id,
        name=column.name,
        kind=column.kind.value,
        position=column.position,
        card_count=card_count,
    )


def _build_detail(template) -> DashboardTemplateDetailOut:
    # A ordenação primária é `position` (a do quadro); `sort_order` entra
    # como desempate para os templates anteriores à migration
    # c8f1a3e57b90, cujas posições foram todas geradas no mesmo backfill.
    cards = sorted(template.cards, key=lambda c: (c.position, c.sort_order, c.id))
    colunas = sorted(template.columns, key=lambda c: (c.position, c.id))

    cards_por_coluna: dict[int, int] = {}
    for card in cards:
        if card.template_column_id is not None:
            cards_por_coluna[card.template_column_id] = (
                cards_por_coluna.get(card.template_column_id, 0) + 1
            )

    return DashboardTemplateDetailOut(
        id=template.id,
        name=template.name,
        description=template.description,
        is_default=template.is_default,
        card_count=len(cards),
        cards=[_card_to_out(c) for c in cards],
        columns=[
            _column_to_out(coluna, cards_por_coluna.get(coluna.id, 0))
            for coluna in colunas
        ],
    )


@router.get("", response_model=list[DashboardTemplateOut])
def list_dashboard_templates(
    db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> list[DashboardTemplateOut]:
    rows = list_templates(db)
    return [
        DashboardTemplateOut(
            id=row.template.id,
            name=row.template.name,
            description=row.template.description,
            is_default=row.template.is_default,
            card_count=row.card_count,
        )
        for row in rows
    ]


@router.post(
    "", response_model=DashboardTemplateOut, status_code=status.HTTP_201_CREATED
)
def create_dashboard_template(
    payload: DashboardTemplateCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DashboardTemplateOut:
    try:
        template = create_template(
            db,
            name=payload.name,
            description=payload.description,
            is_default=payload.is_default,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um template com esse nome",
        )
    return DashboardTemplateOut(
        id=template.id,
        name=template.name,
        description=template.description,
        is_default=template.is_default,
        card_count=0,
    )


@router.get("/{template_id}", response_model=DashboardTemplateDetailOut)
def get_dashboard_template(
    template_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DashboardTemplateDetailOut:
    try:
        template = get_template_detail(db, template_id)
    except TemplateNotFoundError:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    return _build_detail(template)


@router.patch("/{template_id}", response_model=DashboardTemplateDetailOut)
def update_dashboard_template(
    template_id: int,
    payload: DashboardTemplateUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DashboardTemplateDetailOut:
    try:
        template = update_template(
            db,
            template_id,
            name=payload.name,
            description=payload.description,
            is_default=payload.is_default,
        )
        db.commit()
    except TemplateNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Template não encontrado")
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um template com esse nome",
        )
    db.refresh(template)
    return _build_detail(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dashboard_template(
    template_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    try:
        delete_template(db, template_id)
        db.commit()
    except TemplateNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Template não encontrado")
    except (DefaultTemplateDeletionError, TemplateInUseError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


# ------------------------------------------------- Colunas de template


@router.get("/{template_id}/columns", response_model=list[DashboardTemplateColumnOut])
def list_dashboard_template_columns(
    template_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[DashboardTemplateColumnOut]:
    try:
        template = get_template_detail(db, template_id)
    except TemplateNotFoundError:
        raise HTTPException(status_code=404, detail="Template não encontrado")

    cards_por_coluna: dict[int, int] = {}
    for card in template.cards:
        if card.template_column_id is not None:
            cards_por_coluna[card.template_column_id] = (
                cards_por_coluna.get(card.template_column_id, 0) + 1
            )

    return [
        _column_to_out(coluna, cards_por_coluna.get(coluna.id, 0))
        for coluna in list_template_columns(db, template_id)
    ]


@router.post(
    "/{template_id}/columns",
    response_model=DashboardTemplateColumnOut,
    status_code=status.HTTP_201_CREATED,
)
def create_dashboard_template_column(
    template_id: int,
    payload: DashboardTemplateColumnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> DashboardTemplateColumnOut:
    assert_can(Action.MANAGE_TEMPLATE, current_user.role)
    try:
        coluna = add_template_column(
            db,
            template_id,
            name=payload.name,
            kind=DashboardColumnKind(payload.kind),
        )
        db.commit()
    except TemplateNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Template não encontrado")
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma coluna com esse nome neste template",
        )
    db.refresh(coluna)
    return _column_to_out(coluna, 0)


@router.patch(
    "/{template_id}/columns/{column_id}",
    response_model=DashboardTemplateColumnOut,
)
def update_dashboard_template_column(
    template_id: int,
    column_id: int,
    payload: DashboardTemplateColumnUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> DashboardTemplateColumnOut:
    assert_can(Action.MANAGE_TEMPLATE, current_user.role)
    try:
        coluna = update_template_column(
            db,
            column_id,
            name=payload.name,
            kind=DashboardColumnKind(payload.kind),
        )
        if coluna.template_id != template_id:
            db.rollback()
            raise HTTPException(
                status_code=404, detail="Coluna de template não encontrada"
            )
        db.commit()
    except TemplateColumnNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Coluna de template não encontrada")
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma coluna com esse nome neste template",
        )
    db.refresh(coluna)
    return _column_to_out(coluna, 0)


@router.patch(
    "/{template_id}/columns/{column_id}/move",
    response_model=DashboardTemplateColumnOut,
)
def move_dashboard_template_column(
    template_id: int,
    column_id: int,
    payload: DashboardTemplateColumnMove,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> DashboardTemplateColumnOut:
    assert_can(Action.MANAGE_TEMPLATE, current_user.role)
    try:
        coluna = move_template_column(
            db,
            column_id,
            prev_column_id=payload.prev_column_id,
            next_column_id=payload.next_column_id,
        )
        if coluna.template_id != template_id:
            db.rollback()
            raise HTTPException(
                status_code=404, detail="Coluna de template não encontrada"
            )
        db.commit()
    except TemplateColumnNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Coluna de template não encontrada")
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    db.refresh(coluna)
    return _column_to_out(coluna, 0)


@router.delete(
    "/{template_id}/columns/{column_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_dashboard_template_column(
    template_id: int,
    column_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    assert_can(Action.MANAGE_TEMPLATE, current_user.role)
    coluna = db.get(DashboardTemplateColumn, column_id)
    if coluna is None or coluna.template_id != template_id:
        raise HTTPException(status_code=404, detail="Coluna de template não encontrada")

    try:
        delete_template_column(db, column_id)
        db.commit()
    except TemplateColumnNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Coluna de template não encontrada")
    except TemplateColumnInUseError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


# --------------------------------------------------- Cards de template


@router.post(
    "/{template_id}/cards",
    response_model=DashboardTemplateCardOut,
    status_code=status.HTTP_201_CREATED,
)
def create_dashboard_template_card(
    template_id: int,
    payload: DashboardTemplateCardCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DashboardTemplateCardOut:
    try:
        card = add_template_card(
            db,
            template_id,
            title=payload.title,
            description=payload.description,
            category_id=payload.category_id,
            template_column_id=payload.template_column_id,
            sort_order=payload.sort_order,
        )
        db.commit()
    except TemplateNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Template não encontrado")
    except CategoryNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    except TemplateColumnNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Coluna de template não encontrada")
    db.refresh(card)
    return _card_to_out(card)


@router.delete(
    "/template-cards/{template_card_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_dashboard_template_card(
    template_card_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    try:
        delete_template_card(db, template_card_id)
        db.commit()
    except TemplateCardNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Card de template não encontrado")
    except TemplateInUseError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.patch(
    "/template-cards/{template_card_id}", response_model=DashboardTemplateCardOut
)
def update_dashboard_template_card(
    template_card_id: int,
    payload: DashboardTemplateCardUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DashboardTemplateCardOut:
    try:
        card = update_template_card(
            db,
            template_card_id,
            title=payload.title,
            description=payload.description,
            category_id=payload.category_id,
            template_column_id=payload.template_column_id,
            sort_order=payload.sort_order,
        )
        db.commit()
    except TemplateCardNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Card de template não encontrado")
    except CategoryNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    except TemplateColumnNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Coluna de template não encontrada")
    db.refresh(card)
    return _card_to_out(card)
