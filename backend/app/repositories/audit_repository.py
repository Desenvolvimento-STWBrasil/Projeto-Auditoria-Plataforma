from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import Audit
from app.models.audit_control import AuditControl
from app.models.control_catalog import ControlCatalog


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, audit_id: int) -> Audit | None:
        return self.db.get(Audit, audit_id)

    def list_by_client(self, client_user_id: int) -> list[Audit]:
        return list(
            self.db.scalars(
                select(Audit).where(Audit.client_user_id == client_user_id)
            ).all()
        )

    def create_with_controls(self, *, name: str, client_user_id: int) -> Audit:
        audit = Audit(name=name, client_user_id=client_user_id)
        self.db.add(audit)
        self.db.flush()

        catalog = self.db.scalars(select(ControlCatalog)).all()
        for control in catalog:
            ac = AuditControl(audit_id=audit.id, control_id=control.id)
            self.db.add(ac)

        return audit
