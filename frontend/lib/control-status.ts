/**
 * Vocabulário único de status de conformidade de um controle, usado pelos
 * três dashboards que exibem esse conceito: admin (cards do dashboard da
 * empresa), auditorias (controles de uma auditoria) e cliente/sub-cliente
 * (controles da própria empresa). Antes desta unificação cada tela definia
 * seu próprio label/cor localmente e divergia (ex.: cliente não tinha
 * "Não conforme"; auditorias mostrava o enum cru sem badge; cores
 * inconsistentes entre telas para o mesmo status) — ver B-M20 no
 * relatorio_bugs.md.
 */
export type ControlStatus =
  | "EM_ANALISE"
  | "PARCIAL"
  | "CONFORME"
  | "NAOCONFORME";

export const CONTROL_STATUS_ORDER: ControlStatus[] = [
  "EM_ANALISE",
  "PARCIAL",
  "CONFORME",
  "NAOCONFORME",
];

const LABELS: Record<ControlStatus, string> = {
  EM_ANALISE: "Em análise",
  PARCIAL: "Parcial",
  CONFORME: "Conforme",
  NAOCONFORME: "Não conforme",
};

// Semântica de cor consistente em todos os dashboards: neutro (em
// andamento) -> âmbar (atenção) -> verde (positivo) -> vermelho (negativo).
const COLOR_CLASSES: Record<ControlStatus, string> = {
  EM_ANALISE: "bg-zinc-200 text-zinc-800",
  PARCIAL: "bg-amber-100 text-amber-800",
  CONFORME: "bg-green-100 text-green-800",
  NAOCONFORME: "bg-red-100 text-red-800",
};

// Cor de destaque (texto) usada em KPIs numéricos — mesma família de cor
// do badge correspondente, só que na variante "forte" para contraste sobre
// fundo branco.
const ACCENT_TEXT_CLASSES: Record<ControlStatus, string> = {
  EM_ANALISE: "text-zinc-600",
  PARCIAL: "text-amber-600",
  CONFORME: "text-green-600",
  NAOCONFORME: "text-red-600",
};

export function controlStatusLabel(status: ControlStatus): string {
  return LABELS[status];
}

/** Classes do badge (pílula) de status — combinar sempre com `.status-chip`. */
export function controlStatusBadgeClass(status: ControlStatus): string {
  return `status-chip ${COLOR_CLASSES[status]}`;
}

export function controlStatusAccentClass(status: ControlStatus): string {
  return ACCENT_TEXT_CLASSES[status];
}

// Estado ativo do seletor de status (botão pressionado): mesma cor do
// badge, na variante "sólida" para dar contraste de seleção.
const BUTTON_ACTIVE_CLASSES: Record<ControlStatus, string> = {
  EM_ANALISE: "bg-zinc-800 text-white",
  PARCIAL: "bg-amber-500 text-white",
  CONFORME: "bg-green-600 text-white",
  NAOCONFORME: "bg-red-600 text-white",
};

// Estado inativo: contorno na cor do status, para o usuário já
// reconhecer a opção antes de selecioná-la.
const BUTTON_INACTIVE_CLASSES: Record<ControlStatus, string> = {
  EM_ANALISE: "border border-zinc-300 text-zinc-700 hover:bg-zinc-100",
  PARCIAL: "border border-amber-300 text-amber-700 hover:bg-amber-50",
  CONFORME: "border border-green-300 text-green-700 hover:bg-green-50",
  NAOCONFORME: "border border-red-300 text-red-700 hover:bg-red-50",
};

/**
 * Classes do botão seletor de status (segmented control), usado onde o
 * usuário troca o status de um controle. `active` indica se esse botão
 * representa o status atual do controle.
 */
export function controlStatusButtonClass(
  status: ControlStatus,
  active: boolean,
): string {
  const base = "rounded-full px-4 py-2 text-sm font-medium transition";
  return `${base} ${active ? BUTTON_ACTIVE_CLASSES[status] : BUTTON_INACTIVE_CLASSES[status]}`;
}
