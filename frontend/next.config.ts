import type { NextConfig } from "next";

/* 
Teto de corpo das requisições que passam pelo next - 10 MB de evidência
*/

const LIMIT_CORP_UPLOAD = "11mb";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    serverActions: {
      /* Padrão do next é 1MB - o upload de evidência passa por Server Action */
      bodySizeLimit: LIMIT_CORP_UPLOAD,
    },

    /* O proxy.ts roda em /private/* e bufferiza o corpo com teto padrão de 10MB; acima disso trunca em silencio ou seja, ele aceita um pedaço do arquivo e deixa a evidência corrompida sem dar erro */
    proxyClientMaxBodySize: LIMIT_CORP_UPLOAD,
  },
};

export default nextConfig;
