import Link from "next/link";

import type { CompanyAdminListItem } from "../actions";

/**
 * Bloco de identidade da empresa — avatar de iniciais, nome e e-mail.
 *
 * Compartilhado pela linha da tabela (desktop) e pelo card (mobile), que
 * são duas apresentações do mesmo registro. Manter isto num lugar só
 * evita o defeito clássico do layout responsivo duplicado: um campo
 * mudar de um lado e não do outro.
 */

/**
 * Duas letras a partir das duas primeiras palavras significativas. Sem
 * as preposições, `Nortex Logística e Transportes` viraria "NL" num
 * registro e "NE" em outro parecido — a inicial existe para diferenciar.
 */
const PALAVRAS_IGNORADAS = new Set(["de", "da", "do", "das", "dos", "e"]);

export function iniciaisDaEmpresa(nome: string): string {
  const palavras = nome
    .split(/\s+/)
    .filter((p) => p && !PALAVRAS_IGNORADAS.has(p.toLowerCase()));

  const letras = (palavras.length > 0 ? palavras : [nome])
    .slice(0, 2)
    .map((p) => p[0])
    .join("");

  return letras.toUpperCase() || "?";
}

/**
 * O e-mail do responsável só aparece quando é DIFERENTE do e-mail da
 * empresa.
 *
 * Na base real os dois coincidem na maioria dos cadastros — o print que
 * originou esta reorganização tinha a mesma string repetida nas cinco
 * linhas visíveis, ocupando duas colunas para dizer uma coisa só.
 */
export function emailProprioDoResponsavel(
  company: CompanyAdminListItem,
): string | null {
  const daEmpresa = company.email.trim().toLowerCase();
  const doResponsavel = company.principal_email.trim().toLowerCase();
  return daEmpresa === doResponsavel ? null : company.principal_email;
}

export function perfilHref(companyId: number) {
  return `/private/admin/empresas/${companyId}/perfil`;
}

export function usuariosHref(companyId: number) {
  return `/private/admin/empresas/${companyId}/usuarios`;
}

export function dashboardHref(companyId: number) {
  return `/private/admin/empresas/${companyId}/dashboard`;
}

export function CompanyIdentity({
  company,
}: {
  company: CompanyAdminListItem;
}) {
  return (
    <Link
      href={perfilHref(company.id)}
      className="group flex items-center gap-3"
      title={`Abrir o perfil de ${company.name}`}
    >
      <span
        aria-hidden="true"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-(--color-surface) text-xs font-semibold text-zinc-600"
      >
        {iniciaisDaEmpresa(company.name)}
      </span>

      <span className="min-w-0">
        <span className="block truncate font-medium text-(--color-dark) transition group-hover:text-(--color-primary)">
          {company.name}
        </span>
        <span className="block truncate text-xs text-zinc-500" title={company.email}>
          {company.email}
        </span>
      </span>
    </Link>
  );
}
