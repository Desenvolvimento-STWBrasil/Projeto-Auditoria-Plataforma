from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CompanyMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class CompanyMessageAuthorOut(BaseModel):
    id: int
    full_name: str
    role: str


class CompanyMessageOut(BaseModel):
    id: int
    content: str
    created_at: datetime
    read_at: datetime | None
    is_from_admin: bool
    author: CompanyMessageAuthorOut


class CompanyOut(BaseModel):
    id: int
    name: str
