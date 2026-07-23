"""Upstreams registrados (config v1): serviços do ecossistema + seus /metrics."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Upstream:
    name: str
    url: str


# Default do ecossistema portfolio (gates / FakeScraper).
REGISTRY: list[Upstream] = [
    Upstream("svc-guardrails", "http://svc-guardrails:8200/metrics"),
    Upstream("svc-evals", "http://svc-evals:8201/metrics"),
    Upstream("svc-inference", "http://svc-inference:8202/metrics"),
    Upstream("svc-router", "http://svc-router:8203/metrics"),
    Upstream("svc-rag", "http://svc-rag:8204/metrics"),
    Upstream("svc-orchestrator", "http://svc-orchestrator:8206/metrics"),
]


def _parse_env_upstreams(raw: str) -> list[Upstream]:
    """Formato: name=url,name=url  (vírgula separa entradas)."""
    out: list[Upstream] = []
    for part in raw.split(","):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, url = part.split("=", 1)
        name, url = name.strip(), url.strip()
        if name and url:
            out.append(Upstream(name, url))
    return out


def registry() -> list[Upstream]:
    """Override via OBS_UPSTREAMS (desafio-Khal compose) sem quebrar gates default."""
    raw = os.environ.get("OBS_UPSTREAMS", "").strip()
    if raw:
        parsed = _parse_env_upstreams(raw)
        if parsed:
            return parsed
    return list(REGISTRY)
