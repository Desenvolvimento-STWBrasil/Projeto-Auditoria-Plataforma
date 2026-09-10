from __future__ import annotations

import uuid
from pathlib import Path

import aiofiles
import structlog

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

logger = structlog.get_logger(__name__)


class StorageKeyOutsideUploadDirError(ValueError):
    """`storage_key` resolve para fora de uploads/ — recusado (B-M28)."""


async def save_file(content: bytes, original_filename: str) -> str:
    """Salve arquivo em disco e retorna o path relativo"""
    ext = Path(original_filename).suffix.lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / filename
    async with aiofiles.open(dest, "wb") as f:
        await f.write(content)
    return str(dest)


def _resolver_dentro_do_upload_dir(storage_key: str) -> Path:
    """
    Resolve `storage_key` e garante que o caminho final está dentro de
    UPLOAD_DIR.

    Ponto ÚNICO de verificação (B-M28). A guarda introduzida em P.2 vivia
    só dentro de `delete_files()`, então o download
    (`admin.py::download_evidence`) resolvia sem ela — mesma classe de
    assimetria que causou B-A26, onde o storage sabia gravar e ler mas não
    apagar. Uma barreira instalada no consumidor não acompanha a próxima
    implementação de storage; instalada aqui, acompanha.

    A chave é resolvida COMO ESTÁ e depois verificada — nunca reescrita.
    Descartar o diretório com `Path(storage_key).name` e re-enraizar em
    UPLOAD_DIR pareceria mais seguro e é pior: "/etc/passwd" viraria
    "uploads/passwd", a verificação passaria, e `delete_files` contaria
    como removido um arquivo que nunca existiu. Uma chave fora do lugar é
    um defeito de dado — o certo é recusá-la e registrar, não adivinhar o
    que ela queria dizer.
    """
    upload_root = UPLOAD_DIR.resolve()

    try:
        caminho = Path(storage_key).resolve()
        caminho.relative_to(upload_root)
    except (ValueError, OSError):
        raise StorageKeyOutsideUploadDirError(
            f"storage_key resolve para fora de uploads/: {storage_key!r}"
        )
    return caminho


def get_absolute_path(storage_key: str) -> Path:
    """Resolve o caminho físico de um arquivo já salvo, a partir do
    `storage_key` gravado em Evidence.storage_key por save_file(). Hoje
    storage_key já é o path relativo completo retornado por save_file()
    (ex.: "uploads/<uuid>.pdf").

    Ponto único de mudança se o backend de armazenamento evoluir para
    S3/Azure Blob (ver services/storage_backend.py), sem precisar alterar
    o endpoint de download (admin.py::download_evidence) que a consome.

    Levanta `StorageKeyOutsideUploadDirError` para qualquer chave que
    escape do diretório de uploads — quem chama converte para 404, nunca
    para 500 e nunca servindo o arquivo."""
    return _resolver_dentro_do_upload_dir(storage_key)


def delete_files(storage_keys: list[str]) -> int:
    """
     Apaga do disco os arquivos de `storage_keys` e devolve quantos foram
    de fato removidos (B-A26).

    Deve ser chamada SOMENTE depois de o commit da transação que apagou
    os registros correspondentes ter tido sucesso: apagar antes deixaria
    registro órfão apontando para arquivo inexistente em caso de rollback.

    Nunca levanta exceção — a transação de banco já está committada e não
    pode ser desfeita por causa de um arquivo. Cada falha vira log
    estruturado, para varredura posterior de órfãos
    (scripts/prune_orphan_uploads.py).
    """

    removed = 0

    for storage_key in storage_keys:
        try:
            path = get_absolute_path(storage_key)
        except StorageKeyOutsideUploadDirError:
            logger.warning(
                "evidence_file_delete_outside_upload_dir", storage_key=storage_key
            )
            continue

        try:
            path.unlink(missing_ok=True)
            removed += 1
        except OSError as exc:
            logger.warning(
                "evidence_file_delete_failed", storage_key=storage_key, error=str(exc)
            )
    return removed
