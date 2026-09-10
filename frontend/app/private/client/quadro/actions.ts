"use server";

import { callBackend } from "@/lib/server-backend";
import { getAccessToken, requireClient } from "@/lib/session";
import { Board } from "../../admin/empresas/[id]/dashboard/actions";
import { DashboardCardDetail } from "../../admin/actions";

export type MyCompany = {
  id: number;
  name: string;
};

/*
 * Empresa do usuário logado.
 * Backend: GET /api/v1/companies/me — já existia (foi criada para a tela
 * de mensagens do cliente), porque nenhum endpoint client-facing expõe
 * `company_id`: `GET /client/controls` devolve dados de auditoria, sem
 * referência nenhuma à empresa.
 */
export async function getMyCompanyAction(): Promise<MyCompany> {
  await requireClient();
  const token = await getAccessToken();
  return callBackend<MyCompany>("/api/v1/companies/me", {
    token: token ?? undefined,
  });
}

/*
 * Quadro da própria empresa, em modo leitura.
 * Backend: GET /api/v1/dashboard/companies/{id}/board.
 *
 * `include_hidden` é sempre `false`: card oculto e coluna arquivada são
 * decisão interna do auditor sobre o que ainda é trabalho em aberto —
 * mostrá-los ao cliente só produziria pergunta sobre algo que a
 * auditoria já tirou de cena.
 */
export async function getClientBoardAction(companyId: number): Promise<Board> {
  await requireClient();
  const token = await getAccessToken();
  return callBackend<Board>(
    `/api/v1/dashboard/companies/${companyId}/board?include_hidden=false&search=`,
    { token: token ?? undefined },
  );
}

/*
 * Detalhe de um card do próprio quadro.
 * Backend: GET /api/v1/dashboard/cards/{id}.
 *
 * Gêmea de `getCardDetailAction` de `admin/actions.ts`, com
 * `requireClient()` no lugar de `requireAdmin()`. O backend devolve
 * `checklist` e `history` VAZIOS para papel não-admin (B-A28) — não 403:
 * o card existe e o cliente tem direito de vê-lo, só não ao registro
 * interno do auditor sobre ele. `description` e `labels` vêm
 * preenchidos, porque são o que ele precisa para saber o que entregar
 * (U7).
 */
export async function getCardDetailAction(
  cardId: number,
): Promise<DashboardCardDetail> {
  await requireClient();
  const token = await getAccessToken();
  return callBackend<DashboardCardDetail>(`/api/v1/dashboard/cards/${cardId}`, {
    token: token ?? undefined,
  });
}

export type SendCardQuestionResult =
  | { ok: true }
  | { ok: false; message: string };

/*
 * Pergunta do cliente sobre um card.
 * Backend: POST /api/v1/dashboard/cards/{id}/entries, `CHAT_QUESTION`.
 *
 * O chat do card é bilateral por decisão de projeto — "sempre visível às
 * duas partes", ao contrário de checklist e histórico (B-A28). Uma
 * "conversa com o cliente" em que só o auditor escreve não é conversa, e
 * `Action.ASK_QUESTION` já autoriza `user` e `sub-user` justamente para
 * isto.
 *
 * `CHAT_QUESTION` e não `CHAT_ANSWER`: o tipo não é escolha do cliente.
 * `CHAT_ANSWER` está em ADMIN_ONLY_ENTRY_TYPES e o backend devolveria
 * 403 — o que é o comportamento correto, e é por isso que o tipo é
 * fixado aqui em vez de vir por parâmetro.
 */
export async function sendCardQuestionAction(
  cardId: number,
  content: string,
): Promise<SendCardQuestionResult> {
  await requireClient();
  const token = await getAccessToken();

  try {
    await callBackend(`/api/v1/dashboard/cards/${cardId}/entries`, {
      method: "POST",
      token: token ?? undefined,
      body: { entry_type: "CHAT_QUESTION", content },
    });
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao enviar a mensagem.";
    return { ok: false, message };
  }
}
