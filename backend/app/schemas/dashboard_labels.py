from __future__ import annotations

from pydantic import BaseModel, Field


class DashboardLabelOut(BaseModel):
    id: int
    name: str
    color: str
    sort_order: int


class DashboardLabelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: str = Field(default="#788c5d", max_length=20)
    sort_order: int = Field(default=0)


class DashboardLabelUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: str = Field(max_length=20)
    sort_order: int


# Mais uma parte concluida.
# Continuar a leitura do arquivo CODE.md
# backend/app/schemas/dashboard_runtime.py
# Para encontrar com facilidade, FASE 4 - Schemas e rotas
