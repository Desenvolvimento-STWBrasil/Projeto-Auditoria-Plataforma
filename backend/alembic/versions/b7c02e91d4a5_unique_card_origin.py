"""unique constraint on dashboard card origin

Revision ID: b7c02e91d4a5
Revises: a3d81f4c7b02
Create Date: 2026-08-25 17:32:47.583857

M-19. A idempotência de apply_template_to_company depende de uma
invariante que hoje vive só num dict em memória: dentro de um dashboard,
no máximo um card aponta para um dado card de template. Um dict SILENCIA
violações — se dois cards do mesmo dashboard tiverem o mesmo
origin_template_card_id, um sobrescreve o outro sem erro.

Em MySQL, linhas com NULL em qualquer coluna do índice não participam da
checagem de unicidade — cards customizados (origin_template_card_id IS
NULL) seguem podendo ser vários, que é o comportamento desejado.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "b7c02e91d4a5"
down_revision: Union[str, None] = "a3d81f4c7b02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_dashboard_card_origin_per_dashboard",
        "dashboard_cards",
        ["dashboard_id", "origin_template_card_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_dashboard_card_origin_per_dashboard", "dashboard_cards", type_="unique"
    )
