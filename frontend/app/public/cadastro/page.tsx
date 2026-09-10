"use client";

import { PublicAuthCleanup } from "@/_components/public-auth-cleanup";
import { useState } from "react";

type FormData = {
  nome: string;
  email: string;
  senha: string;
  telefone: string;
  confirmarSenha: string;
  accepted: boolean;
};

type FormErrors = Partial<Record<keyof FormData, string>>;

const inicialFormData: FormData = {
  nome: "",
  email: "",
  telefone: "",
  senha: "",
  confirmarSenha: "",
  accepted: false,
};

function CadastroPage() {
  const [formData, setFormData] = useState<FormData>(inicialFormData);
  const [errors, setErrors] = useState<FormErrors>({});
  const [apiMessage, setApiMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  function handleChange(field: keyof FormData, value: string | boolean) {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: "" }));
    setApiMessage("");
  }

  function validateForm(data: FormData): FormErrors {
    const nextErrors: FormErrors = {};

    if (!data.nome.trim()) nextErrors.nome = "Nome é obrigatório";
    if (!data.email.trim()) {
      nextErrors.email = "E-mail é obrigatório";
    } else if (!/^\S+@\S+\.\S+$/.test(data.email)) {
      nextErrors.email = "Informe um e-mail inválido";
    }

    if (!data.senha) {
      nextErrors.senha = "Senha é obrigatória";
    } else if (data.senha.length < 10) {
      nextErrors.senha = "A senha deve conter no mínimo 10 caracteres";
    } else if (
      !/[A-Z]/.test(data.senha) ||
      !/[a-z]/.test(data.senha) ||
      !/\d/.test(data.senha) ||
      !/[^\w\s]/.test(data.senha)
    ) {
      nextErrors.senha =
        "Use maiúscula, minúscula, número e caractere especial.";
    }

    if (!data.confirmarSenha) {
      nextErrors.confirmarSenha = "Confirmação de senha é obrigatória";
    } else if (data.confirmarSenha !== data.senha) {
      nextErrors.confirmarSenha = "As senhas não coincidem";
    }

    if (!data.accepted) {
      nextErrors.accepted = "Você precisa aceitar os termos de uso.";
    }

    return nextErrors;
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setApiMessage("");

    const validationErrors = validateForm(formData);
    setErrors(validationErrors);

    if (Object.keys(validationErrors).length > 0) return;

    setIsLoading(true);

    try {
      const payload = {
        full_name: formData.nome,
        email: formData.email,
        password: formData.senha,
        phone: formData.telefone || undefined,
      };

      const response = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.detail ?? "Não foi possível realizar o cadastro.");
      }

      setApiMessage("Cadastro realizado com sucesso!");
      setFormData(inicialFormData);
    } catch (error) {
      setApiMessage(
        error instanceof Error
          ? error.message
          : "Não foi possível realizar o cadastro. Tente novamente.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-(--color-surface) flex items-center justify-center">
      <PublicAuthCleanup />
      <div className="container-page">
        <div className="mx-auto w-full max-w-2xl card">
          <h1 className="text-2xl font-semibold text-(--color-dark)">Criar conta</h1>
          <p className="mt-1 text-sm text-zinc-600">
            Preencha seus dados para acessar a plataforma.
          </p>
          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium">Nome completo</label>
              <input
                className={`field ${errors.nome ? "border-red-400" : ""}`}
                value={formData.nome}
                onChange={(e) => handleChange("nome", e.target.value)}
                placeholder="Seu nome"
              />
              {errors.nome ? <p className="mt-1 text-xs text-red-600">{errors.nome}</p> : null}
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium">E-mail</label>
              <input
                type="email"
                className={`field ${errors.email ? "border-red-400" : ""}`}
                value={formData.email}
                onChange={(e) => handleChange("email", e.target.value)}
                placeholder="voce@empresa.com"
              />
              {errors.email ? (
                <p className="mt-1 text-xs text-red-600">{errors.email}</p>
              ) : null}
            </div>

            <div>
              <label
                htmlFor="telefone"
                className="mb-1 block text-sm font-medium text-(--color-dark)"
              >
                Telefone
              </label>
              <input
                id="telefone"
                type="tel"
                className="field"
                placeholder="(11) 99999-8888"
                value={formData.telefone}
                onChange={(event) => handleChange("telefone", event.target.value)}
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium">Senha</label>
              <input
                type="password"
                className={`field ${errors.senha ? "border-red-400" : ""}`}
                value={formData.senha}
                onChange={(e) => handleChange("senha", e.target.value)}
                placeholder="Mín. 10 caracteres"
              />
              {errors.senha ? (
                <p className="mt-1 text-xs text-red-600">{errors.senha}</p>
              ) : null}
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Confirmar senha</label>
              <input
                type="password"
                className={`field ${errors.confirmarSenha ? "border-red-400" : ""}`}
                value={formData.confirmarSenha}
                onChange={(e) => handleChange("confirmarSenha", e.target.value)}
                placeholder="Repita a senha"
              />
              {errors.confirmarSenha ? (
                <p className="mt-1 text-xs text-red-600">{errors.confirmarSenha}</p>
              ) : null}
            </div>

            <div>
              <input
                type="checkbox"
                id="terms"
                checked={formData.accepted}
                onChange={(e) => handleChange("accepted", e.target.checked)}
                className="h-4 w-4"
              />
              <label htmlFor="terms" className="text-sm text-gray-700 px-1">
                Li e aceito os termos de uso
              </label>
              {errors.accepted ? (
                <p className="mt-1 text-xs text-red-600">{errors.accepted}</p>
              ) : null}
            </div>

            {apiMessage ? (
              <p className="rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm">
                {apiMessage}
              </p>
            ) : null}
            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                className="btn-primary flex-1"
                disabled={isLoading}
              >
                {isLoading ? "Criando conta..." : "Criar conta"}
              </button>
              <a href="/public/login" className="btn-secondary flex-1 text-center">
                Já tenho conta
              </a>
            </div>
          </form>
        </div>
      </div>
    </main>
  );
}

export default CadastroPage;
