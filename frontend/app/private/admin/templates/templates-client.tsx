"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import {
  createTemplateAction,
  createTemplateCardAction,
  createTemplateCategoryAction,
  createTemplateColumnAction,
  deleteTemplateAction,
  deleteTemplateCardAction,
  deleteTemplateCategoryAction,
  deleteTemplateColumnAction,
  getTemplateDetailAction,
  listTemplateCategoriesAction,
  listTemplatesAction,
  moveTemplateColumnAction,
  TemplateCategory,
  TemplateColumn,
  TemplateColumnKind,
  TemplateDetail,
  TemplateListItem,
  updateTemplateAction,
  updateTemplateCardAction,
  updateTemplateCategoryAction,
  updateTemplateColumnAction,
} from "./actions";
import { ModalShell } from "@/app/private/_components/modal-shell";
import {
  CategoriesModal,
  type CategoryFormState,
} from "./_components/categories-modal";

type TemplatesClientProps = {
  initialTemplates: TemplateListItem[];
  initialSelectedTemplateId: number | null;
  initialDetail: TemplateDetail | null;
  initialCategories: TemplateCategory[];
};

const EMPTY_CATEGORY_FORM: CategoryFormState = {
  name: "",
  color: "#788c5d",
  sortOrder: 0,
};

type CardFormState = {
  title: string;
  description: string;
  categoryId: number | "";
  templateColumnId: number | "";
  sortOrder: number;
};

const EMPTY_CARD_FORM: CardFormState = {
  title: "",
  description: "",
  categoryId: "",
  templateColumnId: "",
  sortOrder: 0,
};

export function TemplatesClient({
  initialTemplates,
  initialSelectedTemplateId,
  initialDetail,
  initialCategories,
}: TemplatesClientProps) {
  const [templates, setTemplates] =
    useState<TemplateListItem[]>(initialTemplates);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(
    initialSelectedTemplateId,
  );
  const [detail, setDetail] = useState<TemplateDetail | null>(initialDetail);
  /*
   * Categoria virou ESTADO aqui porque esta tela passou a ser quem a
   * cria/edita/exclui. Ela saiu do quadro de uma empresa
   * (`+ Nova categoria`, em company-dashboard-client) porque é
   * vocabulário GLOBAL: criar uma categoria ali afetava todas as
   * empresas da plataforma, e nada na tela dizia isso.
   */
  const [categories, setCategories] =
    useState<TemplateCategory[]>(initialCategories);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isPending, startTransition] = useTransition();
  const isFirstRender = useRef(true);

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    if (selectedTemplateId === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDetail(null);
      return;
    }

    let cancelado = false;
    setIsLoadingDetail(true);
    getTemplateDetailAction(selectedTemplateId)
      .then((data) => {
        if (!cancelado) setDetail(data);
      })
      .catch(() => {
        if (!cancelado) setDetail(null);
      })
      .finally(() => {
        if (!cancelado) setIsLoadingDetail(false);
      });

    return () => {
      cancelado = true;
    };
  }, [selectedTemplateId]);

  async function refreshAll(keepTemplateId: number | null) {
    const [freshTemplates, freshDetail] = await Promise.all([
      listTemplatesAction(),
      keepTemplateId
        ? getTemplateDetailAction(keepTemplateId).catch(() => null)
        : Promise.resolve(null),
    ]);
    setTemplates(freshTemplates);
    setSelectedTemplateId(
      freshDetail ? keepTemplateId : (freshTemplates[0]?.id ?? null),
    );
    setDetail(freshDetail);
  }

  // ---- Categorias de card (vocabulário global) ----
  const [categoryForm, setCategoryForm] =
    useState<CategoryFormState>(EMPTY_CATEGORY_FORM);
  const [editingCategoryId, setEditingCategoryId] = useState<number | null>(
    null,
  );
  const [categoryMsg, setCategoryMsg] = useState("");
  /*
   * Estados só de UI, nascidos com o modal:
   *
   * - `isCreatingCategory` separa "formulário de criação aberto" de
   *   "nenhum formulário". Antes o formulário era permanente e
   *   `editingCategoryId === null` bastava para significar "modo
   *   criação"; com os campos abrindo na linha, os dois estados
   *   precisam ser distinguíveis.
   * - `pendingDeleteCategoryId` é a confirmação inline que substituiu o
   *   `window.confirm`.
   */
  const [isCategoriesOpen, setIsCategoriesOpen] = useState(false);
  const [isCreatingCategory, setIsCreatingCategory] = useState(false);
  const [pendingDeleteCategoryId, setPendingDeleteCategoryId] = useState<
    number | null
  >(null);

  async function refreshCategories() {
    setCategories(await listTemplateCategoriesAction());
  }

  function openCategories() {
    setCategoryMsg("");
    setIsCreatingCategory(false);
    setEditingCategoryId(null);
    setPendingDeleteCategoryId(null);
    setCategoryForm(EMPTY_CATEGORY_FORM);
    setIsCategoriesOpen(true);
  }

  function startCreateCategory() {
    setEditingCategoryId(null);
    setPendingDeleteCategoryId(null);
    setCategoryForm(EMPTY_CATEGORY_FORM);
    setCategoryMsg("");
    setIsCreatingCategory(true);
  }

  function cancelCategoryForm() {
    setIsCreatingCategory(false);
    setEditingCategoryId(null);
    setCategoryForm(EMPTY_CATEGORY_FORM);
  }

  function handleSaveCategory() {
    if (!categoryForm.name.trim()) {
      setCategoryMsg("Informe o nome da categoria.");
      return;
    }
    setCategoryMsg("");
    startTransition(async () => {
      const entrada = {
        name: categoryForm.name.trim(),
        color: categoryForm.color,
        sort_order: categoryForm.sortOrder,
      };
      const resultado =
        editingCategoryId === null
          ? await createTemplateCategoryAction(entrada)
          : await updateTemplateCategoryAction(editingCategoryId, entrada);

      if (!resultado.ok) {
        setCategoryMsg(resultado.message);
        return;
      }
      setCategoryForm(EMPTY_CATEGORY_FORM);
      setEditingCategoryId(null);
      setIsCreatingCategory(false);
      await refreshCategories();
      setCategoryMsg("Categoria salva.");
    });
  }

  function startEditCategory(category: TemplateCategory) {
    setIsCreatingCategory(false);
    setPendingDeleteCategoryId(null);
    setEditingCategoryId(category.id);
    setCategoryForm({
      name: category.name,
      color: category.color,
      sortOrder: category.sort_order,
    });
    setCategoryMsg("");
  }

  function askDeleteCategory(category: TemplateCategory) {
    setIsCreatingCategory(false);
    setEditingCategoryId(null);
    setCategoryMsg("");
    setPendingDeleteCategoryId(category.id);
  }

  function handleDeleteCategory(category: TemplateCategory) {
    startTransition(async () => {
      const resultado = await deleteTemplateCategoryAction(category.id);
      if (!resultado.ok) {
        // 409 do backend: a mensagem dele diz QUANTOS cards/definições
        // ainda usam a categoria — é a informação que o admin precisa
        // para saber o que reclassificar antes de tentar de novo.
        setCategoryMsg(resultado.message);
        setPendingDeleteCategoryId(null);
        return;
      }
      setPendingDeleteCategoryId(null);
      await refreshCategories();
      setCategoryMsg("Categoria excluída.");
    });
  }

  // ---- Novo template ----
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newIsDefault, setNewIsDefault] = useState(false);
  const [createMsg, setCreateMsg] = useState("");

  function handleCreateTemplate() {
    if (!newName.trim()) {
      setCreateMsg("Informe o nome do template.");
      return;
    }
    setCreateMsg("");
    startTransition(async () => {
      const result = await createTemplateAction({
        name: newName.trim(),
        description: newDescription.trim() || null,
        is_default: newIsDefault,
      });
      if (!result.ok) {
        setCreateMsg(result.message);
        return;
      }
      setIsCreateOpen(false);
      setNewName("");
      setNewDescription("");
      setNewIsDefault(false);
      await refreshAll(selectedTemplateId);
    });
  }

  // ---- Edição do template selecionado ----
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editIsDefault, setEditIsDefault] = useState(false);
  const [editMsg, setEditMsg] = useState("");
  const [isEditOpen, setIsEditOpen] = useState(false);

  function openEdit() {
    if (!detail) return;
    setEditName(detail.name);
    setEditDescription(detail.description ?? "");
    setEditIsDefault(detail.is_default);
    setEditMsg("");
    setIsEditOpen(true);
  }

  function handleUpdateTemplate() {
    if (!detail) return;
    if (!editName.trim()) {
      setEditMsg("Informe o nome do template.");
      return;
    }
    startTransition(async () => {
      const result = await updateTemplateAction(detail.id, {
        name: editName.trim(),
        description: editDescription.trim() || null,
        is_default: editIsDefault,
      });
      if (!result.ok) {
        setEditMsg(result.message);
        return;
      }
      setIsEditOpen(false);
      await refreshAll(detail.id);
    });
  }

  function handleDeleteTemplate() {
    if (!detail) return;
    if (
      !window.confirm(
        `Excluir o template "${detail.name}"? Os cards já criados nas empresas a partir dele NÃO são removidos.`,
      )
    ) {
      return;
    }
    startTransition(async () => {
      const result = await deleteTemplateAction(detail.id);
      if (!result.ok) {
        window.alert(result.message);
        return;
      }
      await refreshAll(null);
    });
  }

  // ---- Colunas do template ----
  const [columnMsg, setColumnMsg] = useState("");
  const [newColumnName, setNewColumnName] = useState("");
  const [newColumnKind, setNewColumnKind] =
    useState<TemplateColumnKind>("COLUMN");

  function handleCreateColumn() {
    if (!detail || !newColumnName.trim()) return;
    setColumnMsg("");
    startTransition(async () => {
      const result = await createTemplateColumnAction(detail.id, {
        name: newColumnName.trim(),
        kind: newColumnKind,
      });
      if (!result.ok) {
        setColumnMsg(result.message);
        return;
      }
      setNewColumnName("");
      setNewColumnKind("COLUMN");
      await refreshAll(detail.id);
    });
  }

  function handleRenameColumn(column: TemplateColumn) {
    if (!detail) return;
    const nome = window.prompt("Novo nome da coluna:", column.name);
    if (!nome || !nome.trim()) return;
    setColumnMsg("");
    startTransition(async () => {
      const result = await updateTemplateColumnAction(detail.id, column.id, {
        name: nome.trim(),
        kind: column.kind,
      });
      if (!result.ok) {
        setColumnMsg(result.message);
        return;
      }
      await refreshAll(detail.id);
    });
  }

  function handleMoveColumn(column: TemplateColumn, direcao: -1 | 1) {
    if (!detail) return;
    const colunas = detail.columns;
    const indice = colunas.findIndex((c) => c.id === column.id);
    const destino = indice + direcao;
    if (indice < 0 || destino < 0 || destino >= colunas.length) return;

    // Âncoras calculadas sobre a lista SEM a coluna movida — mandar a
    // própria coluna como âncora produziria 422 no servidor.
    const restantes = colunas.filter((c) => c.id !== column.id);
    const prev = destino > 0 ? (restantes[destino - 1]?.id ?? null) : null;
    const next = restantes[destino]?.id ?? null;

    setColumnMsg("");
    startTransition(async () => {
      const result = await moveTemplateColumnAction(
        detail.id,
        column.id,
        prev,
        next,
      );
      if (!result.ok) {
        setColumnMsg(result.message);
        return;
      }
      await refreshAll(detail.id);
    });
  }

  function handleDeleteColumn(column: TemplateColumn) {
    if (!detail) return;
    if (!window.confirm(`Excluir a coluna "${column.name}" do template?`)) {
      return;
    }
    setColumnMsg("");
    startTransition(async () => {
      const result = await deleteTemplateColumnAction(detail.id, column.id);
      if (!result.ok) {
        // 409 quando há card de template vinculado — a mensagem do
        // backend diz quantos.
        setColumnMsg(result.message);
        return;
      }
      await refreshAll(detail.id);
    });
  }

  // ---- Cards do template ----
  const [cardForm, setCardForm] = useState<CardFormState>(EMPTY_CARD_FORM);
  const [editingCardId, setEditingCardId] = useState<number | null>(null);

  function startNewCard() {
    setEditingCardId(null);
    setCardForm({
      ...EMPTY_CARD_FORM,
      sortOrder: detail?.cards.length ?? 0,
    });
  }

  function startEditCard(cardId: number) {
    const card = detail?.cards.find((c) => c.id === cardId);
    if (!card) return;
    setEditingCardId(cardId);
    setCardForm({
      title: card.title,
      description: card.description ?? "",
      categoryId: card.category_id ?? "",
      templateColumnId: card.template_column_id ?? "",
      sortOrder: card.sort_order,
    });
  }

  function handleSaveCard() {
    if (!detail || !cardForm.title.trim()) return;
    const payload = {
      title: cardForm.title.trim(),
      description: cardForm.description.trim() || null,
      category_id: cardForm.categoryId === "" ? null : cardForm.categoryId,
      template_column_id:
        cardForm.templateColumnId === "" ? null : cardForm.templateColumnId,
      sort_order: cardForm.sortOrder,
    };

    startTransition(async () => {
      const result = editingCardId
        ? await updateTemplateCardAction(editingCardId, payload)
        : await createTemplateCardAction(detail.id, payload);
      if (!result.ok) {
        window.alert(result.message);
        return;
      }
      setCardForm(EMPTY_CARD_FORM);
      setEditingCardId(null);
      await refreshAll(detail.id);
    });
  }

  function handleDeleteCard(cardId: number) {
    if (!detail) return;
    if (!window.confirm("Excluir este card do template?")) return;
    startTransition(async () => {
      const result = await deleteTemplateCardAction(cardId);
      if (!result.ok) {
        window.alert(result.message);
        return;
      }
      await refreshAll(detail.id);
    });
  }

  const nomeDaColuna = (columnId: number | null): string => {
    if (columnId === null) return "Sem coluna";
    return (
      detail?.columns.find((coluna) => coluna.id === columnId)?.name ??
      "Sem coluna"
    );
  };

  return (
    <main className="min-h-screen bg-(--color-surface) py-8">
      <div className="container-page space-y-6">
        <header className="card">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold text-(--color-dark)">
                Templates de Dashboard
              </h1>
              <p className="mt-1 text-sm text-zinc-600">
                Definições reutilizáveis de <strong>coluna</strong> e{" "}
                <strong>card</strong>, aplicáveis a qualquer empresa — editar um
                template não altera automaticamente os quadros já criados; a
                empresa é atualizada por &quot;Aplicar template&quot; /
                &quot;Restaurar do template&quot;.
              </p>
            </div>
            {/*
              Vocabulário global vira ACESSO, não bloco: as categorias
              ocupavam ~620 px logo abaixo daqui, empurrando a lista de
              templates — o conteúdo que dá nome à tela — para fora da
              primeira dobra. O botão secundário ao lado do primário
              declara a hierarquia: criar template é a ação da tela,
              manter categorias é apoio.
            */}
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-secondary"
                aria-haspopup="dialog"
                onClick={openCategories}
              >
                Categorias de card · {categories.length}
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={() => {
                  setIsCreateOpen(true);
                  setCreateMsg("");
                }}
              >
                Novo template
              </button>
            </div>
          </div>
        </header>

        <div className="grid gap-6 lg:grid-cols-3">
          <section className="space-y-2 lg:col-span-1">
            {templates.length === 0 ? (
              <p className="text-sm text-zinc-600">
                Nenhum template cadastrado ainda.
              </p>
            ) : (
              templates.map((template) => (
                <button
                  key={template.id}
                  type="button"
                  onClick={() => setSelectedTemplateId(template.id)}
                  className={`card w-full text-left transition ${
                    template.id === selectedTemplateId
                      ? "ring-2 ring-(--color-primary)"
                      : ""
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-semibold">
                      {template.name}
                    </span>
                    {template.is_default ? (
                      <span className="rounded-full bg-(--color-primary) px-2 py-0.5 text-[10px] font-semibold text-white">
                        padrão
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-1 text-xs text-zinc-500">
                    {template.card_count} card(s)
                  </p>
                </button>
              ))
            )}
          </section>

          <section className="space-y-4 lg:col-span-2">
            <article className="card">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-lg font-semibold">
                  {detail ? detail.name : "Nenhum template selecionado"}
                </h2>
                {detail ? (
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={openEdit}
                    >
                      Editar
                    </button>
                    <button
                      type="button"
                      className="btn-danger-outline"
                      disabled={isPending}
                      onClick={handleDeleteTemplate}
                    >
                      Excluir
                    </button>
                  </div>
                ) : null}
              </div>

              {detail?.description ? (
                <p className="mt-2 text-sm text-zinc-600">
                  {detail.description}
                </p>
              ) : null}

              {isLoadingDetail ? (
                <p className="mt-3 text-sm text-zinc-500">
                  Carregando template...
                </p>
              ) : null}
            </article>

            {detail ? (
              <article className="card">
                <h3 className="text-base font-semibold">
                  Colunas do template ({detail.columns.length})
                </h3>
                <p className="mt-1 text-sm text-zinc-600">
                  A ordem aqui é a ordem em que as colunas nascem no quadro da
                  empresa. Uma <strong>seção</strong> é um separador visual
                  (como <code>ISO 27001:2022 &gt;&gt;</code>) e não aceita
                  cards.
                </p>

                {columnMsg ? (
                  <p
                    role="status"
                    className="mt-3 rounded-lg bg-zinc-50 p-2 text-sm text-zinc-700"
                  >
                    {columnMsg}
                  </p>
                ) : null}

                <ul className="mt-3 divide-y divide-(--color-neutral)">
                  {detail.columns.map((column, indice) => (
                    <li
                      key={column.id}
                      className="flex flex-wrap items-center justify-between gap-3 py-2"
                    >
                      <div>
                        <p className="text-sm font-medium text-(--color-dark)">
                          {column.name}
                          {column.kind === "SECTION" ? (
                            <span className="ml-2 rounded-full bg-(--color-dark) px-2 py-0.5 text-[10px] text-white">
                              seção
                            </span>
                          ) : null}
                        </p>
                        <p className="text-xs text-zinc-500">
                          {column.card_count} card(s) nascem aqui
                        </p>
                      </div>
                      <div className="flex shrink-0 gap-2">
                        <button
                          type="button"
                          className="btn-secondary text-xs"
                          aria-label={`Mover a coluna ${column.name} para cima`}
                          disabled={indice === 0 || isPending}
                          onClick={() => handleMoveColumn(column, -1)}
                        >
                          ↑
                        </button>
                        <button
                          type="button"
                          className="btn-secondary text-xs"
                          aria-label={`Mover a coluna ${column.name} para baixo`}
                          disabled={
                            indice === detail.columns.length - 1 || isPending
                          }
                          onClick={() => handleMoveColumn(column, 1)}
                        >
                          ↓
                        </button>
                        <button
                          type="button"
                          className="btn-secondary text-xs"
                          onClick={() => handleRenameColumn(column)}
                        >
                          Renomear
                        </button>
                        <button
                          type="button"
                          className="btn-danger-outline text-xs"
                          disabled={isPending}
                          onClick={() => handleDeleteColumn(column)}
                        >
                          Excluir
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>

                {detail.columns.length === 0 ? (
                  <p className="mt-3 text-sm text-zinc-600">
                    Nenhuma coluna ainda — os cards deste template nascerão sem
                    coluna no quadro da empresa.
                  </p>
                ) : null}

                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <input
                    className="field w-56 text-sm"
                    placeholder="Nome da coluna"
                    aria-label="Nome da coluna nova"
                    value={newColumnName}
                    onChange={(e) => setNewColumnName(e.target.value)}
                  />
                  <select
                    className="field w-auto text-sm"
                    aria-label="Tipo da coluna nova"
                    value={newColumnKind}
                    onChange={(e) =>
                      setNewColumnKind(e.target.value as TemplateColumnKind)
                    }
                  >
                    <option value="COLUMN">Coluna</option>
                    <option value="SECTION">Seção (separador)</option>
                  </select>
                  <button
                    type="button"
                    className="btn-primary text-sm"
                    disabled={!newColumnName.trim() || isPending}
                    onClick={handleCreateColumn}
                  >
                    + Coluna
                  </button>
                </div>
              </article>
            ) : null}

            {detail ? (
              <article className="card">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-semibold">
                    Cards do template ({detail.cards.length})
                  </h3>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={startNewCard}
                  >
                    + Novo card
                  </button>
                </div>

                <ul className="mt-4 divide-y divide-(--color-neutral)">
                  {detail.cards.map((card) => (
                    <li
                      key={card.id}
                      className="flex items-start justify-between gap-3 py-3"
                    >
                      <div>
                        <p className="text-sm font-medium text-(--color-dark)">
                          {card.title}
                        </p>
                        {card.description ? (
                          <p className="mt-0.5 text-xs text-zinc-600">
                            {card.description}
                          </p>
                        ) : null}
                        <p className="mt-1 text-xs text-zinc-500">
                          Coluna: {nomeDaColuna(card.template_column_id)} ·
                          Categoria: {card.category_name ?? "Sem categoria"} ·
                          ordem {card.sort_order}
                        </p>
                      </div>
                      <div className="flex shrink-0 gap-2">
                        <button
                          type="button"
                          className="btn-secondary"
                          onClick={() => startEditCard(card.id)}
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          className="btn-danger-outline"
                          disabled={isPending}
                          onClick={() => handleDeleteCard(card.id)}
                        >
                          Excluir
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>

                {cardForm.title !== "" || editingCardId !== null ? (
                  <div className="mt-4 space-y-3 rounded-lg border border-(--color-neutral) p-3">
                    <p className="text-sm font-semibold">
                      {editingCardId ? "Editar card" : "Novo card"}
                    </p>
                    <input
                      className="field"
                      placeholder="Título do card"
                      aria-label="Título do card"
                      value={cardForm.title}
                      onChange={(e) =>
                        setCardForm((prev) => ({
                          ...prev,
                          title: e.target.value,
                        }))
                      }
                    />
                    <textarea
                      className="field"
                      rows={4}
                      placeholder="Descrição — texto normativo do controle (opcional)"
                      aria-label="Descrição do card"
                      value={cardForm.description}
                      onChange={(e) =>
                        setCardForm((prev) => ({
                          ...prev,
                          description: e.target.value,
                        }))
                      }
                    />
                    <select
                      className="field"
                      aria-label="Coluna do card"
                      value={cardForm.templateColumnId}
                      onChange={(e) =>
                        setCardForm((prev) => ({
                          ...prev,
                          templateColumnId: e.target.value
                            ? Number(e.target.value)
                            : "",
                        }))
                      }
                    >
                      <option value="">Sem coluna</option>
                      {detail.columns
                        .filter((coluna) => coluna.kind === "COLUMN")
                        .map((coluna) => (
                          <option key={coluna.id} value={coluna.id}>
                            {coluna.name}
                          </option>
                        ))}
                    </select>
                    <select
                      className="field"
                      aria-label="Categoria do card"
                      value={cardForm.categoryId}
                      onChange={(e) =>
                        setCardForm((prev) => ({
                          ...prev,
                          categoryId: e.target.value
                            ? Number(e.target.value)
                            : "",
                        }))
                      }
                    >
                      <option value="">Sem categoria</option>
                      {categories.map((category) => (
                        <option key={category.id} value={category.id}>
                          {category.name}
                        </option>
                      ))}
                    </select>
                    <input
                      className="field"
                      type="number"
                      placeholder="Ordem"
                      aria-label="Ordem do card"
                      value={cardForm.sortOrder}
                      onChange={(e) =>
                        setCardForm((prev) => ({
                          ...prev,
                          sortOrder: Number(e.target.value) || 0,
                        }))
                      }
                    />
                    <div className="flex gap-2">
                      <button
                        type="button"
                        className="btn-primary"
                        disabled={!cardForm.title.trim() || isPending}
                        onClick={handleSaveCard}
                      >
                        {editingCardId ? "Salvar card" : "Criar card"}
                      </button>
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => {
                          setCardForm(EMPTY_CARD_FORM);
                          setEditingCardId(null);
                        }}
                      >
                        Cancelar
                      </button>
                    </div>
                  </div>
                ) : null}
              </article>
            ) : null}
          </section>
        </div>

        {isCategoriesOpen ? (
          <CategoriesModal
            categories={categories}
            form={categoryForm}
            editingCategoryId={editingCategoryId}
            isCreating={isCreatingCategory}
            pendingDeleteId={pendingDeleteCategoryId}
            message={categoryMsg}
            isPending={isPending}
            onChangeForm={(patch) =>
              setCategoryForm((prev) => ({ ...prev, ...patch }))
            }
            onStartCreate={startCreateCategory}
            onStartEdit={startEditCategory}
            onCancelForm={cancelCategoryForm}
            onSave={handleSaveCategory}
            onAskDelete={askDeleteCategory}
            onCancelDelete={() => setPendingDeleteCategoryId(null)}
            onConfirmDelete={handleDeleteCategory}
            onClose={() => setIsCategoriesOpen(false)}
          />
        ) : null}

        {isCreateOpen ? (
          <ModalShell
            title="Novo template"
            maxWidthClass="max-w-md"
            onClose={() => setIsCreateOpen(false)}
          >
            <div className="mt-4 space-y-3">
              <input
                className="field"
                placeholder="Nome do template"
                aria-label="Nome do template"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
              <textarea
                className="field"
                rows={2}
                placeholder="Descrição (opcional)"
                aria-label="Descrição do template"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
              />
              <label className="flex items-center gap-2 text-sm text-zinc-700">
                <input
                  type="checkbox"
                  checked={newIsDefault}
                  onChange={(e) => setNewIsDefault(e.target.checked)}
                />
                Definir como template padrão (usado em novos onboardings)
              </label>
              {createMsg ? (
                <p role="alert" className="text-sm text-red-600">
                  {createMsg}
                </p>
              ) : null}
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setIsCreateOpen(false)}
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  disabled={isPending}
                  onClick={handleCreateTemplate}
                >
                  Criar template
                </button>
              </div>
            </div>
          </ModalShell>
        ) : null}

        {isEditOpen && detail ? (
          <ModalShell
            title="Editar template"
            maxWidthClass="max-w-md"
            onClose={() => setIsEditOpen(false)}
          >
            <div className="mt-4 space-y-3">
              <input
                className="field"
                aria-label="Nome do template"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
              />
              <textarea
                className="field"
                rows={2}
                aria-label="Descrição do template"
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
              />
              <label className="flex items-center gap-2 text-sm text-zinc-700">
                <input
                  type="checkbox"
                  checked={editIsDefault}
                  onChange={(e) => setEditIsDefault(e.target.checked)}
                />
                Definir como template padrão
              </label>
              {editMsg ? (
                <p role="alert" className="text-sm text-red-600">
                  {editMsg}
                </p>
              ) : null}
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setIsEditOpen(false)}
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  disabled={isPending}
                  onClick={handleUpdateTemplate}
                >
                  Salvar
                </button>
              </div>
            </div>
          </ModalShell>
        ) : null}
      </div>
    </main>
  );
}
