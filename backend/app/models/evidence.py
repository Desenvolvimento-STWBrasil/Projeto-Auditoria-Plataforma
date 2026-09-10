from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base



class Evidence(Base):
    __tablename__ = "evidences"
    
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    audit_control_id: Mapped[int] = mapped_column(
        ForeignKey("audit_controls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    uploaded_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    audit_control: Mapped["AuditControl"] = relationship(back_populates="evidences")