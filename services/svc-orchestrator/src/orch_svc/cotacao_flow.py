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
Candidatos RAG (top_k ampliado) + closes Neo4j passam por `orch_svc.rerank`
antes de virarem `exemplos` (top 3).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

from orch_svc.quote_client import QuoteOutcome, QuoteStatus
from orch_svc.rerank import Candidate, rerank, texts_only

RAG_COLLECTION = "namastex_conversas"
RAG_CANDIDATES = 10
RERANK_TOP_K = 3


class _BuildResult(Protocol):
    body: dict[str, Any] | None
    missing: list[str]
    errors: list[str]
    refusals: list[str]


class _QuoteClient(Protocol):
    def quote(self, body: dict[str, Any], trace: str) -> QuoteOutcome: ...


class _Rag(Protocol):
    def search(self, query: str, domain: str, trace: str, top_k: int = 10) -> list[Any]: ...


@dataclass
class DecisaoCotacao:
    acao: str                                   # apresentar_cotacao | pedir_dado | recusar | pedir_correcao | escalar_humano
    quote: dict[str, Any] | None = None
    faltam: list[str] = field(default_factory=list)
    motivos: list[str] = field(default_factory=list)
    exemplos: list[str] = field(default_factory=list)   # few-shot re-ranked
    exemplos_meta: list[dict[str, Any]] = field(default_factory=list)
    escalate: bool = False


def _rag_search(rag: _Rag, query: str, domain: str, trace: str, top_k: int) -> list[Any]:
    try:
        return rag.search(query, domain, trace, top_k=top_k)
    except TypeError:
        return rag.search(query, domain, trace)  # type: ignore[call-arg]


def _coletar_exemplos(
    *,
    query: str,
    rag: _Rag | None,
    trace: str,
    plano_id: str | None,
    graph_examples: Sequence[str] | None,
) -> tuple[list[str], list[dict[str, Any]]]:
    cands: list[Candidate] = []
    if rag is not None and query:
        try:
            for h in _rag_search(rag, query, RAG_COLLECTION, trace, RAG_CANDIDATES):
                cands.append(
                    Candidate(
                        text=getattr(h, "text", str(h)),
                        score=float(getattr(h, "score", 0.0) or 0.0),
                        source="rag",
                    )
                )
        except Exception:
            pass
    for t in graph_examples or ():
        if t and str(t).strip():
            cands.append(Candidate(text=str(t).strip(), score=0.55, source="neo4j"))
    if not cands:
        return [], []
    ranked = rerank(cands, query=query, plano_id=plano_id, top_k=RERANK_TOP_K)
    meta = [
        {"score": round(h.score, 4), "source": h.source, "features": h.features}
        for h in ranked
    ]
    return texts_only(ranked), meta


def _extrair_body(build_result: Any) -> dict[str, Any]:
    """BuildResult.payload -> dict do POST /quote.

    REGRA: nenhum campo enviado ao /quote pode ser nulo — campos None são OMITIDOS
    do body (filtro duro, independente do método de serialização do payload).
    """
    payload = getattr(build_result, "payload", None) or getattr(build_result, "body", None)
    if payload is None:
        return {}
    raw: dict[str, Any]
    if isinstance(payload, dict):
        raw = payload
    else:
        for meth in ("to_dict", "to_body", "as_body", "as_dict", "model_dump", "dict"):
            fn = getattr(payload, meth, None)
            if callable(fn):
                raw = fn()
                break
        else:
            raw = dict(getattr(payload, "__dict__", {}))
    return {k: v for k, v in raw.items() if v is not None}   # nunca envia null


def decidir_cotacao(
    build_result: _BuildResult,
    quote_client: _QuoteClient,
    *,
    query: str | None = None,
    rag: _Rag | None = None,
    plano_id: str | None = None,
    graph_examples: Sequence[str] | None = None,
    trace: str = "-",
) -> DecisaoCotacao:
    if build_result.missing:
        return DecisaoCotacao("pedir_dado", faltam=list(build_result.missing))
    if build_result.refusals:
        return DecisaoCotacao("recusar", motivos=list(build_result.refusals))
    if build_result.errors:
        return DecisaoCotacao("pedir_correcao", motivos=list(build_result.errors))

    # RAG + Neo4j → re-rank (falha não bloqueia cotação)
    exemplos, exemplos_meta = _coletar_exemplos(
        query=query or "",
        rag=rag,
        trace=trace,
        plano_id=plano_id,
        graph_examples=graph_examples,
    )

    out = quote_client.quote(_extrair_body(build_result), trace)
    if out.status is QuoteStatus.QUOTED:
        return DecisaoCotacao(
            "apresentar_cotacao",
            quote=out.quote,
            exemplos=exemplos,
            exemplos_meta=exemplos_meta,
        )
    if out.status is QuoteStatus.REFUSED:
        return DecisaoCotacao(
            "recusar",
            motivos=[out.reason or "cotacao_recusada"],
            exemplos=exemplos,
            exemplos_meta=exemplos_meta,
        )
    if out.status is QuoteStatus.INVALID:
        return DecisaoCotacao("pedir_correcao", motivos=[out.reason or "payload_invalido"])
    return DecisaoCotacao("escalar_humano", motivos=[out.reason or "quote_indisponivel"], escalate=True)
