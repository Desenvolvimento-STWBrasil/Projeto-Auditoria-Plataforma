"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import {
  listMessagesAction,
  listMySubUserRequestsAction,
  requestSubUserAction,
  sendMessageAction,
  uploadEvidenceAction,
  type MySubUserRequest,
} from "./actions";
import { AddCollaboratorModal } from "./_components/add-collaborator-modal";
import { StatusKanbanBoard } from "./_components/status-kanban-board";
import {
  ControlDetailModal,
  type DetailTabKey,
} from "./_components/control-detail-modal";
import type { AutorConversa, Controle } from "./_components/types";
import { PageHeader } from "../_components/page-header";
import { StatusSummaryCards } from "../_components/status-summary-cards";
import { evidenceSizeError } from "@/lib/upload-limits";

type ClientDashboardClientProps = {
  initialControles: Controle[];
  role: "admin" | "user" | "sub-user";
  userId: number;
  companyName: string | null;
  initialSubUserRequests: MySubUserRequest[];
};

export function ClientDashboardClient({
  initialControles,
  role,
  userId,
  companyName,
  initialSubUserRequests,
}: ClientDashboardClientProps) {
  const [controles, setControles] = useState<Controle[]>(initialControles);
  /*
   * `null` = nenhum controle aberto, e é assim que a tela carrega. Um
   * card pré-selecionado abriria o modal por cima do quadro em todo
   * carregamento — mesmo raciocínio já aplicado ao modal de card do
   * Admin.
   */
  const [controleSelecionadoId, setControleSelecionadoId] = useState<
    string | null
  >(null);

  const [isLoadingMessages, setIsLoadingMessages] = useState(false);

  const [subUserName, setSubUserName] = useState("");
  const [subUserEmail, setSubUserEmail] = useState("");
  const [subReqMsg, setSubReqMsg] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const [subUserRequests, setSubUserRequests] = useState<MySubUserRequest[]>(
    initialSubUserRequests,
  );
  const [dismissedRequestIds, setDismissedRequestIds] = useState<Set<number>>(
    new Set(),
  );
  const [isPending, startTransition] = useTransition();
  const [isUploading, setIsUploading] = useState(false);
  const [isSendingMsg, setIsSendingMsg] = useState(false);
  const [isAddCollaboratorOpen, setIsAddCollaboratorOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<DetailTabKey>("detalhes");

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
    if (controleSelecionadoId === null) return null;
    return controles.find((c) => c.id === controleSelecionadoId) ?? null;
  }, [controles, controleSelecionadoId]);

  // Busca o histórico de mensagens sob demanda ao ABRIR um controle no
  // modal (mesmo padrão do `<CardDetailModal>` do admin): sem card aberto
  // por padrão, não há mais primeira renderização a pular.
  useEffect(() => {
    if (controleSelecionadoId === null) return;

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

  function abrirControle(id: string) {
    setFileName("");
    setActiveTab("detalhes");
    setControleSelecionadoId(id);
  }

  function anexarEvidencia(file: File) {
    if (!controleSelecionado) return;
    const auditControlId = Number(controleSelecionado.id);

    /* Recusa no navegador o que o servidor recusaria de qualquer jeito
    evita subir o arquivo inteiro só para receber um error */
    const erroTamanho = evidenceSizeError(file);
    if (erroTamanho) {
      window.alert(erroTamanho);
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setIsUploading(true);
    startTransition(async () => {
      try {
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
      } catch {
        window.alert("Não foi possível enviar a evidência. Tente novamente");
      } finally {
        setIsUploading(false);
      }
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
      <div className="container-page space-y-6">
        <PageHeader
          title={companyName ?? "Dashboard do Cliente"}
          description="Acompanhe status, anexe evidências e responda solicitações da auditoria."
          action={
            role === "user" ? (
              <button
                type="button"
                className="btn-primary inline-flex shrink-0 items-center gap-2"
                onClick={() => setIsAddCollaboratorOpen(true)}
              >
                + Adicionar Colaborador
                {visibleSubUserRequests.length > 0 ? (
                  <span
                    aria-label={`${visibleSubUserRequests.length} solicitação(ões) em acompanhamento`}
                    className="rounded-full bg-white/25 px-1.5 py-0.5 text-[10px] font-semibold leading-none"
                  >
                    {visibleSubUserRequests.length}
                  </span>
                ) : null}
              </button>
            ) : undefined
          }
        />

        <StatusSummaryCards
          summary={{
            em_analise: totalEmAnalise,
            parcial: totalParcial,
            conforme: totalConforme,
            naoconforme: totalNaoConforme,
          }}
        />

        {controles.length === 0 ? (
          <div className="card">
            <p className="text-sm text-zinc-700">
              Nenhum controle disponível para exibir no momento.
            </p>
          </div>
        ) : (
          <StatusKanbanBoard
            controles={controles}
            selectedId={controleSelecionadoId}
            onSelectControle={abrirControle}
          />
        )}
      </div>

      {controleSelecionado ? (
        <ControlDetailModal
          controle={controleSelecionado}
          activeTab={activeTab}
          onChangeTab={setActiveTab}
          isLoadingMessages={isLoadingMessages}
          isUploading={isUploading}
          isSendingMsg={isSendingMsg}
          fileName={fileName}
          duvida={duvida}
          onChangeDuvida={setDuvida}
          onUploadEvidence={anexarEvidencia}
          onSendDuvida={enviarDuvida}
          onClose={() => setControleSelecionadoId(null)}
        />
      ) : null}

      {isAddCollaboratorOpen ? (
        <AddCollaboratorModal
          name={subUserName}
          email={subUserEmail}
          onChangeName={setSubUserName}
          onChangeEmail={setSubUserEmail}
          message={subReqMsg}
          onDismissMessage={() => setSubReqMsg(null)}
          isPending={isPending}
          onSubmit={handleRequestSubUser}
          requests={visibleSubUserRequests}
          onDismissRequest={dismissSubUserRequest}
          onClose={() => setIsAddCollaboratorOpen(false)}
        />
      ) : null}
    </main>
  );
}
