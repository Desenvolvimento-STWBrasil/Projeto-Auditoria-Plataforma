"use client";

import { useEffect, useId } from "react";

/**
 * Casca comum dos diálogos da tela de empresas.
 *
 * Os três modais (criar, editar, excluir) repetiam o mesmo overlay em
 * três lugares e nenhum deles se anunciava como diálogo: sem
 * `role="dialog"`, sem `aria-modal`, sem título associado e sem fechar
 * no `Escape`. Para leitor de tela era um pedaço de página que aparecia
 * do nada; para teclado, uma armadilha de onde só se saía com o mouse.
 *
 * Não faz *focus trap* — isso exigiria varrer a árvore de focáveis e é
 * mais máquina do que estes formulários curtos pedem. `Escape`, rótulo e
 * papel corretos resolvem o essencial.
 */
type ModalShellProps = {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  /** Diálogo destrutivo ganha a moldura vermelha da exclusão. */
  tone?: "default" | "danger";
  maxWidthClass?: string;
};

export function ModalShell({
  title,
  onClose,
  children,
  tone = "default",
  maxWidthClass = "max-w-xl",
}: ModalShellProps) {
  const titleId = useId();

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={`w-full ${maxWidthClass} max-h-[90vh] overflow-y-auto rounded-xl bg-white p-6 shadow-xl ${
          tone === "danger" ? "border-2 border-red-200" : ""
        }`}
      >
        <div className="flex items-start justify-between gap-4">
          <h3
            id={titleId}
            className={`text-base font-semibold ${
              tone === "danger" ? "text-red-700" : "text-(--color-dark)"
            }`}
          >
            {title}
          </h3>
          <button
            type="button"
            className="btn-ghost shrink-0"
            aria-label="Fechar"
            onClick={onClose}
          >
            <span aria-hidden="true" className="text-lg leading-none">
              ×
            </span>
          </button>
        </div>

        {children}
      </div>
    </div>
  );
}
