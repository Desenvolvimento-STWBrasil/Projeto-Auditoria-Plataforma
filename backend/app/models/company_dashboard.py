from __future__ import annotations

from datetime import datetime
import enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.dashboard_board import dashboard_card_labels


class DashboardMessageType(str, enum.Enum):
    QUESTION = "QUESTION"
    ANSWER = "ANSWER"


class DashboardCardStatus(str, enum.Enum):
    EM_ANALISE = "EM_ANALISE"
    PARCIAL = "PARCIAL"
    CONFORME = "CONFORME"
    NAOCONFORME = "NAOCONFORME"


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(160), nullable=False, unique=True, index=True
    )
    email: Mapped[str] = mapped_column(
        String(160), nullable=False, unique=True, index=True
    )
    phone: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)

    principal_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relacionamentos de posse usados pela exclusão em cascata de empresa
    # (ver services/company_admin.py::delete_company_cascade, proposta
    # M.1). `cascade="all, delete-orphan"` faz o SQLAlchemy apagar
    # dashboard/cards/notes/checklist/history/messages e company_messages
    # no nível do ORM quando `db.delete(company)` é chamado — não dependemos
    # só do `ON DELETE CASCADE` do banco (que existe desde 9d5a3c1b2e77 /
    # bf7239a52df8, mas não é respeitado pelo SQLite dos testes sem
    # `PRAGMA foreign_keys=ON`).
    dashboard: Mapped["Dashboard | None"] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
        uselist=False,
    )
    messages: Mapped[list["CompanyMessage"]] = relationship(  # type: ignore
        back_populates="company",
        cascade="all, delete-orphan",
    )


class DashboardCardCategory(Base):
    """
    Vocabulário fechado de categorias de card, editável pelo admin — o
    mesmo papel que `ControlCatalog` cumpre para `AuditControl`, aplicado
    ao domínio do dashboard (proposta O.3 em docs/plano_implementacao.md).
    Substitui `DashboardCard.tag`/`DashboardTemplateCard.tag` (texto
    livre) como forma de agrupar/filtrar/editar em massa por categoria.
    `tag` permanece nas duas tabelas como campo histórico — ver a
    migration 4f2b8e6a91d3 para a estratégia de backfill.

    Desde o quadro Kanban (migration c8f1a3e57b90) a categoria deixou de
    ser o eixo de AGRUPAMENTO VISUAL — esse papel passou a
    `DashboardColumn`, que é por quadro. A categoria continua sendo o eixo
    de CLASSIFICAÇÃO global, e continua alimentando o filtro lateral e o
    `bulk_update_cards(operation="set_category")`. Ver D-1 do PRD.
    """

    __tablename__ = "dashboard_card_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="#788c5d")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class DashboardTemplate(Base):
    __tablename__ = "dashboard_templates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    cards: Mapped[list["DashboardTemplateCard"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
    )
    # Mesmo motivo do cascade em `Company.dashboard`: sem ele, excluir um
    # template deixa colunas órfãs no SQLite dos testes, que não aplica
    # `ON DELETE CASCADE` sem `PRAGMA foreign_keys=ON`.
    columns: Mapped[list["DashboardTemplateColumn"]] = relationship(  # type: ignore
        back_populates="template",
        cascade="all, delete-orphan",
    )


class DashboardTemplateCard(Base):
    __tablename__ = "dashboard_template_cards"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("dashboard_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tag: Mapped[str] = mapped_column(String(60), nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("dashboard_card_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Em que coluna do template este card nasce (§4.1.2 do PRD).
    template_column_id: Mapped[int | None] = mapped_column(
        ForeignKey("dashboard_template_columns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Campo histórico desde c8f1a3e57b90 — substituído por `position`.
    # Mantido preenchido para não quebrar consumidor antigo, mesma
    # política conservadora aplicada a `tag` na migration 4f2b8e6a91d3.
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    position: Mapped[str] = mapped_column(String(64), nullable=False, default="a0")

    template: Mapped["DashboardTemplate"] = relationship(back_populates="cards")
    category: Mapped["DashboardCardCategory | None"] = relationship()
    template_column: Mapped["DashboardTemplateColumn | None"] = relationship(  # type: ignore
        back_populates="cards"
    )


class Dashboard(Base):
    __tablename__ = "dashboards"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    cards: Mapped[list["DashboardCard"]] = relationship(
        back_populates="dashboard",
        cascade="all, delete-orphan",
    )
    # Sem este cascade, `delete_company_cascade` deixa colunas órfãs no
    # SQLite dos testes — exatamente o motivo já documentado no comentário
    # de `Company.dashboard` logo acima.
    columns: Mapped[list["DashboardColumn"]] = relationship(  # type: ignore
        back_populates="dashboard",
        cascade="all, delete-orphan",
    )
    company: Mapped["Company"] = relationship(back_populates="dashboard")


class DashboardCard(Base):
    __tablename__ = "dashboard_cards"

    __table_args__ = (
        # M-19: a invariante que sustenta a idempotência de
        # apply_template_to_company. NULL não participa da unicidade em
        # MySQL, então cards customizados seguem livres.
        UniqueConstraint(
            "dashboard_id",
            "origin_template_card_id",
            name="uq_dashboard_card_origin_per_dashboard",
        ),
        # Cobre o ORDER BY do carregamento do quadro e elimina o filesort
        # com 215 cards (CA-13). Mesmo padrão das migrations 56d322bbd83a /
        # d5c4d7cd6687 / eafa65e9df05.
        Index("ix_dashboard_cards_column_position", "column_id", "position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dashboard_id: Mapped[int] = mapped_column(
        ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False, index=True
    )

    control_code: Mapped[str | None] = mapped_column(
        String(40), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    tag: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("dashboard_card_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    origin_template_card_id: Mapped[int | None] = mapped_column(
        ForeignKey("dashboard_template_cards.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[DashboardCardStatus] = mapped_column(
        Enum(DashboardCardStatus, name="dashboard_card_status"),
        nullable=False,
        default=DashboardCardStatus.EM_ANALISE,
        index=True,
    )

    # SET NULL e não CASCADE: apagar uma coluna nunca apaga card — o card
    # cai no bucket sintético "Sem coluna" do quadro. Mesma escolha já
    # feita para `category_id` logo acima.
    column_id: Mapped[int | None] = mapped_column(
        ForeignKey("dashboard_columns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    position: Mapped[str] = mapped_column(String(64), nullable=False, default="a0")
    # 68 % dos cards do quadro real têm descrição, e ela é o texto
    # normativo do controle. Sem esta coluna, `apply_template_to_company`
    # descartava silenciosamente `DashboardTemplateCard.description`
    # desde O.3.
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Coluna criada em v1 sem UI (v2), para evitar uma 2ª migration.
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Campo histórico desde c8f1a3e57b90 — a ordenação real do quadro é
    # `position`. Mantido preenchido por retrocompatibilidade, mesma
    # política que `tag` recebeu na migration 4f2b8e6a91d3 (B12).
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    dashboard: Mapped["Dashboard"] = relationship(back_populates="cards")
    category: Mapped["DashboardCardCategory | None"] = relationship()
    origin_template_card: Mapped["DashboardTemplateCard | None"] = relationship()
    column: Mapped["DashboardColumn | None"] = relationship(  # type: ignore
        back_populates="cards"
    )
    labels: Mapped[list["DashboardLabel"]] = relationship(  # type: ignore
        secondary=dashboard_card_labels,
        order_by="DashboardLabel.sort_order",
    )
    notes: Mapped[list["DashboardCardNote"]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )
    checklist_items: Mapped[list["DashboardCardchecklistItem"]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )
    history_items: Mapped[list["DashboardCardHistoryEntry"]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )
    messages: Mapped[list["DashboardCardMessage"]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )


class DashboardCardNote(Base):
    __tablename__ = "dashboard_card_notes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(
        ForeignKey("dashboard_cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    card: Mapped["DashboardCard"] = relationship(back_populates="notes")


class DashboardCardchecklistItem(Base):
    __tablename__ = "dashboard_card_checklist_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(
        ForeignKey("dashboard_cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    card: Mapped["DashboardCard"] = relationship(back_populates="checklist_items")


class DashboardCardHistoryEntry(Base):
    __tablename__ = "dashboard_card_history_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(
        ForeignKey("dashboard_cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    card: Mapped["DashboardCard"] = relationship(back_populates="history_items")
    actor_user: Mapped["User"] = relationship(back_populates="history_items")  # type: ignore


class DashboardCardMessage(Base):
    __tablename__ = "dashboard_card_messages"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(
        ForeignKey("dashboard_cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    message_type: Mapped[DashboardMessageType] = mapped_column(
        Enum(DashboardMessageType, name="dashboard_message_type"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    card: Mapped["DashboardCard"] = relationship(back_populates="messages")
    author_user: Mapped["User"] = relationship(back_populates="messages")  # type: ignore
