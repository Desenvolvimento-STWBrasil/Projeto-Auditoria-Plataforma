from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """
    ⚠️ NÃO IMPLEMENTADO (B-B19). A coluna existe (migration 5e977e8b49da)
    mas NENHUMA query do backend filtra por ela — todas as exclusões são
    FÍSICAS, incluindo a cascata de empresa (services/company_admin.py) e
    os arquivos em disco (services/storage.py::delete_files).

    Não assuma que gravar `deleted_at` esconde um registro: não esconde.
    Antes de ativar o soft delete é preciso decidir o que acontece com o
    ARQUIVO de uma evidência logicamente excluída — a resposta errada
    reabre B-A26 (LGPD). Ver N11 em docs/relatorio_funcionalidades.md.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
