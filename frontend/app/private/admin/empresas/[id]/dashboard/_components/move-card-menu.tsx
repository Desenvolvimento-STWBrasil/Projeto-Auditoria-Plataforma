"use client";

import { useState } from "react";

import type {
  Board as BoardData,
  BoardCard as BoardCardData,
} from "../actions";
import { ancorasPorIndice, type MoveIntent } from "./board";

type MoveCardMenuProps = {
  card: BoardCardData;
  board: BoardData;
  onMoveCard: (intent: MoveIntent) => void;
};

export function MoveCardMenu({ card, board, onMoveCard }: MoveCardMenuProps) {
  // Colunas `SECTION` ficam fora da lista: elas não aceitam card, e
  // oferecê-las aqui só produziria um 422 depois do clique (CA-18).
  const colunasDestino = board.columns.filter(
    (coluna) => coluna.kind === "COLUMN",
  );

  const [colunaId, setColunaId] = useState<number | "">(card.column_id ?? "");
  const [indice, setIndice] = useState(0);

  const colunaEscolhida =
    colunaId === ""
      ? null
      : (colunasDestino.find((coluna) => coluna.id === colunaId) ?? null);

  const cardsDoDestino = colunaEscolhida
    ? colunaEscolhida.cards.filter((c) => c.id !== card.id)
    : [];

  function confirmar() {
    if (colunaEscolhida === null) return;
    const { prevCardId, nextCardId } = ancorasPorIndice(
      colunaEscolhida.cards,
      card.id,
      indice,
    );
    onMoveCard({
      cardId: card.id,
      columnId: colunaEscolhida.id,
      prevCardId,
      nextCardId,
    });
  }

  return (
    <details className="mt-2 border-t border-(--color-neutral) pt-1">
      <summary className="cursor-pointer list-none text-[11px] font-medium text-(--color-primary)">
        Mover para…
      </summary>

      <div className="mt-2 space-y-2">
        <label className="block text-[11px] text-zinc-600">
          Coluna
          <select
            className="field mt-0.5 text-xs"
            aria-label={`Coluna de destino para ${card.title}`}
            value={colunaId}
            onChange={(evento) => {
              setColunaId(
                evento.target.value ? Number(evento.target.value) : "",
              );
              setIndice(0);
            }}
          >
            <option value="">Escolha a coluna…</option>
            {colunasDestino.map((coluna) => (
              <option key={coluna.id} value={coluna.id}>
                {coluna.name}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-[11px] text-zinc-600">
          Posição
          <select
            className="field mt-0.5 text-xs"
            aria-label={`Posição de destino para ${card.title}`}
            value={indice}
            onChange={(evento) => setIndice(Number(evento.target.value))}
          >
            {Array.from({ length: cardsDoDestino.length + 1 }, (_, i) => (
              <option key={i} value={i}>
                {i === 0
                  ? "No início"
                  : i === cardsDoDestino.length
                    ? "No fim"
                    : `Depois de: ${cardsDoDestino[i - 1].title}`}
              </option>
            ))}
          </select>
        </label>

        <button
          type="button"
          className="btn-primary w-full text-xs"
          disabled={colunaEscolhida === null}
          onClick={confirmar}
        >
          Mover
        </button>
      </div>
    </details>
  );
}
