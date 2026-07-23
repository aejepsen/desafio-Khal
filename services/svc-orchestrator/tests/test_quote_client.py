"""Testes do cliente resiliente do /quote — os desfechos que o desafio avalia."""
import httpx
import pytest

from orch_svc.circuit import CircuitBreaker
from orch_svc.quote_client import QuoteStatus, ResilientQuoteClient


class FakeResp:
    def __init__(self, status, payload=None, text=""):
        self.status_code = status
        self._p = payload or {}
        self.text = text or str(payload or "")

    def json(self):
        return self._p


def _seq(responses):
    it = iter(responses)

    def _post(url, json=None, timeout=None):
        r = next(it)
        if isinstance(r, Exception):
            raise r
        return r

    return _post


def _client(**kw):
    return ResilientQuoteClient(base_url="http://q", backoff_base_s=0.0,
                                _sleep=lambda s: None, **kw)


def test_quoted(monkeypatch):
    monkeypatch.setattr("httpx.post", _seq([FakeResp(200, {"premio_mensal": 100})]))
    o = _client().quote({"idade": 30, "veiculo_ano": 2020})
    assert o.status is QuoteStatus.QUOTED
    assert o.quote["premio_mensal"] == 100 and o.attempts == 1 and not o.escalate


def test_refused_nao_reintenta(monkeypatch):
    calls = []

    def post(url, json=None, timeout=None):
        calls.append(1)
        return FakeResp(422, {"motivo": "Idade fora das faixas aceitas."})

    monkeypatch.setattr("httpx.post", post)
    o = _client(max_retries=3).quote({})
    assert o.status is QuoteStatus.REFUSED and "Idade" in o.reason and len(calls) == 1


def test_invalid_400(monkeypatch):
    monkeypatch.setattr("httpx.post", _seq([FakeResp(400, {"detalhe": "falta veiculo_ano"})]))
    o = _client().quote({})
    assert o.status is QuoteStatus.INVALID and "veiculo_ano" in o.reason


def test_retry_depois_sucesso(monkeypatch):
    monkeypatch.setattr("httpx.post",
                        _seq([FakeResp(503), FakeResp(500), FakeResp(200, {"premio_mensal": 9})]))
    o = _client(max_retries=3).quote({})
    assert o.status is QuoteStatus.QUOTED and o.attempts == 3


def test_timeout_reintenta(monkeypatch):
    monkeypatch.setattr("httpx.post", _seq([httpx.ConnectTimeout("t"), FakeResp(200, {"ok": 1})]))
    o = _client(max_retries=2).quote({})
    assert o.status is QuoteStatus.QUOTED


def test_esgota_escala_humano(monkeypatch):
    monkeypatch.setattr("httpx.post", _seq([FakeResp(500), FakeResp(502), FakeResp(503)]))
    o = _client(max_retries=3).quote({})
    assert o.status is QuoteStatus.UNAVAILABLE and o.escalate is True


def test_circuito_aberto_escala_imediato(monkeypatch):
    br = CircuitBreaker(3, 30.0)
    monkeypatch.setattr("httpx.post", _seq([FakeResp(500)] * 3))
    c = _client(max_retries=3, breaker=br)
    c.quote({})                              # 3 falhas -> abre circuito
    o = c.quote({})                          # circuito OPEN -> não bate no downstream
    assert o.status is QuoteStatus.UNAVAILABLE and o.escalate and "OPEN" in o.reason
