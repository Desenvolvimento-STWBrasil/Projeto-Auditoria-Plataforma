import { describe, expect, it } from "vitest";

import {
  FUSO_DA_PLATAFORMA,
  formatarData,
  formatarDataHora,
} from "./date-format";

/*
 * O instante que expõe o defeito: 01:00 UTC de 09/09 é 22:00 de 08/09 em
 * São Paulo. Formatado no fuso do contêiner (UTC) sai "09/09"; no
 * navegador de quem opera daqui, "08/09". Era essa diferença que o React
 * acusava como divergência de hidratação em `empresas-client.tsx`.
 */
const VIRADA_DO_DIA = "2026-09-09T01:00:00Z";

describe("formatarData", () => {
  it("resolve a virada do dia pelo fuso da plataforma, não pelo UTC", () => {
    expect(formatarData(VIRADA_DO_DIA)).toBe("08/09/2026");
  });

  it("não depende do fuso da máquina que renderiza", () => {
    /*
     * A propriedade que conserta a hidratação: o resultado é o mesmo no
     * servidor (contêiner em UTC) e no cliente (navegador em qualquer
     * fuso), porque `timeZone` está declarado no formatador.
     *
     * Comparar com um formatador explicitamente pinado no MESMO fuso
     * demonstra isso sem depender do `TZ` do processo de teste — se
     * `date-format` deixasse de pinar, a igualdade quebraria em toda
     * máquina que não estivesse em São Paulo.
     */
    const pinado = new Date(VIRADA_DO_DIA).toLocaleString("pt-BR", {
      timeZone: FUSO_DA_PLATAFORMA,
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });

    expect(formatarData(VIRADA_DO_DIA)).toBe(pinado);
  });

  it("e o fuso pinado NÃO é UTC — pinar em UTC consertaria a hidratação e mostraria a data errada", () => {
    const emUtc = new Date(VIRADA_DO_DIA).toLocaleString("pt-BR", {
      timeZone: "UTC",
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });

    expect(emUtc).toBe("09/09/2026");
    expect(formatarData(VIRADA_DO_DIA)).not.toBe(emUtc);
  });

  it("formata data comum em dd/mm/aaaa", () => {
    expect(formatarData("2026-09-09T15:00:00Z")).toBe("09/09/2026");
  });

  it("devolve string vazia para entrada inválida", () => {
    // Melhor um espaço em branco na tabela do que "Invalid Date" no meio
    // de uma listagem de auditoria.
    expect(formatarData("")).toBe("");
    expect(formatarData("não é data")).toBe("");
  });
});

describe("formatarDataHora", () => {
  it("inclui hora e minuto no fuso da plataforma", () => {
    // 01:00 UTC = 22:00 do dia anterior em São Paulo.
    expect(formatarDataHora(VIRADA_DO_DIA)).toBe("08/09/2026, 22:00");
  });

  it("distingue dois eventos do mesmo dia", () => {
    // É o requisito do histórico do card: sem hora, duas mudanças de
    // status no mesmo dia ficariam indistinguíveis.
    const manha = formatarDataHora("2026-09-09T12:00:00Z");
    const tarde = formatarDataHora("2026-09-09T18:00:00Z");

    expect(manha).not.toBe(tarde);
    expect(manha).toBe("09/09/2026, 09:00");
    expect(tarde).toBe("09/09/2026, 15:00");
  });

  it("devolve string vazia para entrada inválida", () => {
    expect(formatarDataHora("qualquer coisa")).toBe("");
  });
});
