import "server-only";

import { cache } from "react";
import { cookies } from "next/headers";
import { jwtVerify } from "jose";
import { callBackend } from "./server-backend";
import { redirect } from "next/navigation";

export type SessionRole = "admin" | "user" | "sub-user";

export type SessionUser = {
  id: number;
  role: SessionRole;
};

export type SessionProfile = {
  id: number;
  full_name: string;
  email: string;
  role: SessionRole;
  company_name: string | null;
};

const JWT_SECRET = process.env.JWT_SECRET;
const JWT_ALGORITHM = process.env.JWT_ALGORITHM ?? "HS256";

function getSecretKey(): Uint8Array {
  if (!JWT_SECRET) {
    throw new Error(
      "JWT_SECRET não configurado em frontend/ .env.local - necessário para" +
        "validar a sessão (ver docs/plano_implementacao.md, item D.1)",
    );
  }
  return new TextEncoder().encode(JWT_SECRET);
}

/**
 * Lê o cookie httpOnly `access_token` da requisição atual.
 * Retorna `null` se não houver sessão.
 */
export async function getAccessToken(): Promise<string | null> {
  const store = await cookies();
  return store.get("access_token")?.value ?? null;
}

/**
 * Verifica assinatura + expiração do access_token localmente (sem nenhuma
 * chamada de rede ao backend) e devolve `{id, role}` extraídos do próprio
 * JWT. Memoizado por requisição via `cache()` do React — mesmo chamado
 * várias vezes (layout, page, actions), só decodifica uma vez.
 *
 * Retorna `null` se: não houver token; a assinatura for inválida; o token
 * estiver expirado; ou for um refresh_token usado no lugar de um
 * access_token (proteção simétrica à de `get_current_user` no backend,
 * ver item A.10).
 */

export const getCurrentUser = cache(async (): Promise<SessionUser | null> => {
  const token = await getAccessToken();
  if (!token) return null;

  try {
    const { payload } = await jwtVerify(token, getSecretKey(), {
      algorithms: [JWT_ALGORITHM],
    });

    if (payload.type && payload.type !== "access") return null;

    const id = Number(payload.sub);
    const role = payload.role as SessionRole | undefined;
    if (!Number.isFinite(id) || !role) return null;

    return { id, role };
  } catch {
    return null;
  }
});

/**
 * Busca o perfil completo (full_name/email) no backend — GET /users/perfil.
 * Diferente de `getCurrentUser()`, faz uma chamada de rede real, necessária
 * porque o JWT não carrega `full_name`/`email` por design. Memoizado por
 * requisição via `cache()`: não importa quantos Server Components chamem
 * esta função no mesmo carregamento de página, o backend só é chamado 1 vez.
 */

export const getCurrentUserProfile = cache(
  async (): Promise<SessionProfile | null> => {
    const token = await getAccessToken();
    if (!token) return null;

    try {
      return await callBackend<SessionProfile>("/api/v1/users/perfil", {
        token,
      });
    } catch {
      return null;
    }
  },
);

/**
 * Garante que existe uma sessão de access_token válida. Redireciona para
 * /public/login (preservando o destino original em ?redirect=) se não
 * houver. Use em todo Server Component/Server Action que exige login,
 * independente do papel.
 */
export async function requireUser(): Promise<SessionUser> {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/public/login");
  }
  return user;
}

/* Garante sessão válida e papel === "admin"; senão redireciona para /private/client. */
export async function requireAdmin(): Promise<SessionUser> {
  const user = await requireUser();
  if (user.role !== "admin") {
    redirect("/private/client");
  }
  return user;
}

/** Garante sessão válida E papel !== "admin" (user ou sub-user); senão redireciona para /private/admin. */
export async function requireClient(): Promise<SessionUser> {
  const user = await requireUser();
  if (user.role === "admin") {
    redirect("/private/admin");
  }
  return user;
}
