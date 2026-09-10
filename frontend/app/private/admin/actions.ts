"use server";

import { revalidatePath } from "next/cache";
import { requireAdmin, getAccessToken } from "@/lib/session";
import { callBackend } from "@/lib/server-backend";
import {
  listCompaniesWithUnreadAction,
  listCompanyMessagesAction,
} from "./mensagens/actions";

export type PendingSubUserRequest = {
  id: number;
  principal_user_id: number;
  requested_full_name: string;
  request_email: string;
  status: string;
  requested_at: string;
  processed_at: string | null;
  company_name: string | null;
};

export type ApproveSubUserRequestResult =
  | { ok: true }
  | { ok: false; message: string };

/**
 * Aprova uma solicitação de sub-usuário pendente.
 * Backend: POST /api/v1/sub-users/requests/{id}/approve.
 */
export async function approveSubUserRequestAction(
  requestId: number,
): Promise<ApproveSubUserRequestResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(`/api/v1/sub-users/requests/${requestId}/approve`, {
      method: "POST",
      token: token ?? undefined,
    });
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : "Não foi possível aprovar a solicitação no momento.";
    return { ok: false, message };
  }

  revalidatePath("/private/admin");
  return { ok: true };
}

export type RejectSubUserRequestResult =
  | { ok: true }
  | { ok: false; message: string };

/**
 * Recusa uma solicitação de sub-usuário pendente. O cliente que solicitou
 * vê a recusa no próprio dashboard (GET /sub-users/requests/me).
 * Backend: POST /api/v1/sub-users/requests/{id}/reject.
 */
export async function rejectSubUserRequestAction(
  requestId: number,
): Promise<RejectSubUserRequestResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(`/api/v1/sub-users/requests/${requestId}/reject`, {
      method: "POST",
      token: token ?? undefined,
    });
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : "Não foi possível recusar a solicitação no momento.";
    return { ok: false, message };
  }

  revalidatePath("/private/admin");
  return { ok: true };
}

export type AdminUnreadCounts = {
  auditorias: number;
  mensagens: number;
};

/**
 * Contagens agregadas de não lidas para o badge do menu superior do admin.
 * Chamada tanto no carregamento inicial (layout.tsx) quanto pelo polling
 * do próprio UserMenu — por isso não lança em caso de falha, só devolve
 * zero, para nunca quebrar o menu por causa do badge.
 */
export async function getAdminUnreadCountsAction(): Promise<AdminUnreadCounts> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const [auditorias, mensagens] = await Promise.all([
      callBackend<{ unread_count: number }>(
        "/api/v1/admin/messages/unread-count",
        { token: token ?? undefined },
      ),
      callBackend<{ unread_count: number }>("/api/v1/companies/unread-count", {
        token: token ?? undefined,
      }),
    ]);
    return {
      auditorias: auditorias.unread_count,
      mensagens: mensagens.unread_count,
    };
  } catch {
    return { auditorias: 0, mensagens: 0 };
  }
}

// ---- Cards de dashboard (D.6) — as 3 funções abaixo continuam aqui
// porque são genéricas (operam por card_id, não por empresa) e agora são
// consumidas por /private/admin/empresas/[id]/dashboard (proposta O.1),
// não mais diretamente pela Home. ----

export type CardStatus = "EM_ANALISE" | "PARCIAL" | "CONFORME" | "NAOCONFORME";

export type BoardLabelRef = {
  id: number;
  name: string;
  color: string;
};

export type DashboardChecklistItem = {
  id: number;
  title: string;
  done: boolean;
};

export type DashboardUserRef = {
  id: number;
  full_name: string;
};

/*
 * `actor_user` / `author_user` chegam do backend desde E.7 e eram
 * DESCARTADOS aqui: os tipos declaravam só `{id, action, created_at}`, e
 * o painel renderizava apenas o texto. O histórico existe para responder
 * "o que mudou, quando e quem fez" — sem estes dois campos ele
 * respondia só o primeiro terço.
 *
 * Nulo é caso legítimo: `actor_user_id` é `SET NULL` (usuário removido),
 * e entrada semeada por script não tem autor.
 */
export type DashboardHistoryEntry = {
  id: number;
  action: string;
  created_at: string;
  actor_user: DashboardUserRef | null;
};

export type DashboardChatMessage = {
  id: number;
  message_type: string;
  content: string;
  created_at: string;
  author_user: DashboardUserRef | null;
};

export type DashboardCardDetail = {
  id: number;
  control_code: string | null;
  title: string;
  tag: string;
  status: CardStatus;
  description: string | null;
  column_id: number | null;
  // `tag` é o nome CONGELADO na criação do card; `category_id` é o
  // vínculo vivo. O formulário de edição depende do segundo — pré-encher
  // um <select> de categoria com texto histórico selecionaria a opção
  // errada assim que a categoria fosse renomeada.
  category_id: number | null;
  category_name: string | null;
  labels: BoardLabelRef[];
  checklist: DashboardChecklistItem[];
  history: DashboardHistoryEntry[];
  chat: DashboardChatMessage[];
};

/** Busca o detalhe completo (checklist/histórico/chat) de um card específico. */
export async function getCardDetailAction(
  cardId: number,
): Promise<DashboardCardDetail> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<DashboardCardDetail>(`/api/v1/dashboard/cards/${cardId}`, {
    token: token ?? undefined,
  });
}

export type UpdateCardStatusResult =
  | { ok: true; status: CardStatus }
  | { ok: false; message: string };

/** Atualiza o status de um card. Backend: PATCH /dashboard/cards/{id}/status. */
export async function updateCardStatusAction(
  cardId: number,
  status: CardStatus,
): Promise<UpdateCardStatusResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const updated = await callBackend<{ status: CardStatus }>(
      `/api/v1/dashboard/cards/${cardId}/status`,
      { method: "PATCH", token: token ?? undefined, body: { status } },
    );
    return { ok: true, status: updated.status };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao atualizar o status.";
    return { ok: false, message };
  }
}

export type ToggleChecklistItemResult =
  | { ok: true; done: boolean }
  | { ok: false; message: string };

/** Alterna um item de checklist. Backend: PATCH /dashboard/checklist-items/{id}/toggle. */
export async function toggleChecklistItemAction(
  itemId: number,
): Promise<ToggleChecklistItemResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const result = await callBackend<{ ok: boolean; done: boolean }>(
      `/api/v1/dashboard/checklist-items/${itemId}/toggle`,
      { method: "PATCH", token: token ?? undefined },
    );
    return { ok: true, done: result.done };
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : "Falha ao atualizar o checklist.";
    return { ok: false, message };
  }
}

export type CardEntryType =
  | "CHECKLIST"
  | "HISTORY"
  | "CHAT_QUESTION"
  | "CHAT_ANSWER";

export type CreateCardEntryResult =
  | { ok: true }
  | { ok: false; message: string };

/**
 * Cria uma entrada no card: item de checklist, registro de histórico ou
 * mensagem de conversa. Backend: POST /dashboard/cards/{id}/entries.
 *
 * O endpoint existe desde D.6 e **nunca teve consumidor**: a interface
 * sabia LER checklist, histórico e conversa, e não sabia escrever em
 * nenhum dos três. Era possível marcar um item de checklist, nunca
 * criar um; era possível ler a conversa com o cliente, nunca responder.
 *
 * Quem pode o quê é decisão do backend (B-A23): checklist, histórico e
 * `CHAT_ANSWER` são registro do auditor; `CHAT_QUESTION` é a escrita
 * legítima do lado auditado.
 */
export async function createCardEntryAction(
  cardId: number,
  entryType: CardEntryType,
  content: string,
): Promise<CreateCardEntryResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(`/api/v1/dashboard/cards/${cardId}/entries`, {
      method: "POST",
      token: token ?? undefined,
      body: { entry_type: entryType, content },
    });
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao registrar a entrada.";
    return { ok: false, message };
  }
}

export type DeleteChecklistItemResult =
  | { ok: true }
  | { ok: false; message: string };

/** Remove um item de checklist. Backend: DELETE /dashboard/checklist-items/{id}. */
export async function deleteChecklistItemAction(
  itemId: number,
): Promise<DeleteChecklistItemResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(`/api/v1/dashboard/checklist-items/${itemId}`, {
      method: "DELETE",
      token: token ?? undefined,
    });
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao remover o item.";
    return { ok: false, message };
  }
}

// ---- Novo em O.1: KPIs agregados (uma query) + prévia de mensagens não lidas ----

export type DashboardStatusSummary = {
  em_analise: number;
  parcial: number;
  conforme: number;
  naoconforme: number;
};

/**
 * KPIs agregados de TODAS as empresas para os 4 cartões do topo da Home.
 * Backend: GET /api/v1/dashboard/status-summary — uma única query SQL
 * agrupada, substituindo o antigo `listAllCardsAction` (buscava a lista
 * completa de cards de cada empresa só para somar por status no cliente;
 * removida nesta revisão por não ter mais nenhum consumidor).
 */
export async function getDashboardStatusSummaryAction(): Promise<DashboardStatusSummary> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<DashboardStatusSummary>(
    "/api/v1/dashboard/status-summary",
    { token: token ?? undefined },
  );
}

export type RecentUnreadCompanyMessage = {
  company_id: number;
  company_name: string;
  unread_count: number;
  last_message_preview: string;
  last_message_id: number;
};

const RECENT_UNREAD_PREVIEW_LIMIT = 5;

/**
 * Prévia das empresas com mensagens não lidas, para o widget "Mensagens
 * não lidas" da Home — composição de duas Server Actions já existentes em
 * mensagens/actions.ts (nenhum endpoint de backend novo): a contagem por
 * empresa (listCompaniesWithUnreadAction) e o histórico de cada uma
 * (listCompanyMessagesAction), do qual usamos só a última mensagem. Cada
 * item já traz `last_message_id`, usado para montar o deep-link
 * /private/admin/mensagens?empresa=&conversa=.
 */
export async function getRecentUnreadCompanyMessagesAction(): Promise<
  RecentUnreadCompanyMessage[]
> {
  await requireAdmin();

  const companies = await listCompaniesWithUnreadAction();
  const withUnread = companies
    .filter((company) => company.unread_count > 0)
    .sort((a, b) => b.unread_count - a.unread_count)
    .slice(0, RECENT_UNREAD_PREVIEW_LIMIT);

  return Promise.all(
    withUnread.map(async (company) => {
      const messages = await listCompanyMessagesAction(company.id);
      const last = messages[messages.length - 1];
      return {
        company_id: company.id,
        company_name: company.name,
        unread_count: company.unread_count,
        last_message_preview: last?.content ?? "",
        last_message_id: last?.id ?? 0,
      };
    }),
  );
}
