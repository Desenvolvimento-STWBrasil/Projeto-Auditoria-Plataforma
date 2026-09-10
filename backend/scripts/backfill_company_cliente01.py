"""
Script one-off: cria Company + Dashboard (a partir do template padrão) para o
usuário principal 'cliente01@teste.com', que existia no banco antes do fluxo
de onboarding (/api/v1/onboarding/principal-user) ser implementado e por isso
nunca ganhou uma empresa vinculada.

Sintoma que motivou o script: GET /api/v1/companies/me devolvia 404 "Empresa
não encontrada para este usuário" ao abrir /private/client/mensagens logado
como cliente01 (ou como os sub-users dela, subcliente01/subteste, que herdam
a empresa do principal_user_id=3).

Reaproveita a mesma função de serviço usada pelo onboarding
(app.services.dashboard_builder.create_company_dashboard_from_template) para
que o resultado seja idêntico ao de uma empresa criada pelo fluxo normal.

Uso: python scripts/backfill_company_cliente01.py
"""

from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.company_dashboard import Company
from app.models.user import User
from app.services.dashboard_builder import (
    create_company_dashboard_from_template,
    resolve_template,
)

TARGET_EMAIL = "cliente01@teste.com"
COMPANY_NAME = "Cliente 01"


def main() -> None:
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == TARGET_EMAIL))
        if user is None:
            raise SystemExit(f"Usuário {TARGET_EMAIL!r} não encontrado.")

        existing = db.scalar(
            select(Company).where(Company.principal_user_id == user.id)
        )
        if existing is not None:
            raise SystemExit(
                f"Usuário {TARGET_EMAIL!r} (id={user.id}) já tem empresa "
                f"vinculada: {existing.name!r} (id={existing.id}). Nada a fazer."
            )

        if db.scalar(select(Company).where(Company.email == TARGET_EMAIL)):
            raise SystemExit(
                f"Já existe uma empresa com email {TARGET_EMAIL!r} vinculada "
                "a outro usuário — ajuste COMPANY_NAME/email antes de rodar."
            )

        template = resolve_template(db, None)  # usa o template padrão (is_default=1)

        company, dashboard, cards_created = create_company_dashboard_from_template(
            db,
            principal_user=user,
            company_name=COMPANY_NAME,
            company_email=TARGET_EMAIL,
            company_phone=None,
            template=template,
        )
        db.commit()
        db.refresh(company)
        db.refresh(dashboard)

        print(
            f"OK: empresa {company.name!r} (id={company.id}) criada para "
            f"user id={user.id}; dashboard id={dashboard.id} com "
            f"{cards_created} cards (template {template.name!r})."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
