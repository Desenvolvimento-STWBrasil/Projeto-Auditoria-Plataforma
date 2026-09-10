"use client";

import { ModalShell } from "@/app/private/_components/modal-shell";
import type { TemplateCategory } from "../actions";

/**
 * Categorias de card, agora dentro de um diálogo.
 *
 * Antes era a maior seção de /private/admin/templates: um `.card` com
 * formulário fixo à esquerda e a lista completa à direita, ~620 px com
 * as 9 categorias em uso. A tela se chama "Templates de Dashboard", mas
 * o primeiro e maior bloco dela era manutenção de vocabulário — tarefa
 * que se faz uma vez e raramente se revisita —, e a lista de templates
 * só começava depois de ~800 px de rolagem.
 *
 * Duas mudanças de interação vêm junto com a mudança de lugar:
 *
 * 1. O formulário ABRE NA LINHA da categoria editada. Antes era um só,
 *    no topo, compartilhado entre criar e editar: clicar em "Editar" na
 *    8ª categoria alterava campos fora do campo de visão, e o admin
 *    editava sem ver o que estava editando.
 * 2. A exclusão confirma NA LINHA, no lugar do `window.confirm`. O texto
 *    é o mesmo — inclusive o aviso de que a exclusão é recusada enquanto
 *    houver card classificado na categoria.
 */
export type CategoryFormState = {
  name: string;
  color: string;
  sortOrder: number;
};

type CategoriesModalProps = {
  categories: TemplateCategory[];
  form: CategoryFormState;
  /** Categoria cuja linha está em edição; `null` = nenhuma. */
  editingCategoryId: number | null;
  /** Formulário de criação aberto (distinto de "nenhum formulário"). */
  isCreating: boolean;
  /** Categoria com a confirmação de exclusão aberta na linha. */
  pendingDeleteId: number | null;
  message: string;
  isPending: boolean;
  onChangeForm: (patch: Partial<CategoryFormState>) => void;
  onStartCreate: () => void;
  onStartEdit: (category: TemplateCategory) => void;
  onCancelForm: () => void;
  onSave: () => void;
  onAskDelete: (category: TemplateCategory) => void;
  onCancelDelete: () => void;
  onConfirmDelete: (category: TemplateCategory) => void;
  onClose: () => void;
};

export function CategoriesModal({
  categories,
  form,
  editingCategoryId,
  isCreating,
  pendingDeleteId,
  message,
  isPending,
  onChangeForm,
  onStartCreate,
  onStartEdit,
  onCancelForm,
  onSave,
  onAskDelete,
  onCancelDelete,
  onConfirmDelete,
  onClose,
}: CategoriesModalProps) {
  return (
    <ModalShell
      title="Categorias de card"
      onClose={onClose}
      maxWidthClass="max-w-2xl"
    >
      <p className="mt-1 text-sm text-zinc-600">
        Classificação <strong>global</strong>, compartilhada por todas as
        empresas — é o eixo do filtro e do &quot;Mudar categoria&quot; em lote.
        Categoria não é coluna do quadro: quem organiza visualmente o quadro de
        cada empresa são as seções, definidas por template.
      </p>

      {message ? (
        <p
          role="status"
          className="mt-4 rounded-lg bg-zinc-50 p-2 text-sm text-zinc-700"
        >
          {message}
        </p>
      ) : null}

      <div className="mt-4 flex items-center justify-between gap-3 border-b border-(--color-neutral) pb-3">
        <p className="text-sm text-zinc-500">
          {categories.length} categoria{categories.length === 1 ? "" : "s"}
        </p>
        <button
          type="button"
          className="btn-primary px-3 py-1.5 text-sm"
          disabled={isCreating}
          onClick={onStartCreate}
        >
          + Nova categoria
        </button>
      </div>

      {isCreating ? (
        <div className="mt-3 rounded-xl border border-(--color-neutral) bg-(--color-surface) p-3">
          <h4 className="text-sm font-semibold text-(--color-dark)">
            Nova categoria
          </h4>
          <CategoryFields
            form={form}
            isPending={isPending}
            saveLabel="Criar categoria"
            onChangeForm={onChangeForm}
            onSave={onSave}
            onCancel={onCancelForm}
          />
        </div>
      ) : null}

      <ul className="mt-1 divide-y divide-(--color-neutral)">
        {categories.length === 0 ? (
          <li className="py-6 text-center text-sm text-zinc-600">
            Nenhuma categoria cadastrada ainda.
          </li>
        ) : null}

        {categories.map((category) => {
          if (editingCategoryId === category.id) {
            return (
              <li key={category.id} className="py-3">
                <h4 className="text-sm font-semibold text-(--color-dark)">
                  Editando “{category.name}”
                </h4>
                <CategoryFields
                  form={form}
                  isPending={isPending}
                  saveLabel="Salvar categoria"
                  onChangeForm={onChangeForm}
                  onSave={onSave}
                  onCancel={onCancelForm}
                />
              </li>
            );
          }

          if (pendingDeleteId === category.id) {
            return (
              <li key={category.id} className="py-3">
                <div className="rounded-xl border border-red-200 bg-red-50 p-3">
                  <p className="text-sm font-medium text-red-800">
                    Excluir a categoria “{category.name}”?
                  </p>
                  <p className="mt-1 text-sm text-red-700">
                    Os cards que a usam <strong>não</strong> são apagados — mas
                    a exclusão é recusada enquanto existir card ou definição de
                    template classificado nela.
                  </p>
                  <div className="mt-3 flex justify-end gap-2">
                    <button
                      type="button"
                      className="btn-secondary px-3 py-1.5 text-sm"
                      onClick={onCancelDelete}
                    >
                      Cancelar
                    </button>
                    <button
                      type="button"
                      className="btn-danger px-3 py-1.5 text-sm"
                      /*
                       * Rótulo com o nome: sem ele um leitor de tela
                       * anuncia três botões "Excluir" idênticos na
                       * mesma lista, e o que confirma não se distingue
                       * dos que apenas perguntam.
                       */
                      aria-label={`Confirmar exclusão de ${category.name}`}
                      disabled={isPending}
                      onClick={() => onConfirmDelete(category)}
                    >
                      Excluir
                    </button>
                  </div>
                </div>
              </li>
            );
          }

          return (
            <li
              key={category.id}
              className="flex flex-wrap items-center gap-x-3 gap-y-2 py-3"
            >
              <span
                aria-hidden="true"
                className="h-4 w-4 shrink-0 rounded-full border border-zinc-300"
                /*
                 * Cor vem do banco (`dashboard_categories.color`), então
                 * é `style` inline e não classe: o Tailwind não gera
                 * utilitário para valor dinâmico — mesma razão já
                 * documentada em `globals.css` para `.label-chip`.
                 */
                style={{ backgroundColor: category.color }}
              />
              <span className="min-w-0 flex-1 truncate text-sm font-medium text-(--color-dark)">
                {category.name}
              </span>
              <span className="text-xs whitespace-nowrap text-zinc-500">
                ordem {category.sort_order}
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="btn-secondary px-3 py-1 text-xs"
                  onClick={() => onStartEdit(category)}
                >
                  Editar
                </button>
                <button
                  type="button"
                  className="btn-danger-outline px-3 py-1 text-xs"
                  disabled={isPending}
                  onClick={() => onAskDelete(category)}
                >
                  Excluir
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </ModalShell>
  );
}

/**
 * Os três campos, usados tanto na criação quanto na edição — é o mesmo
 * formulário que existia antes, só que agora renderizado no contexto de
 * quem está sendo editado.
 */
function CategoryFields({
  form,
  isPending,
  saveLabel,
  onChangeForm,
  onSave,
  onCancel,
}: {
  form: CategoryFormState;
  isPending: boolean;
  saveLabel: string;
  onChangeForm: (patch: Partial<CategoryFormState>) => void;
  onSave: () => void;
  onCancel: () => void;
}) {
  return (
    <form
      className="mt-2 grid gap-3 sm:grid-cols-[1fr_auto_auto]"
      onSubmit={(e) => {
        e.preventDefault();
        onSave();
      }}
    >
      <label className="block text-xs text-zinc-600">
        Nome
        <input
          className="field mt-1 py-1.5 text-sm"
          aria-label="Nome da categoria"
          value={form.name}
          onChange={(e) => onChangeForm({ name: e.target.value })}
        />
      </label>

      <label className="block text-xs text-zinc-600">
        Cor
        <input
          type="color"
          aria-label="Cor da categoria"
          className="mt-1 h-9 w-full rounded-lg border border-(--color-neutral) sm:w-16"
          value={form.color}
          onChange={(e) => onChangeForm({ color: e.target.value })}
        />
      </label>

      <label className="block text-xs text-zinc-600">
        Ordem
        <input
          type="number"
          className="field mt-1 py-1.5 text-sm sm:w-24"
          aria-label="Ordem da categoria"
          value={form.sortOrder}
          onChange={(e) =>
            onChangeForm({ sortOrder: Number(e.target.value) || 0 })
          }
        />
      </label>

      <div className="flex gap-2 sm:col-span-3 sm:justify-end">
        <button
          type="button"
          className="btn-secondary px-3 py-1.5 text-sm"
          onClick={onCancel}
        >
          Cancelar
        </button>
        <button
          type="submit"
          className="btn-primary px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-50"
          disabled={!form.name.trim() || isPending}
        >
          {saveLabel}
        </button>
      </div>
    </form>
  );
}
