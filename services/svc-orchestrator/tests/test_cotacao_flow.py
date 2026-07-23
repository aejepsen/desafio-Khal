"""Testes da decisão de cotação (porteiro + /quote + RAG + HITL)."""
from types import SimpleNamespace

from orch_svc.cotacao_flow import decidir_cotacao
from orch_svc.quote_client import QuoteOutcome, QuoteStatus


def _br(body=None, missing=None, errors=None, refusals=None):
    return SimpleNamespace(body=body, missing=missing or [], errors=errors or [],
                           refusals=refusals or [])


class FakeQuote:
    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = 0

    def quote(self, body, trace):
        self.calls += 1
        return self.outcome


class FakeRag:
    def search(self, query, domain, trace):
        return [SimpleNamespace(text="lead fechou corolla 2020"), SimpleNamespace(text="ok")]


def test_pedir_dado_nao_cota():
    fq = FakeQuote(None)
    d = decidir_cotacao(_br(missing=["idade"]), fq)
    assert d.acao == "pedir_dado" and "idade" in d.faltam and fq.calls == 0


def test_recusa_local_nao_cota():
    fq = FakeQuote(None)
    d = decidir_cotacao(_br(refusals=["idade_fora_range_contrato"]), fq)
    assert d.acao == "recusar" and fq.calls == 0


def test_apresenta_cotacao_com_fewshot():
    fq = FakeQuote(QuoteOutcome(QuoteStatus.QUOTED, quote={"premio_mensal": 120}))
    d = decidir_cotacao(_br(body={"idade": 30, "veiculo_ano": 2020}), fq,
                        query="corolla 2020", rag=FakeRag())
    assert d.acao == "apresentar_cotacao" and d.quote["premio_mensal"] == 120
    assert len(d.exemplos) == 2


def test_quote_refused_422():
    fq = FakeQuote(QuoteOutcome(QuoteStatus.REFUSED, reason="Idade fora das faixas"))
    d = decidir_cotacao(_br(body={}), fq)
    assert d.acao == "recusar" and "Idade" in d.motivos[0]


def test_quote_unavailable_escala_humano():
    fq = FakeQuote(QuoteOutcome(QuoteStatus.UNAVAILABLE, reason="esgotou", escalate=True))
    d = decidir_cotacao(_br(body={}), fq)
    assert d.acao == "escalar_humano" and d.escalate is True


def test_rag_falha_nao_bloqueia():
    class RagQuebrado:
        def search(self, *a):
            raise RuntimeError("rag down")

    fq = FakeQuote(QuoteOutcome(QuoteStatus.QUOTED, quote={"premio_mensal": 9}))
    d = decidir_cotacao(_br(body={"idade": 40, "veiculo_ano": 2015}), fq,
                        query="x", rag=RagQuebrado())
    assert d.acao == "apresentar_cotacao" and d.exemplos == []   # degradou gracioso
