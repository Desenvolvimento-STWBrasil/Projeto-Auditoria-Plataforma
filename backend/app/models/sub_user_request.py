from __future__ import annotations

from datetime import datetime
import enum

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column


from app.db.base import Base


class SubUserRequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class SubUserRequest(Base):
    __tablename__ = "sub_user_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    principal_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    requested_full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    request_email: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[SubUserRequestStatus] = mapped_column(
        Enum(SubUserRequestStatus, name="sub_user_request_status"),
        nullable=False,
        default=SubUserRequestStatus.PENDING,
        index=True,
    )

    processed_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    request_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )