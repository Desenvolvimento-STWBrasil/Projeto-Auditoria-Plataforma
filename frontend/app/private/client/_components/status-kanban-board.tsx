"use client";

import {
  CONTROL_STATUS_ORDER,
  controlStatusAccentClass,
  controlStatusLabel,
} from "@/lib/control-status";
import { ControlCard } from "./control-card";
import type { Controle } from "./types";

type StatusKanbanBoardProps = {
  controles: Controle[];
  selectedId: string | null;
  onSelectControle: (id: string) => void;
};

/**
 * Quadro Kanban por STATUS (4 colunas fixas), usado pelos dashboards de
 * Cliente e Colaborador — não é o mesmo `<Board>` do admin (colunas
 * livres de template, ver CA-20): aqui o agrupamento é sempre pelas 4
 * colunas de `CONTROL_STATUS_ORDER`, então o quadro cabe lado a lado sem
 * precisar de accordion.
 */
export function StatusKanbanBoard({
  controles,
  selectedId,
  onSelectControle,
}: StatusKanbanBoardProps) {
  return (
    <div className="status-board">
      {CONTROL_STATUS_ORDER.map((status) => {
        const cards = controles.filter((controle) => controle.status === status);
        return (
          <section
            key={status}
            className="status-column"
            aria-label={`Coluna ${controlStatusLabel(status)}`}
          >
            <header className="status-column-header">
              <span className={`text-sm font-semibold ${controlStatusAccentClass(status)}`}>
                {controlStatusLabel(status)}
              </span>
              <span className="status-column-count">{cards.length}</span>
            </header>

            <div className="status-column-body">
              {cards.length === 0 ? (
                <p className="status-column-empty">Nenhum controle neste status.</p>
              ) : (
                cards.map((controle) => (
                  <ControlCard
                    key={controle.id}
                    controle={controle}
                    isSelected={controle.id === selectedId}
                    onSelect={onSelectControle}
                  />
                ))
              )}
            </div>
          </section>
        );
      })}
    </div>
  );
}
