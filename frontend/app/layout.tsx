import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Plataforma de Auditoria",
  description: "Gestao de evidencias e controles de auditoria",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="pt-BR"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      {/*
        `suppressHydrationWarning` por causa de EXTENSÃO DE NAVEGADOR, não
        de código nosso.

        Extensões escrevem atributos no `<body>` antes do React hidratar —
        ColorZilla põe `cz-shortcut-listen="true"`, Grammarly põe
        `data-gr-ext-installed`, e há outras. O HTML do servidor não os
        tem, o do cliente sim, e o React reclama de uma divergência que
        nenhuma mudança no `layout.tsx` resolve: ele é estático (nenhum
        `Date.now()`, nenhum `typeof window`, nenhuma classe dinâmica).

        O custo de NÃO suprimir não é o aviso em si — é o aviso aparecer
        em todo carregamento em desenvolvimento, virar ruído esperado e,
        com isso, esconder uma divergência de hidratação de verdade.

        O alcance é estreito de propósito: `suppressHydrationWarning` vale
        um nível só, para os atributos e o texto DESTE elemento. Nada
        dentro de `{children}` deixa de ser verificado, e o `<body>` daqui
        não tem atributo dinâmico nenhum para mascarar.
      */}
      <body className="min-h-full flex flex-col" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
