"""
Testa a conexão MySQL usando DATABASE_URL do backend/.env

Uso (pasta backend, venv ativado):
  python scripts/check_db.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text

from app.core.config import settings


def main() -> None:
    url = settings.DATABASE_URL
    # Não imprimir senha: só driver e destino após @
    if "@" in url:
        safe = url.split("@", 1)[1]
        print(f"Tentando conectar em: ...@{safe}")
    else:
        print("DATABASE_URL sem '@' — confira o formato no .env")

    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("OK — MySQL respondeu. Pode rodar o Alembic.")
    except OSError as e:
        print("Erro de rede / conexão recusada — servidor MySQL provavelmente não está escutando nessa porta.")
        print(f"Detalhe: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Falha na conexão: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
