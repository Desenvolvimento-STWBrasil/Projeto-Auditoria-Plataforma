"use server";

import { requireAdmin, getAccessToken } from "@/lib/session";
import { callBackend } from "@/lib/server-backend";

export type TemplateListItem = {
  id: number;
  name: string;
  description: string | null;
  is_default: boolean;
  card_count: number;
};

export type TemplateColumnKind = "COLUMN" | "SECTION";

export type TemplateColumn = {
  id: number;
  name: string;
  kind: TemplateColumnKind;
  position: string;
  card_count: number;
};

export type TemplateCard = {
  id: number;
  title: string;
  description: string | null;
  category_id: number | null;
  category_name: string | null;
  template_column_id: number | null;
  position: string;
  sort_order: number;
};

export type TemplateDetail = TemplateListItem & {
  cards: TemplateCard[];
  columns: TemplateColumn[];
};

export type TemplateCategory = {
  id: number;
  name: string;
  color: string;
  sort_order: number;
};

/** Backend: GET /api/v1/admin/templates. */
export async function listTemplatesAction(): Promise<TemplateListItem[]> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<TemplateListItem[]>("/api/v1/admin/templates", {
    token: token ?? undefined,
  });
}

/** Backend: GET /api/v1/admin/templates/{id}. */
export async function getTemplateDetailAction(
  templateId: number,
): Promise<TemplateDetail> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<TemplateDetail>(`/api/v1/admin/templates/${templateId}`, {
    token: token ?? undefined,
  });
}

/** Backend: GET /api/v1/admin/dashboard-categories. */
export async function listTemplateCategoriesAction(): Promise<
  TemplateCategory[]
> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<TemplateCategory[]>("/api/v1/admin/dashboard-categories", {
    token: token ?? undefined,
  });
}

export type TemplateMutationResult =
  | { ok: true }
  | { ok: false; message: string };

/*
 * ------------------------------------------------ Categorias de card
 *
 * O CRUD de categoria mora aqui, e não em
 * `empresas/[id]/dashboard/actions.ts`, porque categoria é vocabulário
 * GLOBAL: ela não pertence a empresa nenhuma. O "+ Nova categoria" vivia
 * no quadro de UMA empresa, o que sugeria o contrário — criar uma
 * categoria ali afetava todas as empresas da plataforma, sem nada na tela
 * dizer isso.
 *
 * Mesmo formato de `dashboard-labels/actions.ts`: os dois são
 * vocabulários globais com o mesmo CRUD e a mesma regra de exclusão
 * bloqueada quando em uso.
 */

export type CategoryMutationResult =
  | { ok: true }
  | { ok: false; message: string };

/** Backend: POST /api/v1/admin/dashboard-categories — 409 se o nome repetir. */
export async function createTemplateCategoryAction(input: {
  name: string;
  color: string;
  sort_order: number;
}): Promise<CategoryMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend("/api/v1/admin/dashboard-categories", {
      method: "POST",
      token: token ?? undefined,
      body: input,
    });
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao criar a categoria.";
    return { ok: false, message };
  }
}

/** Backend: PATCH /api/v1/admin/dashboard-categories/{id}. */
export async function updateTemplateCategoryAction(
  categoryId: number,
  input: { name: string; color: string; sort_order: number },
): Promise<CategoryMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(`/api/v1/admin/dashboard-categories/${categoryId}`, {
      method: "PATCH",
      token: token ?? undefined,
      body: input,
    });
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao editar a categoria.";
    return { ok: false, message };
  }
}

/**
 * Backend: DELETE /api/v1/admin/dashboard-categories/{id}.
 *
 * Devolve **409** quando a categoria está em uso por algum card ou
 * definição de template, com a contagem na mensagem. A exclusão é
 * BLOQUEADA, não em cascata — a FK é `SET NULL`, então apagar em cascata
 * deixaria N cards sem classificação em silêncio. Quem chama repassa a
 * mensagem do backend, que é a que diz quantos.
 */
export async function deleteTemplateCategoryAction(
  categoryId: number,
): Promise<CategoryMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(`/api/v1/admin/dashboard-categories/${categoryId}`, {
      method: "DELETE",
      token: token ?? undefined,
    });
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao excluir a categoria.";
    return { ok: false, message };
  }
}

/** Backend: POST /api/v1/admin/templates. */
export async function createTemplateAction(input: {
  name: string;
  description: string | null;
  is_default: boolean;
}): Promise<TemplateMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend("/api/v1/admin/templates", {
      method: "POST",
      token: token ?? undefined,
      body: input,
    });
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao criar o template.";
    return { ok: false, message };
  }
}

/** Backend: PATCH /api/v1/admin/templates/{id}. */
export async function updateTemplateAction(
  templateId: number,
  input: { name: string; description: string | null; is_default: boolean },
): Promise<TemplateMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(`/api/v1/admin/templates/${templateId}`, {
      method: "PATCH",
      token: token ?? undefined,
      body: input,
    });
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao editar o template.";
    return { ok: false, message };
  }
}

/** Backend: DELETE /api/v1/admin/templates/{id}. */
export async function deleteTemplateAction(
  templateId: number,
): Promise<TemplateMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(`/api/v1/admin/templates/${templateId}`, {
      method: "DELETE",
      token: token ?? undefined,
    });
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao excluir o template.";
    return { ok: false, message };
  }
}

// -------------------------------------------------- Colunas de template

/** Backend: POST /api/v1/admin/templates/{id}/columns. */
export async function createTemplateColumnAction(
  templateId: number,
  input: { name: string; kind: TemplateColumnKind },
): Promise<TemplateMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(`/api/v1/admin/templates/${templateId}/columns`, {
      method: "POST",
      token: token ?? undefined,
      body: input,
    });
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao criar a coluna.";
    return { ok: false, message };
  }
}

/** Backend: PATCH /api/v1/admin/templates/{id}/columns/{colId}. */
export async function updateTemplateColumnAction(
  templateId: number,
  columnId: number,
  input: { name: string; kind: TemplateColumnKind },
): Promise<TemplateMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(
      `/api/v1/admin/templates/${templateId}/columns/${columnId}`,
      { method: "PATCH", token: token ?? undefined, body: input },
    );
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao editar a coluna.";
    return { ok: false, message };
  }
}

/**
 * Backend: PATCH /api/v1/admin/templates/{id}/columns/{colId}/move.
 *
 * Manda ÂNCORAS (`prev_column_id`/`next_column_id`), nunca a chave de
 * ordenação — mesma regra do quadro (§4.2 do PRD): quem calcula a
 * `position` é o servidor, dentro da transação.
 */
export async function moveTemplateColumnAction(
  templateId: number,
  columnId: number,
  prevColumnId: number | null,
  nextColumnId: number | null,
): Promise<TemplateMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(
      `/api/v1/admin/templates/${templateId}/columns/${columnId}/move`,
      {
        method: "PATCH",
        token: token ?? undefined,
        body: { prev_column_id: prevColumnId, next_column_id: nextColumnId },
      },
    );
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao mover a coluna.";
    return { ok: false, message };
  }
}

/** Backend: DELETE /api/v1/admin/templates/{id}/columns/{colId} — 409 se em uso. */
export async function deleteTemplateColumnAction(
  templateId: number,
  columnId: number,
): Promise<TemplateMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(
      `/api/v1/admin/templates/${templateId}/columns/${columnId}`,
      { method: "DELETE", token: token ?? undefined },
    );
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao excluir a coluna.";
    return { ok: false, message };
  }
}

// ---------------------------------------------------- Cards de template

/** Backend: POST /api/v1/admin/templates/{id}/cards. */
export async function createTemplateCardAction(
  templateId: number,
  input: {
    title: string;
    description: string | null;
    category_id: number | null;
    template_column_id: number | null;
    sort_order: number;
  },
): Promise<TemplateMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(`/api/v1/admin/templates/${templateId}/cards`, {
      method: "POST",
      token: token ?? undefined,
      body: input,
    });
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao criar o card.";
    return { ok: false, message };
  }
}

/** Backend: PATCH /api/v1/admin/templates/template-cards/{id}. */
export async function updateTemplateCardAction(
  templateCardId: number,
  input: {
    title: string;
    description: string | null;
    category_id: number | null;
    template_column_id: number | null;
    sort_order: number;
  },
): Promise<TemplateMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(
      `/api/v1/admin/templates/template-cards/${templateCardId}`,
      { method: "PATCH", token: token ?? undefined, body: input },
    );
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao editar o card.";
    return { ok: false, message };
  }
}

/** Backend: DELETE /api/v1/admin/templates/template-cards/{id}. */
export async function deleteTemplateCardAction(
  templateCardId: number,
): Promise<TemplateMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(
      `/api/v1/admin/templates/template-cards/${templateCardId}`,
      { method: "DELETE", token: token ?? undefined },
    );
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao excluir o card.";
    return { ok: false, message };
  }
}
