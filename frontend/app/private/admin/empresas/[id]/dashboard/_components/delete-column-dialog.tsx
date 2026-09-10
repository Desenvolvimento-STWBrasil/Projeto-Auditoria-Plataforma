"use client";

import { useState } from "react";

import type {
  Board as BoardData,
  BoardColumn as BoardColumnData,
} from "../actions";

type DeleteColumnDialogProps = {
  column: BoardColumnData;
  board: BoardData;
  isPending: boolean;
  onCancel: () => void;
  /** Move os cards visíveis para `destinoId` e SÓ ENTÃO exclui. */
  onRelocateAndDelete: (destinoId: number) => void;
  onDelete: () => void;
};

/**
 * Confirmação de exclusão de coluna ou seção.
 *
 * Substitui um `window.confirm` que dizia "os cards NÃO são apagados"
 * e nada mais. A frase era verdadeira e insuficiente: ela não dizia
 * QUANTOS cards estavam em jogo, não avisava que o backend recusaria a
 * exclusão por causa deles (409 `ColumnNotEmptyError`), e não oferecia
 * nada para resolver — o admin descobria o problema só depois de
 * confirmar, e tinha de ir mover os cards à mão, um por um.
 *
 * A regra de negócio NÃO mudou, e é a mais segura das três possíveis:
 * exclusão bloqueada enquanto houver card visível. O que mudou é que
 * agora a tela declara a regra ANTES e oferece o passo que falta —
 * realocar os cards — reaproveitando o `set_column` em lote que já
 * existia para a barra de seleção.
 */
export function DeleteColumnDialog({
  column,
  board,
  isPending,
  onCancel,
  onRelocateAndDelete,
  onDelete,
}: DeleteColumnDialogProps) {
  const [destino, setDestino] = useState<number | "">("");

  /*
   * A contagem que importa é a de cards VISÍVEIS, porque é exatamente
   * essa que o backend usa para recusar (`delete_column` filtra
   * `hidden.is_(False)`). Contar todos aqui faria a tela avisar de um
   * bloqueio que não existe.
   */
  const visiveis = column.cards.filter((card) => !card.hidden);
  const ocultos = column.cards.length - visiveis.length;
  const bloqueada = visiveis.length > 0;

  const eSecao = column.kind === "SECTION";
  const rotulo = eSecao ? "seção" : "coluna";

  // Destinos possíveis: colunas comuns do quadro, menos ela mesma. Seção
  // não entra — ela não aceita card (o servidor devolveria 422).
  const destinos = board.columns.filter(
    (candidata) => candidata.kind === "COLUMN" && candidata.id !== column.id,
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-excluir-coluna"
        className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl"
      >
        <h3 id="titulo-excluir-coluna" className="text-base font-semibold">
          Excluir a {rotulo} &quot;{column.name}&quot;?
        </h3>

        {eSecao ? (
          <p className="mt-3 text-sm text-zinc-700">
            Uma seção é um separador visual e não contém cards — excluí-la
            não afeta card nenhum. Ela sai da ordem do quadro desta empresa;
            o template que a originou não é alterado.
          </p>
        ) : bloqueada ? (
          <>
            <p className="mt-3 text-sm text-zinc-700">
              Esta coluna tem{" "}
              <strong>
                {visiveis.length} card(s) visível(is)
              </strong>
              . A exclusão será <strong>recusada</strong> enquanto eles
              estiverem aqui — os cards nunca são apagados junto com a
              coluna.
            </p>
            <p className="mt-2 text-sm text-zinc-700">
              Escolha para onde movê-los. Eles vão para o fim da coluna de
              destino, mantendo status, etiquetas, checklist, histórico e
              conversa.
            </p>

            <label className="mt-4 block text-sm text-zinc-700">
              Mover os cards para
              <select
                className="field mt-1"
                aria-label="Coluna de destino dos cards"
                value={destino}
                onChange={(e) =>
                  setDestino(e.target.value ? Number(e.target.value) : "")
                }
              >
                <option value="">Escolha a coluna...</option>
                {destinos.map((candidata) => (
                  <option key={candidata.id} value={candidata.id}>
                    {candidata.name}
                  </option>
                ))}
              </select>
            </label>

            {destinos.length === 0 ? (
              <p className="mt-2 text-sm text-red-700">
                Não há outra coluna neste quadro para receber os cards. Crie
                uma coluna antes de excluir esta.
              </p>
            ) : null}
          </>
        ) : (
          <p className="mt-3 text-sm text-zinc-700">
            Esta coluna não tem nenhum card visível
            {ocultos > 0
              ? ` (${ocultos} card(s) arquivado(s) ficarão sem coluna, no balde "Sem coluna" do quadro)`
              : ""}
            . Excluí-la não apaga card nenhum.
          </p>
        )}

        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onCancel}>
            Cancelar
          </button>
          {bloqueada && !eSecao ? (
            <button
              type="button"
              className="btn-danger-outline"
              disabled={destino === "" || isPending}
              onClick={() => onRelocateAndDelete(Number(destino))}
            >
              Mover {visiveis.length} card(s) e excluir
            </button>
          ) : (
            <button
              type="button"
              className="btn-danger-outline"
              disabled={isPending}
              onClick={onDelete}
            >
              Excluir {rotulo}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
