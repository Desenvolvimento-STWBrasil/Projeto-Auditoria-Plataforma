import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-backend");
vi.mock("@/lib/session");

import {
  backendMock,
  prepararSessao,
  requireClientMock,
  TOKEN,
  ultimaChamada,
} from "@/test/helpers/action-mocks";
import {
  listMessagesAction,
  listMySubUserRequestsAction,
  requestSubUserAction,
  sendMessageAction,
  uploadEvidenceAction,
} from "./actions";

beforeEach(prepararSessao);

/**
 * Server Actions do cliente auditado. Todas passam por `requireClient()`
 * — a guarda que impede um admin de agir pela área do cliente e
 * vice-versa.
 */
describe("requestSubUserAction", () => {
  it("envia a solicitação ao endpoint de sub-usuários", async () => {
    backendMock.mockResolvedValue({ id: 1 });

    const resultado = await requestSubUserAction({
      requested_full_name: "João Souza",
      request_email: "joao@cliente.com",
    });

    expect(requireClientMock).toHaveBeenCalled();
    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/sub-users/requests");
    expect(opcoes.method).toBe("POST");
    expect(opcoes.token).toBe(TOKEN);
    expect(opcoes.body).toEqual({
      requested_full_name: "João Souza",
      request_email: "joao@cliente.com",
    });
    expect(resultado).toEqual({ ok: true });
  });

  it("converte erro do backend em resultado tratável, sem lançar", async () => {
    backendMock.mockRejectedValue(
      new Error("Apenas usuário principal pode solicitar sub-user"),
    );

    await expect(
      requestSubUserAction({
        requested_full_name: "João",
        request_email: "joao@cliente.com",
      }),
    ).resolves.toEqual({
      ok: false,
      message: "Apenas usuário principal pode solicitar sub-user",
    });
  });
});

describe("listMySubUserRequestsAction", () => {
  it("lê o histórico do próprio cliente", async () => {
    backendMock.mockResolvedValue([{ id: 1, status: "REJECTED" }]);

    const requisicoes = await listMySubUserRequestsAction();

    expect(requireClientMock).toHaveBeenCalled();
    expect(ultimaChamada()[0]).toBe("/api/v1/sub-users/requests/me");
    expect(requisicoes).toHaveLength(1);
  });
});

describe("uploadEvidenceAction", () => {
  it("envia o FormData ao controle correto e devolve o nome do arquivo", async () => {
    backendMock.mockResolvedValue({
      id: 7,
      file_path: "uploads/abc.pdf",
      filename: "politica.pdf",
    });

    const formData = new FormData();
    formData.append("file", new File(["conteudo"], "politica.pdf"));

    const resultado = await uploadEvidenceAction(42, formData);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/client/controls/42/evidences");
    expect(opcoes.method).toBe("POST");
    expect(opcoes.body).toBeInstanceOf(FormData);
    expect(resultado).toEqual({ ok: true, fileName: "politica.pdf" });
  });

  it("propaga a mensagem do backend em extensão recusada", async () => {
    backendMock.mockRejectedValue(
      new Error("Tipo de arquivo não permitido: .exe"),
    );

    await expect(
      uploadEvidenceAction(42, new FormData()),
    ).resolves.toEqual({
      ok: false,
      message: "Tipo de arquivo não permitido: .exe",
    });
  });

  it("propaga a mensagem do backend em arquivo grande demais", async () => {
    backendMock.mockRejectedValue(new Error("Arquivo maior que 10MB"));

    const resultado = await uploadEvidenceAction(42, new FormData());

    expect(resultado).toEqual({ ok: false, message: "Arquivo maior que 10MB" });
  });
});

describe("listMessagesAction / sendMessageAction", () => {
  it("lista as mensagens do controle", async () => {
    backendMock.mockResolvedValue([{ id: 1, content: "Olá" }]);

    await listMessagesAction(42);

    expect(ultimaChamada()[0]).toBe("/api/v1/client/controls/42/messages");
  });

  it("envia a mensagem com o conteúdo no corpo", async () => {
    backendMock.mockResolvedValue({
      id: 2,
      content: "Qual evidência?",
      created_at: "2026-08-26T00:00:00Z",
    });

    const resultado = await sendMessageAction(42, "Qual evidência?");

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/client/controls/42/messages");
    expect(opcoes.method).toBe("POST");
    expect(opcoes.body).toEqual({ content: "Qual evidência?" });
    expect(resultado).toEqual({ ok: true, content: "Qual evidência?" });
  });

  it("devolve falha tratável quando o envio quebra", async () => {
    backendMock.mockRejectedValue(new Error("Sem acesso"));

    await expect(sendMessageAction(42, "x")).resolves.toEqual({
      ok: false,
      message: "Sem acesso",
    });
  });
});
