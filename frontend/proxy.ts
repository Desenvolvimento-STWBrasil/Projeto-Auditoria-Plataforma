import { jwtVerify } from "jose";
import { NextRequest, NextResponse } from "next/server";

/**
 * Proxy (substitui middleware.ts — renomeação obrigatória nesta versão do
 * Next.js, "middleware" está deprecado desde a v16.0.0).
 *
 * Faz, nesta ordem:
 * 1. Em rotas públicas de "logout forçado" (/, /public/login, /public/cadastro),
 *    limpa os cookies de sessão.
 * 2. Em qualquer rota /private/*, verifica a assinatura do access_token e,
 *    se ausente/expirado mas houver refresh_token válido, renova a sessão
 *    silenciosamente chamando o backend diretamente (fecha o loop de
 *    auto-refresh deixado em aberto no item A.10).
 * 3. Valida o papel (role) simetricamente para /private/admin e
 *    /private/client (absorve o item D.2).
 *
 * Checagem OTIMISTA (só lê o cookie) — a checagem AUTORITATIVA é feita pela
 * DAL (lib/session.ts) em cada Server Component/Server Action, e pelo
 * backend em cada endpoint. Nunca dependa só deste arquivo para autorização.
 */

/* Rotas públicas que devem forçar logout automaticamente */
const FORCE_LOGOUT_PATHS = new Set(["/", "/public/login", "/public/cadastro"]);
const BACKEND_API_URL = process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000";
const JWT_SECRET = process.env.JWT_SECRET;
const JWT_ALGORITHM = process.env.JWT_ALGORITHM ?? "HS256";

/**
 * Os defaults abaixo espelham os de backend/app/core/config.py
 * (JWT_EXPIRES_MINUTES = 15, JWT_REFRESH_EXPIRES_DAYS = 7). Divergir
 * fazia o cookie sobreviver 45 min ao token que ele carrega (B-M29):
 * o proxy renovava em silêncio, escondendo a inconsistência atrás de um
 * round-trip extra a cada navegação.
 */
const ACCESS_TOKEN_MAX_AGE_SECONDS =
  Number(process.env.JWT_EXPIRES_MINUTES ?? 15) * 60;

const REFRESH_TOKEN_MAX_AGE_SECONDS =
  Number(process.env.JWT_REFRESH_EXPIRES_DAYS ?? 7) * 24 * 60 * 60;

type AccessTokenPayload = {
  sub: string;
  role?: "admin" | "user" | "sub-user";
  type?: string;
};

type RefreshedTokens = {
  access_token: string;
  refresh_token: string;
};

async function verifyAccessToken(
  token: string,
): Promise<AccessTokenPayload | null> {
  if (!JWT_SECRET) return null;

  try {
    const secret = new TextEncoder().encode(JWT_SECRET);
    const { payload } = await jwtVerify(token, secret, {
      algorithms: [JWT_ALGORITHM],
    });
    if (payload.type && payload.type !== "access") return null;
    return payload as AccessTokenPayload;
  } catch {
    return null;
  }
}

async function tryRefresh(
  refreshToken: string,
): Promise<RefreshedTokens | null> {
  try {
    const resp = await fetch(`${BACKEND_API_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
      cache: "no-store",
    });
    if (!resp.ok) return null;
    return (await resp.json()) as RefreshedTokens;
  } catch {
    return null;
  }
}

function setSessionCookies(
  response: NextResponse,
  tokens: RefreshedTokens,
): void {
  response.cookies.set("access_token", tokens.access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: ACCESS_TOKEN_MAX_AGE_SECONDS,
  });
  response.cookies.set("refresh_token", tokens.refresh_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: REFRESH_TOKEN_MAX_AGE_SECONDS,
  });
}

function clearSessionCookies(response: NextResponse): void {
  response.cookies.set("access_token", "", {
    httpOnly: true,
    path: "/",
    maxAge: 0,
  });
  response.cookies.set("refresh_token", "", {
    httpOnly: true,
    path: "/",
    maxAge: 0,
  });
}

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const accessToken = request.cookies.get("access_token")?.value;
  const refreshToken = request.cookies.get("refresh_token")?.value;

  if (FORCE_LOGOUT_PATHS.has(pathname)) {
    const response = NextResponse.next();
    if (accessToken || refreshToken) clearSessionCookies(response);
    return response;
  }

  if (!pathname.startsWith("/private")) {
    return NextResponse.next();
  }

  let payload = accessToken ? await verifyAccessToken(accessToken) : null;
  let refreshedTokens: RefreshedTokens | null = null;

  if (!payload && refreshToken) {
    refreshedTokens = await tryRefresh(refreshToken);
    if (refreshedTokens) {
      payload = await verifyAccessToken(refreshedTokens.access_token);
    }
  }

  if (!payload || !payload.role) {
    const url = request.nextUrl.clone();
    url.pathname = "/public/login";
    url.searchParams.set("redirect", pathname);
    const response = NextResponse.redirect(url);
    clearSessionCookies(response);
    return response;
  }

  if (pathname.startsWith("/private/admin") && payload.role !== "admin") {
    const response = NextResponse.redirect(
      new URL("/private/client", request.url),
    );
    if (refreshedTokens) setSessionCookies(response, refreshedTokens);
    return response;
  }

  if (pathname.startsWith("/private/client") && payload.role === "admin") {
    const response = NextResponse.redirect(
      new URL("/private/admin", request.url),
    );
    if (refreshedTokens) setSessionCookies(response, refreshedTokens);
    return response;
  }

  const response = NextResponse.next();
  if (refreshedTokens) setSessionCookies(response, refreshedTokens);
  return response;
}

export const config = {
  matcher: ["/", "/private/:path*", "/public/:path*"],
};
