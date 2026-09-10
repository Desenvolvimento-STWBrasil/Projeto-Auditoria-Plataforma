from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal

from app.schemas.dashboard_board import LabelRef


class DashboardCardCreate(BaseModel):
    control_code: str | None = Field(
        default=None, description="Código do controle (opcional)"
    )
    title: str = Field(min_length=1, max_length=160, description="Título do card")
    category_id: int = Field(description="Categoria do card (obrigatória desde O.4)")
    column_id: int | None = Field(
        default=None, description="Coluna do quadro em que o card nasce"
    )
    # 20 000 porque as descrições reais são texto normativo longo (PRD §1.1).
    description: str | None = Field(
        default=None, max_length=20000, description="Texto normativo do controle"
    )
    status: Literal["EM_ANALISE", "PARCIAL", "CONFORME", "NAOCONFORME"] = Field(
        default="EM_ANALISE", description="Status do card"
    )


class DashboardchecklistItem(BaseModel):
    id: int
    title: str
    done: bool


class DashboardUserRef(BaseModel):
    id: int
    full_name: str


class DashboardHistoryOut(BaseModel):
    id: int
    action: str
    created_at: datetime
    actor_user: DashboardUserRef | None = None


class DashboardMessageOut(BaseModel):
    id: int
    message_type: str
    content: str
    created_at: datetime
    author_user: DashboardUserRef | None = None


class DashboardCardDetailOut(BaseModel):
    id: int
    control_code: str | None = None
    title: str
    tag: str
    status: str
    # Campos do quadro. `description` é o que o cliente precisa ler para
    # saber o que entregar (U7) — até aqui esse texto não tinha onde
    # existir na plataforma.
    description: str | None = None
    column_id: int | None = None
    # A categoria faltava neste payload desde O.3: o detalhe se anunciava
    # "completo" e devolvia só a `tag` (texto histórico, congelado no nome
    # que a categoria tinha na criação do card). Sem `category_id` não há
    # como pré-preencher o formulário de edição do card sem uma segunda
    # leitura do quadro só para descobrir a categoria dele.
    category_id: int | None = None
    category_name: str | None = None
    labels: list[LabelRef] = Field(default_factory=list)
    checklist: list[DashboardchecklistItem]
    history: list[DashboardHistoryOut]
    chat: list[DashboardMessageOut]


class CardStatusUpdateIn(BaseModel):
    status: Literal["EM_ANALISE", "PARCIAL", "CONFORME", "NAOCONFORME"]


class CardEntryCreateIn(BaseModel):
    entry_type: Literal["CHECKLIST", "HISTORY", "CHAT_QUESTION", "CHAT_ANSWER"]
    content: str = Field(min_length=1, max_length=1000)


class DashboardCardNoteCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class DashboardCardNoteOut(BaseModel):
    id: int
    content: str
    created_by_user_id: int
    created_by_name: str
    created_at: datetime


class DashboardStatusSummary(BaseModel):
    """
    Contagem agregada de `DashboardCard` por status, em TODAS as empresas
    (excluindo ocultos desde O.4) — alimenta os 4 KPIs do topo da Home.
    """

    em_analise: int
    parcial: int
    conforme: int
    naoconforme: int
