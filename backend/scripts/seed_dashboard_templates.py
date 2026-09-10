from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.company_dashboard import (
    DashboardCardCategory,
    DashboardTemplate,
    DashboardTemplateCard,
)
from app.models.dashboard_board import DashboardColumnKind, DashboardTemplateColumn
from app.services.fractional_index import n_keys_between


def _resolve_category_id(db, name: str) -> int | None:
    category = db.scalar(
        select(DashboardCardCategory).where(DashboardCardCategory.name == name)
    )
    return category.id if category else None


def main() -> None:
    # (título, categoria/tag, ordem, nome da coluna em que o card nasce)
    templates = [
        {
            "name": "Template 1",
            "description": "Template de dashboard padrão",
            "is_default": True,
            "columns": ["A fazer", "Em análise", "Concluído"],
            "cards": [
                ("Card 1", "Financeiro", 0, "A fazer"),
                ("Card 2", "Operacional", 1, "A fazer"),
                ("Card 3", "Vendas", 2, "Em análise"),
            ],
        },
        {
            "name": "Template 2",
            "description": "Template de dashboard de exemplo",
            "is_default": False,
            "columns": ["A fazer", "Em análise", "Concluído"],
            "cards": [
                ("Card 1", "Financeiro", 0, "A fazer"),
                ("Card 2", "Operacional", 1, "A fazer"),
                ("Card 3", "Vendas", 2, "Em análise"),
            ],
        },
    ]

    with SessionLocal() as db:
        for tp1 in templates:
            existing = db.scalar(
                select(DashboardTemplate).where(DashboardTemplate.name == tp1["name"])
            )
            if existing:
                # Mantém o flag de default sincronizado se o template já existir
                existing.is_default = tp1["is_default"]
                continue

            template = DashboardTemplate(
                name=tp1["name"],
                description=tp1["description"],
                is_default=tp1["is_default"],
            )
            db.add(template)
            db.flush()

            # As colunas vêm ANTES dos cards: o card precisa do
            # `template_column_id` no momento do insert.
            coluna_por_nome: dict[str, DashboardTemplateColumn] = {}
            posicoes = n_keys_between(None, None, len(tp1["columns"]))
            for nome_da_coluna, position in zip(tp1["columns"], posicoes):
                coluna = DashboardTemplateColumn(
                    template_id=template.id,
                    name=nome_da_coluna,
                    kind=DashboardColumnKind.COLUMN,
                    position=position,
                )
                db.add(coluna)
                coluna_por_nome[nome_da_coluna] = coluna
            db.flush()

            posicoes_de_card = n_keys_between(None, None, len(tp1["cards"]))
            for (title, tag, order, nome_da_coluna), position in zip(
                tp1["cards"], posicoes_de_card
            ):
                db.add(
                    DashboardTemplateCard(
                        template_id=template.id,
                        title=title,
                        tag=tag,
                        category_id=_resolve_category_id(db, tag),
                        template_column_id=coluna_por_nome[nome_da_coluna].id,
                        sort_order=order,
                        position=position,
                    )
                )

        db.commit()
        print("Templates de dashboard carregados com sucesso.")


if __name__ == "__main__":
    main()
