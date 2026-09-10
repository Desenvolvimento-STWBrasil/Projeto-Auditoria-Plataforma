import { callBackend } from "@/lib/server-backend";
import { getAccessToken, requireAdmin } from "@/lib/session";
import {
  getDashboardStatusSummaryAction,
  getRecentUnreadCompanyMessagesAction,
  PendingSubUserRequest,
} from "./actions";
import { listCompaniesAdminAction } from "./empresas/actions";
import { AdminDashboardClient } from "./admin-dashboard-client";

const COMPANIES_PREVIEW_LIMIT = 5;

export default async function AdminPage() {
  await requireAdmin();
  const token = await getAccessToken();

  const [pendingRequests, statusSummary, recentUnreadMessages, companies] =
    await Promise.all([
      callBackend<PendingSubUserRequest[]>(
        "/api/v1/sub-users/requests/pending",
        { token: token ?? undefined },
      ),
      getDashboardStatusSummaryAction(),
      getRecentUnreadCompanyMessagesAction(),
      listCompaniesAdminAction(0, ""),
    ]);

  return (
    <AdminDashboardClient
      initialPendingRequests={pendingRequests}
      statusSummary={statusSummary}
      recentUnreadMessages={recentUnreadMessages}
      companiesPreview={companies.items.slice(0, COMPANIES_PREVIEW_LIMIT)}
      companiesTotal={companies.total}
    />
  );
}
