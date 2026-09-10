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
  listCompanyAuditsAction,
} from "./actions";

beforeEach(prepararSessao);

/**
 * Filtro de auditorias por empresa (O.2 / F65). `Audit` não tem
 * `company_id` — o backend resolve os membros da empresa a partir do
 * usuário principal. O que se fixa aqui é o parâmetro que a tela envia.
 */
describe("listCompanyAuditsAction", () => {
  it("filtra por company_id na query", async () => {
    backendMock.mockResolvedValue({ total: 0, skip: 0, limit: 100, items: [] });

    await listCompanyAuditsAction(4);

    expect(requireAdminMock).toHaveBeenCalled();
    const [rota] = ultimaChamada();
    expect(rota.startsWith("/api/v1/admin/audits?")).toBe(true);
    const query = new URLSearchParams(rota.split("?")[1]);
    expect(query.get("company_id")).toBe("4");
  });
});
