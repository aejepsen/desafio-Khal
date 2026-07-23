"""Extração de slots do lead — heurística + LLM opcional (svc-inference).

Heurística sempre roda (rápida, offline). Se houver cliente de inference, o LLM
enriquece (plano/veículo em texto livre). Falha de LLM NÃO bloqueia: degrada
para a heurística. O domínio determinístico continua sendo o porteiro final.

Campos do LLM só entram se estiverem *ancurados* no texto do lead (anti-alucinação).
"""
from __future__ import annotations

import json
import re
from typing import Any, Protocol

from orch_svc.agente_cotacao import extrair_slots_heuristica

_JSON_BLOCK = re.compile(r"\{[^{}]*\}", re.S)
_CEP_DIGITS = re.compile(r"\d{5}\d{3}|\d{5}-?\d{3}")

_SYSTEM = (
    "Você extrai dados para cotação de seguro auto. "
    "Responda APENAS um JSON válido, sem markdown, com chaves opcionais: "
    "idade (int), veiculo_ano (int), plano_id (essencial|completo|premium), "
    "cep (str), veiculo_texto (str), data_inicio (YYYY-MM-DD). "
    "REGRA: só inclua uma chave se o valor aparecer EXPLICITAMENTE na mensagem do lead. "
    "Omita chaves desconhecidas. NÃO invente CEP, plano, veículo, idade nem data."
)


class _ChatClient(Protocol):
    def chat(self, messages: list[dict[str, str]], trace: str) -> str: ...


def _parse_json_slots(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {}
    candidates = [text]
    m = _JSON_BLOCK.search(text)
    if m:
        candidates.insert(0, m.group(0))
    for raw in candidates:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return _sanitize(data)
    return {}


def _sanitize(data: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if "idade" in data and data["idade"] is not None:
        try:
            out["idade"] = int(data["idade"])
        except (TypeError, ValueError):
            pass
    if "veiculo_ano" in data and data["veiculo_ano"] is not None:
        try:
            out["veiculo_ano"] = int(data["veiculo_ano"])
        except (TypeError, ValueError):
            pass
    plano = data.get("plano_id")
    if isinstance(plano, str) and plano.strip().lower() in {"essencial", "completo", "premium"}:
        out["plano_id"] = plano.strip().lower()
    cep = data.get("cep")
    if isinstance(cep, str) and cep.strip():
        out["cep"] = cep.strip()
    vt = data.get("veiculo_texto")
    if isinstance(vt, str) and vt.strip():
        out["veiculo_texto"] = vt.strip()
    di = data.get("data_inicio")
    if isinstance(di, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", di.strip()):
        out["data_inicio"] = di.strip()
    return out


def _ancorado_no_texto(slots: dict[str, Any], texto: str) -> dict[str, Any]:
    """Descarta campos LLM que não têm evidência literal na mensagem."""
    raw = texto or ""
    low = raw.lower()
    digits = re.sub(r"\D", "", raw)
    out: dict[str, Any] = {}

    if "idade" in slots:
        idade = slots["idade"]
        if re.search(rf"\b{idade}\s*anos\b", low) or re.search(rf"\bidade\s*{idade}\b", low):
            out["idade"] = idade

    if "veiculo_ano" in slots:
        ano = slots["veiculo_ano"]
        if re.search(rf"\b{ano}\b", raw):
            out["veiculo_ano"] = ano

    if "plano_id" in slots:
        plano = slots["plano_id"]
        # exige a palavra do plano (ou sinônimo heurístico) no texto
        ok = plano in low
        if plano == "completo" and re.search(r"\bintermedi", low):
            ok = True
        if plano == "essencial" and re.search(r"essencial|b[áa]sico|simples", low):
            ok = True
        if plano == "premium" and re.search(r"premium|cobertura total|mais completo", low):
            ok = True
        if ok:
            out["plano_id"] = plano

    if "cep" in slots:
        cep_digits = re.sub(r"\D", "", str(slots["cep"]))
        if len(cep_digits) >= 8 and cep_digits[:8] in digits:
            out["cep"] = slots["cep"]

    if "veiculo_texto" in slots:
        vt = str(slots["veiculo_texto"]).strip()
        tokens = [t for t in re.findall(r"[a-zA-ZÀ-ü]{3,}", vt.lower()) if t not in {"um", "uma", "ano"}]
        if tokens and all(t in low for t in tokens[:2]):
            out["veiculo_texto"] = vt

    if "data_inicio" in slots:
        di = slots["data_inicio"]
        if di in raw:
            out["data_inicio"] = di

    return out


def _merge(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    """LLM prevalece quando traz valor ancorado; heurística preenche buracos."""
    merged = dict(base)
    for k, v in extra.items():
        if v is not None and v != "":
            merged[k] = v
    return merged


def extrair_slots(texto: str, inference: _ChatClient | None = None,
                  *, trace: str = "extract") -> dict[str, Any]:
    heur = extrair_slots_heuristica(texto)
    if inference is None:
        return heur
    try:
        content = inference.chat(
            [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": texto},
            ],
            trace,
        )
    except Exception:
        return heur
    llm = _ancorado_no_texto(_parse_json_slots(content), texto)
    return _merge(heur, llm)


def fazer_extrator(inference: _ChatClient | None = None) -> Any:
    """Callable compatível com run_turno(..., extrair=...)."""

    def _fn(texto: str) -> dict[str, Any]:
        return extrair_slots(texto, inference)

    return _fn
