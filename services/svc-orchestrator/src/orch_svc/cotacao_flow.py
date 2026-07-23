"""Decisão de cotação: integra porteiro (domínio) + /quote resiliente + RAG + HITL.

Fluxo (b)+(c)+(d):
  build_result (porteiro seguro_auto valida slots e monta o body)
    -> missing   : pedir_dado        (dados insuficientes — não cota)
    -> refusals  : recusar           (regra local: fora de faixa de contrato)
    -> errors    : pedir_correcao    (cep/data/plano inválidos)
    -> body ok   : [RAG few-shot] -> quote_client.quote(body):
         QUOTED      -> apresentar_cotacao
         REFUSED     -> recusar          (422: regra de negócio do quote-service)
         INVALID     -> pedir_correcao   (400)
         UNAVAILABLE -> escalar_humano   (5xx/timeout esgotado — HITL, nunca inventa)

Critério HITL explícito: escala quando `escalar_humano` (quote-service indisponível)
ou quando `pedir_dado` persiste além do limite de tentativas (decidido no agente).
RAG é enriquecimento (few-shot dinâmico) — falha nele NÃO bloqueia a cotação.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from orch_svc.quote_client import QuoteOutcome, QuoteStatus

RAG_COLLECTION = "namastex_conversas"


class _BuildResult(Protocol):
    body: dict[str, Any] | None
    missing: list[str]
    errors: list[str]
    refusals: list[str]


class _QuoteClient(Protocol):
    def quote(self, body: dict[str, Any], trace: str) -> QuoteOutcome: ...


class _Rag(Protocol):
    def search(self, query: str, domain: str, trace: str) -> list[Any]: ...


@dataclass
class DecisaoCotacao:
    acao: str                                   # apresentar_cotacao | pedir_dado | recusar | pedir_correcao | escalar_humano
    quote: dict[str, Any] | None = None
    faltam: list[str] = field(default_factory=list)
    motivos: list[str] = field(default_factory=list)
    exemplos: list[str] = field(default_factory=list)   # few-shot do RAG
    escalate: bool = False


def _extrair_body(build_result: Any) -> dict[str, Any]:
    """BuildResult.payload -> dict do POST /quote (tolera nomes de método)."""
    payload = getattr(build_result, "payload", None) or getattr(build_result, "body", None)
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return payload
    for meth in ("to_body", "as_body", "as_dict", "model_dump", "dict"):
        fn = getattr(payload, meth, None)
        if callable(fn):
            return fn()
    return dict(getattr(payload, "__dict__", {}))


def decidir_cotacao(build_result: _BuildResult, quote_client: _QuoteClient, *,
                    query: str | None = None, rag: _Rag | None = None,
                    trace: str = "-") -> DecisaoCotacao:
    if build_result.missing:
        return DecisaoCotacao("pedir_dado", faltam=list(build_result.missing))
    if build_result.refusals:
        return DecisaoCotacao("recusar", motivos=list(build_result.refusals))
    if build_result.errors:
        return DecisaoCotacao("pedir_correcao", motivos=list(build_result.errors))

    exemplos: list[str] = []
    if rag is not None and query:
        try:
            hits = rag.search(query, RAG_COLLECTION, trace)
            exemplos = [getattr(h, "text", str(h)) for h in hits]
        except Exception:
            exemplos = []                       # RAG é enriquecimento; não bloqueia

    out = quote_client.quote(_extrair_body(build_result), trace)
    if out.status is QuoteStatus.QUOTED:
        return DecisaoCotacao("apresentar_cotacao", quote=out.quote, exemplos=exemplos)
    if out.status is QuoteStatus.REFUSED:
        return DecisaoCotacao("recusar", motivos=[out.reason or "cotacao_recusada"], exemplos=exemplos)
    if out.status is QuoteStatus.INVALID:
        return DecisaoCotacao("pedir_correcao", motivos=[out.reason or "payload_invalido"])
    return DecisaoCotacao("escalar_humano", motivos=[out.reason or "quote_indisponivel"], escalate=True)
