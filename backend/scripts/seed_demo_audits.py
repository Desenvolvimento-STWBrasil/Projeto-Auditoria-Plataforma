"""
Seed de dados de demonstração para a aba Auditorias (Audit/AuditControl).

Continuação de scripts/seed_demo_companies.py: usa os mesmos 5 clientes
principais fictícios já criados por aquele script para popular auditorias
reais — cada uma com todos os controles do catálogo (scripts/seed_catalog.py,
já expandido com o mesmo tema ISO/IEC 27001:2022 usado no dashboard),
avaliados com status variado, evidências em PDF de verdade salvas em
uploads/ (o botão "baixar evidência" funciona) e mensagens de chat por
controle nos itens não conformes.

Pré-requisito: rodar scripts/seed_demo_companies.py antes (cria as 5
empresas/usuários principais usados aqui). Empresa cujo principal não for
encontrado é pulada com aviso.

Idempotente por nome de auditoria + cliente: rodar de novo não duplica.

Uso:
    cd backend
    ./venv/Scripts/python.exe scripts/seed_demo_audits.py
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.audit import Audit, AuditStatus
from app.models.audit_control import AuditControl, AuditControlStatus
from app.models.control_catalog import ControlCatalog
from app.models.evidence import Evidence
from app.models.message import Message
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from scripts.seed_catalog import SEED_CONTROLS, seed_controls

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

NOW = datetime.now(timezone.utc)

CO = AuditControlStatus.CONFORME
PA = AuditControlStatus.PARCIAL
NA = AuditControlStatus.NAOCONFORME
EM = AuditControlStatus.EM_ANALISE


def _at(days_ago: float, hour: int = 10) -> datetime:
    return (NOW - timedelta(days=days_ago)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )


class DemoAudit:
    def __init__(
        self,
        *,
        principal_email: str,
        name: str,
        status: AuditStatus,
        created_days_ago: float,
        control_statuses: list[AuditControlStatus],
    ) -> None:
        self.principal_email = principal_email
        self.name = name
        self.status = status
        self.created_days_ago = created_days_ago
        self.control_statuses = control_statuses


# Mesma escala de maturidade por empresa usada em seed_demo_companies.py
# (TechNova avançada, Horizonte inicial, GreenAgro equilibrada, Vitalis
# crítica, Nortex intermediária) e mesma ordem de controles do catálogo
# (5.1, 5.2, 5.3, 5.7, 5.23, 6.3, 7.4, 8.8, 8.24).
DEMO_AUDITS: list[DemoAudit] = [
    DemoAudit(
        principal_email="marina.ferreira@technova.com.br",
        name="Auditoria Anual 2025",
        status=AuditStatus.CLOSED,
        created_days_ago=95,
        control_statuses=[CO, CO, CO, PA, CO, CO, CO, PA, CO],
    ),
    DemoAudit(
        principal_email="marina.ferreira@technova.com.br",
        name="Auditoria de Acompanhamento 2026",
        status=AuditStatus.ACTIVE,
        created_days_ago=20,
        control_statuses=[CO, CO, CO, PA, CO, CO, EM, PA, CO],
    ),
    DemoAudit(
        principal_email="eduardo.souza@horizonteconstrutora.com.br",
        name="Auditoria Inicial 2026",
        status=AuditStatus.ACTIVE,
        created_days_ago=10,
        control_statuses=[EM, EM, PA, NA, EM, EM, EM, NA, PA],
    ),
    DemoAudit(
        principal_email="eduardo.souza@horizonteconstrutora.com.br",
        name="Auditoria de Certificação 2027",
        status=AuditStatus.DRAFT,
        created_days_ago=2,
        control_statuses=[EM, EM, EM, EM, EM, EM, EM, EM, EM],
    ),
    DemoAudit(
        principal_email="camila.alves@greenagro.com.br",
        name="Auditoria Anual 2026",
        status=AuditStatus.ACTIVE,
        created_days_ago=45,
        control_statuses=[CO, PA, EM, NA, PA, CO, EM, PA, NA],
    ),
    DemoAudit(
        principal_email="rafael.costa@vitalissaude.com.br",
        name="Auditoria de Conformidade 2026",
        status=AuditStatus.ACTIVE,
        created_days_ago=60,
        control_statuses=[NA, PA, CO, NA, PA, EM, CO, PA, NA],
    ),
    DemoAudit(
        principal_email="juliana.pires@nortexlog.com.br",
        name="Auditoria Anual 2026",
        status=AuditStatus.ACTIVE,
        created_days_ago=30,
        control_statuses=[PA, PA, EM, CO, PA, NA, EM, PA, PA],
    ),
]


def _make_evidence_pdf(
    *, control_code: str, control_title: str, company_hint: str, submitted_by: str, date_str: str
) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(595, 400))
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, 350, "Evidência de Auditoria")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, 320, f"Controle {control_code} — {control_title}")
    pdf.drawString(50, 300, f"Empresa: {company_hint}")
    pdf.drawString(50, 280, f"Enviado por: {submitted_by}")
    pdf.drawString(50, 260, f"Data: {date_str}")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        50,
        220,
        "Documento comprobatório referente ao atendimento deste controle,",
    )
    pdf.drawString(50, 205, "anexado durante o ciclo de auditoria (dado de demonstração).")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _save_evidence_pdf(content: bytes) -> tuple[str, int]:
    filename = f"{uuid.uuid4().hex}.pdf"
    dest = UPLOAD_DIR / filename
    dest.write_bytes(content)
    return str(dest), len(content)


def build_audit(db: Session, admin: User, demo: DemoAudit) -> None:
    principal = db.scalar(select(User).where(User.email == demo.principal_email))
    if principal is None:
        print(f"  principal não encontrado, pulando: {demo.principal_email} — rode "
              f"scripts/seed_demo_companies.py primeiro.")
        return

    existing = db.scalar(
        select(Audit).where(
            Audit.client_user_id == principal.id, Audit.name == demo.name
        )
    )
    if existing:
        print(f"  já existe, pulando: {demo.name} ({demo.principal_email})")
        return

    created_at = _at(demo.created_days_ago, hour=9)

    audit = AuditRepository(db).create_with_controls(
        name=demo.name, client_user_id=principal.id
    )
    audit.status = demo.status
    audit.created_at = created_at
    db.flush()

    rows = db.execute(
        select(AuditControl, ControlCatalog)
        .join(ControlCatalog, ControlCatalog.id == AuditControl.control_id)
        .where(AuditControl.audit_id == audit.id)
        .order_by(ControlCatalog.id.asc())
    ).all()

    asker = db.scalar(
        select(User).where(User.parent_user_id == principal.id)
    ) or principal

    evidence_count = 0
    message_count = 0

    for index, ((control, catalog), status) in enumerate(
        zip(rows, demo.control_statuses)
    ):
        control.status = status
        review_at = created_at + timedelta(days=2 + index)
        control.created_at = created_at
        control.updated_at = review_at

        if status in (CO, PA):
            pdf_bytes = _make_evidence_pdf(
                control_code=catalog.code,
                control_title=catalog.title,
                company_hint=demo.name,
                submitted_by=principal.full_name,
                date_str=review_at.strftime("%d/%m/%Y"),
            )
            storage_key, size_bytes = _save_evidence_pdf(pdf_bytes)
            db.add(
                Evidence(
                    audit_control_id=control.id,
                    uploaded_by_id=principal.id,
                    file_name=f"evidencia-{catalog.code}.pdf",
                    storage_key=storage_key,
                    mime_type="application/pdf",
                    size_bytes=size_bytes,
                    created_at=review_at,
                )
            )
            evidence_count += 1

        if status == NA:
            db.add(
                Message(
                    audit_control_id=control.id,
                    author_user_id=asker.id,
                    message=(
                        f"Bom dia! Sobre o controle {catalog.code} ({catalog.title}): "
                        "o que exatamente está pendente para sairmos de não "
                        "conformidade?"
                    ),
                    created_at=review_at + timedelta(hours=2),
                )
            )
            db.add(
                Message(
                    audit_control_id=control.id,
                    author_user_id=admin.id,
                    message=(
                        "Bom dia! Falta o documento oficial assinado pela área "
                        "responsável, além da evidência de que a comunicação "
                        "chegou às equipes envolvidas. Pode reenviar até o "
                        "fechamento deste ciclo?"
                    ),
                    created_at=review_at + timedelta(hours=5),
                )
            )
            message_count += 2

    db.flush()
    print(
        f"  criada: {demo.name} ({principal.email}) — status={demo.status.value}, "
        f"{len(rows)} controles, {evidence_count} evidência(s), {message_count} mensagem(ns)"
    )


def main() -> None:
    with SessionLocal() as db:
        try:
            admin = db.scalar(select(User).where(User.role == "admin"))
            if admin is None:
                raise RuntimeError(
                    "Nenhum usuário admin encontrado — rode scripts/seed_admin.py primeiro."
                )

            seed_controls(db, SEED_CONTROLS)
            db.flush()
            print(f"Catálogo de controles: {len(SEED_CONTROLS)} controle(s) garantido(s).")

            for demo in DEMO_AUDITS:
                build_audit(db, admin, demo)

            db.commit()
            print("\nSeed de auditorias de demonstração concluído.")
        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main()
