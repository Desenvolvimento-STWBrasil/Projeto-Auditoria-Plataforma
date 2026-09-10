"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { LogoutButton } from "./logout-button";
import type { SessionProfile } from "@/lib/session";
import {
  getAdminUnreadCountsAction,
  type AdminUnreadCounts,
} from "../admin/actions";

const ROLE_LABEL: Record<SessionProfile["role"], string> = {
  admin: "Administrador",
  user: "Cliente",
  "sub-user": "Sub-usuário",
};

// Intervalo de polling do badge de não lidas do admin — sem WebSocket/
// tempo real, mesmo padrão assíncrono já decidido para os 2 canais de
// chat existentes (proposta L.1).
const UNREAD_POLL_INTERVAL_MS = 45_000;

export function UserMenu({
  profile,
  initialUnread = null,
}: {
  profile: SessionProfile | null;
  initialUnread?: AdminUnreadCounts | null;
}) {
  const pathname = usePathname();
  const isAdmin = profile?.role === "admin";
  const [unread, setUnread] = useState<AdminUnreadCounts | null>(initialUnread);

  useEffect(() => {
    if (!isAdmin) return;

    const interval = setInterval(() => {
      getAdminUnreadCountsAction().then(setUnread);
    }, UNREAD_POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [isAdmin]);

  if (!profile) return null;

  const homeHref = isAdmin ? "/private/admin" : "/private/client";

  const navItems = [
    { href: homeHref, label: "Dashboard", unread: 0 },
    ...(isAdmin
      ? [
          { href: "/private/admin/empresas", label: "Empresas", unread: 0 },
          { href: "/private/admin/templates", label: "Templates", unread: 0 },
          {
            href: "/private/admin/auditorias",
            label: "Auditorias",
            unread: unread?.auditorias ?? 0,
          },
        ]
      : []),
    {
      href: isAdmin ? "/private/admin/mensagens" : "/private/client/mensagens",
      label: "Mensagens",
      unread: isAdmin ? (unread?.mensagens ?? 0) : 0,
    },
  ];

  const initials =
    profile.full_name
      .trim()
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join("") || "?";

  return (
    <header className="sticky top-0 z-40 border-b border-(--color-neutral) bg-white/95 backdrop-blur supports-backdrop-filter:bg-white/80">
      <div className="container-page flex h-16 items-center justify-between gap-4">
        <div className="flex min-w-0 items-center gap-6">
          <Link
            href={homeHref}
            className="flex shrink-0 items-center gap-2"
            aria-label="Ir para o painel"
          >
            <span className="inline-block h-3 w-3 rounded-full bg-(--color-primary)" />
            <strong className="hidden text-sm sm:inline md:text-base">
              Plataforma de Auditoria
            </strong>
          </Link>

          <nav
            aria-label="Navegação principal"
            className="flex items-center gap-1 overflow-x-auto"
          >
            {navItems.map((item) => {
              const active =
                item.href === homeHref
                  ? pathname === item.href
                  : pathname === item.href ||
                    pathname?.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition ${
                    active
                      ? "bg-(--color-primary)/10 text-(--color-primary)"
                      : "text-(--color-dark) hover:bg-(--color-surface) hover:text-(--color-primary)"
                  }`}
                >
                  {item.label}
                  {item.unread > 0 ? (
                    <span
                      aria-label={`${item.unread} mensagem(ns) não lida(s)`}
                      className="rounded-full bg-(--color-primary) px-1.5 py-0.5 text-[10px] font-semibold leading-none text-white"
                    >
                      {item.unread}
                    </span>
                  ) : null}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex shrink-0 items-center gap-3">
          <div className="hidden items-center gap-2 sm:flex">
            <span
              aria-hidden="true"
              className="flex h-8 w-8 items-center justify-center rounded-full bg-(--color-dark) text-xs font-semibold text-white"
            >
              {initials}
            </span>
            <div className="hidden leading-tight md:block">
              <p className="max-w-40 truncate text-sm font-semibold">
                {profile.full_name}
              </p>
              <p className="text-xs text-zinc-500">
                {ROLE_LABEL[profile.role]}
              </p>
            </div>
          </div>
          <LogoutButton />
        </div>
      </div>
    </header>
  );
}
