from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - registra todos os models em Base.metadata
from app.core.jwt import create_access_token
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.audit import Audit, AuditStatus
from app.models.audit_control import AuditControl, AuditControlStatus
from app.models.company_dashboard import Company, Dashboard, DashboardCard
from app.models.control_catalog import ControlCatalog
from app.models.dashboard_board import (
    DashboardColumn,
    DashboardColumnKind,
    DashboardLabel,
)
from app.models.user import User
from app.services.fractional_index import n_keys_between

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    """
    Zera os contadores do slowapi entre testes.

    O rate limit de `/auth/login` (5/min por IP) é global ao processo e
    todos os testes chegam do mesmo "IP". Sem este reset, um teste que
    faça login passa isolado e falha na suíte completa, com 429 no lugar
    do status esperado — uma falha que depende da ORDEM de execução e
    aponta para o lugar errado.

    As duas instâncias de `Limiter` são resetadas porque são objetos
    distintos: `app.main.limiter` (registrada em `app.state`) e
    `app.api.v1.auth.limiter` (a que os decoradores de /login e /refresh
    de fato usam).
    """
    from app.api.v1 import auth as auth_module
    from app import main as main_module

    for limiter in (main_module.limiter, auth_module.limiter):
        try:
            limiter.reset()
        except Exception:  # pragma: no cover - backend de storage sem reset
            pass
    yield


@pytest.fixture(autouse=True)
def _isolate_uploads(tmp_path, monkeypatch):
    """Evita que os testes gravem arquivos reais em backend/uploads/."""
    from app.services import storage

    test_upload_dir = tmp_path / "uploads"
    test_upload_dir.mkdir()
    monkeypatch.setattr(storage, "UPLOAD_DIR", test_upload_dir)


@pytest.fixture
def db():
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db) -> User:
    admin = User(
        full_name="Admin Teste",
        email="admin@test.com",
        password_hash=hash_password("Admin123!"),
        role="admin",
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def admin_token(admin_user: User) -> str:
    return create_access_token(subject=str(admin_user.id), role="admin")


@pytest.fixture
def principal_user(db) -> User:
    user = User(
        full_name="Cliente Teste",
        email="cliente@test.com",
        password_hash=hash_password("Cliente123!"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_token(principal_user: User) -> str:
    return create_access_token(subject=str(principal_user.id), role="user")


@pytest.fixture
def sub_user(db, principal_user: User) -> User:
    sub = User(
        full_name="Sub-usuário Teste",
        email="subusuario@test.com",
        password_hash=hash_password("SubUser123!"),
        role="sub-user",
        parent_user_id=principal_user.id,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@pytest.fixture
def sub_user_token(sub_user: User) -> str:
    return create_access_token(subject=str(sub_user.id), role="sub-user")


@pytest.fixture
def catalog_control(db) -> ControlCatalog:
    control = ControlCatalog(
        code="5.1",
        title="Política de Segurança da Informação",
        description="Política deve ser definida, aprovada, comunicada e revisada.",
        expected_evidence="Política assinada",
    )
    db.add(control)
    db.commit()
    db.refresh(control)
    return control


@pytest.fixture
def company(db, principal_user: User) -> Company:
    company_obj = Company(
        name="Empresa Teste",
        email="empresa@test.com",
        phone="11999999999",
        principal_user_id=principal_user.id,
    )
    db.add(company_obj)
    db.commit()
    db.refresh(company_obj)
    return company_obj


@pytest.fixture
def dashboard(db, company: Company) -> Dashboard:
    dashboard_obj = Dashboard(
        company_id=company.id, title=f"Dashboard - {company.name}"
    )
    db.add(dashboard_obj)
    db.commit()
    db.refresh(dashboard_obj)
    return dashboard_obj


@pytest.fixture
def dashboard_column(db, dashboard: Dashboard) -> DashboardColumn:
    """Uma coluna comum (`kind=COLUMN`) no quadro da empresa de teste."""
    coluna = DashboardColumn(
        dashboard_id=dashboard.id,
        name="Controles Organizacionais",
        kind=DashboardColumnKind.COLUMN,
        position="a0",
    )
    db.add(coluna)
    db.commit()
    db.refresh(coluna)
    return coluna


@pytest.fixture
def board_com_3_colunas(db, dashboard: Dashboard) -> list[DashboardColumn]:
    """
    Quadro de três colunas, a do meio sendo uma `SECTION`.

    A seção no meio (e não na ponta) é deliberada: é a disposição do
    quadro real (`ISO 27001:2022 >>` separa blocos normativos) e é a que
    quebra código que assume "toda coluna aceita card".
    """
    posicoes = n_keys_between(None, None, 3)
    colunas = [
        DashboardColumn(
            dashboard_id=dashboard.id,
            name="A fazer",
            kind=DashboardColumnKind.COLUMN,
            position=posicoes[0],
        ),
        DashboardColumn(
            dashboard_id=dashboard.id,
            name="ISO 27001:2022 >>",
            kind=DashboardColumnKind.SECTION,
            position=posicoes[1],
        ),
        DashboardColumn(
            dashboard_id=dashboard.id,
            name="Concluído",
            kind=DashboardColumnKind.COLUMN,
            position=posicoes[2],
        ),
    ]
    db.add_all(colunas)
    db.commit()
    for coluna in colunas:
        db.refresh(coluna)
    return colunas


@pytest.fixture
def etiquetas(db) -> list[DashboardLabel]:
    """Subconjunto do vocabulário semeado pela migration c8f1a3e57b90."""
    labels = [
        DashboardLabel(name="Item Critico", color="#96311D", sort_order=0),
        DashboardLabel(name="Alta Criticidade", color="#C2410C", sort_order=1),
        DashboardLabel(name="Baixa Criticidade", color="#2C5A8C", sort_order=3),
    ]
    db.add_all(labels)
    db.commit()
    for label in labels:
        db.refresh(label)
    return labels


@pytest.fixture
def dashboard_card(
    db, dashboard: Dashboard, dashboard_column: DashboardColumn
) -> DashboardCard:
    card = DashboardCard(
        dashboard_id=dashboard.id,
        control_code="5.1",
        title="Política de Segurança da Informação",
        tag="governanca",
        column_id=dashboard_column.id,
        position="a0",
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


@pytest.fixture
def audit_with_control(db, principal_user: User, catalog_control: ControlCatalog):
    audit = Audit(
        name="Auditoria Teste",
        client_user_id=principal_user.id,
        status=AuditStatus.ACTIVE,
    )
    db.add(audit)
    db.flush()

    audit_control = AuditControl(
        audit_id=audit.id,
        control_id=catalog_control.id,
        status=AuditControlStatus.EM_ANALISE,
    )
    db.add(audit_control)
    db.commit()
    db.refresh(audit_control)
    return audit, audit_control
