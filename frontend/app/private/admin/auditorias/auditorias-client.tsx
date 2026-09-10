"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import {
  AuditControlDetail,
  AuditControlStatus,
  AuditDetail,
  AuditListItem,
  AuditStatus,
  getAuditDetailAction,
  markControlMessagesReadAction,
  sendControlMessageAction,
  updateAuditStatusAction,
  updateControlStatusAction,
} from "./actions";
import {
  CONTROL_STATUS_ORDER,
  controlStatusBadgeClass,
  controlStatusLabel,
} from "@/lib/control-status";

function labelStatus(status: AuditStatus) {
  if (status === "DRAFT") return "Rascunho";
  if (status === "ACTIVE") return "Em andamento";
  return "Encerrada";
}

function classStatus(status: AuditStatus) {
  if (status === "DRAFT") return "status-chip bg-zinc-200 text-zinc-800";
  if (status === "ACTIVE") return "status-chip bg-amber-100 text-amber-800";
  return "status-chip bg-green-100 text-green-800";
}

type AuditoriasClientProps = {
  initialAudits: AuditListItem[];
  initialSelectedAuditId: number | null;
  initialDetail: AuditDetail | null;
};

export function AuditoriasClient({
  initialAudits,
  initialSelectedAuditId,
  initialDetail,
}: AuditoriasClientProps) {
  const [audits] = useState<AuditListItem[]>(initialAudits);
  const [selectedAuditId, setSelectedAuditId] = useState<number | null>(
    initialSelectedAuditId,
  );
  const [detail, setDetail] = useState<AuditDetail | null>(initialDetail);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isPending, startTransition] = useTransition();
  const isFirstRender = useRef(true);

  const [expandedControlId, setExpandedControlId] = useState<number | null>(
    null,
  );
  const [messageDraft, setMessageDraft] = useState("");

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }

    if (selectedAuditId === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDetail(null);
      return;
    }

    let cancelado = false;
    setIsLoadingDetail(true);
    getAuditDetailAction(selectedAuditId)
      .then((data) => {
        if (!cancelado) setDetail(data);
      })
      .finally(() => {
        if (!cancelado) setIsLoadingDetail(false);
      });

    return () => {
      cancelado = true;
    };
  }, [selectedAuditId]);

  const pendingControls =
    detail?.controls.filter((c) => c.status === "EM_ANALISE").length ?? 0;

  function handleCloseAudit() {
    if (!detail) return;
    if (
      !window.confirm(
        "Encerrar esta auditoria? Depois de encerrada ela não pode ser reaberta por esta tela",
      )
    ) {
      return;
    }
    startTransition(async () => {
      const result = await updateAuditStatusAction(detail.id, "CLOSED");
      if (result.ok) {
        setDetail(result.detail);
      } else {
        window.alert(result.message);
      }
    });
  }

  function handleUpdateControlStatus(
    controlId: number,
    status: AuditControlStatus,
  ) {
    startTransition(async () => {
      const result = await updateControlStatusAction(controlId, status);
      if (result.ok) {
        setDetail(result.detail);
      } else {
        window.alert(result.message);
      }
    });
  }

  // Marca como lidas as mensagens do cliente ao abrir a conversa de um
  // controle — mesmo padrão já usado em mensagens-client.tsx ao trocar de
  // empresa selecionada.
  useEffect(() => {
    if (expandedControlId === null) return;
    markControlMessagesReadAction(expandedControlId).then(() => {
      setDetail((prev) =>
        prev
          ? {
              ...prev,
              controls: prev.controls.map((control) =>
                control.id === expandedControlId
                  ? {
                      ...control,
                      messages: control.messages.map((message) =>
                        message.is_from_admin
                          ? message
                          : { ...message, read_at: message.read_at ?? "" },
                      ),
                    }
                  : control,
              ),
            }
          : prev,
      );
    });
  }, [expandedControlId]);

  function unreadMessagesCount(control: AuditControlDetail) {
    return control.messages.filter((m) => !m.is_from_admin && !m.read_at)
      .length;
  }

  function toggleConversation(controlId: number) {
    setMessageDraft("");
    setExpandedControlId((prev) => (prev === controlId ? null : controlId));
  }

  function handleSendControlMessage(controlId: number) {
    const content = messageDraft.trim();
    if (!content) return;
    setMessageDraft("");

    startTransition(async () => {
      const result = await sendControlMessageAction(controlId, content);
      if (result.ok) {
        setDetail((prev) =>
          prev
            ? {
                ...prev,
                controls: prev.controls.map((control) =>
                  control.id === controlId
                    ? {
                        ...control,
                        messages: [...control.messages, result.created],
                      }
                    : control,
                ),
              }
            : prev,
        );
      } else {
        window.alert(result.message);
      }
    });
  }

  return (
    <main className="min-h-screen bg-(--color-surface) py-8">
      <div className="container-page space-y-6">
        <header className="card">
          <h1 className="text-2xl font-semibold text-(--color-dark)">
            Gestão de Auditorias
          </h1>
          <p className="mt-1 text-sm text-zinc-600">
            Encerramento formal, evidências e relatório em PDF por auditoria.
          </p>
        </header>

        <div className="grid gap-6 lg:grid-cols-3">
          <section className="space-y-2 lg:col-span-1">
            {audits.length === 0 ? (
              <p className="text-sm text-zinc-600">
                Nenhuma auditoria cadastrada ainda.
              </p>
            ) : (
              audits.map((audit) => (
                <button
                  key={audit.id}
                  type="button"
                  onClick={() => setSelectedAuditId(audit.id)}
                  className={`card w-full text-left transition ${
                    audit.id === selectedAuditId
                      ? "ring-2 ring-(--color-primary)"
                      : ""
                  }`}
                >
                  <h2 className="text-sm font-semibold">{audit.name}</h2>
                  <span className={`mt-2 inline-block ${classStatus(audit.status)}`}>
                    {labelStatus(audit.status)}
                  </span>
                </button>
              ))
            )}
          </section>

          <section className="space-y-4 lg:col-span-2">
            <article className="card">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h3 className="text-lg font-semibold">
                  {detail ? detail.name : "Nenhuma auditoria selecionada"}
                </h3>
                <span className={classStatus(detail?.status ?? "DRAFT")}>
                  {detail ? labelStatus(detail.status) : "Sem status"}
                </span>
              </div>

              {detail ? (
                <p className="mt-1 text-sm text-zinc-600">
                  Cliente: {detail.client_name}
                </p>
              ) : null}

              {isLoadingDetail ? (
                <p className="mt-3 text-sm text-zinc-500">
                  Carregando detalhes...
                </p>
              ) : null}

              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  className="btn-primary"
                  disabled={
                    !detail ||
                    detail.status === "CLOSED" ||
                    pendingControls > 0 ||
                    isPending
                  }
                  onClick={handleCloseAudit}
                >
                  {detail?.status === "CLOSED"
                    ? "Auditoria encerrada"
                    : "Encerrar auditoria"}
                </button>

                {detail && detail.status === "CLOSED" ? (
                  <a
                    className="btn-secondary"
                    href={`/api/admin/audits/${detail.id}/report`}
                  >
                    Baixar relatório PDF
                  </a>
                ) : null}
              </div>

              {detail && pendingControls > 0 && detail.status !== "CLOSED" ? (
                <p className="mt-2 text-xs text-amber-700">
                  {pendingControls} controle(s) ainda em análise — encerre todos
                  antes de fechar a auditoria.
                </p>
              ) : null}
            </article>

            <article className="card">
              <h3 className="text-base font-semibold">
                Controles e evidências
              </h3>
              <ul className="mt-3 space-y-3">
                {(detail?.controls ?? []).map((control) => (
                  <li
                    key={control.id}
                    className="rounded-lg border border-(--color-neutral) p-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm font-semibold">
                        {control.control_code} — {control.control_title}
                      </p>
                      <div className="flex items-center gap-2">
                        <span className={controlStatusBadgeClass(control.status)}>
                          {controlStatusLabel(control.status)}
                        </span>
                        <select
                          className="rounded-lg border border-(--color-neutral) bg-white px-2 py-1 text-xs"
                          value={control.status}
                          disabled={detail?.status === "CLOSED" || isPending}
                          onChange={(e) =>
                            handleUpdateControlStatus(
                              control.id,
                              e.target.value as AuditControlStatus,
                            )
                          }
                        >
                          {CONTROL_STATUS_ORDER.map((status) => (
                            <option key={status} value={status}>
                              {controlStatusLabel(status)}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    {control.evidences.length === 0 ? (
                      <p className="mt-2 text-xs text-zinc-500">
                        Nenhuma evidência anexada.
                      </p>
                    ) : (
                      <ul className="mt-2 space-y-1">
                        {control.evidences.map((evidence) => (
                          <li
                            key={evidence.id}
                            className="flex items-center justify-between text-xs"
                          >
                            <span>
                              {evidence.file_name} — enviado por{" "}
                              {evidence.uploaded_by_name}
                            </span>
                            <a
                              className="text-(--color-primary) underline"
                              href={`/api/admin/evidences/${evidence.id}/download`}
                            >
                              Baixar
                            </a>
                          </li>
                        ))}
                      </ul>
                    )}

                    <div className="mt-3 border-t border-(--color-neutral) pt-3">
                      <button
                        type="button"
                        className="flex items-center gap-2 text-xs font-medium text-(--color-primary)"
                        onClick={() => toggleConversation(control.id)}
                      >
                        {expandedControlId === control.id
                          ? "Ocultar conversa"
                          : "Conversa / Dúvidas"}
                        {unreadMessagesCount(control) > 0 ? (
                          <span className="rounded-full bg-(--color-primary) px-2 py-0.5 text-[10px] font-semibold text-white">
                            {unreadMessagesCount(control)}
                          </span>
                        ) : null}
                      </button>

                      {expandedControlId === control.id ? (
                        <div className="mt-3 space-y-2">
                          {control.messages.length === 0 ? (
                            <p className="text-xs text-zinc-500">
                              Nenhuma mensagem ainda.
                            </p>
                          ) : (
                            control.messages.map((message) => (
                              <div
                                key={message.id}
                                className={`max-w-[85%] rounded-lg px-3 py-2 text-xs ${
                                  message.is_from_admin
                                    ? "ml-auto bg-(--color-primary) text-white"
                                    : "bg-zinc-100 text-(--color-dark)"
                                }`}
                              >
                                <p className="opacity-70">
                                  {message.author_full_name}
                                </p>
                                <p>{message.content}</p>
                              </div>
                            ))
                          )}

                          <div className="flex gap-2 pt-1">
                            <input
                              className="field flex-1 text-xs"
                              placeholder="Responder ao cliente..."
                              value={messageDraft}
                              disabled={isPending}
                              onChange={(e) => setMessageDraft(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") {
                                  handleSendControlMessage(control.id);
                                }
                              }}
                            />
                            <button
                              type="button"
                              className="btn-primary"
                              disabled={isPending || !messageDraft.trim()}
                              onClick={() =>
                                handleSendControlMessage(control.id)
                              }
                            >
                              Enviar
                            </button>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            </article>
          </section>
        </div>
      </div>
    </main>
  );
}
