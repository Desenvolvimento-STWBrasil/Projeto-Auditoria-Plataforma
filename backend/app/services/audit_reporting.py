from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import Audit
from app.models.audit_control import AuditControl
from app.models.control_catalog import ControlCatalog
from app.models.evidence import Evidence
from app.models.message import Message
from app.models.user import User


@dataclass
class EvidenceData:
    id: int
    file_name: str
    mime_type: str | None
    size_bytes: int | None
    created_at: datetime
    uploaded_by_name: str


@dataclass
class MessageData:
    id: int
    content: str
    created_at: datetime
    read_at: datetime | None
    author_user_id: int
    author_full_name: str
    is_from_admin: bool


@dataclass
class AuditControlData:
    id: int
    control_code: str
    control_title: str
    status: str
    evidences: list[EvidenceData] = field(default_factory=list)
    messages: list[MessageData] = field(default_factory=list)


@dataclass
class AuditReportData:
    id: int
    name: str
    status: str
    created_at: datetime
    client_name: str
    controls: list[AuditControlData] = field(default_factory=list)


def load_audit_report_data(db: Session, audit_id: int) -> AuditReportData | None:
    """
    Monta o detalhe completo de uma auditoria — controles do catálogo com
    seu status e a lista de evidências de cada um (incluindo o nome de
    quem enviou). Função única reaproveitada por dois consumidores:
    GET /admin/audits/{id} (JSON, tela /private/admin/auditorias) e
    generate_audit_report_pdf() (PDF, ver services/report_generator.py) —
    garante que a tela e o PDF nunca mostrem dados divergentes por terem
    duas implementações de consulta separadas.

    Retorna None se a auditoria não existir (o chamador decide o 404).
    """

    audit = db.get(Audit, audit_id)
    if audit is None:
        return None

    client = db.get(User, audit.client_user_id)
    client_name = client.full_name if client is not None else "Cliente removido"

    control_rows = db.execute(
        select(AuditControl, ControlCatalog)
        .join(ControlCatalog, ControlCatalog.id == AuditControl.control_id)
        .where(AuditControl.audit_id == audit.id)
        .order_by(ControlCatalog.code.asc())
    ).all()

    control_ids = [ac.id for ac, _ in control_rows]

    # Resolve todas as evidências de todos os controles numa única query
    # (evita N+1 — mesmo cuidado já aplicado em
    # dashboard_cards.py::get_card_details() para actor_user/author_user).
    evidences_by_control: dict[int, list[EvidenceData]] = {
        cid: [] for cid in control_ids
    }
    if control_ids:
        evidence_rows = db.execute(
            select(Evidence, User.full_name)
            .join(User, User.id == Evidence.uploaded_by_id)
            .where(Evidence.audit_control_id.in_(control_ids))
            .order_by(Evidence.created_at.asc())
        ).all()
        for evidence, uploader_name in evidence_rows:
            evidences_by_control[evidence.audit_control_id].append(
                EvidenceData(
                    id=evidence.id,
                    file_name=evidence.file_name,
                    mime_type=evidence.mime_type,
                    size_bytes=evidence.size_bytes,
                    created_at=evidence.created_at,
                    uploaded_by_name=uploader_name,
                )
            )

    # Mesma técnica anti-N+1 acima, agora para o chat "Conversa / Dúvidas"
    # (Message) de cada controle — alimenta a seção nova de mensagens da
    # tela /private/admin/auditorias.
    messages_by_control: dict[int, list[MessageData]] = {
        cid: [] for cid in control_ids
    }
    if control_ids:
        message_rows = db.execute(
            select(Message, User.full_name, User.role)
            .join(User, User.id == Message.author_user_id)
            .where(Message.audit_control_id.in_(control_ids))
            .order_by(Message.created_at.asc())
        ).all()
        for message, author_name, author_role in message_rows:
            messages_by_control[message.audit_control_id].append(
                MessageData(
                    id=message.id,
                    content=message.message,
                    created_at=message.created_at,
                    read_at=message.read_at,
                    author_user_id=message.author_user_id,
                    author_full_name=author_name,
                    is_from_admin=author_role == "admin",
                )
            )

    controls = [
        AuditControlData(
            id=ac.id,
            control_code=catalog.code,
            control_title=catalog.title,
            status=ac.status.value,
            evidences=evidences_by_control.get(ac.id, []),
            messages=messages_by_control.get(ac.id, []),
        )
        for ac, catalog in control_rows
    ]

    return AuditReportData(
        id=audit.id,
        name=audit.name,
        status=audit.status.value,
        created_at=audit.created_at,
        client_name=client_name,
        controls=controls,
    )
