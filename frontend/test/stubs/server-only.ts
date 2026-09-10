/**
 * Stub de `server-only` para o ambiente de teste.
 *
 * O pacote real não exporta nada — ele existe para falhar no build
 * quando um módulo de servidor é importado por um Client Component.
 * Essa barreira continua ativa no `next build`; sob o Vitest, onde não
 * há a distinção servidor/cliente do Next, ela só impediria os testes
 * de importar `lib/session.ts`.
 */
export {};
