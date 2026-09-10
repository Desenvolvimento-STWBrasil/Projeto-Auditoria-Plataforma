from __future__ import annotations

import secrets
import string

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository


def get_user_by_email(db: Session, email: str) -> User | None:
    repo = UserRepository(db)
    return repo.get_by_email(email)


def create_user(
    db: Session,
    *,
    full_name: str,
    email: str,
    password: str,
    role: str = "user",
    parent_user_id: int | None = None,
) -> User:
    repo = UserRepository(db)
    return repo.create(
        full_name=full_name,
        email=email,
        password_hash=hash_password(password),
        role=role,
        parent_user_id=parent_user_id,
    )


def authenticate_user(db: Session, *, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def generate_temporary_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%&"
    return "".join(secrets.choice(alphabet) for _ in range(length))
