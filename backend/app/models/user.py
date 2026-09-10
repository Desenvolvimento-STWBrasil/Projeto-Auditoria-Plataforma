from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.company_dashboard import DashboardCardHistoryEntry, DashboardCardMessage
from app.db.mixins import TimestampMixin, SoftDeleteMixin


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))

    # Roles válidas: admin | user| sub-user
    role: Mapped[str] = mapped_column(String(32), default="user", index=True)

    # Se role = sub-user, aponta para o usuário principal
    parent_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relacionamentos para runtime de dashboard
    history_items: Mapped[list["DashboardCardHistoryEntry"]] = relationship(
        back_populates="actor_user"
    )
    messages: Mapped[list["DashboardCardMessage"]] = relationship(
        back_populates="author_user"
    )
