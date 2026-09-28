import { afterEach, describe, expect, it, vi } from "vitest";
import { isSecureCookie } from "./cookie-security";

describe("isSecureCookie", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("marca Secure quando o ambiente é HTTPS (domínio definitivo)", () => {
    expect(isSecureCookie("https://auditoria.exemplo.com.br")).toBe(true);
  });

  it("não marca Secure no acesso por IP em HTTP (servidor sem domínio)", () => {
    expect(isSecureCookie("http://203.0.113.10")).toBe(false);
  });

  it("não marca Secure no túnel SSH nem no dev local", () => {
    expect(isSecureCookie("http://localhost:8081")).toBe(false);
    expect(isSecureCookie("http://localhost:3000")).toBe(false);
  });

  it("ignora maiúsculas e espaços vindos do .env", () => {
    expect(isSecureCookie(" HTTPS://Auditoria.Exemplo.com.br ")).toBe(true);
  });

  it("sem APP_URL definida, não marca Secure", () => {
    vi.stubEnv("APP_URL", "");
    expect(isSecureCookie()).toBe(false);
  });

  it("lê APP_URL do ambiente quando chamada sem argumento", () => {
    vi.stubEnv("APP_URL", "https://auditoria.exemplo.com.br");
    expect(isSecureCookie()).toBe(true);
  });
});
