from __future__ import annotations

from sqlalchemy import select

from app.models.company_dashboard import DashboardCardCategory

CANONICAL_NAMES = ["Financeiro", "Operacional", "Vendas", "Compliance"]


def test_canonical_categories_are_seedable(db):
    """
    O.3: garante que as 4 categorias canônicas usadas pela migration
    4f2b8e6a91d3 (e reaproveitadas pelo seed de templates) podem ser
    criadas sem violar a constraint UNIQUE(name) — regressão simples,
    mas suficiente: se o nome de alguma colidir com outra ou o modelo
    mudar de forma incompatível, este teste falha antes de qualquer
    endpoint de O.4 ser exercitado.
    """
    for order, name in enumerate(CANONICAL_NAMES):
        db.add(DashboardCardCategory(name=name, color="#788c5d", sort_order=order))
    db.commit()

    rows = db.scalars(
        select(DashboardCardCategory).order_by(DashboardCardCategory.sort_order.asc())
    ).all()
    assert [r.name for r in rows] == CANONICAL_NAMES


def test_dashboard_card_can_reference_category_and_origin(db, dashboard_card):
    """DashboardCard aceita category_id/origin_template_card_id nulos (card
    "customizado", sem origem em template) e hidden=False por padrão."""
    assert dashboard_card.category_id is None
    assert dashboard_card.origin_template_card_id is None
    assert dashboard_card.hidden is False
