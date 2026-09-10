"use server";

import { revalidatePath } from "next/cache";
import { getAccessToken, requireAdmin } from "@/lib/session";
import { CardStatus } from "../../../actions";
import { callBackend } from "@/lib/server-backend";

export type BoardLabelRef = {
  id: number;
  name: string;
  color: string;
};

export type CompanyDashboardCardListItem = {
  id: number;
  control_code: string | null;
  title: string;
  tag: string;
  status: CardStatus;
  category_id: number | null;
  category_name: string | null;
  hidden: boolean;
  origin_template_card_id: number | null;
  is_outdated: boolean;
  column_id: number | null;
  position: string;
  description: string | null;
  labels: BoardLabelRef[];
};

export type BoardCard = {
  id: number;
  control_code: string | null;
  title: string;
  description: string | null;
  status: CardStatus;
  position: string;
  column_id: number | null;
  category_id: number | null;
  category_name: string | null;
  labels: BoardLabelRef[];
  hidden: boolean;
  origin_template_card_id: number | null;
  is_outdated: boolean;
};

export type BoardColumnKind = "COLUMN" | "SECTION";

export type BoardColumn = {
  id: number;
  name: string;
  kind: BoardColumnKind;
  position: string;
  hidden: boolean;
  wip_limit: number | null;
  cards: BoardCard[];
  card_count: number;
};

export type Board = {
  dashboard_id: number;
  company_id: number;
  title: string;
  columns: BoardColumn[];
  uncolumned: BoardCard[];
  labels: BoardLabelRef[];
};

export type DashboardCardCategory = {
  id: number;
  name: string;
  color: string;
  sort_order: number;
};

export type DashboardLabel = {
  id: number;
  name: string;
  color: string;
  sort_order: number;
};

export type DashboardTemplateOption = {
  id: number;
  name: string;
  description: string | null;
  is_default: boolean;
  card_count: number;
};

const ROTA_DASHBOARD = "/private/admin/empresas/[id]/dashboard";

/**
 * Quadro completo da empresa — colunas ordenadas, cards agrupados e o
 * vocabulário de etiquetas, numa chamada só.
 * Backend: GET /api/v1/dashboard/companies/{id}/board.
 */
export async function getBoardAction(
  companyId: number,
  includeHidden = false,
  search = "",
): Promise<Board> {
  await requireAdmin();
  const token = await getAccessToken();
  const parametros = new URLSearchParams({
    include_hidden: String(includeHidden),
    search,
  });
  return callBackend<Board>(
    `/api/v1/dashboard/companies/${companyId}/board?${parametros.toString()}`,
    { token: token ?? undefined },
  );
}

/**
 * Cards de UMA empresa, com categoria/ocultação/rastreio de template.
 * Backend: GET /api/v1/dashboard/companies/{id}/cards.
 */
export async function listCardsForCompanyAction(
  companyId: number,
  includeHidden = true,
): Promise<CompanyDashboardCardListItem[]> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<CompanyDashboardCardListItem[]>(
    `/api/v1/dashboard/companies/${companyId}/cards?include_hidden=${includeHidden}`,
    { token: token ?? undefined },
  );
}

/* Categorias disponíveis. Backend: GET /api/v1/admin/dashboard-categories.  */
export async function listCategoriesAction(): Promise<DashboardCardCategory[]> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<DashboardCardCategory[]>(
    "/api/v1/admin/dashboard-categories",
    {
      token: token ?? undefined,
    },
  );
}

/* Vocabulário de etiquetas. Backend: GET /api/v1/admin/dashboard-labels. */
export async function listLabelsAction(): Promise<DashboardLabel[]> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<DashboardLabel[]>("/api/v1/admin/dashboard-labels", {
    token: token ?? undefined,
  });
}

/* Templates disponíveis para aplicar. Backend: GET /api/v1/admin/templates. */
export async function listTemplatesAction(): Promise<
  DashboardTemplateOption[]
> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<DashboardTemplateOption[]>("/api/v1/admin/templates", {
    token: token ?? undefined,
  });
}

export type ApplyTemplateResult =
  | {
      ok: true;
      created_count: number;
      adopted_count: number;
      already_applied_count: number;
      outdated_card_ids: number[];
      columns_created_count: number;
    }
  | { ok: false; message: string };

/*
 * Aplica um template numa empresa já existente — idempotente: cria só o
 * que falta e sinaliza (sem sobrescrever) os cards que divergem do
 * template atual. Backend: POST
 * /api/v1/dashboard/companies/{id}/apply-template.
 */
export async function applyTemplateToCompanyAction(
  companyId: number,
  templateId: number,
): Promise<ApplyTemplateResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const result = await callBackend<{
      created_count: number;
      adopted_count: number;
      already_applied_count: number;
      outdated_card_ids: number[];
      columns_created_count: number;
    }>(`/api/v1/dashboard/companies/${companyId}/apply-template`, {
      method: "POST",
      token: token ?? undefined,
      body: { template_id: templateId },
    });
    revalidatePath(ROTA_DASHBOARD, "page");
    return { ok: true, ...result };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao aplicar o template.";
    return { ok: false, message };
  }
}

export type BulkCardOperation =
  | "hide"
  | "unhide"
  | "remove"
  | "set_category"
  | "set_column"
  | "restore_from_template";

export type BulkCardOperationResult =
  | { ok: true; affected_count: number }
  | { ok: false; message: string };

/*
 * Operação em lote sobre os cards de uma empresa. Backend: PATCH
 * /api/v1/dashboard/companies/{id}/cards/bulk.
 */
export async function bulkUpdateCardsAction(
  companyId: number,
  cardIds: number[],
  operation: BulkCardOperation,
  categoryId: number | null = null,
  columnId: number | null = null,
): Promise<BulkCardOperationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const result = await callBackend<{ affected_count: number }>(
      `/api/v1/dashboard/companies/${companyId}/cards/bulk`,
      {
        method: "PATCH",
        token: token ?? undefined,
        body: {
          card_ids: cardIds,
          operation,
          category_id: categoryId,
          column_id: columnId,
        },
      },
    );
    return { ok: true, affected_count: result.affected_count };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao aplicar a operação";
    return { ok: false, message };
  }
}

export type CreateCardResult =
  | { ok: true; card: CompanyDashboardCardListItem }
  | { ok: false; message: string };

/*
 * Cria um card manual ("+ Adicionar card" no rodapé de uma coluna). O
 * card nasce sem `origin_template_card_id` — é o que o distingue
 * visualmente como "custom" na lista.
 */
export async function createCardForCompanyAction(
  companyId: number,
  title: string,
  categoryId: number,
  controlCode: string | null,
  columnId: number | null = null,
  description: string | null = null,
): Promise<CreateCardResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const card = await callBackend<CompanyDashboardCardListItem>(
      `/api/v1/dashboard/companies/${companyId}/cards`,
      {
        method: "POST",
        token: token ?? undefined,
        body: {
          title,
          category_id: categoryId,
          control_code: controlCode,
          column_id: columnId,
          description,
        },
      },
    );
    return { ok: true, card };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao criar o card";
    return { ok: false, message };
  }
}

// -------------------------------------------------- Colunas do quadro

export type BoardColumnRef = {
  id: number;
  name: string;
  kind: BoardColumnKind;
  position: string;
  hidden: boolean;
  wip_limit: number | null;
};

export type ColumnMutationResult =
  | { ok: true; column: BoardColumnRef }
  | { ok: false; message: string };

/* Backend: POST /api/v1/dashboard/companies/{id}/columns. */
export async function createColumnAction(
  companyId: number,
  name: string,
  kind: BoardColumnKind = "COLUMN",
  afterColumnId: number | null = null,
): Promise<ColumnMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const column = await callBackend<BoardColumnRef>(
      `/api/v1/dashboard/companies/${companyId}/columns`,
      {
        method: "POST",
        token: token ?? undefined,
        body: { name, kind, after_column_id: afterColumnId },
      },
    );
    // Criar coluna muda a ESTRUTURA do quadro, não a posição de um item:
    // revalidar aqui é barato e mantém o Server Component em dia.
    revalidatePath(ROTA_DASHBOARD, "page");
    return { ok: true, column };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao criar a coluna.";
    return { ok: false, message };
  }
}

/* Backend: PATCH /api/v1/dashboard/columns/{id}. */
export async function updateColumnAction(
  columnId: number,
  name: string,
  hidden: boolean,
  wipLimit: number | null,
): Promise<ColumnMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const column = await callBackend<BoardColumnRef>(
      `/api/v1/dashboard/columns/${columnId}`,
      {
        method: "PATCH",
        token: token ?? undefined,
        body: { name, hidden, wip_limit: wipLimit },
      },
    );
    return { ok: true, column };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao editar a coluna.";
    return { ok: false, message };
  }
}

/* Backend: PATCH /api/v1/dashboard/columns/{id}/move. */
export async function moveColumnAction(
  columnId: number,
  prevColumnId: number | null,
  nextColumnId: number | null,
): Promise<ColumnMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const column = await callBackend<BoardColumnRef>(
      `/api/v1/dashboard/columns/${columnId}/move`,
      {
        method: "PATCH",
        token: token ?? undefined,
        body: { prev_column_id: prevColumnId, next_column_id: nextColumnId },
      },
    );
    return { ok: true, column };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao mover a coluna.";
    return { ok: false, message };
  }
}

export type DeleteColumnResult = { ok: true } | { ok: false; message: string };

/* Backend: DELETE /api/v1/dashboard/columns/{id} — 409 se houver card visível. */
export async function deleteColumnAction(
  columnId: number,
): Promise<DeleteColumnResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(`/api/v1/dashboard/columns/${columnId}`, {
      method: "DELETE",
      token: token ?? undefined,
    });
    revalidatePath(ROTA_DASHBOARD, "page");
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao excluir a coluna.";
    return { ok: false, message };
  }
}

// ------------------------------------------------------- Cards do quadro

export type MoveCardResult =
  | { ok: true; card: BoardCard }
  | { ok: false; message: string };

/**
 * Move um card entre/dentro de colunas.
 *
 * O cliente manda ÂNCORAS (`prevCardId`/`nextCardId`), nunca a chave de
 * ordenação: quem calcula a `position` é o servidor, dentro da transação
 * (§4.2 do PRD).
 *
 * **Sem `revalidatePath` de propósito** (§4.7 do PRD): revalidar
 * recarregaria os 215 cards a cada arrasto e desfaria o `useOptimistic`
 * no meio da interação. O estado local é a verdade durante a sessão.
 */
export async function moveCardAction(
  cardId: number,
  columnId: number | null,
  prevCardId: number | null,
  nextCardId: number | null,
): Promise<MoveCardResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const card = await callBackend<BoardCard>(
      `/api/v1/dashboard/cards/${cardId}/move`,
      {
        method: "PATCH",
        token: token ?? undefined,
        body: {
          column_id: columnId,
          prev_card_id: prevCardId,
          next_card_id: nextCardId,
        },
      },
    );
    return { ok: true, card };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao mover o card.";
    return { ok: false, message };
  }
}

export type UpdateCardResult =
  | { ok: true; card: BoardCard }
  | { ok: false; message: string };

/* Backend: PATCH /api/v1/dashboard/cards/{id} — texto do card, nunca status. */
export async function updateCardAction(
  cardId: number,
  title: string,
  description: string | null,
  controlCode: string | null,
  categoryId: number | null,
): Promise<UpdateCardResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const card = await callBackend<BoardCard>(
      `/api/v1/dashboard/cards/${cardId}`,
      {
        method: "PATCH",
        token: token ?? undefined,
        body: {
          title,
          description,
          control_code: controlCode,
          category_id: categoryId,
        },
      },
    );
    return { ok: true, card };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao editar o card.";
    return { ok: false, message };
  }
}

export type SetCardLabelsResult =
  | { ok: true; labels: BoardLabelRef[] }
  | { ok: false; message: string };

/* Backend: PUT /api/v1/dashboard/cards/{id}/labels — substitui o conjunto. */
export async function setCardLabelsAction(
  cardId: number,
  labelIds: number[],
): Promise<SetCardLabelsResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const labels = await callBackend<BoardLabelRef[]>(
      `/api/v1/dashboard/cards/${cardId}/labels`,
      {
        method: "PUT",
        token: token ?? undefined,
        body: { label_ids: labelIds },
      },
    );
    return { ok: true, labels };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao aplicar as etiquetas.";
    return { ok: false, message };
  }
}
