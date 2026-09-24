/* 
Limite único de tamanho das evidências no frontend

Espelha `MAX_UPLOAD_MB` de backend/app/api/v1/client.py - o backend é a autoridade (responde 413)
este módulo existe para o navegador recusar ANTES de subir o arquivo, em vez de o usuário esperar o envio de 30 MB
só para receber um erro. Se um dia o limite mudar, mude nos dois lugares e em next.config.ts (LIMIT_CORP_UPLOAD) e nginx.conf (client_max_body_size)
*/

export const MAX_EVIDENCE_MB = 10;
export const MAX_EVIDENCE_BYTES = MAX_EVIDENCE_MB * 1024 * 1024;

/* 
Devolve a mensagem de erro para o usuário se o arquivo passar do limite,
ou `null` se ele puder ser enviado. Mesma regra do backend: exatamente 10 MB
é aceito, 1 byte a mais é recusado (`total > max_bytes`)
*/

export function evidenceSizeError(file: Pick<File, "size">): string | null {
  if (file.size <= MAX_EVIDENCE_BYTES) return null;
  const tamanhoMb = (file.size / 1024 / 1024).toLocaleString("pt-BR", {
    maximumFractionDigits: 1,
  });
  return `O arquivo tem ${tamanhoMb} MB e o limite é ${MAX_EVIDENCE_MB} MB`;
}
