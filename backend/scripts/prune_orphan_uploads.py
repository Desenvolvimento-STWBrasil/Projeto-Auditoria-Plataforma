"""
Lista (e, com --apply, remove) arquivos em backend/uploads/ que não têm
registro correspondente em `evidences.storage_key` — órfãos deixados por
exclusões de empresa anteriores à correção de B-A26.

Uso:
    python -m scripts.prune_orphan_uploads           # só relata
    python -m scripts.prune_orphan_uploads --apply   # remove de fato
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.evidence import Evidence  # noqa: E402
from app.services.storage import UPLOAD_DIR  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="remove os arquivos órfãos (sem esta flag, apenas relata)",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        referenced = {
            Path(key).name for key in db.scalars(select(Evidence.storage_key)).all()
        }

    files = sorted(p for p in UPLOAD_DIR.iterdir() if p.is_file())
    orphans = [p for p in files if p.name not in referenced]

    print(f"arquivos em {UPLOAD_DIR}/: {len(files)}")
    print(f"registros em evidences:    {len(referenced)}")
    print(f"órfãos encontrados:        {len(orphans)}")

    total_bytes = 0
    for path in orphans:
        size = path.stat().st_size
        total_bytes += size
        marca = "REMOVIDO" if args.apply else "ÓRFÃO   "
        print(f"  {marca}  {path.name}  ({size} bytes)")
        if args.apply:
            path.unlink(missing_ok=True)

    print(f"total: {total_bytes} bytes ({total_bytes / 1_048_576:.2f} MB)")
    if not args.apply and orphans:
        print("\nNada foi removido. Rode com --apply para excluir de fato.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
