from __future__ import annotations

"""
Registro de movimentações de um card.

A tabela `dashboard_card_history_entries` existe desde D.6, o endpoint de
leitura devolve o histórico desde então, e a tela sempre soube exibi-lo —
mas **nada no sistema o escrevia**. As únicas escritas eram
`POST /cards/{id}/entries` com `entry_type=HISTORY` (manual, e sem
consumidor até esta entrega) e o `seed_demo_companies.py`. Ou seja: o
histórico que aparecia num card de demonstração era dado semeado, e num
card real ele ficava vazio para sempre.

Este módulo é o único lugar onde o TEXTO de um evento é decidido. Estava
prestes a nascer espalhado por quatro routers e dois services, e um
histórico de auditoria em que a mesma mudança é descrita de duas formas
diferentes dependendo de onde foi feita não serve para auditar nada.

Segue a camada praticada na base (B4): `db.add`, nunca `db.commit()` —
quem controla a transação é o router. Não damos `flush()` a cada entrada
de propósito: em operação em lote isso seria um round-trip por card, e o
`flush`/`commit` de quem chamou persiste tudo junto.
"""

from app.models.company_dashboard import (
    DashboardCardHistoryEntry,
    DashboardCardStatus,
)
from app.models.user import User
from sqlalchemy.orm import Session

#: `DashboardCardHistoryEntry.action` é `String(255)`. Título de card vai a
#: 160 caracteres e descrição é `Text`, então uma frase do tipo "X alterado
#: de <antigo> para <novo>" estoura a coluna com facilidade — em MySQL isso
#: é erro de inserção, e derrubaria a operação de negócio (salvar o card)
#: por causa do registro dela.
ACTION_MAX_LENGTH = 255

STATUS_LABELS: dict[DashboardCardStatus, str] = {
    DashboardCardStatus.EM_ANALISE: "Em análise",
    DashboardCardStatus.PARCIAL: "Parcial",
    DashboardCardStatus.CONFORME: "Conforme",
    DashboardCardStatus.NAOCONFORME: "Não conforme",
}


def _fit(action: str) -> str:
    """Trunca preservando o começo — é onde está o que mudou."""
    if len(action) <= ACTION_MAX_LENGTH:
        return action
    return action[: ACTION_MAX_LENGTH - 1] + "…"


def status_label(status: DashboardCardStatus) -> str:
    """
    Rótulo em pt-BR do status.

    O histórico guarda TEXTO, não referência: uma entrada escrita hoje
    continua dizendo "Conforme" mesmo que o rótulo mude amanhã. Para um
    registro de auditoria isso é o comportamento certo — ele preserva o
    que foi dito na época, não o vocabulário de agora.
    """
    return STATUS_LABELS.get(status, status.value)


def record(
    db: Session,
    card_id: int,
    action: str,
    actor: User | None = None,
) -> DashboardCardHistoryEntry:
    """Registra UMA movimentação. `actor` nulo = ação sem usuário
    atribuível (script, migração, automação)."""
    entry = DashboardCardHistoryEntry(
        card_id=card_id,
        action=_fit(action),
        actor_user_id=actor.id if actor is not None else None,
    )
    db.add(entry)
    return entry


def record_many(
    db: Session,
    card_ids: list[int],
    action: str,
    actor: User | None = None,
) -> None:
    """
    Mesma movimentação em vários cards — o caso da barra de ação em lote
    e da aplicação de template.

    Um `add` por card e um `flush` só no fim (o de quem chamou): é o que
    mantém "aplicar template em 215 cards" com custo previsível.
    """
    texto = _fit(action)
    actor_id = actor.id if actor is not None else None
    db.add_all(
        [
            DashboardCardHistoryEntry(
                card_id=card_id, action=texto, actor_user_id=actor_id
            )
            for card_id in card_ids
        ]
    )


# ------------------------------------------------------------- Mensagens
#
# Uma função por tipo de evento, e não strings soltas nos call sites: é
# isso que garante que "mudou de coluna" se leia igual quer tenha vindo
# do arrasto, do menu "Mover para…" ou da ação em lote.


def card_created(*, template_name: str | None = None) -> str:
    if template_name:
        return f"Card criado pela aplicação do template {template_name}"
    return "Card criado"


def status_changed(
    anterior: DashboardCardStatus, novo: DashboardCardStatus
) -> str:
    return (
        f"Status alterado de {status_label(anterior)} "
        f"para {status_label(novo)}"
    )


def fields_changed(mudancas: list[str]) -> str:
    """`mudancas` já vem descrita campo a campo por `describe_change`."""
    return "Card editado: " + "; ".join(mudancas)


def describe_change(campo: str, anterior: str | None, novo: str | None) -> str:
    """
    Um campo que mudou, em texto.

    Vazio e nulo são a mesma coisa aos olhos de quem lê o histórico
    ("(vazio)"), embora sejam diferentes no banco — a distinção importa
    para a coluna, não para a frase.
    """
    de = anterior if anterior else "(vazio)"
    para = novo if novo else "(vazio)"
    return f"{campo} de “{de}” para “{para}”"


def column_changed(anterior: str | None, novo: str | None) -> str:
    return (
        f"Movido de {anterior or 'Sem coluna'} para {novo or 'Sem coluna'}"
    )


def reordered_within_column(nome_da_coluna: str | None) -> str:
    return f"Reordenado em {nome_da_coluna or 'Sem coluna'}"


def category_changed(anterior: str | None, novo: str | None) -> str:
    return (
        f"Categoria alterada de {anterior or '(nenhuma)'} "
        f"para {novo or '(nenhuma)'}"
    )


def category_set(novo: str | None) -> str:
    """
    Versão em LOTE de `category_changed`: sem o "de".

    Cinquenta cards têm cinquenta categorias de origem diferentes, e ler
    cada uma para compor "de X para Y" custaria uma consulta por card —
    justamente o que a ação em lote existe para evitar. "Alterada para Y"
    é menos informação, mas é verdade; "de (nenhuma) para Y" seria
    barato e mentiroso.
    """
    return f"Categoria alterada para {novo or '(nenhuma)'} (ação em lote)"


def column_set(novo: str | None) -> str:
    """Versão em lote de `column_changed`, pelo mesmo motivo."""
    return f"Movido para {novo or 'Sem coluna'} (ação em lote)"


def visibility_changed(*, hidden: bool) -> str:
    return "Card arquivado" if hidden else "Card reexibido"


def checklist_item_added(titulo: str) -> str:
    return f"Item de checklist adicionado: {titulo}"


def checklist_item_removed(titulo: str) -> str:
    return f"Item de checklist removido: {titulo}"


def checklist_item_toggled(titulo: str, *, done: bool) -> str:
    estado = "concluído" if done else "reaberto"
    return f"Item de checklist {estado}: {titulo}"


def restored_from_template() -> str:
    return "Card restaurado a partir da definição do template"


def labels_changed(nomes: list[str]) -> str:
    if not nomes:
        return "Etiquetas removidas"
    return "Etiquetas definidas: " + ", ".join(nomes)
