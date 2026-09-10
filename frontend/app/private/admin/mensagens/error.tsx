"use client";

import { useEffect } from "react";

export default function MensagensError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(
      "[private/admin/mensagens] erro ao carregador a página:",
      error,
    );
  }, [error]);

  return (
    <main className="min-h-screen flex items-center justify-center bg-(--color-surface) p-6">
      <div className="card max-w-md text-center">
        <h1 className="text-lg font-semibold text-(--color-dark)">
          Não foi possível carregar as mensagens
        </h1>
        <p className="mt-2 text-sm text-zinc-600">
          {error.message || "Ocorreu inesperado ao buscar os dados"}
        </p>
        <button
          type="button"
          className="btn-primary mt-4"
          onClick={() => reset()}
        >
          Tentar novamente
        </button>
      </div>
    </main>
  );
}
