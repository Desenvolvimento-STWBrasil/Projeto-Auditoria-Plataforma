from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_admin
from app.core.access import get_company_with_access, resolve_owner_user_id
from app.db.session import get_db
from app.models.company_dashboard import (
    Company,
    Dashboard,
    DashboardCard,
    DashboardCardCategory,
    DashboardCardchecklistItem,
    DashboardCardHistoryEntry,
    DashboardCardMessage,
    DashboardCardNote,
    DashboardCardStatus,
    DashboardMessageType,
    DashboardTemplate,
)
from app.models.dashboard_board import (
    DashboardColumn,
    DashboardColumnKind,
    DashboardLabel,
)
from app.models.user import User
from app.schemas.dashboard_board import LabelRef
from app.schemas.dashboard_runtime import (
    CardEntryCreateIn,
    CardStatusUpdateIn,
    DashboardCardCreate,
    DashboardCardDetailOut,
    DashboardCardNoteCreate,
    DashboardCardNoteOut,
    DashboardchecklistItem,
    DashboardHistoryOut,
    DashboardMessageOut,
    DashboardStatusSummary,
    DashboardUserRef,
)
from app.schemas.dashboard_templates import (
    ApplyTemplateRequest,
    ApplyTemplateResult,
    BulkCardOperation,
    BulkCardOperationResult,
    DashboardCardWithCategoryOut,
)
from app.services.dashboard_board import ColumnKindError, ColumnNotFoundError
from app.services.dashboard_template_admin import (
    CategoryNotFoundError,
    DashboardNotFoundError,
    apply_template_to_company,
    bulk_update_cards,
)
from app.services import dashboard_card_history as history
from app.services.fractional_index import key_between

from app.core.policy import Action, assert_can, can

#: Qual `Action` autoriza cada tipo de entrada.
#:
#: Substitui o `ADMIN_ONLY_ENTRY_TYPES = frozenset({...})` que vivia aqui:
#: era uma regra de papel escrita à mão, num router, enquanto
#: `WRITE_CARD_HISTORY`, `TOGGLE_CHECKLIST` e `ASK_QUESTION` já existiam em
#: `policy.py` — declaradas e nunca aplicadas em lugar nenhum. Duas fontes
#: de verdade para a mesma pergunta, e a que valia não era a que se
#: revisava num PR.
ENTRY_TYPE_ACTIONS = {
    "CHECKLIST": Action.TOGGLE_CHECKLIST,
    "HISTORY": Action.WRITE_CARD_HISTORY,
    "CHAT_QUESTION": Action.ASK_QUESTION,
    "CHAT_ANSWER": Action.ANSWER_QUESTION,
}

router = APIRouter(prefix="/dashboard", tags=["Dashboard Runtime"])


def _get_card_with_access(
    db: Session, card_id: int, current_user: User
) -> DashboardCard:
    stmt = (
        select(DashboardCard, Company)
        .join(Dashboard, Dashboard.id == DashboardCard.dashboard_id)
        .join(Company, Company.id == Dashboard.company_id)
        .where(DashboardCard.id == card_id)
    )
    row = db.execute(stmt).first()
    if row is not None:
        card, company = row
        if current_user.role == "admin":
            return card
        if company.principal_user_id == resolve_owner_user_id(current_user):
            return card

    # 404 também para card de outra empresa (B-B23) — ver
    # core/access.py::get_company_with_access.
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Card não encontrado ou sem acesso",
    )


def _card_is_outdated(card: DashboardCard) -> bool:
    """
    O card divergiu da definição de template da qual nasceu?

    Desde o quadro Kanban compara quatro coisas, não duas: título,
    categoria, **coluna** e **descrição**. Um card que divergiu do
    template na coluna em que está, ou no texto normativo, está tão
    desatualizado quanto um que divergiu no título — e é justamente a
    divergência de texto que o admin precisa ver para decidir se restaura.

    A comparação de coluna NÃO é `card.column_id != origin.template_column_id`:
    esses dois números vivem em tabelas diferentes (`dashboard_columns` e
    `dashboard_template_columns`) e compará-los diretamente marcaria todo
    card como desatualizado. O que se compara é a ORIGEM da coluna atual
    do card com a coluna de template declarada na definição.
    """
    if card.origin_template_card_id is None or card.origin_template_card is None:
        return False
    origin = card.origin_template_card

    coluna_de_origem = (
        card.column.origin_template_column_id if card.column is not None else None
    )

    return (
        card.title != origin.title
        or card.category_id != origin.category_id
        or (card.description or "") != (origin.description or "")
        or coluna_de_origem != origin.template_column_id
    )


def _label_refs(labels: list[DashboardLabel]) -> list[LabelRef]:
    return [
        LabelRef(id=label.id, name=label.name, color=label.color) for label in labels
    ]


def _card_out(card: DashboardCard) -> DashboardCardWithCategoryOut:
    """Serialização única do card de listagem — antes ela estava repetida
    em três rotas, e os campos novos teriam de entrar nas três."""
    return DashboardCardWithCategoryOut(
        id=card.id,
        control_code=card.control_code,
        title=card.title,
        tag=card.tag,
        status=card.status.value,
        category_id=card.category_id,
        category_name=card.category.name if card.category else None,
        hidden=card.hidden,
        origin_template_card_id=card.origin_template_card_id,
        is_outdated=_card_is_outdated(card),
        column_id=card.column_id,
        position=card.position,
        description=card.description,
        labels=_label_refs(card.labels),
    )


@router.get("/status-summary", response_model=DashboardStatusSummary)
def get_dashboard_status_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DashboardStatusSummary:
    """
    Contagem agregada de cards por status, em UMA única query SQL agrupada
    — alimenta os 4 KPIs do topo da Home (/private/admin), substituindo o
    padrão anterior de buscar a lista completa de cards de TODAS as
    empresas só para somar localmente no frontend (`listAllCardsAction`,
    removida em O.1). Desde O.4, cards ocultos (`hidden=True`) não entram
    na contagem — um card oculto não é mais "trabalho em aberto" aos
    olhos do resumo.
    """
    rows = db.execute(
        select(DashboardCard.status, func.count(DashboardCard.id))
        .where(DashboardCard.hidden.is_(False))
        .group_by(DashboardCard.status)
    ).all()
    counts = {status_enum.value: 0 for status_enum in DashboardCardStatus}
    for status_value, count in rows:
        counts[status_value.value] = count
    return DashboardStatusSummary(
        em_analise=counts["EM_ANALISE"],
        parcial=counts["PARCIAL"],
        conforme=counts["CONFORME"],
        naoconforme=counts["NAOCONFORME"],
    )


@router.get(
    "/companies/{company_id}/cards", response_model=list[DashboardCardWithCategoryOut]
)
def list_cards_by_company(
    company_id: int,
    search: str = Query(default=""),
    include_hidden: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DashboardCardWithCategoryOut]:
    """
    Listagem plana de cards da empresa.

    Continua existindo depois do quadro: é o que alimenta consumidores que
    não querem o agrupamento (busca, exportação, checagens). Quem quer o
    quadro pronto usa `GET /dashboard/companies/{id}/board`.
    """
    get_company_with_access(db, company_id, current_user)

    dashboard = db.scalar(select(Dashboard).where(Dashboard.company_id == company_id))
    if not dashboard:
        return []

    stmt = select(DashboardCard).where(DashboardCard.dashboard_id == dashboard.id)
    if not include_hidden:
        stmt = stmt.where(DashboardCard.hidden.is_(False))
    if search.strip():
        query = f"%{search.strip()}%"
        stmt = stmt.where(
            (DashboardCard.title.ilike(query))
            | (DashboardCard.control_code.ilike(query))
        )

    cards = db.scalars(
        stmt.options(
            selectinload(DashboardCard.category),
            selectinload(DashboardCard.origin_template_card),
            # Sem estes dois, 215 cards custam 430 queries extras (B9):
            # `labels` é M:N e `column` é lida por `_card_is_outdated`.
            selectinload(DashboardCard.labels),
            selectinload(DashboardCard.column),
        )
        # A ordenação passa a ser a do quadro (`position`), e não mais
        # `sort_order` — os dois convergem para os dados existentes
        # porque o backfill da migration c8f1a3e57b90 gerou `position` na
        # ordem `sort_order ASC, id ASC`.
        .order_by(DashboardCard.position.asc(), DashboardCard.id.asc())
    ).all()

    return [_card_out(card) for card in cards]


@router.post(
    "/companies/{company_id}/cards",
    response_model=DashboardCardWithCategoryOut,
    status_code=status.HTTP_201_CREATED,
)
def create_card_for_company(
    company_id: int,
    payload: DashboardCardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> DashboardCardWithCategoryOut:
    """
    Desde O.4, `category_id` é obrigatório (o "+ Adicionar card" da aba
    Dashboard & Template sempre pede uma categoria) — `tag` deixou de ser
    aceito no payload e é derivado do nome da categoria, mesma regra já
    aplicada a `dashboard_template_admin.py::_category_tag`.

    Desde o quadro Kanban, o card nasce DENTRO de uma coluna: o
    "+ Adicionar card" agora vive no rodapé de cada coluna, e a posição é
    calculada com `key_between` a partir do fim daquela coluna — não mais
    `max(sort_order) + 1` sobre o dashboard inteiro.
    """
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada"
        )

    dashboard = db.scalar(select(Dashboard).where(Dashboard.company_id == company_id))
    if not dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard não encontrado"
        )

    category = db.get(DashboardCardCategory, payload.category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")

    column: DashboardColumn | None = None
    if payload.column_id is not None:
        column = db.get(DashboardColumn, payload.column_id)
        # Coluna de outro quadro é indistinguível de coluna inexistente
        # para quem chama (B-B23).
        if column is None or column.dashboard_id != dashboard.id:
            raise HTTPException(status_code=404, detail="Coluna não encontrada")
        if column.kind == DashboardColumnKind.SECTION:
            raise HTTPException(
                status_code=422,
                detail="Coluna do tipo seção não aceita cards — ela é um separador visual",
            )

    max_sort = db.scalar(
        select(func.max(DashboardCard.sort_order)).where(
            DashboardCard.dashboard_id == dashboard.id
        )
    )
    next_sort = (max_sort + 1) if max_sort is not None else 0

    ultima_position = db.scalar(
        select(func.max(DashboardCard.position)).where(
            DashboardCard.dashboard_id == dashboard.id,
            DashboardCard.column_id.is_(None)
            if column is None
            else DashboardCard.column_id == column.id,
        )
    )

    card = DashboardCard(
        dashboard_id=dashboard.id,
        control_code=payload.control_code,
        title=payload.title,
        tag=category.name,
        category_id=category.id,
        description=payload.description,
        column_id=column.id if column is not None else None,
        position=key_between(ultima_position, None),
        status=DashboardCardStatus(payload.status),
        sort_order=next_sort,
    )
    db.add(card)
    # `flush` antes do registro: o histórico referencia `card.id`, que só
    # existe depois do INSERT.
    db.flush()
    history.record(db, card.id, history.card_created(), current_user)
    db.commit()
    db.refresh(card)

    return _card_out(card)


@router.post(
    "/companies/{company_id}/apply-template",
    response_model=ApplyTemplateResult,
)
def apply_template_to_company_endpoint(
    company_id: int,
    payload: ApplyTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ApplyTemplateResult:
    """
    Aplica um template numa empresa já existente — proposta O.4, §3.5 do
    documento de origem ("Planta do Dashboard"). Idempotente: chamado 2x
    seguidas com o mesmo template, a segunda chamada não cria nada novo
    (ver services/dashboard_template_admin.py::apply_template_to_company).
    """
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    template = db.get(DashboardTemplate, payload.template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template não encontrado")

    try:
        outcome = apply_template_to_company(db, company, template, current_user)
        db.commit()
    except DashboardNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Empresa sem dashboard")

    return ApplyTemplateResult(
        created_count=outcome.created_count,
        adopted_count=outcome.adopted_count,
        already_applied_count=outcome.skipped_existing_count,
        outdated_card_ids=outcome.outdated_card_ids,
        columns_created_count=outcome.columns_created_count,
    )


@router.patch(
    "/companies/{company_id}/cards/bulk",
    response_model=BulkCardOperationResult,
)
def bulk_update_company_cards(
    company_id: int,
    payload: BulkCardOperation,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> BulkCardOperationResult:
    """
    Ocultar / reexibir / mudar categoria / mudar coluna / remover /
    restaurar do template, em lote, sobre os cards de UMA empresa — a
    peça de UI que faltava para "50 cards" deixar de ser 50 cliques
    (proposta O.4, §3.4 do documento de origem). `card_ids` de outra
    empresa são filtrados silenciosamente pelo service (ver
    bulk_update_cards).
    """
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    if payload.operation == "set_category" and payload.category_id is None:
        raise HTTPException(
            status_code=422,
            detail="category_id é obrigatório para a operação set_category",
        )

    if payload.operation == "set_column" and payload.column_id is None:
        raise HTTPException(
            status_code=422,
            detail="column_id é obrigatório para a operação set_column",
        )

    try:
        outcome = bulk_update_cards(
            db,
            company,
            card_ids=payload.card_ids,
            operation=payload.operation,
            category_id=payload.category_id,
            column_id=payload.column_id,
            actor=current_user,
        )
        db.commit()
    except DashboardNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Empresa sem dashboard")
    except CategoryNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    except ColumnNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Coluna não encontrada")
    except ColumnKindError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))

    return BulkCardOperationResult(affected_count=outcome.affected_count)


@router.get("/cards/{card_id}", response_model=DashboardCardDetailOut)
def get_card_details(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardCardDetailOut:
    """
    Detalhe de um card.

    O chat é bilateral e sempre visível às duas partes. O **checklist** e o
    **histórico** são registro interno da equipe de auditoria (B-A28): o
    cliente vê listas vazias, não 403 — o card existe e ele tem direito de
    vê-lo, apenas não a essas duas coleções. Manter o mesmo formato de
    resposta evita quebrar qualquer consumidor e mantém a semântica
    honesta ("nada a exibir para você aqui"), em vez de fingir que o card
    não tem checklist.

    Efeito colateral bem-vindo: para papel não-admin, duas queries deixam
    de ser executadas.

    A `description` NÃO segue essa regra: ela é o texto normativo do
    controle, e é exatamente o que o cliente precisa ler para saber o que
    entregar (U7). Vai para os dois papéis.
    """
    card = _get_card_with_access(db, card_id, current_user)

    pode_ver_interno = can(Action.READ_CARD_INTERNALS, current_user.role)

    checklist: list[DashboardCardchecklistItem] = []
    history: list[DashboardCardHistoryEntry] = []
    if pode_ver_interno:
        checklist = list(
            db.scalars(
                select(DashboardCardchecklistItem)
                .where(DashboardCardchecklistItem.card_id == card.id)
                .order_by(DashboardCardchecklistItem.id.asc())
            ).all()
        )
        history = list(
            db.scalars(
                select(DashboardCardHistoryEntry)
                .where(DashboardCardHistoryEntry.card_id == card.id)
                .order_by(DashboardCardHistoryEntry.id.asc())
            ).all()
        )

    chat = db.scalars(
        select(DashboardCardMessage)
        .where(DashboardCardMessage.card_id == card.id)
        .order_by(DashboardCardMessage.id.asc())
    ).all()

    user_ids = {
        item.actor_user_id for item in history if item.actor_user_id is not None
    }
    user_ids |= {item.author_user_id for item in chat}
    users_by_id: dict[int, User] = {}
    if user_ids:
        rows = db.scalars(select(User).where(User.id.in_(user_ids))).all()
        users_by_id = {u.id: u for u in rows}

    def _user_ref(user_id: int | None) -> DashboardUserRef | None:
        user = users_by_id.get(user_id) if user_id is not None else None
        if user is None:
            return None
        return DashboardUserRef(id=user.id, full_name=user.full_name)

    return DashboardCardDetailOut(
        id=card.id,
        control_code=card.control_code,
        title=card.title,
        tag=card.tag,
        status=card.status.value,
        description=card.description,
        column_id=card.column_id,
        category_id=card.category_id,
        category_name=card.category.name if card.category else None,
        labels=_label_refs(card.labels),
        checklist=[
            DashboardchecklistItem(
                id=item.id,
                title=item.title,
                done=item.done,
            )
            for item in checklist
        ],
        history=[
            DashboardHistoryOut(
                id=item.id,
                action=item.action,
                created_at=item.created_at,
                actor_user=_user_ref(item.actor_user_id),
            )
            for item in history
        ],
        chat=[
            DashboardMessageOut(
                id=item.id,
                message_type=item.message_type.value,
                content=item.content,
                created_at=item.created_at,
                author_user=_user_ref(item.author_user_id),
            )
            for item in chat
        ],
    )


@router.patch("/cards/{card_id}/status", response_model=DashboardCardWithCategoryOut)
def update_card_status(
    card_id: int,
    payload: CardStatusUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> DashboardCardWithCategoryOut:
    """
    Status de conformidade é declaração DO AUDITOR sobre o auditado —
    restrito a admin (B-A23). O cliente continua VENDO o status em
    GET /dashboard/companies/{id}/cards; só não pode alterá-lo.
    """
    assert_can(Action.SET_CARD_STATUS, current_user.role)  # permissão
    card = _get_card_with_access(db, card_id, current_user)  # escopo

    anterior = card.status
    novo = DashboardCardStatus(payload.status)
    card.status = novo
    # Só registra se MUDOU: clicar duas vezes em "Conforme" não é
    # movimentação, e um histórico cheio de "Conforme -> Conforme"
    # esconde os eventos que importam.
    if anterior != novo:
        history.record(
            db, card.id, history.status_changed(anterior, novo), current_user
        )
    db.commit()
    db.refresh(card)

    return _card_out(card)


@router.post("/cards/{card_id}/entries", status_code=status.HTTP_201_CREATED)
def create_card_entry(
    card_id: int,
    payload: CardEntryCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    card = _get_card_with_access(db, card_id, current_user)

    # B-A23: checklist, histórico e resposta de chat são registro do
    # auditor. Só CHAT_QUESTION é escrita legítima do cliente. Quem
    # declara isso é `policy.py`, não este router.
    acao = ENTRY_TYPE_ACTIONS.get(payload.entry_type)
    if acao is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de entrada inválido"
        )
    assert_can(acao, current_user.role)

    if payload.entry_type == "CHECKLIST":
        db.add(
            DashboardCardchecklistItem(
                card_id=card.id, title=payload.content, done=False
            )
        )
        history.record(
            db,
            card.id,
            history.checklist_item_added(payload.content),
            current_user,
        )
    elif payload.entry_type == "HISTORY":
        db.add(
            DashboardCardHistoryEntry(
                card_id=card.id,
                action=payload.content,
                actor_user_id=current_user.id,
            )
        )
    elif payload.entry_type == "CHAT_QUESTION":
        db.add(
            DashboardCardMessage(
                card_id=card.id,
                author_user_id=current_user.id,
                message_type=DashboardMessageType.QUESTION,
                content=payload.content,
            )
        )
    elif payload.entry_type == "CHAT_ANSWER":
        db.add(
            DashboardCardMessage(
                card_id=card.id,
                author_user_id=current_user.id,
                message_type=DashboardMessageType.ANSWER,
                content=payload.content,
            )
        )

    db.commit()
    return {"message": "Entrada criada com sucesso"}


@router.patch("/checklist-items/{item_id}/toggle", status_code=status.HTTP_200_OK)
def toggle_checklist_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """
    Checklist interno da equipe de auditoria — restrito a admin (B-A23).
    A checagem de posse por empresa deixa de ser necessária: o admin tem
    acesso a todas as empresas por definição, e o cliente não tem acesso
    nenhum a esta rota.
    """
    assert_can(Action.TOGGLE_CHECKLIST, current_user.role)
    item = db.get(DashboardCardchecklistItem, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado"
        )

    item.done = not item.done
    history.record(
        db,
        item.card_id,
        history.checklist_item_toggled(item.title, done=item.done),
        current_user,
    )
    db.commit()
    db.refresh(item)
    return {"ok": True, "done": item.done}


@router.delete(
    "/checklist-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_checklist_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    """
    Remove um item de checklist.

    Faltava o par de `POST /cards/{id}/entries` com `entry_type=CHECKLIST`:
    dava para criar e marcar, nunca para desfazer. Um item criado com
    texto errado ficava no card para sempre, contando no denominador do
    progresso ("0 de 3 concluídos") e empurrando a barra para baixo sem
    ter como sair.

    Exclusão de verdade, e não `hidden`: um item de checklist não tem
    histórico próprio nem é referenciado por nada — ao contrário de card e
    coluna, que arquivam justamente porque outras coisas apontam para
    eles. Restrito a admin, como o resto do checklist (B-A23).
    """
    assert_can(Action.TOGGLE_CHECKLIST, current_user.role)
    item = db.get(DashboardCardchecklistItem, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado"
        )

    # O texto do item é lido ANTES do delete: depois do `db.delete` o
    # objeto vira transiente e `item.title` deixa de ser confiável — o
    # histórico registraria "Item de checklist removido: " sem dizer qual.
    history.record(
        db,
        item.card_id,
        history.checklist_item_removed(item.title),
        current_user,
    )
    db.delete(item)
    db.commit()


@router.post(
    "/cards/{card_id}/notes",
    response_model=DashboardCardNoteOut,
    status_code=status.HTTP_201_CREATED,
)
def create_card_note(
    card_id: int,
    payload: DashboardCardNoteCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> DashboardCardNoteOut:
    """
    Cria uma nota interna no card — anotação da equipe de auditoria, distinta
    do chat (DashboardCardMessage), que é o canal de Q&A com o cliente.
    Restrito a admin: notas são um registro interno, não visível/editável
    pelo cliente (ao contrário do chat e do checklist).
    """
    card = db.get(DashboardCard, card_id)
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Card não encontrado"
        )

    note = DashboardCardNote(
        card_id=card.id,
        content=payload.content,
        created_by_user_id=admin.id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    return DashboardCardNoteOut(
        id=note.id,
        content=note.content,
        created_by_user_id=note.created_by_user_id,
        created_by_name=admin.full_name,
        created_at=note.created_at,
    )


@router.get("/cards/{card_id}/notes", response_model=list[DashboardCardNoteOut])
def list_card_notes(
    card_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[DashboardCardNoteOut]:
    card = db.get(DashboardCard, card_id)
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Card não encontrado"
        )

    rows = db.execute(
        select(DashboardCardNote, User.full_name)
        .join(User, User.id == DashboardCardNote.created_by_user_id)
        .where(DashboardCardNote.card_id == card_id)
        .order_by(DashboardCardNote.id.asc())
    ).all()

    return [
        DashboardCardNoteOut(
            id=note.id,
            content=note.content,
            created_by_user_id=note.created_by_user_id,
            created_by_name=full_name,
            created_at=note.created_at,
        )
        for note, full_name in rows
    ]
