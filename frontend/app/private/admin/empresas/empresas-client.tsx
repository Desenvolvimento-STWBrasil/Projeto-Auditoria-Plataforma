"use client";

import { useEffect, useRef, useState, useTransition } from "react";

import {
  createCompanyAction,
  deleteCompanyAction,
  getCompanyAdminDetailAction,
  listCompaniesAdminAction,
  updateCompanyAction,
  type CompanyAdminDetail,
  type CompanyAdminListItem,
  type PaginatedCompanies,
  type TemplateOption,
} from "./actions";
import { CompanyCard } from "./_components/company-card";
import { CompanyRow } from "./_components/company-row";
import {
  CreateCompanyModal,
  EMPTY_CREATE_FORM,
  type CreateFormState,
} from "./_components/create-company-modal";
import { DeleteCompanyModal } from "./_components/delete-company-modal";
import {
  EditCompanyModal,
  EMPTY_EDIT_FORM,
  type EditFormState,
} from "./_components/edit-company-modal";
import {
  CompaniesSkeleton,
  EmptyState,
  ListErrorState,
} from "./_components/list-states";

const PAGE_SIZE = 10;

type EmpresasClientProps = {
  initialCompanies: PaginatedCompanies;
  initialTemplates: TemplateOption[];
};

export function EmpresasClient({
  initialCompanies,
  initialTemplates,
}: EmpresasClientProps) {
  const [companies, setCompanies] = useState<CompanyAdminListItem[]>(
    initialCompanies.items,
  );
  const [total, setTotal] = useState(initialCompanies.total);
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [isLoadingList, setIsLoadingList] = useState(false);
  const [listError, setListError] = useState("");
  const [templates] = useState<TemplateOption[]>(initialTemplates);
  const [isPending, startTransition] = useTransition();
  const isFirstRender = useRef(true);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  // Recarrega a lista ao trocar página ou busca — pula a primeira
  // renderização, pois a página 0 sem busca já veio pronta via props
  // (initialCompanies), sem precisar de fetch no cliente.
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }

    let cancelado = false;
    setIsLoadingList(true);
    setListError("");

    const handle = setTimeout(() => {
      listCompaniesAdminAction(page, search)
        .then((result) => {
          if (cancelado) return;
          setCompanies(result.items);
          setTotal(result.total);
        })
        .catch((error: unknown) => {
          if (cancelado) return;
          setListError(
            error instanceof Error
              ? error.message
              : "Falha ao carregar as empresas.",
          );
        })
        .finally(() => {
          if (!cancelado) setIsLoadingList(false);
        });
    }, 300);

    return () => {
      cancelado = true;
      clearTimeout(handle);
    };
  }, [page, search]);

  function refreshList() {
    startTransition(async () => {
      try {
        setListError("");
        const result = await listCompaniesAdminAction(page, search);
        setCompanies(result.items);
        setTotal(result.total);
      } catch (error) {
        setListError(
          error instanceof Error
            ? error.message
            : "Falha ao recarregar as empresas.",
        );
      }
    });
  }

  // ---- Criação ----
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [createMsg, setCreateMsg] = useState("");
  // B-A29: quando o e-mail de credenciais não sai, esta é a única cópia
  // da senha que existe. Fica num aviso persistente, fora do modal, para
  // não sumir quando o formulário fechar.
  const [createdCredentials, setCreatedCredentials] = useState<{
    email: string;
    password: string;
  } | null>(null);
  const [createForm, setCreateForm] =
    useState<CreateFormState>(EMPTY_CREATE_FORM);

  function openCreateModal() {
    setCreateMsg("");
    setCreateForm(EMPTY_CREATE_FORM);
    setIsCreateOpen(true);
  }

  function handleCreate() {
    if (
      !createForm.principalName.trim() ||
      !createForm.companyName.trim() ||
      !createForm.principalEmail.trim()
    ) {
      setCreateMsg("Preencha nome do responsável, empresa e e-mail.");
      return;
    }
    setCreateMsg("");
    setIsCreating(true);
    startTransition(async () => {
      const result = await createCompanyAction({
        full_name: createForm.principalName,
        company_name: createForm.companyName,
        email: createForm.principalEmail,
        phone: createForm.principalPhone || null,
        template_id: createForm.templateId || null,
        manual_dashboard: createForm.manualDashboard,
      });
      setIsCreating(false);
      if (!result.ok) {
        setCreateMsg(result.message);
        return;
      }
      if (!result.emailDelivered && result.temporaryPassword) {
        setCreatedCredentials({
          email: result.email,
          password: result.temporaryPassword,
        });
      }
      setIsCreateOpen(false);
      setPage(0);
      setSearch("");
      refreshList();
    });
  }

  // ---- Edição ----
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editingCompanyId, setEditingCompanyId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<EditFormState>(EMPTY_EDIT_FORM);
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [editMsg, setEditMsg] = useState("");

  function openEditModal(companyItem: CompanyAdminListItem) {
    setEditingCompanyId(companyItem.id);
    setEditForm({
      name: companyItem.name,
      email: companyItem.email,
      phone: companyItem.phone ?? "",
    });
    setEditMsg("");
    setIsEditOpen(true);
  }

  function handleSaveEdit() {
    if (editingCompanyId === null) return;
    if (!editForm.name.trim() || !editForm.email.trim()) {
      setEditMsg("Nome e e-mail são obrigatórios.");
      return;
    }
    setIsSavingEdit(true);
    setEditMsg("");
    startTransition(async () => {
      const result = await updateCompanyAction(editingCompanyId, {
        name: editForm.name,
        email: editForm.email,
        phone: editForm.phone || null,
      });
      setIsSavingEdit(false);
      if (!result.ok) {
        setEditMsg(result.message);
        return;
      }
      setIsEditOpen(false);
      refreshList();
    });
  }

  // ---- Exclusão em cascata ----
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [deletingCompany, setDeletingCompany] =
    useState<CompanyAdminListItem | null>(null);
  const [deleteImpact, setDeleteImpact] = useState<CompanyAdminDetail | null>(
    null,
  );
  const [isLoadingImpact, setIsLoadingImpact] = useState(false);
  const [confirmChecked, setConfirmChecked] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteMsg, setDeleteMsg] = useState("");

  function openDeleteModal(companyItem: CompanyAdminListItem) {
    setDeletingCompany(companyItem);
    setDeleteImpact(null);
    setConfirmChecked(false);
    setDeleteMsg("");
    setIsDeleteOpen(true);
    setIsLoadingImpact(true);
    getCompanyAdminDetailAction(companyItem.id)
      .then((detail) => setDeleteImpact(detail))
      .catch((error: unknown) => {
        setDeleteMsg(
          error instanceof Error
            ? error.message
            : "Falha ao calcular o impacto da exclusão.",
        );
      })
      .finally(() => setIsLoadingImpact(false));
  }

  function handleConfirmDelete() {
    if (!deletingCompany || !confirmChecked) return;
    setIsDeleting(true);
    setDeleteMsg("");
    startTransition(async () => {
      const result = await deleteCompanyAction(deletingCompany.id);
      setIsDeleting(false);
      if (!result.ok) {
        setDeleteMsg(result.message);
        return;
      }
      setIsDeleteOpen(false);
      setDeletingCompany(null);
      setDeleteImpact(null);
      refreshList();
    });
  }

  // ---- Apresentação ----
  const temResultado = companies.length > 0;
  const primeiroDaPagina = total === 0 ? 0 : page * PAGE_SIZE + 1;
  const ultimoDaPagina = page * PAGE_SIZE + companies.length;

  return (
    <main className="min-h-screen bg-(--color-surface)">
      {/*
        Faixa branca no lugar do `.card` de antes: o cabeçalho gastava
        ~110 px acima da dobra para um título e uma frase de instrução
        que se lê uma vez. O aviso de cascata desceu para o modal de
        exclusão, que é onde a decisão acontece. Mesmo padrão de faixa
        usado em `[id]/layout.tsx`.
      */}
      <div className="border-b border-(--color-neutral) bg-white">
        <div className="container-page flex flex-wrap items-center justify-between gap-4 py-6">
          <div>
            <h1 className="text-2xl font-semibold text-(--color-dark)">
              Empresas
            </h1>
            <p className="mt-1 text-sm text-zinc-600">
              Clientes auditados — cadastro, responsável e acesso ao quadro de
              cada um.
            </p>
          </div>
          <button type="button" className="btn-primary" onClick={openCreateModal}>
            Nova empresa
          </button>
        </div>
      </div>

      <div className="container-page space-y-6 py-6">
        {createdCredentials && (
          <div
            role="alert"
            className="rounded-xl border border-amber-400 bg-amber-50 p-4 text-sm text-amber-900"
          >
            <p className="font-semibold">
              O e-mail de credenciais não foi enviado.
            </p>
            <p className="mt-1">
              Anote a senha temporária agora — ela não será exibida novamente e
              não há recuperação de senha na plataforma.
            </p>
            <dl className="mt-3 space-y-1 font-mono text-base">
              <div className="flex gap-2">
                <dt className="text-amber-800">E-mail:</dt>
                <dd>{createdCredentials.email}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="text-amber-800">Senha:</dt>
                <dd className="tracking-wider">{createdCredentials.password}</dd>
              </div>
            </dl>
            <button
              type="button"
              className="mt-3 text-sm font-medium underline"
              onClick={() => setCreatedCredentials(null)}
            >
              Já anotei, ocultar
            </button>
          </div>
        )}

        <section className="card">
          {/* Busca e contagem na mesma faixa: o resultado do filtro fica
              ao lado do filtro, não no rodapé da tabela. */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative w-full sm:max-w-md">
              <label htmlFor="busca-empresas" className="sr-only">
                Buscar empresa
              </label>
              <span
                aria-hidden="true"
                className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-zinc-400"
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                >
                  <circle cx="11" cy="11" r="7" />
                  <path d="m20 20-3.5-3.5" />
                </svg>
              </span>
              <input
                id="busca-empresas"
                type="search"
                placeholder="Buscar por empresa ou responsável..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(0);
                }}
                className="field py-2 pl-9 text-sm"
              />
              {search ? (
                <button
                  type="button"
                  aria-label="Limpar o campo de busca"
                  className="absolute top-1/2 right-2 -translate-y-1/2 rounded-full px-2 py-1 text-sm text-zinc-500 transition hover:bg-zinc-100"
                  onClick={() => {
                    setSearch("");
                    setPage(0);
                  }}
                >
                  ×
                </button>
              ) : null}
            </div>

            <p className="text-sm whitespace-nowrap text-zinc-500">
              {total} empresa{total === 1 ? "" : "s"}
            </p>
          </div>

          {listError ? (
            <ListErrorState
              message={listError}
              onRetry={refreshList}
              isRetrying={isPending}
            />
          ) : null}

          <div className="mt-4" aria-live="polite">
            {isLoadingList ? (
              <CompaniesSkeleton />
            ) : !temResultado ? (
              <EmptyState
                search={search}
                onClearSearch={() => {
                  setSearch("");
                  setPage(0);
                }}
                onCreate={openCreateModal}
              />
            ) : (
              <>
                {/*
                  `table-fixed`: com larguras automáticas o navegador
                  distribuía espaço por volume de texto, e a coluna do
                  telefone ficava estreita a ponto de quebrar
                  "(21) 98765-4321" em três linhas. Aqui a largura segue
                  a importância da informação, e o `truncate` das células
                  só funciona porque a largura é conhecida.

                  Sem `overflow-x-auto` neste nível: abaixo de `lg` a
                  lista vira cards, então não há o que rolar de lado — e
                  o menu "⋯", que é `absolute`, não pode ter ancestral
                  com overflow, senão fica recortado.
                */}
                <table className="hidden w-full table-fixed text-left text-sm lg:table">
                  <caption className="sr-only">
                    Empresas clientes cadastradas na plataforma
                  </caption>
                  <thead>
                    <tr className="border-b border-(--color-neutral) text-[11px] font-medium tracking-wide text-zinc-500 uppercase">
                      <th scope="col" className="w-[32%] pb-2 pr-4">
                        Empresa
                      </th>
                      <th scope="col" className="w-[26%] pb-2 pr-4">
                        Responsável
                      </th>
                      <th scope="col" className="w-[15%] pb-2 pr-4">
                        Equipe
                      </th>
                      <th scope="col" className="w-[110px] pb-2 pr-4">
                        Cadastrada
                      </th>
                      <th scope="col" className="w-[170px] pb-2 text-right">
                        <span className="sr-only">Ações</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {companies.map((item) => (
                      <CompanyRow
                        key={item.id}
                        company={item}
                        onEdit={openEditModal}
                        onDelete={openDeleteModal}
                      />
                    ))}
                  </tbody>
                </table>

                <ul className="space-y-3 lg:hidden">
                  {companies.map((item) => (
                    <CompanyCard
                      key={item.id}
                      company={item}
                      onEdit={openEditModal}
                      onDelete={openDeleteModal}
                    />
                  ))}
                </ul>
              </>
            )}
          </div>

          {totalPages > 1 || page > 0 ? (
            <nav
              aria-label="Paginação das empresas"
              className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-(--color-neutral) pt-4 text-sm text-zinc-600"
            >
              <span>
                Mostrando {primeiroDaPagina}–{ultimoDaPagina} de {total} ·
                página {page + 1} de {totalPages}
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="btn-secondary px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={page === 0 || isLoadingList}
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                >
                  Anterior
                </button>
                <button
                  type="button"
                  className="btn-secondary px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={page + 1 >= totalPages || isLoadingList}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Próxima
                </button>
              </div>
            </nav>
          ) : null}
        </section>
      </div>

      {isCreateOpen ? (
        <CreateCompanyModal
          form={createForm}
          templates={templates}
          message={createMsg}
          isSubmitting={isCreating || isPending}
          onChange={(patch) => setCreateForm((prev) => ({ ...prev, ...patch }))}
          onSubmit={handleCreate}
          onClose={() => setIsCreateOpen(false)}
        />
      ) : null}

      {isEditOpen ? (
        <EditCompanyModal
          form={editForm}
          message={editMsg}
          isSubmitting={isSavingEdit || isPending}
          onChange={(patch) => setEditForm((prev) => ({ ...prev, ...patch }))}
          onSubmit={handleSaveEdit}
          onClose={() => setIsEditOpen(false)}
        />
      ) : null}

      {isDeleteOpen && deletingCompany ? (
        <DeleteCompanyModal
          companyName={deletingCompany.name}
          impact={deleteImpact}
          isLoadingImpact={isLoadingImpact}
          confirmChecked={confirmChecked}
          isDeleting={isDeleting || isPending}
          message={deleteMsg}
          onToggleConfirm={setConfirmChecked}
          onConfirm={handleConfirmDelete}
          onClose={() => setIsDeleteOpen(false)}
        />
      ) : null}
    </main>
  );
}
