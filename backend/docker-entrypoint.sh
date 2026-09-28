#!/bin/sh
set -e

echo "Aplicando migrations (alembic upgrade head)..."
alembic upgrade head

echo "Garantindo usuário admin (idempotente)..."
# Sem "|| true": se o seed falhar (ex.: ADMIN_PASSWORD vazio, banco
# inacessível), o container NÃO sobe e o erro aparece no log. Num banco
# novo, subir sem admin deixaria a plataforma sem ninguém para entrar.
# O seed já é idempotente: admin existente → só imprime e sai com 0.
python -m scripts.seed_admin

exec "$@"