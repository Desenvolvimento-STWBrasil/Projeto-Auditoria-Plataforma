from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company_dashboard import (
    Company,
    Dashboard,
    DashboardCard,
    DashboardTemplate,
    DashboardTemplateCard,
)
from app.models.dashboard_board import DashboardColumn, DashboardTemplateColumn
from app.models.user import User
from app.services.fractional_index import key_between, n_keys_between


def resolve_template(db: Session, template_id: int | None) -> DashboardTemplate:
    if template_id is not None:
        template = db.get(DashboardTemplate, template_id)
        if not template:
            raise ValueError("Template não encontrado")
        return template

    default_template = db.scalar(
        select(DashboardTemplate).where(DashboardTemplate.is_default.is_(True))
    )
    if not default_template:
        raise ValueError("Nenhum template padrão configurado")
    return default_template


def create_company_dashboard_from_template(
    db: Session,
    *,
    principal_user: User,
    company_name: str,
    company_email: str,
    company_phone: str | None = None,
    template: DashboardTemplate | None = None,
) -> tuple[Company, Dashboard, int]:
    """
    Caminho de ONBOARDING: cria empresa, quadro, colunas e cards a partir
    do template, numa transação só.

    O retorno continua sendo `(company, dashboard, cards_criados)` — a
    contagem de colunas não entra na tupla porque `admin_onboarding.py`
    a desempacota posicionalmente. Quem precisa desse número é
    `apply_template_to_company`, que devolve um dataclass e pode crescer
    sem quebrar chamador.
    """
    company = Company(
        name=company_name,
        email=company_email,
        phone=company_phone,
        principal_user_id=principal_user.id,
    )
    db.add(company)
    db.flush()

    dashboard = Dashboard(
        company_id=company.id,
        title=f"Dashboard - {company_name}",
    )
    db.add(dashboard)
    db.flush()

    if template is None:
        db.flush()
        return company, dashboard, 0

    # ---- Colunas antes dos cards: o card precisa do `column_id` no
    # momento do insert, e o mapa template_column_id -> column_id é o que
    # torna esse insert possível numa passada só.
    template_columns = list(
        db.scalars(
            select(DashboardTemplateColumn)
            .where(DashboardTemplateColumn.template_id == template.id)
            .order_by(
                DashboardTemplateColumn.position.asc(),
                DashboardTemplateColumn.id.asc(),
            )
        ).all()
    )

    column_by_template_column: dict[int, DashboardColumn] = {}
    if template_columns:
        for template_column, position in zip(
            template_columns, n_keys_between(None, None, len(template_columns))
        ):
            coluna = DashboardColumn(
                dashboard_id=dashboard.id,
                name=template_column.name,
                kind=template_column.kind,
                position=position,
                origin_template_column_id=template_column.id,
            )
            db.add(coluna)
            column_by_template_column[template_column.id] = coluna
        db.flush()

    template_cards = db.scalars(
        select(DashboardTemplateCard)
        .where(DashboardTemplateCard.template_id == template.id)
        .order_by(
            DashboardTemplateCard.position.asc(),
            DashboardTemplateCard.sort_order.asc(),
            DashboardTemplateCard.id.asc(),
        )
    ).all()

    ultima_position: dict[int | None, str | None] = {}
    created_cards = 0
    for card in template_cards:
        coluna = (
            column_by_template_column.get(card.template_column_id)
            if card.template_column_id is not None
            else None
        )
        column_id = coluna.id if coluna is not None else None

        position = key_between(ultima_position.get(column_id), None)
        ultima_position[column_id] = position

        db.add(
            DashboardCard(
                dashboard_id=dashboard.id,
                title=card.title,
                tag=card.tag,
                category_id=card.category_id,
                # A descrição do template deixa de ser descartada aqui
                # também — o defeito era simétrico nos dois caminhos.
                description=card.description,
                column_id=column_id,
                position=position,
                origin_template_card_id=card.id,
                sort_order=created_cards,
            )
        )
        created_cards += 1

    db.flush()
    return company, dashboard, created_cards
