from __future__ import annotations

from datetime import date
from typing import Any


def check_plano(plano_id: str, plans: dict[str, Any]) -> str | None:
    ids = {p["id"] for p in plans["planos"]}
    if plano_id not in ids:
        return f"Plano '{plano_id}' inexistente. Opcoes: {', '.join(sorted(ids))}."
    return None


def check_faixa_etaria(idade: int, plans: dict[str, Any]) -> str | None:
    for f in plans["regras"]["faixa_etaria"]:
        if f["idade_min"] <= idade <= f["idade_max"]:
            if f.get("recusar"):
                return str(f["motivo"])
            return None
    return "Idade fora das faixas aceitas."


def check_idade_veiculo(veiculo_ano: int, plans: dict[str, Any], hoje: date | None = None) -> str | None:
    ref = hoje or date.today()
    anos = ref.year - veiculo_ano
    for f in plans["regras"]["idade_veiculo"]:
        if f["anos_min"] <= anos <= f["anos_max"]:
            if f.get("recusar"):
                return str(f["motivo"])
            return None
    return "Idade do veiculo fora das faixas aceitas."


def is_cep_alto_risco(cep: str | None, plans: dict[str, Any]) -> bool:
    """Informativo — não bloqueia; o agravo é aplicado pelo quote-service."""
    if not cep:
        return False
    pref = cep.replace("-", "")[:2]
    return pref in plans["regras"]["regiao_cep"]["prefixos_alto_risco"]
