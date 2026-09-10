from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.access import member_user_ids
from app.models.audit import Audit
from app.models.audit_control import AuditControl
from app.models.company_dashboard import Company, Dashboard, DashboardCard
from app.models.company_message import CompanyMessage
from app.models.sub_user_request import SubUserRequest
from app.models.user import User
from app.models.evidence import Evidence
from app.models.dashboard_board import DashboardColumn


class CompanyNotFoundError(Exception):
    """Levantada quando `company_id` não existe — o router converte para
    404. Separada de um `ValueError` genérico para não ser confundida com
    erro de validação de payload."""


@dataclass
class CompanyAdminData:
    """Linha "achatada" de empresa + usuário principal + contagens,
    usada tanto pela listagem quanto pelo detalhe (a diferença entre os
    dois é só quais campos o schema Pydantic expõe — ver
    schemas/company_admin.py)."""

    company: Company
    principal_full_name: str
    principal_email: str
    sub_user_count: int
    sub_user_emails: list[str]
    audit_count: int
    dashboard_card_count: int
    company_message_count: int


@dataclass
class CompanyDeletionSummaryData:
    company_id: int
    company_name: str
    deleted_principal_user_id: int
    deleted_sub_users: int
    deleted_sub_user_requests: int
    deleted_audits: int
    deleted_audit_controls: int
    deleted_dashboard_cards: int
    deleted_company_messages: int
    evidence_storage_keys: list[str]
    deleted_dashboard_columns: int = 0


def _load_admin_data(db: Session, company: Company) -> CompanyAdminData:
    principal = db.get(User, company.principal_user_id)
    if principal is None:
        # Não deveria acontecer (FK RESTRICT garante o usuário principal
        # sempre existir enquanto a empresa existir) — defensivo.
        raise CompanyNotFoundError("Usuário principal da empresa não encontrado")

    member_ids = member_user_ids(db, company.principal_user_id)

    sub_user_emails = list(
        db.scalars(
            select(User.email)
            .where(User.parent_user_id == company.principal_user_id)
            .order_by(User.email.asc())
        ).all()
    )
    sub_user_count = len(sub_user_emails)

    audit_count = (
        db.scalar(
            select(func.count(Audit.id)).where(Audit.client_user_id.in_(member_ids))
        )
        or 0
    )

    dashboard_card_count = 0
    if company.dashboard is not None:
        dashboard_card_count = (
            db.scalar(
                select(func.count(DashboardCard.id)).where(
                    DashboardCard.dashboard_id == company.dashboard.id
                )
            )
            or 0
        )

    company_message_count = (
        db.scalar(
            select(func.count(CompanyMessage.id)).where(
                CompanyMessage.company_id == company.id
            )
        )
        or 0
    )

    return CompanyAdminData(
        company=company,
        principal_full_name=principal.full_name,
        principal_email=principal.email,
        sub_user_count=sub_user_count,
        sub_user_emails=sub_user_emails,
        audit_count=audit_count,
        dashboard_card_count=dashboard_card_count,
        company_message_count=company_message_count,
    )


def _bulk_admin_data(db: Session, companies: list[Company]) -> list[CompanyAdminData]:
    """
    Monta o `CompanyAdminData` de VÁRIAS empresas com um número constante
    de queries (B-M26).

    `_load_admin_data` continua sendo o caminho certo para UMA empresa (o
    detalhe em `GET /admin/companies/{id}`). Reusá-la num laço custava ~7
    queries por linha — 143 numa página de 20, medido por sonda. É o
    padrão clássico de N+1 em código bem organizado: **uma função de
    detalhe reusada numa listagem**, e a função de detalhe está certa.

    Duas dessas 7 queries liam a MESMA linha de `users` duas vezes
    (`member_user_ids` e `sub_user_emails`, com projeções diferentes).
    Aqui os sub-usuários são lidos uma vez só e servem aos dois usos.
    """
    if not companies:
        return []

    company_ids = [c.id for c in companies]
    principal_ids = [c.principal_user_id for c in companies]
    principal_to_company = {c.principal_user_id: c.id for c in companies}

    # 1 query: usuários principais + sub-usuários da página, de uma vez.
    users = db.scalars(
        select(User).where(
            or_(User.id.in_(principal_ids), User.parent_user_id.in_(principal_ids))
        )
    ).all()

    principal_by_id: dict[int, User] = {}
    subs_by_parent: dict[int, list[User]] = {}
    for user in users:
        if user.parent_user_id is not None:
            subs_by_parent.setdefault(user.parent_user_id, []).append(user)
        if user.id in principal_to_company:
            principal_by_id[user.id] = user

    # member_ids por principal, sem nenhuma query adicional.
    member_to_principal: dict[int, int] = {}
    for principal_id in principal_ids:
        member_to_principal[principal_id] = principal_id
        for sub in subs_by_parent.get(principal_id, []):
            member_to_principal[sub.id] = principal_id

    # 1 query: dashboards da página.
    dashboard_to_company: dict[int, int] = dict(
        db.execute(
            select(Dashboard.id, Dashboard.company_id).where(
                Dashboard.company_id.in_(company_ids)
            )
        ).all()
    )

    # 1 query: contagem de cards por dashboard, reagrupada por empresa.
    cards_by_company: dict[int, int] = {}
    if dashboard_to_company:
        rows = db.execute(
            select(DashboardCard.dashboard_id, func.count(DashboardCard.id))
            .where(DashboardCard.dashboard_id.in_(dashboard_to_company.keys()))
            .group_by(DashboardCard.dashboard_id)
        ).all()
        for dashboard_id, total in rows:
            company_id = dashboard_to_company[dashboard_id]
            cards_by_company[company_id] = cards_by_company.get(company_id, 0) + total

    # 1 query: auditorias por membro, reagrupadas por empresa. `Audit` não
    # tem `company_id` — a FK real é `client_user_id`, que pode ser o
    # principal OU qualquer sub-usuário dele.
    audits_by_company: dict[int, int] = {}
    if member_to_principal:
        rows = db.execute(
            select(Audit.client_user_id, func.count(Audit.id))
            .where(Audit.client_user_id.in_(member_to_principal.keys()))
            .group_by(Audit.client_user_id)
        ).all()
        for client_user_id, total in rows:
            company_id = principal_to_company[member_to_principal[client_user_id]]
            audits_by_company[company_id] = audits_by_company.get(company_id, 0) + total

    # 1 query: mensagens gerais por empresa.
    messages_by_company: dict[int, int] = dict(
        db.execute(
            select(CompanyMessage.company_id, func.count(CompanyMessage.id))
            .where(CompanyMessage.company_id.in_(company_ids))
            .group_by(CompanyMessage.company_id)
        ).all()
    )

    resultado: list[CompanyAdminData] = []
    for company in companies:
        principal = principal_by_id.get(company.principal_user_id)
        if principal is None:
            # FK RESTRICT garante que não acontece enquanto a empresa
            # existir; defensivo, e coerente com _load_admin_data.
            raise CompanyNotFoundError("Usuário principal da empresa não encontrado")

        subs = sorted(
            subs_by_parent.get(company.principal_user_id, []),
            key=lambda u: u.email,
        )
        resultado.append(
            CompanyAdminData(
                company=company,
                principal_full_name=principal.full_name,
                principal_email=principal.email,
                sub_user_count=len(subs),
                sub_user_emails=[s.email for s in subs],
                audit_count=audits_by_company.get(company.id, 0),
                dashboard_card_count=cards_by_company.get(company.id, 0),
                company_message_count=messages_by_company.get(company.id, 0),
            )
        )
    return resultado


def list_companies_admin(
    db: Session, *, search: str | None, skip: int, limit: int
) -> tuple[list[CompanyAdminData], int]:
    """Lista paginada de empresas para a tela "Lista de Empresas",
    com busca por nome/e-mail da empresa OU nome/e-mail do usuário
    principal (o admin normalmente lembra de um dos dois, não
    necessariamente do nome exato da empresa).

    Custo constante em número de queries (B-M26): 2 para a página
    (contagem + linhas) + 5 agregadas, independentemente de `limit`."""

    base_query = select(Company).join(User, User.id == Company.principal_user_id)

    if search:
        term = f"%{search.strip()}%"
        base_query = base_query.where(
            or_(
                Company.name.ilike(term),
                Company.email.ilike(term),
                User.full_name.ilike(term),
                User.email.ilike(term),
            )
        )

    total = (
        db.scalar(
            select(func.count()).select_from(
                base_query.with_only_columns(Company.id).subquery()
            )
        )
        or 0
    )

    companies = list(
        db.scalars(
            base_query.order_by(Company.name.asc()).offset(skip).limit(limit)
        ).all()
    )

    return _bulk_admin_data(db, companies), total


def get_company_admin_detail(db: Session, company_id: int) -> CompanyAdminData:
    company = db.get(Company, company_id)
    if company is None:
        raise CompanyNotFoundError("Empresa não encontrada")
    return _load_admin_data(db, company)


def update_company_admin(
    db: Session,
    company_id: int,
    *,
    name: str,
    email: str,
    phone: str | None,
) -> Company:
    """Atualiza os campos cadastrais da empresa. Não altera o usuário
    principal (nome/e-mail de login) — decisão de escopo registrada na
    seção 2 de M.1 em docs/plano_implementacao.md, para não misturar
    edição de empresa com troca de credencial de acesso, que tem
    implicações de segurança próprias (reenvio de e-mail, sessões ativas
    etc.) fora do escopo deste CRUD. `db.flush()` (não `commit()`) para o
    router controlar o commit e poder capturar `IntegrityError` de nomes/
    e-mails duplicados antes de persistir."""

    company = db.get(Company, company_id)
    if company is None:
        raise CompanyNotFoundError("Empresa não encontrada")

    company.name = name
    company.email = email
    company.phone = phone
    db.flush()
    return company


def delete_company_cascade(db: Session, company_id: int) -> CompanyDeletionSummaryData:
    """Exclui uma empresa e **tudo** que depende dela, numa única
    transação — usuário principal, sub-usuários, solicitações de
    sub-usuário pendentes, auditorias (+ controles + evidências +
    mensagens), dashboard (+ cards + notas + checklist + histórico +
    mensagens do card) e o chat geral da empresa (`company_messages`).

    Feito por exclusão explícita (`db.delete()` por objeto, não SQL cru
    em massa) em ordem de dependência — não confia só no `ON DELETE
    CASCADE` do banco (que existe no MySQL de produção, ver migrations
    9d5a3c1b2e77/bf7239a52df8, mas o SQLite usado nos testes não aplica
    FKs por padrão) nem em cascade automático do SQLAlchemy para
    `Audit`/`SubUserRequest` (que não têm relationship declarada a partir
    de `Company`, pois a FK real é `Audit.client_user_id -> users.id`,
    não `company_id` — não existe essa coluna em `audits`). A ordem
    importa: 1) sub_user_requests e audits (dependem só dos usuários,
    não da empresa) 2) a empresa em si (cascata ORM para dashboard/
    company_messages, ver Company.dashboard/Company.messages em
    models/company_dashboard.py) 3) sub-usuários 4) usuário principal —
    só depois do passo 2, pois `Company.principal_user_id` é
    `ON DELETE RESTRICT`.

    Levanta `sqlalchemy.exc.IntegrityError` (sem capturar) se restar
    alguma referência não prevista — o router converte para 409 em vez de
    deixar a exclusão parcial committada. Nenhum commit é feito aqui; o
    router chama `db.commit()` após checar que não houve exceção, para
    manter o padrão dos outros endpoints (ex.: admin_onboarding.py)."""

    company = db.get(Company, company_id)
    if company is None:
        raise CompanyNotFoundError("Empresa não encontrada")

    # Números "antes" da exclusão, para o resumo devolvido ao frontend —
    # reaproveita a mesma contagem exposta em GET /admin/companies/{id},
    # calculada antes de qualquer `db.delete()` desta função.
    data = _load_admin_data(db, company)

    dashboard_column_count = 0
    if company.dashboard is not None:
        dashboard_column_count = (
            db.scalar(
                select(func.count(DashboardColumn.id)).where(
                    DashboardColumn.dashboard_id == company.dashboard.id
                )
            )
            or 0
        )

    principal_user_id = company.principal_user_id
    member_ids = member_user_ids(db, principal_user_id)
    company_name = company.name

    # 1) Solicitações de sub-usuário pendentes/processadas de qualquer
    #    membro da empresa (principal ou sub-usuário) como solicitante.
    pending_requests = list(
        db.scalars(
            select(SubUserRequest).where(
                SubUserRequest.principal_user_id.in_(member_ids)
            )
        ).all()
    )
    for request in pending_requests:
        db.delete(request)
    db.flush()

    # 2) Auditorias de qualquer membro — cascata ORM já configurada em
    #    Audit.controls / AuditControl.evidences / AuditControl.messages.
    audits = list(
        db.scalars(select(Audit).where(Audit.client_user_id.in_(member_ids))).all()
    )
    audit_ids = [audit.id for audit in audits]
    # Contado ANTES de deletar: depois de `db.delete(audit)` + `flush()`, o
    # objeto Audit é expirado e ler `audit.controls` de novo dispararia um
    # SELECT que não acha mais nada (ObjectDeletedError), já que a cascata
    # ORM (Audit.controls, cascade="all, delete-orphan") já apagou os
    # AuditControl junto no mesmo flush.
    audit_control_count = (
        db.scalar(
            select(func.count(AuditControl.id)).where(
                AuditControl.audit_id.in_(audit_ids)
            )
        )
        or 0
        if audit_ids
        else 0
    )

    # B-A26: os storage_key precisam ser lidos ANTES do db.delete(audit) —
    # a cascata ORM (Audit.controls -> AuditControl.evidences) apaga as
    # linhas de `evidences` no mesmo flush, e depois disso não há como
    # descobrir quais arquivos ficaram órfãos em uploads/.
    evidence_storage_keys: list[str] = []
    if audit_ids:
        evidence_storage_keys = list(
            db.scalars(
                select(Evidence.storage_key)
                .join(AuditControl, AuditControl.id == Evidence.audit_control_id)
                .where(AuditControl.audit_id.in_(audit_ids))
            ).all()
        )

    for audit in audits:
        db.delete(audit)
    db.flush()

    # 3) A empresa — cascata ORM para dashboard/cards/notas/checklist/
    #    histórico/mensagens do card e para o chat geral (company_messages).
    db.delete(company)
    db.flush()

    # 4) Sub-usuários, depois o usuário principal (nesta ordem: o
    #    principal só pode ser removido depois de todos os sub-usuários,
    #    que apontam para ele via parent_user_id).
    sub_users = list(
        db.scalars(select(User).where(User.parent_user_id == principal_user_id)).all()
    )
    for sub_user in sub_users:
        db.delete(sub_user)
    db.flush()

    principal_user = db.get(User, principal_user_id)
    if principal_user is not None:
        db.delete(principal_user)
        db.flush()

    return CompanyDeletionSummaryData(
        company_id=company_id,
        company_name=company_name,
        deleted_principal_user_id=principal_user_id,
        deleted_sub_users=len(sub_users),
        deleted_sub_user_requests=len(pending_requests),
        deleted_audits=len(audits),
        deleted_audit_controls=audit_control_count,
        deleted_dashboard_cards=data.dashboard_card_count,
        deleted_dashboard_columns=dashboard_column_count,
        deleted_company_messages=data.company_message_count,
        evidence_storage_keys=evidence_storage_keys,
    )
