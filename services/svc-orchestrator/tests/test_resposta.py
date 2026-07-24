"""Testes da redação de resposta (template + LLM opcional)."""
from __future__ import annotations

from orch_svc.cotacao_flow import DecisaoCotacao
from orch_svc.resposta import redigir_resposta


class _FakeLlm:
    def __init__(self, text: str = "Mensagem polida.", fail: bool = False) -> None:
        self.text = text
        self.fail = fail
        self.calls = 0

    def chat(self, messages, trace: str) -> str:
        self.calls += 1
        if self.fail:
            raise RuntimeError("down")
        return self.text


def test_template_cotacao():
    d = DecisaoCotacao(
        "apresentar_cotacao",
        quote={"plano_nome": "Essencial", "premio_mensal": 137.88, "franquia": 4500},
    )
    red = redigir_resposta(d, idade=35)
    assert red.fonte == "template"
    assert "137.88" in red.texto
    assert "Essencial" in red.texto
    assert "compare" in red.texto.lower() or "compar" in red.texto.lower()
    assert "ajustar o plano agora" not in red.texto.lower()


def test_template_pedir_dado():
    d = DecisaoCotacao("pedir_dado", faltam=["plano_id"],
                      motivos=["Pra cotar seu seguro eu preciso de: o plano desejado."])
    red = redigir_resposta(d, idade=22)
    assert "plano" in red.texto.lower()


def test_template_objecao():
    d = DecisaoCotacao("reverter_objecao", motivos=["reancorar em valor"])
    red = redigir_resposta(d, idade=60, framework="feel-felt-found")
    assert "reancorar" in red.texto.lower() or "entendo" in red.texto.lower()


def test_llm_polido():
    fake = _FakeLlm(
        "Olá! Sua cotação ficou em R$ 137,88 no Essencial. "
        "Quer que eu detalhe as coberturas ou compare com Completo ou Premium?"
    )
    d = DecisaoCotacao(
        "apresentar_cotacao",
        quote={"plano_nome": "Essencial", "premio_mensal": 137.88, "franquia": 4500},
    )
    red = redigir_resposta(d, idade=28, inference=fake, mensagem_lead="pode cotar")
    assert fake.calls == 1
    assert red.fonte == "llm"
    assert "137" in red.texto
    assert "137.88" in red.rascunho
    assert red.index_key.startswith("apresentar_cotacao")


def test_llm_excecao_cai_no_fallback():
    """Ação normal (não-HITL): exceção no client de inference -> llm_fallback."""
    fake = _FakeLlm(fail=True)
    d = DecisaoCotacao(
        "apresentar_cotacao",
        quote={"plano_nome": "Essencial", "premio_mensal": 137.88, "franquia": 4500},
    )
    red = redigir_resposta(d, idade=40, inference=fake, mensagem_lead="pode cotar")
    assert fake.calls == 1
    assert red.fonte == "llm_fallback"
    assert "137.88" in red.texto


def test_escalar_humano_nunca_chama_llm():
    """HITL grau A: resposta é sempre template, LLM nem é acionado (mesmo se disponível)."""
    fake = _FakeLlm("Mensagem que não deveria ser usada.")
    d = DecisaoCotacao("escalar_humano", motivos=["quote indisponível"], escalate=True)
    red = redigir_resposta(d, idade=40, inference=fake)
    assert fake.calls == 0
    assert red.fonte == "template"
    assert "humano" in red.texto.lower()
