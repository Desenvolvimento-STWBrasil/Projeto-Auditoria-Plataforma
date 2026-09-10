import {
  listCompaniesWithUnreadAction,
  listCompanyMessagesAction,
} from "./actions";
import { MensagensClient } from "./mensagens-client";

export default async function AdminMensagensPage(
  props: PageProps<"/private/admin/mensagens">,
) {
  const searchParams = await props.searchParams;
  const empresaParam = Array.isArray(searchParams.empresa)
    ? searchParams.empresa[0]
    : searchParams.empresa;
  const conversaParam = Array.isArray(searchParams.conversa)
    ? searchParams.conversa[0]
    : searchParams.conversa;

  const companies = await listCompaniesWithUnreadAction();

  const empresaId = empresaParam ? Number(empresaParam) : NaN;
  const empresaValida =
    Number.isFinite(empresaId) &&
    companies.some((company) => company.id === empresaId);

  const selectedCompanyId = empresaValida
    ? empresaId
    : (companies[0]?.id ?? null);

  const initialMessages = selectedCompanyId
    ? await listCompanyMessagesAction(selectedCompanyId)
    : [];

  const highlightId = conversaParam ? Number(conversaParam) : NaN;
  const initialHighlightMessageId = Number.isFinite(highlightId)
    ? highlightId
    : null;

  return (
    <MensagensClient
      initialCompanies={companies}
      initialSelectedCompanyId={selectedCompanyId}
      initialMessages={initialMessages}
      initialHighlightMessageId={initialHighlightMessageId}
    />
  );
}
