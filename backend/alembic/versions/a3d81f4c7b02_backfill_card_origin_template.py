"""backfill dashboard_cards.origin_template_card_id

Revision ID: a3d81f4c7b02
Revises: 4f2b8e6a91d3
Create Date: 2026-08-25 17:08:05.833234

Corrige B-A24. A migration 4f2b8e6a91d3 (fase O.3) acrescentou
`dashboard_cards.origin_template_card_id` mas não a preencheu, deixando
100% dos cards pré-O.3 invisíveis para a checagem de idempotência de
`apply_template_to_company` — que compara SÓ por essa coluna. Resultado:
a primeira aplicação de template numa empresa antiga duplica o dashboard
inteiro.

O casamento é feito por (template, título) e SÓ quando há exatamente um
card de template candidato com aquele título. Títulos ambíguos (o mesmo
texto em 2+ cards do mesmo template) são deixados com NULL de propósito —
adivinhar qual é qual seria pior que não ligar.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a3d81f4c7b02"
down_revision: Union[str, None] = "4f2b8e6a91d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # Títulos que aparecem exatamente 1x dentro do seu template — só
    # esses podem ser casados sem ambiguidade.
    unambiguous = bind.execute(sa.text("""
            SELECT template_id, title, MIN(id) AS template_card_id
              FROM dashboard_template_cards
             GROUP BY template_id, title
            HAVING COUNT(*) = 1
            """)).fetchall()

    for _template_id, title, template_card_id in unambiguous:
        bind.execute(
            sa.text("""
                UPDATE dashboard_cards
                   SET origin_template_card_id = :template_card_id
                 WHERE origin_template_card_id IS NULL
                   AND title = :title
                """),
            {"template_card_id": template_card_id, "title": title},
        )


def downgrade() -> None:
    # Não há como distinguir o vínculo restaurado por esta migration de um
    # vínculo criado organicamente depois dela. Reverter apagaria dados
    # legítimos, então o downgrade é deliberadamente um no-op.
    pass
