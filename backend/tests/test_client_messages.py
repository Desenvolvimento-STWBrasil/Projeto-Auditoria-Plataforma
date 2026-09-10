from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.message import Message


def test_send_message_success(
    client: TestClient, user_token: str, audit_with_control
):
    _audit, audit_control = audit_with_control

    response = client.post(
        f"/api/v1/client/controls/{audit_control.id}/messages",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"content": "Qual evidência vocês esperam para este controle?"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "Qual evidência vocês esperam para este controle?"
    assert "id" in data
    assert "created_at" in data


def test_send_message_persists_and_list_returns_it(
    client: TestClient, user_token: str, audit_with_control, db
):
    _audit, audit_control = audit_with_control

    post_response = client.post(
        f"/api/v1/client/controls/{audit_control.id}/messages",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"content": "Dúvida enviada pelo cliente"},
    )
    assert post_response.status_code == 201

    message = db.scalar(
        select(Message).where(Message.audit_control_id == audit_control.id)
    )
    assert message is not None
    assert message.message == "Dúvida enviada pelo cliente"
    assert message.author_user_id is not None

    list_response = client.get(
        f"/api/v1/client/controls/{audit_control.id}/messages",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert list_response.status_code == 200
    messages = list_response.json()
    assert len(messages) == 1
    assert messages[0]["content"] == "Dúvida enviada pelo cliente"
    assert messages[0]["author_id"] is not None


def test_send_message_rejects_empty_content(
    client: TestClient, user_token: str, audit_with_control
):
    _audit, audit_control = audit_with_control

    response = client.post(
        f"/api/v1/client/controls/{audit_control.id}/messages",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"content": "   "},
    )
    assert response.status_code == 422


def test_send_message_rejects_non_string_content(
    client: TestClient, user_token: str, audit_with_control
):
    # Este é o teste que teria pego a regressão do item B.4: antes da
    # correção, send_message recebia payload: dict não tipado e fazia
    # payload.get("content", "").strip() — um content que não fosse string
    # (ex. um número) quebrava com AttributeError (500) em vez de um 422
    # de validação bem tratado. Com o schema MessageCreate(content: str),
    # o FastAPI/Pydantic rejeita antes mesmo de a view rodar.
    _audit, audit_control = audit_with_control

    response = client.post(
        f"/api/v1/client/controls/{audit_control.id}/messages",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"content": 12345},
    )
    assert response.status_code == 422


def test_messages_without_access_returns_404(
    client: TestClient, db, audit_with_control
):
    from app.core.jwt import create_access_token
    from app.core.security import hash_password
    from app.models.user import User

    _audit, audit_control = audit_with_control

    outro_user = User(
        full_name="Outro Cliente",
        email="outro-mensagens@test.com",
        password_hash=hash_password("Outro123!"),
        role="user",
    )
    db.add(outro_user)
    db.commit()
    db.refresh(outro_user)
    outro_token = create_access_token(subject=str(outro_user.id), role="user")

    get_response = client.get(
        f"/api/v1/client/controls/{audit_control.id}/messages",
        headers={"Authorization": f"Bearer {outro_token}"},
    )
    assert get_response.status_code == 404

    post_response = client.post(
        f"/api/v1/client/controls/{audit_control.id}/messages",
        headers={"Authorization": f"Bearer {outro_token}"},
        json={"content": "Não deveria conseguir enviar"},
    )
    assert post_response.status_code == 404


def test_sub_user_can_send_and_list_messages(
    client: TestClient, sub_user_token: str, audit_with_control
):
    # Regressão do item B.4 ("Dois problemas adicionais"): list_messages/
    # send_message checavam só Audit.client_user_id == current_user.id, sem
    # resolver parent_user_id para sub-usuários — um sub-user que já via o
    # controle listado em GET /client/controls recebia 404 aqui. Corrigido
    # com _resolve_owner_user_id, compartilhado com upload_evidence (B.3).
    _audit, audit_control = audit_with_control

    post_response = client.post(
        f"/api/v1/client/controls/{audit_control.id}/messages",
        headers={"Authorization": f"Bearer {sub_user_token}"},
        json={"content": "Mensagem enviada pelo sub-usuário"},
    )
    assert post_response.status_code == 201

    list_response = client.get(
        f"/api/v1/client/controls/{audit_control.id}/messages",
        headers={"Authorization": f"Bearer {sub_user_token}"},
    )
    assert list_response.status_code == 200
    messages = list_response.json()
    assert len(messages) == 1
    assert messages[0]["content"] == "Mensagem enviada pelo sub-usuário"


def test_sub_user_without_parent_link_gets_400(client: TestClient, db):
    from app.core.jwt import create_access_token
    from app.core.security import hash_password
    from app.models.user import User

    orphan_sub_user = User(
        full_name="Sub-usuário Órfão",
        email="orfao@test.com",
        password_hash=hash_password("Orfao123!"),
        role="sub-user",
        parent_user_id=None,
    )
    db.add(orphan_sub_user)
    db.commit()
    db.refresh(orphan_sub_user)
    orphan_token = create_access_token(subject=str(orphan_sub_user.id), role="sub-user")

    response = client.get(
        "/api/v1/client/controls/1/messages",
        headers={"Authorization": f"Bearer {orphan_token}"},
    )
    assert response.status_code == 400
