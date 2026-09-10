// @vitest-environment jsdom

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  Board,
  allCards,
  ancorasPorIndice,
  moveCardInBoard,
  type MoveIntent,
} from "./board";
import type { Board as BoardData, BoardCard } from "../actions";

function card(id: number, titulo: string, colunaId: number | null): BoardCard {
  return {
    id,
    control_code: `5.${id}`,
    title: titulo,
    description: null,
    status: "EM_ANALISE",
    position: `a${id}`,
    column_id: colunaId,
    category_id: null,
    category_name: null,
    labels: [],
    hidden: false,
    origin_template_card_id: null,
    is_outdated: false,
  };
}

function quadro(): BoardData {
  return {
    dashboard_id: 1,
    company_id: 7,
    title: "Dashboard - Empresa",
    columns: [
      {
        id: 10,
        name: "A fazer",
        kind: "COLUMN",
        position: "a0",
        hidden: false,
        wip_limit: null,
        cards: [card(1, "Política de SI", 10), card(2, "Inventário", 10)],
        card_count: 2,
      },
      {
        id: 11,
        name: "ISO 27001:2022 >>",
        kind: "SECTION",
        position: "a1",
        hidden: false,
        wip_limit: null,
        cards: [],
        card_count: 0,
      },
      {
        id: 12,
        name: "Concluído",
        kind: "COLUMN",
        position: "a2",
        hidden: false,
        wip_limit: null,
        cards: [card(3, "Backup", 12)],
        card_count: 1,
      },
    ],
    uncolumned: [],
    labels: [],
  };
}

const propsBase = {
  selectedCardId: null,
  onSelectCard: vi.fn(),
};

describe("moveCardInBoard (núcleo do otimismo — CA-16)", () => {
  it("move o card para outra coluna, no fim", () => {
    const intent: MoveIntent = {
      cardId: 1,
      columnId: 12,
      prevCardId: 3,
      nextCardId: null,
    };

    const resultado = moveCardInBoard(quadro(), intent);

    expect(resultado.columns[0].cards.map((c) => c.id)).toEqual([2]);
    expect(resultado.columns[2].cards.map((c) => c.id)).toEqual([3, 1]);
    expect(resultado.columns[2].card_count).toBe(2);
  });

  it("move o card para o início da coluna de destino", () => {
    const resultado = moveCardInBoard(quadro(), {
      cardId: 1,
      columnId: 12,
      prevCardId: null,
      nextCardId: 3,
    });

    expect(resultado.columns[2].cards.map((c) => c.id)).toEqual([1, 3]);
  });

  it("reordena dentro da mesma coluna", () => {
    const resultado = moveCardInBoard(quadro(), {
      cardId: 1,
      columnId: 10,
      prevCardId: 2,
      nextCardId: null,
    });

    expect(resultado.columns[0].cards.map((c) => c.id)).toEqual([2, 1]);
  });

  it("não muta o quadro original", () => {
    const original = quadro();
    const antes = JSON.stringify(original);

    moveCardInBoard(original, {
      cardId: 1,
      columnId: 12,
      prevCardId: null,
      nextCardId: null,
    });

    expect(JSON.stringify(original)).toBe(antes);
  });

  it("devolve o mesmo quadro quando o card não existe", () => {
    const original = quadro();
    expect(
      moveCardInBoard(original, {
        cardId: 999,
        columnId: 12,
        prevCardId: null,
        nextCardId: null,
      }),
    ).toBe(original);
  });
});

describe("ancorasPorIndice", () => {
  it("no início devolve prev nulo", () => {
    const cards = quadro().columns[0].cards;
    expect(ancorasPorIndice(cards, 99, 0)).toEqual({
      prevCardId: null,
      nextCardId: 1,
    });
  });

  it("no fim devolve next nulo", () => {
    const cards = quadro().columns[0].cards;
    expect(ancorasPorIndice(cards, 99, 2)).toEqual({
      prevCardId: 2,
      nextCardId: null,
    });
  });

  it("ignora o próprio card ao calcular as âncoras", () => {
    const cards = quadro().columns[0].cards;
    expect(ancorasPorIndice(cards, 1, 0)).toEqual({
      prevCardId: null,
      nextCardId: 2,
    });
  });
});

describe("allCards", () => {
  it("inclui os cards sem coluna", () => {
    const comOrfao = { ...quadro(), uncolumned: [card(9, "Órfão", null)] };
    expect(allCards(comOrfao).map((c) => c.id)).toEqual([1, 2, 3, 9]);
  });
});

describe("<Board /> — renderização", () => {
  it("renderiza colunas e cards na ordem recebida (CA-05)", () => {
    render(<Board board={quadro()} {...propsBase} />);

    const colunaA = screen.getByTestId("column-10");
    expect(within(colunaA).getByText("Política de SI")).toBeInTheDocument();
    expect(within(colunaA).getByText(/2\s*card\(s\)/)).toBeInTheDocument();
  });

  it("readOnly esconde todo controle de edição (CA-17)", () => {
    render(<Board board={quadro()} readOnly {...propsBase} />);

    expect(screen.queryByText("Mover para…")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Arrastar o card/ }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("checkbox", { name: /Selecionar/ }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Ações da coluna/ }),
    ).not.toBeInTheDocument();
    // O conteúdo continua visível — é modo LEITURA, não tela vazia.
    expect(screen.getByText("Política de SI")).toBeInTheDocument();
  });

  it("mostra o balde de cards sem coluna", () => {
    const comOrfao = { ...quadro(), uncolumned: [card(9, "Órfão", null)] };
    render(<Board board={comOrfao} {...propsBase} />);

    expect(screen.getByText("Sem coluna")).toBeInTheDocument();
    expect(screen.getByText("Órfão")).toBeInTheDocument();
  });

  it("seleção em massa continua funcionando sobre o quadro (CA-21)", async () => {
    const usuario = userEvent.setup();
    const onToggleCardSelection = vi.fn();

    render(
      <Board
        board={quadro()}
        {...propsBase}
        selectedCardIds={new Set()}
        onToggleCardSelection={onToggleCardSelection}
      />,
    );

    await usuario.click(
      screen.getByRole("checkbox", { name: "Selecionar Política de SI" }),
    );

    expect(onToggleCardSelection).toHaveBeenCalledWith(1);
  });

  it("colapsar coluna esconde os cards dela (CA-21)", () => {
    render(
      <Board
        board={quadro()}
        {...propsBase}
        collapsedColumns={new Set([10])}
        onToggleColumnCollapse={vi.fn()}
      />,
    );

    expect(screen.queryByText("Política de SI")).not.toBeInTheDocument();
    expect(screen.getByText("Backup")).toBeInTheDocument();
  });

  it("com todas as faixas recolhidas, nenhum card aparece e o quadro segue navegável", () => {
    render(
      <Board
        board={quadro()}
        {...propsBase}
        collapsedColumns={new Set([10, 12])}
        onToggleColumnCollapse={vi.fn()}
      />,
    );

    // É este o estado inicial do Dashboard: as faixas se anunciam, os
    // 215 cards não são despejados de uma vez.
    expect(screen.queryByText("Política de SI")).not.toBeInTheDocument();
    expect(screen.queryByText("Backup")).not.toBeInTheDocument();
    expect(screen.getByTestId("column-10")).toBeInTheDocument();
    expect(screen.getByTestId("column-12")).toBeInTheDocument();
    // A seção é um separador: não recolhe nem esconde nada.
    expect(screen.getByTestId("section-11")).toBeInTheDocument();
  });

  it("quadro sem colunas mostra a mensagem de vazio", () => {
    render(<Board board={{ ...quadro(), columns: [] }} {...propsBase} />);

    expect(
      screen.getByText("Este quadro ainda não tem colunas."),
    ).toBeInTheDocument();
  });
});
