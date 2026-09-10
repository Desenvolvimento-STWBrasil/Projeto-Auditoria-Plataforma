import { getCurrentUserProfile } from "@/lib/session";
import { getAdminUnreadCountsAction } from "./admin/actions";
import { UserMenu } from "./_components/user-menu";

export default async function PrivateLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const profile = await getCurrentUserProfile();
  const initialUnread =
    profile?.role === "admin" ? await getAdminUnreadCountsAction() : null;

  return (
    <>
      <UserMenu profile={profile} initialUnread={initialUnread} />
      {children}
    </>
  );
}
