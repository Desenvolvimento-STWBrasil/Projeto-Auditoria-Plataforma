export default function AdminLoading() {
  return (
    <main className="min-h-screen bg-(--color-surface) py-8">
      <div className="container-page space-y-6">
        <div className="card animate-pulse">
          <div className="h-6 w-48 rounded bg-zinc-200" />
          <div className="mt-2 h-4 w-72 rounded bg-zinc-100" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="card animate-pulse">
              <div className="h-4 w-20 rounded bg-zinc-100" />
              <div className="mt-3 h-8 w-12 rounded bg-zinc-200" />
            </div>
          ))}
        </div>
        <div className="card animate-pulse">
          <div className="h-5 w-64 rounded bg-zinc-200" />
          <div className="mt-3 h-4 w-full rounded bg-zinc-100" />
        </div>
      </div>
    </main>
  );
}
