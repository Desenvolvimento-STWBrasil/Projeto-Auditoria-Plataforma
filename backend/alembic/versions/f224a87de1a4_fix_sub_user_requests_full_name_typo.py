"""fix_sub_user_requests_full_name_typo

Revision ID: f224a87de1a4
Revises: 83cf1e14efa8
Create Date: 2026-08-12 11:57:33.981335

A migration commit reescreveu 447a4e1de59d (create_table de
sub_user_requests) para usar `requested_full_name`, alinhando o nome ao
schema Pydantic/ORM/frontend — mas isso só afeta bancos criados *depois*
da reescrita. Bancos cujo `alembic upgrade` já havia rodado a versão
antiga da migration continuam com a coluna física `request_full_name`,
causando `OperationalError: Unknown column 'sub_user_requests.
requested_full_name'` em qualquer SELECT do endpoint
GET /api/v1/sub-users/requests/pending (erro 500 na tela de admin).

Guardado com inspector: em bancos já criados com o nome novo (migration
447a4e1de59d aplicada após a correção), a coluna renomeada não existe e
o upgrade é no-op.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


# revision identifiers, used by Alembic.
revision: str = 'f224a87de1a4'
down_revision: Union[str, None] = '83cf1e14efa8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {c["name"] for c in sa_inspect(bind).get_columns("sub_user_requests")}
    if "request_full_name" in columns and "requested_full_name" not in columns:
        op.alter_column(
            "sub_user_requests",
            "request_full_name",
            new_column_name="requested_full_name",
            existing_type=sa.String(length=255),
            existing_nullable=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    columns = {c["name"] for c in sa_inspect(bind).get_columns("sub_user_requests")}
    if "requested_full_name" in columns and "request_full_name" not in columns:
        op.alter_column(
            "sub_user_requests",
            "requested_full_name",
            new_column_name="request_full_name",
            existing_type=sa.String(length=255),
            existing_nullable=False,
        )
