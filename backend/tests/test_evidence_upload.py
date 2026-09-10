from __future__ import annotations

import io

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.evidence import Evidence


def test_upload_evidence_success(
    client: TestClient, user_token: str, audit_with_control
):
    # Este é o teste que teria pego o item B.3 nas duas vezes em que
    # regrediu: se os kwargs de Evidence(...) não baterem com o model,
    # o endpoint quebra com TypeError antes mesmo de chegar aqui.
    _audit, audit_control = audit_with_control

    file_content = b"%PDF-1.4 conteudo de teste"
    response = client.post(
        f"/api/v1/client/controls/{audit_control.id}/evidences",
        headers={"Authorization": f"Bearer {user_token}"},
        files={"file": ("evidencia.pdf", io.BytesIO(file_content), "application/pdf")},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "evidencia.pdf"
    assert "id" in data


def test_upload_evidence_persists_correct_columns(
    client: TestClient,
    user_token: str,
    audit_with_control,
    db,
):
    _audit, audit_control = audit_with_control

    file_content = b"conteudo"
    response = client.post(
        f"/api/v1/client/controls/{audit_control.id}/evidences",
        headers={"Authorization": f"Bearer {user_token}"},
        files={"file": ("prova.pdf", io.BytesIO(file_content), "application/pdf")},
    )
    assert response.status_code == 201

    evidence = db.scalar(
        select(Evidence).where(Evidence.audit_control_id == audit_control.id)
    )
    assert evidence is not None
    assert evidence.file_name == "prova.pdf"
    assert evidence.storage_key is not None
    assert evidence.uploaded_by_id is not None
    assert evidence.mime_type == "application/pdf"
    assert evidence.size_bytes == len(file_content)


def test_upload_evidence_rejects_disallowed_extension(
    client: TestClient,
    user_token: str,
    audit_with_control,
):
    _audit, audit_control = audit_with_control

    response = client.post(
        f"/api/v1/client/controls/{audit_control.id}/evidences",
        headers={"Authorization": f"Bearer {user_token}"},
        files={"file": ("malware.exe", io.BytesIO(b"x"), "application/octet-stream")},
    )
    assert response.status_code == 415


def test_upload_evidence_rejects_oversized_file(
    client: TestClient,
    user_token: str,
    audit_with_control,
):
    _audit, audit_control = audit_with_control

    too_big = b"0" * (11 * 1024 * 1024)  # 11MB > limite de 10MB
    response = client.post(
        f"/api/v1/client/controls/{audit_control.id}/evidences",
        headers={"Authorization": f"Bearer {user_token}"},
        files={"file": ("grande.pdf", io.BytesIO(too_big), "application/pdf")},
    )
    assert response.status_code == 413


def test_upload_evidence_without_access_returns_404(
    client: TestClient, db, audit_with_control
):
    from app.core.jwt import create_access_token
    from app.core.security import hash_password
    from app.models.user import User

    _audit, audit_control = audit_with_control

    outro_user = User(
        full_name="Outro Cliente",
        email="outro@test.com",
        password_hash=hash_password("Outro123!"),
        role="user",
    )
    db.add(outro_user)
    db.commit()
    db.refresh(outro_user)
    outro_token = create_access_token(subject=str(outro_user.id), role="user")

    response = client.post(
        f"/api/v1/client/controls/{audit_control.id}/evidences",
        headers={"Authorization": f"Bearer {outro_token}"},
        files={"file": ("evidencia.pdf", io.BytesIO(b"x"), "application/pdf")},
    )
    assert response.status_code == 404


def test_sub_user_can_upload_evidence(
    client: TestClient, sub_user_token: str, audit_with_control
):
    # Regressão do item B.3 ("Pendência residual... autorização não resolve
    # sub-usuário", mesma causa raiz do B.4): upload_evidence checava só
    # Audit.client_user_id == current_user.id, sem resolver parent_user_id
    # para sub-usuários — um sub-user que já via o controle listado em
    # GET /client/controls recebia 404 aqui. Corrigido com
    # _resolve_owner_user_id, compartilhado com list_messages/send_message.
    _audit, audit_control = audit_with_control

    response = client.post(
        f"/api/v1/client/controls/{audit_control.id}/evidences",
        headers={"Authorization": f"Bearer {sub_user_token}"},
        files={"file": ("evidencia.pdf", io.BytesIO(b"conteudo"), "application/pdf")},
    )
    assert response.status_code == 201
