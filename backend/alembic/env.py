from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Ensure project root is on sys.path so `import app...` works
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# Import Base + models so metadata is populated
from app.db.base import Base  # noqa: E402
from app.core.config import settings  # noqa: E402

# Import modules (not app.models.* wildcard) to avoid relying on __init__.py exports.
import app.models.audit  # noqa: E402,F401
import app.models.audit_control  # noqa: E402,F401
import app.models.control_catalog  # noqa: E402,F401
import app.models.evidence  # noqa: E402,F401
import app.models.message  # noqa: E402,F401
import app.models.user  # noqa: E402,F401
import app.models.dashboard_board  # noqa: E402,F401
import app.models.company_dashboard  # noqa: E402, F401
import app.models.sub_user_request  # noqa: E402, F401
import app.models.company_message  # noqa: E402, F401

target_metadata = Base.metadata


def get_url() -> str:
    # Prefer application settings (loads from .env)
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(
        get_url(),
        poolclass=pool.NullPool,
        pool_pre_ping=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
