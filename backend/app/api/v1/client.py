from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence import Evidence
from app.api.deps import get_current_user
from app.core.access import resolve_owner_user_id
from app.db.session import get_db
from app.models.audit_control import AuditControl
from app.models.audit import Audit
from app.models.control_catalog import ControlCatalog
from app.models.user import User
from app.models.message import Message
from app.repositories.audit_repository import AuditRepository
from app.schemas.admin import AuditOut
from app.schemas.audit import ClientControlItem, MessageCreate
from app.services.storage import save_file

router = APIRouter(prefix="/client", tags=["Client"])

MAX_UPLOAD_MB = 10
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".docx", ".xlsx"}
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024  # 1 MB


async def _read_limited(file: UploadFile, max_bytes: int) -> bytes:
    """
    Lê o upload em blocos e aborta assim que ultrapassa `max_bytes`
    (B-M22). O `await file.read()` direto materializava o arquivo inteiro
    na RAM ANTES da checagem de tamanho — um upload de 2 GB derrubava o
    worker antes de receber o 413 que deveria tê-lo barrado.
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(UPLOAD_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Arquivo maior que {MAX_UPLOAD_MB}MB",
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.get("/controls", response_model=list[ClientControlItem])
def list_client_controls(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ClientControlItem]:
    """
    Retorna todos controless (instanciados) pertencentes ao cliente logado
    """

    if current_user.role not in ("user", "sub-user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso apenas para user/sub-user",
        )
    owner_user_id = resolve_owner_user_id(current_user)

    stmt = (
        select(
            Audit.id,
            Audit.name,
            AuditControl.id,
            AuditControl.status,
            ControlCatalog.code,
            ControlCatalog.title,
            ControlCatalog.description,
            ControlCatalog.expected_evidence,
        )
        .join(AuditControl, AuditControl.audit_id == Audit.id)
        .join(ControlCatalog, ControlCatalog.id == AuditControl.control_id)
        .where(Audit.client_user_id == owner_user_id)
        .order_by(Audit.id.desc(), ControlCatalog.code.asc())
    )

    rows = db.execute(stmt).all()

    return [
        ClientControlItem(
            audit_id=row[0],
            audit_name=row[1],
            audit_control_id=row[2],
            status=row[3],
            control_code=row[4],
            control_title=row[5],
            control_description=row[6],
            expected_evidence=row[7],
        )
        for row in rows
    ]


@router.get("/audits", response_model=list[AuditOut])
def list_my_audits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AuditOut]:
    """Lista as auditorias do cliente logado (tela "minhas auditorias"),
    sem o detalhamento por controle já coberto por GET /client/controls."""
    if current_user.role not in ("user", "sub-user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso apenas para user/sub-user",
        )
    owner_user_id = resolve_owner_user_id(current_user)
    audits = AuditRepository(db).list_by_client(owner_user_id)
    return [AuditOut.model_validate(a) for a in audits]


@router.get("/audits/{audit_id}", response_model=AuditOut)
def get_my_audit(
    audit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuditOut:
    """Detalhe de uma auditoria específica do cliente logado."""
    if current_user.role not in ("user", "sub-user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso apenas para user/sub-user",
        )
    owner_user_id = resolve_owner_user_id(current_user)
    audit = AuditRepository(db).get_by_id(audit_id)
    if audit is None or audit.client_user_id != owner_user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Auditoria não encontrada ou sem acesso",
        )
    return AuditOut.model_validate(audit)


@router.post("/controls/{audit_control_id}/evidences", status_code=201)
async def upload_evidence(
    audit_control_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    # Verificar owership do audit_control
    ac = db.scalar(
        select(AuditControl)
        .join(
            Audit, Audit.id == AuditControl.audit_id
        )  # JOIN correto — já foi bug, hoje está certo
        .where(
            AuditControl.id == audit_control_id,
            Audit.client_user_id == resolve_owner_user_id(current_user),
        )
    )
    if not ac:
        raise HTTPException(
            status_code=404, detail="Controle não encontrado ou sem acesso"
        )

    # Validar extensão ANTES de ler qualquer byte (B-M22): recusar um
    # arquivo de 2 GB pelo nome custa nada; recusá-lo depois de lê-lo
    # custa 2 GB de RAM.
    filename = file.filename or "upload.bin"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415, detail=f"Tipo de arquivo não permitido: {ext}"
        )

    # Ler com teto de memória (B-M22)
    content = await _read_limited(file, MAX_UPLOAD_BYTES)

    file_path = await save_file(content, filename)

    evidence = Evidence(
        audit_control_id=audit_control_id,
        storage_key=file_path,
        file_name=filename,
        uploaded_by_id=current_user.id,
        mime_type=file.content_type,
        size_bytes=len(content),
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    return {"id": evidence.id, "file_path": file_path, "filename": filename}


@router.get("/controls/{audit_control_id}/messages")
def list_messages(
    audit_control_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    ac = db.scalar(
        select(AuditControl)
        .join(Audit, Audit.id == AuditControl.audit_id)
        .where(
            AuditControl.id == audit_control_id,
            Audit.client_user_id == resolve_owner_user_id(current_user),
        )
    )
    if not ac:
        raise HTTPException(
            status_code=404, detail="Controle não encontrado ou sem acesso"
        )

    messages = db.scalars(
        select(Message)
        .where(Message.audit_control_id == audit_control_id)
        .order_by(Message.created_at.asc())
    ).all()

    return [
        {
            "id": m.id,
            "content": m.message,
            "author_id": m.author_user_id,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


@router.post("/controls/{audit_control_id}/messages", status_code=201)
def send_message(
    audit_control_id: int,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Mensagem não pode ser vazia")

    ac = db.scalar(
        select(AuditControl)
        .join(Audit, Audit.id == AuditControl.audit_id)
        .where(
            AuditControl.id == audit_control_id,
            Audit.client_user_id == resolve_owner_user_id(current_user),
        )
    )
    if not ac:
        raise HTTPException(
            status_code=404, detail="Controle não encontrado ou sem acesso"
        )

    msg = Message(
        audit_control_id=audit_control_id,
        author_user_id=current_user.id,
        message=content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return {
        "id": msg.id,
        "content": msg.message,
        "created_at": msg.created_at.isoformat(),
    }
