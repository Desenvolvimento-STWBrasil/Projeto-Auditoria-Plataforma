from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class SubUserRequestCreate(BaseModel):
    requested_full_name: str = Field(min_length=3, max_length=120)
    request_email: EmailStr


class SubUserRequestPublic(BaseModel):
    id: int
    principal_user_id: int
    requested_full_name: str
    request_email: EmailStr
    status: str
    requested_at: datetime
    processed_at: datetime | None = None
    # Nome da empresa do usuário principal que solicitou o sub-usuário.
    # Resolvido via join com `companies.principal_user_id` — não é uma
    # coluna de `sub_user_requests`. Pode vir `None` quando o principal
    # ainda não tem empresa cadastrada.
    company_name: str | None = None


class SubUserApproveResponse(BaseModel):
    request_id: int
    sub_user_id: int
    sub_user_email: EmailStr
    email_delivered: bool
    temporary_password: str | None = None
    status: str
