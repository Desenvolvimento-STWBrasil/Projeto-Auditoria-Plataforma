import { NextRequest, NextResponse } from "next/server";
import { callBackend } from "@/lib/server-backend";

export async function POST(request: NextRequest) {
  try {
    const payload = await request.json();

    const data = await callBackend("/api/v1/auth/register", {
      method: "POST",
      body: payload,
    });

    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Erro ao cadastrar usuário";
    return NextResponse.json({ detail: message }, { status: 400 });
  }
}
