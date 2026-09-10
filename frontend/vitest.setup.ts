import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";

/**
 * O `cleanup` do Testing Library só é carregado quando o teste roda sob
 * jsdom — o ambiente padrão é `node` (ver vitest.config.ts), e importar
 * `@testing-library/react` sem DOM falha na hora.
 */
afterEach(async () => {
  if (typeof document !== "undefined") {
    const { cleanup } = await import("@testing-library/react");
    cleanup();
  }
  vi.clearAllMocks();
});
