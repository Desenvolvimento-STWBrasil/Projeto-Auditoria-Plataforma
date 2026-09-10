import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-backend");
vi.mock("@/lib/session");
vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));

import {
  backendMock,
  prepararSessao,
  requireAdminMock,
  ultimaChamada,
} from "@/test/helpers/action-mocks";
import {
  createDashboardLabelAction,
  deleteDashboardLabelAction,
  listDashboardLabelsAction,
  updateDashboardLabelAction,
} from "./actions";

beforeEach(prepararSessao);

describe("CRUD de etiquetas", () => {
  it("lista pela rota de dashboard-labels", async () => {
    backendMock.mockResolvedValue([]);

    await listDashboardLabelsAction();

    expect(requireAdminMock).toHaveBeenCalled();
    expect(ultimaChamada()[0]).toBe("/api/v1/admin/dashboard-labels");
  });

  it("cria com POST", async () => {
    backendMock.mockResolvedValue({ id: 1 });

    const resultado = await createDashboardLabelAction({
      name: "Item Critico",
      color: "#96311D",
      sort_order: 0,
    });

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/dashboard-labels");
    expect(opcoes.method).toBe("POST");
    expect(resultado.ok).toBe(true);
  });

  it("edita com PATCH", async () => {
    backendMock.mockResolvedValue({ id: 1 });

    await updateDashboardLabelAction(1, {
      name: "Crítico",
      color: "#000000",
      sort_order: 2,
    });

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/dashboard-labels/1");
    expect(opcoes.method).toBe("PATCH");
  });

  it("exclui com DELETE", async () => {
    backendMock.mockResolvedValue(null);

    await deleteDashboardLabelAction(1);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/dashboard-labels/1");
    expect(opcoes.method).toBe("DELETE");
  });

  it("devolve a mensagem do backend quando a etiqueta está em uso (409)", async () => {
    backendMock.mockRejectedValue(new Error("Etiqueta em uso por 63 card(s)"));

    const resultado = await deleteDashboardLabelAction(1);

    expect(resultado.ok).toBe(false);
    if (!resultado.ok) {
      expect(resultado.message).toContain("63 card(s)");
    }
  });

  it("devolve falha tratável em nome duplicado (409)", async () => {
    backendMock.mockRejectedValue(
      new Error("Já existe uma etiqueta com esse nome"),
    );

    const resultado = await createDashboardLabelAction({
      name: "Item Critico",
      color: "#96311D",
      sort_order: 0,
    });

    expect(resultado.ok).toBe(false);
  });
});
