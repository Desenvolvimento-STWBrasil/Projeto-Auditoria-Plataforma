"use client";

import type { TemplateOption } from "../actions";
import { ModalShell } from "@/app/private/_components/modal-shell";

/**
 * Formulário de nova empresa. Só apresentação: validação, chamada da
 * action e tratamento de erro continuam em `empresas-client.tsx` — o
 * onboarding cria empresa + usuário principal + dashboard numa
 * transação só, e essa regra não pertence a um componente de tela.
 *
 * Os campos ganharam `<label>` visível. Antes eram cinco `placeholder`
 * empilhados, e placeholder some quando se começa a digitar: quem
 * chegasse ao quinto campo não tinha mais como saber o que os anteriores
 * pediam.
 */
export type CreateFormState = {
  principalName: string;
  companyName: string;
  principalEmail: string;
  principalPhone: string;
  templateId: number | "";
  manualDashboard: boolean;
};

export const EMPTY_CREATE_FORM: CreateFormState = {
  principalName: "",
  companyName: "",
  principalEmail: "",
  principalPhone: "",
  templateId: "",
  manualDashboard: false,
};

type CreateCompanyModalProps = {
  form: CreateFormState;
  templates: TemplateOption[];
  message: string;
  isSubmitting: boolean;
  onChange: (patch: Partial<CreateFormState>) => void;
  onSubmit: () => void;
  onClose: () => void;
};

export function CreateCompanyModal({
  form,
  templates,
  message,
  isSubmitting,
  onChange,
  onSubmit,
  onClose,
}: CreateCompanyModalProps) {
  return (
    <ModalShell title="Nova empresa" onClose={onClose}>
      <p className="mt-1 text-sm text-zinc-600">
        A empresa, o usuário principal e o dashboard inicial são criados
        juntos. As credenciais vão por e-mail para o responsável.
      </p>

      <form
        className="mt-4 space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
      >
        <fieldset className="space-y-3">
          <legend className="text-xs font-semibold tracking-wide text-zinc-500 uppercase">
            Empresa
          </legend>
          <label className="block">
            <span className="text-xs font-medium text-zinc-600">
              Nome da empresa
            </span>
            <input
              className="field mt-1"
              value={form.companyName}
              onChange={(e) => onChange({ companyName: e.target.value })}
            />
          </label>
        </fieldset>

        <fieldset className="space-y-3">
          <legend className="text-xs font-semibold tracking-wide text-zinc-500 uppercase">
            Responsável (usuário principal)
          </legend>
          <label className="block">
            <span className="text-xs font-medium text-zinc-600">
              Nome do responsável
            </span>
            <input
              className="field mt-1"
              value={form.principalName}
              onChange={(e) => onChange({ principalName: e.target.value })}
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="text-xs font-medium text-zinc-600">E-mail</span>
              <input
                className="field mt-1"
                type="email"
                value={form.principalEmail}
                onChange={(e) => onChange({ principalEmail: e.target.value })}
              />
            </label>
            <label className="block">
              <span className="text-xs font-medium text-zinc-600">
                Telefone (opcional)
              </span>
              <input
                className="field mt-1"
                value={form.principalPhone}
                onChange={(e) => onChange({ principalPhone: e.target.value })}
              />
            </label>
          </div>
        </fieldset>

        <fieldset className="space-y-3">
          <legend className="text-xs font-semibold tracking-wide text-zinc-500 uppercase">
            Dashboard inicial
          </legend>
          <label className="block">
            <span className="text-xs font-medium text-zinc-600">Template</span>
            <select
              className="field mt-1"
              disabled={form.manualDashboard}
              value={form.templateId}
              onChange={(e) =>
                onChange({
                  templateId: e.target.value ? Number(e.target.value) : "",
                })
              }
            >
              <option value="">Template padrão</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </label>

          <label className="flex items-center gap-2 text-sm text-zinc-700">
            <input
              type="checkbox"
              checked={form.manualDashboard}
              onChange={(e) => {
                const checked = e.target.checked;
                // Template e criação manual são excludentes: marcar a
                // segunda tem de zerar o primeiro, senão o formulário
                // envia um `template_id` que o backend vai ignorar.
                onChange(
                  checked
                    ? { manualDashboard: true, templateId: "" }
                    : { manualDashboard: false },
                );
              }}
            />
            Criar dashboard manualmente (sem template automático)
          </label>
        </fieldset>

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
            {isSubmitting ? "Criando empresa..." : "Criar empresa"}
          </button>
        </div>
      </form>
    </ModalShell>
  );
}
