/**
 * Cabeçalho único de página privada (card + h1 + subtítulo + ação opcional).
 *
 * Antes desta extração, o admin ("Resumo") e o cliente ("Dashboard do
 * Cliente") reimplementavam o mesmo bloco com classes digitadas à mão em
 * cada arquivo — pequenas divergências (tamanho de fonte, espaçamento)
 * se acumulavam sem ninguém perceber. Com um único componente, mudar o
 * padrão visual do cabeçalho é uma edição em um lugar só.
 */
type PageHeaderProps = {
  title: string;
  description?: string;
  action?: React.ReactNode;
};

export function PageHeader({ title, description, action }: PageHeaderProps) {
  return (
    <header className="card">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-(--color-dark)">
            {title}
          </h1>
          {description ? (
            <p className="mt-1 text-sm text-zinc-600">{description}</p>
          ) : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
    </header>
  );
}
