import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-backend");
vi.mock("@/lib/session");

import {
  backendMock,
  prepararSessao,
  requireClientMock,
  ultimaChamada,
} from "@/test/helpers/action-mocks";
import {
  listMyCompanyMessagesAction,
  markMyCompanyMessagesAsReadAction,
  sendMyCompanyMessageAction,
} from "./actions";

beforeEach(prepararSessao);

/**
 * O mesmo canal geral, do lado do cliente. As rotas são idênticas às do
 * admin — a diferença é a guarda de papel (`requireClient`) e o filtro
 * de "outro lado" que o backend aplica ao marcar como lido.
 */
describe("mensagens gerais do cliente", () => {
  it("lista pela rota da própria empresa", async () => {
    backendMock.mockResolvedValue([]);

    await listMyCompanyMessagesAction(4);

    expect(requireClientMock).toHaveBeenCalled();
    expect(ultimaChamada()[0]).toBe("/api/v1/companies/4/messages");
  });

  it("marca como lidas com PATCH", async () => {
    backendMock.mockResolvedValue({ marked_as_read: 1 });

    await markMyCompanyMessagesAsReadAction(4);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/companies/4/messages/read");
    expect(opcoes.method).toBe("PATCH");
  });

  it("envia mensagem e devolve a criada", async () => {
    backendMock.mockResolvedValue({ id: 9, content: "Dúvida" });

    const resultado = await sendMyCompanyMessageAction(4, "Dúvida");

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/companies/4/messages");
    expect(opcoes.body).toEqual({ content: "Dúvida" });
    expect(resultado).toEqual({ ok: true, created: { id: 9, content: "Dúvida" } });
  });

  it("converte erro em resultado tratável", async () => {
    backendMock.mockRejectedValue(new Error("Sem acesso"));

    await expect(sendMyCompanyMessageAction(4, "x")).resolves.toEqual({
      ok: false,
      message: "Sem acesso",
    });
  });
});
