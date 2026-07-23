"""Testes do re-rank (RAG + sinais Neo4j/plano/ganho)."""
from __future__ import annotations

from orch_svc.clients import FakeRag
from orch_svc.cotacao_flow import decidir_cotacao
from orch_svc.quote_client import QuoteOutcome, QuoteStatus
from orch_svc.rerank import Candidate, rerank


class _BR:
    missing: list = []
    errors: list = []
    refusals: list = []
    payload = {"idade": 35, "veiculo_ano": 2020, "cep": "01310100", "plano_id": "completo"}


class _Q:
    def quote(self, body, trace):
        return QuoteOutcome(QuoteStatus.QUOTED, quote={"premio_mensal": 199.9, "plano_id": "completo"})


def test_rerank_boost_ganho_e_plano():
    cands = [
        Candidate("outcome=perdido sem plano", 0.9, "rag"),
        Candidate("outcome=ganho plano=completo fechado boleto apólice", 0.5, "neo4j"),
        Candidate("contexto generico", 0.8, "rag"),
    ]
    top = rerank(cands, query="quero completo", plano_id="completo", top_k=2)
    assert top[0].source == "neo4j"
    assert top[0].features.get("ganho") is True
    assert top[0].features.get("plano_match") == "completo"


def test_decidir_cotacao_rerank_com_graph():
    d = decidir_cotacao(
        _BR(),
        _Q(),
        query="quero o completo",
        rag=FakeRag(hits=5),
        plano_id="completo",
        graph_examples=[
            "outcome=ganho has_close=true plano=completo conversa=#99 — fechado boleto",
        ],
        trace="t-rerank",
    )
    assert d.acao == "apresentar_cotacao"
    assert len(d.exemplos) <= 3
    assert d.exemplos_meta
    assert any(m.get("source") == "neo4j" for m in d.exemplos_meta) or d.exemplos
