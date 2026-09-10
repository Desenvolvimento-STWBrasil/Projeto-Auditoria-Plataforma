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
  createTemplateAction,
  createTemplateCardAction,
  createTemplateCategoryAction,
  createTemplateColumnAction,
  deleteTemplateAction,
  deleteTemplateCategoryAction,
  deleteTemplateColumnAction,
  getTemplateDetailAction,
  listTemplateCategoriesAction,
  listTemplatesAction,
  moveTemplateColumnAction,
  updateTemplateAction,
  updateTemplateCardAction,
  updateTemplateCategoryAction,
  updateTemplateColumnAction,
} from "./actions";

beforeEach(prepararSessao);

/**
 * Editor de templates (O.4). Duas rotas merecem atenção especial:
 *
 * - `POST /admin/templates/{id}/cards` foi **sobrescrita por engano** no
 *   BLOCO P e voltava 404 (defeito registrado em P.7). O teste fixa a
 *   rota.
 * - Os dois `DELETE` respondem **409** quando o template ou o card está
 *   em uso (B-A25) — o resultado tem de chegar tratável à tela, não como
 *   exceção.
 */
describe("leitura de templates", () => {
  it("lista templates", async () => {
    backendMock.mockResolvedValue([]);

    await listTemplatesAction();

    expect(requireAdminMock).toHaveBeenCalled();
    expect(ultimaChamada()[0]).toBe("/api/v1/admin/templates");
  });

  it("lê o detalhe do template", async () => {
    backendMock.mockResolvedValue({ id: 2, cards: [] });

    await getTemplateDetailAction(2);

    expect(ultimaChamada()[0]).toBe("/api/v1/admin/templates/2");
  });

  it("lista as categorias disponíveis", async () => {
    backendMock.mockResolvedValue([]);

    await listTemplateCategoriesAction();

    expect(ultimaChamada()[0]).toBe("/api/v1/admin/dashboard-categories");
  });
});

describe("CRUD de template", () => {
  it("cria com POST", async () => {
    backendMock.mockResolvedValue({ id: 3 });

    const resultado = await createTemplateAction({
      name: "ISO 27001",
      description: null,
      is_default: false,
    });

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/templates");
    expect(opcoes.method).toBe("POST");
    expect(resultado.ok).toBe(true);
  });

  it("atualiza com PATCH", async () => {
    backendMock.mockResolvedValue({ id: 3 });

    await updateTemplateAction(3, {
      name: "ISO 27001:2022",
      description: "Anexo A",
      is_default: true,
    });

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/templates/3");
    expect(opcoes.method).toBe("PATCH");
  });

  it("exclui com DELETE", async () => {
    backendMock.mockResolvedValue(null);

    await deleteTemplateAction(3);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/templates/3");
    expect(opcoes.method).toBe("DELETE");
  });

  it("traz o 409 de template em uso até a tela (B-A25)", async () => {
    backendMock.mockRejectedValue(
      new Error("Template em uso por 9 card(s) de empresas já configuradas."),
    );

    const resultado = await deleteTemplateAction(3);

    expect(resultado.ok).toBe(false);
    expect(resultado).toHaveProperty("message");
  });
});

describe("colunas de template", () => {
  it("cria coluna pela rota do template", async () => {
    backendMock.mockResolvedValue({ id: 1 });

    await createTemplateColumnAction(3, {
      name: "Controle 5",
      kind: "COLUMN",
    });

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/templates/3/columns");
    expect(opcoes.method).toBe("POST");
    expect(opcoes.body).toMatchObject({ name: "Controle 5", kind: "COLUMN" });
  });

  it("cria coluna do tipo seção", async () => {
    backendMock.mockResolvedValue({ id: 2 });

    await createTemplateColumnAction(3, {
      name: "ISO 27001:2022 >>",
      kind: "SECTION",
    });

    const [, opcoes] = ultimaChamada();
    expect(opcoes.body).toMatchObject({ kind: "SECTION" });
  });

  it("edita coluna com PATCH", async () => {
    backendMock.mockResolvedValue({ id: 1 });

    await updateTemplateColumnAction(3, 1, {
      name: "Renomeada",
      kind: "COLUMN",
    });

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/templates/3/columns/1");
    expect(opcoes.method).toBe("PATCH");
  });

  it("move coluna mandando âncoras, nunca a posição", async () => {
    backendMock.mockResolvedValue({ id: 1 });

    await moveTemplateColumnAction(3, 1, 5, 6);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/templates/3/columns/1/move");
    expect(opcoes.body).toEqual({ prev_column_id: 5, next_column_id: 6 });
  });

  it("devolve falha tratável quando a coluna está em uso (409)", async () => {
    backendMock.mockRejectedValue(
      new Error("Coluna de template em uso por 12 card(s) de template."),
    );

    const resultado = await deleteTemplateColumnAction(3, 1);

    expect(resultado.ok).toBe(false);
    if (!resultado.ok) {
      expect(resultado.message).toContain("12 card(s)");
    }
  });
});

describe("cards de template com coluna", () => {
  it("envia template_column_id ao criar", async () => {
    backendMock.mockResolvedValue({ id: 9 });

    await createTemplateCardAction(3, {
      title: "Política de SI",
      description: "Texto normativo",
      category_id: 2,
      template_column_id: 1,
      sort_order: 0,
    });

    const [, opcoes] = ultimaChamada();
    expect(opcoes.body).toMatchObject({
      template_column_id: 1,
      description: "Texto normativo",
    });
  });

  it("envia template_column_id nulo quando o card não tem coluna", async () => {
    backendMock.mockResolvedValue({ id: 9 });

    await updateTemplateCardAction(9, {
      title: "Card",
      description: null,
      category_id: null,
      template_column_id: null,
      sort_order: 0,
    });

    const [, opcoes] = ultimaChamada();
    expect(opcoes.body).toMatchObject({ template_column_id: null });
  });
});

describe("categorias de card (vocabulário global)", () => {
  /*
   * O CRUD de categoria mudou de casa: vivia como um "+ Nova categoria"
   * no quadro de UMA empresa, o que sugeria que a categoria pertencia
   * àquela empresa — criar uma ali afetava todas as empresas da
   * plataforma. Agora mora na aba Templates, junto do resto do
   * vocabulário global.
   */
  it("cria com POST na rota global de categorias", async () => {
    backendMock.mockResolvedValue({ id: 5, name: "Governança" });

    const resultado = await createTemplateCategoryAction({
      name: "Governança",
      color: "#788c5d",
      sort_order: 0,
    });

    expect(requireAdminMock).toHaveBeenCalled();
    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/dashboard-categories");
    expect(opcoes.method).toBe("POST");
    expect(opcoes.body).toEqual({
      name: "Governança",
      color: "#788c5d",
      sort_order: 0,
    });
    expect(resultado).toEqual({ ok: true });
  });

  it("propaga o 409 de nome repetido", async () => {
    backendMock.mockRejectedValue(
      new Error("Já existe uma categoria com esse nome"),
    );

    await expect(
      createTemplateCategoryAction({
        name: "Governança",
        color: "#788c5d",
        sort_order: 0,
      }),
    ).resolves.toEqual({
      ok: false,
      message: "Já existe uma categoria com esse nome",
    });
  });

  it("edita com PATCH", async () => {
    backendMock.mockResolvedValue({ id: 5, name: "Governança TI" });

    const resultado = await updateTemplateCategoryAction(5, {
      name: "Governança TI",
      color: "#123456",
      sort_order: 2,
    });

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/dashboard-categories/5");
    expect(opcoes.method).toBe("PATCH");
    expect(resultado).toEqual({ ok: true });
  });

  it("exclui com DELETE", async () => {
    backendMock.mockResolvedValue(undefined);

    const resultado = await deleteTemplateCategoryAction(5);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/dashboard-categories/5");
    expect(opcoes.method).toBe("DELETE");
    expect(resultado).toEqual({ ok: true });
  });

  it("repassa a contagem do 409 quando a categoria está em uso", async () => {
    /*
     * A exclusão é BLOQUEADA, não em cascata: a FK é `SET NULL`, então
     * apagar em cascata deixaria N cards sem classificação em silêncio.
     * A mensagem do backend é a que diz QUANTOS — perdê-la aqui tiraria
     * do admin a informação de que ele precisa para reclassificar.
     */
    backendMock.mockRejectedValue(
      new Error("Categoria em uso por 12 card(s)/definição(ões) de template"),
    );

    await expect(deleteTemplateCategoryAction(5)).resolves.toEqual({
      ok: false,
      message: "Categoria em uso por 12 card(s)/definição(ões) de template",
    });
  });

  it("lista pela mesma rota global", async () => {
    backendMock.mockResolvedValue([]);

    await listTemplateCategoriesAction();

    expect(ultimaChamada()[0]).toBe("/api/v1/admin/dashboard-categories");
  });
});
