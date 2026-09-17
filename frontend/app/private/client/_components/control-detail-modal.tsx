"use client";

import { ModalShell } from "@/app/private/_components/modal-shell";
import { controlStatusBadgeClass, controlStatusLabel } from "@/lib/control-status";
import { tabItemClass } from "@/lib/tab-styles";
import type { Controle } from "./types";

export const DETAIL_TABS = [
  { key: "detalhes", label: "Detalhes" },
  { key: "evidencias", label: "Evidências" },
  { key: "conversa", label: "Conversa" },
] as const;
export type DetailTabKey = (typeof DETAIL_TABS)[number]["key"];

type ControlDetailModalProps = {
  controle: Controle;
  activeTab: DetailTabKey;
  onChangeTab: (tab: DetailTabKey) => void;
  isLoadingMessages: boolean;
  isUploading: boolean;
  isSendingMsg: boolean;
  fileName: string;
  duvida: string;
  onChangeDuvida: (value: string) => void;
  onUploadEvidence: (file: File) => void;
  onSendDuvida: () => void;
  onClose: () => void;
};

export function ControlDetailModal({
  controle,
  activeTab,
  onChangeTab,
  isLoadingMessages,
  isUploading,
  isSendingMsg,
  fileName,
  duvida,
  onChangeDuvida,
  onUploadEvidence,
  onSendDuvida,
  onClose,
}: ControlDetailModalProps) {
  return (
    <ModalShell
      title={`Controle ${controle.codigo} - ${controle.titulo}`}
      onClose={onClose}
      maxWidthClass="max-w-2xl"
    >
      <span className={`mt-1 inline-block ${controlStatusBadgeClass(controle.status)}`}>
        {controlStatusLabel(controle.status)}
      </span>

      <nav
        aria-label="Detalhes do controle"
        className="mt-4 flex gap-1 overflow-x-auto border-b border-(--color-neutral)"
      >
        {DETAIL_TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => onChangeTab(tab.key)}
            aria-current={activeTab === tab.key ? "page" : undefined}
            className={tabItemClass(activeTab === tab.key)}
          >
            {tab.label}
            {tab.key === "conversa" && controle.conversa.length > 0 ? (
              <span className="ml-1.5 rounded-full bg-zinc-200 px-1.5 py-0.5 text-[10px] font-semibold leading-none text-zinc-700">
                {controle.conversa.length}
              </span>
            ) : null}
          </button>
        ))}
      </nav>

      <div className="mt-4">
        {activeTab === "detalhes" ? (
          <div>
            <p className="text-sm text-zinc-700">{controle.descricao}</p>
            <div className="mt-4 rounded-xl bg-zinc-50 p-3 text-sm">
              <p className="font-semibold">Evidência esperada:</p>
              <p className="text-zinc-700">{controle.evidenciaEsperada}</p>
            </div>
          </div>
        ) : null}

        {activeTab === "evidencias" ? (
          <div>
            <div className="flex items-center justify-between">
              <label className="btn-secondary text-sm cursor-pointer">
                {isUploading ? "Enviando..." : "+ Anexar evidência"}
                <input
                  type="file"
                  className="hidden"
                  disabled={isUploading}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) onUploadEvidence(file);
                  }}
                />
              </label>
              {fileName && <p className="text-sm mt-2">Arquivo: {fileName}</p>}
            </div>
            <ul className="mt-3 space-y-2 text-sm">
              {controle.evidencias.map((arquivo) => (
                <li
                  key={arquivo}
                  className="rounded-lg border border-(--color-neutral) px-3 py-2"
                >
                  {arquivo}
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-zinc-500">
              Formatos permitidos: PDF / PNG / JPG / JPEG / WEBP / DOCX / XLSX |
              Tamanho máximo: 10MB
            </p>
          </div>
        ) : null}

        {activeTab === "conversa" ? (
          <div>
            {isLoadingMessages ? (
              <p className="text-sm text-zinc-500">Carregando mensagens...</p>
            ) : null}

            <div className="max-h-96 space-y-2 overflow-y-auto pr-1">
              {controle.conversa.map((item, index) => (
                <div
                  key={`${item.autor}-${index}`}
                  className={`rounded-lg p-3 text-sm ${
                    item.autor === "CLIENTE" ? "bg-blue-50 text-right" : "bg-zinc-50"
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
                onChange={(e) => onChangeDuvida(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") onSendDuvida();
                }}
              />
              <button
                type="button"
                className="btn-primary"
                disabled={isSendingMsg}
                onClick={onSendDuvida}
              >
                {isSendingMsg ? "Enviando..." : "Enviar"}
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </ModalShell>
  );
}
