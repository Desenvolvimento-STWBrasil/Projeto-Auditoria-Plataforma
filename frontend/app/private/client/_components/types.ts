import type { ControlStatus } from "@/lib/control-status";

export type AutorConversa = "AUDITORIA" | "CLIENTE";

export type Controle = {
  id: string;
  codigo: string;
  titulo: string;
  descricao: string;
  evidenciaEsperada: string;
  status: ControlStatus;
  evidencias: string[];
  conversa: { autor: AutorConversa; mensagem: string }[];
};
