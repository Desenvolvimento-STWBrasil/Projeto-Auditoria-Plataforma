"use client";

/**
 * Sub-usuários de uma empresa, resumidos em um chip que abre.
 *
 * Este era o pior ponto da listagem. A célula mostrava a lista completa
 * de e-mails dentro de 220 px com `break-all`, e `break-all` quebra no
 * meio da palavra: `patricia.alm / eida@horizo / nteconstrut /
 * ora.com.br`. Quatro linhas por e-mail, duas ou três pessoas por
 * empresa — a célula sozinha definia a altura da linha inteira (~120 px)
 * e continuava ilegível.
 *
 * A troca é chip fechado por padrão (altura constante em toda a tabela)
 * com os e-mails a um clique, dentro da própria linha. O dado não sai da
 * tela: o requisito era desamontoar, não esconder.
 *
 * `truncate` no lugar de `break-all` — cortar no fim com reticências
 * ainda deixa o e-mail reconhecível; quebrar no meio, não. O `title`
 * devolve o endereço inteiro no hover.
 */
type SubUsersCellProps = {
  companyName: string;
  emails: string[];
  count: number;
};

export function SubUsersCell({
  companyName,
  emails,
  count,
}: SubUsersCellProps) {
  if (count === 0) {
    return (
      <span className="text-sm text-zinc-400" aria-label="Sem colaboradores">
        —
      </span>
    );
  }

  const rotulo = `${count} colaborador${count > 1 ? "es" : ""}`;

  return (
    <details className="group">
      <summary
        className="inline-flex cursor-pointer list-none items-center gap-1 rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-700 transition hover:bg-zinc-200"
        title={`Ver os colaboradores de ${companyName}`}
      >
        <span
          aria-hidden="true"
          className="text-[9px] transition group-open:rotate-90"
        >
          ▶
        </span>
        {rotulo}
      </summary>

      <ul className="mt-2 space-y-1">
        {emails.map((email) => (
          <li
            key={email}
            title={email}
            className="truncate text-xs text-zinc-500"
          >
            {email}
          </li>
        ))}
      </ul>
    </details>
  );
}
