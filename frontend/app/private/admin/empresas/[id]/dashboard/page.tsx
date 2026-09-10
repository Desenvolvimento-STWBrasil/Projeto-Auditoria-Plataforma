import { notFound } from "next/navigation";
import { getCompanyAdminDetailAction } from "@/app/private/admin/empresas/actions";
import {
  getBoardAction,
  listCategoriesAction,
  listLabelsAction,
  listTemplatesAction,
} from "./actions";
import { CompanyDashboardClient } from "./company-dashboard-client";

export default async function CompanyDashboardPage(
  props: PageProps<"/private/admin/empresas/[id]/dashboard">,
) {
  const { id } = await props.params;
  const companyId = Number(id);
  if (!Number.isFinite(companyId)) notFound();

  /*
   * O detalhe do primeiro card visível era buscado aqui (`initialCardDetail`)
   * porque o painel de detalhe ficava fixo no rodapé e abriria vazio.
   * Agora o detalhe vive num modal, que nasce fechado: ninguém precisa
   * dele no carregamento, e essa era uma quinta ida ao backend em toda
   * abertura da tela — mais uma consulta ao banco para popular um painel
   * que o admin talvez nem olhasse.
   */
  const [company, board, categories, labels, templates] = await Promise.all([
    getCompanyAdminDetailAction(companyId).catch(() => null),
    // `include_hidden=true`: o filtro de ocultos é do cliente (toggle
    // "Mostrar cards e colunas arquivados"), então o servidor entrega
    // tudo e a UI decide o que mostrar.
    getBoardAction(companyId, true),
    listCategoriesAction(),
    listLabelsAction(),
    listTemplatesAction(),
  ]);
  if (!company) notFound();

  return (
    <CompanyDashboardClient
      companyId={companyId}
      companyName={company.name}
      initialBoard={board}
      categories={categories}
      labels={labels}
      templates={templates}
    />
  );
}
