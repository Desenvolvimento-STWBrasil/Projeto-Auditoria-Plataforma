import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-backend");
vi.mock("@/lib/session");
vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));

import { revalidatePath } from "next/cache";

import {
  backendMock,
  prepararSessao,
  requireAdminMock,
  TOKEN,
  ultimaChamada,
} from "@/test/helpers/action-mocks";
import {
  createCompanyAction,
  deleteCompanyAction,
  getCompanyAdminDetailAction,
  listCompaniesAdminAction,
  updateCompanyAction,
} from "./actions";

beforeEach(prepararSessao);

const ENTRADA_EMPRESA = {
  full_name: "Maria Silva",
  company_name: "Construtora Alfa",
  email: "maria@alfa.com",
  phone: null,
  template_id: 1,
  manual_dashboard: false,
};

describe("listCompaniesAdminAction", () => {
  it("traduz página em skip e envia a busca", async () => {
    backendMock.mockResolvedValue({ total: 0, skip: 0, limit: 10, items: [] });

    await listCompaniesAdminAction(2, "Alfa");

    expect(requireAdminMock).toHaveBeenCalled();
    const [rota] = ultimaChamada();
    expect(rota.startsWith("/api/v1/admin/companies?")).toBe(true);
    const query = new URLSearchParams(rota.split("?")[1]);
    expect(query.get("search")).toBe("Alfa");
    // page 2 com PAGE_SIZE 10 -> skip 20
    expect(Number(query.get("skip"))).toBe(2 * Number(query.get("limit")));
  });

  it("omite o parâmetro search quando a busca está vazia", async () => {
    backendMock.mockResolvedValue({ total: 0, skip: 0, limit: 10, items: [] });

    await listCompaniesAdminAction(0, "   ");

    const query = new URLSearchParams(ultimaChamada()[0].split("?")[1]);
    expect(query.has("search")).toBe(false);
    expect(query.get("skip")).toBe("0");
  });
});

describe("getCompanyAdminDetailAction", () => {
  it("lê o detalhe pela rota do id", async () => {
    backendMock.mockResolvedValue({ id: 4, name: "Alfa" });

    await getCompanyAdminDetailAction(4);

    expect(ultimaChamada()[0]).toBe("/api/v1/admin/companies/4");
  });
});

describe("createCompanyAction — B-A29", () => {
  it("devolve a senha temporária quando o e-mail não foi entregue", async () => {
    backendMock.mockResolvedValue({
      user_id: 2,
      company_id: 3,
      dashboard_id: 4,
      dashboard_cards_created: 9,
      email_delivered: false,
      temporary_password: "Xk8!aB2mQz1p",
    });

    const resultado = await createCompanyAction(ENTRADA_EMPRESA);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/onboarding/principal-user");
    expect(opcoes.method).toBe("POST");
    expect(opcoes.token).toBe(TOKEN);
    expect(resultado).toEqual({
      ok: true,
      emailDelivered: false,
      temporaryPassword: "Xk8!aB2mQz1p",
      email: "maria@alfa.com",
    });
    expect(revalidatePath).toHaveBeenCalledWith("/private/admin/empresas");
  });

  it("não trafega a senha quando o e-mail foi entregue", async () => {
    backendMock.mockResolvedValue({
      user_id: 2,
      company_id: 3,
      dashboard_id: 4,
      dashboard_cards_created: 9,
      email_delivered: true,
      temporary_password: null,
    });

    const resultado = await createCompanyAction(ENTRADA_EMPRESA);

    expect(resultado).toEqual({
      ok: true,
      emailDelivered: true,
      temporaryPassword: null,
      email: "maria@alfa.com",
    });
  });

  it("devolve o 409 de e-mail duplicado como mensagem tratável", async () => {
    backendMock.mockRejectedValue(new Error("E-mail já cadastrado"));

    const resultado = await createCompanyAction(ENTRADA_EMPRESA);

    expect(resultado).toEqual({ ok: false, message: "E-mail já cadastrado" });
    expect(revalidatePath).not.toHaveBeenCalled();
  });
});

describe("updateCompanyAction", () => {
  it("usa PATCH e revalida a listagem", async () => {
    backendMock.mockResolvedValue({ id: 4, name: "Alfa Ltda" });

    const resultado = await updateCompanyAction(4, {
      name: "Alfa Ltda",
      email: "contato@alfa.com",
      phone: "11999999999",
    });

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/companies/4");
    expect(opcoes.method).toBe("PATCH");
    expect(revalidatePath).toHaveBeenCalledWith("/private/admin/empresas");
    expect(resultado.ok).toBe(true);
  });

  it("propaga o 409 de nome duplicado", async () => {
    backendMock.mockRejectedValue(
      new Error("Já existe outra empresa com esse nome ou e-mail"),
    );

    const resultado = await updateCompanyAction(4, {
      name: "Alfa",
      email: "a@a.com",
      phone: null,
    });

    expect(resultado).toEqual({
      ok: false,
      message: "Já existe outra empresa com esse nome ou e-mail",
    });
  });
});

describe("deleteCompanyAction", () => {
  it("usa DELETE e revalida a listagem", async () => {
    backendMock.mockResolvedValue({
      company_id: 4,
      company_name: "Alfa",
      deleted_evidence_files: 3,
    });

    const resultado = await deleteCompanyAction(4);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/companies/4");
    expect(opcoes.method).toBe("DELETE");
    expect(revalidatePath).toHaveBeenCalledWith("/private/admin/empresas");
    expect(resultado.ok).toBe(true);
  });

  it("propaga o 409 de exclusão com vínculo não previsto", async () => {
    backendMock.mockRejectedValue(
      new Error("Não foi possível excluir a empresa: existem registros vinculados"),
    );

    const resultado = await deleteCompanyAction(4);

    expect(resultado.ok).toBe(false);
  });
});
