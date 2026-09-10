import { callBackend } from "@/lib/server-backend";
import { getAccessToken, requireClient } from "@/lib/session";
import { listMyCompanyMessagesAction } from "./actions";
import { MensagensClient } from "./mensagens-client";

type CompanyOut = { id: number; name: string };

export default async function ClientMensagensPage() {
  await requireClient();
  const token = await getAccessToken();

  const company = await callBackend<CompanyOut>("/api/v1/companies/me", {
    token: token ?? undefined,
  });

  const initialMessages = await listMyCompanyMessagesAction(company.id);

  return (
    <MensagensClient companyId={company.id} initialMessages={initialMessages} />
  );
}
