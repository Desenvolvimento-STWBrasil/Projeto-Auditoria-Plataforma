"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { getSafeRedirectPath } from "@/lib/safe-redirect";

type LoginResponse = {
  ok: true;
  role: "admin" | "user" | "sub-user" | null;
};

export function LoginForm() {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const router = useRouter();
  const searchParams = useSearchParams();

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErro("");

    if (!email || !senha) {
      setErro("Preencha e-mail e senha.");
      return;
    }

    setIsLoading(true);

    try {
      const loginResp = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password: senha }),
      });

      const data = (await loginResp.json().catch(() => null)) as
        | LoginResponse
        | { detail?: string }
        | null;

      if (!loginResp.ok || !data || !("ok" in data)) {
        const detail = data && "detail" in data ? data.detail : undefined;
        throw new Error(detail ?? "Não foi possível entrar.");
      }

      const redirect = getSafeRedirectPath(
        searchParams.get("redirect"),
        data.role === "admin" ? "/private/admin" : "/private/client",
      );
      router.push(redirect);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Erro inesperado.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-(--color-surface) flex items-center justify-center">
      <div className="w-full max-w-5xl px-4">
        <div className="mx-auto grid w-full overflow-hidden rounded-3xl border border-(--color-neutral) bg-white shadow-sm md:grid-cols-2">
          <section className="bg-(--color-dark) p-8 text-white md:p-10">
            <p className="mb-3 inline-block rounded-full bg-white/15 px-3 py-1 text-xs font-medium">
              Plataforma de Auditoria
            </p>
            <h1 className="text-3xl font-semibold leading-tight">
              Acesse sua conta
            </h1>
            <p className="mt-4 text-sm text-zinc-200">
              Entre para acessar seu dashboard.
            </p>
          </section>

          <section className="p-8 md:p-10">
            <h2 className="text-2xl font-semibold text-(--color-dark)">
              Login
            </h2>

            <form onSubmit={handleSubmit} className="mt-6 space-y-4">
              <div>
                <label
                  htmlFor="email"
                  className="mb-1 block text-sm font-medium"
                >
                  E-mail
                </label>
                <input
                  id="email"
                  type="email"
                  className="field"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="voce@empresa.com"
                />
              </div>

              <div>
                <label
                  htmlFor="senha"
                  className="mb-1 block text-sm font-medium"
                >
                  Senha
                </label>
                <input
                  id="senha"
                  type="password"
                  className="field"
                  value={senha}
                  onChange={(e) => setSenha(e.target.value)}
                  placeholder="Digite sua senha"
                />
              </div>

              {erro ? (
                <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {erro}
                </p>
              ) : null}

              <button
                type="submit"
                className="btn-primary w-full"
                disabled={isLoading}
              >
                {isLoading ? "Entrando..." : "Entrar"}
              </button>
            </form>
          </section>
        </div>
      </div>
    </main>
  );
}
