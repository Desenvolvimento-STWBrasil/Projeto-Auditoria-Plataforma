import { requireClient } from "@/lib/session";
import { getClientBoardAction, getMyCompanyAction } from "./actions";
import { ClientBoardClient } from "./client-board-client";

export default async function ClientBoardPage() {
  await requireClient();

  const company = await getMyCompanyAction();
  const board = await getClientBoardAction(company.id);

  /*
   * O detalhe do primeiro card não é mais pré-carregado: o card abre em
   * modal, e o modal nasce fechado. Mesma mudança feita no dashboard do
   * admin, pela mesma razão — era uma ida ao backend para preencher um
   * painel que o cliente talvez nem olhasse.
   */
  return <ClientBoardClient companyName={company.name} board={board} />;
}
