// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DeleteColumnDialog } from "./delete-column-dialog";
import type {
  Board as BoardData,
  BoardCard as BoardCardData,
  BoardColumn as BoardColumnData,
} from "../actions";

function card(id: number, oculto = false): BoardCardData {
  return {
    id,
    control_code: `5.${id}`,
    title: `Card ${id}`,
    description: null,
    status: "EM_ANALISE",
    position: `a${id}`,
    column_id: 10,
    category_id: null,
    category_name: null,
    labels: [],
    hidden: oculto,
    origin_template_card_id: null,
    is_outdated: false,
  };
}

function coluna(
  sobrescreve: Partial<BoardColumnData> = {},
): BoardColumnData {
  return {
    id: 10,
    name: "A fazer",
    kind: "COLUMN",
    position: "a0",
    hidden: false,
    wip_limit: null,
    cards: [],
    card_count: 0,
    ...sobrescreve,
  };
}

function quadro(colunas: BoardColumnData[]): BoardData {
  return {
    dashboard_id: 1,
    company_id: 7,
    title: "Quadro",
    columns: colunas,
    uncolumned: [],
    labels: [],
  };
}

const destino = coluna({ id: 12, name: "Concluído" });
const secao = coluna({
  id: 11,
  name: "ISO 27001:2022 >>",
  kind: "SECTION",
});

const propsBase = {
  isPending: false,
  onCancel: vi.fn(),
  onRelocateAndDelete: vi.fn(),
  onDelete: vi.fn(),
};

describe("coluna com cards visíveis", () => {
  const comCards = coluna({ cards: [card(1), card(2)], card_count: 2 });

  it("declara a contagem e o bloqueio ANTES de confirmar", () => {
    render(
      <DeleteColumnDialog
        {...propsBase}
        column={comCards}
        board={quadro([comCards, destino])}
      />,
    );

    // O `window.confirm` anterior dizia "os cards NÃO são apagados" e
    // nada mais: não dizia quantos, nem que o backend recusaria (409).
    expect(screen.getByText(/2 card\(s\) visível\(is\)/)).toBeInTheDocument();
    expect(screen.getByText(/recusada/)).toBeInTheDocument();
  });

  it("exige um destino antes de permitir a exclusão", async () => {
    const usuario = userEvent.setup();
    const onRelocateAndDelete = vi.fn();
    render(
      <DeleteColumnDialog
        {...propsBase}
        onRelocateAndDelete={onRelocateAndDelete}
        column={comCards}
        board={quadro([comCards, destino])}
      />,
    );

    const botao = screen.getByRole("button", {
      name: "Mover 2 card(s) e excluir",
    });
    expect(botao).toBeDisabled();

    await usuario.selectOptions(
      screen.getByLabelText("Coluna de destino dos cards"),
      "12",
    );
    await usuario.click(botao);

    expect(onRelocateAndDelete).toHaveBeenCalledWith(12);
  });

  it("não oferece a própria coluna nem seções como destino", () => {
    render(
      <DeleteColumnDialog
        {...propsBase}
        column={comCards}
        board={quadro([comCards, secao, destino])}
      />,
    );

    const opcoes = Array.from(
      screen
        .getByLabelText("Coluna de destino dos cards")
        .querySelectorAll("option"),
    ).map((opcao) => opcao.textContent);

    expect(opcoes).toContain("Concluído");
    // Mover para si mesma não resolve nada; seção não aceita card e o
    // servidor devolveria 422.
    expect(opcoes).not.toContain("A fazer");
    expect(opcoes).not.toContain("ISO 27001:2022 >>");
  });

  it("avisa quando não há destino possível", () => {
    render(
      <DeleteColumnDialog
        {...propsBase}
        column={comCards}
        board={quadro([comCards])}
      />,
    );

    expect(
      screen.getByText(/Não há outra coluna neste quadro/),
    ).toBeInTheDocument();
  });

  it("não oferece o caminho de exclusão direta", () => {
    render(
      <DeleteColumnDialog
        {...propsBase}
        column={comCards}
        board={quadro([comCards, destino])}
      />,
    );

    expect(
      screen.queryByRole("button", { name: /^Excluir coluna$/ }),
    ).not.toBeInTheDocument();
  });
});

describe("coluna sem cards visíveis", () => {
  it("exclui direto, sem pedir destino", async () => {
    const usuario = userEvent.setup();
    const onDelete = vi.fn();
    const vazia = coluna();
    render(
      <DeleteColumnDialog
        {...propsBase}
        onDelete={onDelete}
        column={vazia}
        board={quadro([vazia, destino])}
      />,
    );

    expect(
      screen.queryByLabelText("Coluna de destino dos cards"),
    ).not.toBeInTheDocument();
    await usuario.click(
      screen.getByRole("button", { name: "Excluir coluna" }),
    );

    expect(onDelete).toHaveBeenCalled();
  });

  it("card ARQUIVADO não bloqueia, mas o destino dele é declarado", () => {
    /*
     * `delete_column` conta só `hidden.is_(False)`, então card arquivado
     * não recusa a exclusão — ele cai no balde "Sem coluna" pela FK
     * `SET NULL`. Avisar disso é o que separa "não excluir dados
     * relacionados em silêncio" de fazê-lo.
     */
    const soOcultos = coluna({
      cards: [card(1, true), card(2, true)],
      card_count: 2,
    });
    render(
      <DeleteColumnDialog
        {...propsBase}
        column={soOcultos}
        board={quadro([soOcultos, destino])}
      />,
    );

    expect(screen.getByText(/2 card\(s\) arquivado\(s\)/)).toBeInTheDocument();
    expect(screen.getByText(/Sem coluna/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Excluir coluna" }),
    ).toBeEnabled();
  });
});

describe("seção (separador)", () => {
  it("exclui direto e explica que não afeta card nenhum", async () => {
    const usuario = userEvent.setup();
    const onDelete = vi.fn();
    render(
      <DeleteColumnDialog
        {...propsBase}
        onDelete={onDelete}
        column={secao}
        board={quadro([secao, destino])}
      />,
    );

    expect(
      screen.getByRole("dialog", {
        name: 'Excluir a seção "ISO 27001:2022 >>"?',
      }),
    ).toBeInTheDocument();
    expect(screen.getByText(/separador visual/)).toBeInTheDocument();
    expect(
      screen.queryByLabelText("Coluna de destino dos cards"),
    ).not.toBeInTheDocument();

    await usuario.click(screen.getByRole("button", { name: "Excluir seção" }));
    expect(onDelete).toHaveBeenCalled();
  });
});

describe("cancelar", () => {
  it("não exclui nada", async () => {
    const usuario = userEvent.setup();
    const onCancel = vi.fn();
    const onDelete = vi.fn();
    const vazia = coluna();
    render(
      <DeleteColumnDialog
        {...propsBase}
        onCancel={onCancel}
        onDelete={onDelete}
        column={vazia}
        board={quadro([vazia])}
      />,
    );

    await usuario.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(onCancel).toHaveBeenCalled();
    expect(onDelete).not.toHaveBeenCalled();
  });
});
