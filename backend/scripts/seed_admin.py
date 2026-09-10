from __future__ import annotations

import os

from sqlalchemy import select
from dotenv import load_dotenv
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User

load_dotenv()

def main() -> None:
    """ 
    Seed idempotente:
    - se o admin ja existir (por email), não cria outro.
    - se não existir, cria com role='admin'
    """

    admin_name = os.getenv("ADMIN_FULL_NAME", "Administrador")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@auditoria.com")
    admin_password = os.getenv("ADMIN_PASSWORD") 
    
    if not admin_password:
        raise RuntimeError(
            "ADMIN_PASSWORD não definido. "
            "Defina uma senha forte via variável de ambiente de rodar o seed"
        )
    
    with SessionLocal() as session:
        try:
            existing = session.scalar(select(User).where(User.email == admin_email))
            if existing:
                print(f"Admin já existe: {admin_email} (id={existing.id})")
                return
            
            admin = User(
                full_name=admin_name,
                email=admin_email,
                password_hash=hash_password(admin_password),
                role="admin",
            )
            session.add(admin)
            session.commit()
            session.refresh(admin)
            
            print(f"Admin criado com sucesso: {admin.email} (id={admin.id})")
            
        except Exception:
            session.rollback()
            raise
        
if __name__ == "__main__":
    main()