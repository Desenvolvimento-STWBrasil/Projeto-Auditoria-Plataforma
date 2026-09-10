export default function ClientBoardLoading() {
  return (
    <main className="min-h-screen bg-(--color-surface) py-8">
      <div className="container-page space-y-6">
        <div className="card animate-pulse">
          <div className="h-6 w-56 rounded bg-zinc-200" />
          <div className="mt-2 h-4 w-80 rounded bg-zinc-100" />
        </div>
        <div className="flex gap-4 overflow-hidden">
          <div className="card h-96 w-72 shrink-0 animate-pulse" />
          <div className="card h-96 w-72 shrink-0 animate-pulse" />
          <div className="card h-96 w-72 shrink-0 animate-pulse" />
        </div>
      </div>
    </main>
  );
}
