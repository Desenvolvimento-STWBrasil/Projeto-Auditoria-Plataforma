from __future__ import annotations

from pydantic import BaseModel


class ClientControlItem(BaseModel):
    audit_id: int
    audit_name: str

    audit_control_id: int
    status: str

    control_code: str
    control_title: str
    control_description: str
    expected_evidence: str | None


class MessageCreate(BaseModel):
    content: str