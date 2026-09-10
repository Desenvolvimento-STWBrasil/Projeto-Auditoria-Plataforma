import { SignJWT } from "jose";
import { beforeEach, describe, expect, it, vi } from "vitest";

/**
 * `lib/session.ts` é a DAL de sessão — a checagem **autoritativa** que
 * todo Server Component e Server Action faz. O `proxy.ts` é otimista e
 * documenta isso no próprio arquivo; é aqui que a decisão vale.
 *
 * Os testes assinam JWTs de verdade com `jose` em vez de mockar
 * `jwtVerify`. Mockar a verificação de assinatura num teste de
 * autorização removeria justamente a parte que importa.
 */

const SEGREDO = "x".repeat(64);

const cookieStore = new Map<string, string>();
const redirectMock = vi.fn((destino: string) => {
  throw new Error(`NEXT_REDIRECT:${destino}`);
});
const callBackendMock = vi.fn();

vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: (nome: string) => {
      const value = cookieStore.get(nome);
      return value === undefined ? undefined : { name: nome, value };
    },
  }),
}));

vi.mock("next/navigation", () => ({
  redirect: (destino: string) => redirectMock(destino),
}));

vi.mock("./server-backend", () => ({
  callBackend: (...args: unknown[]) => callBackendMock(...args),
}));

// `cache()` do React memoiza por requisição. Fora de um escopo de
// requisição o comportamento não é garantido, e um resultado memoizado
// vazaria de um teste para o seguinte — o que faria o teste de "token
// expirado" passar com o payload do teste anterior.
vi.mock("react", async () => {
  const real = await vi.importActual<typeof import("react")>("react");
  return { ...real, cache: <T,>(fn: T) => fn };
});

async function assinar(
  payload: Record<string, unknown>,
  { segredo = SEGREDO, expiraEm = "1h" } = {},
): Promise<string> {
  return new SignJWT(payload)
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime(expiraEm)
    .sign(new TextEncoder().encode(segredo));
}

async function importarSessao() {
  vi.resetModules();
  process.env.JWT_SECRET = SEGREDO;
  process.env.JWT_ALGORITHM = "HS256";
  return import("./session");
}

beforeEach(() => {
  cookieStore.clear();
  redirectMock.mockClear();
  callBackendMock.mockReset();
});

describe("getCurrentUser", () => {
  it("devolve id e papel de um access_token válido", async () => {
    cookieStore.set("access_token", await assinar({ sub: "42", role: "admin" }));
    const { getCurrentUser } = await importarSessao();

    await expect(getCurrentUser()).resolves.toEqual({ id: 42, role: "admin" });
  });

  it("devolve null quando não há cookie", async () => {
    const { getCurrentUser } = await importarSessao();

    await expect(getCurrentUser()).resolves.toBeNull();
  });

  it("devolve null para assinatura de outro segredo", async () => {
    cookieStore.set(
      "access_token",
      await assinar({ sub: "42", role: "admin" }, { segredo: "y".repeat(64) }),
    );
    const { getCurrentUser } = await importarSessao();

    await expect(getCurrentUser()).resolves.toBeNull();
  });

  it("devolve null para token expirado", async () => {
    cookieStore.set(
      "access_token",
      await assinar({ sub: "42", role: "admin" }, { expiraEm: "-1h" }),
    );
    const { getCurrentUser } = await importarSessao();

    await expect(getCurrentUser()).resolves.toBeNull();
  });

  it("recusa um refresh_token usado no lugar de access_token", async () => {
    // Proteção simétrica à de deps.py::get_current_user no backend.
    cookieStore.set(
      "access_token",
      await assinar({ sub: "42", role: "admin", type: "refresh" }),
    );
    const { getCurrentUser } = await importarSessao();

    await expect(getCurrentUser()).resolves.toBeNull();
  });

  it("aceita token com type=access explícito", async () => {
    cookieStore.set(
      "access_token",
      await assinar({ sub: "7", role: "user", type: "access" }),
    );
    const { getCurrentUser } = await importarSessao();

    await expect(getCurrentUser()).resolves.toEqual({ id: 7, role: "user" });
  });

  it("devolve null quando o payload não traz papel", async () => {
    cookieStore.set("access_token", await assinar({ sub: "42" }));
    const { getCurrentUser } = await importarSessao();

    await expect(getCurrentUser()).resolves.toBeNull();
  });

  it("devolve null quando o sub não é numérico", async () => {
    cookieStore.set("access_token", await assinar({ sub: "abc", role: "user" }));
    const { getCurrentUser } = await importarSessao();

    await expect(getCurrentUser()).resolves.toBeNull();
  });
});

describe("requireUser / requireAdmin / requireClient", () => {
  it("requireUser redireciona ao login sem sessão", async () => {
    const { requireUser } = await importarSessao();

    await expect(requireUser()).rejects.toThrow("NEXT_REDIRECT:/public/login");
    expect(redirectMock).toHaveBeenCalledWith("/public/login");
  });

  it("requireAdmin manda o cliente para a área dele", async () => {
    cookieStore.set("access_token", await assinar({ sub: "9", role: "user" }));
    const { requireAdmin } = await importarSessao();

    await expect(requireAdmin()).rejects.toThrow(
      "NEXT_REDIRECT:/private/client",
    );
  });

  it("requireAdmin deixa o admin passar", async () => {
    cookieStore.set("access_token", await assinar({ sub: "1", role: "admin" }));
    const { requireAdmin } = await importarSessao();

    await expect(requireAdmin()).resolves.toEqual({ id: 1, role: "admin" });
    expect(redirectMock).not.toHaveBeenCalled();
  });

  it("requireClient manda o admin para a área dele", async () => {
    cookieStore.set("access_token", await assinar({ sub: "1", role: "admin" }));
    const { requireClient } = await importarSessao();

    await expect(requireClient()).rejects.toThrow("NEXT_REDIRECT:/private/admin");
  });

  it("requireClient aceita user e sub-user", async () => {
    for (const role of ["user", "sub-user"] as const) {
      cookieStore.set("access_token", await assinar({ sub: "5", role }));
      const { requireClient } = await importarSessao();

      await expect(requireClient()).resolves.toEqual({ id: 5, role });
    }
  });
});

describe("getCurrentUserProfile", () => {
  it("busca o perfil no backend com o token do cookie", async () => {
    const token = await assinar({ sub: "3", role: "user" });
    cookieStore.set("access_token", token);
    callBackendMock.mockResolvedValue({
      id: 3,
      full_name: "Maria",
      email: "maria@test.com",
      role: "user",
    });
    const { getCurrentUserProfile } = await importarSessao();

    const perfil = await getCurrentUserProfile();

    expect(callBackendMock).toHaveBeenCalledWith("/api/v1/users/perfil", {
      token,
    });
    expect(perfil?.full_name).toBe("Maria");
  });

  it("devolve null — sem lançar — quando o backend falha", async () => {
    cookieStore.set("access_token", await assinar({ sub: "3", role: "user" }));
    callBackendMock.mockRejectedValue(new Error("backend fora do ar"));
    const { getCurrentUserProfile } = await importarSessao();

    await expect(getCurrentUserProfile()).resolves.toBeNull();
  });

  it("nem chama o backend quando não há sessão", async () => {
    const { getCurrentUserProfile } = await importarSessao();

    await expect(getCurrentUserProfile()).resolves.toBeNull();
    expect(callBackendMock).not.toHaveBeenCalled();
  });
});
