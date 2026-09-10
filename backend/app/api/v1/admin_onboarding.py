from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.company_dashboard import Company, DashboardTemplate
from app.models.user import User
from app.schemas.admin_onboarding import (
    CompanyFilterItem,
    DashboardTemplateItem,
    PrincipalUserOnboardingRequest,
    PrincipalUserOnboardingResponse,
)
from app.services.dashboard_builder import (
    create_company_dashboard_from_template,
    resolve_template,
)
from app.services.email_sender import send_principal_user_credentials_email
from app.services.users import (
    create_user,
    generate_temporary_password,
    get_user_by_email,
)

router = APIRouter(prefix="/onboarding", tags=["Admin Onboarding"])


@router.get("/companies", response_model=list[CompanyFilterItem])
def list_companies(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[CompanyFilterItem]:
    rows = db.scalars(select(Company).order_by(Company.name.asc())).all()
    return [CompanyFilterItem(id=company.id, name=company.name) for company in rows]


@router.get("/templates", response_model=list[DashboardTemplateItem])
def list_templates(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[DashboardTemplateItem]:
    rows = db.scalars(
        select(DashboardTemplate).order_by(DashboardTemplate.name.asc())
    ).all()
    return [
        DashboardTemplateItem(
            id=template.id,
            name=template.name,
            description=template.description,
            is_default=template.is_default,
        )
        for template in rows
    ]


@router.post(
    "/principal-user",
    response_model=PrincipalUserOnboardingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_principal_user_with_dashboard(
    payload: PrincipalUserOnboardingRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> PrincipalUserOnboardingResponse:
    if get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="E-mail já cadastrado"
        )

    template = None
    if not payload.manual_dashboard:
        try:
            template = resolve_template(db, payload.template_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            )

    if db.scalar(select(Company).where(Company.email == payload.email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Empresa já cadastrada"
        )

    initial_password = generate_temporary_password()

    try:
        principal_user = create_user(
            db,
            full_name=payload.full_name,
            email=payload.email,
            password=initial_password,
            role="user",
        )

        company, dashboard, cards_created = create_company_dashboard_from_template(
            db,
            principal_user=principal_user,
            company_name=payload.company_name,
            company_email=payload.email,
            company_phone=payload.phone,
            template=template,
        )

        db.commit()
        db.refresh(principal_user)
        db.refresh(company)
        db.refresh(dashboard)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail ou empresa já cadastrados (requisição concorrente).",
        )

    except Exception:
        db.rollback()
        raise

    # Reuso da infraestrutura de email: envia e-mail de credenciais para o usuário principal
    email_delivered = send_principal_user_credentials_email(
        to_email=principal_user.email,
        full_name=principal_user.full_name,
        company_name=company.name,
        temporary_password=initial_password,
    )

    return PrincipalUserOnboardingResponse(
        user_id=principal_user.id,
        company_id=company.id,
        dashboard_id=dashboard.id,
        dashboard_cards_created=cards_created,
        email_delivered=email_delivered,
        temporary_password=None if email_delivered else initial_password,
    )
