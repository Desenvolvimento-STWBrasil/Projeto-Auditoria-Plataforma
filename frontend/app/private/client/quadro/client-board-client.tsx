"use client";

import { useEffect, useState, useTransition } from "react";

import { Board } from "../../admin/empresas/[id]/dashboard/_components/board";
import { CardDetailModal } from "../../admin/empresas/[id]/dashboard/_components/card-detail-modal";
import { Board as BoardData } from "../../admin/empresas/[id]/dashboard/actions";
import { DashboardCardDetail } from "../../admin/actions";
import { getCardDetailAction, sendCardQuestionAction } from "./actions";

type ClientBoardClientProps = {
  companyName: string;
  board: BoardData;
};

/*
 * Mesmo `<Board>` do admin, em modo leitura (CA-17).
 *
 * Reusar o componente — em vez de escrever uma versão "só de leitura" —
 * é o que garante que o cliente veja as colunas na MESMA ordem que o
 * auditor montou. Duas implementações divergiriam na primeira mudança de
 * ordenação, e a divergência apareceria numa reunião com o cliente, não
 * num teste.
 *
 * O mesmo vale para o `<CardDetailModal>`: a casca é compartilhada e o
 * `readOnly` é que decide o que o cliente pode fazer lá dentro. O modal
 * em modo leitura não recebe `onSaveCard`, então nem o botão "Editar"
 * existe para ele.
 */
export function ClientBoardClient({
  companyName,
  board,
}: ClientBoardClientProps) {
  const [cardSelecionadoId, setCardSelecionadoId] = useState<number | null>(
    null,
  );
  const [cardDetail, setCardDetail] = useState<DashboardCardDetail | null>(
    null,
  );
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [isPending, startTransition] = useTransition();

  /*
   * O accordion do quadro em linhas vale para o cliente também: sem
   * estado nenhum aqui, `collapsedColumns?.has(...) ?? false` deixaria
   * TODAS as faixas abertas e a tela do cliente voltaria a despejar os
   * cards de uma vez — exatamente o que o admin deixou de ter.
   */
  const [collapsedColumns, setCollapsedColumns] = useState<Set<number>>(
    () => new Set(board.columns.map((coluna) => coluna.id)),
  );

  function toggleColumnCollapse(columnId: number) {
    setCollapsedColumns((prev) => {
      const next = new Set(prev);
      if (next.has(columnId)) next.delete(columnId);
      else next.add(columnId);
      return next;
    });
  }

  useEffect(() => {
    if (cardSelecionadoId === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setCardDetail(null);
      return;
    }

    let cancelado = false;
    setIsLoadingDetail(true);
    getCardDetailAction(cardSelecionadoId)
      .then((detail) => {
        if (!cancelado) setCardDetail(detail);
      })
      .catch(() => {
        if (!cancelado) setCardDetail(null);
      })
      .finally(() => {
        if (!cancelado) setIsLoadingDetail(false);
      });

    return () => {
      cancelado = true;
    };
  }, [cardSelecionadoId]);

  /*
   * Pergunta do cliente sobre o card.
   *
   * Recarrega o detalhe em seguida em vez de acrescentar a mensagem em
   * memória: `id` e `created_at` são do servidor, e inventá-los aqui
   * criaria uma mensagem que desaparece no próximo carregamento.
   */
  function enviarPergunta(content: string) {
    if (cardSelecionadoId === null) return;
    const cardId = cardSelecionadoId;
    setFeedback("");
    startTransition(async () => {
      const result = await sendCardQuestionAction(cardId, content);
      if (!result.ok) {
        setFeedback(result.message);
        return;
      }
      const fresco = await getCardDetailAction(cardId).catch(() => null);
      if (fresco) setCardDetail(fresco);
    });
  }

  const totalDeCards =
    board.columns.reduce((soma, coluna) => soma + coluna.cards.length, 0) +
    board.uncolumned.length;

  return (
    <main className="min-h-screen bg-(--color-surface) py-8">
      <div className="container-page space-y-6">
        <header className="card">
          <h1 className="text-2xl font-semibold text-(--color-dark)">
            Quadro de {companyName}
          </h1>
          <p className="mt-1 text-sm text-zinc-600">
            {board.columns.length} seção(ões) · {totalDeCards} controle(s).
            Este é o andamento da due diligence como a equipe de auditoria o
            organizou. Clique numa seção para abri-la e num card para ler a
            descrição do controle e conversar sobre ele.
          </p>
          {feedback ? (
            <p
              role="status"
              className="mt-3 rounded-lg bg-zinc-50 p-2 text-sm text-zinc-700"
            >
              {feedback}
            </p>
          ) : null}
        </header>

        {totalDeCards === 0 ? (
          <section className="card">
            <p className="text-sm text-zinc-600">
              A equipe de auditoria ainda não montou o quadro da sua empresa.
            </p>
          </section>
        ) : (
          <Board
            board={board}
            readOnly
            selectedCardId={cardSelecionadoId}
            onSelectCard={setCardSelecionadoId}
            collapsedColumns={collapsedColumns}
            onToggleColumnCollapse={toggleColumnCollapse}
          />
        )}
      </div>

      {cardSelecionadoId !== null ? (
        <CardDetailModal
          cardDetail={cardDetail}
          isLoading={isLoadingDetail}
          isPending={isPending}
          readOnly
          onClose={() => setCardSelecionadoId(null)}
          onSendMessage={enviarPergunta}
        />
      ) : null}
    </main>
  );
}
