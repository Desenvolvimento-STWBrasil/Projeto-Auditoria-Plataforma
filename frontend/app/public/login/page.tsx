import { Suspense } from "react";
import { LoginForm } from "./login-form";
import { PublicAuthCleanup } from "@/_components/public-auth-cleanup";

export default function LoginPage() {
  return (
    <Suspense fallback={<main className="min-h-screen" />}>
      <PublicAuthCleanup />
      <LoginForm />
    </Suspense>
  );
}
