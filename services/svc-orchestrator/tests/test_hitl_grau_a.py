"""HITL grau A — mensagem ao lead sem jargão de /quote."""
from __future__ import annotations

from orch_svc.cotacao_flow import DecisaoCotacao
from orch_svc.fechamento_index import lookup_fechamento, validar_fechamento_llm
from orch_svc.hitl_copy import (
    classificar_motivo_hitl,
    mensagem_hitl_lead,
    validar_hitl_lead,
)
from orch_svc.resposta import redigir_resposta


def test_classifica_quote_503():
    assert classificar_motivo_hitl(["esgotou 3 tentativas (última: 503)"]) == "quote_instavel"


def test_mensagem_lead_sem_jargao():
    msg = mensagem_hitl_lead(["esgotou 3 tentativas (última: 503)"])
    assert "503" not in msg
    assert "circuito" not in msg.lower()
    assert "invent" not in msg.lower()
    assert "atendente humano" in msg.lower()
    assert "instabilidade" in msg.lower()
    assert validar_hitl_lead(msg)


def test_rejeita_pitch_e_jargao():
    assert not validar_hitl_lead("503 no circuito — te ligo depois")
    assert not validar_hitl_lead("Plano Completo R$ 199,90/mês pra sua família")
    assert not validar_hitl_lead("Ideal para proteger sua família e patrimônio.")


def test_fechamento_escalar_quote_grau_a():
    d = DecisaoCotacao(
        "escalar_humano",
        escalate=True,
        motivos=["esgotou 3 tentativas (última: 503)"],
    )
    spec, texto, params = lookup_fechamento(d, idade=35)
    assert spec.key == "escalar_humano"
    assert "503" not in texto
    assert "atendente humano" in texto.lower()
    assert "instabilidade" in texto.lower() or "não consigo" in texto.lower()
    assert params.get("motivos_internos", "").find("503") >= 0


def test_redigir_escalar_ignora_llm_ruim():
    class Fake:
        def chat(self, messages, trace: str) -> str:
            return (
                "Vamos conversar sobre cobertura familiar e patrimonial. "
                "R$ 199,90/mês. Motivo: 503."
            )

    d = DecisaoCotacao(
        "escalar_humano",
        escalate=True,
        motivos=["circuito OPEN (quote-service instável)"],
    )
    red = redigir_resposta(d, idade=40, inference=Fake(), mensagem_lead="pode cotar")
    assert red.fonte == "template"
    assert "503" not in red.texto
    assert "199" not in red.texto
    assert "atendente humano" in red.texto.lower()
    assert validar_hitl_lead(red.texto)
