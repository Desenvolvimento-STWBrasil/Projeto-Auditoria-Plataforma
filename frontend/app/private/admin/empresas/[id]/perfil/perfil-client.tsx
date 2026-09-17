"use client";

import { useRouter } from "next/navigation";
import {
  CompanyAdminDetail,
  deleteCompanyAction,
  updateCompanyAction,
} from "../../actions";
import { useState, useTransition } from "react";

type PerfilClientProps = {
  initialDetail: CompanyAdminDetail;
};

export function PerfilClient({ initialDetail }: PerfilClientProps) {
  const router = useRouter();
  const [detail, setDetail] = useState(initialDetail);
  const [form, setForm] = useState({
    name: initialDetail.name,
    email: initialDetail.email,
    phone: initialDetail.phone ?? "",
  });
  const [isSaving, setIsSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");
  const [isPending, startTransition] = useTransition();

  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [confirmChecked, setConfirmChecked] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteMsg, setDeleteMsg] = useState("");

  function handleSave() {
    if (!form.name.trim() || !form.email.trim()) {
      setSaveMsg("Nome e e-mail são obrigatórios.");
      return;
    }
    setIsSaving(true);
    setSaveMsg("");
    startTransition(async () => {
      const result = await updateCompanyAction(detail.id, {
        name: form.name,
        email: form.email,
        phone: form.phone || null,
      });
      setIsSaving(false);
      if (!result.ok) {
        setSaveMsg(result.message);
        return;
      }
      setDetail(result.company);
      setSaveMsg("Alterações salvas");
    });
  }

  function handleConfirmDelete() {
    if (!confirmChecked) return;
    setIsDeleting(true);
    setDeleteMsg("");
    startTransition(async () => {
      const result = await deleteCompanyAction(detail.id);
      setIsDeleting(false);
      if (!result.ok) {
        setDeleteMsg(result.message);
        return;
      }
      router.push("/private/admin/empresas");
    });
  }

  return (
    <main className="py-8">
      <div className="container-page space-y-6">
        <section className="card max-w-xl">
          <h2 className="text-base font-semibold text-(--color-dark)">
            Dados cadastrais
          </h2>

          <div className="mt-4 space-y-3">
            <div>
              <label className="text-xs font-medium text-zinc-600">
                Nome da empresa
              </label>
              <input
                className="field mt-1"
                value={form.name}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, name: e.target.value }))
                }
              />
            </div>
            <div>
              <label className="text-xs font-medium text-zinc-600">
                E-mail da empresa
              </label>
              <input
                className="field mt-1"
                type="email"
                value={form.email}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, email: e.target.value }))
                }
              />
            </div>
            <div>
              <label className="text-xs font-medium text-zinc-600">
                Telefone (opcional)
              </label>
              <input
                className="field mt-1"
                value={form.phone}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, phone: e.target.value }))
                }
              />
            </div>

            <button
              type="button"
              className="btn-primary"
              disabled={isSaving || isPending}
              onClick={handleSave}
            >
              {isSaving ? "Salvando..." : "Salvar alterações"}
            </button>

            {saveMsg ? (
              <p className="text-sm text-zinc-700">{saveMsg}</p>
            ) : null}
          </div>
        </section>

        <section className="card max-w-xl border-red-200">
          <h2 className="text-base font-semibold text-red-700">
            Zona de risco
          </h2>
          <p className="mt-2 text-sm text-zinc-600">
            Excluir esta empresa remove em cascata usuários, auditorias,
            dashboard e mensagens — ação irreversível.
          </p>
          <button
            type="button"
            className="btn-danger-outline mt-4"
            onClick={() => {
              setIsDeleteOpen(true);
              setConfirmChecked(false);
              setDeleteMsg("");
            }}
          >
            Excluir empresa
          </button>
        </section>

        {isDeleteOpen ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
            <div className="w-full max-w-lg rounded-xl border-2 border-red-200 bg-white p-6 shadow-xl">
              <h3 className="text-base font-semibold text-red-700">
                Excluir &quot;{detail.name}&quot;?
              </h3>
              <ul className="mt-3 space-y-1 rounded-lg bg-red-50 p-3 text-sm text-red-800">
                <li>
                  • O usuário principal ({detail.principal_full_name}) e{" "}
                  {detail.sub_user_count} colaborador(es)
                </li>
                <li>
                  • {detail.audit_count} auditoria(s), com controles, evidências
                  e mensagens
                </li>
                <li>
                  • {detail.dashboard_card_count} card(s) do dashboard, com
                  notas, checklist e histórico
                </li>
                <li>
                  • {detail.company_message_count} mensagem(ns) do chat geral
                </li>
              </ul>

              <label className="mt-4 flex items-start gap-2 text-sm text-zinc-800">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={confirmChecked}
                  onChange={(e) => setConfirmChecked(e.target.checked)}
                />
                Entendo que esta exclusão é permanente e não pode ser desfeita.
              </label>

              {deleteMsg ? (
                <p className="mt-2 text-sm text-red-600">{deleteMsg}</p>
              ) : null}

              <div className="mt-4 flex justify-end gap-2">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setIsDeleteOpen(false)}
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  className="btn-danger"
                  disabled={!confirmChecked || isDeleting || isPending}
                  onClick={handleConfirmDelete}
                >
                  {isDeleting ? "Excluindo..." : "Excluir definitivamente"}
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </main>
  );
}
