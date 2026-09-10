from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.policy import Action, assert_can
from app.db.session import get_db
from app.models.dashboard_board import DashboardLabel
from app.models.user import User
from app.schemas.dashboard_labels import (
    DashboardLabelCreate,
    DashboardLabelOut,
    DashboardLabelUpdate,
)
from app.services.dashboard_board import (
    LabelInUseError,
    LabelNotFoundError,
    create_label,
    delete_label,
    list_labels,
    update_label,
)

router = APIRouter(prefix="/admin/dashboard-labels", tags=["Admin - Etiquetas de Card"])


def _to_out(label: DashboardLabel) -> DashboardLabelOut:
    return DashboardLabelOut(
        id=label.id, name=label.name, color=label.color, sort_order=label.sort_order
    )


@router.get("", response_model=list[DashboardLabelOut])
def list_dashboard_labels(
    db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> list[DashboardLabelOut]:
    return [_to_out(label) for label in list_labels(db)]


@router.post("", response_model=DashboardLabelOut, status_code=status.HTTP_201_CREATED)
def create_dashboard_label(
    payload: DashboardLabelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> DashboardLabelOut:
    assert_can(Action.MANAGE_LABEL, current_user.role)
    try:
        label = create_label(
            db, name=payload.name, color=payload.color, sort_order=payload.sort_order
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma etiqueta com esse nome",
        )
    return _to_out(label)


@router.patch("/{label_id}", response_model=DashboardLabelOut)
def update_dashboard_label(
    label_id: int,
    payload: DashboardLabelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> DashboardLabelOut:
    assert_can(Action.MANAGE_LABEL, current_user.role)
    try:
        label = update_label(
            db,
            label_id,
            name=payload.name,
            color=payload.color,
            sort_order=payload.sort_order,
        )
        db.commit()
    except LabelNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Etiqueta não encontrada")
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma etiqueta com esse nome",
        )
    return _to_out(label)


@router.delete("/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dashboard_label(
    label_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    assert_can(Action.MANAGE_LABEL, current_user.role)
    try:
        delete_label(db, label_id)
        db.commit()
    except LabelNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Etiqueta não encontrada")
    except LabelInUseError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
