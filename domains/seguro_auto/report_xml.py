"""Gera XML tabular: colunas de planos/slots (input) + JSON /quote (output)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .models import BuildResult, LeadSlots
from .plans import load_plans
from .validate import is_cep_alto_risco


INPUT_COLS = (
    "case_id",
    "plano_id_in",
    "plano_nome",
    "base_mensal",
    "franquia",
    "idade",
    "faixa_etaria",
    "veiculo_ano",
    "idade_veiculo_anos",
    "faixa_idade_veiculo",
    "cep",
    "cep_prefixo",
    "cep_alto_risco",
    "data_inicio",
    "veiculo_texto",
    "verified",
)

OUTPUT_COLS = (
    "ok",
    "out_plano_id",
    "out_idade",
    "out_veiculo_ano",
    "out_cep",
    "out_data_inicio",
    "missing",
    "errors",
    "refusals",
)


def _faixa_etaria_label(idade: int | None, plans: dict[str, Any]) -> str:
    if idade is None:
        return ""
    for f in plans["regras"]["faixa_etaria"]:
        if f["idade_min"] <= idade <= f["idade_max"]:
            tag = "recusar" if f.get("recusar") else f"x{f.get('multiplicador', '')}"
            return f"{f['idade_min']}-{f['idade_max']}({tag})"
    return "fora"


def _faixa_veiculo_label(anos: int | None, plans: dict[str, Any]) -> str:
    if anos is None:
        return ""
    for f in plans["regras"]["idade_veiculo"]:
        if f["anos_min"] <= anos <= f["anos_max"]:
            tag = "recusar" if f.get("recusar") else f"x{f.get('multiplicador', '')}"
            return f"{f['anos_min']}-{f['anos_max']}({tag})"
    return "fora"


def _plano_meta(plano_id: str | None, plans: dict[str, Any]) -> tuple[str, str, str]:
    if not plano_id:
        return "", "", ""
    pid = str(plano_id).strip().lower()
    for p in plans["planos"]:
        if p["id"] == pid or p["nome"].lower() == pid:
            return str(p["nome"]), str(p["base_mensal"]), str(p["franquia"])
    return "", "", ""


def row_from_case(
    *,
    case_id: str,
    slots: LeadSlots,
    result: BuildResult,
    verified: bool,
    today: date,
    plans: dict[str, Any] | None = None,
) -> dict[str, str]:
    plans = plans or load_plans()
    idade = result.payload.idade if result.payload else None
    # prefer parsed intent for annotation; fall back to raw slot
    try:
        idade_ann = int(slots.idade) if slots.idade not in (None, "") else idade
    except (TypeError, ValueError):
        idade_ann = idade

    veiculo_ano_ann = result.payload.veiculo_ano if result.payload else None
    if veiculo_ano_ann is None and slots.veiculo_ano not in (None, ""):
        try:
            veiculo_ano_ann = int(slots.veiculo_ano)
        except (TypeError, ValueError):
            veiculo_ano_ann = None

    idade_veiculo = (today.year - veiculo_ano_ann) if veiculo_ano_ann is not None else None
    plano_in = "" if slots.plano_id in (None, "") else str(slots.plano_id)
    nome, base, franquia = _plano_meta(plano_in or (result.payload.plano_id if result.payload else None), plans)

    cep = result.payload.cep if result.payload and result.payload.cep else (
        str(slots.cep) if slots.cep not in (None, "") else ""
    )
    digits = "".join(c for c in cep if c.isdigit())
    prefixo = digits[:2] if len(digits) >= 2 else ""

    out = result.payload.to_dict() if result.payload else {}
    return {
        "case_id": case_id,
        "plano_id_in": plano_in,
        "plano_nome": nome,
        "base_mensal": base,
        "franquia": franquia,
        "idade": "" if slots.idade in (None, "") else str(slots.idade),
        "faixa_etaria": _faixa_etaria_label(idade_ann if isinstance(idade_ann, int) else None, plans),
        "veiculo_ano": "" if slots.veiculo_ano in (None, "") else str(slots.veiculo_ano),
        "idade_veiculo_anos": "" if idade_veiculo is None else str(idade_veiculo),
        "faixa_idade_veiculo": _faixa_veiculo_label(idade_veiculo, plans),
        "cep": "" if slots.cep in (None, "") else str(slots.cep),
        "cep_prefixo": prefixo,
        "cep_alto_risco": str(is_cep_alto_risco(cep or None, plans)).lower(),
        "data_inicio": "" if slots.data_inicio in (None, "") else str(slots.data_inicio),
        "veiculo_texto": "" if slots.veiculo_texto in (None, "") else str(slots.veiculo_texto),
        "verified": str(verified).lower(),
        "ok": str(result.ok).lower(),
        "out_plano_id": str(out.get("plano_id", "")),
        "out_idade": str(out.get("idade", "")),
        "out_veiculo_ano": str(out.get("veiculo_ano", "")),
        "out_cep": str(out.get("cep", "")),
        "out_data_inicio": str(out.get("data_inicio", "")),
        "missing": "|".join(result.missing),
        "errors": "|".join(result.errors),
        "refusals": "|".join(result.refusals),
    }


def write_results_xml(
    rows: Iterable[dict[str, str]],
    path: Path,
    *,
    today: date,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    root = ET.Element(
        "domain_quote_results",
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "today": today.isoformat(),
            "source_plans": "quote-service/data/plans.json",
        },
    )
    cols_el = ET.SubElement(root, "columns")
    for name in INPUT_COLS:
        ET.SubElement(cols_el, "col", {"name": name, "role": "input_planos_slots"})
    for name in OUTPUT_COLS:
        ET.SubElement(cols_el, "col", {"name": name, "role": "output_quote_json"})

    rows_el = ET.SubElement(root, "rows")
    for row in rows:
        row_el = ET.SubElement(rows_el, "row")
        for name in (*INPUT_COLS, *OUTPUT_COLS):
            cell = ET.SubElement(row_el, name)
            cell.text = row.get(name, "")

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return path
