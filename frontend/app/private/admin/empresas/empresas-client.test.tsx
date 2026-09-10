// @vitest-environment jsdom

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { EmpresasClient } from "./empresas-client";
import type { CompanyAdminListItem, PaginatedCompanies } from "./actions";

/**
 * Testes da listagem de empresas depois da reorganização de UI.
 *
 * O que se protege aqui são as decisões de apresentação que têm razão de
 * ser — e que uma refatoração futura desfaria sem perceber:
 *
 * - o e-mail do responsável não é repetido quando é o mesmo da empresa;
 * - os sub-usuários existem na página, recolhidos, e não sumiram;
 * - as ações destrutivas continuam alcançáveis, agora dentro do menu;
 * - vazio de busca e vazio de cadastro oferecem saídas diferentes.
 *
 * As Server Actions são mockadas: o contrato delas com o backend já é
 * coberto por `actions.test.ts`.
 */
vi.mock("./actions", () => ({
  listCompaniesAdminAction: vi.fn(),
  getCompanyAdminDetailAction: vi.fn(),
  createCompanyAction: vi.fn(),
  updateCompanyAction: vi.fn(),
  deleteCompanyAction: vi.fn(),
}));

function empresa(
  overrides: Partial<CompanyAdminListItem> = {},
): CompanyAdminListItem {
  return {
    id: 1,
    name: "Construtora Horizonte S.A.",
    email: "contato@horizonteconstrutora.com.br",
    phone: "(21) 98765-4321",
    principal_user_id: 10,
    principal_full_name: "Eduardo Lima Souza",
    principal_email: "eduardo.souza@horizonteconstrutora.com.br",
    sub_user_count: 2,
    sub_user_emails: [
      "patricia.almeida@horizonteconstrutora.com.br",
      "rodrigo.teixeira@horizonteconstrutora.com.br",
    ],
    created_at: "2026-08-07T12:00:00Z",
    ...overrides,
  };
}

function paginada(items: CompanyAdminListItem[]): PaginatedCompanies {
  return { total: items.length, skip: 0, limit: 10, items };
}

function renderizar(items: CompanyAdminListItem[]) {
  return render(
    <EmpresasClient
      initialCompanies={paginada(items)}
      initialTemplates={[{ id: 1, name: "ISO 27001" }]}
    />,
  );
}

describe("EmpresasClient", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("mostra empresa, responsável e data de cadastro", () => {
    renderizar([empresa()]);

    expect(
      screen.getAllByText("Construtora Horizonte S.A.").length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText("Eduardo Lima Souza").length).toBeGreaterThan(0);
    expect(screen.getAllByText("07/08/2026").length).toBeGreaterThan(0);
  });

  it("omite o e-mail do responsável quando é o mesmo da empresa", () => {
    const mesmoEmail = "eduardo.souza@horizonte.com.br";
    renderizar([
      empresa({ email: mesmoEmail, principal_email: mesmoEmail }),
    ]);

    // Uma ocorrência por apresentação (tabela e cards convivem no DOM,
    // alternando por CSS) — o que não pode é aparecer duas vezes DENTRO
    // da mesma linha, como acontecia antes.
    const tabela = screen.getByRole("table");
    expect(within(tabela).getAllByText(mesmoEmail)).toHaveLength(1);
  });

  it("mantém os sub-usuários na página, recolhidos até o clique", async () => {
    const user = userEvent.setup();
    renderizar([empresa()]);

    const chip = screen.getAllByText("2 sub-usuários")[0];
    expect(
      screen.queryAllByText("patricia.almeida@horizonteconstrutora.com.br")[0],
    ).not.toBeVisible();

    await user.click(chip);

    expect(
      screen.getAllByText("patricia.almeida@horizonteconstrutora.com.br")[0],
    ).toBeVisible();
  });

  it("mostra travessão para empresa sem sub-usuário", () => {
    renderizar([empresa({ sub_user_count: 0, sub_user_emails: [] })]);

    expect(screen.getAllByLabelText("Sem sub-usuários").length).toBeGreaterThan(
      0,
    );
  });

  it("abre o menu de ações com Editar e Excluir, e fecha no Escape", async () => {
    const user = userEvent.setup();
    renderizar([empresa()]);

    const gatilho = screen.getAllByRole("button", {
      name: /Mais ações para Construtora Horizonte/,
    })[0];

    await user.click(gatilho);
    expect(
      screen.getByRole("menuitem", { name: "Editar dados" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("menuitem", { name: "Excluir empresa" }),
    ).toBeInTheDocument();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("abre o diálogo de exclusão com o aviso de cascata", async () => {
    const user = userEvent.setup();
    const { getCompanyAdminDetailAction } = await import("./actions");
    vi.mocked(getCompanyAdminDetailAction).mockResolvedValue({
      ...empresa(),
      audit_count: 3,
      dashboard_card_count: 42,
      company_message_count: 7,
    });

    renderizar([empresa()]);

    await user.click(
      screen.getAllByRole("button", {
        name: /Mais ações para Construtora Horizonte/,
      })[0],
    );
    await user.click(screen.getByRole("menuitem", { name: "Excluir empresa" }));

    const dialogo = await screen.findByRole("dialog");
    expect(
      within(dialogo).getByText(/irreversível/),
    ).toBeInTheDocument();
    // O botão só libera depois do checkbox — a guarda continua de pé.
    expect(
      within(dialogo).getByRole("button", { name: "Excluir definitivamente" }),
    ).toBeDisabled();
  });

  it("oferece cadastrar quando não há nenhuma empresa", () => {
    renderizar([]);

    expect(
      screen.getByText("Nenhuma empresa cadastrada ainda."),
    ).toBeInTheDocument();
    // Um no cabeçalho, outro no estado vazio.
    expect(screen.getAllByRole("button", { name: "Nova empresa" })).toHaveLength(
      2,
    );
  });

  it("oferece limpar a busca quando o filtro não acha nada", async () => {
    const user = userEvent.setup();
    const { listCompaniesAdminAction } = await import("./actions");
    vi.mocked(listCompaniesAdminAction).mockResolvedValue(paginada([]));

    renderizar([empresa()]);

    await user.type(screen.getByLabelText("Buscar empresa"), "inexistente");

    // O texto do vazio só chega depois do debounce de 300 ms; esperar
    // por ele (e não pelo botão) evita casar com o "×" do campo.
    expect(
      await screen.findByText(/Nenhuma empresa corresponde a/),
    ).toBeInTheDocument();
    const limpar = screen.getByRole("button", { name: "Limpar busca" });

    vi.mocked(listCompaniesAdminAction).mockResolvedValue(
      paginada([empresa()]),
    );
    await user.click(limpar);

    expect(
      await screen.findAllByText("Construtora Horizonte S.A."),
    ).not.toHaveLength(0);
  });
});
