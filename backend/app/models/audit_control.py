from __future__ import annotations

import enum

from sqlalchemy import (
    Enum,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, SoftDeleteMixin


class AuditControlStatus(str, enum.Enum):
    EM_ANALISE = "EM_ANALISE"
    PARCIAL = "PARCIAL"
    CONFORME = "CONFORME"
    NAOCONFORME = "NAOCONFORME"


class AuditControl(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "audit_controls"

    __table_args__ = (
        UniqueConstraint(
            "audit_id", "control_id", name="uq_audit_control_one_per_audit"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    audit_id: Mapped[int] = mapped_column(
        ForeignKey("audits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    control_id: Mapped[int] = mapped_column(
        ForeignKey("control_catalog.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    status: Mapped[AuditControlStatus] = mapped_column(
        Enum(AuditControlStatus, name="audit_control_status"),
        nullable=False,
        default=AuditControlStatus.EM_ANALISE,
        index=True,
    )

    audit: Mapped["Audit"] = relationship(back_populates="controls")
    control: Mapped["ControlCatalog"] = relationship(back_populates="audit_controls")

    evidences: Mapped[list["Evidence"]] = relationship(
        back_populates="audit_control",
        cascade="all, delete-orphan",
    )
    messages: Mapped[list["Message"]] = relationship(
        back_populates="audit_control",
        cascade="all, delete-orphan",
    )
