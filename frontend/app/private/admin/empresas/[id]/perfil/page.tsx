import { notFound } from "next/navigation";
import { getCompanyAdminDetailAction } from "../../actions";
import { PerfilClient } from "./perfil-client";

export default async function CompanyPerfilPage(
  props: PageProps<"/private/admin/empresas/[id]/perfil">,
) {
  const { id } = await props.params;
  const companyId = Number(id);
  if (!Number.isFinite(companyId)) notFound();

  const detail = await getCompanyAdminDetailAction(companyId).catch(() => null);
  if (!detail) notFound();

  return <PerfilClient initialDetail={detail} />;
}
