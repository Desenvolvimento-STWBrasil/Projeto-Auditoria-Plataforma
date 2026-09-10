from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CompanyMessage(Base):
    """
    Mensagem de um canal geral de comunicação entre o admin e uma empresa
    cliente — não vinculada a nenhum AuditControl nem DashboardCard (ver
    proposta L.1 em docs/plano_implementacao.md). Diferente de Message
    (chat por controle, tabela `messages`) e DashboardCardMessage (chat por
    card), este é o único canal "solto", pensado para dúvidas gerais que não
    pertencem a um controle ou card específico.

    Sem soft delete e sem `updated_at`: mensagem é append-only, nunca
    editada — mesma regra já aplicada aos dois chats existentes.
    """

    __tablename__ = "company_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    author_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    company: Mapped["Company"] = relationship(back_populates="messages")
    author_user: Mapped["User"] = relationship()
