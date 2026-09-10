import { getAccessToken, requireAdmin } from "@/lib/session";
import { notFound } from "next/navigation";
import { getCompanyAdminDetailAction } from "../../actions";
import { callBackend } from "@/lib/server-backend";
import { PendingSubUserRequest } from "../../../actions";
import { UsuariosClient } from "./usuarios-client";

export default async function CompanyUsersPage(
  props: PageProps<"/private/admin/empresas/[id]/usuarios">,
) {
  await requireAdmin();
  const { id } = await props.params;
  const companyId = Number(id);
  if (!Number.isFinite(companyId)) notFound();

  const token = await getAccessToken();
  const [company, allPending] = await Promise.all([
    getCompanyAdminDetailAction(companyId).catch(() => null),
    callBackend<PendingSubUserRequest[]>("/api/v1/sub-users/requests/pending", {
      token: token ?? undefined,
    }),
  ]);
  if (!company) notFound();

  const pendingForCompany = allPending.filter(
    (request) => request.company_name === company.name,
  );

  return (
    <UsuariosClient
      company={company}
      initialPendingRequests={pendingForCompany}
    />
  );
}
