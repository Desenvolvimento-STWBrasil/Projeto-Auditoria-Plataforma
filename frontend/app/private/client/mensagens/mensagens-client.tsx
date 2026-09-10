"use client";

import { useEffect, useState, useTransition } from "react";
import {
  CompanyMessage,
  markMyCompanyMessagesAsReadAction,
  sendMyCompanyMessageAction,
} from "./actions";

type MensagensClientProps = {
  companyId: number;
  initialMessages: CompanyMessage[];
};

export function MensagensClient({
  companyId,
  initialMessages,
}: MensagensClientProps) {
  const [messages, setMessages] = useState<CompanyMessage[]>(initialMessages);
  const [draft, setDraft] = useState("");
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    markMyCompanyMessagesAsReadAction(companyId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleSend() {
    if (!draft.trim()) return;
    const content = draft.trim();
    setDraft("");

    startTransition(async () => {
      const result = await sendMyCompanyMessageAction(companyId, content);
      if (result.ok) {
        setMessages((prev) => [...prev, result.created]);
      } else {
        window.alert(result.message);
      }
    });
  }
  return (
    <main className="min-h-screen bg-(--color-surface) py-8">
      <div className="container-page space-y-6">
        <header className="card">
          <h1 className="text-2xl font-semibold text-(--color-dark)">
            Mensagens
          </h1>
          <p className="mt-1 text-sm text-zinc-600">
            Canal direto com a equipe de auditoria, para dúvidas gerais fora do
            escopo de um controle específico.
          </p>
        </header>

        <article className="card flex h-128 flex-col">
          <div className="flex-1 space-y-2 overflow-y-auto">
            {messages.length === 0 ? (
              <p className="text-sm text-zinc-600">
                Nenhuma mensagem ainda. Envie a primeira.
              </p>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                    message.is_from_admin
                      ? "bg-zinc-100 text-(--color-dark)"
                      : "ml-auto bg-(--color-primary) text-white"
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
              disabled={isPending}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSend();
              }}
            />
            <button
              type="button"
              className="btn-primary"
              disabled={isPending || !draft.trim()}
              onClick={handleSend}
            >
              Enviar
            </button>
          </div>
        </article>
      </div>
    </main>
  );
}
