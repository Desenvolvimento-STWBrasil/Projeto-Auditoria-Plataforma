/**
 * Formatação única de data e hora da plataforma.
 *
 * Nasceu de um defeito de hidratação real: `empresas-client.tsx` fazia
 * `new Date(item.created_at).toLocaleDateString("pt-BR")` dentro de um
 * `"use client"`, que o Next renderiza no servidor **e** no cliente. O
 * locale estava fixo, mas o FUSO não — o servidor formatava no fuso do
 * contêiner (UTC) e o navegador no fuso local. Uma empresa criada em
 * `2026-09-09T01:00:00Z` saía `09/09/2026` do servidor e `08/09/2026` em
 * São Paulo, e o React acusava divergência de hidratação.
 *
 * O erro só aparecia para registros criados entre 00:00 e 03:00 UTC, o
 * que é exatamente o pior tipo de bug: raro o bastante para ninguém
 * reproduzir, frequente o bastante para aparecer em produção.
 *
 * A correção é PINAR o fuso. Não é o mesmo que "formatar em UTC":
 *
 * - fuso do navegador → não determinístico contra o servidor (o bug);
 * - UTC → determinístico, mas mostra a data errada para quem opera daqui
 *   (um evento das 22h de segunda apareceria como terça);
 * - fuso pinado → determinístico E correto para quem lê.
 *
 * A plataforma é brasileira e monofuso — o `lang="pt-BR"` do layout e o
 * locale fixo em todas as telas já assumiam isso; aqui a suposição fica
 * declarada num lugar só. Se um dia houver operação em outro fuso, é esta
 * constante que muda (e não 3 call sites), passando a vir do perfil do
 * usuário.
 */

/** Fuso em que a equipe de auditoria opera. Ver a nota do módulo. */
export const FUSO_DA_PLATAFORMA = "America/Sao_Paulo";

const OPCOES_DATA: Intl.DateTimeFormatOptions = {
  timeZone: FUSO_DA_PLATAFORMA,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
};

const OPCOES_DATA_HORA: Intl.DateTimeFormatOptions = {
  ...OPCOES_DATA,
  hour: "2-digit",
  minute: "2-digit",
};

/**
 * `""` para entrada inválida, em vez de "Invalid Date" na tela.
 *
 * `created_at` sempre vem preenchido do backend, mas um campo de data
 * nulo ou malformado não deve virar texto quebrado no meio de uma tabela
 * de auditoria.
 */
function formatar(iso: string, opcoes: Intl.DateTimeFormatOptions): string {
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return "";
  return data.toLocaleString("pt-BR", opcoes);
}

/** Só a data: `09/09/2026`. */
export function formatarData(iso: string): string {
  return formatar(iso, OPCOES_DATA);
}

/**
 * Data e hora: `09/09/2026, 11:35`.
 *
 * A hora não é enfeite no histórico do card: duas mudanças de status no
 * mesmo dia ficariam indistinguíveis sem ela.
 */
export function formatarDataHora(iso: string): string {
  return formatar(iso, OPCOES_DATA_HORA);
}
