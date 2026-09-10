#!/bin/sh
set -e

echo "Aplicando migrations (alembic upgrade head)..."
python -m alembic upgrade head

echo "Garantindo usuário admin (idempotente)..."
python scripts/seed_admin.py || true

exec "$@"
