"""
M-18: garante que TODA migration é ao menos importável e que a cadeia tem
um único head.

Não substitui um `alembic upgrade` real contra MySQL (ver o job
`migrations` em ci.yml), mas pega a classe de erro que já escapou DUAS
vezes neste repositório: SyntaxError no arquivo (O.5) e nome do arquivo
divergindo do `revision` declarado (I.5).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_ROOT = Path(__file__).resolve().parents[1]
VERSIONS_DIR = BACKEND_ROOT / "alembic" / "versions"
MIGRATIONS = sorted(VERSIONS_DIR.glob("*.py"))


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # pega SyntaxError
    return module


def test_there_are_migrations():
    assert MIGRATIONS, "nenhuma migration encontrada em alembic/versions/"


@pytest.mark.parametrize("path", MIGRATIONS, ids=lambda p: p.stem)
def test_migration_module_is_importable(path: Path):
    module = _load(path)
    assert hasattr(module, "revision")
    assert hasattr(module, "down_revision")
    assert callable(getattr(module, "upgrade", None))
    assert callable(getattr(module, "downgrade", None))


@pytest.mark.parametrize("path", MIGRATIONS, ids=lambda p: p.stem)
def test_filename_matches_declared_revision(path: Path):
    """Incidente I.5 e sua reincidência em O.5: o nome do arquivo saindo
    de sincronia com `revision` deixa a cadeia inconsistente."""
    module = _load(path)
    assert path.stem.startswith(
        module.revision
    ), f"arquivo {path.name} declara revision={module.revision!r}"


def test_single_head():
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    assert len(heads) == 1, f"cadeia com múltiplos heads: {heads}"
