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
  applyTemplateToCompanyAction,
  bulkUpdateCardsAction,
  createCardForCompanyAction,
  createColumnAction,
  deleteColumnAction,
  getBoardAction,
  listCardsForCompanyAction,
  listCategoriesAction,
  listLabelsAction,
  listTemplatesAction,
  moveCardAction,
  moveColumnAction,
  setCardLabelsAction,
  updateCardAction,
  updateColumnAction,
} from "./actions";

beforeEach(prepararSessao);

describe("cards da empresa", () => {
  it("inclui os ocultos por padrão", async () => {
    backendMock.mockResolvedValue([]);

    await listCardsForCompanyAction(4);

    expect(requireAdminMock).toHaveBeenCalled();
    expect(ultimaChamada()[0]).toBe(
      "/api/v1/dashboard/companies/4/cards?include_hidden=true",
    );
  });

  it("respeita include_hidden=false", async () => {
    backendMock.mockResolvedValue([]);

    await listCardsForCompanyAction(4, false);

    expect(ultimaChamada()[0]).toBe(
      "/api/v1/dashboard/companies/4/cards?include_hidden=false",
    );
  });

  it("cria card pela rota da empresa", async () => {
    backendMock.mockResolvedValue({ id: 20 });

    await createCardForCompanyAction(4, "Novo card", 2, "5.1");

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/dashboard/companies/4/cards");
    expect(opcoes.method).toBe("POST");
  });
});

describe("categorias", () => {
  it("lista pela rota de dashboard-categories", async () => {
    backendMock.mockResolvedValue([]);

    await listCategoriesAction();

    expect(ultimaChamada()[0]).toBe("/api/v1/admin/dashboard-categories");
  });

  // A CRIAÇÃO de categoria deixou de morar aqui: categoria é vocabulário
  // global e o CRUD dela vive em `templates/actions.ts`, coberto por
  // `templates/actions.test.ts`. Este arquivo mantém só a LEITURA, que é
  // o que o quadro de uma empresa consome.
});

describe("aplicação de template (B-A24)", () => {
  it("chama apply-template e devolve as contagens", async () => {
    backendMock.mockResolvedValue({
      created_count: 0,
      adopted_count: 9,
      already_applied_count: 0,
      outdated_card_ids: [],
    });

    const resultado = await applyTemplateToCompanyAction(4, 2);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/dashboard/companies/4/apply-template");
    expect(opcoes.method).toBe("POST");
    expect(resultado.ok).toBe(true);
  });

  it("lista os templates aplicáveis", async () => {
    backendMock.mockResolvedValue([]);

    await listTemplatesAction();

    expect(ultimaChamada()[0]).toBe("/api/v1/admin/templates");
  });
});

describe("edição em massa", () => {
  it.each(["hide", "unhide", "remove", "restore_from_template"] as const)(
    "envia a operação %s pela rota bulk",
    async (operacao) => {
      backendMock.mockResolvedValue({ affected_count: 3 });

      await bulkUpdateCardsAction(4, [1, 2, 3], operacao);

      const [rota, opcoes] = ultimaChamada();
      expect(rota).toBe("/api/v1/dashboard/companies/4/cards/bulk");
      expect(opcoes.method).toBe("PATCH");
      expect(opcoes.body).toMatchObject({
        card_ids: [1, 2, 3],
        operation: operacao,
      });
    },
  );

  it("envia category_id em set_category", async () => {
    backendMock.mockResolvedValue({ affected_count: 2 });

    await bulkUpdateCardsAction(4, [1, 2], "set_category", 7);

    const [, opcoes] = ultimaChamada();
    expect(opcoes.body).toMatchObject({
      operation: "set_category",
      category_id: 7,
    });
  });

  it("devolve falha tratável quando o backend recusa", async () => {
    backendMock.mockRejectedValue(new Error("Categoria não encontrada"));

    const resultado = await bulkUpdateCardsAction(4, [1], "set_category", 99);

    expect(resultado.ok).toBe(false);
  });
});

describe("quadro (board)", () => {
  it("lê o quadro pela rota de board, com include_hidden e busca", async () => {
    backendMock.mockResolvedValue({ columns: [], uncolumned: [], labels: [] });

    await getBoardAction(4, true, "backup");

    expect(requireAdminMock).toHaveBeenCalled();
    expect(ultimaChamada()[0]).toBe(
      "/api/v1/dashboard/companies/4/board?include_hidden=true&search=backup",
    );
  });

  it("lista o vocabulário de etiquetas", async () => {
    backendMock.mockResolvedValue([]);

    await listLabelsAction();

    expect(ultimaChamada()[0]).toBe("/api/v1/admin/dashboard-labels");
  });
});

describe("colunas", () => {
  it("cria coluna pela rota da empresa", async () => {
    backendMock.mockResolvedValue({ id: 1, name: "Nova" });

    await createColumnAction(4, "Nova", "COLUMN", null);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/dashboard/companies/4/columns");
    expect(opcoes.method).toBe("POST");
    expect(opcoes.body).toMatchObject({
      name: "Nova",
      kind: "COLUMN",
      after_column_id: null,
    });
  });

  it("edita coluna com PATCH", async () => {
    backendMock.mockResolvedValue({ id: 1 });

    await updateColumnAction(1, "Renomeada", true, 5);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/dashboard/columns/1");
    expect(opcoes.method).toBe("PATCH");
    expect(opcoes.body).toMatchObject({
      name: "Renomeada",
      hidden: true,
      wip_limit: 5,
    });
  });

  it("move coluna mandando âncoras", async () => {
    backendMock.mockResolvedValue({ id: 1 });

    await moveColumnAction(1, 2, 3);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/dashboard/columns/1/move");
    expect(opcoes.body).toMatchObject({
      prev_column_id: 2,
      next_column_id: 3,
    });
  });

  it("devolve falha tratável quando o backend recusa a exclusão (409)", async () => {
    backendMock.mockRejectedValue(
      new Error("Coluna com 3 card(s) visível(is)."),
    );

    const resultado = await deleteColumnAction(1);

    expect(resultado.ok).toBe(false);
    if (!resultado.ok) {
      expect(resultado.message).toContain("card(s)");
    }
  });
});

describe("mover card", () => {
  it("manda ÂNCORAS, nunca a chave de ordenação", async () => {
    backendMock.mockResolvedValue({ id: 1, position: "a0V" });

    await moveCardAction(1, 12, 88, 91);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/dashboard/cards/1/move");
    expect(opcoes.method).toBe("PATCH");
    expect(opcoes.body).toEqual({
      column_id: 12,
      prev_card_id: 88,
      next_card_id: 91,
    });
    // O cliente nunca calcula `position` (§4.2 do PRD).
    expect(opcoes.body).not.toHaveProperty("position");
  });

  it("devolve falha tratável para o otimismo reverter (CA-16)", async () => {
    backendMock.mockRejectedValue(new Error("Coluna não encontrada"));

    const resultado = await moveCardAction(1, 999, null, null);

    expect(resultado.ok).toBe(false);
  });
});

describe("edição de card e etiquetas", () => {
  it("edita o texto do card sem tocar em status", async () => {
    backendMock.mockResolvedValue({ id: 1 });

    await updateCardAction(1, "Novo título", "Descrição", "5.1", 2);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/dashboard/cards/1");
    expect(opcoes.method).toBe("PATCH");
    expect(opcoes.body).not.toHaveProperty("status");
  });

  it("substitui o conjunto de etiquetas com PUT", async () => {
    backendMock.mockResolvedValue([]);

    await setCardLabelsAction(1, [2, 3]);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/dashboard/cards/1/labels");
    expect(opcoes.method).toBe("PUT");
    expect(opcoes.body).toMatchObject({ label_ids: [2, 3] });
  });
});

describe("edição em massa por coluna", () => {
  it("envia column_id em set_column", async () => {
    backendMock.mockResolvedValue({ affected_count: 3 });

    await bulkUpdateCardsAction(4, [1, 2, 3], "set_column", null, 12);

    const [, opcoes] = ultimaChamada();
    expect(opcoes.body).toMatchObject({
      operation: "set_column",
      column_id: 12,
    });
  });
});

describe("criação de card no quadro", () => {
  it("envia column_id e description", async () => {
    backendMock.mockResolvedValue({ id: 20 });

    await createCardForCompanyAction(4, "Card", 2, "5.1", 12, "Texto");

    const [, opcoes] = ultimaChamada();
    expect(opcoes.body).toMatchObject({
      column_id: 12,
      description: "Texto",
    });
  });
});
