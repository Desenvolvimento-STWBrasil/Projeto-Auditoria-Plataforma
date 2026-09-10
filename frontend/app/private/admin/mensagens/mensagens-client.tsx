/* eslint-disable react-hooks/set-state-in-effect */
"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import {
  CompanyMessage,
  CompanyWithUnread,
  listCompanyMessagesAction,
  markCompanyMessagesAsReadAction,
  sendCompanyMessageAction,
} from "./actions";

type MensagensClientProps = {
  initialCompanies: CompanyWithUnread[];
  initialSelectedCompanyId: number | null;
  initialMessages: CompanyMessage[];
  initialHighlightMessageId?: number | null;
};

export function MensagensClient({
  initialCompanies,
  initialSelectedCompanyId,
  initialMessages,
  initialHighlightMessageId = null,
}: MensagensClientProps) {
  const [companies, setCompanies] = useState(initialCompanies);
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(
    initialSelectedCompanyId,
  );
  const [messages, setMessages] = useState<CompanyMessage[]>(initialMessages);
  const [draft, setDraft] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isPending, startTransition] = useTransition();
  const isFirstRender = useRef(true);
  const [highlightMessageId, setHighlightMessageId] = useState<number | null>(
    initialHighlightMessageId,
  );
  const messageRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  // Busca as mensagens da empresa selecionada sob demanda — pula a
  // primeira renderização, pois a empresa inicial já veio pronta via
  // props (initialMessages), sem precisar de fetch no cliente. Mesmo
  // padrão já usado em admin-dashboard-client.tsx.
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    if (selectedCompanyId === null) {
      setMessages([]);
      return;
    }

    let cancelado = false;
    setIsLoading(true);
    listCompanyMessagesAction(selectedCompanyId)
      .then((data) => {
        if (!cancelado) setMessages(data);
      })
      .finally(() => {
        if (!cancelado) setIsLoading(false);
      });

    return () => {
      cancelado = true;
    };
  }, [selectedCompanyId]);

  /* Marca com lidas os mensagens do cliente ao abrir/troca de empresa */
  useEffect(() => {
    if (selectedCompanyId === null) return;
    markCompanyMessagesAsReadAction(selectedCompanyId).then(() => {
      setCompanies((prev) =>
        prev.map((c) =>
          c.id === selectedCompanyId ? { ...c, unread_count: 0 } : c,
        ),
      );
    });
  }, [selectedCompanyId]);

  // Deep-link vindo da Home (/private/admin/mensagens?empresa=&conversa=):
  // rola até a mensagem indicada e a destaca por alguns segundos. Roda
  // sempre que a lista de mensagens muda (não só na montagem), pois na
  // primeira renderização `messages` já vem pronta via props, mas o ref
  // do elemento só existe depois do primeiro paint.
  useEffect(() => {
    if (highlightMessageId == null) return;
    const node = messageRefs.current.get(highlightMessageId);
    if (!node) return;

    node.scrollIntoView({ behavior: "smooth", block: "center" });
    const timeout = setTimeout(() => setHighlightMessageId(null), 3000);
    return () => clearTimeout(timeout);
  }, [highlightMessageId, messages]);

  function handleSend() {
    if (selectedCompanyId === null || !draft.trim()) return;
    const content = draft.trim();
    setDraft("");

    startTransition(async () => {
      const result = await sendCompanyMessageAction(selectedCompanyId, content);
      if (result.ok) {
        setMessages((prev) => [...prev, result.created]);
      } else {
        window.alert(result.message);
      }
    });
  }

  const selectedCompany = companies.find((c) => c.id === selectedCompanyId);

  return (
    <main className="min-h-screen bg-(--color-surface) py-8">
      <div className="container-page space-y-6">
        <header className="card">
          <h1 className="text-2xl font-semibold text-(--color-dark)">
            Mensagens
          </h1>
          <p className="mt-1 text-sm text-zinc-600">
            Canal de comunicação geral com cada empresa, fora do escopo de um
            controle ou card específico.
          </p>
        </header>

        <div className="grid gap-6 lg:grid-cols-3">
          <section className="space-y-2 lg:col-span-1">
            {companies.length === 0 ? (
              <p className="text-sm text-zinc-600">
                Nenhuma empresa cadastrada ainda.
              </p>
            ) : (
              companies.map((company) => (
                <button
                  key={company.id}
                  type="button"
                  onClick={() => setSelectedCompanyId(company.id)}
                  className={`card w-full text-left transition ${
                    company.id === selectedCompanyId
                      ? "ring-2 ring-(--color-primary)"
                      : ""
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold">
                      {company.name}
                    </span>
                    {company.unread_count > 0 ? (
                      <span className="rounded-full bg-(--color-primary) px-2 py-0.5 text-xs font-semibold text-white">
                        {company.unread_count}
                      </span>
                    ) : null}
                  </div>
                </button>
              ))
            )}
          </section>

          <section className="lg:col-span-2">
            <article className="card flex h-128 flex-col">
              <h2 className="text-base font-semibold">
                {selectedCompany
                  ? selectedCompany.name
                  : "Selecione uma empresa"}
              </h2>

              <div className="mt-3 flex-1 space-y-2 overflow-y-auto">
                {isLoading ? (
                  <p className="text-sm text-zinc-500">
                    Carregando mensagens...
                  </p>
                ) : messages.length === 0 ? (
                  <p className="text-sm text-zinc-600">
                    Nenhuma mensagem ainda. Envie a primeira.
                  </p>
                ) : (
                  messages.map((message) => (
                    <div
                      key={message.id}
                      data-message-id={message.id}
                      ref={(node) => {
                        if (node) messageRefs.current.set(message.id, node);
                        else messageRefs.current.delete(message.id);
                      }}
                      className={`max-w-[80%] rounded-lg px-3 py-2 text-sm transition-colors duration-500 ${
                        message.is_from_admin
                          ? "ml-auto bg-(--color-primary) text-white"
                          : "bg-zinc-100 text-(--color-dark)"
                      } ${
                        highlightMessageId === message.id
                          ? "ring-2 ring-offset-2 ring-amber-400"
                          : ""
                      }`}
                    >
                      <p className="text-xs opacity-70">
                        {message.author.full_name}
                      </p>
                      <p>{message.content}</p>
                    </div>
                  ))
                )}
              </div>

              <div className="mt-4 flex gap-2">
                <input
                  className="field flex-1"
                  placeholder="Escreva uma mensagem..."
                  value={draft}
                  disabled={selectedCompanyId === null || isPending}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleSend();
                  }}
                />
                <button
                  type="button"
                  className="btn-primary"
                  disabled={
                    selectedCompanyId === null || isPending || !draft.trim()
                  }
                  onClick={handleSend}
                >
                  Enviar
                </button>
              </div>
            </article>
          </section>
        </div>
      </div>
    </main>
  );
}
