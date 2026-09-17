import { controlStatusAccentClass, type ControlStatus } from "@/lib/control-status";

/**
 * As 4 contagens de status de conformidade, no mesmo layout de cards
 * (grid responsivo `sm:2 lg:4`) em toda a aplicação: admin ("Resumo") e
 * cliente/colaborador (dashboard). Era o mesmo dado renderizado com
 * classes diferentes em cada tela (tamanho de fonte, alinhamento,
 * peso) — unificado aqui como a fonte única do padrão visual do admin.
 */
export type StatusSummary = {
  em_analise: number;
  parcial: number;
  conforme: number;
  naoconforme: number;
};

const TILES: { key: keyof StatusSummary; label: string; status: ControlStatus }[] = [
  { key: "em_analise", label: "Em análise", status: "EM_ANALISE" },
  { key: "parcial", label: "Parcial", status: "PARCIAL" },
  { key: "conforme", label: "Conforme", status: "CONFORME" },
  { key: "naoconforme", label: "Não conforme", status: "NAOCONFORME" },
];

export function StatusSummaryCards({ summary }: { summary: StatusSummary }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {TILES.map((tile) => (
        <article key={tile.key} className="card">
          <p className="text-sm text-zinc-600">{tile.label}</p>
          <p
            className={`mt-2 text-3xl font-semibold ${controlStatusAccentClass(tile.status)}`}
          >
            {summary[tile.key]}
          </p>
        </article>
      ))}
    </div>
  );
}
