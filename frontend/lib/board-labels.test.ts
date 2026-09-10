import { describe, expect, it } from "vitest";

import {
  DEFAULT_LABEL_COLOR,
  TRELLO_COLOR_MAP,
  labelChipClass,
  labelChipStyle,
  sortLabels,
  trelloColorToHex,
  type BoardLabel,
} from "./board-labels";

describe("labelChipStyle", () => {
  it("usa o hex do banco como cor de fundo", () => {
    expect(labelChipStyle("#96311D")).toEqual({ backgroundColor: "#96311D" });
  });

  it("expande hex curto", () => {
    expect(labelChipStyle("#abc")).toEqual({ backgroundColor: "#aabbcc" });
  });

  it("cai no default em vez de deixar o chip sem cor", () => {
    expect(labelChipStyle("nao-e-cor")).toEqual({
      backgroundColor: DEFAULT_LABEL_COLOR,
    });
  });

  it("aceita nome de cor do Trello ainda não convertido", () => {
    expect(labelChipStyle("red_dark")).toEqual({ backgroundColor: "#96311D" });
  });
});

describe("labelChipClass", () => {
  it("usa texto claro sobre fundo escuro", () => {
    expect(labelChipClass("#96311D")).toContain("text-white");
  });

  it("usa texto escuro sobre fundo claro", () => {
    expect(labelChipClass("#FFFFFF")).toContain("text-zinc-900");
  });

  it("sempre inclui a classe de forma do chip", () => {
    expect(labelChipClass("#000000")).toContain("label-chip");
  });
});

describe("sortLabels", () => {
  const etiquetas: (BoardLabel & { sort_order: number })[] = [
    { id: 3, name: "Baixa Criticidade", color: "#2C5A8C", sort_order: 3 },
    { id: 1, name: "Item Critico", color: "#96311D", sort_order: 0 },
    { id: 2, name: "Alta Criticidade", color: "#C2410C", sort_order: 1 },
  ];

  it("ordena por sort_order", () => {
    expect(sortLabels(etiquetas).map((e) => e.name)).toEqual([
      "Item Critico",
      "Alta Criticidade",
      "Baixa Criticidade",
    ]);
  });

  it("desempata por nome", () => {
    const empatadas = [
      { id: 1, name: "Zebra", color: "#000", sort_order: 0 },
      { id: 2, name: "Alfa", color: "#000", sort_order: 0 },
    ];
    expect(sortLabels(empatadas).map((e) => e.name)).toEqual(["Alfa", "Zebra"]);
  });

  it("não muta o array recebido", () => {
    const original = [...etiquetas];
    sortLabels(etiquetas);
    expect(etiquetas).toEqual(original);
  });

  it("trata sort_order ausente como 0", () => {
    const semOrdem: BoardLabel[] = [
      { id: 1, name: "B", color: "#000" },
      { id: 2, name: "A", color: "#000" },
    ];
    expect(sortLabels(semOrdem).map((e) => e.name)).toEqual(["A", "B"]);
  });
});

describe("trelloColorToHex", () => {
  it("converte todas as 11 cores do quadro de origem", () => {
    expect(Object.keys(TRELLO_COLOR_MAP)).toHaveLength(11);
    for (const nome of Object.keys(TRELLO_COLOR_MAP)) {
      expect(trelloColorToHex(nome)).toMatch(/^#[0-9A-F]{6}$/i);
    }
  });

  it("cai no default para cor desconhecida ou ausente", () => {
    expect(trelloColorToHex("sky_neon")).toBe(DEFAULT_LABEL_COLOR);
    expect(trelloColorToHex(null)).toBe(DEFAULT_LABEL_COLOR);
    expect(trelloColorToHex(undefined)).toBe(DEFAULT_LABEL_COLOR);
  });
});
