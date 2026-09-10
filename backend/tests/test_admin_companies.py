from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.audit import Audit
from app.models.audit_control import AuditControl
from app.models.company_dashboard import (
    Company,
    Dashboard,
    DashboardCard,
    DashboardCardchecklistItem,
    DashboardCardHistoryEntry,
    DashboardCardMessage,
    DashboardCardNote,
    DashboardMessageType,
)
from app.models.company_message import CompanyMessage
from app.models.evidence import Evidence
from app.models.message import Message
from app.models.sub_user_request import SubUserRequest
from app.models.user import User


def test_list_companies_requires_admin(client: TestClient, user_token: str):
    response = client.get(
        "/api/v1/admin/companies", headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403


def test_list_companies_paginated(
    client: TestClient, admin_token: str, company: Company
):
    response = client.get(
        "/api/v1/admin/companies?skip=0&limit=10",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    row = next(item for item in data["items"] if item["id"] == company.id)
    assert row["name"] == company.name
    assert row["principal_email"] == "cliente@test.com"
    assert row["sub_user_count"] == 0


def test_list_companies_search_by_principal_email(
    client: TestClient, admin_token: str, company: Company
):
    response = client.get(
        "/api/v1/admin/companies?search=cliente@test.com",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == company.id

    miss = client.get(
        "/api/v1/admin/companies?search=nao-existe-nunca",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert miss.json()["total"] == 0


def test_get_company_detail_counts(
    client: TestClient,
    admin_token: str,
    db,
    company: Company,
    sub_user: User,
    audit_with_control,
):
    response = client.get(
        f"/api/v1/admin/companies/{company.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sub_user_count"] == 1
    assert data["sub_user_emails"] == [sub_user.email]
    assert data["audit_count"] == 1


def test_get_company_detail_not_found(client: TestClient, admin_token: str):
    response = client.get(
        "/api/v1/admin/companies/999999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


def test_update_company_success(client: TestClient, admin_token: str, company: Company):
    response = client.patch(
        f"/api/v1/admin/companies/{company.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Empresa Renomeada",
            "email": company.email,
            "phone": "11888888888",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Empresa Renomeada"
    assert data["phone"] == "11888888888"


def test_update_company_duplicate_name_returns_409(
    client: TestClient, admin_token: str, db, company: Company
):
    other_principal = User(
        full_name="Outro Principal",
        email="outroprincipal@test.com",
        password_hash="x",
        role="user",
    )
    db.add(other_principal)
    db.flush()
    other_company = Company(
        name="Outra Empresa",
        email="outraempresa@test.com",
        principal_user_id=other_principal.id,
    )
    db.add(other_company)
    db.commit()

    response = client.patch(
        f"/api/v1/admin/companies/{other_company.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": company.name, "email": other_company.email, "phone": None},
    )
    assert response.status_code == 409


def test_update_company_requires_admin(
    client: TestClient, user_token: str, company: Company
):
    response = client.patch(
        f"/api/v1/admin/companies/{company.id}",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"name": company.name, "email": company.email, "phone": None},
    )
    assert response.status_code == 403


def test_delete_company_not_found(client: TestClient, admin_token: str):
    response = client.delete(
        "/api/v1/admin/companies/999999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


def test_delete_company_requires_admin(
    client: TestClient, user_token: str, company: Company
):
    response = client.delete(
        f"/api/v1/admin/companies/{company.id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403


def test_delete_company_cascades_everything(
    client: TestClient,
    admin_token: str,
    db,
    company: Company,
    principal_user: User,
    sub_user: User,
    dashboard: Dashboard,
    dashboard_card: DashboardCard,
    audit_with_control,
):
    """Reproduz o requisito crítico do módulo: excluir a empresa deve
    remover em cascata TODAS as entidades relacionadas — usuário
    principal, sub-usuário, auditoria + controle + evidência + mensagem
    de chat do controle, dashboard + card + nota + checklist + histórico
    + mensagem do card, chat geral da empresa e solicitação de
    sub-usuário — numa única transação, sem deixar registro órfão."""
    audit, audit_control = audit_with_control

    evidence = Evidence(
        audit_control_id=audit_control.id,
        uploaded_by_id=principal_user.id,
        file_name="evidencia.pdf",
        storage_key="empresa-teste/evidencia.pdf",
    )
    db.add(evidence)

    message = Message(
        audit_control_id=audit_control.id,
        author_user_id=principal_user.id,
        message="Segue evidência anexada.",
    )
    db.add(message)

    company_message = CompanyMessage(
        company_id=company.id,
        author_user_id=principal_user.id,
        content="Dúvida geral sobre o processo.",
    )
    db.add(company_message)

    note = DashboardCardNote(
        card_id=dashboard_card.id,
        content="Nota do controle.",
        created_by_user_id=principal_user.id,
    )
    db.add(note)

    checklist_item = DashboardCardchecklistItem(
        card_id=dashboard_card.id,
        title="Item do checklist",
    )
    db.add(checklist_item)

    history_entry = DashboardCardHistoryEntry(
        card_id=dashboard_card.id,
        action="Status alterado",
        actor_user_id=principal_user.id,
    )
    db.add(history_entry)

    card_message = DashboardCardMessage(
        card_id=dashboard_card.id,
        author_user_id=principal_user.id,
        message_type=DashboardMessageType.QUESTION,
        content="Pergunta sobre o card.",
    )
    db.add(card_message)

    sub_user_request = SubUserRequest(
        principal_user_id=principal_user.id,
        requested_full_name="Outro Sub-usuário",
        request_email="outrosubusuario@test.com",
    )
    db.add(sub_user_request)

    db.commit()

    response = client.delete(
        f"/api/v1/admin/companies/{company.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    summary = response.json()
    assert summary["company_id"] == company.id
    assert summary["deleted_principal_user_id"] == principal_user.id
    assert summary["deleted_sub_users"] == 1
    assert summary["deleted_sub_user_requests"] == 1
    assert summary["deleted_audits"] == 1
    assert summary["deleted_audit_controls"] == 1
    assert summary["deleted_dashboard_cards"] == 1
    assert summary["deleted_company_messages"] == 1

    db.expire_all()

    assert db.get(Company, company.id) is None
    assert db.get(User, principal_user.id) is None
    assert db.get(User, sub_user.id) is None
    assert db.get(Audit, audit.id) is None
    assert db.get(AuditControl, audit_control.id) is None
    assert db.get(Evidence, evidence.id) is None
    assert db.get(Message, message.id) is None
    assert db.get(Dashboard, dashboard.id) is None
    assert db.get(DashboardCard, dashboard_card.id) is None
    assert db.get(DashboardCardNote, note.id) is None
    assert db.get(DashboardCardchecklistItem, checklist_item.id) is None
    assert db.get(DashboardCardHistoryEntry, history_entry.id) is None
    assert db.get(DashboardCardMessage, card_message.id) is None
    assert db.get(CompanyMessage, company_message.id) is None
    assert db.get(SubUserRequest, sub_user_request.id) is None


def test_delete_company_without_related_data(
    client: TestClient, admin_token: str, db, company: Company, principal_user: User
):
    """Empresa "vazia" (sem sub-usuário/auditoria/dashboard) também deve
    ser excluída sem erro — os cascades opcionais não podem ser
    obrigatórios."""
    response = client.delete(
        f"/api/v1/admin/companies/{company.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    summary = response.json()
    assert summary["deleted_sub_users"] == 0
    assert summary["deleted_audits"] == 0
    assert summary["deleted_dashboard_cards"] == 0
    assert summary["deleted_company_messages"] == 0

    db.expire_all()
    assert db.get(Company, company.id) is None
    assert db.get(User, principal_user.id) is None


def test_delete_company_removes_evidence_files_from_disk(
    client: TestClient,
    admin_token: str,
    db,
    company,
    principal_user,
    audit_with_control,
):
    """B-A26: excluir a empresa precisa apagar os PDFs de evidência do
    disco, não só os registros — são documentos confidenciais do cliente."""
    from pathlib import Path

    from app.models.evidence import Evidence
    from app.services import storage

    _, audit_control = audit_with_control
    stored = storage.UPLOAD_DIR / "abcdef1234567890.pdf"
    stored.write_bytes(b"%PDF-1.4 conteudo confidencial")

    db.add(
        Evidence(
            audit_control_id=audit_control.id,
            uploaded_by_id=principal_user.id,
            file_name="politica.pdf",
            storage_key=str(stored),
            mime_type="application/pdf",
            size_bytes=stored.stat().st_size,
        )
    )
    db.commit()
    assert stored.exists()

    response = client.delete(
        f"/api/v1/admin/companies/{company.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["deleted_evidence_files"] == 1
    assert not Path(stored).exists()


def test_delete_files_ignores_path_outside_upload_dir(tmp_path):
    """B-A26: um storage_key apontando para fora de uploads/ é recusado."""
    from app.services.storage import delete_files

    fora = tmp_path / "nao_deve_sumir.txt"
    fora.write_text("importante")

    removidos = delete_files([str(fora)])

    assert removidos == 0
    assert fora.exists()
