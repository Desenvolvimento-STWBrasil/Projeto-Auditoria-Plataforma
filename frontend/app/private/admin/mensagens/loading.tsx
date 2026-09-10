export default function MensagensLoading() {
  return (
    <main className="min-h-screen bg-(--color-surface) py-8">
      <div className="container-page space-y-6">
        <div className="card animate-pulse">
          <div className="h-6 w-48 rounded bg-zinc-200" />
          <div className="mt-2 h-4 w-72 rounded bg-zinc-100" />
        </div>
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="card h-64 animate-pulse lg:col-span-1" />
          <div className="card h-128 animate-pulse lg:col-span-2" />
        </div>
      </div>
    </main>
  );
}
