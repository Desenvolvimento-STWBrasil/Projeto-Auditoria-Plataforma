import { callBackend } from "@/lib/server-backend";
import { getAccessToken, getCurrentUserProfile, requireClient } from "@/lib/session";
import { ClientDashboardClient } from "./client-dashboard-client";
import {
  ChatMessage,
  listMessagesAction,
  type MySubUserRequest,
} from "./actions";

type ClientControlApi = {
  audit_id: number;
  audit_name: string;
  audit_control_id: number;
  status: "EM_ANALISE" | "PARCIAL" | "CONFORME" | "NAOCONFORME";
  control_code: string;
  control_title: string;
  control_description: string;
  expected_evidence: string | null;
};

export default async function ClientPage() {
  const user = await requireClient();
  const token = await getAccessToken();
  const profile = await getCurrentUserProfile();

  const rawControles = await callBackend<ClientControlApi[]>(
    "/api/v1/client/controls",
    { token: token ?? undefined },
  );

  const firstControlId = rawControles[0]?.audit_control_id ?? null;
  const initialMessages: ChatMessage[] = firstControlId
    ? await listMessagesAction(firstControlId)
    : [];

  // Só usuário principal (role "user") pode solicitar/ver solicitações de
  // sub-usuário — o backend rejeita com 403 para admin/sub-user.
  const initialSubUserRequests: MySubUserRequest[] =
    user.role === "user"
      ? await callBackend<MySubUserRequest[]>("/api/v1/sub-users/requests/me", {
          token: token ?? undefined,
        })
      : [];

  const initialControles = rawControles.map((item) => ({
    id: String(item.audit_control_id),
    codigo: item.control_code,
    titulo: item.control_title,
    descricao: item.control_description,
    evidenciaEsperada: item.expected_evidence ?? "Não informado",
    status: item.status,
    evidencias: [] as string[],
    conversa:
      item.audit_control_id === firstControlId
        ? initialMessages.map((m) => ({
            autor: (m.author_id === user.id ? "CLIENTE" : "AUDITORIA") as
              | "AUDITORIA"
              | "CLIENTE",
            mensagem: m.content,
          }))
        : ([] as { autor: "AUDITORIA" | "CLIENTE"; mensagem: string }[]),
  }));

  return (
    <ClientDashboardClient
      initialControles={initialControles}
      role={user.role}
      userId={user.id}
      companyName={profile?.company_name ?? null}
      initialSubUserRequests={initialSubUserRequests}
    />
  );
}
