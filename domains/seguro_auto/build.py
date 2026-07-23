from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from .models import BuildResult, LeadSlots, QuoteRequestPayload
from .normalize import (
    parse_cep,
    parse_data_inicio,
    parse_idade,
    parse_plano_id,
    parse_veiculo_ano,
)
from .plans import load_plans
from .validate import check_faixa_etaria, check_idade_veiculo, check_plano


def build_quote_request(
    slots: LeadSlots | dict[str, Any],
    *,
    plans_path: str | Path | None = None,
    require_verified: bool = True,
    verified: bool = True,
    today: date | None = None,
) -> BuildResult:
    """Extrai e valida campos do POST /quote conforme planos.json.

    Não calcula prêmio. Se `require_verified` e `verified` for False, recusa montar
    o payload (o agente só chama após confirmar os dados).
    """
    if require_verified and not verified:
        return BuildResult(
            ok=False,
            errors=["dados_nao_verificados"],
        )

    if isinstance(slots, dict):
        slots = LeadSlots(**{k: slots.get(k) for k in LeadSlots.__dataclass_fields__})

    plans = load_plans(str(plans_path) if plans_path else None)
    missing: list[str] = []
    errors: list[str] = []
    refusals: list[str] = []

    idade = parse_idade(slots.idade)
    veiculo_ano = parse_veiculo_ano(slots.veiculo_ano, slots.veiculo_texto)
    plano_id = parse_plano_id(slots.plano_id)
    cep_raw = slots.cep
    cep = parse_cep(cep_raw) if cep_raw not in (None, "") else None
    data_inicio = parse_data_inicio(slots.data_inicio)

    if idade is None:
        missing.append("idade")
    if veiculo_ano is None:
        missing.append("veiculo_ano")
    if cep_raw in (None, ""):
        missing.append("cep")
    elif cep is None:
        errors.append("cep_invalido")
    if slots.data_inicio not in (None, "") and data_inicio is None:
        errors.append("data_inicio_invalida")

    if idade is not None and not (0 <= idade <= 200):
        errors.append("idade_fora_range_contrato")
    if veiculo_ano is not None and not (1950 <= veiculo_ano <= 2100):
        errors.append("veiculo_ano_fora_range_contrato")

    if plano_id is None:
        missing.append("plano_id")
    else:
        plano_err = check_plano(plano_id, plans)
        if plano_err:
            errors.append(plano_err)

    if idade is not None and "idade" not in missing:
        motivo = check_faixa_etaria(idade, plans)
        if motivo:
            refusals.append(motivo)

    if veiculo_ano is not None and "veiculo_ano" not in missing:
        motivo = check_idade_veiculo(veiculo_ano, plans, hoje=today)
        if motivo:
            refusals.append(motivo)

    if missing or errors or refusals:
        return BuildResult(
            ok=False,
            missing=missing,
            errors=errors,
            refusals=refusals,
        )

    assert (
        idade is not None
        and veiculo_ano is not None
        and plano_id is not None
        and cep is not None
    )
    payload = QuoteRequestPayload(
        idade=idade,
        veiculo_ano=veiculo_ano,
        plano_id=plano_id,
        cep=cep,
        data_inicio=data_inicio,
    )
    return BuildResult(ok=True, payload=payload)
