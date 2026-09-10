"use client";

import { useMemo, useState } from "react";

import {
  CONTROL_STATUS_ORDER,
  controlStatusButtonClass,
  controlStatusLabel,
} from "@/lib/control-status";
import { labelChipClass, labelChipStyle, sortLabels } from "@/lib/board-labels";
import { formatarDataHora } from "@/lib/date-format";
import type {
  CardStatus,
  DashboardCardDetail,
} from "@/app/private/admin/actions";
import type { BoardLabelRef, DashboardLabel } from "../actions";

/** Limite de `CardEntryCreateIn.content` no backend. Validar aqui evita
 *  gastar uma ida ao servidor para receber 422 de volta. */
export const CARD_ENTRY_MAX_LENGTH = 1000;

type CardDetailPanelProps = {
  cardDetail: DashboardCardDetail | null;
  isLoading: boolean;
  isPending: boolean;
  readOnly?: boolean;
  labels?: DashboardLabel[];
  onChangeStatus?: (status: CardStatus) => void;
  onToggleChecklistItem?: (itemId: number) => void;
  onToggleLabel?: (labelId: number) => void;
  onAddChecklistItem?: (title: string) => void;
  onDeleteChecklistItem?: (itemId: number) => void;
  /* A conversa é bilateral (B-A28): existe para os dois papéis, e é a
   * única escrita que o `readOnly` NÃO bloqueia. Quem decide o tipo da
   * mensagem (QUESTION/ANSWER) é a action de cada lado, não este
   * componente. */
  onSendMessage?: (content: string) => void;
};

export function CardDetailPanel({
  cardDetail,
  isLoading,
  isPending,
  readOnly = false,
  labels = [],
  onChangeStatus,
  onToggleChecklistItem,
  onToggleLabel,
  onAddChecklistItem,
  onDeleteChecklistItem,
  onSendMessage,
}: CardDetailPanelProps) {
  const [novoItem, setNovoItem] = useState("");
  const [novaMensagem, setNovaMensagem] = useState("");
  const checkListInfo = useMemo(() => {
    if (!cardDetail) return { total: 0, concluidos: 0 };
    const total = cardDetail.checklist.length;
    const concluidos = cardDetail.checklist.filter((i) => i.done).length;
    return { total, concluidos };
  }, [cardDetail]);

  const percentual =
    checkListInfo.total === 0
      ? 0
      : Math.round((checkListInfo.concluidos / checkListInfo.total) * 100);

  const etiquetasDoCard: BoardLabelRef[] = cardDetail?.labels ?? [];
  const idsDoCard = new Set(etiquetasDoCard.map((e) => e.id));

  return (
    <section className="space-y-4">
      <article className="card">
        {/*
          O título e o badge de status NÃO são renderizados aqui: quem os
          mostra é o cabeçalho do `CardDetailModal`, que é também o
          `aria-labelledby` do diálogo. Repeti-los produzia o mesmo texto
          duas vezes na tela e dois nomes acessíveis concorrentes para o
          mesmo card.
        */}
        {isLoading ? (
          <p className="mt-3 text-sm text-zinc-500">Carregando detalhes...</p>
        ) : null}

        {etiquetasDoCard.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-1">
            {sortLabels(etiquetasDoCard).map((etiqueta) => (
              <span
                key={etiqueta.id}
                className={labelChipClass(etiqueta.color)}
                style={labelChipStyle(etiqueta.color)}
              >
                {etiqueta.name}
              </span>
            ))}
          </div>
        ) : null}

        {/*
          A descrição é o texto normativo do controle. Até esta entrega
          ela existia só em `DashboardTemplateCard` e era descartada na
          aplicação do template — o cliente nunca conseguia lê-la (U7).
        */}
        {cardDetail?.description ? (
          <div className="mt-4">
            <p className="mb-1 text-xs font-medium text-zinc-500">
              Descrição do controle
            </p>
            <p className="whitespace-pre-wrap rounded-lg bg-zinc-50 p-3 text-sm text-zinc-700">
              {cardDetail.description}
            </p>
          </div>
        ) : null}

        {!readOnly && onChangeStatus ? (
          <div className="mt-4">
            <p className="mb-2 text-xs font-medium text-zinc-500">
              Status do controle
            </p>
            <div
              role="group"
              aria-label="Status do controle"
              className="flex flex-wrap gap-2"
            >
              {CONTROL_STATUS_ORDER.map((status) => {
                const isActive = cardDetail?.status === status;
                return (
                  <button
                    key={status}
                    type="button"
                    className={controlStatusButtonClass(status, isActive)}
                    aria-pressed={isActive}
                    disabled={!cardDetail || isPending}
                    onClick={() => onChangeStatus(status)}
                  >
                    {controlStatusLabel(status)}
                  </button>
                );
              })}
            </div>
          </div>
        ) : null}

        {!readOnly && onToggleLabel && labels.length > 0 ? (
          <div className="mt-4">
            <p className="mb-2 text-xs font-medium text-zinc-500">
              Etiquetas de criticidade
            </p>
            <div className="flex flex-wrap gap-2">
              {sortLabels(labels).map((etiqueta) => {
                const ativa = idsDoCard.has(etiqueta.id);
                return (
                  <button
                    key={etiqueta.id}
                    type="button"
                    aria-pressed={ativa}
                    disabled={!cardDetail || isPending}
                    className={`${labelChipClass(etiqueta.color)} ${
                      ativa ? "ring-2 ring-(--color-dark)" : "opacity-50"
                    }`}
                    style={labelChipStyle(etiqueta.color)}
                    onClick={() => onToggleLabel(etiqueta.id)}
                  >
                    {etiqueta.name}
                  </button>
                );
              })}
            </div>
          </div>
        ) : null}

      </article>

      {!readOnly ? (
        <article className="card">
          <h3 className="text-base font-semibold">Checklist de conformidade</h3>
          <p className="mt-1 text-sm text-zinc-600">
            {checkListInfo.concluidos} de {checkListInfo.total} itens concluídos
          </p>

          {/* A barra de progresso vive aqui e não mais no topo do painel:
              ela mede o checklist, e media-o a três seções de distância
              dele. */}
          <div className="mt-2 h-2 w-full rounded-full bg-zinc-200">
            <div
              className="h-2 rounded-full bg-green-500 transition-all"
              style={{ width: `${percentual}%` }}
              role="progressbar"
              aria-label="Progresso do checklist"
              aria-valuenow={percentual}
              aria-valuemin={0}
              aria-valuemax={100}
            ></div>
          </div>

          <ul className="mt-3 space-y-2">
            {(cardDetail?.checklist ?? []).map((item) => (
              <li
                key={item.id}
                className="flex items-center gap-2 rounded-lg bg-zinc-50 p-2"
              >
                <input
                  type="checkbox"
                  aria-label={item.title}
                  checked={item.done}
                  disabled={isPending}
                  onChange={() => onToggleChecklistItem?.(item.id)}
                />
                <span
                  className={`flex-1 text-sm ${item.done ? "text-zinc-500 line-through" : ""}`}
                >
                  {item.title}
                </span>
                {onDeleteChecklistItem ? (
                  <button
                    type="button"
                    className="shrink-0 rounded px-1 text-xs text-red-700 hover:bg-red-50 disabled:opacity-40"
                    aria-label={`Remover item ${item.title}`}
                    disabled={isPending}
                    onClick={() => onDeleteChecklistItem(item.id)}
                  >
                    Remover
                  </button>
                ) : null}
              </li>
            ))}
            {(cardDetail?.checklist ?? []).length === 0 ? (
              <li className="text-sm text-zinc-500">
                Nenhum item de checklist ainda.
              </li>
            ) : null}
          </ul>

          {onAddChecklistItem && cardDetail ? (
            <form
              className="mt-3 flex gap-2"
              onSubmit={(evento) => {
                evento.preventDefault();
                const texto = novoItem.trim();
                if (!texto) return;
                onAddChecklistItem(texto);
                setNovoItem("");
              }}
            >
              <input
                className="field text-sm"
                aria-label="Novo item de checklist"
                placeholder="Ex.: Evidência documental apresentada"
                maxLength={CARD_ENTRY_MAX_LENGTH}
                value={novoItem}
                onChange={(e) => setNovoItem(e.target.value)}
              />
              <button
                type="submit"
                className="btn-secondary shrink-0 text-xs"
                disabled={!novoItem.trim() || isPending}
              >
                + Item
              </button>
            </form>
          ) : null}
        </article>
      ) : null}

      {!readOnly ? (
        <article className="card">
          <h3 className="text-base font-semibold">Histórico</h3>
          <p className="mt-1 text-sm text-zinc-600">
            Movimentações do card, da mais antiga para a mais recente.
          </p>
          <ol className="mt-3 space-y-2">
            {(cardDetail?.history ?? []).map((evento, index) => {
              const isUltimo = index === (cardDetail?.history.length ?? 0) - 1;
              return (
                <li
                  key={evento.id}
                  className={`rounded-lg border px-3 py-2 text-sm ${
                    isUltimo
                      ? "border-green-300 bg-green-50"
                      : "border-(--color-neutral)"
                  }`}
                >
                  <p className={isUltimo ? "font-semibold" : ""}>
                    {evento.action}
                  </p>
                  {/*
                    "O que mudou" sem "quando" e "quem" não é histórico de
                    auditoria — e os dois campos já vinham do backend
                    desde E.7, descartados aqui.
                  */}
                  <p className="mt-0.5 text-xs text-zinc-500">
                    {formatarDataHora(evento.created_at)}
                    {evento.actor_user
                      ? ` · ${evento.actor_user.full_name}`
                      : ""}
                  </p>
                </li>
              );
            })}
            {(cardDetail?.history ?? []).length === 0 ? (
              <li className="text-sm text-zinc-500">
                Nenhuma movimentação registrada ainda.
              </li>
            ) : null}
          </ol>
        </article>
      ) : null}

      <article className="card">
        <h3 className="text-base font-semibold">Conversa com o cliente</h3>
        <ul className="mt-3 space-y-2">
          {(cardDetail?.chat ?? []).map((mensagem) => (
            <li
              key={mensagem.id}
              className={`rounded-lg px-3 py-2 text-sm ${
                mensagem.message_type === "QUESTION"
                  ? "bg-zinc-50"
                  : "bg-(--color-primary)/5"
              }`}
            >
              <p className="whitespace-pre-wrap">{mensagem.content}</p>
              <p className="mt-1 text-xs text-zinc-500">
                {mensagem.author_user
                  ? `${mensagem.author_user.full_name} · `
                  : ""}
                {formatarDataHora(mensagem.created_at)}
                {/* QUESTION vem do lado auditado, ANSWER do auditor —
                    a cor de fundo já distinguia os dois, mas cor sozinha
                    não é informação acessível. */}
                {mensagem.message_type === "QUESTION"
                  ? " · pergunta"
                  : " · resposta da auditoria"}
              </p>
            </li>
          ))}
          {(cardDetail?.chat ?? []).length === 0 ? (
            <li className="text-sm text-zinc-500">Nenhuma mensagem ainda.</li>
          ) : null}
        </ul>

        {onSendMessage && cardDetail ? (
          <form
            className="mt-3 space-y-2"
            onSubmit={(evento) => {
              evento.preventDefault();
              const texto = novaMensagem.trim();
              if (!texto) return;
              onSendMessage(texto);
              setNovaMensagem("");
            }}
          >
            <textarea
              className="field min-h-20 text-sm"
              aria-label="Nova mensagem"
              placeholder="Escreva uma mensagem sobre este controle..."
              maxLength={CARD_ENTRY_MAX_LENGTH}
              value={novaMensagem}
              onChange={(e) => setNovaMensagem(e.target.value)}
            />
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs text-zinc-500">
                {novaMensagem.length}/{CARD_ENTRY_MAX_LENGTH}
              </span>
              <button
                type="submit"
                className="btn-primary text-xs"
                disabled={!novaMensagem.trim() || isPending}
              >
                Enviar
              </button>
            </div>
          </form>
        ) : null}
      </article>
    </section>
  );
}
