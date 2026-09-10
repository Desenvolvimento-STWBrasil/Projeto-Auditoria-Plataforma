"""
Seed de dados de demonstração para inspecionar o fluxo real do dashboard.

Cria 5 empresas fictícias, cada uma com 1 cliente principal + 2 sub-usuários,
um dashboard com 9 cards baseados em controles estilo ISO 27001 (status
variado por empresa, para simular diferentes níveis de maturidade), notas,
checklist, histórico, mensagens por card (Q&A) e mensagens do chat geral da
empresa.

Idempotente por e-mail: se a empresa (pelo e-mail do usuário principal) já
existir, ela é pulada — rodar de novo não duplica dados.

Uso:
    cd backend
    ./venv/Scripts/python.exe scripts/seed_demo_companies.py

Senha de login de todos os usuários criados por este script: Teste123
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.company_dashboard import (
    DashboardCard,
    DashboardCardchecklistItem,
    DashboardCardHistoryEntry,
    DashboardCardMessage,
    DashboardCardNote,
    DashboardCardStatus,
    DashboardMessageType,
    DashboardTemplate,
    DashboardTemplateCard,
)
from app.models.company_message import CompanyMessage
from app.models.user import User
from app.services.dashboard_builder import create_company_dashboard_from_template
from app.services.users import create_user, get_user_by_email

DEMO_PASSWORD = "Teste123"

NOW = datetime.now(timezone.utc)

CO = DashboardCardStatus.CONFORME
PA = DashboardCardStatus.PARCIAL
NA = DashboardCardStatus.NAOCONFORME
EM = DashboardCardStatus.EM_ANALISE

# Controles do template de demonstração (código, título, tema/tag) — estilo
# ISO/IEC 27001:2022 Anexo A, mesma inspiração do scripts/seed_catalog.py.
DEMO_CONTROLS: tuple[tuple[str, str, str], ...] = (
    ("5.1", "Política de Segurança da Informação", "Organizacional"),
    ("5.2", "Papéis e Responsabilidades de Segurança da Informação", "Organizacional"),
    ("5.3", "Segregação de Funções", "Organizacional"),
    ("5.7", "Inteligência de Ameaças", "Organizacional"),
    ("5.23", "Segurança da Informação no Uso de Serviços em Nuvem", "Organizacional"),
    ("6.3", "Conscientização, Educação e Treinamento em Segurança da Informação", "Pessoas"),
    ("7.4", "Monitoramento de Segurança Física", "Físico"),
    ("8.8", "Gestão de Vulnerabilidades Técnicas", "Tecnológico"),
    ("8.24", "Uso de Criptografia", "Tecnológico"),
)

DEMO_TEMPLATE_NAME = "Controles Essenciais - ISO 27001:2022"

NOTE_TEXT = {
    CO: "Evidências apresentadas atendem integralmente ao controle. Sem pendências identificadas nesta revisão.",
    PA: "Controle parcialmente implementado. Parte das evidências foi apresentada; itens remanescentes descritos no checklist.",
    NA: "Controle não atende aos requisitos mínimos. Evidências insuficientes ou ausentes — plano de ação corretivo necessário até a próxima revisão.",
}

CHECKLIST_DONE = {
    CO: (True, True),
    PA: (True, False),
    NA: (False, False),
}


def _at(days_ago: float, hour: int = 10) -> datetime:
    return (NOW - timedelta(days=days_ago)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )


class DemoCompany:
    def __init__(
        self,
        *,
        name: str,
        phone: str,
        principal_name: str,
        principal_email: str,
        sub_users: list[tuple[str, str]],
        card_statuses: list[DashboardCardStatus],
        signup_days_ago: int,
        chat: list[tuple[str, str, float, bool]],
    ) -> None:
        self.name = name
        self.phone = phone
        self.principal_name = principal_name
        self.principal_email = principal_email
        self.sub_users = sub_users
        self.card_statuses = card_statuses
        self.signup_days_ago = signup_days_ago
        # chat: (author "principal"|"admin", content, days_ago, read)
        self.chat = chat


DEMO_COMPANIES: list[DemoCompany] = [
    DemoCompany(
        name="TechNova Soluções em TI Ltda",
        phone="(11) 91234-5678",
        principal_name="Marina Duarte Ferreira",
        principal_email="marina.ferreira@technova.com.br",
        sub_users=[
            ("Bruno Castro Lima", "bruno.lima@technova.com.br"),
            ("Fernanda Oliveira Rocha", "fernanda.rocha@technova.com.br"),
        ],
        card_statuses=[CO, CO, CO, PA, CO, CO, EM, PA, CO],
        signup_days_ago=90,
        chat=[
            ("principal", "Boa tarde! Ficamos com uma dúvida sobre o prazo de conclusão da auditoria deste trimestre.", 6, True),
            ("admin", "Boa tarde, Marina! O prazo é até o fim do mês. Qualquer pendência, nos avise por aqui.", 6, True),
            ("principal", "Perfeito, obrigado! Já revisamos quase todos os controles com o time.", 2, False),
        ],
    ),
    DemoCompany(
        name="Construtora Horizonte S.A.",
        phone="(21) 98765-4321",
        principal_name="Eduardo Lima Souza",
        principal_email="eduardo.souza@horizonteconstrutora.com.br",
        sub_users=[
            ("Patrícia Gomes Almeida", "patricia.almeida@horizonteconstrutora.com.br"),
            ("Rodrigo Farias Teixeira", "rodrigo.teixeira@horizonteconstrutora.com.br"),
        ],
        card_statuses=[EM, EM, PA, NA, EM, EM, EM, NA, PA],
        signup_days_ago=10,
        chat=[
            ("principal", "Olá, esta é nossa primeira auditoria na plataforma. Por onde começamos?", 4, True),
            ("admin", "Olá, Eduardo! Comecem revisando os cards marcados como 'Em Análise' no dashboard e anexando as evidências pedidas em cada um.", 4, True),
            ("principal", "Combinado, vamos priorizar os itens não conformes essa semana.", 1, False),
        ],
    ),
    DemoCompany(
        name="GreenAgro Agronegócios Ltda",
        phone="(62) 99876-1234",
        principal_name="Camila Rezende Alves",
        principal_email="camila.alves@greenagro.com.br",
        sub_users=[
            ("Thiago Batista Nunes", "thiago.nunes@greenagro.com.br"),
            ("Larissa Pinto Cardoso", "larissa.cardoso@greenagro.com.br"),
        ],
        card_statuses=[CO, PA, EM, NA, PA, CO, EM, PA, NA],
        signup_days_ago=45,
        chat=[
            ("principal", "Conseguem revisar os anexos que subimos ontem no controle de nuvem?", 5, True),
            ("admin", "Já revisamos — falta só o registro de aprovação formal do fornecedor de nuvem.", 5, True),
        ],
    ),
    DemoCompany(
        name="Vitalis Saúde e Diagnósticos Ltda",
        phone="(31) 97654-3210",
        principal_name="Rafael Nogueira Costa",
        principal_email="rafael.costa@vitalissaude.com.br",
        sub_users=[
            ("Beatriz Andrade Melo", "beatriz.melo@vitalissaude.com.br"),
            ("Gustavo Ramos Barbosa", "gustavo.barbosa@vitalissaude.com.br"),
        ],
        card_statuses=[NA, PA, CO, NA, PA, EM, CO, PA, NA],
        signup_days_ago=60,
        chat=[
            ("principal", "Estamos preocupados com os itens não conformes — envolvem dados sensíveis de pacientes.", 3, True),
            ("admin", "Entendido, Rafael. Priorizem criptografia e segregação de funções — são os de maior risco para dados de saúde.", 3, True),
            ("principal", "Vamos montar um plano de ação essa semana e retornar com evidências.", 1, False),
        ],
    ),
    DemoCompany(
        name="Nortex Logística e Transportes S.A.",
        phone="(51) 98123-4567",
        principal_name="Juliana Martins Pires",
        principal_email="juliana.pires@nortexlog.com.br",
        sub_users=[
            ("Marcelo Vieira Correia", "marcelo.correia@nortexlog.com.br"),
            ("Aline Souza Barros", "aline.barros@nortexlog.com.br"),
        ],
        card_statuses=[PA, PA, EM, CO, PA, NA, EM, PA, PA],
        signup_days_ago=30,
        chat=[
            ("principal", "Bom dia! Alguma atualização sobre o item de segurança física?", 7, True),
            ("admin", "Bom dia, Juliana! Ainda não recebemos o registro de monitoramento do galpão principal.", 7, True),
        ],
    ),
]


def get_or_create_template(db: Session) -> DashboardTemplate:
    existing = db.scalar(
        select(DashboardTemplate).where(DashboardTemplate.name == DEMO_TEMPLATE_NAME)
    )
    if existing:
        return existing

    template = DashboardTemplate(
        name=DEMO_TEMPLATE_NAME,
        description=(
            "Controles essenciais estilo ISO/IEC 27001:2022 (Organizacional, "
            "Pessoas, Físico, Tecnológico) usados para popular dashboards de "
            "demonstração com um fluxo real."
        ),
        is_default=False,
    )
    db.add(template)
    db.flush()

    for order, (_code, title, tag) in enumerate(DEMO_CONTROLS):
        db.add(
            DashboardTemplateCard(
                template_id=template.id,
                title=title,
                tag=tag,
                sort_order=order,
            )
        )
    db.flush()
    return template


def create_demo_user(
    db: Session, *, full_name: str, email: str, role: str, parent_user_id: int | None, created_at: datetime
) -> User:
    user = create_user(
        db,
        full_name=full_name,
        email=email,
        password=DEMO_PASSWORD,
        role=role,
        parent_user_id=parent_user_id,
    )
    user.created_at = created_at
    db.flush()
    return user


def build_company(db: Session, admin: User, template: DashboardTemplate, demo: DemoCompany) -> None:
    if get_user_by_email(db, demo.principal_email):
        print(f"  já existe, pulando: {demo.name} ({demo.principal_email})")
        return

    signup_at = _at(demo.signup_days_ago, hour=9)

    principal = create_demo_user(
        db,
        full_name=demo.principal_name,
        email=demo.principal_email,
        role="user",
        parent_user_id=None,
        created_at=signup_at,
    )

    company, dashboard, _cards_created = create_company_dashboard_from_template(
        db,
        principal_user=principal,
        company_name=demo.name,
        company_email=demo.principal_email,
        company_phone=demo.phone,
        template=template,
    )
    company.created_at = signup_at
    dashboard.created_at = signup_at

    sub_users: list[User] = []
    for offset, (sub_name, sub_email) in enumerate(demo.sub_users, start=1):
        sub_user = create_demo_user(
            db,
            full_name=sub_name,
            email=sub_email,
            role="sub-user",
            parent_user_id=principal.id,
            created_at=signup_at + timedelta(days=offset),
        )
        sub_users.append(sub_user)

    cards = list(
        db.scalars(
            select(DashboardCard)
            .where(DashboardCard.dashboard_id == dashboard.id)
            .order_by(DashboardCard.sort_order.asc())
        ).all()
    )

    asker = sub_users[0] if sub_users else principal

    # Card escolhido para receber a troca de mensagens (Q&A) de demonstração:
    # o primeiro NAOCONFORME, senão o primeiro PARCIAL, senão nenhum.
    qa_card_index: int | None = None
    for status_to_find in (NA, PA):
        if status_to_find in demo.card_statuses:
            qa_card_index = demo.card_statuses.index(status_to_find)
            break

    for index, (card, status) in enumerate(zip(cards, demo.card_statuses)):
        code, _title, _tag = DEMO_CONTROLS[index]
        card.control_code = code
        card.status = status

        if status == EM:
            continue

        review_at = signup_at + timedelta(days=2 + index)

        db.add(
            DashboardCardNote(
                card_id=card.id,
                content=NOTE_TEXT[status],
                created_by_user_id=admin.id,
                created_at=review_at,
            )
        )
        db.add(
            DashboardCardHistoryEntry(
                card_id=card.id,
                action=f"Status alterado para {status.value}",
                actor_user_id=admin.id,
                created_at=review_at,
            )
        )

        done_a, done_b = CHECKLIST_DONE[status]
        db.add(
            DashboardCardchecklistItem(
                card_id=card.id,
                title="Evidência documental apresentada",
                done=done_a,
                created_at=review_at,
            )
        )
        db.add(
            DashboardCardchecklistItem(
                card_id=card.id,
                title="Evidência validada pelo time técnico",
                done=done_b,
                created_at=review_at,
            )
        )

        if index == qa_card_index:
            db.add(
                DashboardCardMessage(
                    card_id=card.id,
                    author_user_id=asker.id,
                    message_type=DashboardMessageType.QUESTION,
                    content=(
                        f"Quais evidências específicas estão faltando para "
                        f"regularizarmos o controle '{card.title}'?"
                    ),
                    created_at=review_at + timedelta(hours=2),
                )
            )
            db.add(
                DashboardCardMessage(
                    card_id=card.id,
                    author_user_id=admin.id,
                    message_type=DashboardMessageType.ANSWER,
                    content=(
                        "Precisamos do documento formalizado e assinado, além do "
                        "registro de comunicação aos colaboradores. Favor anexar "
                        "até o fim do ciclo de auditoria."
                    ),
                    created_at=review_at + timedelta(hours=5),
                )
            )

    for author, content, days_ago, read in demo.chat:
        author_user = admin if author == "admin" else principal
        created_at = _at(days_ago, hour=14)
        db.add(
            CompanyMessage(
                company_id=company.id,
                author_user_id=author_user.id,
                content=content,
                created_at=created_at,
                read_at=created_at + timedelta(hours=3) if read else None,
            )
        )

    db.flush()
    print(f"  criada: {demo.name} (empresa id={company.id}, principal={principal.email}, "
          f"{len(sub_users)} sub-usuários, {len(cards)} cards)")


def main() -> None:
    with SessionLocal() as db:
        try:
            admin = db.scalar(select(User).where(User.role == "admin"))
            if admin is None:
                raise RuntimeError(
                    "Nenhum usuário admin encontrado — rode scripts/seed_admin.py primeiro."
                )

            template = get_or_create_template(db)
            print(f"Template de demonstração: {template.name} (id={template.id})")

            for demo in DEMO_COMPANIES:
                build_company(db, admin, template, demo)

            db.commit()
            print("\nSeed de demonstração concluído.")
            print(f"Senha de login para todos os usuários criados: {DEMO_PASSWORD}")
        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main()
