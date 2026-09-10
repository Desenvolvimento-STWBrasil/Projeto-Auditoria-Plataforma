"use client";

import {
  labelChipClass,
  labelChipStyle,
  sortLabels,
  TRELLO_COLOR_MAP,
} from "@/lib/board-labels";

import {
  createDashboardLabelAction,
  deleteDashboardLabelAction,
  listDashboardLabelsAction,
  updateDashboardLabelAction,
  type DashboardLabelItem,
} from "./actions";
import { useState, useTransition } from "react";

type DashboardLabelsClientProps = {
  initialLabels: DashboardLabelItem[];
};

const FORM_VAZIO = { name: "", color: "#788c5d", sort_order: 0 };

export function DashboardLabelsClient({
  initialLabels,
}: DashboardLabelsClientProps) {
  const [labels, setLabels] = useState<DashboardLabelItem[]>(initialLabels);
  const [form, setForm] = useState(FORM_VAZIO);
  const [editandoId, setEditandoId] = useState<number | null>(null);
  const [feedback, setFeedback] = useState("");
  const [isPending, startTransition] = useTransition();

  async function recarregar() {
    setLabels(await listDashboardLabelsAction());
  }

  function salvar() {
    if (!form.name.trim()) {
      setFeedback("Informe o nome da etiqueta.");
      return;
    }
    setFeedback("");
    startTransition(async () => {
      const entrada = {
        name: form.name.trim(),
        color: form.color,
        sort_order: form.sort_order,
      };
      const resultado =
        editandoId === null
          ? await createDashboardLabelAction(entrada)
          : await updateDashboardLabelAction(editandoId, entrada);

      if (!resultado.ok) {
        setFeedback(resultado.message);
        return;
      }
      setForm(FORM_VAZIO);
      setEditandoId(null);
      await recarregar();
      setFeedback("Etiqueta salva.");
    });
  }

  function editar(label: DashboardLabelItem) {
    setEditandoId(label.id);
    setForm({
      name: label.name,
      color: label.color,
      sort_order: label.sort_order,
    });
    setFeedback("");
  }

  function excluir(label: DashboardLabelItem) {
    if (!window.confirm(`Excluir a etiqueta "${label.name}"?`)) return;
    startTransition(async () => {
      const resultado = await deleteDashboardLabelAction(label.id);
      if (!resultado.ok) {
        setFeedback(resultado.message);
        return;
      }
      await recarregar();
      setFeedback("Etiqueta excluída.");
    });
  }

  return (
    <main className="min-h-screen bg-(--color-surface) py-8">
      <div className="container-page space-y-6">
        <header className="card">
          <h1 className="text-2xl font-semibold text-(--color-dark)">
            Etiquetas de card
          </h1>
          <p className="mt-1 text-sm text-zinc-600">
            Vocabulário global de <strong>criticidade</strong>, aplicável aos
            cards de qualquer empresa. Etiqueta não declara conformidade — quem
            responde &quot;está conforme?&quot; é o <em>status</em> do card, e
            só a equipe de auditoria pode alterá-lo.
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

        <div className="grid gap-6 lg:grid-cols-3">
          <section className="card space-y-3 lg:col-span-1">
            <h2 className="text-base font-semibold">
              {editandoId === null ? "Nova etiqueta" : "Editar etiqueta"}
            </h2>
            <label className="block text-sm text-zinc-700">
              Nome
              <input
                className="field mt-1"
                aria-label="Nome da etiqueta"
                value={form.name}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, name: e.target.value }))
                }
              />
            </label>

            <label className="block text-sm text-zinc-700">
              Cor
              <input
                type="color"
                aria-label="Cor da etiqueta"
                className="mt-1 h-9 w-full rounded-lg border border-zinc-300"
                value={form.color}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, color: e.target.value }))
                }
              />
            </label>
            <div className="flex flex-wrap gap-1">
              {Object.entries(TRELLO_COLOR_MAP).map(([nome, hex]) => (
                <button
                  key={nome}
                  type="button"
                  title={nome}
                  aria-label={`Usar a cor ${nome}`}
                  className="h-6 w-6 rounded border border-zinc-300"
                  style={{ backgroundColor: hex }}
                  onClick={() => setForm((prev) => ({ ...prev, color: hex }))}
                />
              ))}
            </div>

            <label className="block text-sm text-zinc-700">
              Ordem
              <input
                type="number"
                className="field mt-1"
                aria-label="Ordem da etiqueta"
                value={form.sort_order}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    sort_order: Number(e.target.value) || 0,
                  }))
                }
              />
            </label>

            <div className="flex gap-2">
              <button
                type="button"
                className="btn-primary"
                disabled={!form.name.trim() || isPending}
                onClick={salvar}
              >
                {editandoId === null ? "Criar etiqueta" : "Salvar"}
              </button>
              {editandoId !== null ? (
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setEditandoId(null);
                    setForm(FORM_VAZIO);
                  }}
                >
                  Cancelar
                </button>
              ) : null}
            </div>
          </section>

          <section className="card lg:col-span-2">
            <h2 className="text-base font-semibold">
              Etiquetas cadastradas ({labels.length})
            </h2>

            {labels.length === 0 ? (
              <p className="mt-3 text-sm text-zinc-600">
                Nenhuma etiqueta cadastrada ainda.
              </p>
            ) : (
              <ul className="mt-3 divide-y divide-(--color-neutral)">
                {sortLabels(labels).map((label) => (
                  <li
                    key={label.id}
                    className="flex flex-wrap items-center justify-between gap-3 py-3"
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className={labelChipClass(label.color)}
                        style={labelChipStyle(label.color)}
                      >
                        {label.name}
                      </span>
                      <span className="text-xs text-zinc-500">
                        ordem {label.sort_order} · {label.color}
                      </span>
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => editar(label)}
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        className="btn-danger-outline"
                        disabled={isPending}
                        onClick={() => excluir(label)}
                      >
                        Excluir
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
