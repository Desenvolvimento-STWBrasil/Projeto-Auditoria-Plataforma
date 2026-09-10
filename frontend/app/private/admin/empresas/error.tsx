"use client";

import { useEffect } from "react";

export default function EmpresasError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(
      "[private/admin/empresas] erro ao carregar a página:",
      error,
    );
  }, [error]);

  return (
    <main className="min-h-screen flex items-center justify-center bg-(--color-surface) p-6">
      <div className="card max-w-md text-center">
        <h1 className="text-lg font-semibold text-(--color-dark)">
          Não foi possível carregar a lista de empresas
        </h1>
        <p className="mt-2 text-sm text-zinc-600">
          {error.message || "Ocorreu um erro inesperado ao buscar os dados."}
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
