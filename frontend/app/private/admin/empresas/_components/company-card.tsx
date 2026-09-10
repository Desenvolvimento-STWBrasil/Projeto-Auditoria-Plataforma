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
 * A mesma empresa, abaixo de `lg`.
 *
 * A tabela antiga tinha `min-w-205` (820 px) e uma coluna de ações
 * `sticky`: em tablet e celular a tela só era utilizável arrastando de
 * lado, e a coluna grudada comia parte da largura que já faltava.
 *
 * Card empilhado resolve os dois: nada rola na horizontal, e a ordem de
 * leitura passa a ser a ordem de importância (quem é a empresa → quem
 * responde por ela → quando entrou → o que fazer com ela).
 */
type CompanyCardProps = {
  company: CompanyAdminListItem;
  onEdit: (company: CompanyAdminListItem) => void;
  onDelete: (company: CompanyAdminListItem) => void;
};

export function CompanyCard({ company, onEdit, onDelete }: CompanyCardProps) {
  const emailResponsavel = emailProprioDoResponsavel(company);

  return (
    <li className="rounded-xl border border-(--color-neutral) p-4">
      <CompanyIdentity company={company} />

      <dl className="mt-3 space-y-1 text-sm">
        <div className="flex gap-2">
          <dt className="shrink-0 text-zinc-500">Responsável:</dt>
          <dd className="min-w-0 truncate text-(--color-dark)">
            {company.principal_full_name}
          </dd>
        </div>
        {emailResponsavel ? (
          <div className="flex gap-2">
            <dt className="sr-only">E-mail do responsável</dt>
            <dd
              className="min-w-0 truncate text-xs text-zinc-500"
              title={emailResponsavel}
            >
              {emailResponsavel}
            </dd>
          </div>
        ) : null}
        <div className="flex flex-wrap gap-x-2 text-xs text-zinc-500">
          <dt className="sr-only">Telefone e data de cadastro</dt>
          <dd>{company.phone || "Sem telefone"}</dd>
          <dd aria-hidden="true">·</dd>
          <dd>Desde {formatarData(company.created_at)}</dd>
        </div>
      </dl>

      <div className="mt-3">
        <SubUsersCell
          companyName={company.name}
          emails={company.sub_user_emails}
          count={company.sub_user_count}
        />
      </div>

      <div className="mt-4 flex items-center justify-between gap-2 border-t border-(--color-neutral) pt-3">
        <Link
          href={dashboardHref(company.id)}
          className="btn-secondary px-3 py-1.5 text-sm"
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
    </li>
  );
}
