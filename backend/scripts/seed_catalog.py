from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.control_catalog import ControlCatalog


# ================================================
# 1. Estrutura de dados do Seed
# ================================================
@dataclass(frozen=True)
class SeedControl:
    code: str
    title: str
    description: str
    expected_evidence: str | None


# ================================================
# 2. Dados iniciais (exemplo para começar)
# ================================================
SEED_CONTROLS: tuple[SeedControl, ...] = (
    SeedControl(
        code="5.1",
        title="Política de Segurança da Informação",
        description="Política deve ser definida, aprovada, comunicada e revisada",
        expected_evidence="Política assinada + evidência de comunicação interna + revisão periódica",
    ),
    SeedControl(
        code="5.2",
        title="Papéis e Responsabilidades",
        description="Responsabilidades de segurança definidas e atribuídas.",
        expected_evidence="Documento formal de papéis/responsabilidades + responsáveis nomeados.",
    ),
    SeedControl(
        code="5.3",
        title="Segregação de Funções",
        description="Separação de funções conflitantes para redução de risco.",
        expected_evidence="Matriz de segregação + evidência de revisão periódica.",
    ),
    # Controles abaixo seguem o mesmo tema ISO/IEC 27001:2022 Anexo A usado
    # no template de dashboard de demonstração (ver DEMO_CONTROLS em
    # scripts/seed_demo_companies.py) — mesmos códigos/títulos, para que
    # Dashboard e Auditorias contem a mesma história ao popular dados de
    # exemplo.
    SeedControl(
        code="5.7",
        title="Inteligência de Ameaças",
        description="Coleta, análise e uso de informações sobre ameaças à segurança da informação para subsidiar ações preventivas.",
        expected_evidence="Relatórios de inteligência de ameaças + registro de ações preventivas tomadas a partir deles.",
    ),
    SeedControl(
        code="5.23",
        title="Segurança da Informação no Uso de Serviços em Nuvem",
        description="Processos de aquisição, uso, gestão e encerramento de serviços em nuvem definidos considerando os requisitos de segurança da informação da organização.",
        expected_evidence="Política de uso de nuvem + contrato/SLA do provedor + registro de avaliação de risco do fornecedor.",
    ),
    SeedControl(
        code="6.3",
        title="Conscientização, Educação e Treinamento em Segurança da Informação",
        description="Colaboradores e partes interessadas relevantes devem receber conscientização, educação e treinamento apropriados em segurança da informação, com atualizações regulares.",
        expected_evidence="Registro de participação em treinamentos + material do treinamento + cronograma de reciclagem periódica.",
    ),
    SeedControl(
        code="7.4",
        title="Monitoramento de Segurança Física",
        description="Instalações devem ser continuamente monitoradas para detectar acesso físico não autorizado.",
        expected_evidence="Registros de CFTV/controle de acesso + relatório de incidentes de segurança física, quando houver.",
    ),
    SeedControl(
        code="8.8",
        title="Gestão de Vulnerabilidades Técnicas",
        description="Informação sobre vulnerabilidades técnicas dos sistemas em uso deve ser obtida, avaliada e tratada de forma tempestiva.",
        expected_evidence="Relatório de scan de vulnerabilidades + plano de correção com prazos + evidência de remediação.",
    ),
    SeedControl(
        code="8.24",
        title="Uso de Criptografia",
        description="Regras para uso efetivo de criptografia, incluindo gestão de chaves, devem ser definidas e implementadas.",
        expected_evidence="Política de criptografia + inventário de onde é aplicada + evidência de gestão de chaves.",
    ),
)


# ================================================
# 3. Funções auxiliares (idempotentes)
# ================================================
def get_or_create_control(session: Session, seed: SeedControl) -> ControlCatalog:
    """
    Buscar um controle pelo code.
    Se existir, retorna o existente.
    Se não existir, criar e retorna o novo
    """
    existing = session.scalar(
        select(ControlCatalog).where(ControlCatalog.code == seed.code)
    )
    if existing:
        # Opcional: atualizar campos caso o seed mude com o tempo
        existing.title = seed.title
        existing.description = seed.description
        existing.expected_evidence = seed.expected_evidence
        return existing

    control = ControlCatalog(
        code=seed.code,
        title=seed.title,
        description=seed.description,
        expected_evidence=seed.expected_evidence,
    )
    session.add(control)
    session.flush()
    return control


def seed_controls(session: Session, controls: Iterable[SeedControl]) -> None:
    for control_seed in controls:
        get_or_create_control(session, control_seed)


# ================================================
# 4. Função principal (main)
# ================================================
def main() -> None:
    with SessionLocal() as session:
        try:
            seed_controls(session, SEED_CONTROLS)
            session.commit()
            print("Seed concluido: catálogo de controles inserido/atualizado.")
        except Exception:
            session.rollback()
            raise


if __name__ == "__main__":
    main()
