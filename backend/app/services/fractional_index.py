from __future__ import annotations

BASE_62_DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

#: Chave da primeira inserção numa lista vazia.
INITIAL_KEY = "a0"

#: Tamanho da coluna `position` (`String(64)`) — ver a docstring do módulo.
MAX_KEY_LENGTH = 64

#: Menor parte inteira representável; nenhuma chave válida é igual a ela,
#: porque não haveria como gerar nada antes.
SMALLEST_INTEGER = "A" + BASE_62_DIGITS[0] * 26


def _integer_length(head: str) -> int:
    """Comprimento total da parte inteira, deduzido do primeiro caractere."""
    if "a" <= head <= "z":
        return ord(head) - ord("a") + 2
    if "A" <= head <= "Z":
        return ord("Z") - ord(head) + 2
    raise ValueError(f"Cabeça de chave inválida: {head!r}")


def _validate_integer(value: str) -> None:
    if len(value) != _integer_length(value[0]):
        raise ValueError(f"Parte inteira inválida: {value!r}")


def _integer_part(key: str) -> str:
    if not key:
        raise ValueError("Chave de ordenação vazia")
    length = _integer_length(key[0])
    if length > len(key):
        raise ValueError(f"Chave de ordenação inválida: {key!r}")
    return key[:length]


def _validate_key(key: str) -> None:
    """
    Uma chave é válida quando: não é o menor inteiro possível; tem parte
    inteira completa; e a parte fracionária não termina em '0'.

    A regra do '0' final não é estética. Se a fração pudesse terminar em
    '0', existiriam duas grafias para o mesmo ponto ("a0V" e "a0V0") e o
    cálculo do ponto médio deixaria de ser fechado.
    """
    if key == SMALLEST_INTEGER:
        raise ValueError(f"Chave de ordenação inválida: {key!r}")
    integer = _integer_part(key)
    fraction = key[len(integer) :]
    if fraction.endswith(BASE_62_DIGITS[0]):
        raise ValueError(
            f"Chave de ordenação inválida (fração termina em '0'): {key!r}"
        )


def _increment_integer(value: str) -> str | None:
    """Próxima parte inteira, ou `None` se o espaço acabou (`z…`)."""
    _validate_integer(value)
    head, digits = value[0], list(value[1:])

    carry = True
    for i in range(len(digits) - 1, -1, -1):
        if not carry:
            break
        position = BASE_62_DIGITS.index(digits[i]) + 1
        if position == len(BASE_62_DIGITS):
            digits[i] = BASE_62_DIGITS[0]
        else:
            digits[i] = BASE_62_DIGITS[position]
            carry = False

    if not carry:
        return head + "".join(digits)

    if head == "Z":
        return "a" + BASE_62_DIGITS[0]
    if head == "z":
        return None

    next_head = chr(ord(head) + 1)
    if next_head > "a":
        digits.append(BASE_62_DIGITS[0])
    else:
        digits.pop()
    return next_head + "".join(digits)


def _decrement_integer(value: str) -> str | None:
    """Parte inteira anterior, ou `None` se o espaço acabou (`A…`)."""
    _validate_integer(value)
    head, digits = value[0], list(value[1:])

    borrow = True
    for i in range(len(digits) - 1, -1, -1):
        if not borrow:
            break
        position = BASE_62_DIGITS.index(digits[i]) - 1
        if position == -1:
            digits[i] = BASE_62_DIGITS[-1]
        else:
            digits[i] = BASE_62_DIGITS[position]
            borrow = False

    if not borrow:
        return head + "".join(digits)

    if head == "a":
        return "Z" + BASE_62_DIGITS[-1]
    if head == "A":
        return None

    previous_head = chr(ord(head) - 1)
    if previous_head < "Z":
        digits.append(BASE_62_DIGITS[-1])
    else:
        digits.pop()
    return previous_head + "".join(digits)


def _midpoint(a: str, b: str | None) -> str:
    """
    Menor fração estritamente entre `a` e `b`, onde ambas são partes
    FRACIONÁRIAS (sem parte inteira). `b is None` significa "1,0".

    O laço de prefixo comum preenche `a` com '0' à direita — é o que
    permite comparar "" com "0V" corretamente (prefixo comum de 1
    caractere) em vez de devolver "0", que terminaria em zero e violaria
    a invariante de `_validate_key`.
    """
    if b is not None and a >= b:
        raise ValueError(f"{a!r} >= {b!r}")
    if a.endswith(BASE_62_DIGITS[0]) or (
        b is not None and b.endswith(BASE_62_DIGITS[0])
    ):
        raise ValueError("Fração não pode terminar em '0'")

    if b is not None:
        common = 0
        while (
            common < len(b)
            and (a[common] if common < len(a) else BASE_62_DIGITS[0]) == b[common]
        ):
            common += 1
        if common > 0:
            return b[:common] + _midpoint(a[common:], b[common:])

    digit_a = BASE_62_DIGITS.index(a[0]) if a else 0
    digit_b = BASE_62_DIGITS.index(b[0]) if b else len(BASE_62_DIGITS)

    if digit_b - digit_a > 1:
        return BASE_62_DIGITS[(digit_a + digit_b) // 2]

    if b is not None and len(b) > 1:
        return b[:1]

    return BASE_62_DIGITS[digit_a] + _midpoint(a[1:], None)


def key_between(prev: str | None, next: str | None) -> str:
    """
    Chave estritamente entre `prev` e `next`. `None` representa a ponta da
    lista (`prev=None` = início, `next=None` = fim).

    Levanta `ValueError` se `prev >= next` — âncoras fora de ordem são um
    erro do chamador, nunca um caso a tolerar em silêncio: tolerá-lo
    produziria uma chave que quebra a ordenação de todo o quadro.
    """
    if prev is not None:
        _validate_key(prev)
    if next is not None:
        _validate_key(next)
    if prev is not None and next is not None and prev >= next:
        raise ValueError(f"Âncoras fora de ordem: {prev!r} >= {next!r}")

    if prev is None:
        if next is None:
            return INITIAL_KEY
        integer_b = _integer_part(next)
        fraction_b = next[len(integer_b) :]
        if integer_b == SMALLEST_INTEGER:
            return integer_b + _midpoint("", fraction_b)
        if integer_b < next:
            return integer_b
        decremented = _decrement_integer(integer_b)
        if decremented is None:
            raise ValueError("Não há espaço de ordenação antes desta chave")
        return decremented

    if next is None:
        integer_a = _integer_part(prev)
        fraction_a = prev[len(integer_a) :]
        incremented = _increment_integer(integer_a)
        if incremented is None:
            return integer_a + _midpoint(fraction_a, None)
        return incremented

    integer_a = _integer_part(prev)
    fraction_a = prev[len(integer_a) :]
    integer_b = _integer_part(next)
    fraction_b = next[len(integer_b) :]

    if integer_a == integer_b:
        return integer_a + _midpoint(fraction_a, fraction_b)

    incremented = _increment_integer(integer_a)
    if incremented is None:
        raise ValueError("Não há espaço de ordenação depois desta chave")
    if incremented < next:
        return incremented
    return integer_a + _midpoint(fraction_a, None)


def n_keys_between(prev: str | None, next: str | None, n: int) -> list[str]:
    if n < 0:
        raise ValueError("n não pode ser negativo")
    if n == 0:
        return []
    if n == 1:
        return [key_between(prev, next)]

    if next is None:
        current = key_between(prev, None)
        keys = [current]
        for _ in range(n - 1):
            current = key_between(current, None)
            keys.append(current)
        return keys

    if prev is None:
        current = key_between(None, next)
        keys = [current]
        for _ in range(n - 1):
            current = key_between(None, current)
            keys.append(current)
        keys.reverse()
        return keys

    middle = n // 2
    pivot = key_between(prev, next)
    return [
        *n_keys_between(prev, pivot, middle),
        pivot,
        *n_keys_between(pivot, next, n - middle - 1),
    ]
