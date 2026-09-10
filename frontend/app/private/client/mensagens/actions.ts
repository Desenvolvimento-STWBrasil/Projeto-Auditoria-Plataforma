"use server";

import { callBackend } from "@/lib/server-backend";
import { getAccessToken, requireClient } from "@/lib/session";

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

export async function listMyCompanyMessagesAction(
  companyId: number,
): Promise<CompanyMessage[]> {
  await requireClient();
  const token = await getAccessToken();
  return callBackend<CompanyMessage[]>(
    `/api/v1/companies/${companyId}/messages`,
    { token: token ?? undefined },
  );
}

export async function markMyCompanyMessagesAsReadAction(
  companyId: number,
): Promise<void> {
  await requireClient();
  const token = await getAccessToken();
  await callBackend(`/api/v1/companies/${companyId}/messages/read`, {
    method: "PATCH",
    token: token ?? undefined,
  });
}

export type SendMyCompanyMessageResult =
  | { ok: true; created: CompanyMessage }
  | { ok: false; message: string };

export async function sendMyCompanyMessageAction(
  companyId: number,
  content: string,
): Promise<SendMyCompanyMessageResult> {
  await requireClient();
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
