"use client";

import Link from "next/link";

import { formatarData } from "@/lib/date-format";
import type { CompanyAdminListItem } from "../actions";
import {
  CompanyIdentity,
  dashboardHref,
  emailProprioDoResponsavel,
  usuariosHref,
} from "./company-identity";
import { RowActionsMenu } from "./row-actions-menu";
import { SubUsersCell } from "./sub-users-cell";

/**
 * Uma linha da tabela de empresas (a partir de `lg`).
 *
 * A altura da linha é o produto que esta tela vende: com a coluna de
 * sub-usuários recolhida e `truncate` nos e-mails, todas as linhas têm a
 * mesma altura, e o olho percorre a coluna da esquerda sem tropeçar.
 *
 * O telefone desceu para junto do responsável — é o telefone DELE, não
 * da empresa, e como coluna própria ele ganhava 90 px que sobravam para
 * o texto e faltavam para o nome, quebrando `(21) 98765-4321` em três
 * linhas.
 */
type CompanyRowProps = {
  company: CompanyAdminListItem;
  onEdit: (company: CompanyAdminListItem) => void;
  onDelete: (company: CompanyAdminListItem) => void;
};

export function CompanyRow({ company, onEdit, onDelete }: CompanyRowProps) {
  const emailResponsavel = emailProprioDoResponsavel(company);

  return (
    <tr className="border-b border-(--color-neutral) transition last:border-0 hover:bg-(--color-surface)">
      <td className="py-3.5 pr-4 align-middle">
        <CompanyIdentity company={company} />
      </td>

      <td className="py-3.5 pr-4 align-middle">
        <p className="truncate text-sm text-(--color-dark)">
          {company.principal_full_name}
        </p>
        {emailResponsavel ? (
          <p className="truncate text-xs text-zinc-500" title={emailResponsavel}>
            {emailResponsavel}
          </p>
        ) : null}
        <p className="text-xs whitespace-nowrap text-zinc-500">
          {company.phone || "Sem telefone"}
        </p>
      </td>

      <td className="py-3.5 pr-4 align-middle">
        <SubUsersCell
          companyName={company.name}
          emails={company.sub_user_emails}
          count={company.sub_user_count}
        />
      </td>

      <td className="py-3.5 pr-4 align-middle text-sm whitespace-nowrap text-zinc-600">
        {formatarData(company.created_at)}
      </td>

      <td className="py-3.5 align-middle">
        <div className="flex items-center justify-end gap-1">
          <Link
            href={dashboardHref(company.id)}
            className="btn-secondary px-3 py-1.5 text-sm whitespace-nowrap"
            title={`Configurar dashboard e template de ${company.name}`}
          >
            Configurar →
          </Link>
          <RowActionsMenu
            companyName={company.name}
            usuariosHref={usuariosHref(company.id)}
            onEdit={() => onEdit(company)}
            onDelete={() => onDelete(company)}
          />
        </div>
      </td>
    </tr>
  );
}
