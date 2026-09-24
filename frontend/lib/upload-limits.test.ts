import { describe, expect, it } from "vitest";

import { MAX_EVIDENCE_BYTES, evidenceSizeError } from "./upload-limits";

describe("evidenceSizeError", () => {
  it("aceita o arquivo pequeno", () => {
    expect(evidenceSizeError({ size: 1024 })).toBeNull();
  });

  it("aceita arquivo exatamente no limite (mesma regra do backend)", () => {
    expect(evidenceSizeError({ size: MAX_EVIDENCE_BYTES })).toBeNull();
  });

  it("recusa 1 byte acima do limite", () => {
    expect(evidenceSizeError({ size: MAX_EVIDENCE_BYTES + 1 })).toMatch(
      /limite é 10 MB/,
    );
  });

  it("informa o tamanho do arquivo em formato brasileiro", () => {
    const dezEMeio = 10.5 * 1024 * 1024;
    expect(evidenceSizeError({ size: dezEMeio })).toBe(
      "O arquivo tem 10,5 MB e o limite é 10 MB",
    );
  });
});
