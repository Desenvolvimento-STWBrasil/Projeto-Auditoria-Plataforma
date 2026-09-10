// @vitest-environment jsdom

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TemplatesClient } from "./templates-client";
import type { TemplateCategory, TemplateListItem } from "./actions";

/**
 * Testes da aba Templates depois que "Categorias de card" virou modal.
 *
 * O que se protege aqui é o motivo da mudança: a tela principal não pode
 * voltar a listar categorias, e nada do que a seção fazia pode ter se
 * perdido no caminho (criar, editar, excluir, com a regra do 409).
 */
vi.mock("./actions", () => ({
  listTemplatesAction: vi.fn(),
  listTemplateCategoriesAction: vi.fn(),
  getTemplateDetailAction: vi.fn(),
  createTemplateAction: vi.fn(),
  updateTemplateAction: vi.fn(),
  deleteTemplateAction: vi.fn(),
  createTemplateCardAction: vi.fn(),
  updateTemplateCardAction: vi.fn(),
  deleteTemplateCardAction: vi.fn(),
  createTemplateColumnAction: vi.fn(),
  updateTemplateColumnAction: vi.fn(),
  deleteTemplateColumnAction: vi.fn(),
  moveTemplateColumnAction: vi.fn(),
  createTemplateCategoryAction: vi.fn(),
  updateTemplateCategoryAction: vi.fn(),
  deleteTemplateCategoryAction: vi.fn(),
}));

const CATEGORIAS: TemplateCategory[] = [
  { id: 1, name: "Financeiro", color: "#1f4e9c", sort_order: 0 },
  { id: 2, name: "Operacional", color: "#1d5b3a", sort_order: 1 },
  { id: 3, name: "Compliance", color: "#8c1d1d", sort_order: 3 },
];

const TEMPLATES: TemplateListItem[] = [
  { id: 7, name: "ISO 27001", description: null, is_default: true, card_count: 12 },
];

function renderizar(categories = CATEGORIAS) {
  return render(
    <TemplatesClient
      initialTemplates={TEMPLATES}
      initialSelectedTemplateId={null}
      initialDetail={null}
      initialCategories={categories}
    />,
  );
}

async function abrirCategorias(user: ReturnType<typeof userEvent.setup>) {
  await user.click(
    screen.getByRole("button", { name: /Categorias de card/ }),
  );
  return screen.getByRole("dialog");
}

describe("TemplatesClient — categorias de card", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    // `refreshCategories` relê a lista depois de cada mutação; sem um
    // valor no mock o componente receberia `undefined` e quebraria no
    // `categories.length` do botão.
    const { listTemplateCategoriesAction } = await import("./actions");
    vi.mocked(listTemplateCategoriesAction).mockResolvedValue(CATEGORIAS);
  });

  it("não lista as categorias na tela principal, só a contagem no botão", () => {
    renderizar();

    expect(
      screen.getByRole("button", { name: "Categorias de card · 3" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Financeiro")).not.toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("abre o modal com todas as categorias e suas ordens", async () => {
    const user = userEvent.setup();
    renderizar();

    const dialogo = await abrirCategorias(user);

    for (const categoria of CATEGORIAS) {
      expect(within(dialogo).getByText(categoria.name)).toBeInTheDocument();
    }
    expect(within(dialogo).getByText("ordem 3")).toBeInTheDocument();
    expect(within(dialogo).getByText("3 categorias")).toBeInTheDocument();
  });

  it("abre os campos de edição na linha da categoria escolhida", async () => {
    const user = userEvent.setup();
    renderizar();
    const dialogo = await abrirCategorias(user);

    // A 3ª categoria: antes o formulário ficava no topo, longe dela.
    const linhas = within(dialogo).getAllByRole("listitem");
    await user.click(
      within(linhas[2]).getByRole("button", { name: "Editar" }),
    );

    const linhaEmEdicao = within(dialogo).getAllByRole("listitem")[2];
    expect(within(linhaEmEdicao).getByText(/Editando/)).toBeInTheDocument();
    expect(
      within(linhaEmEdicao).getByLabelText("Nome da categoria"),
    ).toHaveValue("Compliance");
    expect(within(linhaEmEdicao).getByLabelText("Ordem da categoria")).toHaveValue(
      3,
    );
  });

  it("exige confirmação na linha antes de excluir", async () => {
    const user = userEvent.setup();
    const { deleteTemplateCategoryAction } = await import("./actions");
    vi.mocked(deleteTemplateCategoryAction).mockResolvedValue({ ok: true });

    renderizar();
    const dialogo = await abrirCategorias(user);

    await user.click(within(dialogo).getAllByRole("button", { name: "Excluir" })[0]);
    expect(deleteTemplateCategoryAction).not.toHaveBeenCalled();
    expect(
      within(dialogo).getByText(/Excluir a categoria “Financeiro”/),
    ).toBeInTheDocument();
    // A regra do 409 continua sendo dita antes da confirmação.
    expect(
      within(dialogo).getByText(/recusada enquanto existir card/),
    ).toBeInTheDocument();

    await user.click(
      within(dialogo).getByRole("button", {
        name: "Confirmar exclusão de Financeiro",
      }),
    );
    expect(deleteTemplateCategoryAction).toHaveBeenCalledWith(1);
  });

  it("abre o formulário de criação recolhido, sob demanda", async () => {
    const user = userEvent.setup();
    renderizar();
    const dialogo = await abrirCategorias(user);

    expect(
      within(dialogo).queryByLabelText("Nome da categoria"),
    ).not.toBeInTheDocument();

    await user.click(
      within(dialogo).getByRole("button", { name: "+ Nova categoria" }),
    );
    expect(
      within(dialogo).getByLabelText("Nome da categoria"),
    ).toBeInTheDocument();
  });

  it("fecha no Escape", async () => {
    const user = userEvent.setup();
    renderizar();
    await abrirCategorias(user);

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("mostra o vazio quando não há categoria nenhuma", async () => {
    const user = userEvent.setup();
    renderizar([]);

    const dialogo = await abrirCategorias(user);
    expect(
      within(dialogo).getByText("Nenhuma categoria cadastrada ainda."),
    ).toBeInTheDocument();
  });
});
