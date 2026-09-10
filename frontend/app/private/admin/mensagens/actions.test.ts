import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-backend");
vi.mock("@/lib/session");

import {
  backendMock,
  prepararSessao,
  requireAdminMock,
  rotasChamadas,
  ultimaChamada,
} from "@/test/helpers/action-mocks";
import {
  listCompaniesWithUnreadAction,
  listCompanyMessagesAction,
  markCompanyMessagesAsReadAction,
  sendCompanyMessageAction,
} from "./actions";

beforeEach(prepararSessao);

/**
 * Canal geral admin↔cliente por empresa (L.1). Note que `listCompanies
 * WithUnreadAction` faz **N+1 por design** — uma chamada de contagem por
 * empresa. É aceitável hoje (poucas empresas) e está registrado; o teste
 * fixa o comportamento para que a mudança seja deliberada.
 */
describe("listCompaniesWithUnreadAction", () => {
  it("busca a contagem de não lidas de cada empresa", async () => {
    backendMock
      .mockResolvedValueOnce([
        { id: 1, name: "Alfa" },
        { id: 2, name: "Beta" },
      ])
      .mockResolvedValueOnce({ unread_count: 3 })
      .mockResolvedValueOnce({ unread_count: 0 });

    const empresas = await listCompaniesWithUnreadAction();

    expect(rotasChamadas()).toEqual([
      "/api/v1/onboarding/companies",
      "/api/v1/companies/1/messages/unread-count",
      "/api/v1/companies/2/messages/unread-count",
    ]);
    expect(empresas).toEqual([
      { id: 1, name: "Alfa", unread_count: 3 },
      { id: 2, name: "Beta", unread_count: 0 },
    ]);
  });

  it("devolve lista vazia sem chamar contagem alguma", async () => {
    backendMock.mockResolvedValueOnce([]);

    await expect(listCompaniesWithUnreadAction()).resolves.toEqual([]);
    expect(rotasChamadas()).toEqual(["/api/v1/onboarding/companies"]);
  });
});

describe("mensagens por empresa", () => {
  it("lista pela rota da empresa", async () => {
    backendMock.mockResolvedValue([]);

    await listCompanyMessagesAction(4);

    expect(requireAdminMock).toHaveBeenCalled();
    expect(ultimaChamada()[0]).toBe("/api/v1/companies/4/messages");
  });

  it("marca como lidas com PATCH", async () => {
    backendMock.mockResolvedValue({ marked_as_read: 2 });

    await markCompanyMessagesAsReadAction(4);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/companies/4/messages/read");
    expect(opcoes.method).toBe("PATCH");
  });

  it("envia mensagem com o conteúdo no corpo", async () => {
    backendMock.mockResolvedValue({ id: 8, content: "Bom dia" });

    const resultado = await sendCompanyMessageAction(4, "Bom dia");

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/companies/4/messages");
    expect(opcoes.method).toBe("POST");
    expect(opcoes.body).toEqual({ content: "Bom dia" });
    expect(resultado).toEqual({ ok: true, created: { id: 8, content: "Bom dia" } });
  });

  it("devolve falha tratável quando o envio quebra", async () => {
    backendMock.mockRejectedValue(new Error("Empresa não encontrada ou sem acesso"));

    const resultado = await sendCompanyMessageAction(4, "x");

    expect(resultado).toEqual({
      ok: false,
      message: "Empresa não encontrada ou sem acesso",
    });
  });
});
