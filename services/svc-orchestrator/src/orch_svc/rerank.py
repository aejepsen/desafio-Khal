"""Re-rank de evidências (RAG + Neo4j) antes do few-shot / resposta.

Leve (sem cross-encoder GPU): mistura score vetorial + sinais do dataset
(outcome ganho, plano cotado, fechamento boleto/apólice, fonte grafo).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass(frozen=True)
class Candidate:
    text: str
    score: float = 0.0
    source: str = "rag"  # rag | neo4j | mixed


@dataclass
class RankedHit:
    text: str
    score: float
    source: str
    features: dict[str, Any] = field(default_factory=dict)


_GANHO = re.compile(r"\bganho\b|outcome\s*=\s*ganho", re.I)
_PERDIDO = re.compile(r"\bperdido\b|outcome\s*=\s*perdido", re.I)
_CLOSE = re.compile(r"\b(fechado|boleto|apolice|apólice|maravilha|pode emitir)\b", re.I)


def rerank(
    candidates: Iterable[Candidate],
    *,
    query: str = "",
    plano_id: str | None = None,
    top_k: int = 3,
) -> list[RankedHit]:
    """Ordena candidatos e devolve top_k."""
    q = (query or "").lower()
    plano = (plano_id or "").strip().lower()
    ranked: list[RankedHit] = []

    for c in candidates:
        text = (c.text or "").strip()
        if not text:
            continue
        low = text.lower()
        base = float(c.score or 0.0)
        # normaliza scores tipicamente 0..1; se vier fora, clipa
        base = max(0.0, min(base, 1.5))

        feat: dict[str, Any] = {"base": round(base, 4), "source": c.source}
        bonus = 0.0

        if _GANHO.search(low):
            bonus += 0.18
            feat["ganho"] = True
        if _PERDIDO.search(low):
            bonus -= 0.12
            feat["perdido"] = True
        if plano and plano in low:
            bonus += 0.22
            feat["plano_match"] = plano
        if _CLOSE.search(low):
            bonus += 0.16
            feat["close_signal"] = True
        if c.source == "neo4j":
            bonus += 0.10
            feat["neo4j"] = True
        # overlap lexical simples com a query
        if q:
            tokens = [t for t in re.findall(r"[a-zà-ü0-9]{3,}", q) if t not in {"para", "como", "quero"}]
            hit = sum(1 for t in tokens if t in low)
            if tokens:
                overlap = hit / len(tokens)
                bonus += 0.12 * overlap
                feat["overlap"] = round(overlap, 3)

        final = base + bonus
        ranked.append(RankedHit(text=text, score=final, source=c.source, features=feat))

    ranked.sort(key=lambda h: h.score, reverse=True)
    # dedup por prefixo
    out: list[RankedHit] = []
    seen: set[str] = set()
    for h in ranked:
        key = h.text[:120]
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
        if len(out) >= top_k:
            break
    return out


def texts_only(ranked: list[RankedHit]) -> list[str]:
    return [h.text for h in ranked]
