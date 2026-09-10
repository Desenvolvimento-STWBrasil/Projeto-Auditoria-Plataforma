import { notFound } from "next/navigation";
import { getCompanyAdminDetailAction } from "../actions";
import { CompanyTabsNav } from "./_components/company-tabs-nav";

export default async function CompanyLayout(
  props: LayoutProps<"/private/admin/empresas/[id]">,
) {
  const { id } = await props.params;
  const companyId = Number(id);
  if (!Number.isFinite(companyId)) notFound();

  const company = await getCompanyAdminDetailAction(companyId).catch(
    () => null,
  );
  if (!company) notFound();

  return (
    <div className="min-h-screen bg-(--color-surface)">
      <div className="border-b border-(--color-neutral) bg-white">
        <div className="container-page pt-6">
          <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
            Empresas / {company.name}
          </p>
          <h1 className="mt-1 text-2xl font-semibold text-(--color-dark)">
            {company.name}
          </h1>
          <CompanyTabsNav companyId={companyId} />
        </div>
      </div>
      {props.children}
    </div>
  );
}
