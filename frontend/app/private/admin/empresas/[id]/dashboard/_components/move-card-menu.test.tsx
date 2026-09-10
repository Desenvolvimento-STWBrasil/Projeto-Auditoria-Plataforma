// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MoveCardMenu } from "./move-card-menu";
import type {
  Board as BoardData,
  BoardCard as BoardCardData,
} from "../actions";

function card(
  id: number,
  titulo: string,
  colunaId: number | null,
): BoardCardData {
  return {
    id,
    control_code: null,
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

const board: BoardData = {
  dashboard_id: 1,
  company_id: 7,
  title: "Dashboard",
  columns: [
    {
      id: 10,
      name: "A fazer",
      kind: "COLUMN",
      position: "a0",
      hidden: false,
      wip_limit: null,
      cards: [card(1, "Política de SI", 10)],
      card_count: 1,
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
      cards: [card(2, "Backup", 12), card(3, "Inventário", 12)],
      card_count: 2,
    },
  ],
  uncolumned: [],
  labels: [],
};

const onMoveCard = vi.fn();

beforeEach(() => {
  onMoveCard.mockReset();
});

describe("MoveCardMenu (CA-15 — mover sem arrasto nenhum)", () => {
  it("não oferece colunas do tipo SECTION como destino (CA-18)", async () => {
    const usuario = userEvent.setup();
    render(
      <MoveCardMenu
        card={card(1, "Política de SI", 10)}
        board={board}
        onMoveCard={onMoveCard}
      />,
    );
    await usuario.click(screen.getByText("Mover para…"));

    const seletor = screen.getByLabelText(
      "Coluna de destino para Política de SI",
    );
    const opcoes = Array.from(seletor.querySelectorAll("option")).map(
      (o) => o.textContent,
    );

    expect(opcoes).toContain("A fazer");
    expect(opcoes).toContain("Concluído");
    expect(opcoes).not.toContain("ISO 27001:2022 >>");
  });

  it("move para o início de outra coluna com as âncoras certas", async () => {
    const usuario = userEvent.setup();
    render(
      <MoveCardMenu
        card={card(1, "Política de SI", 10)}
        board={board}
        onMoveCard={onMoveCard}
      />,
    );
    await usuario.click(screen.getByText("Mover para…"));

    await usuario.selectOptions(
      screen.getByLabelText("Coluna de destino para Política de SI"),
      "12",
    );
    await usuario.selectOptions(
      screen.getByLabelText("Posição de destino para Política de SI"),
      "0",
    );
    await usuario.click(screen.getByRole("button", { name: "Mover" }));

    expect(onMoveCard).toHaveBeenCalledWith({
      cardId: 1,
      columnId: 12,
      prevCardId: null,
      nextCardId: 2,
    });
  });

  it("move para o fim de outra coluna", async () => {
    const usuario = userEvent.setup();
    render(
      <MoveCardMenu
        card={card(1, "Política de SI", 10)}
        board={board}
        onMoveCard={onMoveCard}
      />,
    );
    await usuario.click(screen.getByText("Mover para…"));

    await usuario.selectOptions(
      screen.getByLabelText("Coluna de destino para Política de SI"),
      "12",
    );
    await usuario.selectOptions(
      screen.getByLabelText("Posição de destino para Política de SI"),
      "2",
    );
    await usuario.click(screen.getByRole("button", { name: "Mover" }));

    expect(onMoveCard).toHaveBeenCalledWith({
      cardId: 1,
      columnId: 12,
      prevCardId: 3,
      nextCardId: null,
    });
  });

  it("reordena dentro da própria coluna sem se tomar como âncora", async () => {
    const usuario = userEvent.setup();
    render(
      <MoveCardMenu
        card={card(2, "Backup", 12)}
        board={board}
        onMoveCard={onMoveCard}
      />,
    );
    await usuario.click(screen.getByText("Mover para…"));

    await usuario.selectOptions(
      screen.getByLabelText("Posição de destino para Backup"),
      "1",
    );
    await usuario.click(screen.getByRole("button", { name: "Mover" }));

    expect(onMoveCard).toHaveBeenCalledWith({
      cardId: 2,
      columnId: 12,
      prevCardId: 3,
      nextCardId: null,
    });
  });

  it("o botão Mover fica desabilitado enquanto não houver coluna escolhida", async () => {
    const usuario = userEvent.setup();
    render(
      <MoveCardMenu
        card={card(9, "Órfão", null)}
        board={board}
        onMoveCard={onMoveCard}
      />,
    );
    await usuario.click(screen.getByText("Mover para…"));

    expect(screen.getByRole("button", { name: "Mover" })).toBeDisabled();
  });
});
