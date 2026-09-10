import { getAuditDetailAction, listAuditsAction } from "./actions";
import { AuditoriasClient } from "./auditorias-client";

export default async function AdminAuditoriasPage(
  props: PageProps<"/private/admin/auditorias">,
) {
  const searchParams = await props.searchParams;
  const auditIdParam = Array.isArray(searchParams.auditId)
    ? searchParams.auditId[0]
    : searchParams.auditId;
  const requestedAuditId = auditIdParam ? Number(auditIdParam) : NaN;

  const paginated = await listAuditsAction();
  const firstAuditId = paginated.items[0]?.id ?? null;

  let selectedAuditId = Number.isFinite(requestedAuditId)
    ? requestedAuditId
    : firstAuditId;
  let initialDetail = selectedAuditId
    ? await getAuditDetailAction(selectedAuditId).catch(() => null)
    : null;

  // Se o auditId da URL não existir (auditoria removida, id inválido,
  // digitado à mão...), cai de volta para a primeira auditoria da lista
  // em vez de mostrar a tela sem nenhuma seleção.

  if (!initialDetail && selectedAuditId !== firstAuditId) {
    selectedAuditId = firstAuditId;
    initialDetail = firstAuditId
      ? await getAuditDetailAction(firstAuditId).catch(() => null)
      : null;
  }

  return (
    <AuditoriasClient
      initialAudits={paginated.items}
      initialSelectedAuditId={initialDetail ? selectedAuditId : null}
      initialDetail={initialDetail}
    />
  );
}
