import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-backend");
vi.mock("@/lib/session");
vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));

import { revalidatePath } from "next/cache";

import {
  backendMock,
  prepararSessao,
  requireAdminMock,
  rotasChamadas,
  TOKEN,
  ultimaChamada,
} from "@/test/helpers/action-mocks";
import {
  approveSubUserRequestAction,
  createCardEntryAction,
  deleteChecklistItemAction,
  getAdminUnreadCountsAction,
  getCardDetailAction,
  getDashboardStatusSummaryAction,
  rejectSubUserRequestAction,
  toggleChecklistItemAction,
  updateCardStatusAction,
} from "./actions";

beforeEach(prepararSessao);

describe("aprovação e recusa de sub-usuário", () => {
  it("aprova pela rota certa e revalida a home", async () => {
    backendMock.mockResolvedValue({ request_id: 1, sub_user_id: 2 });

    const resultado = await approveSubUserRequestAction(1);

    expect(requireAdminMock).toHaveBeenCalled();
    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/sub-users/requests/1/approve");
    expect(opcoes.method).toBe("POST");
    expect(opcoes.token).toBe(TOKEN);
    expect(revalidatePath).toHaveBeenCalledWith("/private/admin");
    expect(resultado).toEqual({ ok: true });
  });

  it("recusa pela rota certa", async () => {
    backendMock.mockResolvedValue({ id: 1, status: "REJECTED" });

    await rejectSubUserRequestAction(7);

    expect(ultimaChamada()[0]).toBe("/api/v1/sub-users/requests/7/reject");
  });

  it("não revalida quando a aprovação falha", async () => {
    backendMock.mockRejectedValue(new Error("Solicitação já processada"));

    const resultado = await approveSubUserRequestAction(1);

    expect(resultado).toEqual({
      ok: false,
      message: "Solicitação já processada",
    });
    expect(revalidatePath).not.toHaveBeenCalled();
  });
});

describe("getAdminUnreadCountsAction", () => {
  it("agrega os dois contadores independentes", async () => {
    backendMock
      .mockResolvedValueOnce({ unread_count: 3 })
      .mockResolvedValueOnce({ unread_count: 5 });

    const contagens = await getAdminUnreadCountsAction();

    expect(rotasChamadas()).toEqual([
      "/api/v1/admin/messages/unread-count",
      "/api/v1/companies/unread-count",
    ]);
    expect(contagens).toEqual({ auditorias: 3, mensagens: 5 });
  });

  it("degrada para zero em vez de quebrar o cabeçalho", async () => {
    // Este contador alimenta o menu superior, presente em TODA tela
    // privada. Deixar a exceção subir derrubaria a navegação inteira
    // por causa de um badge.
    backendMock.mockRejectedValue(new Error("backend fora do ar"));

    await expect(getAdminUnreadCountsAction()).resolves.toEqual({
      auditorias: 0,
      mensagens: 0,
    });
  });
});

describe("runtime do dashboard", () => {
  it("lê o detalhe do card", async () => {
    backendMock.mockResolvedValue({ id: 3, checklist: [], history: [], chat: [] });

    await getCardDetailAction(3);

    expect(ultimaChamada()[0]).toBe("/api/v1/dashboard/cards/3");
  });

  it("atualiza o status do card com PATCH e devolve o novo status", async () => {
    backendMock.mockResolvedValue({ status: "CONFORME" });

    const resultado = await updateCardStatusAction(3, "CONFORME");

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/dashboard/cards/3/status");
    expect(opcoes.method).toBe("PATCH");
    expect(opcoes.body).toEqual({ status: "CONFORME" });
    expect(resultado).toEqual({ ok: true, status: "CONFORME" });
  });

  it("propaga o 403 de B-A23 como mensagem tratável", async () => {
    backendMock.mockRejectedValue(
      new Error("Acesso restrito a administradores"),
    );

    await expect(updateCardStatusAction(3, "CONFORME")).resolves.toEqual({
      ok: false,
      message: "Acesso restrito a administradores",
    });
  });

  it("alterna item de checklist e devolve o estado novo", async () => {
    backendMock.mockResolvedValue({ ok: true, done: true });

    const resultado = await toggleChecklistItemAction(11);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/dashboard/checklist-items/11/toggle");
    expect(opcoes.method).toBe("PATCH");
    expect(resultado).toEqual({ ok: true, done: true });
  });

  it("busca os KPIs pela rota agregada, não card a card", async () => {
    // O.1 substituiu a soma no navegador por uma query agregada. Se
    // alguém voltar a baixar todos os cards, este teste denuncia.
    backendMock.mockResolvedValue({
      em_analise: 4,
      parcial: 1,
      conforme: 9,
      naoconforme: 2,
    });

    const resumo = await getDashboardStatusSummaryAction();

    expect(ultimaChamada()[0]).toBe("/api/v1/dashboard/status-summary");
    expect(resumo.conforme).toBe(9);
  });
});

describe("escrita no card (checklist, histórico e conversa)", () => {
  /*
   * `POST /cards/{id}/entries` existia desde D.6 e nunca teve consumidor:
   * a interface lia as três coleções e não escrevia em nenhuma. Estes
   * testes fixam o contrato dos quatro tipos de entrada, porque é o
   * `entry_type` que decide a permissão no backend (B-A23) — mandar o
   * tipo errado é um 403 ou, pior, uma mensagem do auditor aparecendo
   * como pergunta do cliente.
   */
  it.each([
    ["CHECKLIST", "Evidência documental apresentada"],
    ["HISTORY", "Revisado com o cliente"],
    ["CHAT_QUESTION", "Qual evidência devo enviar?"],
    ["CHAT_ANSWER", "O relatório de varredura."],
  ] as const)("cria entrada do tipo %s", async (tipo, conteudo) => {
    backendMock.mockResolvedValue({ message: "Entrada criada com sucesso" });

    const resultado = await createCardEntryAction(42, tipo, conteudo);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/dashboard/cards/42/entries");
    expect(opcoes.method).toBe("POST");
    expect(opcoes.body).toEqual({ entry_type: tipo, content: conteudo });
    expect(opcoes.token).toBe(TOKEN);
    expect(resultado).toEqual({ ok: true });
  });

  it("propaga a recusa do backend como mensagem tratável", async () => {
    backendMock.mockRejectedValue(
      new Error("Apenas a equipe de auditoria pode registrar esse tipo de entrada"),
    );

    await expect(
      createCardEntryAction(42, "CHECKLIST", "x"),
    ).resolves.toEqual({
      ok: false,
      message:
        "Apenas a equipe de auditoria pode registrar esse tipo de entrada",
    });
  });

  it("remove item de checklist com DELETE", async () => {
    backendMock.mockResolvedValue(undefined);

    const resultado = await deleteChecklistItemAction(11);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/dashboard/checklist-items/11");
    expect(opcoes.method).toBe("DELETE");
    expect(resultado).toEqual({ ok: true });
  });

  it("propaga falha na remoção do item", async () => {
    backendMock.mockRejectedValue(new Error("Item não encontrado"));

    await expect(deleteChecklistItemAction(11)).resolves.toEqual({
      ok: false,
      message: "Item não encontrado",
    });
  });
});
