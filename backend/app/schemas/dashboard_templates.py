from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.dashboard_board import LabelRef


class DashboardCardCategoryOut(BaseModel):
    id: int
    name: str
    color: str
    sort_order: int


class DashboardCardCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: str = Field(default="#788c5d", max_length=20)
    sort_order: int = Field(default=0)


class DashboardCardCategoryUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: str = Field(max_length=20)
    sort_order: int


class DashboardTemplateColumnOut(BaseModel):
    id: int
    name: str
    kind: Literal["COLUMN", "SECTION"]
    position: str
    card_count: int


class DashboardTemplateColumnCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    kind: Literal["COLUMN", "SECTION"] = "COLUMN"


class DashboardTemplateColumnUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    kind: Literal["COLUMN", "SECTION"] = "COLUMN"


class DashboardTemplateColumnMove(BaseModel):
    prev_column_id: int | None = None
    next_column_id: int | None = None


class DashboardTemplateCardOut(BaseModel):
    id: int
    title: str
    description: str | None
    category_id: int | None
    category_name: str | None
    template_column_id: int | None
    position: str
    sort_order: int


class DashboardTemplateOut(BaseModel):
    id: int
    name: str
    description: str | None
    is_default: bool
    card_count: int


class DashboardTemplateDetailOut(DashboardTemplateOut):
    cards: list[DashboardTemplateCardOut]
    columns: list[DashboardTemplateColumnOut]


class DashboardTemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    is_default: bool = False


class DashboardTemplateUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    is_default: bool


class DashboardTemplateCardCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    # 20 000, e não 2 000: a descrição de template é a MESMA coisa que a
    # descrição do card (texto normativo do controle), e um limite menor
    # aqui truncaria na origem o que o card consegue guardar.
    description: str | None = Field(default=None, max_length=20000)
    category_id: int | None = None
    template_column_id: int | None = None
    sort_order: int = 0


class DashboardTemplateCardUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=20000)
    category_id: int | None = None
    template_column_id: int | None = None
    sort_order: int


class ApplyTemplateRequest(BaseModel):
    template_id: int


class ApplyTemplateResult(BaseModel):
    created_count: int
    adopted_count: int = 0
    already_applied_count: int
    outdated_card_ids: list[int]
    # B-A24 aplicado a colunas: sem este número, aplicar um template de
    # 25 colunas numa empresa que já tem todos os cards mostraria
    # "0 criados" e o admin concluiria que nada aconteceu.
    columns_created_count: int = 0


class BulkCardOperation(BaseModel):
    card_ids: list[int] = Field(min_length=1)
    operation: Literal[
        "hide",
        "unhide",
        "remove",
        "set_category",
        "set_column",
        "restore_from_template",
    ]
    category_id: int | None = None
    column_id: int | None = None


class BulkCardOperationResult(BaseModel):
    affected_count: int


class DashboardCardWithCategoryOut(BaseModel):
    """
    Saída de card com os campos de O.3 expostos — usada pela listagem de
    cards por empresa a partir de O.4. O endpoint de detalhe de card (GET /dashboard/cards/{id}) não
    muda: checklist/histórico/chat continuam fora do escopo de
    categoria/template.

    Desde o quadro Kanban, carrega também os quatro campos espaciais
    (`column_id`, `position`, `description`, `labels`). São adições — o
    contrato antigo continua válido para qualquer consumidor que os
    ignore.
    """

    id: int
    control_code: str | None
    title: str
    tag: str
    status: str
    category_id: int | None
    category_name: str | None
    hidden: bool
    origin_template_card_id: int | None
    is_outdated: bool
    column_id: int | None = None
    position: str = "a0"
    description: str | None = None
    labels: list[LabelRef] = Field(default_factory=list)
