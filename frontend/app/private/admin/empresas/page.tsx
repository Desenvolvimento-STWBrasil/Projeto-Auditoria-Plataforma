import {
  listCompaniesAdminAction,
  listTemplatesAction,
} from "./actions";
import { EmpresasClient } from "./empresas-client";

export default async function EmpresasPage() {
  const [companies, templates] = await Promise.all([
    listCompaniesAdminAction(0, ""),
    listTemplatesAction(),
  ]);

  return (
    <EmpresasClient
      initialCompanies={companies}
      initialTemplates={templates}
    />
  );
}
