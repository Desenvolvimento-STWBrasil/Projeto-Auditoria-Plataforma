from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.access import resolve_owner_user_id
from app.db.session import get_db
from app.models.company_dashboard import Company
from app.models.user import User
from app.schemas.auth import UserPublic

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/perfil", response_model=UserPublic)
def perfil(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserPublic:
    company_name = None
    if current_user.role != "admin":
        owner_id = resolve_owner_user_id(current_user)
        company = db.execute(
            select(Company).where(Company.principal_user_id == owner_id)
        ).scalar_one_or_none()
        company_name = company.name if company else None

    return UserPublic(
        id=current_user.id,
        full_name=current_user.full_name,
        email=current_user.email,
        role=current_user.role,
        company_name=company_name,
    )