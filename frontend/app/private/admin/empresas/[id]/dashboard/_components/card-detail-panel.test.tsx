// @vitest-environment jsdom

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CardDetailPanel } from "./card-detail-panel";
import type { DashboardCardDetail } from "@/app/private/admin/actions";

function detalhe(
  sobrescreve: Partial<DashboardCardDetail> = {},
): DashboardCardDetail {
  return {
    id: 42,
    control_code: "8.8",
    title: "Gestão de Vulnerabilidades Técnicas",
    tag: "Tecnológico",
    status: "CONFORME",
    description: null,
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

const propsBase = { isLoading: false, isPending: false };

describe("Checklist de conformidade", () => {
  it("mostra o progresso como texto e como barra", () => {
    render(
      <CardDetailPanel
        {...propsBase}
        cardDetail={detalhe({
          checklist: [
            { id: 1, title: "Evidência documental", done: true },
            { id: 2, title: "Evidência validada", done: false },
          ],
        })}
      />,
    );

    expect(screen.getByText("1 de 2 itens concluídos")).toBeInTheDocument();
    expect(
      screen.getByRole("progressbar", { name: "Progresso do checklist" }),
    ).toHaveAttribute("aria-valuenow", "50");
  });

  it("checklist vazio não divide por zero", () => {
    render(<CardDetailPanel {...propsBase} cardDetail={detalhe()} />);

    expect(screen.getByText("0 de 0 itens concluídos")).toBeInTheDocument();
    expect(
      screen.getByRole("progressbar", { name: "Progresso do checklist" }),
    ).toHaveAttribute("aria-valuenow", "0");
  });

  it("adicionar item envia o texto e limpa o campo", async () => {
    const usuario = userEvent.setup();
    const onAddChecklistItem = vi.fn();
    render(
      <CardDetailPanel
        {...propsBase}
        cardDetail={detalhe()}
        onAddChecklistItem={onAddChecklistItem}
      />,
    );

    const campo = screen.getByLabelText("Novo item de checklist");
    await usuario.type(campo, "  Evidência aprovada pelo time  ");
    await usuario.click(screen.getByRole("button", { name: "+ Item" }));

    expect(onAddChecklistItem).toHaveBeenCalledWith(
      "Evidência aprovada pelo time",
    );
    expect(campo).toHaveValue("");
  });

  it("não adiciona item em branco", async () => {
    const usuario = userEvent.setup();
    const onAddChecklistItem = vi.fn();
    render(
      <CardDetailPanel
        {...propsBase}
        cardDetail={detalhe()}
        onAddChecklistItem={onAddChecklistItem}
      />,
    );

    await usuario.type(screen.getByLabelText("Novo item de checklist"), "   ");

    expect(screen.getByRole("button", { name: "+ Item" })).toBeDisabled();
    expect(onAddChecklistItem).not.toHaveBeenCalled();
  });

  it("marcar e remover item chamam os handlers com o id certo", async () => {
    const usuario = userEvent.setup();
    const onToggleChecklistItem = vi.fn();
    const onDeleteChecklistItem = vi.fn();
    render(
      <CardDetailPanel
        {...propsBase}
        cardDetail={detalhe({
          checklist: [{ id: 11, title: "Evidência documental", done: false }],
        })}
        onToggleChecklistItem={onToggleChecklistItem}
        onDeleteChecklistItem={onDeleteChecklistItem}
      />,
    );

    await usuario.click(screen.getByRole("checkbox", { name: "Evidência documental" }));
    expect(onToggleChecklistItem).toHaveBeenCalledWith(11);

    await usuario.click(
      screen.getByRole("button", { name: "Remover item Evidência documental" }),
    );
    expect(onDeleteChecklistItem).toHaveBeenCalledWith(11);
  });

  it("sem handler de remoção não existe botão Remover", () => {
    render(
      <CardDetailPanel
        {...propsBase}
        cardDetail={detalhe({
          checklist: [{ id: 11, title: "Evidência documental", done: false }],
        })}
      />,
    );

    expect(screen.queryByRole("button", { name: /Remover item/ })).not.toBeInTheDocument();
  });
});

describe("Histórico", () => {
  it("mostra o que mudou, quando e quem fez", () => {
    render(
      <CardDetailPanel
        {...propsBase}
        cardDetail={detalhe({
          history: [
            {
              id: 1,
              action: "Status alterado para CONFORME",
              created_at: "2026-09-09T14:35:00+00:00",
              actor_user: { id: 3, full_name: "Ana Auditora" },
            },
          ],
        })}
      />,
    );

    expect(
      screen.getByText("Status alterado para CONFORME"),
    ).toBeInTheDocument();
    // Data, hora e autor — os dois últimos vinham do backend e eram
    // descartados pelos tipos do frontend.
    expect(screen.getByText(/09\/09\/2026/)).toBeInTheDocument();
    expect(screen.getByText(/Ana Auditora/)).toBeInTheDocument();
  });

  it("entrada sem autor não escreve 'null' na tela", () => {
    render(
      <CardDetailPanel
        {...propsBase}
        cardDetail={detalhe({
          history: [
            {
              id: 1,
              action: "Card criado",
              created_at: "2026-09-09T14:35:00+00:00",
              actor_user: null,
            },
          ],
        })}
      />,
    );

    expect(screen.queryByText(/null/)).not.toBeInTheDocument();
    expect(screen.getByText(/09\/09\/2026/)).toBeInTheDocument();
  });

  it("readOnly esconde checklist e histórico do cliente (B-A28)", () => {
    render(
      <CardDetailPanel {...propsBase} cardDetail={detalhe()} readOnly />,
    );

    expect(
      screen.queryByText("Checklist de conformidade"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Histórico")).not.toBeInTheDocument();
    // A conversa é bilateral: continua lá.
    expect(screen.getByText("Conversa com o cliente")).toBeInTheDocument();
  });
});

describe("Conversa com o cliente", () => {
  it("identifica autor, data e lado de cada mensagem", () => {
    render(
      <CardDetailPanel
        {...propsBase}
        cardDetail={detalhe({
          chat: [
            {
              id: 1,
              message_type: "QUESTION",
              content: "Qual evidência devo enviar?",
              created_at: "2026-09-09T10:00:00+00:00",
              author_user: { id: 9, full_name: "Cliente Silva" },
            },
            {
              id: 2,
              message_type: "ANSWER",
              content: "O relatório de varredura.",
              created_at: "2026-09-09T11:00:00+00:00",
              author_user: { id: 3, full_name: "Ana Auditora" },
            },
          ],
        })}
      />,
    );

    const pergunta = screen.getByText("Qual evidência devo enviar?")
      .parentElement as HTMLElement;
    expect(within(pergunta).getByText(/Cliente Silva/)).toBeInTheDocument();
    // Cor de fundo sozinha não é informação acessível.
    expect(within(pergunta).getByText(/pergunta/)).toBeInTheDocument();

    const resposta = screen.getByText("O relatório de varredura.")
      .parentElement as HTMLElement;
    expect(
      within(resposta).getByText(/resposta da auditoria/),
    ).toBeInTheDocument();
  });

  it("enviar mensagem repassa o texto e limpa o campo", async () => {
    const usuario = userEvent.setup();
    const onSendMessage = vi.fn();
    render(
      <CardDetailPanel
        {...propsBase}
        cardDetail={detalhe()}
        onSendMessage={onSendMessage}
      />,
    );

    const campo = screen.getByLabelText("Nova mensagem");
    await usuario.type(campo, "Evidência recebida.");
    await usuario.click(screen.getByRole("button", { name: "Enviar" }));

    expect(onSendMessage).toHaveBeenCalledWith("Evidência recebida.");
    expect(campo).toHaveValue("");
  });

  it("o cliente também pode escrever, mesmo em readOnly", async () => {
    const usuario = userEvent.setup();
    const onSendMessage = vi.fn();
    render(
      <CardDetailPanel
        {...propsBase}
        cardDetail={detalhe()}
        readOnly
        onSendMessage={onSendMessage}
      />,
    );

    await usuario.type(screen.getByLabelText("Nova mensagem"), "Dúvida.");
    await usuario.click(screen.getByRole("button", { name: "Enviar" }));

    // A conversa é a única escrita que `readOnly` não bloqueia: uma
    // "conversa com o cliente" em que só o auditor escreve não é conversa.
    expect(onSendMessage).toHaveBeenCalledWith("Dúvida.");
  });

  it("sem handler de envio não existe formulário de mensagem", () => {
    render(<CardDetailPanel {...propsBase} cardDetail={detalhe()} />);

    expect(screen.queryByLabelText("Nova mensagem")).not.toBeInTheDocument();
  });
});
