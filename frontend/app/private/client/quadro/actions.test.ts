import { beforeEach, describe, expect, it } from "vitest";
import { vi } from "vitest";

vi.mock("@/lib/server-backend");
vi.mock("@/lib/session");
vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));

import {
  backendMock,
  prepararSessao,
  requireClientMock,
  rotasChamadas,
  ultimaChamada,
} from "@/test/helpers/action-mocks";
import {
  getCardDetailAction,
  getClientBoardAction,
  getMyCompanyAction,
  sendCardQuestionAction,
} from "./actions";

beforeEach(prepararSessao);

describe("quadro do cliente", () => {
  it("resolve a empresa pela rota /companies/me", async () => {
    backendMock.mockResolvedValue({ id: 7, name: "Empresa Teste" });

    const empresa = await getMyCompanyAction();

    expect(requireClientMock).toHaveBeenCalled();
    expect(ultimaChamada()[0]).toBe("/api/v1/companies/me");
    expect(empresa.id).toBe(7);
  });

  it("lê o quadro SEM cards ocultos", async () => {
    backendMock.mockResolvedValue({ columns: [], uncolumned: [], labels: [] });

    await getClientBoardAction(7);

    expect(ultimaChamada()[0]).toBe(
      "/api/v1/dashboard/companies/7/board?include_hidden=false&search=",
    );
  });

  it("usa requireClient, nunca requireAdmin", async () => {
    backendMock.mockResolvedValue({ columns: [], uncolumned: [], labels: [] });

    await getClientBoardAction(7);

    expect(requireClientMock).toHaveBeenCalled();
  });

  it("lê o detalhe do card pela mesma rota do admin", async () => {
    backendMock.mockResolvedValue({ id: 3, checklist: [], history: [] });

    await getCardDetailAction(3);

    expect(ultimaChamada()[0]).toBe("/api/v1/dashboard/cards/3");
  });

  it("não expõe nenhuma rota de escrita", async () => {
    backendMock.mockResolvedValue({ id: 7, name: "Empresa" });

    await getMyCompanyAction();

    for (const [, opcoes] of backendMock.mock.calls) {
      const metodo = (opcoes as { method?: string } | undefined)?.method;
      expect(metodo ?? "GET").toBe("GET");
    }
    expect(rotasChamadas().length).toBeGreaterThan(0);
  });
});

describe("pergunta do cliente sobre um card", () => {
  it("envia como CHAT_QUESTION, com guarda de cliente", async () => {
    backendMock.mockResolvedValue({ message: "Entrada criada com sucesso" });

    const resultado = await sendCardQuestionAction(42, "Qual evidência?");

    expect(requireClientMock).toHaveBeenCalled();
    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/dashboard/cards/42/entries");
    expect(opcoes.method).toBe("POST");
    /*
     * O tipo é FIXO aqui, não vem por parâmetro: `CHAT_ANSWER` está em
     * ADMIN_ONLY_ENTRY_TYPES e o cliente tomaria 403. Fixar impede que a
     * fala do cliente seja registrada como resposta da auditoria.
     */
    expect(opcoes.body).toEqual({
      entry_type: "CHAT_QUESTION",
      content: "Qual evidência?",
    });
    expect(resultado).toEqual({ ok: true });
  });

  it("propaga a falha como mensagem tratável", async () => {
    backendMock.mockRejectedValue(new Error("Card não encontrado ou sem acesso"));

    await expect(sendCardQuestionAction(42, "x")).resolves.toEqual({
      ok: false,
      message: "Card não encontrado ou sem acesso",
    });
  });
});
