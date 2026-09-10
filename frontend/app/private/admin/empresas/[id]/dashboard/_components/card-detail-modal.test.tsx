// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CardDetailModal } from "./card-detail-modal";
import type { DashboardCardDetail } from "@/app/private/admin/actions";
import type { DashboardCardCategory } from "../actions";

function detalhe(
  sobrescreve: Partial<DashboardCardDetail> = {},
): DashboardCardDetail {
  return {
    id: 42,
    control_code: "8.8",
    title: "Gestão de Vulnerabilidades Técnicas",
    tag: "Tecnológico",
    status: "CONFORME",
    description: "Texto normativo do controle.",
    column_id: 3,
    category_id: 7,
    category_name: "Tecnológico",
    labels: [],
    checklist: [],
    history: [],
    chat: [],
    ...sobrescreve,
  };
}

const categorias: DashboardCardCategory[] = [
  { id: 7, name: "Tecnológico", color: "#788c5d", sort_order: 0 },
  { id: 8, name: "Pessoas", color: "#c0563b", sort_order: 1 },
];

const propsBase = {
  isLoading: false,
  isPending: false,
  onClose: vi.fn(),
};

describe("<CardDetailModal /> — casca", () => {
  it("é um diálogo nomeado pelo card e mostra o status no cabeçalho", () => {
    render(<CardDetailModal cardDetail={detalhe()} {...propsBase} />);

    const dialogo = screen.getByRole("dialog", {
      name: "Controle 8.8 - Gestão de Vulnerabilidades Técnicas",
    });
    expect(dialogo).toHaveAttribute("aria-modal", "true");
    expect(screen.getByText("Conforme")).toBeInTheDocument();
  });

  it("não duplica o título do card", () => {
    // O painel de detalhe renderizava o mesmo título que o cabeçalho do
    // modal — dois nomes acessíveis concorrentes para o mesmo card.
    render(<CardDetailModal cardDetail={detalhe()} {...propsBase} />);

    expect(
      screen.getAllByText(/Gestão de Vulnerabilidades Técnicas/),
    ).toHaveLength(1);
  });

  it("abre já anunciando o carregamento quando o detalhe ainda não chegou", () => {
    render(<CardDetailModal cardDetail={null} isLoading onClose={vi.fn()} isPending={false} />);

    expect(screen.getByText("Carregando card…")).toBeInTheDocument();
  });

  it("Esc fecha o modal", async () => {
    const usuario = userEvent.setup();
    const onClose = vi.fn();
    render(
      <CardDetailModal
        cardDetail={detalhe()}
        isLoading={false}
        isPending={false}
        onClose={onClose}
      />,
    );

    await usuario.keyboard("{Escape}");

    expect(onClose).toHaveBeenCalled();
  });

  it("clique DENTRO do modal não fecha", async () => {
    const usuario = userEvent.setup();
    const onClose = vi.fn();
    render(
      <CardDetailModal
        cardDetail={detalhe()}
        isLoading={false}
        isPending={false}
        onClose={onClose}
      />,
    );

    await usuario.click(screen.getByRole("dialog"));

    expect(onClose).not.toHaveBeenCalled();
  });
});

describe("<CardDetailModal /> — edição", () => {
  it("sem `onSaveCard` não existe botão Editar", () => {
    render(<CardDetailModal cardDetail={detalhe()} {...propsBase} />);

    expect(
      screen.queryByRole("button", { name: "Editar" }),
    ).not.toBeInTheDocument();
  });

  it("readOnly não oferece edição nem com `onSaveCard`", () => {
    // É o caso de /private/client/quadro: o cliente vê o card, não o edita.
    render(
      <CardDetailModal
        cardDetail={detalhe()}
        {...propsBase}
        readOnly
        onSaveCard={vi.fn()}
      />,
    );

    expect(
      screen.queryByRole("button", { name: "Editar" }),
    ).not.toBeInTheDocument();
  });

  it("Editar abre o formulário pré-preenchido com o estado atual do card", async () => {
    const usuario = userEvent.setup();
    render(
      <CardDetailModal
        cardDetail={detalhe()}
        {...propsBase}
        categories={categorias}
        onSaveCard={vi.fn()}
      />,
    );

    await usuario.click(screen.getByRole("button", { name: "Editar" }));

    expect(screen.getByLabelText("Título do card")).toHaveValue(
      "Gestão de Vulnerabilidades Técnicas",
    );
    expect(screen.getByLabelText("Código do controle")).toHaveValue("8.8");
    expect(screen.getByLabelText("Descrição do controle")).toHaveValue(
      "Texto normativo do controle.",
    );
    // O <select> tem de casar pelo id da categoria, não pela `tag`.
    expect(screen.getByLabelText("Categoria do card")).toHaveValue("7");
  });

  it("salvar envia os QUATRO campos, com vazio normalizado para null", async () => {
    const usuario = userEvent.setup();
    const onSaveCard = vi.fn();
    render(
      <CardDetailModal
        cardDetail={detalhe()}
        {...propsBase}
        categories={categorias}
        onSaveCard={onSaveCard}
      />,
    );

    await usuario.click(screen.getByRole("button", { name: "Editar" }));
    await usuario.clear(screen.getByLabelText("Código do controle"));
    await usuario.clear(screen.getByLabelText("Descrição do controle"));
    await usuario.selectOptions(
      screen.getByLabelText("Categoria do card"),
      "8",
    );
    await usuario.click(screen.getByRole("button", { name: "Salvar" }));

    // O PATCH é substituição total: os quatro campos vão sempre, e ""
    // vira null para não gravar string vazia em coluna nullable.
    expect(onSaveCard).toHaveBeenCalledWith({
      title: "Gestão de Vulnerabilidades Técnicas",
      description: null,
      controlCode: null,
      categoryId: 8,
    });
  });

  it("não salva card sem título", async () => {
    const usuario = userEvent.setup();
    const onSaveCard = vi.fn();
    render(
      <CardDetailModal
        cardDetail={detalhe()}
        {...propsBase}
        categories={categorias}
        onSaveCard={onSaveCard}
      />,
    );

    await usuario.click(screen.getByRole("button", { name: "Editar" }));
    await usuario.clear(screen.getByLabelText("Título do card"));

    expect(screen.getByRole("button", { name: "Salvar" })).toBeDisabled();
    expect(onSaveCard).not.toHaveBeenCalled();
  });

  it("Cancelar volta para o detalhe sem salvar", async () => {
    const usuario = userEvent.setup();
    const onSaveCard = vi.fn();
    render(
      <CardDetailModal
        cardDetail={detalhe()}
        {...propsBase}
        categories={categorias}
        onSaveCard={onSaveCard}
      />,
    );

    await usuario.click(screen.getByRole("button", { name: "Editar" }));
    await usuario.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(onSaveCard).not.toHaveBeenCalled();
    expect(screen.queryByLabelText("Título do card")).not.toBeInTheDocument();
    expect(screen.getByText("Checklist de conformidade")).toBeInTheDocument();
  });
});
