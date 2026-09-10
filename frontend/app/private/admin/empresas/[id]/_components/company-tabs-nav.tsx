"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { segment: "perfil", label: "Perfil" },
  { segment: "dashboard", label: "Dashboard & Template" },
  { segment: "usuarios", label: "Usuários" },
  { segment: "auditoria", label: "Auditoria" },
] as const;

export function CompanyTabsNav({ companyId }: { companyId: number }) {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Abas de configuração da empresa"
      className="mt-4 flex gap-1 overflow-x-auto"
    >
      {TABS.map((tab) => {
        const href = `/private/admin/empresas/${companyId}/${tab.segment}`;
        const active = pathname === href || pathname?.startsWith(`${href}/`);
        return (
          <Link
            key={tab.segment}
            href={href}
            aria-current={active ? "page" : undefined}
            className={`shrink-0 rounded-t-lg border-b-2 px-4 py-2 text-sm font-medium transition ${
              active
                ? "border-(--color-primary) text-(--color-primary)"
                : "border-transparent text-zinc-600 hover:text-(--color-dark)"
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
