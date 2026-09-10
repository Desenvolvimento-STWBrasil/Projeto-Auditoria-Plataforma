"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import {
  controlStatusBadgeClass,
  controlStatusLabel,
} from "@/lib/control-status";
import { labelChipClass, labelChipStyle, sortLabels } from "@/lib/board-labels";
import type {
  Board as BoardData,
  BoardCard as BoardCardData,
} from "../actions";
import type { MoveIntent } from "./board";
import { MoveCardMenu } from "./move-card-menu";

type BoardCardProps = {
  card: BoardCardData;
  columnId: number | null;
  readOnly: boolean;
  isSelected: boolean;
  isChecked: boolean;
  onSelect: (cardId: number) => void;
  onToggleSelection?: (cardId: number) => void;
  onMoveCard?: (intent: MoveIntent) => void;
  board: BoardData;
  isOutdated: boolean;
};

export function BoardCard(props: BoardCardProps) {
  // Em modo leitura o card não é arrastável e nenhum hook de arrasto é
  // montado (CA-17). Dois componentes, e não um `disabled`: um
  // `useSortable` desabilitado ainda instala atributos e ouvintes.
  return props.readOnly ? (
    <CardEstatico {...props} />
  ) : (
    <CardArrastavel {...props} />
  );
}

function ConteudoDoCard({
  card,
  isSelected,
  isChecked,
  onSelect,
  onToggleSelection,
  onMoveCard,
  board,
  isOutdated,
  readOnly,
  dragHandle,
}: BoardCardProps & { dragHandle?: React.ReactNode }) {
  return (
    <div
      className={`board-card ${isSelected ? "board-card-selected" : ""}`}
      data-testid={`card-${card.id}`}
    >
      <div className="flex items-start gap-2">
        {!readOnly && onToggleSelection ? (
          <input
            type="checkbox"
            className="mt-1"
            aria-label={`Selecionar ${card.title}`}
            checked={isChecked}
            onChange={() => onToggleSelection(card.id)}
          />
        ) : null}

        <button
          type="button"
          className="flex-1 text-left"
          onClick={() => onSelect(card.id)}
        >
          <p className="text-xs text-zinc-500">
            Controle {card.control_code ?? "—"}
          </p>
          <p className="text-sm font-medium text-(--color-dark)">
            {card.title}
          </p>
        </button>

        {dragHandle}
      </div>

      {card.labels.length > 0 ? (
        <div className="mt-1 flex flex-wrap gap-1">
          {sortLabels(card.labels).map((etiqueta) => (
            <span
              key={etiqueta.id}
              className={labelChipClass(etiqueta.color)}
              style={labelChipStyle(etiqueta.color)}
            >
              {etiqueta.name}
            </span>
          ))}
        </div>
      ) : null}

      <div className="mt-1 flex flex-wrap items-center gap-1">
        <span className={controlStatusBadgeClass(card.status)}>
          {controlStatusLabel(card.status)}
        </span>
        {card.origin_template_card_id === null ? (
          <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] text-zinc-600">
            custom
          </span>
        ) : null}
        {isOutdated ? (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] text-amber-800">
            ≠ template
          </span>
        ) : null}
        {card.hidden ? (
          <span className="rounded-full bg-zinc-200 px-2 py-0.5 text-[10px] text-zinc-700">
            oculto
          </span>
        ) : null}
      </div>

      {!readOnly && onMoveCard ? (
        <MoveCardMenu card={card} board={board} onMoveCard={onMoveCard} />
      ) : null}
    </div>
  );
}

function CardEstatico(props: BoardCardProps) {
  return <ConteudoDoCard {...props} />;
}

function CardArrastavel(props: BoardCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: `card:${props.card.id}`,
    data: { type: "card", columnId: props.columnId },
  });

  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.4 : 1,
      }}
    >
      <ConteudoDoCard
        {...props}
        dragHandle={
          <button
            type="button"
            className="shrink-0 cursor-grab rounded px-1 text-zinc-400 hover:bg-zinc-100"
            aria-label={`Arrastar o card ${props.card.title}`}
            {...attributes}
            {...listeners}
          >
            ⠿
          </button>
        }
      />
    </div>
  );
}
