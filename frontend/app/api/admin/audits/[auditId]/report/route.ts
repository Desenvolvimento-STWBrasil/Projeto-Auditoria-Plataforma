import { NextRequest, NextResponse } from "next/server";
import { getAccessToken, requireAdmin } from "@/lib/session";

const BACKEND_API_URL = process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000";

export async function GET(
  request: NextRequest,
  ctx: RouteContext<"/api/admin/audits/[auditId]/report">,
) {
  await requireAdmin();
  const { auditId } = await ctx.params;
  const token = await getAccessToken();

  const backendResponse = await fetch(
    `${BACKEND_API_URL}/api/v1/admin/audits/${auditId}/report.pdf`,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      cache: "no-store",
    },
  );

  if (!backendResponse.ok) {
    const data = await backendResponse.json().catch(() => null);
    return NextResponse.json(
      { detail: data?.detail ?? "Falha ao gerar o relatório." },
      { status: backendResponse.status },
    );
  }

  const pdfBytes = await backendResponse.arrayBuffer();
  return new NextResponse(pdfBytes, {
    status: 200,
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition":
        backendResponse.headers.get("Content-Disposition") ??
        `attachment; filename="auditoria-${auditId}.pdf"`,
    },
  });
}
