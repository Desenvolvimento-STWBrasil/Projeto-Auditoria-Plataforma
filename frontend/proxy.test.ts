import { SignJWT } from "jose";
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

/**
 * `proxy.ts` substitui o `middleware.ts` (renomeação obrigatória no
 * Next.js 16) e é a primeira das três camadas de autorização.
 *
 * Ele documenta no próprio arquivo que sua checagem é **otimista** — a
 * autoritativa é a DAL (`lib/session.ts`) e o backend. Estes testes
 * cobrem o comportamento que ele de fato promete: limpar sessão nas
 * rotas públicas, barrar `/private/**` sem token, validar o papel
 * simetricamente e renovar a sessão em silêncio quando o access_token
 * expirou mas o refresh ainda vale.
 */

const SEGREDO = "x".repeat(64);
const BACKEND = "http://127.0.0.1:8000";

async function assinar(
  payload: Record<string, unknown>,
  { expiraEm = "1h", segredo = SEGREDO } = {},
): Promise<string> {
  return new SignJWT(payload)
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime(expiraEm)
    .sign(new TextEncoder().encode(segredo));
}

function requisicao(
  caminho: string,
  cookies: Record<string, string> = {},
): NextRequest {
  const headers = new Headers();
  const serializado = Object.entries(cookies)
    .map(([k, v]) => `${k}=${v}`)
    .join("; ");
  if (serializado) headers.set("cookie", serializado);
  return new NextRequest(new URL(caminho, "http://localhost:3000"), { headers });
}

async function importarProxy() {
  vi.resetModules();
  process.env.JWT_SECRET = SEGREDO;
  process.env.JWT_ALGORITHM = "HS256";
  process.env.BACKEND_API_URL = BACKEND;
  return import("./proxy");
}

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("rotas públicas — logout forçado", () => {
  it.each(["/", "/public/login", "/public/cadastro"])(
    "limpa os cookies de sessão em %s",
    async (caminho) => {
      const { proxy } = await importarProxy();

      const resposta = await proxy(
        requisicao(caminho, { access_token: "abc", refresh_token: "def" }),
      );

      expect(resposta.cookies.get("access_token")?.value).toBe("");
      expect(resposta.cookies.get("refresh_token")?.value).toBe("");
    },
  );

  it("não mexe em cookie quando não havia sessão", async () => {
    const { proxy } = await importarProxy();

    const resposta = await proxy(requisicao("/public/login"));

    expect(resposta.cookies.get("access_token")).toBeUndefined();
  });
});

describe("rotas fora de /private", () => {
  it("deixa passar sem verificar nada", async () => {
    const { proxy } = await importarProxy();

    const resposta = await proxy(requisicao("/public/algo-qualquer"));

    expect(resposta.status).toBe(200);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("/private sem sessão válida", () => {
  it("redireciona ao login preservando o destino", async () => {
    const { proxy } = await importarProxy();

    const resposta = await proxy(requisicao("/private/admin/empresas"));

    expect(resposta.status).toBe(307);
    const destino = new URL(resposta.headers.get("location")!);
    expect(destino.pathname).toBe("/public/login");
    expect(destino.searchParams.get("redirect")).toBe("/private/admin/empresas");
  });

  it("redireciona ao login quando o token é de outro segredo", async () => {
    const { proxy } = await importarProxy();
    const token = await assinar(
      { sub: "1", role: "admin" },
      { segredo: "y".repeat(64) },
    );

    const resposta = await proxy(
      requisicao("/private/admin", { access_token: token }),
    );

    expect(resposta.status).toBe(307);
    expect(resposta.headers.get("location")).toContain("/public/login");
  });

  it("recusa um refresh_token usado como access_token", async () => {
    const { proxy } = await importarProxy();
    const token = await assinar({ sub: "1", role: "admin", type: "refresh" });

    const resposta = await proxy(
      requisicao("/private/admin", { access_token: token }),
    );

    expect(resposta.status).toBe(307);
    expect(resposta.headers.get("location")).toContain("/public/login");
  });
});

describe("/private com sessão válida — validação de papel", () => {
  it("deixa o admin entrar em /private/admin", async () => {
    const { proxy } = await importarProxy();
    const token = await assinar({ sub: "1", role: "admin" });

    const resposta = await proxy(
      requisicao("/private/admin", { access_token: token }),
    );

    expect(resposta.status).toBe(200);
  });

  it("manda o cliente que tenta /private/admin para a área dele", async () => {
    const { proxy } = await importarProxy();
    const token = await assinar({ sub: "9", role: "user" });

    const resposta = await proxy(
      requisicao("/private/admin/empresas", { access_token: token }),
    );

    expect(resposta.status).toBe(307);
    expect(resposta.headers.get("location")).toContain("/private/client");
  });

  it("manda o admin que tenta /private/client para a área dele", async () => {
    const { proxy } = await importarProxy();
    const token = await assinar({ sub: "1", role: "admin" });

    const resposta = await proxy(
      requisicao("/private/client", { access_token: token }),
    );

    expect(resposta.status).toBe(307);
    expect(resposta.headers.get("location")).toContain("/private/admin");
  });

  it("deixa o sub-usuário entrar em /private/client", async () => {
    const { proxy } = await importarProxy();
    const token = await assinar({ sub: "5", role: "sub-user" });

    const resposta = await proxy(
      requisicao("/private/client", { access_token: token }),
    );

    expect(resposta.status).toBe(200);
  });
});

describe("renovação silenciosa de sessão", () => {
  it("troca o refresh por um par novo e segue a navegação", async () => {
    const { proxy } = await importarProxy();
    const expirado = await assinar({ sub: "1", role: "admin" }, { expiraEm: "-1h" });
    const novoAccess = await assinar({ sub: "1", role: "admin" });

    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        access_token: novoAccess,
        refresh_token: "refresh-novo",
      }),
    });

    const resposta = await proxy(
      requisicao("/private/admin", {
        access_token: expirado,
        refresh_token: "refresh-antigo",
      }),
    );

    expect(fetchMock).toHaveBeenCalledWith(
      `${BACKEND}/api/v1/auth/refresh`,
      expect.objectContaining({ method: "POST" }),
    );
    expect(resposta.status).toBe(200);
    expect(resposta.cookies.get("access_token")?.value).toBe(novoAccess);
    expect(resposta.cookies.get("refresh_token")?.value).toBe("refresh-novo");
  });

  it("mantém o maxAge do cookie alinhado ao backend (15 min)", async () => {
    // B-M29: o default do frontend era 60, o do backend 15 — o cookie
    // sobrevivia 45 min ao token que carregava.
    delete process.env.JWT_EXPIRES_MINUTES;
    const { proxy } = await importarProxy();
    const expirado = await assinar({ sub: "1", role: "admin" }, { expiraEm: "-1h" });
    const novoAccess = await assinar({ sub: "1", role: "admin" });

    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        access_token: novoAccess,
        refresh_token: "refresh-novo",
      }),
    });

    const resposta = await proxy(
      requisicao("/private/admin", {
        access_token: expirado,
        refresh_token: "refresh-antigo",
      }),
    );

    expect(resposta.cookies.get("access_token")?.maxAge).toBe(15 * 60);
    expect(resposta.cookies.get("refresh_token")?.maxAge).toBe(7 * 24 * 60 * 60);
  });

  it("redireciona ao login quando o refresh também não vale", async () => {
    const { proxy } = await importarProxy();
    const expirado = await assinar({ sub: "1", role: "admin" }, { expiraEm: "-1h" });

    fetchMock.mockResolvedValue({ ok: false, json: async () => ({}) });

    const resposta = await proxy(
      requisicao("/private/admin", {
        access_token: expirado,
        refresh_token: "refresh-invalido",
      }),
    );

    expect(resposta.status).toBe(307);
    expect(resposta.headers.get("location")).toContain("/public/login");
    expect(resposta.cookies.get("access_token")?.value).toBe("");
  });

  it("não derruba a navegação se o backend estiver fora do ar", async () => {
    const { proxy } = await importarProxy();
    const expirado = await assinar({ sub: "1", role: "admin" }, { expiraEm: "-1h" });

    fetchMock.mockRejectedValue(new Error("ECONNREFUSED"));

    const resposta = await proxy(
      requisicao("/private/admin", {
        access_token: expirado,
        refresh_token: "refresh-qualquer",
      }),
    );

    // Sem sessão renovável, o destino correto é o login — não um 500.
    expect(resposta.status).toBe(307);
    expect(resposta.headers.get("location")).toContain("/public/login");
  });

  it("preserva os cookies novos ao redirecionar por papel errado", async () => {
    const { proxy } = await importarProxy();
    const expirado = await assinar({ sub: "9", role: "user" }, { expiraEm: "-1h" });
    const novoAccess = await assinar({ sub: "9", role: "user" });

    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        access_token: novoAccess,
        refresh_token: "refresh-novo",
      }),
    });

    const resposta = await proxy(
      requisicao("/private/admin", {
        access_token: expirado,
        refresh_token: "refresh-antigo",
      }),
    );

    expect(resposta.status).toBe(307);
    expect(resposta.headers.get("location")).toContain("/private/client");
    // A sessão renovada não pode se perder no redirect — senão o próximo
    // request repete o refresh.
    expect(resposta.cookies.get("access_token")?.value).toBe(novoAccess);
  });
});
