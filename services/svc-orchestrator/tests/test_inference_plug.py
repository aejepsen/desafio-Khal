"""Plug INFERENCE_URL: extração + redação via HttpInference (Fake / Demo path)."""
from __future__ import annotations

from orch_svc.clients import FakeInference
from orch_svc.cotacao_flow import DecisaoCotacao
from orch_svc.extracao import extrair_slots
from orch_svc.resposta import redigir_resposta


class _JsonInference:
    """Simula DemoBackend de extract."""

    def chat(self, messages, trace: str) -> str:
        return '{"idade": 41, "plano_id": "premium", "cep": "01310-100", "veiculo_ano": 2019}'


def test_extracao_com_inference_enriquece():
    """Campos do LLM só entram se ancorados literalmente no texto do lead."""
    texto = "tenho 41 anos, quero o premium pro meu carro 2019, cep 01310-100"
    s = extrair_slots(texto, _JsonInference())
    assert s["plano_id"] == "premium"
    assert s["idade"] == 41
    assert s["veiculo_ano"] == 2019
    assert "01310" in s["cep"]


def test_extracao_llm_nao_ancorado_e_descartado():
    """Anti-alucinação: LLM traz idade/veículo/cep sem evidência no texto -> descartado."""
    s = extrair_slots("quero o premium pro meu carro", _JsonInference())
    assert s["plano_id"] == "premium"  # "premium" está literalmente no texto
    assert "idade" not in s  # 41 anos não aparece no texto -> não confia
    assert "veiculo_ano" not in s  # 2019 não aparece no texto -> não confia
    assert "cep" not in s  # cep não aparece no texto -> não confia


def test_extracao_inference_falha_degrada():
    class Boom:
        def chat(self, messages, trace: str) -> str:
            raise RuntimeError("down")

    s = extrair_slots("tenho 30 anos carro 2021", Boom())
    assert s["idade"] == 30
    assert s["veiculo_ano"] == 2021


def test_resposta_com_inference():
    d = DecisaoCotacao(
        "apresentar_cotacao",
        quote={"premio_mensal": 137.88, "plano_nome": "Essencial", "franquia": 2000},
    )
    fake = FakeInference()
    msg = redigir_resposta(d, idade=35, mensagem_lead="cota ai", inference=fake, trace="t1")
    assert msg.texto  # FakeInference devolve texto; path não quebra
    assert msg.fonte in ("llm", "llm_fallback", "template")
    assert fake.calls == ["t1"]
