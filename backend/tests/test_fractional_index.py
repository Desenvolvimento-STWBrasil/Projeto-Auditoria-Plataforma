"""
CA-04: a ordenação do quadro inteiro repousa neste módulo.

O defeito que este arquivo previne é silencioso e tardio: uma chave gerada
FORA do intervalo pedido não quebra nada na hora — o card só aparece no
lugar errado na próxima leitura do quadro, depois do commit, sem erro
nenhum no log. Nenhum teste de rota pegaria isso, porque a rota devolveria
200.

Por isso o teste é de PROPRIEDADE, não de exemplo: para toda combinação de
âncoras (as duas presentes, só a da esquerda, só a da direita, nenhuma), a
chave devolvida tem de ser estritamente maior que a da esquerda e
estritamente menor que a da direita — em ordem lexicográfica de string,
que é a ordem que o `ORDER BY position` do banco vai usar.
"""

from __future__ import annotations

import random

import pytest

from app.services.fractional_index import (
    INITIAL_KEY,
    MAX_KEY_LENGTH,
    key_between,
    n_keys_between,
)


def test_lista_vazia_recebe_a_chave_inicial():
    assert key_between(None, None) == INITIAL_KEY


def test_chave_no_fim_e_maior_que_a_anterior():
    primeira = key_between(None, None)
    segunda = key_between(primeira, None)
    assert primeira < segunda


def test_chave_no_inicio_e_menor_que_a_seguinte():
    primeira = key_between(None, None)
    anterior = key_between(None, primeira)
    assert anterior < primeira


def test_chave_no_meio_fica_estritamente_entre_as_ancoras():
    a = key_between(None, None)
    b = key_between(a, None)
    meio = key_between(a, b)
    assert a < meio < b


@pytest.mark.parametrize("quantidade", [1, 2, 3, 10, 50])
def test_n_keys_between_devolve_n_chaves_ordenadas(quantidade: int):
    chaves = n_keys_between(None, None, quantidade)
    assert len(chaves) == quantidade
    assert chaves == sorted(chaves)
    assert len(set(chaves)) == quantidade


def test_n_keys_between_respeita_as_ancoras():
    a = key_between(None, None)
    b = key_between(a, None)
    chaves = n_keys_between(a, b, 7)
    assert all(a < chave < b for chave in chaves)
    assert chaves == sorted(chaves)


def test_n_keys_between_com_zero_devolve_lista_vazia():
    assert n_keys_between(None, None, 0) == []


def test_ancoras_fora_de_ordem_levantam_value_error():
    a = key_between(None, None)
    b = key_between(a, None)
    with pytest.raises(ValueError):
        key_between(b, a)


def test_ancoras_iguais_levantam_value_error():
    a = key_between(None, None)
    with pytest.raises(ValueError):
        key_between(a, a)


def test_chave_malformada_levanta_value_error():
    """Fração terminada em '0' não é chave válida — ver `_validate_key`."""
    with pytest.raises(ValueError):
        key_between("a0V0", None)


def test_mil_insercoes_consecutivas_no_mesmo_ponto_mantem_a_ordem():
    """
    CA-04, cláusula de ordem: 1 000 inserções consecutivas no MESMO ponto
    (sempre logo depois da mesma âncora) preservam a ordem lexicográfica
    estrita, **sem nenhum rebalanceamento** — nenhuma chave já existente
    é reescrita.
    """
    ancora = key_between(None, None)
    seguinte = key_between(ancora, None)

    lista = [ancora, seguinte]
    for _ in range(1000):
        nova = key_between(lista[0], lista[1])
        assert lista[0] < nova < lista[1]
        lista.insert(1, nova)

    assert lista == sorted(lista)
    assert len(set(lista)) == len(lista)


def test_mil_insercoes_no_fim_nao_estouram_o_tamanho_da_coluna():
    """
    O caso REAL de volume: 1 000 cards criados em sequência (é o que
    `apply_template_to_company` e o importador do Trello fazem). A parte
    inteira da chave absorve o crescimento e o comprimento fica em 3-4
    caracteres, muito abaixo de `String(64)`.
    """
    chaves: list[str] = []
    atual: str | None = None
    for _ in range(1000):
        atual = key_between(atual, None)
        chaves.append(atual)

    assert chaves == sorted(chaves)
    assert max(len(c) for c in chaves) <= MAX_KEY_LENGTH


def test_lote_de_mil_chaves_nao_estoura_o_tamanho_da_coluna():
    """
    O caminho de `apply_template_to_company` e do importador do Trello:
    `n_keys_between` divide o intervalo binariamente, então 1 000 chaves
    de uma vez cabem em 3 caracteres.
    """
    chaves = n_keys_between(None, None, 1000)
    assert chaves == sorted(chaves)
    assert max(len(c) for c in chaves) <= MAX_KEY_LENGTH


def test_mil_arrastos_para_posicoes_arbitrarias_nao_estouram_a_coluna():
    """
    O padrão de uso real do arrasto: 1 000 movimentos para posições
    variadas de uma lista que cresce. `random.seed` fixo para o teste ser
    determinístico — um teste de ordenação que muda de resultado a cada
    execução não é barreira, é ruído.
    """
    random.seed(20260827)
    lista = n_keys_between(None, None, 2)

    for _ in range(1000):
        indice = random.randrange(1, len(lista))
        nova = key_between(lista[indice - 1], lista[indice])
        assert lista[indice - 1] < nova < lista[indice]
        lista.insert(indice, nova)

    assert lista == sorted(lista)
    assert max(len(c) for c in lista) <= MAX_KEY_LENGTH


def test_o_pior_caso_cabe_em_64_caracteres():
    """
    Barreira do limite documentado no módulo: inserir SEMPRE no mesmo
    intervalo gasta ~1 caractere a cada 5 inserções, e `String(64)` cobre
    exatamente 310 dessas. Fixamos 300 como barreira, com margem.

    Se este teste falhar, a leitura é: o algoritmo continua correto, mas o
    tipo da coluna ficou apertado — a correção é alargar `position`, não
    trocar o índice fracionário.
    """
    ancora = key_between(None, None)
    atual = key_between(ancora, None)

    for _ in range(300):
        atual = key_between(ancora, atual)
        assert ancora < atual

    assert len(atual) <= MAX_KEY_LENGTH
