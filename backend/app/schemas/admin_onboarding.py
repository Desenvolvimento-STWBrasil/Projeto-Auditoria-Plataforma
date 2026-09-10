from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class PrincipalUserOnboardingRequest(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    company_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=40)
    template_id: int | None = None
    manual_dashboard: bool = False


class PrincipalUserOnboardingResponse(BaseModel):
    user_id: int
    company_id: int
    dashboard_id: int
    dashboard_cards_created: int
    email_delivered: bool
    temporary_password: str | None = None


class CompanyFilterItem(BaseModel):
    id: int
    name: str


class DashboardTemplateItem(BaseModel):
    id: int
    name: str
    description: str | None
    is_default: bool


""" 1.4 Serviço: backend/app/services/dashboard_builder.py """
