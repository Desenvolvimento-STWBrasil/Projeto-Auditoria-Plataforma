// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DndContext } from "@dnd-kit/core";

import { BoardColumn } from "./board-column";
import type {
  Board as BoardData,
  BoardCard as BoardCardData,
  BoardColumn as BoardColumnData,
} from "../actions";

function card(id: number, titulo: string): BoardCardData {
  return {
    id,
    control_code: null,
    title: titulo,
    description: null,
    status: "EM_ANALISE",
    position: `a${id}`,
    column_id: 10,
    category_id: null,
    category_name: null,
    labels: [],
    hidden: false,
    origin_template_card_id: 1,
    is_outdated: false,
  };
}

const colunaComum: BoardColumnData = {
  id: 10,
  name: "A fazer",
  kind: "COLUMN",
  position: "a0",
  hidden: false,
  wip_limit: null,
  cards: [card(1, "Política de SI")],
  card_count: 1,
};

const secao: BoardColumnData = {
  id: 11,
  name: "ISO 27001:2022 >>",
  kind: "SECTION",
  position: "a1",
  hidden: false,
  wip_limit: null,
  cards: [],
  card_count: 0,
};

const board: BoardData = {
  dashboard_id: 1,
  company_id: 7,
  title: "Dashboard",
  columns: [colunaComum, secao],
  uncolumned: [],
  labels: [],
};

const handlers = {
  onRenameColumn: vi.fn(),
  onArchiveColumn: vi.fn(),
  onDeleteColumn: vi.fn(),
  onMoveColumn: vi.fn(),
  onAddCard: vi.fn(),
};

function renderColuna(
  column: BoardColumnData,
  extras: Record<string, unknown> = {},
) {
  return render(
    <DndContext>
      <BoardColumn
        column={column}
        board={board}
        readOnly={false}
        isFirst={false}
        isLast={false}
        collapsed={false}
        selectedCardId={null}
        onSelectCard={vi.fn()}
        outdatedCardIds={[]}
        columnHandlers={handlers}
        {...extras}
      />
    </DndContext>,
  );
}

describe("coluna do tipo SECTION (CA-18)", () => {
  it("renderiza como separador horizontal, sem contador de cards", () => {
    renderColuna(secao);

    const separador = screen.getByRole("separator", {
      name: "Seção ISO 27001:2022 >>",
    });
    expect(separador).toBeInTheDocument();
    // No quadro em linhas o separador divide faixas, não colunas.
    expect(separador).toHaveAttribute("aria-orientation", "horizontal");
    expect(screen.queryByText(/card\(s\)/)).not.toBeInTheDocument();
  });

  it("não oferece área de soltar nem + Adicionar card", () => {
    renderColuna(secao);

    // Seção não aceita card por definição: oferecê-la como destino faria
    // o servidor recusar com 422 depois do arrasto já ter "acontecido".
    expect(
      screen.queryByRole("button", { name: /Adicionar card/ }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/card\(s\)/)).not.toBeInTheDocument();
  });

  it("oferece as MESMAS ações da faixa, com rótulo de seção", async () => {
    const usuario = userEvent.setup();
    renderColuna(secao);

    // Até aqui a seção renderizava só o nome: não havia como renomeá-la,
    // reordená-la, arquivá-la nem excluí-la pela tela, embora o backend
    // aceitasse as quatro.
    await usuario.click(
      screen.getByRole("button", { name: "Ações da seção ISO 27001:2022 >>" }),
    );
    await usuario.click(screen.getByRole("button", { name: "Excluir" }));

    expect(handlers.onDeleteColumn).toHaveBeenCalledWith(secao);
  });

  it("o rótulo acessível diz 'seção', não 'coluna'", () => {
    renderColuna(secao);

    expect(
      screen.getByRole("button", {
        name: "Mover seção ISO 27001:2022 >> para cima",
      }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Mover coluna/ }),
    ).not.toBeInTheDocument();
  });

  it("readOnly esconde o menu da seção (CA-17)", () => {
    render(
      <DndContext>
        <BoardColumn
          column={secao}
          board={board}
          readOnly
          isFirst={false}
          isLast={false}
          collapsed={false}
          selectedCardId={null}
          onSelectCard={vi.fn()}
          outdatedCardIds={[]}
        />
      </DndContext>,
    );

    expect(
      screen.queryByRole("button", { name: /Ações da seção/ }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("separator")).toBeInTheDocument();
  });
});

describe("coluna comum", () => {
  it("mostra nome e contador", () => {
    renderColuna(colunaComum);

    expect(screen.getByText(/A fazer/)).toBeInTheDocument();
    expect(screen.getByText(/1\s*card\(s\)/)).toBeInTheDocument();
  });

  it("mostra o limite de WIP e destaca quando estourado", () => {
    renderColuna({
      ...colunaComum,
      wip_limit: 1,
      cards: [card(1, "Política de SI"), card(2, "Inventário")],
      card_count: 2,
    });

    const contador = screen.getByText(/2\/1\s*card\(s\)/);
    expect(contador).toBeInTheDocument();
    expect(contador.className).toContain("text-red-600");
  });

  it("marca a coluna arquivada", () => {
    renderColuna({ ...colunaComum, hidden: true });

    expect(screen.getByText("arquivada")).toBeInTheDocument();
  });

  it("aciona o menu de renomear", async () => {
    const usuario = userEvent.setup();
    renderColuna(colunaComum);

    await usuario.click(
      screen.getByRole("button", { name: "Ações da coluna A fazer" }),
    );
    await usuario.click(screen.getByRole("button", { name: "Renomear" }));

    expect(handlers.onRenameColumn).toHaveBeenCalledWith(colunaComum);
  });

  it("desabilita a seta de mover na ponta do quadro", () => {
    renderColuna(colunaComum, { isFirst: true });

    expect(
      screen.getByRole("button", {
        name: "Mover coluna A fazer para cima",
      }),
    ).toBeDisabled();
  });

  it("o cabeçalho da faixa recolhe e expande os cards (accordion)", async () => {
    const usuario = userEvent.setup();
    const onToggleCollapse = vi.fn();
    renderColuna(colunaComum, { onToggleCollapse });

    const barra = screen.getByRole("button", { expanded: true });
    await usuario.click(barra);

    expect(onToggleCollapse).toHaveBeenCalledWith(10);
  });

  it("faixa recolhida esconde os cards mas mantém nome e contador", () => {
    renderColuna(colunaComum, { collapsed: true });

    expect(screen.queryByText("Política de SI")).not.toBeInTheDocument();
    expect(screen.getByText(/A fazer/)).toBeInTheDocument();
    expect(screen.getByText(/1\s*card\(s\)/)).toBeInTheDocument();
    expect(screen.getByRole("button", { expanded: false })).toBeInTheDocument();
  });

  it("coluna vazia mostra a mensagem de vazio", () => {
    renderColuna({ ...colunaComum, cards: [], card_count: 0 });

    expect(screen.getByText("Nenhum card nesta coluna.")).toBeInTheDocument();
  });

  it("readOnly esconde o menu e o + Adicionar card (CA-17)", () => {
    render(
      <BoardColumn
        column={colunaComum}
        board={board}
        readOnly
        isFirst={false}
        isLast={false}
        collapsed={false}
        selectedCardId={null}
        onSelectCard={vi.fn()}
        outdatedCardIds={[]}
      />,
    );

    expect(
      screen.queryByRole("button", { name: /Ações da coluna/ }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Política de SI")).toBeInTheDocument();
  });
});
