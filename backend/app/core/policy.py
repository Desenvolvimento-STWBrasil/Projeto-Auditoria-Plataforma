from __future__ import annotations

import enum

from fastapi import HTTPException, status


class Action(str, enum.Enum):
    """
    Ações cujo direito NÃO decorre de posse. Existe porque posse e
    permissão são coisas diferentes numa plataforma de auditoria: o
    cliente é dono dos próprios cards e evidências, mas quem declara
    conformidade é o auditor (ver B-A23 em docs/relatorio_bugs.md).

    Desde B-A28 o enum cobre também LEITURA. O enum nasceu da pergunta
    "quem pode declarar conformidade?" e respondeu só a ela; leitura
    ficou fora do vocabulário, então cada endpoint decidia sozinho — e
    `get_card_details` decidiu não decidir. O registro interno do auditor
    (checklist e histórico) é confidencial em relação ao auditado, do
    mesmo modo que a escrita é privativa dele.
    """

    SET_CARD_STATUS = "SET_CARD_STATUS"
    SET_CONTROL_STATUS = "SET_CONTROL_STATUS"
    WRITE_CARD_HISTORY = "WRITE_CARD_HISTORY"
    TOGGLE_CHECKLIST = "TOGGLE_CHECKLIST"
    WRITE_CARD_NOTE = "WRITE_CARD_NOTE"
    CLOSE_AUDIT = "CLOSE_AUDIT"
    MANAGE_TEMPLATE = "MANAGE_TEMPLATE"
    MANAGE_CATEGORY = "MANAGE_CATEGORY"
    DELETE_COMPANY = "DELETE_COMPANY"
    # Leitura de registro interno do auditor (B-A28):
    READ_CARD_INTERNALS = "READ_CARD_INTERNALS"
    # Escritas legítimas do lado auditado:
    UPLOAD_EVIDENCE = "UPLOAD_EVIDENCE"
    ASK_QUESTION = "ASK_QUESTION"
    # Responder no chat do card é fala DA auditoria: o cliente pergunta
    # (ASK_QUESTION), o auditor responde. Nasceu junto com a substituição
    # do `ADMIN_ONLY_ENTRY_TYPES` de dashboard_cards.py — era o único dos
    # quatro tipos de entrada sem ação declarada aqui.
    ANSWER_QUESTION = "ANSWER_QUESTION"
    REQUEST_SUB_USER = "REQUEST_SUB_USER"
    # Quadro Kanban (PRD §4.4). O quadro é LEITURA para o cliente e
    # ESCRITA só para o auditor, pela mesma razão de B-A23: a disposição
    # do quadro é a leitura que o auditor faz do andamento da due
    # diligence, não um espaço de trabalho compartilhado. O cliente vê o
    # quadro inteiro em GET /dashboard/companies/{id}/board — só não o
    # rearranja.
    MANAGE_COLUMN = "MANAGE_COLUMN"  # criar/renomear/mover/arquivar/excluir coluna
    MOVE_CARD = "MOVE_CARD"  # arrastar card entre e dentro de colunas
    MANAGE_LABEL = "MANAGE_LABEL"  # criar/renomear/mover/arquivar/excluir label
    # Editar o TEXTO do card (título, descrição, código, categoria). Era a
    # única escrita do quadro que decidia sozinha, com `require_admin`
    # solto no router e sem linha nesta tabela — do lado de fora o efeito
    # é o mesmo, mas a decisão não estava declarada em lugar nenhum, e é
    # exatamente esse tipo de omissão que deixou B-A28 passar.
    EDIT_CARD = "EDIT_CARD"


# Fonte única de verdade. Uma linha aqui é mais fácil de revisar num PR
# do que uma condição espalhada por 11 routers.
ALLOWED_ROLES: dict[Action, frozenset[str]] = {
    Action.SET_CARD_STATUS: frozenset({"admin"}),
    Action.SET_CONTROL_STATUS: frozenset({"admin"}),
    Action.WRITE_CARD_HISTORY: frozenset({"admin"}),
    Action.TOGGLE_CHECKLIST: frozenset({"admin"}),
    Action.WRITE_CARD_NOTE: frozenset({"admin"}),
    Action.CLOSE_AUDIT: frozenset({"admin"}),
    Action.MANAGE_TEMPLATE: frozenset({"admin"}),
    Action.MANAGE_CATEGORY: frozenset({"admin"}),
    Action.DELETE_COMPANY: frozenset({"admin"}),
    Action.READ_CARD_INTERNALS: frozenset({"admin"}),
    Action.UPLOAD_EVIDENCE: frozenset({"user", "sub-user"}),
    Action.ASK_QUESTION: frozenset({"admin", "user", "sub-user"}),
    Action.ANSWER_QUESTION: frozenset({"admin"}),
    Action.REQUEST_SUB_USER: frozenset({"user"}),
    Action.MANAGE_COLUMN: frozenset({"admin"}),
    Action.MOVE_CARD: frozenset({"admin"}),
    Action.MANAGE_LABEL: frozenset({"admin"}),
    Action.EDIT_CARD: frozenset({"admin"}),
}


def can(action: Action, role: str) -> bool:
    """True se `role` pode executar `action`."""
    return role in ALLOWED_ROLES[action]


def assert_can(action: Action, role: str) -> None:
    """Levanta 403 se `role` não pode executar `action`."""
    if not can(action, role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Papel '{role}' não pode executar {action.value}",
        )
