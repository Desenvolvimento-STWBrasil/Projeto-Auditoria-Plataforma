import { listDashboardLabelsAction } from "./actions";
import { DashboardLabelsClient } from "./dashboard-labels-client";

export default async function AdminDashboardLabelsPage() {
  const labels = await listDashboardLabelsAction();

  return <DashboardLabelsClient initialLabels={labels} />;
}