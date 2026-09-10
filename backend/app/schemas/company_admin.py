from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class CompanyAdminListItem(BaseModel):
    """Uma linha da tabela "Lista de Empresas" (GET /admin/companies)."""

    id: int
    name: str
    email: str
    phone: str | None
    principal_user_id: int
    principal_full_name: str
    principal_email: str
    sub_user_count: int
    sub_user_emails: list[str]
    created_at: datetime


class CompanyAdminDetail(CompanyAdminListItem):
    """Detalhe de uma empresa — alimenta o formulário de edição e os
    números de impacto exibidos no modal de confirmação de exclusão
    (GET /admin/companies/{id})."""

    audit_count: int
    dashboard_card_count: int
    company_message_count: int


class CompanyUpdateRequest(BaseModel):
    """Edição de dados cadastrais da empresa. Cria/edita usuário principal
    é feito por telas dedicadas (onboarding); aqui só os 3 campos que
    pertencem de fato à tabela `companies`."""

    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=40)


class CompanyDeletionSummary(BaseModel):
    """Retorno de DELETE /admin/companies/{id} — números do que foi
    removido em cascata, para o frontend confirmar ao usuário o que
    aconteceu (a mesma contagem que já foi mostrada como aviso antes da
    confirmação, via GET /admin/companies/{id})."""

    company_id: int
    company_name: str
    deleted_principal_user_id: int
    deleted_sub_users: int
    deleted_sub_user_requests: int
    deleted_audits: int
    deleted_audit_controls: int
    deleted_dashboard_cards: int
    # Quadro Kanban: as colunas caem junto com o dashboard, via cascata
    # ORM de `Dashboard.columns`. Aparecem no resumo porque uma entidade
    # removida que não aparece no resumo é uma exclusão silenciosa.
    deleted_dashboard_columns: int = 0
    deleted_company_messages: int
    # B-A26: quantos arquivos de evidência saíram do disco de fato. Zero
    # não é erro — uma empresa pode não ter nenhuma evidência anexada.
    deleted_evidence_files: int = 0
