from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User

class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)
    
    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))
    
    def list_by_role(self, role: str) -> list[User]:
        return list(self.db.scalars(select(User).where(User.role == role)).all())
    
    def create(self, *, full_name: str, email: str, password_hash: str, role: str, parent_user_id: int | None = None) -> User:
        user = User(
            full_name=full_name,
            email=email,
            password_hash=password_hash,
            role=role,
            parent_user_id=parent_user_id,
        )
        self.db.add(user)
        self.db.flush()
        return user