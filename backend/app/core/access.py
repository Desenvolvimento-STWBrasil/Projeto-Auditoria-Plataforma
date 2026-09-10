from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company_dashboard import Company, Dashboard
from app.models.dashboard_board import DashboardColumn
from app.models.user import User

"""
Posse de recurso por usuário — ponto único (M-01c).

Este conceito existia em **quatro** cópias: `client.py`,
`dashboard_cards.py`, `company_messages.py` e, na direção inversa,
`company_admin.py::member_user_ids`. Quatro cópias de uma regra de acesso
significam quatro lugares para corrigir quando a regra muda — e três para
esquecer.

O custo disso foi medido, não suposto: B-B21 corrigiu um typo (`vísculo`)
que existia em **uma** das quatro; B-B23 (403 → 404) precisou ser aplicado
em três arquivos. A unificação faz a próxima mudança ser de um lugar só.

**Posse não é permissão.** Este módulo responde "este recurso é deste
usuário?". Quem responde "este papel pode executar esta ação?" é
`app/core/policy.py`. Os dois são necessários, e confundi-los foi
exatamente o que produziu B-A23 e B-A28.
"""


def resolve_owner_user_id(current_user: User) -> int:
    """
    ID do usuário "dono" dos dados: o próprio, ou o principal de quem ele
    é sub-usuário.

    Sub-usuários não têm dados próprios — têm acesso aos do principal ao
    qual estão vinculados.
    """
    if current_user.role == "sub-user":
        if current_user.parent_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sub-usuário sem vínculo com usuário principal",
            )
        return current_user.parent_user_id
    return current_user.id


def member_user_ids(db: Session, principal_user_id: int) -> list[int]:
    """
    A relação inversa de `resolve_owner_user_id`: usuário principal +
    todos os seus sub-usuários.

    Usada onde é preciso partir da empresa para achar os usuários — o
    filtro de auditoria por empresa (`Audit` não tem `company_id`, só
    `client_user_id`) e a exclusão em cascata.
    """
    sub_user_ids = db.scalars(
        select(User.id).where(User.parent_user_id == principal_user_id)
    ).all()
    return [principal_user_id, *sub_user_ids]


def get_company_with_access(
    db: Session, company_id: int, current_user: User
) -> Company:
    """
    Empresa acessível pelo chamador, ou 404.

    Devolve **404 — e não 403** — quando a empresa existe mas não é do
    chamador (B-B23). Distinguir "não existe" de "existe e não é sua"
    permite enumerar os `company_id` da plataforma. Mesma convenção já
    usada em `client.py::get_my_audit` ("não encontrada ou sem acesso").
    """
    company = db.get(Company, company_id)

    if company is not None:
        if current_user.role == "admin":
            return company
        if company.principal_user_id == resolve_owner_user_id(current_user):
            return company

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Empresa não encontrada ou sem acesso",
    )


def get_column_with_access(
    db: Session, column_id: int, current_user: User
) -> DashboardColumn:
    """
    Coluna de quadro acessível pelo chamador, ou 404.

    Mesmo molde de `get_company_with_access`, um JOIN mais longe
    (`dashboard_columns → dashboards → companies`) e com a mesma
    convenção de **404 em qualquer caso que não seja acesso legítimo**:
    coluna inexistente e coluna de outra empresa são indistinguíveis para
    quem chama (B-B23).

    Note que esta função responde só POSSE. A permissão de mexer na
    coluna é `Action.MANAGE_COLUMN`, verificada ANTES, no router — a
    ordem de `update_card_status`, que garante 403 para papel errado e
    404 para tenant errado, nunca o inverso.
    """
    row = db.execute(
        select(DashboardColumn, Company)
        .join(Dashboard, Dashboard.id == DashboardColumn.dashboard_id)
        .join(Company, Company.id == Dashboard.company_id)
        .where(DashboardColumn.id == column_id)
    ).first()

    if row is not None:
        column, company = row
        if current_user.role == "admin":
            return column
        if company.principal_user_id == resolve_owner_user_id(current_user):
            return column

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Coluna não encontrada ou sem acesso",
    )
