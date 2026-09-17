"use client";

import type { CompanyAdminDetail } from "../actions";
import { ModalShell } from "@/app/private/_components/modal-shell";

/**
 * Confirmação da exclusão em cascata.
 *
 * Este é o único lugar da listagem onde o aviso de cascata precisa
 * estar por extenso — por isso ele saiu do cabeçalho da página, onde
 * era lido uma vez e ignorado depois. Aqui ele chega com os números
 * reais da empresa, buscados no momento em que o modal abre.
 *
 * O checkbox de confirmação e o botão desabilitado enquanto o impacto
 * carrega são deliberados: sem eles daria para confirmar antes de saber
 * o que se está apagando.
 */
type DeleteCompanyModalProps = {
  companyName: string;
  impact: CompanyAdminDetail | null;
  isLoadingImpact: boolean;
  confirmChecked: boolean;
  isDeleting: boolean;
  message: string;
  onToggleConfirm: (checked: boolean) => void;
  onConfirm: () => void;
  onClose: () => void;
};

export function DeleteCompanyModal({
  companyName,
  impact,
  isLoadingImpact,
  confirmChecked,
  isDeleting,
  message,
  onToggleConfirm,
  onConfirm,
  onClose,
}: DeleteCompanyModalProps) {
  return (
    <ModalShell
      title={`Excluir “${companyName}”?`}
      onClose={onClose}
      tone="danger"
      maxWidthClass="max-w-lg"
    >
      <p className="mt-2 text-sm text-zinc-700">
        Esta ação é <strong>irreversível</strong> e remove imediatamente, em
        uma única transação:
      </p>

      {isLoadingImpact ? (
        <p className="mt-3 text-sm text-zinc-500">
          Calculando o impacto da exclusão...
        </p>
      ) : impact ? (
        <ul className="mt-3 space-y-1 rounded-lg bg-red-50 p-3 text-sm text-red-800">
          <li>
            • O usuário principal ({impact.principal_full_name}) e{" "}
            {impact.sub_user_count} colaborador(es)
          </li>
          <li>
            • {impact.audit_count} auditoria(s), com todos os controles,
            evidências e mensagens
          </li>
          <li>
            • {impact.dashboard_card_count} card(s) do dashboard, com notas,
            checklist e histórico
          </li>
          <li>
            • {impact.company_message_count} mensagem(ns) do chat geral com a
            empresa
          </li>
        </ul>
      ) : null}

      <label className="mt-4 flex items-start gap-2 text-sm text-zinc-800">
        <input
          type="checkbox"
          className="mt-1"
          checked={confirmChecked}
          onChange={(e) => onToggleConfirm(e.target.checked)}
          disabled={isLoadingImpact}
        />
        Entendo que esta exclusão é permanente e não pode ser desfeita.
      </label>

      {message ? (
        <p role="alert" className="mt-2 text-sm text-red-600">
          {message}
        </p>
      ) : null}

      <div className="mt-4 flex justify-end gap-2">
        <button type="button" className="btn-secondary" onClick={onClose}>
          Cancelar
        </button>
        <button
          type="button"
          className="btn-danger"
          disabled={!confirmChecked || isDeleting || isLoadingImpact}
          onClick={onConfirm}
        >
          {isDeleting ? "Excluindo..." : "Excluir definitivamente"}
        </button>
      </div>
    </ModalShell>
  );
}
