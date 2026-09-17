import Link from "next/link";

import { PublicAuthCleanup } from "@/_components/public-auth-cleanup";

const highlights = [
  {
    title: "Gestão de Evidências",
    description:
      "Envio e acompanhamento de arquivos com histórico de atualizações.",
  },
  {
    title: "Análise por Status",
    description:
      "Visualização por Em análise, Parcial (50%) e Conforme (100%).",
  },
  {
    title: "Comunicação Centralizada",
    description: "Canal de dúvidas entre cliente e auditoria no mesmo fluxo.",
  },
  {
    title: "Enviar evidência",
    description:
      "Permite ao usuário anexar documentos, imagens ou arquivos que comprovem a execução ou conformidade de um item avaliado. Essas evidências serão utilizadas para análise pela equipe de auditoria.",
  },
  {
    title: "Auditoria analisa",
    description:
      "Nesta etapa, a equipe de auditoria revisa as evidências enviadas, verificando sua validade, consistência e aderência aos critérios estabelecidos.",
  },
  {
    title: "Resultado de conformidade",
    description:
      "Apresenta o resultado final da análise, indicando se o item está em conformidade, não conformidade ou se requer ajustes adicionais, com base nas evidências avaliadas.",
  },
];

export default function Home() {
  return (
    <>
      <main className="min-h-screen bg-(--color-surface)">
        <PublicAuthCleanup />
        <header className="border-b border-(--color-neutral) bg-white">
          <div className="container-page flex h-16 items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="inline-block h-3 w-3 rounded-full bg-(--color-primary)" />
              <strong className="text-sm md:text-base">
                Plataforma de Auditoria
              </strong>
            </div>
            <nav className="hidden items-center gap-2 md:flex">
              <Link href="/public/login" className="btn-secondary">
                Entrar
              </Link>
              <Link href="/public/cadastro" className="btn-primary">
                Criar conta
              </Link>
            </nav>
          </div>
        </header>

        <section className="container-page py-12 md:py-16">
          <div className="grid gap-6 md:grid-cols-2 md:items-center">
            <div>
              <p className="mb-3 inline-flex rounded-full bg-(--color-primary)/10 px-3 py-1 text-xs font-semibold text-(--color-primary)">
                ISO 27001 - Controles e Evidências
              </p>
              <h1 className="text-3xl font-semibold leading-tight md:text-5xl">
                Centralize auditoria, evidências e comunicação em um só lugar.
              </h1>
              <p className="mt-4 max-w-xl text-sm text-zinc-700 md:text-base">
                Uma interface intuitiva para clientes e auditores acompanharem
                status, anexos e histórico de conformidade com segurança e
                clareza.
              </p>
              <div className="mt-6 flex flex-col gap-3 sm:flex-row">
                <Link href="/public/login" className="btn-primary">
                  Acessar login
                </Link>
                <Link
                  href="/public/cadastro"
                  className="btn-secondary text-center"
                >
                  Quero me cadastrar
                </Link>
              </div>
            </div>
            {/* B-B11: atalhos diretos para as areas privadas so existem em
                desenvolvimento. Em producao eles anunciavam as rotas internas
                na home publica, sem qualquer proposito para o visitante. */}
            {process.env.NODE_ENV === "development" && (
              <div className="card">
                <h2 className="text-lg font-semibold">
                  Acessos rápidos (fase de desenvolvimento)
                </h2>
                <p className="mt-1 text-sm text-zinc-600">
                  Atalhos para validação visual das telas enquanto o backend é
                  finalizado.
                </p>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <Link
                    href="/private/admin"
                    className="btn-secondary text-center"
                  >
                    Dashboard Admin
                  </Link>
                  <Link
                    href="/private/client"
                    className="btn-secondary text-center"
                  >
                    Dashboard Clientes
                  </Link>
                </div>
              </div>
            )}
          </div>
        </section>

        <section className="container-page pb-12 md:pb-16">
          <div className="grid gap-4 md:grid-cols-3">
            {highlights.map((item) => (
              <article key={item.title} className="card">
                <h3 className="text-base font-semibold">{item.title}</h3>
                <p className="mt-2 text-sm text-zinc-700">{item.description}</p>
              </article>
            ))}
          </div>
        </section>
      </main>
    </>
  );
}

/* Fase 6 - Fundação do Frontend */
/* Começar as implementações front end */
