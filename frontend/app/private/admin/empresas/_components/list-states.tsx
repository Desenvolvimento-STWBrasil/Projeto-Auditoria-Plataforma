"use client";

/**
 * Estados de carregamento, vazio e erro da lista de empresas.
 *
 * Os três eram uma linha de texto. O de carregamento era o pior: a
 * tabela inteira colapsava para uma célula com "Carregando..." a cada
 * troca de página e a cada busca (debounce de 300 ms), então a tela
 * pulava enquanto o administrador ainda estava digitando.
 *
 * O esqueleto ocupa exatamente o espaço que a lista vai ocupar, e o
 * salto desaparece.
 */

const LINHAS_DO_ESQUELETO = 5;

export function CompaniesSkeleton() {
  return (
    <div aria-busy="true" aria-label="Carregando empresas">
      <span className="sr-only">Carregando empresas…</span>
      <ul className="animate-pulse divide-y divide-(--color-neutral)">
        {Array.from({ length: LINHAS_DO_ESQUELETO }, (_, i) => (
          <li key={i} className="flex items-center gap-3 py-4">
            <span className="h-9 w-9 shrink-0 rounded-full bg-zinc-200" />
            <span className="flex-1 space-y-2">
              <span className="block h-3.5 w-2/5 rounded bg-zinc-200" />
              <span className="block h-3 w-3/5 rounded bg-zinc-100" />
            </span>
            <span className="hidden h-8 w-40 rounded-xl bg-zinc-100 lg:block" />
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Vazio de busca e vazio de cadastro são situações diferentes e pedem
 * saídas diferentes: uma é "seu filtro não achou nada" (limpe o filtro),
 * a outra é "ainda não existe nada" (cadastre a primeira). A mensagem
 * única de antes — "Nenhuma empresa encontrada." — não dizia qual das
 * duas, nem oferecia saída nenhuma.
 */
type EmptyStateProps = {
  search: string;
  onClearSearch: () => void;
  onCreate: () => void;
};

export function EmptyState({
  search,
  onClearSearch,
  onCreate,
}: EmptyStateProps) {
  const buscando = search.trim().length > 0;

  return (
    <div className="px-4 py-12 text-center">
      <p className="text-sm font-medium text-(--color-dark)">
        {buscando
          ? `Nenhuma empresa corresponde a “${search.trim()}”.`
          : "Nenhuma empresa cadastrada ainda."}
      </p>
      <p className="mt-1 text-sm text-zinc-500">
        {buscando
          ? "A busca cobre nome e e-mail da empresa e do responsável."
          : "Cadastre a primeira empresa cliente para começar a auditoria."}
      </p>

      {buscando ? (
        <button type="button" className="btn-secondary mt-4" onClick={onClearSearch}>
          Limpar busca
        </button>
      ) : (
        <button type="button" className="btn-primary mt-4" onClick={onCreate}>
          Nova empresa
        </button>
      )}
    </div>
  );
}

/**
 * O erro de carregamento era um `<p>` vermelho sem saída — o
 * administrador tinha de recarregar a página inteira. `onRetry` refaz a
 * mesma busca da página atual.
 */
type ListErrorStateProps = {
  message: string;
  onRetry: () => void;
  isRetrying: boolean;
};

export function ListErrorState({
  message,
  onRetry,
  isRetrying,
}: ListErrorStateProps) {
  return (
    <div
      role="alert"
      className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3"
    >
      <p className="text-sm text-red-800">{message}</p>
      <button
        type="button"
        className="btn-secondary px-3 py-1.5 text-sm"
        disabled={isRetrying}
        onClick={onRetry}
      >
        {isRetrying ? "Tentando..." : "Tentar novamente"}
      </button>
    </div>
  );
}
