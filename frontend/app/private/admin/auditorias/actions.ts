"use server";

import { callBackend } from "@/lib/server-backend";
import { getAccessToken, requireAdmin } from "@/lib/session";

export type AuditStatus = "DRAFT" | "ACTIVE" | "CLOSED";

export type AuditControlStatus =
  | "EM_ANALISE"
  | "PARCIAL"
  | "CONFORME"
  | "NAOCONFORME";

export type AuditListItem = {
  id: number;
  name: string;
  client_user_id: number;
  status: AuditStatus;
  created_at: string;
};

export type PaginatedAudits = {
  total: number;
  skip: number;
  limit: number;
  items: AuditListItem[];
};

export type EvidenceAdmin = {
  id: number;
  file_name: string;
  mime_type: string | null;
  size_bytes: number | null;
  created_at: string;
  uploaded_by_name: string;
};

export type ControlMessage = {
  id: number;
  content: string;
  created_at: string;
  read_at: string | null;
  author_user_id: number;
  author_full_name: string;
  is_from_admin: boolean;
};

export type AuditControlDetail = {
  id: number;
  control_code: string;
  control_title: string;
  status: AuditControlStatus;
  evidences: EvidenceAdmin[];
  messages: ControlMessage[];
};

export type AuditDetail = {
  id: number;
  name: string;
  status: AuditStatus;
  created_at: string;
  client_name: string;
  controls: AuditControlDetail[];
};

/** Lista as auditorias (paginado). Backend: GET /api/v1/admin/audits. */
export async function listAuditsAction(): Promise<PaginatedAudits> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<PaginatedAudits>("/api/v1/admin/audits?skip=0&limit=50", {
    token: token ?? undefined,
  });
}

/** Detalhe completo de uma auditoria. Backend: GET /api/v1/admin/audits/{id}. */
export async function getAuditDetailAction(
  auditId: number,
): Promise<AuditDetail> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<AuditDetail>(`/api/v1/admin/audits/${auditId}`, {
    token: token ?? undefined,
  });
}

export type UpdateAuditStatusResult =
  | { ok: true; detail: AuditDetail }
  | { ok: false; message: string };

/*
 * Encerra (ou reabre) formalmente uma auditoria.
 * Backend: PATCH /api/v1/admin/audits/{id}/status — proposta L.2.
 */
export async function updateAuditStatusAction(
  auditId: number,
  status: AuditStatus,
): Promise<UpdateAuditStatusResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const detail = await callBackend<AuditDetail>(
      `/api/v1/admin/audits/${auditId}/status`,
      { method: "PATCH", token: token ?? undefined, body: { status } },
    );
    return { ok: true, detail };
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : "Falha ao atualizar o status da auditoria.";
    return { ok: false, message };
  }
}

/*
 * Marca o status de um controle avaliado (Em análise / Parcial / Conforme /
 * Não conforme) dentro de uma auditoria.
 * Backend: PATCH /api/v1/admin/audit-controls/{id}/status.
 */
export async function updateControlStatusAction(
  auditControlId: number,
  status: AuditControlStatus,
): Promise<UpdateAuditStatusResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const detail = await callBackend<AuditDetail>(
      `/api/v1/admin/audit-controls/${auditControlId}/status`,
      { method: "PATCH", token: token ?? undefined, body: { status } },
    );
    return { ok: true, detail };
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : "Falha ao atualizar o status do controle.";
    return { ok: false, message };
  }
}

export type SendControlMessageResult =
  | { ok: true; created: ControlMessage }
  | { ok: false; message: string };

/**
 * Envia a resposta do admin na "Conversa / Dúvidas" de um controle.
 * Backend: POST /api/v1/admin/audit-controls/{id}/messages.
 */
export async function sendControlMessageAction(
  auditControlId: number,
  content: string,
): Promise<SendControlMessageResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const created = await callBackend<ControlMessage>(
      `/api/v1/admin/audit-controls/${auditControlId}/messages`,
      { method: "POST", token: token ?? undefined, body: { content } },
    );
    return { ok: true, created };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao enviar mensagem.";
    return { ok: false, message };
  }
}

/**
 * Marca como lidas as mensagens do cliente/sub-usuário num controle —
 * chamado ao expandir a conversa. Backend:
 * PATCH /api/v1/admin/audit-controls/{id}/messages/read.
 */
export async function markControlMessagesReadAction(
  auditControlId: number,
): Promise<void> {
  await requireAdmin();
  const token = await getAccessToken();
  await callBackend(
    `/api/v1/admin/audit-controls/${auditControlId}/messages/read`,
    { method: "PATCH", token: token ?? undefined },
  );
}
