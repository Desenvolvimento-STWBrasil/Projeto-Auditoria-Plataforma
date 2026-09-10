"use server";

import { revalidatePath } from "next/cache";
import { callBackend } from "@/lib/server-backend";
import { getAccessToken, requireAdmin } from "@/lib/session";

export type CompanyAdminListItem = {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  principal_user_id: number;
  principal_full_name: string;
  principal_email: string;
  sub_user_count: number;
  sub_user_emails: string[];
  created_at: string;
};

export type CompanyAdminDetail = CompanyAdminListItem & {
  audit_count: number;
  dashboard_card_count: number;
  company_message_count: number;
};

export type PaginatedCompanies = {
  total: number;
  skip: number;
  limit: number;
  items: CompanyAdminListItem[];
};

export type TemplateOption = { id: number; name: string };

const PAGE_SIZE = 10;

/** Lista paginada de empresas, com busca opcional. Backend: GET /api/v1/admin/companies. */
export async function listCompaniesAdminAction(
  page: number,
  search: string,
): Promise<PaginatedCompanies> {
  await requireAdmin();
  const token = await getAccessToken();
  const skip = page * PAGE_SIZE;
  const query = new URLSearchParams({
    skip: String(skip),
    limit: String(PAGE_SIZE),
  });
  if (search.trim()) query.set("search", search.trim());

  return callBackend<PaginatedCompanies>(
    `/api/v1/admin/companies?${query.toString()}`,
    { token: token ?? undefined },
  );
}

/** Detalhe de uma empresa (contagens de impacto). Backend: GET /api/v1/admin/companies/{id}. */
export async function getCompanyAdminDetailAction(
  companyId: number,
): Promise<CompanyAdminDetail> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<CompanyAdminDetail>(
    `/api/v1/admin/companies/${companyId}`,
    { token: token ?? undefined },
  );
}

/** Templates de dashboard, para o formulário de nova empresa. Backend: GET /api/v1/onboarding/templates. */
export async function listTemplatesAction(): Promise<TemplateOption[]> {
  await requireAdmin();
  const token = await getAccessToken();
  return callBackend<TemplateOption[]>("/api/v1/onboarding/templates", {
    token: token ?? undefined,
  });
}

export type CreateCompanyInput = {
  full_name: string;
  company_name: string;
  email: string;
  phone: string | null;
  template_id: number | null;
  manual_dashboard: boolean;
};

type OnboardingResponse = {
  user_id: number;
  company_id: number;
  dashboard_id: number;
  dashboard_cards_created: number;
  email_delivered: boolean;
  temporary_password: string | null;
};

export type CreateCompanyResult =
  | {
      ok: true;
      /** true = credenciais entregues por e-mail; false = exiba a senha. */
      emailDelivered: boolean;
      /**
       * Preenchida SOMENTE quando `emailDelivered === false` (B-A29).
       * Sem SMTP configurado, esta é a ÚNICA cópia da credencial que
       * existe — o backend só guarda o hash e não há recuperação de
       * senha na plataforma.
       */
      temporaryPassword: string | null;
      email: string;
    }
  | { ok: false; message: string };

/**
 * Cria a empresa + usuário principal + dashboard inicial. Backend: POST
 * /api/v1/onboarding/principal-user — mesmo endpoint já usado pelo modal
 * "Novo usuário" do Dashboard Admin (evita duplicar a regra de negócio de
 * onboarding, que já envia e-mail de credenciais e trata e-mail duplicado
 * com 409; ver seção 2 de M.1 em docs/plano_implementacao.md).
 */
export async function createCompanyAction(
  input: CreateCompanyInput,
): Promise<CreateCompanyResult> {
  await requireAdmin();
  const token = await getAccessToken();

  let created: OnboardingResponse;
  try {
    created = await callBackend<OnboardingResponse>(
      "/api/v1/onboarding/principal-user",
      {
        method: "POST",
        token: token ?? undefined,
        body: input,
      },
    );
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao criar a empresa.";
    return { ok: false, message };
  }

  revalidatePath("/private/admin/empresas");
  return {
    ok: true,
    emailDelivered: created.email_delivered,
    temporaryPassword: created.temporary_password,
    email: input.email,
  };
}

export type UpdateCompanyInput = {
  name: string;
  email: string;
  phone: string | null;
};

export type UpdateCompanyResult =
  | { ok: true; company: CompanyAdminDetail }
  | { ok: false; message: string };

/** Edita nome/e-mail/telefone da empresa. Backend: PATCH /api/v1/admin/companies/{id}. */
export async function updateCompanyAction(
  companyId: number,
  input: UpdateCompanyInput,
): Promise<UpdateCompanyResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const company = await callBackend<CompanyAdminDetail>(
      `/api/v1/admin/companies/${companyId}`,
      { method: "PATCH", token: token ?? undefined, body: input },
    );
    revalidatePath("/private/admin/empresas");
    return { ok: true, company };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao editar a empresa.";
    return { ok: false, message };
  }
}

export type CompanyDeletionSummary = {
  company_id: number;
  company_name: string;
  deleted_principal_user_id: number;
  deleted_sub_users: number;
  deleted_sub_user_requests: number;
  deleted_audits: number;
  deleted_audit_controls: number;
  deleted_dashboard_cards: number;
  deleted_company_messages: number;
};

export type DeleteCompanyResult =
  | { ok: true; summary: CompanyDeletionSummary }
  | { ok: false; message: string };

/**
 * Exclui a empresa em cascata (usuários, auditorias, evidências,
 * dashboard, chats — ver backend/app/services/company_admin.py). Sem
 * confirmação nesta função — o Client Component é quem exibe o modal de
 * aviso antes de chamar esta action. Backend: DELETE
 * /api/v1/admin/companies/{id}.
 */
export async function deleteCompanyAction(
  companyId: number,
): Promise<DeleteCompanyResult> {
  await requireAdmin();
  const token = await getAccessToken();

  try {
    const summary = await callBackend<CompanyDeletionSummary>(
      `/api/v1/admin/companies/${companyId}`,
      { method: "DELETE", token: token ?? undefined },
    );
    revalidatePath("/private/admin/empresas");
    return { ok: true, summary };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Falha ao excluir a empresa.";
    return { ok: false, message };
  }
}
