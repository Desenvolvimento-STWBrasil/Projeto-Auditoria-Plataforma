"use client";

import { useEffect, useMemo, useRef, useState, useTransition } from "react";
import {
  listMessagesAction,
  listMySubUserRequestsAction,
  requestSubUserAction,
  sendMessageAction,
  uploadEvidenceAction,
  type MySubUserRequest,
} from "./actions";
import {
  controlStatusAccentClass,
  controlStatusBadgeClass,
  controlStatusLabel,
  type ControlStatus,
} from "@/lib/control-status";

type StatusControle = ControlStatus;
type AutorConversa = "AUDITORIA" | "CLIENTE";

type Controle = {
  id: string;
  codigo: string;
  titulo: string;
  descricao: string;
  evidenciaEsperada: string;
  status: StatusControle;
  evidencias: string[];
  conversa: { autor: AutorConversa; mensagem: string }[];
};

const statusLabel = controlStatusLabel;
const statusClass = controlStatusBadgeClass;

type ClientDashboardClientProps = {
  initialControles: Controle[];
  role: "admin" | "user" | "sub-user";
  userId: number;
  initialSubUserRequests: MySubUserRequest[];
};

export function ClientDashboardClient({
  initialControles,
  role,
  userId,
  initialSubUserRequests,
}: ClientDashboardClientProps) {
  const [controles, setControles] = useState<Controle[]>(initialControles);
  const [controleSelecionadoId, setControleSelecionadoId] = useState<string>(
    initialControles[0]?.id ?? "",
  );

  const isFirstRender = useRef(true);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);

  const [subUserName, setSubUserName] = useState("");
  const [subUserEmail, setSubUserEmail] = useState("");
  const [subReqMsg, setSubReqMsg] = useState<
    { type: "success" | "error"; text: string } | null
  >(null);
  const [subUserRequests, setSubUserRequests] = useState<MySubUserRequest[]>(
    initialSubUserRequests,
  );
  const [dismissedRequestIds, setDismissedRequestIds] = useState<Set<number>>(
    new Set(),
  );
  const [isPending, startTransition] = useTransition();
  const [isUploading, setIsUploading] = useState(false);
  const [isSendingMsg, setIsSendingMsg] = useState(false);

  const [fileName, setFileName] = useState<string>("");
  const [duvida, setDuvida] = useState("");

  const { totalEmAnalise, totalParcial, totalConforme, totalNaoConforme } =
    useMemo(() => {
      const acc = {
        totalEmAnalise: 0,
        totalParcial: 0,
        totalConforme: 0,
        totalNaoConforme: 0,
      };
      for (const c of controles) {
        if (c.status === "EM_ANALISE") acc.totalEmAnalise += 1;
        else if (c.status === "PARCIAL") acc.totalParcial += 1;
        else if (c.status === "NAOCONFORME") acc.totalNaoConforme += 1;
        else acc.totalConforme += 1;
      }
      return acc;
    }, [controles]);

  const controleSelecionado = useMemo(() => {
    if (!controles.length) return null;
    return (
      controles.find((c) => c.id === controleSelecionadoId) ?? controles[0]
    );
  }, [controles, controleSelecionadoId]);

  // Busca o histórico de mensagens sob demanda ao trocar de controle
  // selecionado — pula a primeira renderização, pois o histórico do
  // controle inicial já veio pronto via props (ver page.tsx), sem
  // nenhum fetch no cliente na carga inicial da página.
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    if (!controleSelecionadoId) return;

    let cancelado = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsLoadingMessages(true);
    listMessagesAction(Number(controleSelecionadoId))
      .then((messages) => {
        if (cancelado) return;
        setControles((prev) =>
          prev.map((c) =>
            c.id === controleSelecionadoId
              ? {
                  ...c,
                  conversa: messages.map((m) => ({
                    autor: (m.author_id === userId
                      ? "CLIENTE"
                      : "AUDITORIA") as AutorConversa,
                    mensagem: m.content,
                  })),
                }
              : c,
          ),
        );
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelado) setIsLoadingMessages(false);
      });

    return () => {
      cancelado = true;
    };
  }, [controleSelecionadoId, userId]);

  function anexarEvidencia(file: File) {
    if (!controleSelecionado) return;
    const auditControlId = Number(controleSelecionado.id);

    const formData = new FormData();
    formData.append("file", file);

    setIsUploading(true);
    startTransition(async () => {
      const result = await uploadEvidenceAction(auditControlId, formData);
      if (result.ok) {
        setFileName(result.fileName);
        setControles((prev) =>
          prev.map((c) =>
            c.id === controleSelecionadoId
              ? { ...c, evidencias: [...c.evidencias, result.fileName] }
              : c,
          ),
        );
      } else {
        window.alert(result.message);
      }
      setIsUploading(false);
    });
  }

  function enviarDuvida() {
    const msg = duvida.trim();
    if (!msg || !controleSelecionadoId) return;
    const auditControlId = Number(controleSelecionadoId);

    setIsSendingMsg(true);
    startTransition(async () => {
      const result = await sendMessageAction(auditControlId, msg);
      if (result.ok) {
        setControles((prev) =>
          prev.map((c) =>
            c.id === controleSelecionadoId
              ? {
                  ...c,
                  conversa: [
                    ...c.conversa,
                    { autor: "CLIENTE", mensagem: result.content },
                  ],
                }
              : c,
          ),
        );
        setDuvida("");
      } else {
        window.alert(result.message);
      }
      setIsSendingMsg(false);
    });
  }

  function handleRequestSubUser() {
    setSubReqMsg(null);
    startTransition(async () => {
      const result = await requestSubUserAction({
        requested_full_name: subUserName,
        request_email: subUserEmail,
      });

      if (!result.ok) {
        setSubReqMsg({ type: "error", text: result.message });
        return;
      }
      setSubReqMsg({
        type: "success",
        text: "Solicitação enviada com sucesso.",
      });
      setSubUserName("");
      setSubUserEmail("");
      listMySubUserRequestsAction()
        .then(setSubUserRequests)
        .catch(() => {});
    });
  }

  const visibleSubUserRequests = useMemo(
    () => subUserRequests.filter((r) => !dismissedRequestIds.has(r.id)),
    [subUserRequests, dismissedRequestIds],
  );

  function dismissSubUserRequest(id: number) {
    setDismissedRequestIds((prev) => new Set(prev).add(id));
  }

  return (
    <main className="min-h-screen bg-(--color-surface) py-8">
      <div className="container-page">
        <header className="mb-6 card">
          <h1 className="text-2xl font-semibold text-(--color-dark)">
            Dashboard do Cliente
          </h1>
          <p className="mt-1 text-sm text-zinc-600">
            Acompanhe status, anexe evidências e responda solicitações da
            auditoria.
          </p>
        </header>

        <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="card text-center">
            <p className="text-xs text-zinc-500 italic">Em análise</p>
            <p
              className={`text-2xl font-bold ${controlStatusAccentClass("EM_ANALISE")}`}
            >
              {totalEmAnalise}
            </p>
          </div>

          <div className="card text-center">
            <p className="text-xs text-zinc-500 italic">Parcial</p>
            <p
              className={`text-2xl font-bold ${controlStatusAccentClass("PARCIAL")}`}
            >
              {totalParcial}
            </p>
          </div>

          <div className="card text-center">
            <p className="text-xs text-zinc-500 italic">Conforme</p>
            <p
              className={`text-2xl font-bold ${controlStatusAccentClass("CONFORME")}`}
            >
              {totalConforme}
            </p>
          </div>

          <div className="card text-center">
            <p className="text-xs text-zinc-500 italic">Não conforme</p>
            <p
              className={`text-2xl font-bold ${controlStatusAccentClass("NAOCONFORME")}`}
            >
              {totalNaoConforme}
            </p>
          </div>
        </div>

        {!controleSelecionado ? (
          <div className="card">
            <p className="text-sm text-zinc-700">
              Nenhum controle disponível para exibir no momento.
            </p>
          </div>
        ) : (
          <div className="grid gap-6 lg:grid-cols-3">
            <section className="space-y-4 lg:col-span-1">
              {controles.map((controle) => (
                <button
                  key={controle.id}
                  type="button"
                  onClick={() => {
                    setFileName("");
                    setControleSelecionadoId(controle.id);
                  }}
                  className={`card w-full text-left transition ${
                    controle.id === controleSelecionadoId
                      ? "ring-2 ring-(--color-primary)"
                      : ""
                  }`}
                >
                  <p className="text-xs font-semibold text-zinc-500">
                    Controle {controle.codigo}
                  </p>
                  <h2 className="mt-1 text-sm font-semibold">
                    {controle.titulo}
                  </h2>
                  <span
                    className={`mt-3 inline-block ${statusClass(controle.status)}`}
                  >
                    {statusLabel(controle.status)}
                  </span>
                </button>
              ))}
            </section>

            <section className="space-y-4 lg:col-span-2">
              <article className="card">
                <h3 className="text-lg font-semibold">
                  Controle {controleSelecionado.codigo} -{" "}
                  {controleSelecionado.titulo}
                </h3>
                <p className="mt-3 text-sm text-zinc-700">
                  {controleSelecionado.descricao}
                </p>
                <div className="mt-4 rounded-xl bg-zinc-50 p-3 text-sm">
                  <p className="font-semibold">Evidência esperada:</p>
                  <p className="text-zinc-700">
                    {controleSelecionado.evidenciaEsperada}
                  </p>
                </div>
              </article>
              <article className="card">
                <div className="flex items-center justify-between">
                  <label className="btn-secondary text-sm cursor-pointer">
                    {isUploading ? "Enviando..." : "+ Anexar evidência"}
                    <input
                      type="file"
                      className="hidden"
                      disabled={isUploading}
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) anexarEvidencia(file);
                      }}
                    />
                  </label>
                  {fileName && (
                    <p className="text-sm mt-2">Arquivo: {fileName}</p>
                  )}
                </div>
                <ul className="mt-3 space-y-2 text-sm">
                  {controleSelecionado.evidencias.map((arquivo) => (
                    <li
                      key={arquivo}
                      className="rounded-lg border border-(--color-neutral) px-3 py-2"
                    >
                      {arquivo}
                    </li>
                  ))}
                </ul>
                <p className="mt-3 text-xs text-zinc-500">
                  Formatos permitidos: PDF / PNG / JPG / JPEG / WEBP / DOCX /
                  XLSX | Tamanho máximo: 10MB
                </p>
              </article>
              <article className="card">
                <h3 className="text-base font-semibold">Conversa / Dúvidas</h3>

                {isLoadingMessages ? (
                  <p className="mt-3 text-sm text-zinc-500">
                    Carregando mensagens...
                  </p>
                ) : null}

                <div className="mt-3 space-y-2">
                  {controleSelecionado.conversa.map((item, index) => (
                    <div
                      key={`${item.autor}-${index}`}
                      className={`rounded-lg p-3 text-sm ${
                        item.autor === "CLIENTE"
                          ? "bg-blue-50 text-right"
                          : "bg-zinc-50"
                      }`}
                    >
                      <p className="font-semibold">
                        {item.autor === "AUDITORIA" ? "Auditoria" : "Você"}
                      </p>
                      <p className="text-zinc-700">{item.mensagem}</p>
                    </div>
                  ))}
                </div>

                <div className="mt-4 flex gap-2">
                  <input
                    className="field"
                    placeholder="Digite sua dúvida ou resposta..."
                    value={duvida}
                    disabled={isSendingMsg}
                    onChange={(e) => setDuvida(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") enviarDuvida();
                    }}
                  />
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={isSendingMsg}
                    onClick={enviarDuvida}
                  >
                    {isSendingMsg ? "Enviando..." : "Enviar"}
                  </button>
                </div>
              </article>
            </section>
          </div>
        )}
        {role === "user" ? (
          <article className="card mt-6">
            <h3 className="text-base font-semibold">Solicitar Sub-usuário</h3>
            <p className="mt-1 text-sm text-zinc-600">
              O admin aprovará a solicitação. A senha será enviada por e-mail ao
              sub-usuário.
            </p>

            <div className="mt-4 grid gap-3">
              <input
                className="field"
                placeholder="Nome completo do sub-usuário"
                value={subUserName}
                onChange={(e) => setSubUserName(e.target.value)}
              />
              <input
                className="field"
                type="email"
                placeholder="E-mail do sub-usuário"
                value={subUserEmail}
                onChange={(e) => setSubUserEmail(e.target.value)}
              />
              <button
                type="button"
                className="btn-primary"
                disabled={isPending}
                onClick={handleRequestSubUser}
              >
                {isPending ? "Enviando..." : "Solicitar criação de sub-usuário"}
              </button>
            </div>

            {subReqMsg ? (
              <div
                className={`mt-4 flex items-start justify-between gap-3 rounded-lg border p-3 text-sm ${
                  subReqMsg.type === "success"
                    ? "border-green-300 bg-green-50 text-green-800"
                    : "border-red-200 bg-red-50 text-red-700"
                }`}
              >
                <p>{subReqMsg.text}</p>
                <button
                  type="button"
                  aria-label="Fechar mensagem"
                  className="shrink-0 text-lg leading-none opacity-60 transition hover:opacity-100"
                  onClick={() => setSubReqMsg(null)}
                >
                  ×
                </button>
              </div>
            ) : null}

            {visibleSubUserRequests.length > 0 ? (
              <ul className="mt-5 space-y-3">
                {visibleSubUserRequests.map((request) => (
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
                        <p className="mt-1 text-zinc-600">
                          Solicitação aprovada.
                        </p>
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
                      onClick={() => dismissSubUserRequest(request.id)}
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </article>
        ) : null}
      </div>
    </main>
  );
}
