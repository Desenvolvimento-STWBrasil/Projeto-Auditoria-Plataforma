"use server";

import { requireClient, getAccessToken } from "@/lib/session";
import { callBackend } from "@/lib/server-backend";

export type RequestSubUserInput = {
  requested_full_name: string;
  request_email: string;
};

export type RequestSubUserResult =
  | { ok: true }
  | { ok: false; message: string };

/**
 * Envia uma solicitação de criação de sub-usuário (só disponível para
 * usuários principais, role "user" — validado aqui e no backend via
 * require_main_user).
 * Backend: POST /api/v1/sub-users/requests.
 */
export async function requestSubUserAction(
  input: RequestSubUserInput,
): Promise<RequestSubUserResult> {
  await requireClient();
  const token = await getAccessToken();

  try {
    await callBackend("/api/v1/sub-users/requests", {
      method: "POST",
      token: token ?? undefined,
      body: input,
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao enviar solicitação.";
    return { ok: false, message };
  }

  return { ok: true };
}

export type SubUserRequestStatus = "PENDING" | "APPROVED" | "REJECTED";

export type MySubUserRequest = {
  id: number;
  requested_full_name: string;
  request_email: string;
  status: SubUserRequestStatus;
  requested_at: string;
  processed_at: string | null;
};

/**
 * Lista as solicitações de sub-usuário do próprio usuário principal
 * (pendentes, aprovadas e recusadas) — usado para mostrar ao cliente
 * quando uma solicitação foi recusada pelo admin.
 * Backend: GET /api/v1/sub-users/requests/me.
 */
export async function listMySubUserRequestsAction(): Promise<
  MySubUserRequest[]
> {
  await requireClient();
  const token = await getAccessToken();
  return callBackend<MySubUserRequest[]>("/api/v1/sub-users/requests/me", {
    token: token ?? undefined,
  });
}

export type UploadEvidenceResult =
  | { ok: true; fileName: string }
  | { ok: false; message: string };

/**
 * Envia um arquivo de evidência para um controle.
 * Backend: POST /api/v1/client/controls/{id}/evidences (multipart/form-data,
 * campo "file" — ver backend/app/api/v1/client.py::upload_evidence).
 *
 * `formData` é montado no Client Component a partir do <input type="file">
 * e passado diretamente como argumento — Server Actions aceitam FormData
 * (incluindo File) quando chamadas programaticamente, sem precisar de um
 * Route Handler intermediário.
 */

export async function uploadEvidenceAction(
  auditControlId: number,
  formData: FormData,
): Promise<UploadEvidenceResult> {
  await requireClient();
  const token = await getAccessToken();

  try {
    const result = await callBackend<{
      id: number;
      file_path: string;
      filename: string;
    }>(`/api/v1/client/controls/${auditControlId}/evidences`, {
      method: "POST",
      token: token ?? undefined,
      body: formData,
    });
    return { ok: true, fileName: result.filename };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao enviar evidência.";
    return { ok: false, message };
  }
}

export type ChatMessage = {
  id: number;
  content: string;
  author_id: number;
  created_at: string;
};

export async function listMessagesAction(
  auditControlId: number,
): Promise<ChatMessage[]> {
  await requireClient();
  const token = await getAccessToken();
  return callBackend<ChatMessage[]>(
    `/api/v1/client/controls/${auditControlId}/messages`,
    {
      token: token ?? undefined,
    },
  );
}

export type SendMessageResult =
  | { ok: true; content: string }
  | { ok: false; message: string };

/**
 * Envia uma mensagem para um controle.
 * Backend: POST /api/v1/client/controls/{id}/messages. A resposta do
 * backend não inclui author_id (ver observação técnica do item B.4) — como
 * quem está enviando é sempre o próprio usuário logado, o autor não precisa
 * vir na resposta; quem chama esta action já sabe que a mensagem é "CLIENTE".
 */

export async function sendMessageAction(
  auditControlId: number,
  content: string,
): Promise<SendMessageResult> {
  await requireClient();
  const token = await getAccessToken();

  try {
    const created = await callBackend<{
      id: number;
      content: string;
      created_at: string;
    }>(`/api/v1/client/controls/${auditControlId}/messages`, {
      method: "POST",
      token: token ?? undefined,
      body: { content },
    });
    return { ok: true, content: created.content };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao enviar mensagem";
    return { ok: false, message };
  }
}
