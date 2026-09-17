/**
 * Estilo único de aba (sublinhado, cor primária quando ativa), usado tanto
 * por abas de navegação (`Link`, ex.: `CompanyTabsNav`) quanto por abas de
 * conteúdo (`button`, ex.: painel de controle do cliente) — o elemento
 * HTML muda conforme o caso, a aparência não.
 */
export function tabItemClass(active: boolean): string {
  return `shrink-0 border-b-2 px-3 py-2 text-sm font-medium transition ${
    active
      ? "border-(--color-primary) text-(--color-primary)"
      : "border-transparent text-zinc-600 hover:text-(--color-dark)"
  }`;
}
