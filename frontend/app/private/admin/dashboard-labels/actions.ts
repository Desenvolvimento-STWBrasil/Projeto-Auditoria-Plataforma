"use server";

import { requireAdmin, getAccessToken } from "@/lib/session";
import { callBackend } from "@/lib/server-backend";

export type DashboardLabelItem = {
  id: number;
  name: string;
  color: string;
  sort_order: number;
};

export type LabelMutationResult = { ok: true } | { ok: false; message: string };

/** Backend: GET /api/v1/admin/dashboard-labels. */
export async function listDashboardLabelsAction(): Promise<
  DashboardLabelItem[]
> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<DashboardLabelItem[]>("/api/v1/admin/dashboard-labels", {
    token: token ?? undefined,
  });
}

/** Backend: POST /api/v1/admin/dashboard-labels — 409 em nome duplicado. */
export async function createDashboardLabelAction(input: {
  name: string;
  color: string;
  sort_order: number;
}): Promise<LabelMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend("/api/v1/admin/dashboard-labels", {
      method: "POST",
      token: token ?? undefined,
      body: input,
    });
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao criar a etiqueta.";
    return { ok: false, message };
  }
}

/** Backend: PATCH /api/v1/admin/dashboard-labels/{id}. */
export async function updateDashboardLabelAction(
  labelId: number,
  input: { name: string; color: string; sort_order: number },
): Promise<LabelMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(`/api/v1/admin/dashboard-labels/${labelId}`, {
      method: "PATCH",
      token: token ?? undefined,
      body: input,
    });
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao editar a etiqueta.";
    return { ok: false, message };
  }
}

/**
 * Backend: DELETE /api/v1/admin/dashboard-labels/{id}.
 *
 * Devolve 409 (e não exclui) se a etiqueta estiver aplicada a algum
 * card — mesma regra de `CategoryInUseError`. A mensagem do backend traz
 * o número de cards, e é ela que a UI exibe: "em uso por 63 card(s)"
 * diz ao admin exatamente o que fazer antes de tentar de novo.
 */
export async function deleteDashboardLabelAction(
  labelId: number,
): Promise<LabelMutationResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    await callBackend(`/api/v1/admin/dashboard-labels/${labelId}`, {
      method: "DELETE",
      token: token ?? undefined,
    });
    return { ok: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao excluir a etiqueta.";
    return { ok: false, message };
  }
}
