from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ControlCatalog(Base):
    __tablename__ = "control_catalog"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    expected_evidence: Mapped[str] = mapped_column(Text, nullable=True)
    
    audit_controls: Mapped[list["AuditControl"]] = relationship(back_populates="control")