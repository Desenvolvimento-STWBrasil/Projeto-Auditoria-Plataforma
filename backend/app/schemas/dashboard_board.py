from __future__ import annotations

"""
Contrato HTTP do quadro.

`BoardOut` é a resposta de UMA chamada (`GET /dashboard/companies/{id}/board`)
que traz o quadro pronto: colunas ordenadas, cards já agrupados dentro
delas e o vocabulário de etiquetas. É a decisão D-5 do PRD — antes, o
cliente React montava esse agrupamento em memória
(`groups: CardGroup[]` em `company-dashboard-client.tsx`), e com colunas
persistidas repetir a lógica de ordenação em dois lugares garantiria que
os dois divergissem.

Nos schemas de ENTRADA de movimento (`ColumnMoveIn`, `CardMoveIn`) o
cliente manda ÂNCORAS, nunca a chave de ordenação. Quem calcula a chave é
o servidor, dentro da transação (§4.2 do PRD): é o que elimina a classe
inteira de bugs "dois clientes calcularam a mesma chave" e mantém a
validação de escopo num lugar só.
"""

from typing import Literal

from pydantic import BaseModel, Field


class LabelRef(BaseModel):
    """Etiqueta como ela aparece EMBUTIDA num card."""

    id: int
    name: str
    color: str


class BoardCardOut(BaseModel):
    id: int
    control_code: str | None
    title: str
    description: str | None
    status: str
    position: str
    column_id: int | None
    category_id: int | None
    category_name: str | None
    labels: list[LabelRef]
    hidden: bool
    origin_template_card_id: int | None
    is_outdated: bool


class BoardColumnOut(BaseModel):
    id: int
    name: str
    kind: Literal["COLUMN", "SECTION"]
    position: str
    hidden: bool
    wip_limit: int | None
    cards: list[BoardCardOut]
    card_count: int


class BoardOut(BaseModel):
    dashboard_id: int
    company_id: int
    title: str
    columns: list[BoardColumnOut]
    # Cards órfãos de coluna (FK SET NULL de uma coluna excluída). Ficam
    # num balde próprio em vez de sumir do quadro.
    uncolumned: list[BoardCardOut]
    # Vocabulário completo de etiquetas, para a UI montar o seletor sem
    # uma segunda chamada.
    labels: list[LabelRef]


class ColumnCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    kind: Literal["COLUMN", "SECTION"] = "COLUMN"
    after_column_id: int | None = None


class ColumnUpdateIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    hidden: bool = False
    wip_limit: int | None = Field(default=None, ge=1)


class ColumnMoveIn(BaseModel):
    prev_column_id: int | None = None
    next_column_id: int | None = None


class ColumnOut(BaseModel):
    id: int
    name: str
    kind: Literal["COLUMN", "SECTION"]
    position: str
    hidden: bool
    wip_limit: int | None


class CardMoveIn(BaseModel):
    column_id: int | None = None
    prev_card_id: int | None = None
    next_card_id: int | None = None


class CardUpdateIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    # 20 000 porque as descrições reais são texto normativo longo: o
    # quadro de referência tem descrições de controle com vários
    # parágrafos (PRD §1.1).
    description: str | None = Field(default=None, max_length=20000)
    control_code: str | None = Field(default=None, max_length=40)
    category_id: int | None = None


class CardLabelsIn(BaseModel):
    """
    Semântica de PUT: a lista enviada SUBSTITUI o conjunto inteiro de
    etiquetas do card. Lista vazia remove todas.
    """

    label_ids: list[int] = Field(default_factory=list)
