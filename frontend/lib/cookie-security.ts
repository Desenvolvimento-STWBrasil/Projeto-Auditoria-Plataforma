/* 
Decide se os cookies de sessão levam a flag `Secure`

A regra segue o endereço PÚBLICO do ambiente (APP_URL), não o NODE_ENV:
- https://... -> Secure (o navegador só devolve o cookie por HTTPS)
- http://... -> sem Secure (produção pelo IP sem domínio, túnel, dev local)

Antes era `NODE_ENV` === "production": a imagem Docker sempre marcava Secure e, no acesso por http://IP, navegador descartava o cookie - o login "passava" mas a sessão sumia (ver ADR-001, D7).
Quando o domínio com HTTPS existir, basta trocar APP_URL no .env
*/

export function isSecureCookie(
  appUrl: string | undefined = process.env.APP_URL,
): boolean {
  return (appUrl ?? "").trim().toLowerCase().startsWith("https://");
}
