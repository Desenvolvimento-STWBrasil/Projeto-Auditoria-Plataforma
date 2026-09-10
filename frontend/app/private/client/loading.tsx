export default function ClientLoading() {
  return (
    <main className="min-h-screen bg-(--color-surface) py-8">
      <div className="container-page">
        <div className="mb-6 card animate-pulse">
          <div className="h-6 w-56 rounded bg-zinc-200" />
          <div className="mt-2 h-4 w-80 rounded bg-zinc-100" />
        </div>
        <div className="mb-6 grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="card animate-pulse text-center">
              <div className="mx-auto h-3 w-16 rounded bg-zinc-100" />
              <div className="mx-auto mt-3 h-8 w-10 rounded bg-zinc-200"></div>
            </div>
          ))}
        </div>
        <div className="card animate-pulse">
          <div className="h-5 w-72 rounede bg-zinc-200" />
        </div>
      </div>
    </main>
  );
}
