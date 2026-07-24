"""Testes do tratamento de objeção — não desistir no primeiro não."""
from orch_svc.objecoes import AcaoObjecao, detectar_objecao, pedido_humano, proxima_acao


def test_detecta_preco():
    assert detectar_objecao("achei muito caro, tem desconto?") == "preco"


def test_preco_pergunta_neutra_nao_e_objecao():
    # Pergunta sobre preço ANTES de qualquer cotação não é objeção — é falta de
    # dado; reclamação real ("caro", "desconto", "alto") continua sendo objeção.
    assert detectar_objecao("qual o preço do plano completo?") is None
    assert detectar_objecao("quero saber o preço do plano completo antes de decidir") is None
    assert detectar_objecao("dá pra parcelar?") is None
    assert detectar_objecao("achei muito caro") == "preco"
    assert detectar_objecao("tá caro demais") == "preco"
    assert detectar_objecao("tem desconto?") == "preco"


def test_detecta_concorrente():
    assert detectar_objecao("cotei na Porto e tá mais barato") == "concorrente"


def test_concorrente_exige_contexto_de_seguradora():
    # "azul"/"porto" soltos (cor do carro, endereço) não são objeção de concorrente.
    assert detectar_objecao("carro azul 2020") is None
    assert detectar_objecao("Fiat Uno azul 2020, cep 01310-100") is None
    assert detectar_objecao("moro perto do porto, cep 01310-100") is None
    # mas seguradora nomeada continua detectando.
    assert detectar_objecao("já cotei na Azul Seguros") == "concorrente"
    assert detectar_objecao("vi na Porto Seguro mais barato") == "concorrente"


def test_cobertura_terceiro_exige_termo_de_seguro():
    # "terceiro" incidental (fila, ordem) não é objeção de cobertura.
    assert detectar_objecao("sou o terceiro da fila, pode me atender?") is None
    # mas o termo de seguro ("a/contra terceiros") continua detectando.
    assert detectar_objecao("só cobre a terceiros?") == "cobertura"


def test_pedido_humano():
    assert pedido_humano("posso falar com o atendente humano?")
    assert pedido_humano("quero falar com um humano agora")
    assert pedido_humano("quero falar com uma pessoa de verdade")
    assert pedido_humano("me transfere pra um atendente")
    # consulta a terceiro (família) não é pedido de atendimento humano.
    assert not pedido_humano("vou falar com minha esposa e te aviso")
    assert not pedido_humano("quero seguro pro meu corolla 2020")


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
