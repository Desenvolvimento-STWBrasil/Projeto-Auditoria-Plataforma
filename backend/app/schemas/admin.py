from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.audit import AuditStatus
from app.models.audit_control import AuditControlStatus


class AuditCreateRequest(BaseModel):
    client_user_id: int = Field(gt=0)
    name: str = Field(min_length=3, max_length=255)


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    client_user_id: int
    status: AuditStatus
    created_at: datetime


class AuditStatusUpdate(BaseModel):
    status: AuditStatus


class AuditControlStatusUpdate(BaseModel):
    status: AuditControlStatus


class EvidenceAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    mime_type: str | None
    size_bytes: int | None
    created_at: datetime
    uploaded_by_name: str


class MessageAdminOut(BaseModel):
    """
    Mensagem do chat "Conversa / Dúvidas" por controle (model `Message`,
    tabela `messages`) do ponto de vista do admin — mesmo padrão de
    `CompanyMessageOut` (is_from_admin já resolvido, sem o front precisar
    conhecer o `role` do autor).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    created_at: datetime
    read_at: datetime | None
    author_user_id: int
    author_full_name: str
    is_from_admin: bool


class AuditControlDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    control_code: str
    control_title: str
    status: str
    evidences: list[EvidenceAdminOut]
    messages: list[MessageAdminOut]


class AuditDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: str
    created_at: datetime
    client_name: str
    controls: list[AuditControlDetailOut]
