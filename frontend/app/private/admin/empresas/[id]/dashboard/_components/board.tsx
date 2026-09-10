"use client";

import { useMemo, useState, type ReactNode } from "react";
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  closestCorners,
  useSensor,
  useSensors,
  type Announcements,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";

import type {
  Board as BoardData,
  BoardCard as BoardCardData,
  BoardColumn as BoardColumnData,
} from "../actions";
import { BoardCard } from "./board-card";
import { BoardColumn } from "./board-column";

/** Intenção de mover um card, na forma que o backend espera (âncoras). */
export type MoveIntent = {
  cardId: number;
  columnId: number | null;
  prevCardId: number | null;
  nextCardId: number | null;
};

export type ColumnMenuHandlers = {
  onRenameColumn: (column: BoardColumnData) => void;
  onArchiveColumn: (column: BoardColumnData) => void;
  onDeleteColumn: (column: BoardColumnData) => void;
  onMoveColumn: (column: BoardColumnData, direcao: -1 | 1) => void;
  onAddCard: (column: BoardColumnData) => void;
};

type BoardProps = {
  board: BoardData;
  readOnly?: boolean;
  selectedCardId: number | null;
  onSelectCard: (cardId: number) => void;
  selectedCardIds?: Set<number>;
  onToggleCardSelection?: (cardId: number) => void;
  onToggleColumnSelection?: (column: BoardColumnData) => void;
  collapsedColumns?: Set<number>;
  onToggleColumnCollapse?: (columnId: number) => void;
  onMoveCard?: (intent: MoveIntent) => void;
  columnHandlers?: ColumnMenuHandlers;
  outdatedCardIds?: number[];
  addCardColumnId?: number | null;
  addCardSlot?: ReactNode;
};

const PREFIXO_CARD = "card:";
const PREFIXO_COLUNA = "column:";
const PREFIXO_AREA = "column-drop:";

/** Todos os cards do quadro, incluindo o balde `uncolumned`. */
export function allCards(board: BoardData): BoardCardData[] {
  return [
    ...board.columns.flatMap((coluna) => coluna.cards),
    ...board.uncolumned,
  ];
}

/**
 * Aplica um movimento de card ao quadro, em memória.
 *
 * Função PURA e exportada de propósito: é ela que o `useOptimistic` do
 * `company-dashboard-client.tsx` usa para reposicionar o card na hora, e
 * é ela que os testes exercitam sem precisar simular arrasto (jsdom não
 * simula). A `position` de verdade vem do servidor; aqui só a ORDEM
 * importa.
 */
export function moveCardInBoard(
  board: BoardData,
  intent: MoveIntent,
): BoardData {
  const card = allCards(board).find((c) => c.id === intent.cardId);
  if (!card) return board;

  const semCard = (cards: BoardCardData[]) =>
    cards.filter((c) => c.id !== intent.cardId);

  function inserir(cards: BoardCardData[]): BoardCardData[] {
    const restantes = semCard(cards);
    const movido = { ...card!, column_id: intent.columnId };

    if (intent.prevCardId !== null) {
      const indice = restantes.findIndex((c) => c.id === intent.prevCardId);
      if (indice >= 0) {
        return [
          ...restantes.slice(0, indice + 1),
          movido,
          ...restantes.slice(indice + 1),
        ];
      }
    }
    if (intent.nextCardId !== null) {
      const indice = restantes.findIndex((c) => c.id === intent.nextCardId);
      if (indice >= 0) {
        return [
          ...restantes.slice(0, indice),
          movido,
          ...restantes.slice(indice),
        ];
      }
    }
    // Sem âncora válida: vai para o fim da coluna.
    return [...restantes, movido];
  }

  return {
    ...board,
    columns: board.columns.map((coluna) => {
      if (coluna.id === intent.columnId) {
        const cards = inserir(coluna.cards);
        return { ...coluna, cards, card_count: cards.length };
      }
      const cards = semCard(coluna.cards);
      return { ...coluna, cards, card_count: cards.length };
    }),
    uncolumned:
      intent.columnId === null
        ? inserir(board.uncolumned)
        : semCard(board.uncolumned),
  };
}

/**
 * Calcula as âncoras a partir de uma coluna de destino e de um índice
 * de inserção — o que o `<select>` do menu "Mover para…" e o `onDragEnd`
 * precisam produzir.
 */
export function ancorasPorIndice(
  cardsDaColuna: BoardCardData[],
  cardId: number,
  indiceDestino: number,
): { prevCardId: number | null; nextCardId: number | null } {
  const restantes = cardsDaColuna.filter((c) => c.id !== cardId);
  const indice = Math.max(0, Math.min(indiceDestino, restantes.length));
  return {
    prevCardId: indice > 0 ? restantes[indice - 1].id : null,
    nextCardId: indice < restantes.length ? restantes[indice].id : null,
  };
}

export function Board({
  board,
  readOnly = false,
  selectedCardId,
  onSelectCard,
  selectedCardIds,
  onToggleCardSelection,
  onToggleColumnSelection,
  collapsedColumns,
  onToggleColumnCollapse,
  onMoveCard,
  columnHandlers,
  outdatedCardIds = [],
  addCardColumnId = null,
  addCardSlot = null,
}: BoardProps) {
  const [cardArrastado, setCardArrastado] = useState<BoardCardData | null>(
    null,
  );

  const sensors = useSensors(
    // 8 px de tolerância: sem isso, um clique no card vira arrasto de
    // zero pixel e o painel de detalhe nunca abre.
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const colunasVisiveis = board.columns;
  const idsDeColuna = useMemo(
    () => colunasVisiveis.map((coluna) => `${PREFIXO_COLUNA}${coluna.id}`),
    [colunasVisiveis],
  );

  const cardPorId = useMemo(() => {
    const mapa = new Map<number, BoardCardData>();
    for (const card of allCards(board)) mapa.set(card.id, card);
    return mapa;
  }, [board]);

  function colunaDoCard(cardId: number): BoardColumnData | null {
    return (
      colunasVisiveis.find((coluna) =>
        coluna.cards.some((c) => c.id === cardId),
      ) ?? null
    );
  }

  /**
   * Anúncios em pt-BR para `aria-live` (CA-14). O dnd-kit anuncia em
   * inglês por padrão; um quadro operável por teclado que fala outra
   * língua não é operável de fato.
   */
  const announcements: Announcements = {
    onDragStart({ active }) {
      const card = cardPorId.get(idNumerico(active.id));
      return card
        ? `Card ${card.title} levantado. Use as setas para mover, espaço para soltar, Esc para cancelar.`
        : "Item levantado.";
    },
    onDragOver({ active, over }) {
      if (!over) return undefined;
      const card = cardPorId.get(idNumerico(active.id));
      return card ? `Card ${card.title} sobre uma nova posição.` : undefined;
    },
    onDragEnd({ active, over }) {
      const card = cardPorId.get(idNumerico(active.id));
      if (!card) return "Movimento concluído.";
      return over
        ? `Card ${card.title} solto na nova posição.`
        : `Card ${card.title} devolvido à posição original.`;
    },
    onDragCancel({ active }) {
      const card = cardPorId.get(idNumerico(active.id));
      return card
        ? `Movimento do card ${card.title} cancelado.`
        : "Movimento cancelado.";
    },
  };

  function handleDragStart(evento: DragStartEvent) {
    const tipo = evento.active.data.current?.type;
    if (tipo === "card") {
      setCardArrastado(cardPorId.get(idNumerico(evento.active.id)) ?? null);
    }
  }

  function handleDragEnd(evento: DragEndEvent) {
    setCardArrastado(null);
    const { active, over } = evento;
    if (!over) return;

    const tipo = active.data.current?.type;

    if (tipo === "column" && columnHandlers) {
      const origem = idsDeColuna.indexOf(String(active.id));
      const destino = idsDeColuna.indexOf(String(over.id));
      if (origem < 0 || destino < 0 || origem === destino) return;
      columnHandlers.onMoveColumn(
        colunasVisiveis[origem],
        destino > origem ? 1 : -1,
      );
      return;
    }

    if (tipo !== "card" || !onMoveCard) return;

    const cardId = idNumerico(active.id);
    const alvo = String(over.id);

    // Soltou sobre a ÁREA vazia de uma coluna: vai para o fim dela.
    if (alvo.startsWith(PREFIXO_AREA)) {
      const colunaId = Number(alvo.slice(PREFIXO_AREA.length));
      const coluna = colunasVisiveis.find((c) => c.id === colunaId);
      if (!coluna || coluna.kind === "SECTION") return;
      const { prevCardId, nextCardId } = ancorasPorIndice(
        coluna.cards,
        cardId,
        coluna.cards.length,
      );
      onMoveCard({ cardId, columnId: coluna.id, prevCardId, nextCardId });
      return;
    }

    // Soltou sobre OUTRO card: assume a posição dele.
    if (alvo.startsWith(PREFIXO_CARD)) {
      const alvoId = Number(alvo.slice(PREFIXO_CARD.length));
      if (alvoId === cardId) return;
      const coluna = colunaDoCard(alvoId);
      if (!coluna || coluna.kind === "SECTION") return;
      const restantes = coluna.cards.filter((c) => c.id !== cardId);
      const indice = restantes.findIndex((c) => c.id === alvoId);
      const { prevCardId, nextCardId } = ancorasPorIndice(
        coluna.cards,
        cardId,
        indice < 0 ? restantes.length : indice,
      );
      onMoveCard({ cardId, columnId: coluna.id, prevCardId, nextCardId });
    }
  }

  const conteudo = (
    <div className="board-scroller" data-testid="board-scroller">
      {colunasVisiveis.length === 0 ? (
        <p className="text-sm text-zinc-600">
          Este quadro ainda não tem colunas.
        </p>
      ) : null}

      {colunasVisiveis.map((coluna, indice) => (
        <BoardColumn
          key={coluna.id}
          column={coluna}
          readOnly={readOnly}
          isFirst={indice === 0}
          isLast={indice === colunasVisiveis.length - 1}
          collapsed={collapsedColumns?.has(coluna.id) ?? false}
          onToggleCollapse={onToggleColumnCollapse}
          onToggleColumnSelection={onToggleColumnSelection}
          selectedCardId={selectedCardId}
          onSelectCard={onSelectCard}
          selectedCardIds={selectedCardIds}
          onToggleCardSelection={onToggleCardSelection}
          onMoveCard={onMoveCard}
          board={board}
          columnHandlers={columnHandlers}
          outdatedCardIds={outdatedCardIds}
          addCardSlot={addCardColumnId === coluna.id ? addCardSlot : null}
        />
      ))}

      {board.uncolumned.length > 0 ? (
        <section className="board-column" aria-label="Sem coluna">
          <header className="border-b border-(--color-neutral) px-3 py-2">
            <p className="text-sm font-semibold text-(--color-dark)">
              Sem coluna
            </p>
            <p className="text-xs text-zinc-500">
              {board.uncolumned.length} card(s) órfão(s) de uma coluna excluída
            </p>
          </header>
          <div className="board-column-body">
            {board.uncolumned.map((card) => (
              <BoardCard
                key={card.id}
                card={card}
                columnId={null}
                readOnly={readOnly}
                isSelected={card.id === selectedCardId}
                isChecked={selectedCardIds?.has(card.id) ?? false}
                onSelect={onSelectCard}
                onToggleSelection={onToggleCardSelection}
                onMoveCard={onMoveCard}
                board={board}
                isOutdated={
                  card.is_outdated || outdatedCardIds.includes(card.id)
                }
              />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );

  // CA-17: em modo leitura o `DndContext` NÃO é montado. Desabilitar
  // sensores não bastaria — o cliente não pode ver controle de edição
  // nenhum, e um contexto montado ainda registra ouvintes de ponteiro.
  if (readOnly) {
    return conteudo;
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      accessibility={{ announcements }}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragCancel={() => setCardArrastado(null)}
    >
      {/*
        `vertical` e não mais `horizontal`: as faixas do quadro são
        empilhadas. A estratégia errada aqui não quebra o arrasto — ela
        calcula o deslocamento no eixo errado, e a faixa "escapa" para o
        lado ao ser levantada.
      */}
      <SortableContext items={idsDeColuna} strategy={verticalListSortingStrategy}>
        {conteudo}
      </SortableContext>

      <DragOverlay>
        {cardArrastado ? (
          <div className="board-card opacity-90 shadow-lg">
            <p className="text-xs text-zinc-500">
              Controle {cardArrastado.control_code ?? "—"}
            </p>
            <p className="text-sm font-medium text-(--color-dark)">
              {cardArrastado.title}
            </p>
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}

function idNumerico(id: string | number): number {
  const texto = String(id);
  const separador = texto.indexOf(":");
  return Number(separador >= 0 ? texto.slice(separador + 1) : texto);
}
