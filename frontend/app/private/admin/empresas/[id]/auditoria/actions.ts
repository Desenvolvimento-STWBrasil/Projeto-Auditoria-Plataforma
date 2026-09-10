"use server";

import { callBackend } from "@/lib/server-backend";
import { getAccessToken, requireAdmin } from "@/lib/session";

export type CompanyAuditListItem = {
  id: number;
  name: string;
  client_user_id: number;
  status: "DRAFT" | "ACTIVE" | "CLOSED";
  created_at: string;
};

type PaginatedCompanyAudits = {
  total: number;
  skip: number;
  limit: number;
  items: CompanyAuditListItem[];
};

export async function listCompanyAuditsAction(
  companyId: number,
): Promise<CompanyAuditListItem[]> {
  await requireAdmin();
  const token = await getAccessToken();
  const result = await callBackend<PaginatedCompanyAudits>(
    `/api/v1/admin/audits?company_id=${companyId}&skip=0&limit=100`,
    { token: token ?? undefined },
  );
  return result.items;
}
