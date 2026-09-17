"use client";

import { useState, useTransition } from "react";
import {
  approveSubUserRequestAction,
  DashboardStatusSummary,
  PendingSubUserRequest,
  RecentUnreadCompanyMessage,
  rejectSubUserRequestAction,
} from "./actions";
import { CompanyAdminListItem } from "./empresas/actions";
import { PageHeader } from "../_components/page-header";
import { StatusSummaryCards } from "../_components/status-summary-cards";
import Link from "next/link";

type AdminDashboardClientProps = {
  initialPendingRequests: PendingSubUserRequest[];
  statusSummary: DashboardStatusSummary;
  recentUnreadMessages: RecentUnreadCompanyMessage[];
  companiesPreview: CompanyAdminListItem[];
  companiesTotal: number;
};

export function AdminDashboardClient({
  initialPendingRequests,
  statusSummary,
  recentUnreadMessages,
  companiesPreview,
  companiesTotal,
}: AdminDashboardClientProps) {
  const [pendingRequests, setPendingRequests] = useState<
    PendingSubUserRequest[]
  >(initialPendingRequests);
  const [approvingRequestId, setApprovingRequestId] = useState<number | null>(
    null,
  );
  const [rejectingRequestId, setRejectingRequestId] = useState<number | null>(
    null,
  );
  const [isPending, startTransition] = useTransition();

  function approveRequest(id: number) {
    setApprovingRequestId(id);
    startTransition(async () => {
      const result = await approveSubUserRequestAction(id);
      if (result.ok) {
        setPendingRequests((prev) => prev.filter((r) => r.id !== id));
      } else {
        window.alert(result.message);
      }
      setApprovingRequestId(null);
    });
  }

  function rejectRequest(id: number) {
    if (!window.confirm("Recusar esta solicitação de colaborador?")) return;

    setRejectingRequestId(id);
    startTransition(async () => {
      const result = await rejectSubUserRequestAction(id);
      if (result.ok) {
        setPendingRequests((prev) => prev.filter((r) => r.id !== id));
      } else {
        window.alert(result.message);
      }
      setRejectingRequestId(null);
    });
  }

  return (
    <main className="min-h-screen bg-(--color-surface) py-8">
      <div className="container-page space-y-6">
        <PageHeader
          title="Resumo"
          description='Visão agregada da auditoria em todos os clientes — para trabalhar os cards de uma empresa, entre em "Empresas" e escolha "Configurar".'
        />

        <StatusSummaryCards summary={statusSummary} />

        <div className="grid gap-6 lg:grid-cols-2">
          <section className="card">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-(--color-dark)">
                Solicitações pendentes de colaborador
              </h2>
              <span className="text-sm text-zinc-500">
                {pendingRequests.length} pendente(s)
              </span>
            </div>

            {pendingRequests.length === 0 ? (
              <p className="mt-3 text-sm text-zinc-600">
                Nenhuma solicitação pendente no momento.
              </p>
            ) : (
              <ul className="mt-4 space-y-3">
                {pendingRequests.map((request) => (
                  <li
                    key={request.id}
                    className="rounded-lg border border-zinc-200 p-3"
                  >
                    <p className="text-sm font-semibold text-(--color-dark)">
                      {request.requested_full_name}
                    </p>
                    <p className="mt-1 text-sm text-zinc-600">
                      {request.request_email}
                    </p>
                    <p className="mt-1 text-sm text-zinc-500">
                      Empresa: {request.company_name ?? "Não identificada"}
                    </p>
                    <div className="mt-3 flex gap-2">
                      <button
                        type="button"
                        className="btn-primary"
                        disabled={
                          isPending &&
                          (approvingRequestId === request.id ||
                            rejectingRequestId === request.id)
                        }
                        onClick={() => approveRequest(request.id)}
                      >
                        {approvingRequestId === request.id
                          ? "Aprovando..."
                          : "Aprovar solicitação"}
                      </button>
                      <button
                        type="button"
                        className="btn-secondary"
                        disabled={
                          isPending &&
                          (approvingRequestId === request.id ||
                            rejectingRequestId === request.id)
                        }
                        onClick={() => rejectRequest(request.id)}
                      >
                        {rejectingRequestId === request.id
                          ? "Recusando..."
                          : "Recusar solicitação"}
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="card">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-(--color-dark)">
                Mensagens não lidas
              </h2>
              <Link
                href="/private/admin/mensagens"
                className="text-sm font-medium text-(--color-primary)"
              >
                ver todas →
              </Link>
            </div>

            {recentUnreadMessages.length === 0 ? (
              <p className="mt-3 text-sm text-zinc-600">
                Nenhuma mensagem não lida no momento.
              </p>
            ) : (
              <ul className="mt-4 space-y-3">
                {recentUnreadMessages.map((message) => (
                  <li key={message.company_id}>
                    <Link
                      href={`/private/admin/mensagens?empresa=${message.company_id}&conversa=${message.last_message_id}`}
                      className="block rounded-lg border border-zinc-200 p-3 transition hover:border-(--color-primary)"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-semibold text-(--color-dark)">
                          {message.company_name}
                        </span>
                        <span className="rounded-full bg-(--color-primary) px-2 py-0.5 text-xs font-semibold text-white">
                          {message.unread_count}
                        </span>
                      </div>
                      <p className="mt-1 truncate text-sm text-zinc-600">
                        {message.last_message_preview}
                      </p>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <section className="card">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-(--color-dark)">
              Empresas
            </h2>
            <Link
              href="/private/admin/empresas"
              className="text-sm font-medium text-(--color-primary)"
            >
              ver todas ({companiesTotal}) →
            </Link>
          </div>

          {companiesPreview.length === 0 ? (
            <p className="mt-3 text-sm text-zinc-600">
              Nenhuma empresa cadastrada ainda.
            </p>
          ) : (
            <ul className="mt-4 divide-y divide-(--color-neutral)">
              {companiesPreview.map((company) => (
                <li
                  key={company.id}
                  className="flex items-center justify-between gap-3 py-3"
                >
                  <div>
                    <p className="text-sm font-semibold text-(--color-dark)">
                      {company.name}
                    </p>
                    <p className="text-xs text-zinc-500">
                      {company.sub_user_count} colaborador(es)
                    </p>
                  </div>
                  <Link
                    href={`/private/admin/empresas/${company.id}/dashboard`}
                    className="btn-secondary shrink-0"
                  >
                    Configurar →
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  );
}
