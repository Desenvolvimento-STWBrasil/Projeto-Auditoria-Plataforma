from __future__ import annotations

from typing import Literal

import structlog

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.audit import Audit, AuditStatus
from app.models.audit_control import AuditControl, AuditControlStatus
from app.models.company_dashboard import Company
from app.models.evidence import Evidence
from app.models.message import Message
from app.models.user import User
from app.schemas.admin import (
    AuditControlStatusUpdate,
    AuditCreateRequest,
    AuditDetailOut,
    AuditOut,
    AuditStatusUpdate,
    MessageAdminOut,
)
from app.schemas.audit import MessageCreate
from app.schemas.auth import UserPublic
from app.schemas.pagination import PaginatedResponse
from app.repositories.audit_repository import AuditRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_reporting import load_audit_report_data
from app.core.access import member_user_ids
from app.services.report_generator import generate_audit_report_pdf
from app.services.storage import (
    StorageKeyOutsideUploadDirError,
    get_absolute_path,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/audits", response_model=AuditOut, status_code=201)
def create_audit(
    payload: AuditCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> AuditOut:
    repo = AuditRepository(db)
    audit = repo.create_with_controls(
        name=payload.name,
        client_user_id=payload.client_user_id,
    )
    db.commit()
    db.refresh(audit)
    return AuditOut.model_validate(audit)


@router.get("/audits", response_model=PaginatedResponse[AuditOut])
def list_audits(
    skip: int = 0,
    limit: int = 20,
    company_id: int | None = None,
    db=Depends(get_db),
    admin=Depends(require_admin),
) -> PaginatedResponse[AuditOut]:
    """
    `company_id` (opcional, proposta O.2) filtra pelas auditorias de todos
    os membros de uma empresa (usuário principal + sub-usuários) —
    necessário porque `Audit.client_user_id` referencia diretamente um
    usuário, não uma empresa; alimenta a aba "Auditoria" de
    /private/admin/empresas/{id}. Sem o parâmetro, comportamento idêntico
    ao anterior (todas as auditorias, sem filtro).
    """
    stmt = select(Audit)
    count_stmt = select(func.count()).select_from(Audit)

    if company_id is not None:
        company = db.get(Company, company_id)
        if company is None:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        member_ids = member_user_ids(db, company.principal_user_id)
        stmt = stmt.where(Audit.client_user_id.in_(member_ids))
        count_stmt = count_stmt.where(Audit.client_user_id.in_(member_ids))

    total = db.scalar(count_stmt)
    items = db.scalars(stmt.offset(skip).limit(limit)).all()
    return PaginatedResponse[AuditOut](
        total=total,
        skip=skip,
        limit=limit,
        items=[AuditOut.model_validate(a) for a in items],
    )


@router.get("/audits/{audit_id}", response_model=AuditDetailOut)
def get_audit_detail(
    audit_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> AuditDetailOut:
    """
    Detalhe completo de uma auditoria — controles + evidências de cada
    controle, com o nome de quem enviou cada evidência. Alimenta a tela
    /private/admin/auditorias (proposta L.2) e reaproveita a mesma função
    de carregamento (load_audit_report_data) usada pela geração de PDF
    (proposta L.3), evitando duas implementações divergentes da mesma
    consulta.
    """
    report = load_audit_report_data(db, audit_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
    return AuditDetailOut.model_validate(report)


@router.patch("/audits/{audit_id}/status", response_model=AuditDetailOut)
def update_audit_status(
    audit_id: int,
    payload: AuditStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AuditDetailOut:
    """
     Encerra (ou reabre) formalmente uma auditoria — proposta L.2. Encerrar
    (CLOSED) só é permitido se nenhum AuditControl vinculado estiver em
    EM_ANALISE.
    """
    audit = db.get(Audit, audit_id)
    if audit is None:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")

    if payload.status == AuditStatus.CLOSED:
        pending = db.scalar(
            select(func.count(AuditControl.id)).where(
                AuditControl.audit_id == audit.id,
                AuditControl.status == AuditControlStatus.EM_ANALISE,
            )
        )
        if pending:
            raise HTTPException(
                status_code=409,
                detail=f"{pending} controle(s) ainda em análise - não é possível encerrar",
            )
    audit.status = payload.status
    db.commit()

    report = load_audit_report_data(db, audit_id)
    return AuditDetailOut.model_validate(report)


@router.patch(
    "/audit-controls/{audit_control_id}/status", response_model=AuditDetailOut
)
def update_audit_control_status(
    audit_control_id: int,
    payload: AuditControlStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AuditDetailOut:
    """
    Marca o status de um controle avaliado dentro de uma auditoria
    (Em análise / Parcial / Conforme / Não conforme) — vocabulário
    alinhado ao usado em DashboardCard (ver B-M20 no relatorio_bugs.md).
    Retorna a auditoria completa (mesmo shape de GET /audits/{id}) para o
    frontend atualizar a tela sem precisar de uma segunda chamada.
    """
    control = db.get(AuditControl, audit_control_id)
    if control is None:
        raise HTTPException(status_code=404, detail="Controle não encontrado")

    control.status = payload.status
    db.commit()

    report = load_audit_report_data(db, control.audit_id)
    return AuditDetailOut.model_validate(report)


@router.post(
    "/audit-controls/{audit_control_id}/messages",
    response_model=MessageAdminOut,
    status_code=201,
)
def send_control_message(
    audit_control_id: int,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> MessageAdminOut:
    """
    Resposta do admin na "Conversa / Dúvidas" de um controle — mesmo
    model/tabela (`Message`) já usado pelo cliente em
    `client.py::send_message`, agora também com um autor admin. Sem
    scoping por empresa: admin responde qualquer controle de qualquer
    auditoria.
    """
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Mensagem não pode ser vazia")

    control = db.get(AuditControl, audit_control_id)
    if control is None:
        raise HTTPException(status_code=404, detail="Controle não encontrado")

    message = Message(
        audit_control_id=audit_control_id,
        author_user_id=admin.id,
        message=content,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    return MessageAdminOut(
        id=message.id,
        content=message.message,
        created_at=message.created_at,
        read_at=message.read_at,
        author_user_id=message.author_user_id,
        author_full_name=admin.full_name,
        is_from_admin=True,
    )


@router.patch("/audit-controls/{audit_control_id}/messages/read", status_code=200)
def mark_control_messages_as_read(
    audit_control_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    """
    Marca como lidas as mensagens do controle que não foram escritas por
    um admin (ou seja, as do cliente/sub-usuário) — chamado ao expandir a
    conversa de um controle na tela /private/admin/auditorias. Mesmo
    padrão de `company_messages.py::mark_company_messages_as_read`.
    """
    control = db.get(AuditControl, audit_control_id)
    if control is None:
        raise HTTPException(status_code=404, detail="Controle não encontrado")

    stmt = (
        select(Message)
        .join(User, User.id == Message.author_user_id)
        .where(
            Message.audit_control_id == audit_control_id,
            Message.read_at.is_(None),
            User.role != "admin",
        )
    )
    unread = db.scalars(stmt).all()
    for message in unread:
        message.read_at = func.now()

    db.commit()
    return {"marked_as_read": len(unread)}


@router.get("/messages/unread-count")
def count_unread_control_messages(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    """
    Total de mensagens não lidas (de qualquer cliente/sub-usuário, em
    qualquer controle) — alimenta o badge de "Auditorias" no menu
    superior. Agregado global de propósito: evita o front ter que buscar
    o detalhe de cada auditoria só para somar não lidas.
    """
    stmt = (
        select(func.count(Message.id))
        .join(User, User.id == Message.author_user_id)
        .where(Message.read_at.is_(None), User.role != "admin")
    )
    count = db.scalar(stmt) or 0
    return {"unread_count": count}


@router.get("/audits/{audit_id}/report.pdf")
def download_audit_report(
    audit_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> Response:
    """
    Gera e retorna o PDF consolidado da auditoria — proposta L.3.
    Reaproveita load_audit_report_data (mesma função de GET /audits/{id}),
    garantindo que o PDF e a tela mostrem exatamente os mesmos dados.
    """
    report = load_audit_report_data(db, audit_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")

    pdf_bytes = generate_audit_report_pdf(report)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="auditoria-{audit_id}.pdf"'
        },
    )


@router.get("/evidences/{evidence_id}/download")
def download_evidence(
    evidence_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> FileResponse:
    """
    Serve o arquivo de evidência gravado em disco - proposta L.4
    """
    evidence = db.get(Evidence, evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail="Evidência não encontrada")

    try:
        file_path = get_absolute_path(evidence.storage_key)
    except StorageKeyOutsideUploadDirError:
        # Registro apontando para fora do storage: nunca serve o arquivo.
        # 404 (e não 500) para não revelar a existência do caminho.
        logger.warning(
            "evidence_download_outside_upload_dir",
            evidence_id=evidence.id,
            storage_key=evidence.storage_key,
        )
        raise HTTPException(status_code=404, detail="Evidência não encontrada")

    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail="Arquivo não encontrado no armazenamento"
        )

    return FileResponse(
        path=file_path,
        filename=evidence.file_name,
        media_type=evidence.mime_type or "application/octet-stream",
    )


@router.get("/users", response_model=list[UserPublic])
def list_users_by_role(
    role: Literal["admin", "user", "sub-user"],
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[UserPublic]:
    """Lista usuários filtrados por papel (ex.: todos os clientes principais,
    para telas administrativas de gestão de usuários/empresas)."""
    users = UserRepository(db).list_by_role(role)
    return [
        UserPublic(id=u.id, full_name=u.full_name, email=u.email, role=u.role)
        for u in users
    ]
