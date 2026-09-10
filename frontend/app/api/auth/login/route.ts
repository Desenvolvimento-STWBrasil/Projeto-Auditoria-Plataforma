import { callBackend } from "@/lib/server-backend";
import { jwtVerify } from "jose";
import { NextRequest, NextResponse } from "next/server";

type LoginResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

// Espelha backend/app/core/config.py — ver B-M29.
const ACCESS_TOKEN_MAX_AGE_SECONDS =
  Number(process.env.JWT_EXPIRES_MINUTES ?? 15) * 60;
const REFRESH_TOKEN_MAX_AGE_SECONDS =
  Number(process.env.JWT_REFRESH_EXPIRES_DAYS ?? 7) * 24 * 60 * 60;

const JWT_SECRET = process.env.JWT_SECRET;
const JWT_ALGORITHM = process.env.JWT_ALGORITHM ?? "HS256";

async function extractRole(
  accessToken: string,
): Promise<"admin" | "user" | "sub-user" | null> {
  if (!JWT_SECRET) return null;

  try {
    const secret = new TextEncoder().encode(JWT_SECRET);
    const { payload } = await jwtVerify(accessToken, secret, {
      algorithms: [JWT_ALGORITHM],
    });
    return (payload.role as "admin" | "user" | "sub-user" | undefined) ?? null;
  } catch {
    return null;
  }
}

export async function POST(request: NextRequest) {
  try {
    const payload = (await request.json()) as {
      email: string;
      password: string;
    };

    const data = await callBackend<LoginResponse>("/api/v1/auth/login", {
      method: "POST",
      body: payload,
    });

    const role = await extractRole(data.access_token);

    const response = NextResponse.json({ ok: true, role });

    response.cookies.set("access_token", data.access_token, {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/",
      maxAge: ACCESS_TOKEN_MAX_AGE_SECONDS,
    });

    response.cookies.set("refresh_token", data.refresh_token, {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/",
      maxAge: REFRESH_TOKEN_MAX_AGE_SECONDS,
    });

    return response;
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Erro ao fazer login";
    return NextResponse.json({ detail: message }, { status: 401 });
  }
}
