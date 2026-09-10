import { describe, expect, it } from "vitest";

import { getSafeRedirectPath } from "./safe-redirect";

/**
 * `getSafeRedirectPath` é a proteção anti-open-redirect do login: o
 * parâmetro `?redirect=` vem da URL, ou seja, do atacante.
 *
 * É a menor função do frontend e uma das poucas onde um descuido tem
 * consequência direta de segurança — por isso abre a suíte.
 */
describe("getSafeRedirectPath", () => {
  const FALLBACK = "/private/client";

  it("aceita um caminho interno absoluto", () => {
    expect(getSafeRedirectPath("/private/admin/empresas", FALLBACK)).toBe(
      "/private/admin/empresas",
    );
  });

  it("preserva query string e fragmento do caminho interno", () => {
    expect(
      getSafeRedirectPath("/private/admin/mensagens?empresa=3", FALLBACK),
    ).toBe("/private/admin/mensagens?empresa=3");
  });

  it("cai no fallback quando o valor é nulo", () => {
    expect(getSafeRedirectPath(null, FALLBACK)).toBe(FALLBACK);
  });

  it("cai no fallback quando o valor é vazio", () => {
    expect(getSafeRedirectPath("", FALLBACK)).toBe(FALLBACK);
  });

  it.each([
    ["//evil.com", "protocol-relative"],
    ["///evil.com", "protocol-relative com três barras"],
    ["https://evil.com", "URL absoluta"],
    ["http://evil.com/path", "URL absoluta com caminho"],
    ["javascript://evil", "esquema javascript"],
    ["private/admin", "caminho relativo sem barra inicial"],
  ])("recusa %s (%s)", (entrada) => {
    expect(getSafeRedirectPath(entrada, FALLBACK)).toBe(FALLBACK);
  });
});
