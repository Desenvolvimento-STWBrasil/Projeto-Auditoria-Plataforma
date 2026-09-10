"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

/**
 * Menu "⋯" das ações secundárias de uma empresa.
 *
 * Por que existe: a listagem tinha três botões de tamanho cheio por
 * linha — Configurar, Editar e Excluir —, todos com o mesmo peso visual.
 * Com 10 linhas na página são 30 alvos disputando atenção, e o mais
 * perigoso deles (exclusão em cascata, irreversível) ficava a um clique
 * de distância do mais rotineiro.
 *
 * Aqui só "Configurar" continua visível na linha; Editar, Ver usuários e
 * Excluir passam a exigir a abertura deste menu. Editar e Excluir não
 * somem da plataforma: as versões completas vivem em
 * `[id]/perfil/perfil-client.tsx`, e este menu é o atalho.
 *
 * Sem biblioteca de UI: o projeto não tem nenhuma, e um `<details>`
 * (padrão de `move-card-menu.tsx`) não fecha em clique fora, que é o
 * comportamento esperado de um menu ancorado numa linha de tabela.
 */
type RowActionsMenuProps = {
  companyName: string;
  usuariosHref: string;
  onEdit: () => void;
  onDelete: () => void;
};

export function RowActionsMenu({
  companyName,
  usuariosHref,
  onEdit,
  onDelete,
}: RowActionsMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    function handlePointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      setIsOpen(false);
      // Devolve o foco ao gatilho: sem isso o foco fica no `body` e a
      // navegação por teclado recomeça do topo da página.
      triggerRef.current?.focus();
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  function runAndClose(action: () => void) {
    setIsOpen(false);
    action();
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        className="btn-ghost"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-label={`Mais ações para ${companyName}`}
        onClick={() => setIsOpen((prev) => !prev)}
      >
        <span aria-hidden="true" className="text-lg leading-none">
          ⋯
        </span>
      </button>

      {isOpen ? (
        <div
          role="menu"
          aria-label={`Ações de ${companyName}`}
          className="menu-panel"
        >
          <button
            type="button"
            role="menuitem"
            className="menu-item"
            onClick={() => runAndClose(onEdit)}
          >
            Editar dados
          </button>
          <Link
            role="menuitem"
            href={usuariosHref}
            className="menu-item"
            onClick={() => setIsOpen(false)}
          >
            Ver usuários
          </Link>
          <div className="my-1 border-t border-(--color-neutral)" />
          <button
            type="button"
            role="menuitem"
            className="menu-item text-red-700 hover:bg-red-50"
            onClick={() => runAndClose(onDelete)}
          >
            Excluir empresa
          </button>
        </div>
      ) : null}
    </div>
  );
}
