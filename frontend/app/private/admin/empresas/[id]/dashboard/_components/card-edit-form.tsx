"use client";

import { useState } from "react";

import type { DashboardCardDetail } from "@/app/private/admin/actions";
import type { DashboardCardCategory } from "../actions";

export type CardEditInput = {
  title: string;
  description: string | null;
  controlCode: string | null;
  categoryId: number | null;
};

type CardEditFormProps = {
  cardDetail: DashboardCardDetail;
  categories: DashboardCardCategory[];
  isPending: boolean;
  onSave: (input: CardEditInput) => void;
  onCancel: () => void;
};

/**
 * Edição do texto do card, dentro do modal.
 *
 * O `PATCH /dashboard/cards/{id}` é uma SUBSTITUIÇÃO, não um patch
 * parcial: `CardUpdateIn` exige os quatro campos e grava exatamente o
 * que recebe. Por isso o formulário nasce pré-preenchido com o estado
 * atual e envia sempre os quatro — mandar só o campo alterado apagaria
 * os outros três, e a descrição (texto normativo do controle, 68 % dos
 * cards reais) é justamente o campo mais caro de perder.
 */
export function CardEditForm({
  cardDetail,
  categories,
  isPending,
  onSave,
  onCancel,
}: CardEditFormProps) {
  const [title, setTitle] = useState(cardDetail.title);
  const [controlCode, setControlCode] = useState(cardDetail.control_code ?? "");
  const [description, setDescription] = useState(cardDetail.description ?? "");
  const [categoryId, setCategoryId] = useState<number | null>(
    cardDetail.category_id,
  );

  const tituloValido = title.trim().length > 0;

  return (
    <form
      className="space-y-3"
      onSubmit={(evento) => {
        evento.preventDefault();
        if (!tituloValido) return;
        onSave({
          title: title.trim(),
          // String vazia e "sem valor" são coisas diferentes no banco
          // (a coluna é nullable): normalizamos aqui para não gravar ""
          // onde o resto do sistema espera NULL.
          description: description.trim() || null,
          controlCode: controlCode.trim() || null,
          categoryId,
        });
      }}
    >
      <label className="block text-sm text-zinc-700">
        Título
        <input
          className="field mt-1"
          aria-label="Título do card"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
      </label>

      <label className="block text-sm text-zinc-700">
        Código do controle
        <input
          className="field mt-1"
          aria-label="Código do controle"
          placeholder="opcional"
          value={controlCode}
          onChange={(e) => setControlCode(e.target.value)}
        />
      </label>

      <label className="block text-sm text-zinc-700">
        Categoria
        <select
          className="field mt-1"
          aria-label="Categoria do card"
          value={categoryId ?? ""}
          onChange={(e) =>
            setCategoryId(e.target.value ? Number(e.target.value) : null)
          }
        >
          <option value="">Sem categoria</option>
          {categories.map((categoria) => (
            <option key={categoria.id} value={categoria.id}>
              {categoria.name}
            </option>
          ))}
        </select>
      </label>

      <label className="block text-sm text-zinc-700">
        Descrição do controle
        <textarea
          className="field mt-1 min-h-32"
          aria-label="Descrição do controle"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </label>

      <div className="flex gap-2">
        <button
          type="submit"
          className="btn-primary"
          disabled={!tituloValido || isPending}
        >
          Salvar
        </button>
        <button type="button" className="btn-secondary" onClick={onCancel}>
          Cancelar
        </button>
      </div>
    </form>
  );
}
