"""
B-A28 / M-23: checklist e histórico são registro interno do auditor.

O BLOCO P (B-A23) fechou a ESCRITA desses dois recursos com precisão, e
deixou a LEITURA aberta. A assimetria era visível dentro do mesmo arquivo:
`notas` de card já eram protegidas na leitura (403 para cliente), mas
`checklist` e `history` voltavam completos no detalhe do card — incluindo
o nome do auditor que executou cada ação.

A asserção que mais importa aqui é `"INTERNO" not in resp.text`: ela pega
vazamento por QUALQUER caminho, inclusive por um campo novo acrescentado
ao response_model no futuro.
"""

from __future__ import annotations

from app.models.company_dashboard import (
    DashboardCardchecklistItem,
    DashboardCardHistoryEntry,
    DashboardCardMessage,
    DashboardCardNote,
    DashboardMessageType,
)

MARCA_CHECKLIST = "INTERNO: conferir contrato de confidencialidade"
MARCA_HISTORICO = "INTERNO: auditor marcou como NAOCONFORME apos revisao"
MARCA_NOTA = "INTERNO: cliente resistente, escalar"
PERGUNTA_DO_CLIENTE = "Qual evidencia devo enviar?"


def _semear_interno(db, card, admin_user, principal_user) -> None:
    db.add(
        DashboardCardchecklistItem(
            card_id=card.id, title=MARCA_CHECKLIST, done=True
        )
    )
    db.add(
        DashboardCardHistoryEntry(
            card_id=card.id,
            action=MARCA_HISTORICO,
            actor_user_id=admin_user.id,
        )
    )
    db.add(
        DashboardCardNote(
            card_id=card.id,
            content=MARCA_NOTA,
            created_by_user_id=admin_user.id,
        )
    )
    db.add(
        DashboardCardMessage(
            card_id=card.id,
            author_user_id=principal_user.id,
            message_type=DashboardMessageType.QUESTION,
            content=PERGUNTA_DO_CLIENTE,
        )
    )
    db.commit()


def test_admin_ve_checklist_e_historico(
    client, db, admin_user, principal_user, admin_token, dashboard_card
):
    _semear_interno(db, dashboard_card, admin_user, principal_user)

    resposta = client.get(
        f"/api/v1/dashboard/cards/{dashboard_card.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo["checklist"]) == 1
    assert len(corpo["history"]) == 1
    assert len(corpo["chat"]) == 1
    assert corpo["history"][0]["actor_user"]["full_name"] == admin_user.full_name


def test_cliente_nao_ve_checklist_nem_historico(
    client, db, admin_user, principal_user, user_token, dashboard_card
):
    _semear_interno(db, dashboard_card, admin_user, principal_user)

    resposta = client.get(
        f"/api/v1/dashboard/cards/{dashboard_card.id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert resposta.status_code == 200, "o cliente continua tendo acesso ao card"
    corpo = resposta.json()
    assert corpo["checklist"] == [], "checklist interno vazou para o cliente (B-A28)"
    assert corpo["history"] == [], "histórico interno vazou para o cliente (B-A28)"
    assert len(corpo["chat"]) == 1, "o chat é bilateral e não pode sumir"
    assert corpo["chat"][0]["content"] == PERGUNTA_DO_CLIENTE
    assert "INTERNO" not in resposta.text


def test_sub_user_nao_ve_checklist_nem_historico(
    client, db, admin_user, principal_user, sub_user_token, dashboard_card
):
    _semear_interno(db, dashboard_card, admin_user, principal_user)

    resposta = client.get(
        f"/api/v1/dashboard/cards/{dashboard_card.id}",
        headers={"Authorization": f"Bearer {sub_user_token}"},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["checklist"] == []
    assert corpo["history"] == []
    assert "INTERNO" not in resposta.text


def test_cliente_continua_sem_acesso_as_notas(
    client, db, admin_user, principal_user, user_token, dashboard_card
):
    """A nota já era protegida; a correção não pode ter afrouxado isso."""
    _semear_interno(db, dashboard_card, admin_user, principal_user)

    resposta = client.get(
        f"/api/v1/dashboard/cards/{dashboard_card.id}/notes",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert resposta.status_code == 403


def test_cliente_continua_vendo_o_status_do_card(
    client, db, admin_user, principal_user, user_token, dashboard_card
):
    """
    B-A23 restringiu a ESCRITA do status. A leitura é legítima: o auditado
    precisa saber como está sendo avaliado.
    """
    _semear_interno(db, dashboard_card, admin_user, principal_user)

    corpo = client.get(
        f"/api/v1/dashboard/cards/{dashboard_card.id}",
        headers={"Authorization": f"Bearer {user_token}"},
    ).json()

    assert corpo["status"] == "EM_ANALISE"
    assert corpo["title"] == dashboard_card.title
