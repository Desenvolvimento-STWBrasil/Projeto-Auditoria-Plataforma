from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import UserPublic

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/perfil", response_model=UserPublic)
def perfil(current_user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic(
        id=current_user.id,
        full_name=current_user.full_name,
        email=current_user.email,
        role=current_user.role
    )