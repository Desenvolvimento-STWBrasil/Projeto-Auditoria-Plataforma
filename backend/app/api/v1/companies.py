from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.company_admin import (
    CompanyAdminDetail,
    CompanyAdminListItem,
    CompanyDeletionSummary,
    CompanyUpdateRequest,
)
from app.schemas.pagination import PaginatedResponse
from app.services.company_admin import (
    CompanyAdminData,
    CompanyNotFoundError,
    delete_company_cascade,
    get_company_admin_detail,
    list_companies_admin,
    update_company_admin,
)
from app.services.storage import delete_files

router = APIRouter(prefix="/admin/companies", tags=["Admin — Empresas"])


def _to_list_item(data: CompanyAdminData) -> CompanyAdminListItem:
    return CompanyAdminListItem(
        id=data.company.id,
        name=data.company.name,
        email=data.company.email,
        phone=data.company.phone,
        principal_user_id=data.company.principal_user_id,
        principal_full_name=data.principal_full_name,
        principal_email=data.principal_email,
        sub_user_count=data.sub_user_count,
        sub_user_emails=data.sub_user_emails,
        created_at=data.company.created_at,
    )


def _to_detail(data: CompanyAdminData) -> CompanyAdminDetail:
    return CompanyAdminDetail(
        **_to_list_item(data).model_dump(),
        audit_count=data.audit_count,
        dashboard_card_count=data.dashboard_card_count,
        company_message_count=data.company_message_count,
    )


@router.get("", response_model=PaginatedResponse[CompanyAdminListItem])
def list_companies(
    search: str | None = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> PaginatedResponse[CompanyAdminListItem]:
    """Lista paginada de empresas — tabela principal da tela "Lista de
    Empresas" (proposta M.1). `search` filtra por nome/e-mail da empresa
    ou nome/e-mail do usuário principal."""
    rows, total = list_companies_admin(db, search=search, skip=skip, limit=limit)
    return PaginatedResponse[CompanyAdminListItem](
        total=total,
        skip=skip,
        limit=limit,
        items=[_to_list_item(row) for row in rows],
    )


@router.get("/{company_id}", response_model=CompanyAdminDetail)
def get_company(
    company_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> CompanyAdminDetail:
    """Detalhe de uma empresa — alimenta o formulário de edição e os
    números de impacto do modal de confirmação de exclusão."""
    try:
        data = get_company_admin_detail(db, company_id)
    except CompanyNotFoundError:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return _to_detail(data)


@router.patch("/{company_id}", response_model=CompanyAdminDetail)
def update_company(
    company_id: int,
    payload: CompanyUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> CompanyAdminDetail:
    """Edita nome/e-mail/telefone da empresa. 409 se o novo nome ou
    e-mail já pertencer a outra empresa (constraint UNIQUE de
    companies.name/companies.email)."""
    try:
        update_company_admin(
            db,
            company_id,
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
        )
        db.commit()
    except CompanyNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe outra empresa com esse nome ou e-mail",
        )

    data = get_company_admin_detail(db, company_id)
    return _to_detail(data)


@router.delete("/{company_id}", response_model=CompanyDeletionSummary)
def delete_company(
    company_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> CompanyDeletionSummary:
    """Exclui a empresa e tudo que depende dela (usuários, auditorias,
    evidências, dashboard, chats — ver services/company_admin.py) numa
    única transação. O frontend deve ter mostrado o resumo de impacto
    (GET /admin/companies/{id}) e pedido confirmação explícita ANTES de
    chamar este endpoint — não há como desfazer.

    Os arquivos de evidência em disco são apagados DEPOIS do commit
    (B-A26): antes dele, um rollback deixaria registro apontando para
    arquivo inexistente."""
    try:
        summary = delete_company_cascade(db, company_id)
        db.commit()
    except CompanyNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Não foi possível excluir a empresa: existem registros "
                "vinculados que a exclusão em cascata não previu. "
                "Nenhuma alteração foi salva."
            ),
        )

    deleted_files = delete_files(summary.evidence_storage_keys)

    return CompanyDeletionSummary(
        company_id=summary.company_id,
        company_name=summary.company_name,
        deleted_principal_user_id=summary.deleted_principal_user_id,
        deleted_sub_users=summary.deleted_sub_users,
        deleted_sub_user_requests=summary.deleted_sub_user_requests,
        deleted_audits=summary.deleted_audits,
        deleted_audit_controls=summary.deleted_audit_controls,
        deleted_dashboard_cards=summary.deleted_dashboard_cards,
        deleted_dashboard_columns=summary.deleted_dashboard_columns,
        deleted_company_messages=summary.deleted_company_messages,
        deleted_evidence_files=deleted_files,
    )
