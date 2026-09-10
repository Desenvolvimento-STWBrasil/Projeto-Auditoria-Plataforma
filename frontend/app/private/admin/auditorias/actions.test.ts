import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-backend");
vi.mock("@/lib/session");

import {
  backendMock,
  prepararSessao,
  requireAdminMock,
  ultimaChamada,
} from "@/test/helpers/action-mocks";
import {
  getAuditDetailAction,
  listAuditsAction,
  markControlMessagesReadAction,
  sendControlMessageAction,
  updateAuditStatusAction,
  updateControlStatusAction,
} from "./actions";

beforeEach(prepararSessao);

describe("listagem e detalhe de auditoria", () => {
  it("lista com paginação fixa", async () => {
    backendMock.mockResolvedValue({ total: 0, skip: 0, limit: 50, items: [] });

    await listAuditsAction();

    expect(requireAdminMock).toHaveBeenCalled();
    expect(ultimaChamada()[0]).toBe("/api/v1/admin/audits?skip=0&limit=50");
  });

  it("lê o detalhe pela rota do id", async () => {
    backendMock.mockResolvedValue({ id: 5, controls: [] });

    await getAuditDetailAction(5);

    expect(ultimaChamada()[0]).toBe("/api/v1/admin/audits/5");
  });
});

describe("encerramento de auditoria (L.2)", () => {
  it("usa PATCH com o status no corpo", async () => {
    backendMock.mockResolvedValue({ id: 5, status: "CLOSED" });

    const resultado = await updateAuditStatusAction(5, "CLOSED");

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/audits/5/status");
    expect(opcoes.method).toBe("PATCH");
    expect(opcoes.body).toEqual({ status: "CLOSED" });
    expect(resultado.ok).toBe(true);
  });

  it("devolve falha tratável quando o backend recusa", async () => {
    backendMock.mockRejectedValue(new Error("Auditoria já encerrada"));

    const resultado = await updateAuditStatusAction(5, "CLOSED");

    expect(resultado).toEqual({ ok: false, message: "Auditoria já encerrada" });
  });
});

describe("status de controle e chat por controle", () => {
  it("atualiza o status do controle com PATCH", async () => {
    backendMock.mockResolvedValue({ id: 3, status: "NAOCONFORME" });

    await updateControlStatusAction(3, "NAOCONFORME");

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/audit-controls/3/status");
    expect(opcoes.method).toBe("PATCH");
    expect(opcoes.body).toEqual({ status: "NAOCONFORME" });
  });

  it("envia mensagem no chat do controle", async () => {
    backendMock.mockResolvedValue({ id: 12, content: "Faltou anexo" });

    const resultado = await sendControlMessageAction(3, "Faltou anexo");

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/audit-controls/3/messages");
    expect(opcoes.method).toBe("POST");
    expect(opcoes.body).toEqual({ content: "Faltou anexo" });
    expect(resultado.ok).toBe(true);
  });

  it("marca as mensagens do controle como lidas", async () => {
    backendMock.mockResolvedValue({ marked_as_read: 4 });

    await markControlMessagesReadAction(3);

    const [rota, opcoes] = ultimaChamada();
    expect(rota).toBe("/api/v1/admin/audit-controls/3/messages/read");
    expect(opcoes.method).toBe("PATCH");
  });
});
