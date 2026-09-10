import { vi } from "vitest";

import { callBackend } from "@/lib/server-backend";
import {
  getAccessToken,
  requireAdmin,
  requireClient,
  requireUser,
} from "@/lib/session";

/**
 * Utilitários para os testes de Server Action.
 *
 * Toda Server Action deste projeto segue a mesma forma:
 *
 *     await requireAdmin() | requireClient()     ← guarda de papel
 *     const token = await getAccessToken()       ← credencial
 *     return callBackend(rota, { method, token, body })
 *
 * O que se testa aqui é **o contrato com o backend** — qual rota, qual
 * método, qual corpo — e o tratamento de erro. O que a API responde de
 * fato já é coberto pelos 258 testes do backend; duplicar aquilo aqui
 * seria testar o mock.
 *
 * Cada arquivo de teste registra os módulos mockados no próprio topo:
 *
 *     vi.mock("@/lib/server-backend");
 *     vi.mock("@/lib/session");
 *     vi.mock("next/cache");
 *
 * O automock do Vitest substitui todos os exports por spies. As
 * declarações precisam ficar no arquivo de teste porque `vi.mock` sobe
 * para o topo do módulo onde é escrito — de um helper importado, não
 * teria efeito.
 */

export const TOKEN = "token-de-teste";

export const backendMock = vi.mocked(callBackend);
export const requireAdminMock = vi.mocked(requireAdmin);
export const requireClientMock = vi.mocked(requireClient);
export const requireUserMock = vi.mocked(requireUser);
export const getAccessTokenMock = vi.mocked(getAccessToken);

/** Estado limpo entre testes, com sessão válida por padrão. */
export function prepararSessao(): void {
  backendMock.mockReset();
  requireAdminMock.mockReset().mockResolvedValue({ id: 1, role: "admin" });
  requireClientMock.mockReset().mockResolvedValue({ id: 9, role: "user" });
  requireUserMock.mockReset().mockResolvedValue({ id: 9, role: "user" });
  getAccessTokenMock.mockReset().mockResolvedValue(TOKEN);
}

/** Última chamada a `callBackend`, como `[rota, opções]`. */
export function ultimaChamada(): [string, Record<string, unknown>] {
  const chamadas = backendMock.mock.calls;
  if (chamadas.length === 0) {
    throw new Error("callBackend não foi chamado");
  }
  const ultima = chamadas[chamadas.length - 1];
  return [ultima[0] as string, (ultima[1] ?? {}) as Record<string, unknown>];
}

/** Todas as rotas chamadas, na ordem — útil para ações que fazem várias. */
export function rotasChamadas(): string[] {
  return backendMock.mock.calls.map((c) => c[0] as string);
}
