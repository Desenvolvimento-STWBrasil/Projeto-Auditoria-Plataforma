"use client";

import { controlStatusBadgeClass, controlStatusLabel } from "@/lib/control-status";
import type { Controle } from "./types";

type ControlCardProps = {
  controle: Controle;
  isSelected: boolean;
  onSelect: (id: string) => void;
};

export function ControlCard({ controle, isSelected, onSelect }: ControlCardProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect(controle.id)}
      className={`status-card ${isSelected ? "status-card-selected" : ""}`}
      data-testid={`control-card-${controle.id}`}
    >
      <p className="text-xs text-zinc-500">Controle {controle.codigo}</p>
      <p className="mt-1 text-sm font-medium text-(--color-dark)">
        {controle.titulo}
      </p>
      <span className={`mt-2 inline-block ${controlStatusBadgeClass(controle.status)}`}>
        {controlStatusLabel(controle.status)}
      </span>
    </button>
  );
}
