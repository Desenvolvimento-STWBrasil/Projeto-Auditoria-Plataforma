#!/bin/sh
set -e

echo "Aplicando migrations (alembic upgrade head)..."
alembic upgrade head

echo "Garantindo usuário admin (idempotente)..."
python -m scripts.seed_admin || true

exec "$@"
