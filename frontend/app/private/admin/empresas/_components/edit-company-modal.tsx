"use client";

import { ModalShell } from "@/app/private/_components/modal-shell";

/**
 * Edição rápida dos três campos que pertencem à tabela `companies`.
 * Trocar o usuário principal ou mexer em sub-usuários é assunto das abas
 * da empresa — este modal é o atalho para o cadastro básico.
 */
export type EditFormState = { name: string; email: string; phone: string };

export const EMPTY_EDIT_FORM: EditFormState = { name: "", email: "", phone: "" };

type EditCompanyModalProps = {
  form: EditFormState;
  message: string;
  isSubmitting: boolean;
  onChange: (patch: Partial<EditFormState>) => void;
  onSubmit: () => void;
  onClose: () => void;
};

export function EditCompanyModal({
  form,
  message,
  isSubmitting,
  onChange,
  onSubmit,
  onClose,
}: EditCompanyModalProps) {
  return (
    <ModalShell title="Editar empresa" onClose={onClose} maxWidthClass="max-w-md">
      <form
        className="mt-4 space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
      >
        <label className="block">
          <span className="text-xs font-medium text-zinc-600">
            Nome da empresa
          </span>
          <input
            className="field mt-1"
            value={form.name}
            onChange={(e) => onChange({ name: e.target.value })}
          />
        </label>

        <label className="block">
          <span className="text-xs font-medium text-zinc-600">
            E-mail da empresa
          </span>
          <input
            className="field mt-1"
            type="email"
            value={form.email}
            onChange={(e) => onChange({ email: e.target.value })}
          />
        </label>

        <label className="block">
          <span className="text-xs font-medium text-zinc-600">
            Telefone (opcional)
          </span>
          <input
            className="field mt-1"
            value={form.phone}
            onChange={(e) => onChange({ phone: e.target.value })}
          />
        </label>

        {message ? (
          <p role="alert" className="text-sm text-red-600">
            {message}
          </p>
        ) : null}

        <div className="flex justify-end gap-2 border-t border-(--color-neutral) pt-4">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancelar
          </button>
          <button
            type="submit"
            className="btn-primary disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isSubmitting}
          >
            {isSubmitting ? "Salvando..." : "Salvar alterações"}
          </button>
        </div>
      </form>
    </ModalShell>
  );
}
