from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LeadSlots:
    """Slots já coletados/verificados pelo agente (ainda podem ser string bruta)."""

    idade: Any = None
    veiculo_ano: Any = None
    plano_id: Any = None
    cep: Any = None
    data_inicio: Any = None
    veiculo_texto: Any = None  # fallback para extrair ano (ex.: "Gol 2020")


@dataclass(frozen=True)
class QuoteRequestPayload:
    """Contrato de POST /quote (quote-service)."""

    idade: int
    veiculo_ano: int
    plano_id: str = "essencial"
    cep: str | None = None
    data_inicio: str | None = None

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "plano_id": self.plano_id,
            "idade": self.idade,
            "veiculo_ano": self.veiculo_ano,
        }
        if self.cep is not None:
            body["cep"] = self.cep
        if self.data_inicio is not None:
            body["data_inicio"] = self.data_inicio
        return body


@dataclass(frozen=True)
class BuildResult:
    ok: bool
    payload: QuoteRequestPayload | None = None
    missing: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    refusals: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "payload": self.payload.to_dict() if self.payload else None,
            "missing": list(self.missing),
            "errors": list(self.errors),
            "refusals": list(self.refusals),
        }
