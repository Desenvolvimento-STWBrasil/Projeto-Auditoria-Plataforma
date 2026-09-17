"use client";

import { useState, useTransition } from "react";
import {
  approveSubUserRequestAction,
  PendingSubUserRequest,
  rejectSubUserRequestAction,
} from "../../../actions";
import { CompanyAdminDetail } from "../../actions";

type UsuariosClientPropos = {
  company: CompanyAdminDetail;
  initialPendingRequests: PendingSubUserRequest[];
};

export function UsuariosClient({
  company,
  initialPendingRequests,
}: UsuariosClientPropos) {
  const [pendingRequests, setPendingRequests] = useState(
    initialPendingRequests,
  );
  const [busyId, setBusyId] = useState<number | null>(null);
  const [isPending, startTransition] = useTransition();

  function approve(id: number) {
    setBusyId(id);
    startTransition(async () => {
      const result = await approveSubUserRequestAction(id);
      if (result.ok) {
        setPendingRequests((prev) => prev.filter((r) => r.id !== id));
      } else {
        window.alert(result.message);
      }
      setBusyId(null);
    });
  }

  function reject(id: number) {
    if (!window.confirm("Recusar esta solicitação de colaborador")) return;
    setBusyId(id);
    startTransition(async () => {
      const result = await rejectSubUserRequestAction(id);
      if (result.ok) {
        setPendingRequests((prev) => prev.filter((r) => r.id !== id));
      } else {
        window.alert(result.message);
      }
      setBusyId(null);
    });
  }

  return (
    <main className="py-8">
      <div className="container-page space-y-6">
        <section className="card max-w-xl">
          <h2 className="text-base font-semibold text-(--color-dark)">
            Usuário principal
          </h2>
          <p className="mt-2 text-sm">{company.principal_full_name}</p>
          <p className="text-sm text-zinc-500">{company.principal_email}</p>
        </section>

        <section className="card max-w-xl">
          <h2 className="text-base font-semibold text-(--color-dark)">
            Colaboradores ({company.sub_user_count})
          </h2>
          {company.sub_user_emails.length === 0 ? (
            <p className="mt-2 text-sm text-zinc-600">
              Nenhum colaborador aprovado ainda.
            </p>
          ) : (
            <ul className="mt-3 space-y-1 text-sm text-zinc-700">
              {company.sub_user_emails.map((email) => (
                <li key={email}>{email}</li>
              ))}
            </ul>
          )}
        </section>

        <section className="card max-w-xl">
          <h2 className="text-base font-semibold text-(--color-dark)">
            Solicitações pendentes
          </h2>
          {pendingRequests.length === 0 ? (
            <p className="mt-2 text-sm text-zinc-600">
              Nenhuma solicitação pendente para esta empresa.
            </p>
          ) : (
            <ul className="mt-3 space-y-3">
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
                  <div className="mt-3 flex gap-2">
                    <button
                      type="button"
                      className="btn-primary"
                      disabled={isPending && busyId === request.id}
                      onClick={() => approve(request.id)}
                    >
                      {busyId === request.id ? "Aprovando..." : "Aprovar"}
                    </button>
                    <button
                      type="button"
                      className="btn-secondary"
                      disabled={isPending && busyId === request.id}
                      onClick={() => reject(request.id)}
                    >
                      {busyId === request.id ? "Recusando..." : "Recusar"}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  );
}
