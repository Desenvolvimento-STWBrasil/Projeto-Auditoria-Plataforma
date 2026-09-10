from __future__ import annotations

import io

from fastapi.testclient import TestClient


def test_get_audit_detail_includes_controls_and_evidences(
    client: TestClient, admin_token: str, user_token: str, audit_with_control
):
    audit, audit_control = audit_with_control
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_client = {"Authorization": f"Bearer {user_token}"}

    upload = client.post(
        f"/api/v1/client/controls/{audit_control.id}/evidences",
        headers=headers_client,
        files={"file": ("evidencia.pdf", io.BytesIO(b"conteudo"), "application/pdf")},
    )
    assert upload.status_code == 201

    response = client.get(f"/api/v1/admin/audits/{audit.id}", headers=headers_admin)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == audit.id
    assert data["client_name"] == "Cliente Teste"
    assert len(data["controls"]) == 1
    control = data["controls"][0]
    assert control["status"] == "EM_ANALISE"
    assert len(control["evidences"]) == 1
    assert control["evidences"][0]["file_name"] == "evidencia.pdf"
    assert control["evidences"][0]["uploaded_by_name"] == "Cliente Teste"


def test_get_audit_detail_requires_admin(
    client: TestClient, user_token: str, audit_with_control
):
    audit, _ = audit_with_control
    response = client.get(
        f"/api/v1/admin/audits/{audit.id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403


def test_get_audit_detail_not_found(client: TestClient, admin_token: str):
    response = client.get(
        "/api/v1/admin/audits/999999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


def test_close_audit_blocked_while_controls_pending(
    client: TestClient, admin_token: str, audit_with_control
):
    audit, _ = audit_with_control
    headers = {"Authorization": f"Bearer {admin_token}"}

    response = client.patch(
        f"/api/v1/admin/audits/{audit.id}/status",
        headers=headers,
        json={"status": "CLOSED"},
    )
    assert response.status_code == 409
    assert "em análise" in response.json()["detail"]


def test_close_audit_succeeds_when_all_controls_resolved(
    client: TestClient, admin_token: str, audit_with_control, db
):
    from app.models.audit_control import AuditControlStatus

    audit, audit_control = audit_with_control
    audit_control.status = AuditControlStatus.CONFORME
    db.commit()

    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.patch(
        f"/api/v1/admin/audits/{audit.id}/status",
        headers=headers,
        json={"status": "CLOSED"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CLOSED"


def test_close_audit_requires_admin(
    client: TestClient, user_token: str, audit_with_control
):
    audit, _ = audit_with_control
    response = client.patch(
        f"/api/v1/admin/audits/{audit.id}/status",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"status": "CLOSED"},
    )
    assert response.status_code == 403


def test_update_control_status_to_naoconforme(
    client: TestClient, admin_token: str, user_token: str, audit_with_control
):
    audit, audit_control = audit_with_control
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_client = {"Authorization": f"Bearer {user_token}"}

    response = client.patch(
        f"/api/v1/admin/audit-controls/{audit_control.id}/status",
        headers=headers_admin,
        json={"status": "NAOCONFORME"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == audit.id
    assert data["controls"][0]["status"] == "NAOCONFORME"

    # o cliente enxerga o mesmo status marcado pelo admin
    client_controls = client.get(
        "/api/v1/client/controls", headers=headers_client
    ).json()
    assert client_controls[0]["status"] == "NAOCONFORME"


def test_update_control_status_requires_admin(
    client: TestClient, user_token: str, audit_with_control
):
    _, audit_control = audit_with_control
    response = client.patch(
        f"/api/v1/admin/audit-controls/{audit_control.id}/status",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"status": "NAOCONFORME"},
    )
    assert response.status_code == 403


def test_update_control_status_not_found(client: TestClient, admin_token: str):
    response = client.patch(
        "/api/v1/admin/audit-controls/999999/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "NAOCONFORME"},
    )
    assert response.status_code == 404


def test_download_audit_report_returns_pdf(
    client: TestClient, admin_token: str, audit_with_control
):
    audit, _ = audit_with_control
    headers = {"Authorization": f"Bearer {admin_token}"}

    response = client.get(
        f"/api/v1/admin/audits/{audit.id}/report.pdf", headers=headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"


def test_download_audit_report_not_found(client: TestClient, admin_token: str):
    response = client.get(
        "/api/v1/admin/audits/999999/report.pdf",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


def test_download_evidence_returns_file_content(
    client: TestClient, admin_token: str, user_token: str, audit_with_control
):
    audit, audit_control = audit_with_control
    headers_client = {"Authorization": f"Bearer {user_token}"}
    headers_admin = {"Authorization": f"Bearer {admin_token}"}

    upload = client.post(
        f"/api/v1/client/controls/{audit_control.id}/evidences",
        headers=headers_client,
        files={
            "file": (
                "evidencia.pdf",
                io.BytesIO(b"conteudo-teste"),
                "application/pdf",
            )
        },
    )
    evidence_id = upload.json()["id"]

    response = client.get(
        f"/api/v1/admin/evidences/{evidence_id}/download", headers=headers_admin
    )
    assert response.status_code == 200
    assert response.content == b"conteudo-teste"
    assert "evidencia.pdf" in response.headers["content-disposition"]


def test_download_evidence_requires_admin(
    client: TestClient, user_token: str, audit_with_control
):
    audit, audit_control = audit_with_control
    headers_client = {"Authorization": f"Bearer {user_token}"}

    upload = client.post(
        f"/api/v1/client/controls/{audit_control.id}/evidences",
        headers=headers_client,
        files={"file": ("evidencia.pdf", io.BytesIO(b"x"), "application/pdf")},
    )
    evidence_id = upload.json()["id"]

    response = client.get(
        f"/api/v1/admin/evidences/{evidence_id}/download",
        headers=headers_client,
    )
    assert response.status_code == 403


def test_download_evidence_not_found(client: TestClient, admin_token: str):
    response = client.get(
        "/api/v1/admin/evidences/999999/download",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


def test_get_audit_detail_includes_client_messages(
    client: TestClient, admin_token: str, user_token: str, audit_with_control
):
    audit, audit_control = audit_with_control
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_client = {"Authorization": f"Bearer {user_token}"}

    client.post(
        f"/api/v1/client/controls/{audit_control.id}/messages",
        headers=headers_client,
        json={"content": "Qual evidência vocês esperam para este controle?"},
    )

    response = client.get(f"/api/v1/admin/audits/{audit.id}", headers=headers_admin)
    assert response.status_code == 200
    messages = response.json()["controls"][0]["messages"]
    assert len(messages) == 1
    assert messages[0]["content"] == "Qual evidência vocês esperam para este controle?"
    assert messages[0]["is_from_admin"] is False
    assert messages[0]["read_at"] is None


def test_send_control_message_by_admin(
    client: TestClient, admin_token: str, audit_with_control
):
    _audit, audit_control = audit_with_control

    response = client.post(
        f"/api/v1/admin/audit-controls/{audit_control.id}/messages",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"content": "Segue orientação sobre a evidência esperada."},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "Segue orientação sobre a evidência esperada."
    assert data["is_from_admin"] is True


def test_send_control_message_requires_admin(
    client: TestClient, user_token: str, audit_with_control
):
    _audit, audit_control = audit_with_control

    response = client.post(
        f"/api/v1/admin/audit-controls/{audit_control.id}/messages",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"content": "Não deveria conseguir"},
    )
    assert response.status_code == 403


def test_send_control_message_not_found(client: TestClient, admin_token: str):
    response = client.post(
        "/api/v1/admin/audit-controls/999999/messages",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"content": "Controle inexistente"},
    )
    assert response.status_code == 404


def test_send_control_message_rejects_empty_content(
    client: TestClient, admin_token: str, audit_with_control
):
    _audit, audit_control = audit_with_control

    response = client.post(
        f"/api/v1/admin/audit-controls/{audit_control.id}/messages",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"content": "   "},
    )
    assert response.status_code == 422


def test_control_messages_unread_count_and_mark_as_read(
    client: TestClient, admin_token: str, user_token: str, audit_with_control
):
    _audit, audit_control = audit_with_control
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_client = {"Authorization": f"Bearer {user_token}"}

    client.post(
        f"/api/v1/client/controls/{audit_control.id}/messages",
        headers=headers_client,
        json={"content": "Primeira dúvida"},
    )
    client.post(
        f"/api/v1/client/controls/{audit_control.id}/messages",
        headers=headers_client,
        json={"content": "Segunda dúvida"},
    )
    # mensagem do próprio admin não deve contar como não lida
    client.post(
        f"/api/v1/admin/audit-controls/{audit_control.id}/messages",
        headers=headers_admin,
        json={"content": "Resposta do admin"},
    )

    unread = client.get("/api/v1/admin/messages/unread-count", headers=headers_admin)
    assert unread.status_code == 200
    assert unread.json()["unread_count"] == 2

    mark_read = client.patch(
        f"/api/v1/admin/audit-controls/{audit_control.id}/messages/read",
        headers=headers_admin,
    )
    assert mark_read.status_code == 200
    assert mark_read.json()["marked_as_read"] == 2

    unread_after = client.get(
        "/api/v1/admin/messages/unread-count", headers=headers_admin
    )
    assert unread_after.json()["unread_count"] == 0


def test_control_messages_unread_count_requires_admin(
    client: TestClient, user_token: str
):
    response = client.get(
        "/api/v1/admin/messages/unread-count",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403
