"use client";

import {
  useEffect,
  useMemo,
  useOptimistic,
  useState,
  useTransition,
} from "react";
import {
  createCardEntryAction,
  deleteChecklistItemAction,
  getCardDetailAction,
  updateCardStatusAction,
  toggleChecklistItemAction,
  type CardStatus,
  type DashboardCardDetail,
} from "@/app/private/admin/actions";
import {
  applyTemplateToCompanyAction,
  bulkUpdateCardsAction,
  createCardForCompanyAction,
  createColumnAction,
  deleteColumnAction,
  getBoardAction,
  moveCardAction,
  moveColumnAction,
  setCardLabelsAction,
  updateCardAction,
  updateColumnAction,
  type Board as BoardData,
  type BoardCard as BoardCardData,
  type BoardColumn as BoardColumnData,
  type DashboardCardCategory,
  type DashboardLabel,
  type DashboardTemplateOption,
} from "./actions";
import {
  Board,
  allCards,
  moveCardInBoard,
  type ColumnMenuHandlers,
  type MoveIntent,
} from "./_components/board";
import { CardDetailModal } from "./_components/card-detail-modal";
import type { CardEditInput } from "./_components/card-edit-form";
import { DeleteColumnDialog } from "./_components/delete-column-dialog";

type CompanyDashboardClientProps = {
  companyId: number;
  companyName: string;
  initialBoard: BoardData;
  categories: DashboardCardCategory[];
  labels: DashboardLabel[];
  templates: DashboardTemplateOption[];
};

export function CompanyDashboardClient({
  companyId,
  companyName,
  initialBoard,
  categories,
  labels,
  templates,
}: CompanyDashboardClientProps) {
  const [board, setBoard] = useState<BoardData>(initialBoard);
  /*
   * O arrasto reposiciona o card NA HORA e a Server Action confirma
   * depois (CA-16). Se a action falhar, o React descarta o estado
   * otimista sozinho ao fim da transição — não precisamos (nem devemos)
   * "desfazer" à mão: desfazer manualmente correria contra o descarte
   * automático e produziria um piscar duplo.
   */
  const [quadroOtimista, aplicarMovimentoOtimista] = useOptimistic(
    board,
    (estado: BoardData, intent: MoveIntent) => moveCardInBoard(estado, intent),
  );

  /*
   * `categories` é PROP, não estado: quem cria/edita/exclui categoria é a
   * aba Templates, porque categoria é vocabulário GLOBAL — não pertence a
   * empresa nenhuma. O quadro só consome a lista, para o "+ Adicionar
   * card" e para o "Mudar categoria" em lote.
   */
  /*
   * `null` = nenhum card aberto, e é assim que a tela carrega. Antes o
   * primeiro card visível vinha pré-selecionado (com o detalhe dele
   * buscado no servidor, em page.tsx) porque o painel de detalhe era
   * fixo no rodapé e ficaria vazio sem isso. Com o modal, uma seleção
   * inicial abriria um diálogo por cima do quadro em todo carregamento —
   * e a busca extra no servidor deixou de ter para quê.
   */
  const [cardSelecionadoId, setCardSelecionadoId] = useState<number | null>(
    null,
  );
  const [cardDetail, setCardDetail] = useState<DashboardCardDetail | null>(
    null,
  );
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);

  const [busca, setBusca] = useState("");
  const [showHidden, setShowHidden] = useState(false);
  /*
   * Nasce com TODAS as faixas recolhidas. Era o contrário (Set vazio =
   * tudo aberto), e com 25 colunas o quadro abria despejando os 215
   * cards de uma vez — o problema que o accordion existe para resolver.
   *
   * Faixa criada DEPOIS do carregamento não entra neste conjunto, então
   * aparece aberta: quem acabou de criar uma coluna quer vê-la.
   */
  const [collapsedColumns, setCollapsedColumns] = useState<Set<number>>(
    () => new Set(initialBoard.columns.map((coluna) => coluna.id)),
  );
  const [selectedCardIds, setSelectedCardIds] = useState<Set<number>>(
    new Set(),
  );
  const [outdatedFromLastApply, setOutdatedFromLastApply] = useState<number[]>(
    [],
  );
  const [feedback, setFeedback] = useState("");
  const [isPending, startTransition] = useTransition();

  /*
   * Busca o detalhe do card sob demanda ao abrir o modal.
   *
   * O `isFirstRender` que existia aqui foi removido junto com o
   * pré-carregamento: ele pulava a primeira execução porque o detalhe
   * inicial vinha por props. Sem props, pular a primeira execução
   * deixaria o modal preso em "Carregando card…" se o quadro abrisse já
   * com um card selecionado.
   */
  useEffect(() => {
    if (cardSelecionadoId === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setCardDetail(null);
      return;
    }

    let cancelado = false;
    setIsLoadingDetail(true);
    getCardDetailAction(cardSelecionadoId)
      .then((detail) => {
        if (!cancelado) setCardDetail(detail);
      })
      .catch(() => {
        if (!cancelado) setCardDetail(null);
      })
      .finally(() => {
        if (!cancelado) setIsLoadingDetail(false);
      });

    return () => {
      cancelado = true;
    };
  }, [cardSelecionadoId]);

  /*
   * O quadro chega do servidor JÁ AGRUPADO (D-5): o que sobra para o
   * cliente é só o FILTRO — busca, cards ocultos e colunas arquivadas.
   * As 38 linhas de `groups: CardGroup[]` que existiam aqui migraram
   * para `services/dashboard_board.py::get_board`.
   */
  const quadroVisivel: BoardData = useMemo(() => {
    const termo = busca.trim().toLocaleLowerCase();

    const passaNoFiltro = (card: BoardCardData) => {
      if (!showHidden && card.hidden) return false;
      if (!termo) return true;
      return (
        card.title.toLocaleLowerCase().includes(termo) ||
        (card.control_code ?? "").toLocaleLowerCase().includes(termo)
      );
    };

    return {
      ...quadroOtimista,
      columns: quadroOtimista.columns
        // CA-19: coluna arquivada só aparece com o toggle ligado — mesmo
        // comportamento que `showHidden` já tinha para cards.
        .filter((coluna) => showHidden || !coluna.hidden)
        .map((coluna) => {
          const cards = coluna.cards.filter(passaNoFiltro);
          return { ...coluna, cards, card_count: cards.length };
        }),
      uncolumned: quadroOtimista.uncolumned.filter(passaNoFiltro),
    };
  }, [quadroOtimista, busca, showHidden]);

  /*
   * Buscar ABRE tudo. Sem isto, o accordion recolhido por padrão
   * quebraria a busca que já existia: o admin digita "8.8", o filtro
   * encontra o card, e a tela continua mostrando só faixas fechadas —
   * indistinguível de "não achei nada".
   */
  const colunasRecolhidas = useMemo(
    () => (busca.trim() ? new Set<number>() : collapsedColumns),
    [busca, collapsedColumns],
  );

  const todosOsCards = useMemo(
    () => allCards(quadroOtimista),
    [quadroOtimista],
  );
  const totalVisivel = todosOsCards.filter((card) => !card.hidden).length;
  const totalOculto = todosOsCards.length - totalVisivel;

  async function refreshBoard() {
    // `include_hidden=true` sempre: o filtro de ocultos é do cliente, e
    // recarregar sem eles faria o toggle "Mostrar ocultos" parar de
    // funcionar até o próximo F5.
    const fresco = await getBoardAction(companyId, true);
    setBoard(fresco);
    setSelectedCardIds(new Set());
  }

  function toggleColumnCollapse(columnId: number) {
    setCollapsedColumns((prev) => {
      const next = new Set(prev);
      if (next.has(columnId)) next.delete(columnId);
      else next.add(columnId);
      return next;
    });
  }

  function expandirTodas() {
    setCollapsedColumns(new Set());
  }

  function recolherTodas() {
    // Sobre o quadro OTIMISTA e não sobre `initialBoard`: colunas criadas
    // durante a sessão também precisam recolher.
    setCollapsedColumns(
      new Set(quadroOtimista.columns.map((coluna) => coluna.id)),
    );
  }

  function toggleCardSelection(cardId: number) {
    setSelectedCardIds((prev) => {
      const next = new Set(prev);
      if (next.has(cardId)) next.delete(cardId);
      else next.add(cardId);
      return next;
    });
  }

  function toggleColumnSelection(column: BoardColumnData) {
    const ids = column.cards.map((card) => card.id);
    const todosSelecionados = ids.every((id) => selectedCardIds.has(id));
    setSelectedCardIds((prev) => {
      const next = new Set(prev);
      for (const id of ids) {
        if (todosSelecionados) next.delete(id);
        else next.add(id);
      }
      return next;
    });
  }

  // ---- Mover card (arrasto e menu "Mover para…") ----
  function handleMoveCard(intent: MoveIntent) {
    setFeedback("");
    startTransition(async () => {
      aplicarMovimentoOtimista(intent);

      const resultado = await moveCardAction(
        intent.cardId,
        intent.columnId,
        intent.prevCardId,
        intent.nextCardId,
      );

      if (!resultado.ok) {
        // Não desfazemos à mão: ao fim desta transição o React descarta
        // o estado otimista e o quadro volta sozinho ao valor de `board`.
        setFeedback(`Não foi possível mover o card: ${resultado.message}`);
        return;
      }

      setBoard((anterior) => {
        const movido = moveCardInBoard(anterior, intent);
        // Reconcilia com a `position` que o SERVIDOR calculou — a nossa
        // era só ordem visual.
        return {
          ...movido,
          columns: movido.columns.map((coluna) => ({
            ...coluna,
            cards: coluna.cards.map((card) =>
              card.id === resultado.card.id ? resultado.card : card,
            ),
          })),
          uncolumned: movido.uncolumned.map((card) =>
            card.id === resultado.card.id ? resultado.card : card,
          ),
        };
      });
    });
  }

  // ---- Colunas ----
  const [colunaParaExcluir, setColunaParaExcluir] =
    useState<BoardColumnData | null>(null);

  /*
   * Move os cards visíveis e SÓ ENTÃO exclui — nesta ordem, e com a
   * exclusão condicionada ao sucesso do movimento. Inverter faria a
   * exclusão bater no 409 do backend; disparar as duas em paralelo
   * deixaria a coluna excluída com os cards ainda apontando para ela.
   */
  function excluirColunaRealocando(destinoId: number) {
    const column = colunaParaExcluir;
    if (!column) return;
    const visiveis = column.cards.filter((card) => !card.hidden);

    startTransition(async () => {
      const movimento = await bulkUpdateCardsAction(
        companyId,
        visiveis.map((card) => card.id),
        "set_column",
        null,
        destinoId,
      );
      if (!movimento.ok) {
        setFeedback(movimento.message);
        return;
      }

      const exclusao = await deleteColumnAction(column.id);
      if (!exclusao.ok) {
        // Os cards JÁ foram movidos: recarregamos o quadro para a tela não
        // ficar mostrando um estado que não é mais o do servidor.
        await refreshBoard();
        setFeedback(exclusao.message);
        return;
      }
      setColunaParaExcluir(null);
      await refreshBoard();
      setFeedback(
        `${movimento.affected_count} card(s) movido(s) e coluna "${column.name}" excluída.`,
      );
    });
  }

  function excluirColunaVazia() {
    const column = colunaParaExcluir;
    if (!column) return;
    startTransition(async () => {
      const resultado = await deleteColumnAction(column.id);
      if (!resultado.ok) {
        // 409 com card visível: a mensagem do backend diz quantos. Chegar
        // aqui significa que o quadro em memória estava desatualizado.
        setFeedback(resultado.message);
        return;
      }
      setColunaParaExcluir(null);
      await refreshBoard();
      setFeedback(
        column.kind === "SECTION" ? "Seção excluída." : "Coluna excluída.",
      );
    });
  }

  const [novaColunaNome, setNovaColunaNome] = useState("");
  const [novaColunaKind, setNovaColunaKind] = useState<"COLUMN" | "SECTION">(
    "COLUMN",
  );

  function handleCriarColuna() {
    if (!novaColunaNome.trim()) return;
    setFeedback("");
    startTransition(async () => {
      const resultado = await createColumnAction(
        companyId,
        novaColunaNome.trim(),
        novaColunaKind,
        null,
      );
      if (!resultado.ok) {
        setFeedback(resultado.message);
        return;
      }
      setNovaColunaNome("");
      await refreshBoard();
      setFeedback("Coluna criada.");
    });
  }

  const columnHandlers: ColumnMenuHandlers = {
    onRenameColumn(column) {
      const nome = window.prompt("Novo nome da coluna:", column.name);
      if (!nome || !nome.trim()) return;
      startTransition(async () => {
        const resultado = await updateColumnAction(
          column.id,
          nome.trim(),
          column.hidden,
          column.wip_limit,
        );
        if (!resultado.ok) {
          setFeedback(resultado.message);
          return;
        }
        await refreshBoard();
      });
    },

    onArchiveColumn(column) {
      startTransition(async () => {
        const resultado = await updateColumnAction(
          column.id,
          column.name,
          !column.hidden,
          column.wip_limit,
        );
        if (!resultado.ok) {
          setFeedback(resultado.message);
          return;
        }
        await refreshBoard();
        setFeedback(column.hidden ? "Coluna reexibida." : "Coluna arquivada.");
      });
    },

    /*
     * Abre o diálogo em vez de excluir direto. O `window.confirm` que
     * vivia aqui dizia "os cards NÃO são apagados" e nada mais —
     * verdadeiro e insuficiente: não dizia quantos cards estavam em jogo,
     * não avisava que o backend recusaria a exclusão por causa deles
     * (409), e não oferecia como resolver.
     */
    onDeleteColumn(column) {
      setFeedback("");
      setColunaParaExcluir(column);
    },

    onMoveColumn(column, direcao) {
      const visiveis = quadroVisivel.columns;
      const indice = visiveis.findIndex((c) => c.id === column.id);
      const destino = indice + direcao;
      if (indice < 0 || destino < 0 || destino >= visiveis.length) return;

      // Âncoras calculadas sobre a lista SEM a coluna movida — mandar a
      // própria coluna como âncora produziria 422 no servidor.
      const restantes = visiveis.filter((c) => c.id !== column.id);
      const prev = destino > 0 ? (restantes[destino - 1]?.id ?? null) : null;
      const next = restantes[destino]?.id ?? null;

      startTransition(async () => {
        const resultado = await moveColumnAction(column.id, prev, next);
        if (!resultado.ok) {
          setFeedback(resultado.message);
          return;
        }
        await refreshBoard();
      });
    },

    onAddCard(column) {
      setNewCardColumnId(column.id);
      setNewCardTitle("");
      setNewCardControlCode("");
      setNewCardCategoryId(categories[0]?.id ?? null);
    },
  };

  // ---- Ação em lote ----
  function runBulk(
    operation:
      | "hide"
      | "unhide"
      | "remove"
      | "set_category"
      | "set_column"
      | "restore_from_template",
    categoryId: number | null = null,
    columnId: number | null = null,
  ) {
    const ids = [...selectedCardIds];
    if (ids.length === 0) return;
    if (
      operation === "remove" &&
      !window.confirm(
        `Remover ${ids.length} card(s)? Histórico, checklist e conversa de cada um são apagados junto — ação irreversível.`,
      )
    ) {
      return;
    }

    setFeedback("");
    startTransition(async () => {
      const result = await bulkUpdateCardsAction(
        companyId,
        ids,
        operation,
        categoryId,
        columnId,
      );
      if (!result.ok) {
        setFeedback(result.message);
        return;
      }
      await refreshBoard();
      setFeedback(`${result.affected_count} card(s) atualizado(s).`);
    });
  }

  // ---- Aplicar template ----
  const [templateToApply, setTemplateToApply] = useState<number | "">("");

  function handleApplyTemplate() {
    if (templateToApply === "") return;
    setFeedback("");
    startTransition(async () => {
      const result = await applyTemplateToCompanyAction(
        companyId,
        Number(templateToApply),
      );
      if (!result.ok) {
        setFeedback(result.message);
        return;
      }
      await refreshBoard();
      setOutdatedFromLastApply(result.outdated_card_ids);
      // B-A24: sem `adopted_count` e `columns_created_count` visíveis,
      // aplicar um template numa empresa que já tem os cards mostraria
      // "0 criados" e o admin concluiria que nada aconteceu — quando na
      // verdade 25 colunas foram criadas.
      const partes = [
        `${result.created_count} card(s) criado(s)`,
        result.columns_created_count > 0
          ? `${result.columns_created_count} coluna(s) criada(s)`
          : null,
        result.adopted_count > 0
          ? `${result.adopted_count} card(s) existente(s) vinculado(s) ao template`
          : null,
        `${result.already_applied_count} já aplicado(s)`,
        result.outdated_card_ids.length > 0
          ? `${result.outdated_card_ids.length} divergente(s) do template (selecione e use "Restaurar do template")`
          : null,
      ].filter(Boolean);

      setFeedback(partes.join(" · "));
    });
  }

  // ---- Novo card (dentro de uma coluna) ----
  const [newCardColumnId, setNewCardColumnId] = useState<number | null>(null);
  const [newCardCategoryId, setNewCardCategoryId] = useState<number | null>(
    null,
  );
  const [newCardTitle, setNewCardTitle] = useState("");
  const [newCardControlCode, setNewCardControlCode] = useState("");

  function handleCreateCard() {
    if (newCardCategoryId === null || !newCardTitle.trim()) return;
    startTransition(async () => {
      const result = await createCardForCompanyAction(
        companyId,
        newCardTitle.trim(),
        newCardCategoryId,
        newCardControlCode.trim() || null,
        newCardColumnId,
        null,
      );
      if (!result.ok) {
        setFeedback(result.message);
        return;
      }
      setNewCardTitle("");
      setNewCardControlCode("");
      setNewCardColumnId(null);
      await refreshBoard();
    });
  }

  // ---- Mudar categoria / coluna em massa ----
  const [isChangeCategoryOpen, setIsChangeCategoryOpen] = useState(false);
  const [categoryToApply, setCategoryToApply] = useState<number | "">("");
  const [isChangeColumnOpen, setIsChangeColumnOpen] = useState(false);
  const [columnToApply, setColumnToApply] = useState<number | "">("");

  function confirmChangeCategory() {
    if (categoryToApply === "") return;
    setIsChangeCategoryOpen(false);
    runBulk("set_category", Number(categoryToApply));
    setCategoryToApply("");
  }

  function confirmChangeColumn() {
    if (columnToApply === "") return;
    setIsChangeColumnOpen(false);
    runBulk("set_column", null, Number(columnToApply));
    setColumnToApply("");
  }

  // ---- Detalhe do card selecionado ----
  function atualizarStatus(status: CardStatus) {
    if (!cardDetail) return;
    const cardId = cardDetail.id;
    startTransition(async () => {
      const result = await updateCardStatusAction(cardId, status);
      if (!result.ok) {
        setFeedback(result.message);
        return;
      }
      setCardDetail((prev) =>
        prev ? { ...prev, status: result.status } : prev,
      );
      setBoard((prev) =>
        mapCards(prev, cardId, (card) => ({
          ...card,
          status: result.status,
        })),
      );
    });
  }

  function alternarChecklist(itemId: number) {
    startTransition(async () => {
      const result = await toggleChecklistItemAction(itemId);
      if (!result.ok) {
        setFeedback(result.message);
        return;
      }
      setCardDetail((prev) =>
        prev
          ? {
              ...prev,
              checklist: prev.checklist.map((item) =>
                item.id === itemId ? { ...item, done: result.done } : item,
              ),
            }
          : prev,
      );
    });
  }

  /*
   * Recarrega o detalhe do card aberto.
   *
   * Checklist, histórico e conversa são coleções que o backend numera
   * (`id` autoincremento) e ordena — criar uma entrada sem ler de volta
   * obrigaria o cliente a INVENTAR o id e o `created_at` do que acabou de
   * criar, e a divergir do servidor no primeiro erro. Recarregar um card
   * é uma query; adivinhar é um bug silencioso.
   */
  async function recarregarDetalhe(cardId: number) {
    const fresco = await getCardDetailAction(cardId).catch(() => null);
    if (fresco) setCardDetail(fresco);
  }

  function adicionarItemDeChecklist(title: string) {
    if (!cardDetail) return;
    const cardId = cardDetail.id;
    setFeedback("");
    startTransition(async () => {
      const result = await createCardEntryAction(cardId, "CHECKLIST", title);
      if (!result.ok) {
        setFeedback(result.message);
        return;
      }
      await recarregarDetalhe(cardId);
    });
  }

  function removerItemDeChecklist(itemId: number) {
    if (!cardDetail) return;
    const cardId = cardDetail.id;
    setFeedback("");
    startTransition(async () => {
      const result = await deleteChecklistItemAction(itemId);
      if (!result.ok) {
        setFeedback(result.message);
        return;
      }
      await recarregarDetalhe(cardId);
    });
  }

  /*
   * `CHAT_ANSWER` e não `CHAT_QUESTION`: do lado do auditor toda mensagem
   * é resposta. O tipo distingue quem falou, e é ele que pinta a mensagem
   * na conversa — mandar `CHAT_QUESTION` daqui faria a fala da auditoria
   * aparecer como pergunta do cliente.
   */
  function enviarMensagem(content: string) {
    if (!cardDetail) return;
    const cardId = cardDetail.id;
    setFeedback("");
    startTransition(async () => {
      const result = await createCardEntryAction(
        cardId,
        "CHAT_ANSWER",
        content,
      );
      if (!result.ok) {
        setFeedback(result.message);
        return;
      }
      await recarregarDetalhe(cardId);
    });
  }

  /*
   * Salva a edição do card feita dentro do modal.
   *
   * A `updateCardAction` existia e era testada desde o quadro Kanban,
   * mas nenhum componente a chamava: não havia onde editar um card na
   * interface. O botão "Editar" do modal é o primeiro consumidor dela.
   *
   * Atualiza as DUAS fontes na mão, como `atualizarStatus` já fazia: o
   * detalhe aberto no modal e o card no quadro atrás dele. Um
   * `refreshBoard()` aqui recarregaria os 215 cards para refletir a
   * mudança de um.
   */
  function salvarEdicaoDoCard(input: CardEditInput) {
    if (!cardDetail) return;
    const cardId = cardDetail.id;
    setFeedback("");
    startTransition(async () => {
      const result = await updateCardAction(
        cardId,
        input.title,
        input.description,
        input.controlCode,
        input.categoryId,
      );
      if (!result.ok) {
        setFeedback(result.message);
        return;
      }
      setCardDetail((prev) =>
        prev
          ? {
              ...prev,
              title: result.card.title,
              description: result.card.description,
              control_code: result.card.control_code,
              category_id: result.card.category_id,
              category_name: result.card.category_name,
            }
          : prev,
      );
      setBoard((prev) =>
        mapCards(prev, cardId, (card) => ({
          ...card,
          title: result.card.title,
          description: result.card.description,
          control_code: result.card.control_code,
          category_id: result.card.category_id,
          category_name: result.card.category_name,
        })),
      );
      setFeedback("Card atualizado.");
    });
  }

  function alternarEtiqueta(labelId: number) {
    if (!cardDetail) return;
    const cardId = cardDetail.id;
    const atuais = cardDetail.labels.map((etiqueta) => etiqueta.id);
    const proximos = atuais.includes(labelId)
      ? atuais.filter((id) => id !== labelId)
      : [...atuais, labelId];

    startTransition(async () => {
      const result = await setCardLabelsAction(cardId, proximos);
      if (!result.ok) {
        setFeedback(result.message);
        return;
      }
      setCardDetail((prev) =>
        prev ? { ...prev, labels: result.labels } : prev,
      );
      setBoard((prev) =>
        mapCards(prev, cardId, (card) => ({ ...card, labels: result.labels })),
      );
    });
  }

  const selectionCount = selectedCardIds.size;

  const slotDeNovoCard =
    newCardColumnId === null ? null : (
      <div className="space-y-2">
        <input
          className="field text-sm"
          placeholder="Título do card"
          value={newCardTitle}
          onChange={(e) => setNewCardTitle(e.target.value)}
        />
        <input
          className="field text-sm"
          placeholder="Código do controle (opcional)"
          value={newCardControlCode}
          onChange={(e) => setNewCardControlCode(e.target.value)}
        />
        <select
          className="field text-sm"
          aria-label="Categoria do novo card"
          value={newCardCategoryId ?? ""}
          onChange={(e) =>
            setNewCardCategoryId(e.target.value ? Number(e.target.value) : null)
          }
        >
          <option value="">Escolha a categoria…</option>
          {categories.map((categoria) => (
            <option key={categoria.id} value={categoria.id}>
              {categoria.name}
            </option>
          ))}
        </select>
        <div className="flex gap-2">
          <button
            type="button"
            className="btn-primary text-xs"
            disabled={
              !newCardTitle.trim() || newCardCategoryId === null || isPending
            }
            onClick={handleCreateCard}
          >
            Criar
          </button>
          <button
            type="button"
            className="btn-secondary text-xs"
            onClick={() => setNewCardColumnId(null)}
          >
            Cancelar
          </button>
        </div>
      </div>
    );

  return (
    <main className="py-8 pb-28">
      <div className="container-page space-y-6">
        <section className="card">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-(--color-dark)">
                Quadro de {companyName}
              </h2>
              <p className="mt-1 text-sm text-zinc-600">
                {quadroOtimista.columns.length} coluna(s) · {totalVisivel}{" "}
                card(s) visível(is) · {totalOculto} oculto(s)
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <select
                className="field w-auto"
                aria-label="Template a aplicar"
                value={templateToApply}
                onChange={(e) =>
                  setTemplateToApply(
                    e.target.value ? Number(e.target.value) : "",
                  )
                }
              >
                <option value="">Aplicar template...</option>
                {templates.map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name} ({template.card_count} cards)
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="btn-primary"
                disabled={templateToApply === "" || isPending}
                onClick={handleApplyTemplate}
              >
                Aplicar
              </button>
            </div>
          </div>

          {feedback ? (
            <p
              role="status"
              className="mt-3 rounded-lg bg-zinc-50 p-2 text-sm text-zinc-700"
            >
              {feedback}
            </p>
          ) : null}
        </section>

        <section className="card space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <input
              type="text"
              placeholder="Buscar por título ou código..."
              aria-label="Buscar cards"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              className="w-full max-w-xs rounded-lg border border-zinc-300 px-3 py-2 text-sm"
            />

            <label className="flex items-center gap-2 text-sm text-zinc-700">
              <input
                type="checkbox"
                checked={showHidden}
                onChange={(e) => setShowHidden(e.target.checked)}
              />
              Mostrar cards e colunas arquivados
            </label>

            <div className="flex items-center gap-1">
              <button
                type="button"
                className="rounded-lg px-2 py-1 text-xs font-medium text-(--color-primary) hover:bg-zinc-100"
                onClick={expandirTodas}
              >
                Expandir tudo
              </button>
              <button
                type="button"
                className="rounded-lg px-2 py-1 text-xs font-medium text-(--color-primary) hover:bg-zinc-100"
                onClick={recolherTodas}
              >
                Recolher tudo
              </button>
            </div>

            <div className="ml-auto flex flex-wrap items-center gap-2">
              <input
                className="field w-48 text-sm"
                placeholder="Nome da coluna nova"
                aria-label="Nome da coluna nova"
                value={novaColunaNome}
                onChange={(e) => setNovaColunaNome(e.target.value)}
              />
              <select
                className="field w-auto text-sm"
                aria-label="Tipo da coluna nova"
                value={novaColunaKind}
                onChange={(e) =>
                  setNovaColunaKind(e.target.value as "COLUMN" | "SECTION")
                }
              >
                <option value="COLUMN">Coluna</option>
                <option value="SECTION">Seção (separador)</option>
              </select>
              <button
                type="button"
                className="btn-secondary text-sm"
                disabled={!novaColunaNome.trim() || isPending}
                onClick={handleCriarColuna}
              >
                + Coluna
              </button>
            </div>
          </div>
        </section>

        <Board
          board={quadroVisivel}
          selectedCardId={cardSelecionadoId}
          onSelectCard={setCardSelecionadoId}
          selectedCardIds={selectedCardIds}
          onToggleCardSelection={toggleCardSelection}
          onToggleColumnSelection={toggleColumnSelection}
          collapsedColumns={colunasRecolhidas}
          onToggleColumnCollapse={toggleColumnCollapse}
          onMoveCard={handleMoveCard}
          columnHandlers={columnHandlers}
          outdatedCardIds={outdatedFromLastApply}
          addCardColumnId={newCardColumnId}
          addCardSlot={slotDeNovoCard}
        />

      </div>

      {/*
        Montado por `cardSelecionadoId` e não por `cardDetail`: o modal
        precisa aparecer JÁ no clique, mostrando "Carregando card…"
        enquanto a Server Action responde. Condicionado ao detalhe, ele
        só apareceria depois da resposta, e o clique pareceria não ter
        surtido efeito.
      */}
      {cardSelecionadoId !== null ? (
        <CardDetailModal
          cardDetail={cardDetail}
          isLoading={isLoadingDetail}
          isPending={isPending}
          labels={labels}
          categories={categories}
          onClose={() => setCardSelecionadoId(null)}
          onChangeStatus={atualizarStatus}
          onToggleChecklistItem={alternarChecklist}
          onToggleLabel={alternarEtiqueta}
          onSaveCard={salvarEdicaoDoCard}
          onAddChecklistItem={adicionarItemDeChecklist}
          onDeleteChecklistItem={removerItemDeChecklist}
          onSendMessage={enviarMensagem}
        />
      ) : null}

      {selectionCount > 0 ? (
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-(--color-neutral) bg-white/95 backdrop-blur">
          <div className="container-page flex flex-wrap items-center justify-between gap-3 py-3">
            <span className="text-sm font-medium text-(--color-dark)">
              {selectionCount} selecionado(s)
            </span>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-secondary"
                disabled={isPending}
                onClick={() => runBulk("hide")}
              >
                Ocultar
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={isPending}
                onClick={() => runBulk("unhide")}
              >
                Reexibir
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={isPending}
                onClick={() => setIsChangeColumnOpen(true)}
              >
                Mover para coluna
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={isPending}
                onClick={() => setIsChangeCategoryOpen(true)}
              >
                Mudar categoria
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={isPending}
                onClick={() => runBulk("restore_from_template")}
              >
                Restaurar do template
              </button>
              <button
                type="button"
                className="btn-danger-outline"
                disabled={isPending}
                onClick={() => runBulk("remove")}
              >
                Remover
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setSelectedCardIds(new Set())}
              >
                Limpar seleção
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {colunaParaExcluir ? (
        <DeleteColumnDialog
          column={colunaParaExcluir}
          // Sobre o quadro OTIMISTA e não o filtrado: a contagem de cards
          // precisa refletir o que EXISTE na coluna, não o que a busca
          // está mostrando. Confirmar a exclusão com o filtro ligado não
          // pode parecer seguro só porque os cards estão escondidos.
          board={quadroOtimista}
          isPending={isPending}
          onCancel={() => setColunaParaExcluir(null)}
          onRelocateAndDelete={excluirColunaRealocando}
          onDelete={excluirColunaVazia}
        />
      ) : null}

      {isChangeCategoryOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h3 className="text-base font-semibold">
              Mudar categoria de {selectionCount} card(s)
            </h3>
            <select
              className="field mt-4"
              aria-label="Categoria de destino"
              value={categoryToApply}
              onChange={(e) =>
                setCategoryToApply(e.target.value ? Number(e.target.value) : "")
              }
            >
              <option value="">Escolha a categoria...</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setIsChangeCategoryOpen(false)}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={categoryToApply === "" || isPending}
                onClick={confirmChangeCategory}
              >
                Aplicar
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {isChangeColumnOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h3 className="text-base font-semibold">
              Mover {selectionCount} card(s) para outra coluna
            </h3>
            <select
              className="field mt-4"
              aria-label="Coluna de destino"
              value={columnToApply}
              onChange={(e) =>
                setColumnToApply(e.target.value ? Number(e.target.value) : "")
              }
            >
              <option value="">Escolha a coluna...</option>
              {quadroOtimista.columns
                .filter((coluna) => coluna.kind === "COLUMN")
                .map((coluna) => (
                  <option key={coluna.id} value={coluna.id}>
                    {coluna.name}
                  </option>
                ))}
            </select>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setIsChangeColumnOpen(false)}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={columnToApply === "" || isPending}
                onClick={confirmChangeColumn}
              >
                Mover
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}

/** Aplica uma transformação a UM card, em qualquer coluna do quadro. */
function mapCards(
  board: BoardData,
  cardId: number,
  transformar: (card: BoardCardData) => BoardCardData,
): BoardData {
  const aplicar = (cards: BoardCardData[]) =>
    cards.map((card) => (card.id === cardId ? transformar(card) : card));

  return {
    ...board,
    columns: board.columns.map((coluna) => ({
      ...coluna,
      cards: aplicar(coluna.cards),
    })),
    uncolumned: aplicar(board.uncolumned),
  };
}
