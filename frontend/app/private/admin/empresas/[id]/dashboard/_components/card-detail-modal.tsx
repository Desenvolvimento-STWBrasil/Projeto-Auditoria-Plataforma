"use client";

import { useEffect, useRef, useState } from "react";

import { controlStatusBadgeClass, controlStatusLabel } from "@/lib/control-status";
import type {
  CardStatus,
  DashboardCardDetail,
} from "@/app/private/admin/actions";
import type { DashboardCardCategory, DashboardLabel } from "../actions";
import { CardDetailPanel } from "./card-detail-panel";
import { CardEditForm, type CardEditInput } from "./card-edit-form";

type CardDetailModalProps = {
  cardDetail: DashboardCardDetail | null;
  isLoading: boolean;
  isPending: boolean;
  readOnly?: boolean;
  labels?: DashboardLabel[];
  categories?: DashboardCardCategory[];
  onClose: () => void;
  onChangeStatus?: (status: CardStatus) => void;
  onToggleChecklistItem?: (itemId: number) => void;
  onToggleLabel?: (labelId: number) => void;
  onSaveCard?: (input: CardEditInput) => void;
  onAddChecklistItem?: (title: string) => void;
  onDeleteChecklistItem?: (itemId: number) => void;
  onSendMessage?: (content: string) => void;
};

/**
 * Modal de detalhe do card.
 *
 * É uma CASCA em volta do `CardDetailPanel`, não uma segunda
 * implementação dele: o painel continua sendo a fonte única do que um
 * card mostra (status, etiquetas, checklist, histórico, conversa), e é o
 * mesmo componente que /private/client/quadro renderiza. Reescrever o
 * conteúdo aqui faria as duas telas divergirem na primeira mudança —
 * mesma razão já documentada em CA-17 para o `<Board>`.
 *
 * O painel vivia fixo no rodapé da página, a meia tela de distância do
 * card clicado. Com o quadro em linhas a distância piorou (a tira de
 * cards rola na horizontal), e é isso que o modal resolve: o detalhe
 * aparece sobre o card, não embaixo do quadro.
 */
export function CardDetailModal({
  cardDetail,
  isLoading,
  isPending,
  readOnly = false,
  labels = [],
  categories = [],
  onClose,
  onChangeStatus,
  onToggleChecklistItem,
  onToggleLabel,
  onSaveCard,
  onAddChecklistItem,
  onDeleteChecklistItem,
  onSendMessage,
}: CardDetailModalProps) {
  const [isEditing, setIsEditing] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  /*
   * Esc fecha. O ouvinte é de `document` e não do contêiner porque o
   * foco pode estar em qualquer campo de dentro (ou em nenhum, logo após
   * a abertura) — preso ao contêiner, o Esc só funcionaria depois de um
   * clique.
   */
  useEffect(() => {
    function onKeyDown(evento: KeyboardEvent) {
      if (evento.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  // Move o foco para o modal na abertura: sem isso o foco continua no
  // card que ficou atrás do backdrop, e a navegação por teclado segue
  // percorrendo o quadro inteiro por baixo do diálogo.
  useEffect(() => {
    containerRef.current?.focus();
  }, []);

  /*
   * Trocar de card com o modal aberto (setas, ou clique num card de
   * baixo) NÃO deve manter o formulário de edição aberto sobre um card
   * diferente daquele que estava sendo editado.
   */
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsEditing(false);
  }, [cardDetail?.id]);

  const podeEditar = !readOnly && onSaveCard !== undefined;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 py-10"
      // Clique no BACKDROP fecha; clique no conteúdo não. O `target ===
      // currentTarget` é o que separa os dois: sem ele, qualquer clique
      // dentro do modal borbulharia até aqui e fecharia o diálogo no meio
      // da digitação.
      onClick={(evento) => {
        if (evento.target === evento.currentTarget) onClose();
      }}
    >
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-do-card"
        tabIndex={-1}
        className="w-full max-w-3xl rounded-xl bg-(--color-surface) p-5 shadow-xl outline-none"
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2
              id="titulo-do-card"
              className="text-lg font-semibold text-(--color-dark)"
            >
              {cardDetail
                ? `Controle ${cardDetail.control_code ?? "—"} - ${cardDetail.title}`
                : "Carregando card…"}
            </h2>
            {cardDetail?.category_name ? (
              <p className="mt-1 text-xs text-zinc-500">
                Categoria: {cardDetail.category_name}
              </p>
            ) : null}
          </div>

          <div className="flex items-center gap-2">
            {cardDetail ? (
              <span className={controlStatusBadgeClass(cardDetail.status)}>
                {controlStatusLabel(cardDetail.status)}
              </span>
            ) : null}

            {podeEditar && cardDetail && !isEditing ? (
              <button
                type="button"
                className="btn-secondary text-sm"
                onClick={() => setIsEditing(true)}
              >
                Editar
              </button>
            ) : null}

            <button
              type="button"
              className="rounded-lg px-2 py-1 text-lg leading-none text-zinc-500 hover:bg-zinc-200"
              aria-label="Fechar detalhe do card"
              onClick={onClose}
            >
              ×
            </button>
          </div>
        </div>

        <div className="mt-4">
          {isEditing && cardDetail && onSaveCard ? (
            <section className="card">
              <h3 className="text-base font-semibold">Editar card</h3>
              <div className="mt-3">
                <CardEditForm
                  // `key` no id do card: trocar de card precisa
                  // RECONSTRUIR o formulário, senão o `useState` interno
                  // guarda o texto do card anterior e salvar sobrescreve
                  // o card errado.
                  key={cardDetail.id}
                  cardDetail={cardDetail}
                  categories={categories}
                  isPending={isPending}
                  onSave={(input) => {
                    onSaveCard(input);
                    setIsEditing(false);
                  }}
                  onCancel={() => setIsEditing(false)}
                />
              </div>
            </section>
          ) : (
            <CardDetailPanel
              cardDetail={cardDetail}
              isLoading={isLoading}
              isPending={isPending}
              readOnly={readOnly}
              labels={labels}
              onChangeStatus={onChangeStatus}
              onToggleChecklistItem={onToggleChecklistItem}
              onToggleLabel={onToggleLabel}
              onAddChecklistItem={onAddChecklistItem}
              onDeleteChecklistItem={onDeleteChecklistItem}
              onSendMessage={onSendMessage}
            />
          )}
        </div>
      </div>
    </div>
  );
}
