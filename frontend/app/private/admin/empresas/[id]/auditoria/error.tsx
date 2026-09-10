"use client";

import { useEffect } from "react";

export default function CompanyAuditsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(
      "[private/admin/empresas/[id]/auditoria] erro ao carregar a página",
      error,
    );
  }, [error]);

  return (
    <main className="flex min-h-[50vh] items-center justify-center p-6">
      <div className="card max-w-md text-center">
        <h1 className="text-lg font-semibold text-(--color-dark)">
          Não foi possível carregar as auditorias desta empresa
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
