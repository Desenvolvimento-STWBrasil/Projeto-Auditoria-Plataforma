from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.jwt import create_access_token, create_refresh_token, decode_refresh_token
from app.core.security import PasswordTooLongError
from app.db.session import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserPublic,
)
from app.services.users import authenticate_user, create_user, get_user_by_email

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

limiter = Limiter(key_func=get_remote_address)


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserPublic:
    if not settings.ALLOW_PUBLIC_REGISTRATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registro público não permitido",
        )

    existing = get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado",
        )

    try:
        user = create_user(
            db,
            full_name=payload.full_name,
            email=payload.email,
            password=payload.password,
            role="user",
        )
    except PasswordTooLongError as exc:
        # Rede de segurança: o validador do schema já barra este caso.
        # Mantida porque create_user() é chamada também por outros caminhos.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )

    db.commit()
    db.refresh(user)

    return UserPublic(
        id=user.id, full_name=user.full_name, email=user.email, role=user.role
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(
    request: Request, payload: UserLogin, db: Session = Depends(get_db)
) -> TokenResponse:
    user = authenticate_user(db, email=payload.email, password=payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )

    access_token = create_access_token(subject=str(user.id), role=user.role)
    refresh_token = create_refresh_token(subject=str(user.id))
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
def refresh(
    request: Request, payload: RefreshTokenRequest, db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Troca um refresh_token válido por um novo par access_token/refresh_token,
    sem exigir email/senha de novo. Ver docs/plano_implementacao.md, item A.10.

    Limitação conhecida (MVP, sem infraestrutura de revogação): os tokens
    são stateless — não há blocklist/tabela de sessões no banco. O
    refresh_token antigo continua criptograficamente válido até sua
    própria expiração mesmo depois de "rotacionado" aqui; a rotação só
    reduz a janela de uso do token anterior no fluxo normal (o cliente
    passa a usar o novo), não revoga o antigo. Logout continua sendo
    apenas client-side (limpeza de cookies), como já era antes desta
    mudança.
    """
    try:
        decoded = decode_refresh_token(payload.refresh_token)
        user_id = int(decoded.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido ou expirado",
        )

    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
        )

    new_access_token = create_access_token(subject=str(user.id), role=user.role)
    new_refresh_token = create_refresh_token(subject=str(user.id))
    return TokenResponse(access_token=new_access_token, refresh_token=new_refresh_token)
