"""Cliente resiliente do quote-service (o sistema que falha de propósito).

O ponto que "mais separa" na avaliação: o que o agente faz quando /quote falha.
Política (ver STATE / README):
  - 200            -> QUOTED   (cotação saiu)
  - 422            -> REFUSED  (regra de negócio: idade/veículo fora de faixa) — OBSERVAÇÃO
  - 400            -> INVALID  (payload inválido: falta dado) — OBSERVAÇÃO ao loop
  - 5xx / timeout  -> retry + backoff; conta no circuit breaker
  - esgotou / circuito OPEN -> UNAVAILABLE (escala humano; NUNCA inventa cotação)

4xx é resposta legítima do downstream (serviço vivo) — não conta como falha de infra
(reusa a semântica do circuit.py: "4xx NÃO conta"). Só transporte/5xx abre o circuito.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from orch_svc.circuit import CircuitBreaker, CircuitOpen


class QuoteStatus(StrEnum):
    QUOTED = "quoted"
    REFUSED = "refused"
    INVALID = "invalid"
    UNAVAILABLE = "unavailable"


@dataclass
class QuoteOutcome:
    status: QuoteStatus
    quote: dict[str, Any] | None = None   # body do 200
    reason: str | None = None             # motivo (refused/invalid) ou erro (unavailable)
    attempts: int = 0
    escalate: bool = False                # UNAVAILABLE -> encaminhar pro humano


def _reason(resp: Any) -> str:
    try:
        d = resp.json()
        return str(d.get("motivo") or d.get("detalhe") or d.get("error") or resp.text[:160])
    except Exception:
        return resp.text[:160]


@dataclass
class ResilientQuoteClient:
    base_url: str
    timeout_s: float = 10.0
    max_retries: int = 3
    backoff_base_s: float = 0.5
    breaker: CircuitBreaker = field(default_factory=lambda: CircuitBreaker(3, 30.0))
    _sleep: Any = time.sleep   # injetável em teste

    def quote(self, body: dict[str, Any], trace: str = "-") -> QuoteOutcome:
        import httpx

        try:
            self.breaker.before_call()
        except CircuitOpen:
            return QuoteOutcome(QuoteStatus.UNAVAILABLE,
                                reason="circuito OPEN (quote-service instável)", escalate=True)

        last = ""
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = httpx.post(f"{self.base_url}/quote", json=body, timeout=self.timeout_s)
            except httpx.HTTPError as exc:                 # timeout / conexão
                self.breaker.on_transport_failure()
                last = f"transporte: {exc}"
                self._backoff(attempt)
                continue

            sc = resp.status_code
            if sc == 200:
                self.breaker.on_success()
                return QuoteOutcome(QuoteStatus.QUOTED, quote=resp.json(), attempts=attempt)
            if sc == 422:                                  # recusa de negócio — observação
                self.breaker.on_success()                  # downstream vivo
                return QuoteOutcome(QuoteStatus.REFUSED, reason=_reason(resp), attempts=attempt)
            if sc == 400:                                  # payload inválido — falta dado
                self.breaker.on_success()
                return QuoteOutcome(QuoteStatus.INVALID, reason=_reason(resp), attempts=attempt)

            # 5xx e inesperados = falha de infra -> retry + circuit
            self.breaker.on_transport_failure()
            last = f"{sc}"
            self._backoff(attempt)

        return QuoteOutcome(QuoteStatus.UNAVAILABLE, attempts=self.max_retries, escalate=True,
                            reason=f"esgotou {self.max_retries} tentativas (última: {last})")

    def _backoff(self, attempt: int) -> None:
        self._sleep(self.backoff_base_s * (2 ** (attempt - 1)))
