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
    s = extrair_slots("quero o premium pro meu carro", _JsonInference())
    assert s["plano_id"] == "premium"
    assert s["idade"] == 41
    assert s["veiculo_ano"] == 2019
    assert "01310" in s["cep"]


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
