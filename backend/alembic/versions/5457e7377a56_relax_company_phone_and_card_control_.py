"""relax company.phone and dashboard_card.control_code to nullable

Revision ID: 5457e7377a56
Revises: d5c4d7cd6687
Create Date: 2026-08-05 00:00:00.000000

Contexto (docs/plano_implementacao.md, itens C.2.a e C.2.b):

- `companies.phone` era NOT NULL, mas o schema de onboarding
  (`PrincipalUserOnboardingRequest.phone`) e o formulário do admin sempre
  trataram o telefone como opcional. Onboarding sem telefone quebrava com
  IntegrityError.
- `dashboard_cards.control_code` era NOT NULL, mas cards criados a partir
  de um `DashboardTemplateCard` (que não tem `control_code`) nunca
  preenchiam essa coluna — todo onboarding com template (o caminho padrão,
  não-manual) quebrava com IntegrityError.

Esta migration relaxa as duas colunas para NULL, alinhando o banco ao que
a API/UI já assumiam. Criação manual de card via
`POST /dashboard/companies/{id}/cards` continua exigindo `control_code`
por validação do schema Pydantic (`DashboardCardCreate`), não do banco.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "5457e7377a56"
down_revision: Union[str, None] = "d5c4d7cd6687"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "companies",
        "phone",
        existing_type=sa.String(160),
        nullable=True,
    )
    op.alter_column(
        "dashboard_cards",
        "control_code",
        existing_type=sa.String(40),
        nullable=True,
    )


def downgrade() -> None:
    # Nota: se houver linhas com phone/control_code NULL no banco no
    # momento do downgrade, este ALTER falha (MySQL não aceita voltar a
    # NOT NULL com dados NULL existentes). Preencha/limpe esses dados
    # antes de rodar o downgrade em um banco com dados reais.
    op.alter_column(
        "dashboard_cards",
        "control_code",
        existing_type=sa.String(40),
        nullable=False,
    )
    op.alter_column(
        "companies",
        "phone",
        existing_type=sa.String(160),
        nullable=False,
    )
