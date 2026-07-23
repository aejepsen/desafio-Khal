from __future__ import annotations

import re
from datetime import date
from typing import Any

_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
_DIGITS_RE = re.compile(r"\D+")


def parse_idade(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    text = str(value).strip()
    m = re.search(r"\d{1,3}", text)
    return int(m.group(0)) if m else None


def parse_veiculo_ano(value: Any, veiculo_texto: Any = None) -> int | None:
    for candidate in (value, veiculo_texto):
        if candidate is None or candidate == "":
            continue
        if isinstance(candidate, bool):
            continue
        if isinstance(candidate, int):
            return candidate
        if isinstance(candidate, float) and candidate.is_integer():
            return int(candidate)
        m = _YEAR_RE.search(str(candidate))
        if m:
            return int(m.group(1))
    return None


def parse_plano_id(value: Any, default: str = "essencial") -> str | None:
    if value is None or value == "":
        return default
    text = str(value).strip().lower()
    # aceita nome amigável
    aliases = {
        "essencial": "essencial",
        "basico": "essencial",
        "básico": "essencial",
        "completo": "completo",
        "premium": "premium",
        "top": "premium",
    }
    if text in aliases:
        return aliases[text]
    for key, pid in aliases.items():
        if key in text:
            return pid
    return text


def parse_cep(value: Any) -> str | None:
    if value is None or value == "":
        return None
    digits = _DIGITS_RE.sub("", str(value))
    if len(digits) != 8:
        return None
    return f"{digits[:5]}-{digits[5:]}"


def parse_data_inicio(value: Any) -> str | None:
    if value is None or value == "":
        return None
    text = str(value).strip()
    try:
        date.fromisoformat(text)
    except ValueError:
        return None
    return text
