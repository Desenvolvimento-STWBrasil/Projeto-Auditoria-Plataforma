import { NextRequest, NextResponse } from "next/server";
import { getAccessToken, requireAdmin } from "@/lib/session";

const BACKEND_API_URL = process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000";

/**
 * Proxy autenticado para download de evidência (proposta L.4) — mesmo
 * motivo/padrão da rota de relatório em PDF (ver
 * app/api/admin/audits/[auditId]/report/route.ts, seção 7.1 de L.2).
 */
export async function GET(
  request: NextRequest,
  ctx: RouteContext<"/api/admin/evidences/[evidenceId]/download">,
) {
  await requireAdmin();
  const { evidenceId } = await ctx.params;
  const token = await getAccessToken();

  const backendResponse = await fetch(
    `${BACKEND_API_URL}/api/v1/admin/evidences/${evidenceId}/download`,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      cache: "no-store",
    },
  );

  if (!backendResponse.ok) {
    const data = await backendResponse.json().catch(() => null);
    return NextResponse.json(
      { detail: data?.detail ?? "Falha ao baixar a evidência." },
      { status: backendResponse.status },
    );
  }

  const fileBytes = await backendResponse.arrayBuffer();
  return new NextResponse(fileBytes, {
    status: 200,
    headers: {
      "Content-Type":
        backendResponse.headers.get("Content-Type") ??
        "application/octet-stream",
      "Content-Disposition":
        backendResponse.headers.get("Content-Disposition") ?? "attachment",
    },
  });
}
