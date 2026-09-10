/**
 * Esqueleto da rota. Espelha o novo layout — faixa de cabeçalho, barra
 * de busca e cinco linhas — para que a troca do loading pela tela real
 * não desloque nada na tela.
 */
export default function EmpresasLoading() {
  return (
    <main className="min-h-screen bg-(--color-surface)">
      <div className="border-b border-(--color-neutral) bg-white">
        <div className="container-page flex items-center justify-between gap-4 py-6">
          <div className="animate-pulse">
            <div className="h-7 w-40 rounded bg-zinc-200" />
            <div className="mt-2 h-4 w-80 max-w-full rounded bg-zinc-100" />
          </div>
          <div className="h-10 w-36 animate-pulse rounded-xl bg-zinc-200" />
        </div>
      </div>

      <div className="container-page py-6">
        <div className="card">
          <div className="h-10 w-full animate-pulse rounded-xl bg-zinc-100 sm:max-w-md" />
          <ul className="mt-4 animate-pulse divide-y divide-(--color-neutral)">
            {Array.from({ length: 5 }, (_, i) => (
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
      </div>
    </main>
  );
}
