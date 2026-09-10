import { redirect } from "next/navigation";

export default async function CompanyRootPage(
  props: PageProps<"/private/admin/empresas/[id]">,
) {
  const { id } = await props.params;
  redirect(`/private/admin/empresas/${id}/perfil`);
}
