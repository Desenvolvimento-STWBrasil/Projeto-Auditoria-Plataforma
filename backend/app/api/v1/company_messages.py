from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status


from app.api.deps import get_current_user
from app.core.access import get_company_with_access, resolve_owner_user_id
from app.db.session import get_db
from app.models.company_dashboard import Company
from app.models.company_message import CompanyMessage
from app.models.user import User
from app.schemas.company_message import (
    CompanyMessageAuthorOut,
    CompanyMessageCreate,
    CompanyMessageOut,
    CompanyOut,
)

router = APIRouter(prefix="/companies", tags=["Company Messages"])


def _to_out(message: CompanyMessage) -> CompanyMessageOut:
    return CompanyMessageOut(
        id=message.id,
        content=message.content,
        created_at=message.created_at,
        read_at=message.read_at,
        is_from_admin=message.author_user.role == "admin",
        author=CompanyMessageAuthorOut(
            id=message.author_user.id,
            full_name=message.author_user.full_name,
            role=message.author_user.role,
        ),
    )


@router.get("/me", response_model=CompanyOut)
def get_my_company(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyOut:
    """
    Retorna a empresa do usuário logado (user/sub-user). Necessário porque
    hoje nenhum endpoint client-facing expõe company_id — GET /client/
    controls retorna dados de auditoria, sem nenhuma referência à empresa.
    Usado por /private/client/mensagens para saber com qual company_id
    chamar GET/POST /companies/{id}/messages.
    """

    if current_user.role not in ("user", "sub-user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Endpoint apenas para user/sub-user",
        )
    owner_user_id = resolve_owner_user_id(current_user)
    company = db.scalar(
        select(Company).where(Company.principal_user_id == owner_user_id)
    )
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada para este usuário",
        )
    return CompanyOut(id=company.id, name=company.name)


@router.get("/unread-count")
def count_all_unread_company_messages(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Agrega o total de mensagens não lidas de TODAS as empresas — alimenta
    o badge de "Mensagens" no menu superior do admin. Restrito a admin:
    cliente/sub-usuário só enxergam a própria empresa, já cobertos por
    `count_unread_company_messages` (por company_id).
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Endpoint restrito a admin"
        )

    stmt = (
        select(func.count(CompanyMessage.id))
        .join(User, User.id == CompanyMessage.author_user_id)
        .where(CompanyMessage.read_at.is_(None), User.role != "admin")
    )
    count = db.scalar(stmt) or 0
    return {"unread_count": count}


@router.get("/{company_id}/messages", response_model=list[CompanyMessageOut])
def list_company_messages(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CompanyMessageOut]:
    company = get_company_with_access(db, company_id, current_user)

    messages = db.scalars(
        select(CompanyMessage)
        .where(CompanyMessage.company_id == company.id)
        .order_by(CompanyMessage.created_at.asc())
    ).all()

    return [_to_out(message) for message in messages]


@router.post(
    "/{company_id}/messages",
    response_model=CompanyMessageOut,
    status_code=status.HTTP_201_CREATED,
)
def send_company_message(
    company_id: int,
    payload: CompanyMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyMessageOut:
    company = get_company_with_access(db, company_id, current_user)

    message = CompanyMessage(
        company_id=company.id,
        author_user_id=current_user.id,
        content=payload.content.strip(),
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    return _to_out(message)


@router.patch("/{company_id}/messages/read", status_code=status.HTTP_200_OK)
def mark_company_messages_as_read(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Marca como lidas todas as mensagens do "outro lado" da conversa — se
    quem chama é admin, marca as mensagens que o cliente escreveu (e
    vice-versa). Chamado ao abrir/trocar a empresa selecionada na tela de
    mensagens.
    """
    company = get_company_with_access(db, company_id, current_user)
    is_admin = current_user.role == "admin"

    other_side_filter = (User.role != "admin") if is_admin else (User.role == "admin")

    stmt = (
        select(CompanyMessage)
        .join(User, User.id == CompanyMessage.author_user_id)
        .where(
            CompanyMessage.company_id == company.id,
            CompanyMessage.read_at.is_(None),
            other_side_filter,
        )
    )
    unread = db.scalars(stmt).all()
    for message in unread:
        message.read_at = func.now()

    db.commit()
    return {"marked_as_read": len(unread)}


@router.get("/{company_id}/messages/unread-count")
def count_unread_company_messages(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    company = get_company_with_access(db, company_id, current_user)
    is_admin = current_user.role == "admin"

    other_side_filter = (User.role != "admin") if is_admin else (User.role == "admin")

    stmt = (
        select(func.count(CompanyMessage.id))
        .join(User, User.id == CompanyMessage.author_user_id)
        .where(
            CompanyMessage.company_id == company.id,
            CompanyMessage.read_at.is_(None),
            other_side_filter,
        )
    )
    count = db.scalar(stmt) or 0
    return {"unread_count": count}
