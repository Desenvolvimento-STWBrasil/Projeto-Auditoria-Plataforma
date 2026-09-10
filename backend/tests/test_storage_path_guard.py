"""
B-M28 / M-16b: a guarda de path traversal vale para TODOS os consumidores.

O BLOCO P (P.2) acrescentou a guarda correta — mas dentro de
`delete_files()`, não em `get_absolute_path()`, que é o ponto único por
onde toda resolução de caminho passa. O DOWNLOAD resolvia sem ela.

Não era explorável: `storage_key` só é gravado por `save_file()`, que gera
UUID. O problema é de projeto — quem portar o `StorageBackend` para S3 vai
portar `save`, `resolve`, `delete` e `exists`, e a guarda, por estar no
consumidor, não iria junto. É a mesma assimetria que causou B-A26, onde o
storage sabia gravar e ler mas não apagar.
"""

from __future__ import annotations

import pytest

from app.models.evidence import Evidence
from app.services import storage
from app.services.storage import (
    StorageKeyOutsideUploadDirError,
    delete_files,
    get_absolute_path,
)

# `UPLOAD_DIR` é lido do MÓDULO a cada chamada, nunca importado por valor:
# a fixture autouse `_isolate_uploads` (conftest.py) troca
# `storage.UPLOAD_DIR` por um tmp_path, e um import por valor congelaria o
# diretório real do repositório — o teste falharia contra código correto.

CHAVES_MALICIOSAS = [
    "../../../etc/passwd",
    "..\\..\\..\\Windows\\System32\\config\\SAM",
    "/etc/shadow",
    "uploads/../../segredo.env",
]


@pytest.mark.parametrize("chave", CHAVES_MALICIOSAS)
def test_get_absolute_path_recusa_ou_confina(chave):
    """
    Ou levanta, ou devolve um caminho dentro de uploads/ — nunca um
    caminho arbitrário do sistema de arquivos.
    """
    try:
        resolvido = get_absolute_path(chave)
    except StorageKeyOutsideUploadDirError:
        return

    # Não levantou: então o caminho TEM de estar confinado.
    resolvido.relative_to(storage.UPLOAD_DIR.resolve())


@pytest.mark.parametrize("chave", CHAVES_MALICIOSAS)
def test_delete_files_nunca_toca_fora_de_uploads(chave, tmp_path):
    alvo = tmp_path / "nao-me-apague.txt"
    alvo.write_text("conteudo importante", encoding="utf-8")

    delete_files([chave])

    assert alvo.exists(), "delete_files apagou um arquivo fora de uploads/"


def test_get_absolute_path_resolve_chave_legitima():
    """A guarda não pode quebrar o caminho normal.

    A chave é construída a partir de `storage.UPLOAD_DIR` — que é o que
    `save_file()` faz — e não escrita à mão como "uploads/x.pdf": sob a
    fixture `_isolate_uploads`, o diretório é um tmp_path, e uma chave
    literal apontaria para o repositório real.
    """
    chave = str(storage.UPLOAD_DIR / "abc123.pdf")

    resolvido = get_absolute_path(chave)

    assert resolvido.name == "abc123.pdf"
    resolvido.relative_to(storage.UPLOAD_DIR.resolve())


def test_get_absolute_path_nao_reenraiza_chave_de_fora(tmp_path):
    """
    Regressão encontrada ao aplicar Q.5: uma primeira versão desta guarda
    fazia `UPLOAD_DIR / Path(chave).name`, transformando "/etc/passwd" em
    "uploads/passwd". A verificação passava e `delete_files` reportava
    sucesso sobre um arquivo que nunca existiu. Recusar é o comportamento
    correto; adivinhar não é.
    """
    fora = tmp_path / "nao_deve_sumir.txt"
    fora.write_text("importante", encoding="utf-8")

    with pytest.raises(StorageKeyOutsideUploadDirError):
        get_absolute_path(str(fora))

    assert delete_files([str(fora)]) == 0
    assert fora.exists()


def test_download_de_evidencia_com_chave_invalida_da_404(
    client, db, admin_token, audit_with_control, principal_user, tmp_path
):
    """
    O consumidor que a guarda de P.2 não cobria. 404 — e não 500, nem o
    arquivo — para não revelar sequer a existência do caminho.

    O arquivo-alvo é criado de verdade, FORA de uploads/. Uma versão
    anterior deste teste usava "../../../etc/passwd", que não existe no
    Windows: o download devolvia 404 por o arquivo não existir, e o teste
    passava IDÊNTICO com e sem a guarda. Foi a verificação por reversão
    que expôs isso — a barreira estava medindo o sistema de arquivos, não
    a correção.
    """
    segredo = tmp_path / "segredo.env"
    segredo.write_text("JWT_SECRET=nao-devia-vazar", encoding="utf-8")
    assert segredo.exists()

    _, audit_control = audit_with_control
    evidencia = Evidence(
        audit_control_id=audit_control.id,
        uploaded_by_id=principal_user.id,
        file_name="segredo.env",
        storage_key=str(segredo),
        mime_type="text/plain",
        size_bytes=segredo.stat().st_size,
    )
    db.add(evidencia)
    db.commit()
    db.refresh(evidencia)

    resposta = client.get(
        f"/api/v1/admin/evidences/{evidencia.id}/download",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resposta.status_code == 404, (
        f"download com storage_key fora de uploads/ devolveu "
        f"{resposta.status_code} — ver B-M28"
    )
    assert "JWT_SECRET" not in resposta.text
    assert segredo.exists(), "o arquivo de fora não pode ser tocado"


def test_download_de_evidencia_legitima_continua_funcionando(
    client, db, admin_token, audit_with_control, principal_user
):
    """
    Contraprova de B-M28: a guarda não pode quebrar o caminho normal.

    Este é o teste que faltava. `get_absolute_path` foi reescrita, e uma
    guarda que recusa tudo passaria em todos os testes de negativa acima
    sem que ninguém notasse que o download parou de funcionar.
    """
    import asyncio

    from app.services.storage import save_file

    conteudo = b"%PDF-1.4 evidencia de teste"
    storage_key = asyncio.run(save_file(conteudo, "politica.pdf"))

    _, audit_control = audit_with_control
    evidencia = Evidence(
        audit_control_id=audit_control.id,
        uploaded_by_id=principal_user.id,
        file_name="politica.pdf",
        storage_key=storage_key,
        mime_type="application/pdf",
        size_bytes=len(conteudo),
    )
    db.add(evidencia)
    db.commit()
    db.refresh(evidencia)

    resposta = client.get(
        f"/api/v1/admin/evidences/{evidencia.id}/download",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resposta.status_code == 200
    assert resposta.content == conteudo
