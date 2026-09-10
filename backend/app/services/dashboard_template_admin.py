from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.company_dashboard import (
    Company,
    Dashboard,
    DashboardCard,
    DashboardCardCategory,
    DashboardCardStatus,
    DashboardTemplate,
    DashboardTemplateCard,
)
from app.models.dashboard_board import (
    DashboardColumn,
    DashboardColumnKind,
    DashboardTemplateColumn,
)
from app.models.user import User
from app.services.dashboard_board import ColumnKindError, ColumnNotFoundError
from app.services.fractional_index import key_between, n_keys_between
from app.services import dashboard_card_history as history


class CategoryNotFoundError(Exception):
    """Categoria não encontrada — o router converte para 404."""


class CategoryInUseError(Exception):
    """
    Categoria ainda referenciada por algum card/template-card — o
    router converte para 409. Regra deliberadamente simples: exclusão
    bloqueada, não em cascata (perder o agrupamento de dezenas de cards
    por um clique errado seria pior que exigir 1 passo a mais do admin:
    trocar a categoria dos cards antes de excluir a antiga).
    """


class TemplateNotFoundError(Exception):
    """Template não encontrado — o router converte para 404."""


class TemplateCardNotFoundError(Exception):
    """Card de template não encontrado — o router converte para 404."""


class TemplateColumnNotFoundError(Exception):
    """Coluna de template não encontrada — o router converte para 404."""


class TemplateColumnInUseError(Exception):
    """
    Coluna de template ainda referenciada por algum `DashboardTemplateCard`
    — o router converte para 409.

    Mesma regra de `TemplateInUseError`, e pela mesma razão: a FK é
    `ON DELETE SET NULL`, então excluir apagaria em silêncio o vínculo que
    diz em que coluna cada card nasce, e todo dashboard criado depois
    disso nasceria com os cards fora de coluna.
    """


class DefaultTemplateDeletionError(Exception):
    """Tentativa de excluir o template marcado como padrão — o router
    converte para 409. Precisa haver sempre 0 ou 1 template padrão, e
    nunca um "buraco" (nenhum) sem decisão explícita do admin."""


class TemplateInUseError(Exception):
    """
    Template (ou card de template) ainda referenciado por
    `dashboard_cards.origin_template_card_id` — o router converte para
    409. Mesma regra de CategoryInUseError, e pela mesma razão (B-A25):
    a FK é ON DELETE SET NULL, então excluir apagaria em silêncio o
    vínculo que sustenta a idempotência de apply_template_to_company,
    o `is_outdated` e o restore_from_template de TODAS as empresas
    derivadas. Trocar o template dos cards antes de excluir é um passo a
    mais; recuperar o vínculo depois é impossível.
    """


class DashboardNotFoundError(Exception):
    """Empresa sem dashboard (não deveria acontecer para uma empresa
    onboardada por create_company_dashboard_from_template, mas defensivo
    para empresas manuais antigas) — o router converte para 404."""


# ---------------------------------------------------------------- Categorias


def list_categories(db: Session) -> list[DashboardCardCategory]:
    return list(
        db.scalars(
            select(DashboardCardCategory).order_by(
                DashboardCardCategory.sort_order.asc(), DashboardCardCategory.name.asc()
            )
        ).all()
    )


def create_category(
    db: Session, *, name: str, color: str, sort_order: int
) -> DashboardCardCategory:
    category = DashboardCardCategory(name=name, color=color, sort_order=sort_order)
    db.add(category)
    db.flush()
    return category


def update_category(
    db: Session, category_id: int, *, name: str, color: str, sort_order: int
) -> DashboardCardCategory:
    category = db.get(DashboardCardCategory, category_id)
    if category is None:
        raise CategoryNotFoundError("Categoria não encontrada")
    category.name = name
    category.color = color
    category.sort_order = sort_order
    db.flush()
    return category


def delete_category(db: Session, category_id: int) -> None:
    category = db.get(DashboardCardCategory, category_id)
    if category is None:
        raise CategoryNotFoundError("Categoria não encontrada")

    in_use = (
        db.scalar(
            select(func.count(DashboardCard.id)).where(
                DashboardCard.category_id == category_id
            )
        )
        or 0
    )
    in_use += (
        db.scalar(
            select(func.count(DashboardTemplateCard.id)).where(
                DashboardTemplateCard.category_id == category_id
            )
        )
        or 0
    )
    if in_use > 0:
        raise CategoryInUseError(
            f"Categoria em uso por {in_use} card(s)/definição(ões) de template"
        )

    db.delete(category)
    db.flush()


# ---------------------------------------------------------------- Templates
@dataclass
class TemplateWithCount:
    template: DashboardTemplate
    card_count: int


def list_templates(db: Session) -> list[TemplateWithCount]:
    """
    Uma única query com LEFT JOIN + GROUP BY, no lugar de N+1 lazy loads
    de `template.cards` só para chamar len() (B-M24). `outerjoin` para
    que template sem nenhum card apareça com card_count = 0.
    """
    rows = db.execute(
        select(DashboardTemplate, func.count(DashboardTemplateCard.id))
        .outerjoin(
            DashboardTemplateCard,
            DashboardTemplateCard.template_id == DashboardTemplate.id,
        )
        .group_by(DashboardTemplate.id)
        .order_by(DashboardTemplate.name.asc())
    ).all()
    return [
        TemplateWithCount(template=template, card_count=card_count)
        for template, card_count in rows
    ]


def get_template_detail(db: Session, template_id: int) -> DashboardTemplate:
    template = db.get(DashboardTemplate, template_id)
    if template is None:
        raise TemplateNotFoundError("Template não encontrado")
    return template


def _clear_default_flag(db: Session) -> None:
    db.execute(
        update(DashboardTemplate)
        .where(DashboardTemplate.is_default.is_(True))
        .values(is_default=False)
    )


def create_template(
    db: Session, *, name: str, description: str | None, is_default: bool
) -> DashboardTemplate:
    if is_default:
        _clear_default_flag(db)
    template = DashboardTemplate(
        name=name, description=description, is_default=is_default
    )
    db.add(template)
    db.flush()
    return template


def update_template(
    db: Session,
    template_id: int,
    *,
    name: str,
    description: str | None,
    is_default: bool,
) -> DashboardTemplate:
    template = db.get(DashboardTemplate, template_id)
    if template is None:
        raise TemplateNotFoundError("Template não encontrado")

    if is_default and not template.is_default:
        _clear_default_flag(db)

    template.name = name
    template.description = description
    template.is_default = is_default
    db.flush()
    return template


def _cards_derived_from_template(db: Session, template_id: int) -> int:
    """Quantos cards de empresa nasceram de algum card DESTE template."""
    return (
        db.scalar(
            select(func.count(DashboardCard.id))
            .select_from(DashboardCard)
            .join(
                DashboardTemplateCard,
                DashboardTemplateCard.id == DashboardCard.origin_template_card_id,
            )
            .where(DashboardTemplateCard.template_id == template_id)
        )
        or 0
    )


def _cards_derived_from_template_card(db: Session, template_card_id: int) -> int:
    """Quantos cards de empresa nasceram DESTE card de template."""
    return (
        db.scalar(
            select(func.count(DashboardCard.id)).where(
                DashboardCard.origin_template_card_id == template_card_id
            )
        )
        or 0
    )


def delete_template(db: Session, template_id: int) -> None:
    template = db.get(DashboardTemplate, template_id)
    if template is None:
        raise TemplateNotFoundError("Template não encontrado")
    if template.is_default:
        raise DefaultTemplateDeletionError(
            "Defina outro template como padrão antes de excluir este"
        )

    in_use = _cards_derived_from_template(db, template_id)
    if in_use > 0:
        raise TemplateInUseError(
            f"Template em uso por {in_use} card(s) de empresas já configuradas. "
            "Remova ou desvincule esses cards antes de excluir o template."
        )

    db.delete(template)
    db.flush()


def _category_tag(db: Session, category_id: int | None) -> str:
    """
    `tag` continua NOT NULL (schema herdado de antes de O.3 — ver
    migration 4f2b8e6a91d3) mesmo depois de category_id virar a fonte de
    verdade; para todo card/template-card criado ou editado pela UI nova
    (O.4), `tag` é mantida em sincronia com o nome da categoria, evitando
    que os dois campos divirjam de forma visível.
    """
    if category_id is None:
        return "Sem categoria"
    category = db.get(DashboardCardCategory, category_id)
    return category.name if category else "Sem categoria"


# ------------------------------------------------- Colunas de template


def list_template_columns(
    db: Session, template_id: int
) -> list[DashboardTemplateColumn]:
    return list(
        db.scalars(
            select(DashboardTemplateColumn)
            .where(DashboardTemplateColumn.template_id == template_id)
            .order_by(
                DashboardTemplateColumn.position.asc(),
                DashboardTemplateColumn.id.asc(),
            )
        ).all()
    )


def add_template_column(
    db: Session,
    template_id: int,
    *,
    name: str,
    kind: DashboardColumnKind = DashboardColumnKind.COLUMN,
) -> DashboardTemplateColumn:
    """Acrescenta uma coluna no FIM do template."""
    template = db.get(DashboardTemplate, template_id)
    if template is None:
        raise TemplateNotFoundError("Template não encontrado")

    existentes = list_template_columns(db, template_id)
    ultima = existentes[-1].position if existentes else None

    coluna = DashboardTemplateColumn(
        template_id=template.id,
        name=name,
        kind=kind,
        position=key_between(ultima, None),
    )
    db.add(coluna)
    db.flush()
    return coluna


def update_template_column(
    db: Session, template_column_id: int, *, name: str, kind: DashboardColumnKind
) -> DashboardTemplateColumn:
    coluna = db.get(DashboardTemplateColumn, template_column_id)
    if coluna is None:
        raise TemplateColumnNotFoundError("Coluna de template não encontrada")
    coluna.name = name
    coluna.kind = kind
    db.flush()
    return coluna


def move_template_column(
    db: Session,
    template_column_id: int,
    *,
    prev_column_id: int | None,
    next_column_id: int | None,
) -> DashboardTemplateColumn:
    coluna = db.get(DashboardTemplateColumn, template_column_id)
    if coluna is None:
        raise TemplateColumnNotFoundError("Coluna de template não encontrada")

    def _ancora(anchor_id: int | None) -> str | None:
        if anchor_id is None:
            return None
        ancora = db.get(DashboardTemplateColumn, anchor_id)
        if (
            ancora is None
            or ancora.template_id != coluna.template_id
            or ancora.id == coluna.id
        ):
            raise TemplateColumnNotFoundError(
                "Âncora de coluna não pertence a este template"
            )
        return ancora.position

    coluna.position = key_between(_ancora(prev_column_id), _ancora(next_column_id))
    db.flush()
    return coluna


def delete_template_column(db: Session, template_column_id: int) -> None:
    coluna = db.get(DashboardTemplateColumn, template_column_id)
    if coluna is None:
        raise TemplateColumnNotFoundError("Coluna de template não encontrada")

    em_uso = (
        db.scalar(
            select(func.count(DashboardTemplateCard.id)).where(
                DashboardTemplateCard.template_column_id == template_column_id
            )
        )
        or 0
    )
    if em_uso > 0:
        raise TemplateColumnInUseError(
            f"Coluna de template em uso por {em_uso} card(s) de template. "
            "Mova esses cards para outra coluna antes de excluir esta."
        )

    db.delete(coluna)
    db.flush()


def _validate_template_column(
    db: Session, template_id: int, template_column_id: int | None
) -> None:
    """
    Impede vincular um card do template A a uma coluna do template B —
    o quadro resultante teria um card apontando para uma coluna que nunca
    vai existir no dashboard derivado.
    """
    if template_column_id is None:
        return
    coluna = db.get(DashboardTemplateColumn, template_column_id)
    if coluna is None or coluna.template_id != template_id:
        raise TemplateColumnNotFoundError("Coluna de template não encontrada")


# ---------------------------------------------------- Cards de template


def add_template_card(
    db: Session,
    template_id: int,
    *,
    title: str,
    description: str | None,
    category_id: int | None,
    template_column_id: int | None,
    sort_order: int,
) -> DashboardTemplateCard:
    template = db.get(DashboardTemplate, template_id)
    if template is None:
        raise TemplateNotFoundError("Template não encontrado")
    if category_id is not None and db.get(DashboardCardCategory, category_id) is None:
        raise CategoryNotFoundError("Categoria não encontrada")
    _validate_template_column(db, template_id, template_column_id)

    ultima = db.scalar(
        select(func.max(DashboardTemplateCard.position)).where(
            DashboardTemplateCard.template_id == template_id,
            (
                DashboardTemplateCard.template_column_id.is_(None)
                if template_column_id is None
                else DashboardTemplateCard.template_column_id == template_column_id
            ),
        )
    )

    card = DashboardTemplateCard(
        template_id=template.id,
        title=title,
        description=description,
        category_id=category_id,
        template_column_id=template_column_id,
        tag=_category_tag(db, category_id),
        sort_order=sort_order,
        position=key_between(ultima, None),
    )
    db.add(card)
    db.flush()
    return card


def update_template_card(
    db: Session,
    template_card_id: int,
    *,
    title: str,
    description: str | None,
    category_id: int | None,
    template_column_id: int | None,
    sort_order: int,
) -> DashboardTemplateCard:
    card = db.get(DashboardTemplateCard, template_card_id)
    if card is None:
        raise TemplateCardNotFoundError("Card de template não encontrado")
    if category_id is not None and db.get(DashboardCardCategory, category_id) is None:
        raise CategoryNotFoundError("Categoria não encontrada")
    _validate_template_column(db, card.template_id, template_column_id)

    card.title = title
    card.description = description
    card.category_id = category_id
    card.template_column_id = template_column_id
    card.tag = _category_tag(db, category_id)
    card.sort_order = sort_order
    db.flush()
    return card


def delete_template_card(db: Session, template_card_id: int) -> None:
    card = db.get(DashboardTemplateCard, template_card_id)
    if card is None:
        raise TemplateCardNotFoundError("Card de template não encontrado")

    in_use = _cards_derived_from_template_card(db, template_card_id)
    if in_use > 0:
        raise TemplateInUseError(
            f"Card de template em uso por {in_use} card(s) de empresas já "
            "configuradas. Remova esses cards antes de excluir a definição."
        )

    db.delete(card)
    db.flush()


# ---------------------------------------------------------------- Aplicação de template
@dataclass
class ApplyTemplateOutcome:
    created_count: int
    adopted_count: int
    skipped_existing_count: int
    outdated_card_ids: list[int]
    # B-A24 aplicado a colunas: "0 cards criados" com 25 colunas criadas
    # não pode parecer, para o admin, que nada aconteceu.
    columns_created_count: int = 0


def apply_template_to_company(
    db: Session, company, template: DashboardTemplate, actor: User | None = None
) -> ApplyTemplateOutcome:
    """
    Idempotente: cria os `DashboardColumn` e os `DashboardCard` que
    faltam (comparando por `origin_template_column_id` /
    `origin_template_card_id`), nunca sobrescreve nada já existente — só
    sinaliza, em `outdated_card_ids`, quais cards divergem do template
    atual.

    B-A24: cards criados ANTES de O.3 não têm `origin_template_card_id`.
    Para eles, casamos por título e ADOTAMOS o card (gravando o vínculo)
    em vez de criar uma cópia. `adopted_count` deixa isso explícito no
    retorno, para o admin não interpretar "0 criados" como "não fez nada".

    As COLUNAS são criadas numa fase própria ANTES do laço de cards, e
    por dois motivos: o card precisa do `column_id` no momento em que é
    inserido, e a idempotência de coluna repousa na mesma
    `UniqueConstraint` que a de card (R2 do PRD).
    """
    dashboard = db.scalar(select(Dashboard).where(Dashboard.company_id == company.id))
    if dashboard is None:
        raise DashboardNotFoundError("Empresa sem dashboard")

    # ---- Fase 1: colunas ----
    template_columns = list(
        db.scalars(
            select(DashboardTemplateColumn)
            .where(DashboardTemplateColumn.template_id == template.id)
            .order_by(
                DashboardTemplateColumn.position.asc(),
                DashboardTemplateColumn.id.asc(),
            )
        ).all()
    )

    company_columns = list(
        db.scalars(
            select(DashboardColumn)
            .where(DashboardColumn.dashboard_id == dashboard.id)
            .order_by(DashboardColumn.position.asc(), DashboardColumn.id.asc())
        ).all()
    )
    column_by_origin: dict[int, DashboardColumn] = {
        coluna.origin_template_column_id: coluna
        for coluna in company_columns
        if coluna.origin_template_column_id is not None
    }

    faltantes = [
        coluna for coluna in template_columns if coluna.id not in column_by_origin
    ]
    columns_created_count = 0
    criados: list[DashboardCard] = []
    if faltantes:
        ultima = company_columns[-1].position if company_columns else None
        for template_column, position in zip(
            faltantes, n_keys_between(ultima, None, len(faltantes))
        ):
            nova = DashboardColumn(
                dashboard_id=dashboard.id,
                name=template_column.name,
                kind=template_column.kind,
                position=position,
                origin_template_column_id=template_column.id,
            )
            db.add(nova)
            column_by_origin[template_column.id] = nova
            columns_created_count += 1
        # Os ids são necessários para gravar `column_id` nos cards abaixo.
        db.flush()

    # ---- Fase 2: cards ----
    template_cards = db.scalars(
        select(DashboardTemplateCard)
        .where(DashboardTemplateCard.template_id == template.id)
        .order_by(
            DashboardTemplateCard.position.asc(),
            DashboardTemplateCard.sort_order.asc(),
            DashboardTemplateCard.id.asc(),
        )
    ).all()

    company_cards = list(
        db.scalars(
            select(DashboardCard).where(DashboardCard.dashboard_id == dashboard.id)
        ).all()
    )

    existing_by_origin: dict[int, DashboardCard] = {
        card.origin_template_card_id: card
        for card in company_cards
        if card.origin_template_card_id is not None
    }

    # Candidatos à adoção: sem vínculo de origem, indexados por título.
    # Um título repetido entre cards órfãos é ambíguo — não adotamos
    # nenhum dos dois, pelo mesmo motivo da migration a3d81f4c7b02.
    orphans_by_title: dict[str, DashboardCard | None] = {}
    for card in company_cards:
        if card.origin_template_card_id is not None:
            continue
        if card.title in orphans_by_title:
            orphans_by_title[card.title] = None  # ambíguo
        else:
            orphans_by_title[card.title] = card

    max_sort = db.scalar(
        select(func.max(DashboardCard.sort_order)).where(
            DashboardCard.dashboard_id == dashboard.id
        )
    )
    next_sort = (max_sort + 1) if max_sort is not None else 0

    # Última posição por coluna, para o card novo nascer no FIM da coluna
    # dele em vez de disputar chave com os que já estão lá.
    ultima_position: dict[int | None, str | None] = {}
    for card in company_cards:
        atual = ultima_position.get(card.column_id)
        if atual is None or card.position > atual:
            ultima_position[card.column_id] = card.position

    created_count = 0
    adopted_count = 0
    skipped_existing_count = 0
    outdated_card_ids: list[int] = []

    for template_card in template_cards:
        coluna_destino = (
            column_by_origin.get(template_card.template_column_id)
            if template_card.template_column_id is not None
            else None
        )
        column_id = coluna_destino.id if coluna_destino is not None else None

        existing = existing_by_origin.get(template_card.id)

        if existing is None:
            orphan = orphans_by_title.get(template_card.title)
            if orphan is not None:
                orphan.origin_template_card_id = template_card.id
                existing_by_origin[template_card.id] = orphan
                orphans_by_title[template_card.title] = None
                adopted_count += 1
                existing = orphan

        if existing is None:
            position = key_between(ultima_position.get(column_id), None)
            ultima_position[column_id] = position
            novo_card = DashboardCard(
                dashboard_id=dashboard.id,
                title=template_card.title,
                tag=template_card.tag,
                category_id=template_card.category_id,
                # Corrige o defeito de origem: até aqui a descrição
                # do template era descartada em silêncio (O.3).
                description=template_card.description,
                column_id=column_id,
                position=position,
                origin_template_card_id=template_card.id,
                hidden=False,
                status=DashboardCardStatus.EM_ANALISE,
                sort_order=next_sort,
            )
            db.add(novo_card)
            criados.append(novo_card)
            next_sort += 1
            created_count += 1
        else:
            skipped_existing_count += 1
            coluna_de_origem = (
                existing.column.origin_template_column_id
                if existing.column is not None
                else None
            )
            if (
                existing.title != template_card.title
                or existing.category_id != template_card.category_id
                or (existing.description or "") != (template_card.description or "")
                or coluna_de_origem != template_card.template_column_id
            ):
                outdated_card_ids.append(existing.id)

    db.flush()

    # Um evento por card criado, num único `add_all` DEPOIS do flush que
    # atribuiu os ids — nunca um `record` dentro do laço.
    #
    # "Um evento agregado para o quadro" não é possível como UMA linha:
    # `dashboard_card_history_entries.card_id` é obrigatório, e histórico
    # de quadro (sem card) seria outra tabela e outra decisão. O que se
    # agrega aqui é a ESCRITA: aplicar um template de 215 cards custa um
    # INSERT em lote, não 215 idas ao banco.
    history.record_many(
        db,
        [card.id for card in criados],
        history.card_created(template_name=template.name),
        actor,
    )

    return ApplyTemplateOutcome(
        created_count=created_count,
        adopted_count=adopted_count,
        skipped_existing_count=skipped_existing_count,
        outdated_card_ids=outdated_card_ids,
        columns_created_count=columns_created_count,
    )


# ---------------------------------------------------------------- Edição em massa
@dataclass
class BulkOperationOutcome:
    affected_count: int


def bulk_update_cards(
    db: Session,
    company: Company,
    *,
    card_ids: list[int],
    operation: str,
    category_id: int | None,
    column_id: int | None = None,
    actor: User | None = None,
) -> BulkOperationOutcome:
    """
     Aplica uma operação a vários cards de UMA empresa de uma vez — barra
    de ação da aba "Dashboard & Template" (proposta O.4). Filtra por
    `dashboard_id` da própria empresa (não só por `id in card_ids`): um
    id de outra empresa enviado por engano (ou de propósito) é
    silenciosamente ignorado, nunca afeta outro cliente.
    """
    dashboard = db.scalar(select(Dashboard).where(Dashboard.company_id == company.id))
    if dashboard is None:
        raise DashboardNotFoundError("Empresa sem dashboard")

    cards = list(
        db.scalars(
            select(DashboardCard).where(
                DashboardCard.dashboard_id == dashboard.id,
                DashboardCard.id.in_(card_ids),
            )
        ).all()
    )

    affected = 0

    if operation == "hide":
        alterados = [card.id for card in cards if not card.hidden]
        for card in cards:
            if not card.hidden:
                card.hidden = True
                affected += 1
        history.record_many(
            db, alterados, history.visibility_changed(hidden=True), actor
        )
    elif operation == "unhide":
        alterados = [card.id for card in cards if card.hidden]
        for card in cards:
            if card.hidden:
                card.hidden = False
                affected += 1
        history.record_many(
            db, alterados, history.visibility_changed(hidden=False), actor
        )
    elif operation == "remove":
        # Sem registro: `dashboard_card_history_entries.card_id` é
        # `ON DELETE CASCADE`, então a entrada seria apagada no mesmo
        # comando que a criou. Um histórico de card removido teria de
        # viver fora do card — outra tabela, outra decisão, não esta.
        for card in cards:
            db.delete(card)
            affected += 1
    elif operation == "set_category":
        if (
            category_id is not None
            and db.get(DashboardCardCategory, category_id) is None
        ):
            raise CategoryNotFoundError("Categoria não encontrada")
        tag_value = _category_tag(db, category_id)
        for card in cards:
            card.category_id = category_id
            card.tag = tag_value
            affected += 1
        history.record_many(
            db,
            [card.id for card in cards],
            history.category_set(tag_value),
            actor,
        )
    elif operation == "set_column":
        # Mover 50 cards de coluna em lote (O.4 aplicado ao quadro). As
        # duas validações são as mesmas de `move_card`: coluna do mesmo
        # quadro e coluna que aceita card.
        coluna = db.get(DashboardColumn, column_id) if column_id is not None else None
        if column_id is not None:
            if coluna is None or coluna.dashboard_id != dashboard.id:
                raise ColumnNotFoundError("Coluna não encontrada")
            if coluna.kind == DashboardColumnKind.SECTION:
                raise ColumnKindError(
                    "Coluna do tipo seção não aceita cards — ela é um separador visual"
                )
        ultima = db.scalar(
            select(func.max(DashboardCard.position)).where(
                DashboardCard.column_id.is_(None)
                if column_id is None
                else DashboardCard.column_id == column_id
            )
        )
        for card in cards:
            card.column_id = column_id
            ultima = key_between(ultima, None)
            card.position = ultima
            affected += 1
        history.record_many(
            db,
            [card.id for card in cards],
            history.column_set(coluna.name if coluna is not None else None),
            actor,
        )
    elif operation == "restore_from_template":
        restaurados: list[int] = []
        origin_ids = {
            c.origin_template_card_id for c in cards if c.origin_template_card_id
        }
        origin_by_id: dict[int, DashboardTemplateCard] = {}
        if origin_ids:
            origin_by_id = {
                tc.id: tc
                for tc in db.scalars(
                    select(DashboardTemplateCard).where(
                        DashboardTemplateCard.id.in_(origin_ids)
                    )
                ).all()
            }
        # Mapa coluna-de-template -> coluna-do-quadro, para restaurar
        # também a coluna e não só os campos de texto.
        column_by_origin = {
            coluna.origin_template_column_id: coluna
            for coluna in db.scalars(
                select(DashboardColumn).where(
                    DashboardColumn.dashboard_id == dashboard.id
                )
            ).all()
            if coluna.origin_template_column_id is not None
        }
        for card in cards:
            origin = (
                origin_by_id.get(card.origin_template_card_id)
                if card.origin_template_card_id
                else None
            )
            # B-M23: card sem origem (ou com origem já excluída, ver
            # B-A25) NÃO conta como restaurado — reportar sucesso aqui
            # mascarava exatamente o problema que o admin precisa ver.
            if origin is None:
                continue
            card.title = origin.title
            card.category_id = origin.category_id
            card.tag = origin.tag
            card.description = origin.description
            if origin.template_column_id is not None:
                coluna = column_by_origin.get(origin.template_column_id)
                if coluna is not None:
                    card.column_id = coluna.id
            affected += 1
            restaurados.append(card.id)
        history.record_many(
            db, restaurados, history.restored_from_template(), actor
        )
    else:
        raise ValueError(f"Operação desconhecida: {operation}")

    db.flush()
    return BulkOperationOutcome(affected_count=affected)
