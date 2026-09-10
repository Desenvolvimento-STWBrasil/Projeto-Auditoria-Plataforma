"use client";

export function LogoutButton() {
  async function handleLogout() {
    // Limpa localStorage legado
    localStorage.removeItem("access_token");
    localStorage.removeItem("token");
    localStorage.removeItem("auth_token");

    await fetch("/api/auth/logout", { method: "POST" });
    // Reload completo (não `router.push`, navegação client-side) — força
    // o navegador a descartar qualquer estado/cache de Server Component
    // da sessão anterior (ex.: getCurrentUser()/getCurrentUserProfile(),
    // memoizados por requisição via cache() em lib/session.ts) em vez de
    // reaproveitá-lo numa navegação client-side. Ver B-B12 em
    // docs/relatorio_bugs.md.
    window.location.href = "/public/login";
  }

  return (
    <button
      type="button"
      onClick={handleLogout}
      className="rounded-xl border border-(--color-neutral) px-4 py-2 text-sm font-medium text-(--color-dark) transition hover:border-red-300 hover:bg-red-50 hover:text-red-600"
    >
      Sair
    </button>
  );
}
