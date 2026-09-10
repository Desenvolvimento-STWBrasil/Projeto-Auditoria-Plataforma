from __future__ import annotations

import bcrypt

# bcrypt opera sobre no máximo 72 bytes. Até a versão 3.x a biblioteca
# truncava em silêncio; a partir da 4.0 levanta ValueError. Nenhum dos dois
# comportamentos é aceitável implicitamente (B-A27): truncar faz duas senhas
# distintas autenticarem a mesma conta; levantar produz HTTP 500 numa rota
# não autenticada. O limite passa a ser tratado aqui, explicitamente, e o
# código deixa de depender de qual versão está instalada.
MAX_PASSWORD_BYTES = 72


class PasswordTooLongError(ValueError):
    """Senha excede o limite físico do bcrypt (72 bytes em UTF-8).

    Levantada só por `hash_password` (caminho de CRIAÇÃO de senha), onde a
    resposta correta é recusar com 422 e explicar o limite ao usuário.
    `verify_password` NÃO a levanta — ver docstring lá.
    """


def _password_bytes(plain_password: str) -> bytes:
    """UTF-8 da senha. Atenção: o limite é em BYTES, não em caracteres —
    'ç' ocupa 2 bytes e um emoji ocupa 4, então uma senha de 40 caracteres
    pode ultrapassar 72 bytes."""
    return plain_password.encode("utf-8")


def hash_password(plain_password: str) -> str:
    """
    Recebe senha em texto puro e devolve hash seguro (bcrypt).
    Nunca salve a senha pura no banco.

    Levanta `PasswordTooLongError` se a senha ultrapassar 72 bytes — quem
    chama converte para 422. Recusar é a única opção correta aqui:
    truncar aceitaria a senha e depois autenticaria qualquer variante que
    compartilhasse os primeiros 72 bytes.
    """
    encoded = _password_bytes(plain_password)
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise PasswordTooLongError(
            f"Senha não pode ultrapassar {MAX_PASSWORD_BYTES} bytes "
            f"(recebida com {len(encoded)})"
        )
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """
    Compara a senha digitada com o hash salvo no banco.
    Retorna True se bater, False caso contrário.

    Uma senha acima de 72 bytes devolve `False`, não exceção: nenhum hash
    armazenado pode ter sido gerado a partir dela (hash_password recusa),
    então ela está necessariamente errada. Devolver False — em vez de 422
    ou 500 — também evita construir um oráculo que diferencie "senha longa
    demais" de "senha incorreta" para quem sonda o endpoint de login.

    O `except ValueError` final é defensivo contra hash corrompido/truncado
    no banco (`checkpw` levanta ValueError quando o salt é inválido); sem
    ele, um único registro ruim derruba o login com 500 em vez de negar.
    """
    encoded = _password_bytes(plain_password)
    if len(encoded) > MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))
    except ValueError:
        return False
