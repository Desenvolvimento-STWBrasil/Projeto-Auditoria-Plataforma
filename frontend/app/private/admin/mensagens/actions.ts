"use server";

import { requireAdmin, getAccessToken } from "@/lib/session";
import { callBackend } from "@/lib/server-backend";

export type CompanyMessageAuthor = {
  id: number;
  full_name: string;
  role: string;
};

export type CompanyMessage = {
  id: number;
  content: string;
  created_at: string;
  read_at: string | null;
  is_from_admin: boolean;
  author: CompanyMessageAuthor;
};

export type CompanyWithUnread = {
  id: number;
  name: string;
  unread_count: number;
};

/**
 * Lista todas as empresas com a contagem de mensagens não lidas de cada
 * uma — usado para montar a lista de "caixas" na tela do admin.
 */
export async function listCompaniesWithUnreadAction(): Promise<
  CompanyWithUnread[]
> {
  await requireAdmin();
  const token = await getAccessToken();

  const companies = await callBackend<{ id: number; name: string }[]>(
    "/api/v1/onboarding/companies",
    { token: token ?? undefined },
  );

  const withUnread = await Promise.all(
    companies.map(async (company) => {
      const { unread_count } = await callBackend<{ unread_count: number }>(
        `/api/v1/companies/${company.id}/messages/unread-count`,
        { token: token ?? undefined },
      );
      return { ...company, unread_count };
    }),
  );

  return withUnread;
}

export async function listCompanyMessagesAction(
  companyId: number,
): Promise<CompanyMessage[]> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<CompanyMessage[]>(
    `/api/v1/companies/${companyId}/messages`,
    { token: token ?? undefined },
  );
}

export async function markCompanyMessagesAsReadAction(
  companyId: number,
): Promise<void> {
  await requireAdmin();
  const token = await getAccessToken();
  await callBackend(`/api/v1/companies/${companyId}/messages/read`, {
    method: "PATCH",
    token: token ?? undefined,
  });
}

export type SendCompanyMessageResult =
  | { ok: true; created: CompanyMessage }
  | { ok: false; message: string };

export async function sendCompanyMessageAction(
  companyId: number,
  content: string,
): Promise<SendCompanyMessageResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const created = await callBackend<CompanyMessage>(
      `/api/v1/companies/${companyId}/messages`,
      { method: "POST", token: token ?? undefined, body: { content } },
    );
    return { ok: true, created };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao enviar mensagem.";
    return { ok: false, message };
  }
}
