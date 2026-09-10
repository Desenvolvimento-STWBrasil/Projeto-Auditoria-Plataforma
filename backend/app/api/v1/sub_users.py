from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_main_user
from app.db.session import get_db
from app.models.company_dashboard import Company
from app.models.sub_user_request import SubUserRequest, SubUserRequestStatus
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.sub_user import (
    SubUserApproveResponse,
    SubUserRequestCreate,
    SubUserRequestPublic,
)
from app.services.email_sender import send_sub_user_credentials_email
from app.services.users import (
    create_user,
    generate_temporary_password,
    get_user_by_email,
)

router = APIRouter(prefix="/sub-users", tags=["Sub-Users"])


@router.post(
    "/requests",
    response_model=SubUserRequestPublic,
    status_code=status.HTTP_201_CREATED,
)
def request_sub_user_request(
    payload: SubUserRequestCreate,
    db: Session = Depends(get_db),
    principal: User = Depends(require_main_user),
) -> SubUserRequestPublic:
    # Evita conflito de e-mail já existente no sistema
    if get_user_by_email(db, payload.request_email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado",
        )

    # Evita múltiplas solicitações pendentes para o mesmo principal + e-mail
    existing_pending = db.scalar(
        select(SubUserRequest).where(
            SubUserRequest.principal_user_id == principal.id,
            SubUserRequest.request_email == payload.request_email,
            SubUserRequest.status == SubUserRequestStatus.PENDING,
        )
    )
    if existing_pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solicitação de sub-usuário pendente",
        )

    request_obj = SubUserRequest(
        principal_user_id=principal.id,
        requested_full_name=payload.requested_full_name,
        request_email=payload.request_email,
        status=SubUserRequestStatus.PENDING,
    )
    db.add(request_obj)
    db.commit()
    db.refresh(request_obj)

    return SubUserRequestPublic(
        id=request_obj.id,
        principal_user_id=request_obj.principal_user_id,
        requested_full_name=request_obj.requested_full_name,
        request_email=request_obj.request_email,
        status=request_obj.status.value,
        requested_at=request_obj.request_at,
        processed_at=request_obj.processed_at,
    )


@router.get("/requests/me", response_model=list[SubUserRequestPublic])
def list_my_requests(
    db: Session = Depends(get_db),
    principal: User = Depends(require_main_user),
) -> list[SubUserRequestPublic]:
    rows = db.scalars(
        select(SubUserRequest)
        .where(SubUserRequest.principal_user_id == principal.id)
        .order_by(SubUserRequest.request_at.desc())
    ).all()

    return [
        SubUserRequestPublic(
            id=row.id,
            principal_user_id=row.principal_user_id,
            requested_full_name=row.requested_full_name,
            request_email=row.request_email,
            status=row.status.value,
            requested_at=row.request_at,
            processed_at=row.processed_at,
        )
        for row in rows
    ]


@router.get("/requests/pending", response_model=list[SubUserRequestPublic])
def list_pending_requests(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[SubUserRequestPublic]:
    # `sub_user_requests` não guarda a empresa diretamente — o join com
    # `companies.principal_user_id` resolve o nome da empresa do usuário
    # principal que fez a solicitação, para exibição no painel do admin.
    rows = db.execute(
        select(SubUserRequest, Company.name)
        .outerjoin(
            Company, Company.principal_user_id == SubUserRequest.principal_user_id
        )
        .where(SubUserRequest.status == SubUserRequestStatus.PENDING)
        .order_by(SubUserRequest.request_at.desc())
    ).all()

    return [
        SubUserRequestPublic(
            id=row.id,
            principal_user_id=row.principal_user_id,
            requested_full_name=row.requested_full_name,
            request_email=row.request_email,
            status=row.status.value,
            requested_at=row.request_at,
            processed_at=row.processed_at,
            company_name=company_name,
        )
        for row, company_name in rows
    ]


@router.post("/requests/{request_id}/approve", response_model=SubUserApproveResponse)
def approve_request(
    request_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> SubUserApproveResponse:
    sub_request = db.scalar(
        select(SubUserRequest).where(SubUserRequest.id == request_id).with_for_update()
    )
    if not sub_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitação não encontrada",
        )

    if sub_request.status != SubUserRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solicitação já processada",
        )

    principal = UserRepository(db).get_by_id(sub_request.principal_user_id)
    if not principal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário principal não encontrado",
        )

    if get_user_by_email(db, sub_request.request_email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado",
        )

    temp_password = generate_temporary_password()
    sub_user = create_user(
        db,
        full_name=sub_request.requested_full_name,
        email=sub_request.request_email,
        password=temp_password,
        role="sub-user",
        parent_user_id=principal.id,
    )

    sub_request.status = SubUserRequestStatus.APPROVED
    sub_request.processed_by_admin_id = admin.id
    sub_request.processed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(sub_request)

    email_delivered = send_sub_user_credentials_email(
        to_email=sub_user.email,
        sub_user_name=sub_user.full_name,
        principal_name=principal.full_name,
        temporary_password=temp_password,
    )

    return SubUserApproveResponse(
        request_id=sub_request.id,
        sub_user_id=sub_user.id,
        sub_user_email=sub_user.email,
        email_delivered=email_delivered,
        temporary_password=None if email_delivered else temp_password,
        status=sub_request.status.value,
    )


@router.post("/requests/{request_id}/reject", response_model=SubUserRequestPublic)
def reject_request(
    request_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> SubUserRequestPublic:
    sub_request = db.scalar(
        select(SubUserRequest).where(SubUserRequest.id == request_id).with_for_update()
    )
    if not sub_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitação não encontrada",
        )

    if sub_request.status != SubUserRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solicitação já processada",
        )

    sub_request.status = SubUserRequestStatus.REJECTED
    sub_request.processed_by_admin_id = admin.id
    sub_request.processed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(sub_request)

    # Não cria usuário nem envia credenciais — a recusa é sinalizada ao
    # usuário principal na própria plataforma, via GET /requests/me
    # (ver ClientDashboardClient), não por e-mail.
    return SubUserRequestPublic(
        id=sub_request.id,
        principal_user_id=sub_request.principal_user_id,
        requested_full_name=sub_request.requested_full_name,
        request_email=sub_request.request_email,
        status=sub_request.status.value,
        requested_at=sub_request.request_at,
        processed_at=sub_request.processed_at,
    )
