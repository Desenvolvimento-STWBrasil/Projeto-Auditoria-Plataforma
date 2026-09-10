from __future__ import annotations

from pathlib import Path
from typing import Protocol


class StorageBackend(Protocol):
    """
    Contrato mínimo de armazenamento de evidência.

    `delete` é parte do contrato de propósito: a ausência dele em
    services/storage.py é a causa estrutural de B-A26 — arquivos
    confidenciais sobrevivendo à exclusão da empresa que os originou.
    Uma implementação nova (S3, Azure Blob) não se completa sem
    responder "como eu apago?".
    """

    async def save(self, content: bytes, original_filename: str) -> str:
        """Persiste o conteúdo e devolve a chave de recuperação"""
        ...

    def resolve(self, storage_key: str) -> Path:
        """Caminho físico (ou URL assinada) para leitura"""
        ...

    def delete(self, storage_key: str) -> bool:
        """Remove o objeto.True se removeu, False se já não existia"""
        ...

    def exists(self, storage_key: str) -> bool:
        """True se o objeto existe no backend"""
        ...
