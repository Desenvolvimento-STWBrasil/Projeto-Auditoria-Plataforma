import { notFound } from "next/navigation";
import { getCompanyAdminDetailAction } from "../../actions";
import Link from "next/link";
import { formatarData } from "@/lib/date-format";
import { listCompanyAuditsAction } from "./actions";

function labelStatus(status: string) {
  if (status === "DRAFT") return "Rascunho";
  if (status === "ACTIVE") return "Em andamento";
  return "Encerrada";
}

export default async function CompanyAuditsPage(
  props: PageProps<"/private/admin/empresas/[id]/auditoria">,
) {
  const { id } = await props.params;
  const companyId = Number(id);
  if (!Number.isFinite(companyId)) notFound();

  const [company, audits] = await Promise.all([
    getCompanyAdminDetailAction(companyId).catch(() => null),
    listCompanyAuditsAction(companyId),
  ]);
  if (!company) notFound();

  return (
    <main className="py-8">
      <div className="container-page space-y-6">
        <section className="card">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-(--color-dark)">
              Auditorias de {company.name}
            </h2>
            <span className="text-sm text-zinc-500">
              {audits.length} auditoria(s)
            </span>
          </div>

          {audits.length === 0 ? (
            <p className="mt-3 text-sm text-zinc-600">
              Nenhuma auditoria formal criada para esta empresa ainda.
            </p>
          ) : (
            <ul className="mt-4 divide-y divide-(--color-neutral)">
              {audits.map((audit) => (
                <li
                  key={audit.id}
                  className="flex items-center justify-between gap-3 py-3"
                >
                  <div>
                    <p className="text-sm font-semibold text-(--color-dark)">
                      {audit.name}
                    </p>
                    <p className="text-xs text-zinc-500">
                      {labelStatus(audit.status)} —{" "}
                      {formatarData(audit.created_at)}
                    </p>
                  </div>
                  <Link
                    href={`/private/admin/auditorias?auditId=${audit.id}`}
                    className="btn-secondary shrink-0"
                  >
                    Ver →
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  );
}
