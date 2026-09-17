"use client";

import { ModalShell } from "@/app/private/_components/modal-shell";
import type { MySubUserRequest } from "../actions";

type AddCollaboratorModalProps = {
  name: string;
  email: string;
  onChangeName: (value: string) => void;
  onChangeEmail: (value: string) => void;
  message: { type: "success" | "error"; text: string } | null;
  onDismissMessage: () => void;
  isPending: boolean;
  onSubmit: () => void;
  requests: MySubUserRequest[];
  onDismissRequest: (id: number) => void;
  onClose: () => void;
};

export function AddCollaboratorModal({
  name,
  email,
  onChangeName,
  onChangeEmail,
  message,
  onDismissMessage,
  isPending,
  onSubmit,
  requests,
  onDismissRequest,
  onClose,
}: AddCollaboratorModalProps) {
  return (
    <ModalShell
      title="Adicionar Colaborador"
      onClose={onClose}
      maxWidthClass="max-w-lg"
    >
      <p className="mt-2 text-sm text-zinc-600">
        O admin aprovará a solicitação. A senha será enviada por e-mail ao
        colaborador.
      </p>

      <div className="mt-4 grid gap-3">
        <input
          className="field"
          placeholder="Nome completo do colaborador"
          value={name}
          onChange={(e) => onChangeName(e.target.value)}
        />
        <input
          className="field"
          type="email"
          placeholder="E-mail do colaborador"
          value={email}
          onChange={(e) => onChangeEmail(e.target.value)}
        />
        <button
          type="button"
          className="btn-primary"
          disabled={isPending}
          onClick={onSubmit}
        >
          {isPending ? "Enviando..." : "Solicitar criação de colaborador"}
        </button>
      </div>

      {message ? (
        <div
          className={`mt-4 flex items-start justify-between gap-3 rounded-lg border p-3 text-sm ${
            message.type === "success"
              ? "border-green-300 bg-green-50 text-green-800"
              : "border-red-200 bg-red-50 text-red-700"
          }`}
        >
          <p>{message.text}</p>
          <button
            type="button"
            aria-label="Fechar mensagem"
            className="shrink-0 text-lg leading-none opacity-60 transition hover:opacity-100"
            onClick={onDismissMessage}
          >
            ×
          </button>
        </div>
      ) : null}

      {requests.length > 0 ? (
        <ul className="mt-5 max-h-64 space-y-3 overflow-y-auto pr-1">
          {requests.map((request) => (
            <li
              key={request.id}
              className={`flex items-start justify-between gap-3 rounded-lg border p-3 text-sm ${
                request.status === "REJECTED"
                  ? "border-red-200 bg-red-50"
                  : "border-zinc-200"
              }`}
            >
              <div>
                <p className="font-semibold text-(--color-dark)">
                  {request.requested_full_name} ({request.request_email})
                </p>
                {request.status === "REJECTED" ? (
                  <p className="mt-1 text-red-700">
                    Solicitação recusada pelo administrador.
                  </p>
                ) : request.status === "APPROVED" ? (
                  <p className="mt-1 text-zinc-600">Solicitação aprovada.</p>
                ) : (
                  <p className="mt-1 text-zinc-600">
                    Aguardando análise do administrador.
                  </p>
                )}
              </div>
              <button
                type="button"
                aria-label="Fechar aviso"
                className="shrink-0 text-lg leading-none opacity-60 transition hover:opacity-100"
                onClick={() => onDismissRequest(request.id)}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </ModalShell>
  );
}
