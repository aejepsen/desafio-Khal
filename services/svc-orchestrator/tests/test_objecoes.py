"""Testes do tratamento de objeção — não desistir no primeiro não."""
from orch_svc.objecoes import AcaoObjecao, detectar_objecao, proxima_acao


def test_detecta_preco():
    assert detectar_objecao("achei muito caro, tem desconto?") == "preco"


def test_detecta_concorrente():
    assert detectar_objecao("cotei na Porto e tá mais barato") == "concorrente"


def test_detecta_indeciso_pausa():
    assert detectar_objecao("vou pensar. depois te falo") == "indeciso"
    assert detectar_objecao("depois te aviso") == "indeciso"
    # "depois" solto / pergunta genérica não devem virar pausa
    assert detectar_objecao("e depois do pagamento?") is None


def test_sem_objecao():
    assert detectar_objecao("quero seguro pro meu corolla 2020") is None


def test_nao_desiste_no_primeiro_nao():
    # 1ª e 2ª tentativas -> reverter (com táticas diferentes), não escalar
    r0 = proxima_acao("preco", 0)
    r1 = proxima_acao("preco", 1)
    assert r0.acao is AcaoObjecao.REVERTER and r1.acao is AcaoObjecao.REVERTER
    assert r0.tatica != r1.tatica and r0.tentativa == 1 and r1.tentativa == 2
    assert r0.framework and r1.framework  # tática rastreável ao método de vendas


def test_escala_apos_esgotar():
    # preco tem 3 táticas; na 3ª tentativa esgota -> escalar
    r = proxima_acao("preco", 3)
    assert r.acao is AcaoObjecao.ESCALAR and "persistiu" in r.motivo


def test_escala_quando_sem_taticas():
    r = proxima_acao("desconhecida", 0)
    assert r.acao is AcaoObjecao.ESCALAR
