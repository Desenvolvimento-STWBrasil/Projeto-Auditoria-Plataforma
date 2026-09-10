"use client";

import type { ReactNode } from "react";
import { useDroppable } from "@dnd-kit/core";
import {
  SortableContext,
  horizontalListSortingStrategy,
} from "@dnd-kit/sortable";

import type {
  Board as BoardData,
  BoardColumn as BoardColumnData,
} from "../actions";
import { BoardCard } from "./board-card";
import type { ColumnMenuHandlers, MoveIntent } from "./board";

type BoardColumnProps = {
  column: BoardColumnData;
  board: BoardData;
  readOnly: boolean;
  isFirst: boolean;
  isLast: boolean;
  collapsed: boolean;
  onToggleCollapse?: (columnId: number) => void;
  onToggleColumnSelection?: (column: BoardColumnData) => void;
  selectedCardId: number | null;
  onSelectCard: (cardId: number) => void;
  selectedCardIds?: Set<number>;
  onToggleCardSelection?: (cardId: number) => void;
  onMoveCard?: (intent: MoveIntent) => void;
  columnHandlers?: ColumnMenuHandlers;
  outdatedCardIds: number[];
  addCardSlot?: ReactNode;
};

export function BoardColumn({
  column,
  board,
  readOnly,
  isFirst,
  isLast,
  collapsed,
  onToggleCollapse,
  onToggleColumnSelection,
  selectedCardId,
  onSelectCard,
  selectedCardIds,
  onToggleCardSelection,
  onMoveCard,
  columnHandlers,
  outdatedCardIds,
  addCardSlot,
}: BoardColumnProps) {
  /*
   * CA-18: `SECTION` é o separador `>>` do Trello. Renderiza como
   * divisor — SEM área de soltar (nenhum `useDroppable`) e SEM contador
   * de cards, porque por definição ela não tem nenhum. Um `useDroppable`
   * aqui faria o dnd-kit oferecer a seção como destino válido, e o
   * servidor recusaria com 422 depois do arrasto já ter "acontecido" na
   * tela.
   *
   * No quadro em linhas o divisor é HORIZONTAL: ele separa blocos de
   * faixas, não blocos de colunas. `aria-orientation` acompanha, senão o
   * leitor de tela anuncia uma orientação que não corresponde ao que
   * está na tela.
   */
  if (column.kind === "SECTION") {
    return (
      <div
        className="board-section-divider"
        role="separator"
        aria-orientation="horizontal"
        aria-label={`Seção ${column.name}`}
        data-testid={`section-${column.id}`}
      >
        <span className="flex-1 text-xs font-semibold tracking-wide text-white">
          {column.name}
        </span>
        {/*
          A seção ganhou o MESMO menu da faixa. Sem ele, uma seção criada
          por engano (ou com o nome errado) era permanente na interface:
          não havia como renomeá-la, reordená-la, arquivá-la nem
          excluí-la, embora o backend aceitasse as quatro — `DELETE
          /dashboard/columns/{id}` nunca distinguiu seção de coluna.
        */}
        {!readOnly && columnHandlers ? (
          <div className="text-white">
            <MenuDeAcoes
              column={column}
              isFirst={isFirst}
              isLast={isLast}
              columnHandlers={columnHandlers}
            />
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <ColunaComum
      column={column}
      board={board}
      readOnly={readOnly}
      isFirst={isFirst}
      isLast={isLast}
      collapsed={collapsed}
      onToggleCollapse={onToggleCollapse}
      onToggleColumnSelection={onToggleColumnSelection}
      selectedCardId={selectedCardId}
      onSelectCard={onSelectCard}
      selectedCardIds={selectedCardIds}
      onToggleCardSelection={onToggleCardSelection}
      onMoveCard={onMoveCard}
      columnHandlers={columnHandlers}
      outdatedCardIds={outdatedCardIds}
      addCardSlot={addCardSlot}
    />
  );
}

/**
 * Setas de reordenar + menu `⋯`, compartilhado pela FAIXA e pela SEÇÃO.
 *
 * Extraído porque a seção passou a ter as mesmas ações. Até aqui ela
 * renderizava só o nome: não havia como renomeá-la, movê-la, arquivá-la
 * nem excluí-la pela tela do Dashboard — o backend aceitava as quatro
 * coisas (`DELETE /dashboard/columns/{id}` nunca distinguiu os dois
 * tipos), e a interface não oferecia nenhuma.
 */
function MenuDeAcoes({
  column,
  isFirst,
  isLast,
  columnHandlers,
}: {
  column: BoardColumnData;
  isFirst: boolean;
  isLast: boolean;
  columnHandlers: ColumnMenuHandlers;
}) {
  // O rótulo acessível acompanha o TIPO: "Ações da seção ISO 27001:2022 >>"
  // e não "Ações da coluna", que descreveria errado o que está na tela.
  const rotulo = column.kind === "SECTION" ? "seção" : "coluna";

  return (
    <div className="flex shrink-0 items-center gap-1">
      {/*
        O quadro é empilhado: reordenar é subir/descer, não
        esquerda/direita. A direção (-1 / 1) que o handler recebe não
        muda — ela é a posição na lista ordenada, e continua sendo o que
        o backend traduz em âncora.
      */}
      <button
        type="button"
        className="rounded px-1 text-xs opacity-70 hover:opacity-100 disabled:opacity-30"
        aria-label={`Mover ${rotulo} ${column.name} para cima`}
        disabled={isFirst}
        onClick={() => columnHandlers.onMoveColumn(column, -1)}
      >
        ↑
      </button>
      <button
        type="button"
        className="rounded px-1 text-xs opacity-70 hover:opacity-100 disabled:opacity-30"
        aria-label={`Mover ${rotulo} ${column.name} para baixo`}
        disabled={isLast}
        onClick={() => columnHandlers.onMoveColumn(column, 1)}
      >
        ↓
      </button>
      <details className="relative">
        <summary
          // `role="button"` explícito: é como Chrome/Firefox já expõem
          // o <summary> de um <details>, mas o jsdom dos testes não
          // faz esse mapeamento — sem ele o menu fica invisível para
          // `getByRole("button")` e, por tabela, para AT que também
          // não mapeiam (CA-14).
          role="button"
          className="cursor-pointer list-none rounded px-1 text-sm opacity-70 hover:opacity-100"
          aria-label={`Ações da ${rotulo} ${column.name}`}
        >
          ⋯
        </summary>
        <div className="absolute right-0 z-20 mt-1 w-44 rounded-lg border border-(--color-neutral) bg-white p-1 text-left shadow-lg">
          <button
            type="button"
            className="block w-full rounded px-2 py-1 text-left text-sm text-zinc-800 hover:bg-zinc-100"
            onClick={() => columnHandlers.onRenameColumn(column)}
          >
            Renomear
          </button>
          <button
            type="button"
            className="block w-full rounded px-2 py-1 text-left text-sm text-zinc-800 hover:bg-zinc-100"
            onClick={() => columnHandlers.onArchiveColumn(column)}
          >
            {column.hidden ? "Reexibir" : "Arquivar"}
          </button>
          <button
            type="button"
            className="block w-full rounded px-2 py-1 text-left text-sm text-red-700 hover:bg-red-50"
            onClick={() => columnHandlers.onDeleteColumn(column)}
          >
            Excluir
          </button>
        </div>
      </details>
    </div>
  );
}

/**
 * Componente separado porque `useDroppable` é um hook: chamá-lo depois
 * de um `return` condicional violaria as regras de hooks. A `SECTION`
 * sai antes; só a coluna comum chega aqui.
 */
function ColunaComum({
  column,
  board,
  readOnly,
  isFirst,
  isLast,
  collapsed,
  onToggleCollapse,
  onToggleColumnSelection,
  selectedCardId,
  onSelectCard,
  selectedCardIds,
  onToggleCardSelection,
  onMoveCard,
  columnHandlers,
  outdatedCardIds,
  addCardSlot,
}: BoardColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: `column-drop:${column.id}`,
    disabled: readOnly,
  });

  const selecionadosNaColuna = column.cards.filter((card) =>
    selectedCardIds?.has(card.id),
  ).length;
  const todosSelecionados =
    column.cards.length > 0 && selecionadosNaColuna === column.cards.length;

  const acimaDoLimite =
    column.wip_limit !== null && column.cards.length > column.wip_limit;

  return (
    <section
      className="board-column"
      aria-label={`Coluna ${column.name}`}
      data-testid={`column-${column.id}`}
    >
      <header className="flex items-start gap-2 border-b border-(--color-neutral) px-3 py-2">
        {!readOnly && onToggleColumnSelection ? (
          <input
            type="checkbox"
            className="mt-1"
            aria-label={`Selecionar todos os cards de ${column.name}`}
            checked={todosSelecionados}
            ref={(node) => {
              if (node) {
                node.indeterminate =
                  selecionadosNaColuna > 0 && !todosSelecionados;
              }
            }}
            onChange={() => onToggleColumnSelection(column)}
          />
        ) : null}

        <button
          type="button"
          className="flex-1 text-left"
          aria-expanded={!collapsed}
          onClick={() => onToggleCollapse?.(column.id)}
        >
          <span className="text-sm font-semibold text-(--color-dark)">
            {collapsed ? "▸" : "▾"} {column.name}
          </span>
          <span
            className={`ml-2 text-xs ${acimaDoLimite ? "font-semibold text-red-600" : "text-zinc-500"}`}
          >
            {column.cards.length}
            {column.wip_limit !== null ? `/${column.wip_limit}` : ""} card(s)
          </span>
          {column.hidden ? (
            <span className="ml-2 rounded-full bg-zinc-200 px-2 py-0.5 text-[10px] text-zinc-700">
              arquivada
            </span>
          ) : null}
        </button>

        {!readOnly && columnHandlers ? (
          <MenuDeAcoes
            column={column}
            isFirst={isFirst}
            isLast={isLast}
            columnHandlers={columnHandlers}
          />
        ) : null}
      </header>

      {collapsed ? null : (
        <div
          ref={setNodeRef}
          className={`board-column-body ${isOver ? "bg-(--color-primary)/5" : ""}`}
        >
          <SortableContext
            items={column.cards.map((card) => `card:${card.id}`)}
            strategy={horizontalListSortingStrategy}
          >
            {column.cards.map((card) => (
              <BoardCard
                key={card.id}
                card={card}
                columnId={column.id}
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
          </SortableContext>

          {/*
            `w-full` porque o corpo da faixa é um flex ROW: sem ele o
            parágrafo encolhe até a largura da palavra mais longa e a
            mensagem fica quebrada numa coluna de 6 caracteres.
          */}
          {column.cards.length === 0 ? (
            <p className="w-full px-1 py-4 text-center text-xs text-zinc-400">
              Nenhum card nesta coluna.
            </p>
          ) : null}
        </div>
      )}

      {!readOnly && columnHandlers ? (
        <footer className="border-t border-(--color-neutral) p-2">
          {addCardSlot ?? (
            <button
              type="button"
              className="text-xs font-medium text-(--color-primary)"
              onClick={() => columnHandlers.onAddCard(column)}
            >
              + Adicionar card
            </button>
          )}
        </footer>
      ) : null}
    </section>
  );
}
