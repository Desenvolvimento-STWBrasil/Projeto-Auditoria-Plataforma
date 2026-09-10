import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

/**
 * M-08b — configuração de testes do frontend.
 *
 * **Ambiente padrão: `node`.** Server Actions, `lib/` e `proxy.ts` são
 * código de servidor — não têm DOM, e rodá-los sob jsdom não é só
 * desnecessário: quebra. O jsdom instala seus próprios `Uint8Array` e
 * `TextEncoder`, de outro realm, e o `jose` recusa a chave com
 * `TypeError: payload must be an instance of Uint8Array`. Isso atingiria
 * `lib/session.ts` e `proxy.ts`, que fazem `new TextEncoder().encode(...)`.
 *
 * Testes de componente declaram o ambiente que precisam no topo do
 * arquivo:
 *
 *     // @vitest-environment jsdom
 *
 * Dois aliases carregam o resto do peso:
 *
 * - `server-only` existe para EXPLODIR quando importado fora do
 *   servidor. `lib/session.ts` o importa de propósito, como barreira.
 *   Sob o Vitest não há o runtime do Next, então aponta para um módulo
 *   vazio — a barreira continua valendo no `next build`, que é onde ela
 *   importa.
 * - `@` reproduz o `paths` do tsconfig.json.
 */
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "node",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["{app,lib,_components}/**/*.{test,spec}.{ts,tsx}", "*.test.ts"],
    exclude: ["node_modules/**", ".next/**"],
    coverage: {
      provider: "v8",
      include: ["app/**/actions.ts", "lib/**/*.ts", "proxy.ts"],
      reporter: ["text", "text-summary"],
    },
  },
  resolve: {
    alias: {
      "@": resolve(__dirname, "."),
      "server-only": resolve(__dirname, "test/stubs/server-only.ts"),
    },
  },
});
