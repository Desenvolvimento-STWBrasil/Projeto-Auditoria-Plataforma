export type BoardLabel = {
  id: number;
  name: string;
  color: string;
};

export const TRELLO_COLOR_MAP: Record<string, string> = {
  red_dark: "#96311D",
  orange: "#C2410C",
  yellow_light: "#A16207",
  yellow_dark: "#854D0E",
  blue: "#2C5A8C",
  blue_light: "#0E7490",
  blue_dark: "#1E3A8A",
  purple: "#6D28D9",
  green: "#1F6B4C",
  black_dark: "#3F3F46",
  pink_dark: "#9D174D",
};

/** Cor de fallback — a mesma default de `dashboard_labels.color`. */
export const DEFAULT_LABEL_COLOR = "#788c5d";

const HEX_COMPLETO = /^#[0-9a-fA-F]{6}$/;
const HEX_CURTO = /^#[0-9a-fA-F]{3}$/;

function normalizarHex(color: string): string {
  const valor = (color ?? "").trim();
  if (HEX_COMPLETO.test(valor)) return valor;
  if (HEX_CURTO.test(valor)) {
    const [, r, g, b] = valor;
    return `#${r}${r}${g}${g}${b}${b}`;
  }

  // Nome de cor do Trello ainda não convertido, ou lixo: nunca deixamos
  // o chip sem cor.
  return TRELLO_COLOR_MAP[valor] ?? DEFAULT_LABEL_COLOR;
}

/*
 * Luminância relativa aproximada (0 = preto, 1 = branco), na fórmula
 * simplificada do WCAG. Serve a uma pergunta só: o texto por cima deste
 * fundo tem de ser claro ou escuro?
 */
function luminancia(hex: string): number {
  const valor = normalizarHex(hex);
  const r = parseInt(valor.slice(1, 3), 16) / 255;
  const g = parseInt(valor.slice(3, 5), 16) / 255;
  const b = parseInt(valor.slice(5, 7), 16) / 255;
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/*
 * Classes do chip de etiqueta. A COR DE FUNDO não sai daqui — sai de
 * `labelChipStyle`. O que esta função decide é a cor do TEXTO, para o
 * contraste funcionar tanto sobre `#96311D` (vermelho escuro) quanto
 * sobre `#A16207` (âmbar).
 */
export function labelChipClass(color: string): string {
  return luminancia(color) > 0.6
    ? "label-chip text-zinc-900"
    : "label-chip text-white";
}

/** Estilo inline do chip — ver a docstring do módulo para o porquê. */
export function labelChipStyle(color: string): { backgroundColor: string } {
  return { backgroundColor: normalizarHex(color) };
}

/*
 * Ordem canônica de exibição: `sort_order` do banco primeiro, nome como
 * desempate. Duas telas que ordenem etiquetas de formas diferentes
 * mostram o mesmo card de dois jeitos — foi exatamente B-M20.
 *
 * Não muta o array recebido: o quadro guarda os cards em estado
 * otimista, e ordenar no lugar corromperia a lista que o React ainda
 * está renderizando.
 */
export function sortLabels<T extends BoardLabel & { sort_order?: number }>(
  labels: T[],
): T[] {
  return [...labels].sort((a, b) => {
    const ordemA = a.sort_order ?? 0;
    const ordemB = b.sort_order ?? 0;
    if (ordemA !== ordemB) return ordemA - ordemB;
    return a.name.localeCompare(b.name, "pt-BR");
  });
}

/** Converte a cor nomeada do export do Trello para o hex do tema. */
export function trelloColorToHex(color: string | null | undefined): string {
  if (!color) return DEFAULT_LABEL_COLOR;
  return TRELLO_COLOR_MAP[color] ?? DEFAULT_LABEL_COLOR;
}
