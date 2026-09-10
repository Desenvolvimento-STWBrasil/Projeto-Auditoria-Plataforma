from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover - somente para anotacoes
    # Import adiado: `company_dashboard` importa `dashboard_card_labels`
    # deste modulo, entao um import em tempo de execucao seria circular.
    # As anotacoes abaixo sao resolvidas pelo registry do SQLAlchemy.
    from app.models.company_dashboard import (
        Dashboard,
        DashboardCard,
        DashboardTemplate,
        DashboardTemplateCard,
    )


class DashboardColumnKind(str, enum.Enum):
    """
    `SECTION` é a lista separadora do Trello (nome terminado em `>>`, ex.:
    `ISO 27001:2022 >>`): existe para dividir visualmente o quadro em
    blocos normativos, tem zero cards por definição e **não aceita** que
    um card seja solto nela. Renderiza como divisor, não como coluna.
    """

    COLUMN = "COLUMN"
    SECTION = "SECTION"


#: M:N entre card e etiqueta. Declarada como `Table` do Core (e não como
#: model) porque não tem identidade nem comportamento próprios — é
#: consumida via `secondary=` em `DashboardCard.labels`.
dashboard_card_labels = Table(
    "dashboard_card_labels",
    Base.metadata,
    Column(
        "card_id",
        ForeignKey("dashboard_cards.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "label_id",
        ForeignKey("dashboard_labels.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class DashboardTemplateColumn(Base):
    """Coluna de UM template — a planta a partir da qual as colunas de
    cada empresa nascem em `apply_template_to_company`."""

    __tablename__ = "dashboard_template_columns"

    __table_args__ = (
        UniqueConstraint(
            "template_id", "name", name="uq_dashboard_template_column_name"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("dashboard_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[DashboardColumnKind] = mapped_column(
        Enum(DashboardColumnKind, name="dashboard_column_kind"),
        nullable=False,
        default=DashboardColumnKind.COLUMN,
    )
    # O default existe só para não quebrar inserts diretos de seed/teste;
    # a chave real vem sempre de `app.services.fractional_index`
    # (INITIAL_KEY == "a0").
    position: Mapped[str] = mapped_column(String(64), nullable=False, default="a0")

    template: Mapped["DashboardTemplate"] = relationship(back_populates="columns")
    cards: Mapped[list["DashboardTemplateCard"]] = relationship(
        back_populates="template_column"
    )


class DashboardColumn(Base):
    __tablename__ = "dashboard_columns"

    __table_args__ = (
        # Mesma invariante que `uq_dashboard_card_origin_per_dashboard`
        # (migration b7c02e91d4a5) instalou para cards, pela mesma razão:
        # é ela que sustenta a idempotência de apply_template_to_company.
        # Em MySQL, NULL não participa da unicidade — colunas criadas à
        # mão pelo admin seguem livres.
        UniqueConstraint(
            "dashboard_id",
            "origin_template_column_id",
            name="uq_dashboard_column_origin_per_dashboard",
        ),
        # Cobre o ORDER BY do carregamento do quadro (CA-13).
        Index("ix_dashboard_columns_board_position", "dashboard_id", "position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dashboard_id: Mapped[int] = mapped_column(
        ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[DashboardColumnKind] = mapped_column(
        Enum(DashboardColumnKind, name="dashboard_column_kind"),
        nullable=False,
        default=DashboardColumnKind.COLUMN,
    )
    position: Mapped[str] = mapped_column(String(64), nullable=False, default="a0")
    # Equivalente ao `closed` da lista do Trello: arquiva sem apagar.
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Limite de WIP — coluna criada em v1, UI em v2 (evita uma 2ª migration).
    wip_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    origin_template_column_id: Mapped[int | None] = mapped_column(
        ForeignKey("dashboard_template_columns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    dashboard: Mapped["Dashboard"] = relationship(back_populates="columns")
    # SEM `delete-orphan`: apagar uma coluna NUNCA apaga card. A FK é
    # ON DELETE SET NULL e o card cai no bucket "Sem coluna" — mesma
    # escolha já feita para `category_id`.
    cards: Mapped[list["DashboardCard"]] = relationship(back_populates="column")
    origin_template_column: Mapped["DashboardTemplateColumn | None"] = relationship()


class DashboardLabel(Base):
    """
    Vocabulário GLOBAL de etiquetas, espelho estrutural de
    `DashboardCardCategory`: mesmo formato de campos, mesmo CRUD, mesma
    regra de exclusão bloqueada quando em uso.
    """

    __tablename__ = "dashboard_labels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="#788c5d")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
