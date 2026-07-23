"""Testes da persona por idade (modula tom, não a decisão)."""
from orch_svc.persona import Faixa, diretriz_de_estilo, persona_por_idade


def test_faixas():
    assert persona_por_idade(22).faixa is Faixa.JOVEM
    assert persona_por_idade(40).faixa is Faixa.MEIA
    assert persona_por_idade(65).faixa is Faixa.SENIOR
    assert persona_por_idade(None).faixa is Faixa.DESCONHECIDA


def test_bordas():
    assert persona_por_idade(30).faixa is Faixa.JOVEM
    assert persona_por_idade(31).faixa is Faixa.MEIA
    assert persona_por_idade(50).faixa is Faixa.MEIA
    assert persona_por_idade(51).faixa is Faixa.SENIOR


def test_diretriz_injetavel():
    d = diretriz_de_estilo(70)
    assert "senior" in d and "formal" in d
