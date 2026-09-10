from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.company_dashboard import DashboardCardCategory
from app.models.user import User
from app.schemas.dashboard_templates import (
    DashboardCardCategoryCreate,
    DashboardCardCategoryOut,
    DashboardCardCategoryUpdate,
)
from app.services.dashboard_template_admin import (
    CategoryInUseError,
    CategoryNotFoundError,
    create_category,
    delete_category,
    list_categories,
    update_category,
)

router = APIRouter(
    prefix="/admin/dashboard-categories", tags=["Admin — Categorias de Card"]
)


def _to_out(category: DashboardCardCategory) -> DashboardCardCategoryOut:
    return DashboardCardCategoryOut(
        id=category.id,
        name=category.name,
        color=category.color,
        sort_order=category.sort_order,
    )


@router.get("", response_model=list[DashboardCardCategoryOut])
def list_dashboard_categories(
    db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> list[DashboardCardCategoryOut]:
    return [_to_out(c) for c in list_categories(db)]


@router.post(
    "", response_model=DashboardCardCategoryOut, status_code=status.HTTP_201_CREATED
)
def create_dashboard_category(
    payload: DashboardCardCategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DashboardCardCategoryOut:
    try:
        category = create_category(
            db, name=payload.name, color=payload.color, sort_order=payload.sort_order
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma categoria com esse nome",
        )
    return _to_out(category)


@router.patch("/{category_id}", response_model=DashboardCardCategoryOut)
def update_dashboard_category(
    category_id: int,
    payload: DashboardCardCategoryUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DashboardCardCategoryOut:
    try:
        category = update_category(
            db,
            category_id,
            name=payload.name,
            color=payload.color,
            sort_order=payload.sort_order,
        )
        db.commit()
    except CategoryNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma categoria com esse nome",
        )
    return _to_out(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dashboard_category(
    category_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> None:
    try:
        delete_category(db, category_id)
        db.commit()
    except CategoryNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    except CategoryInUseError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
