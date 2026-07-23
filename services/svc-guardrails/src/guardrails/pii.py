"""Máscara de PII pt-BR (CPF, placa, CNH, CEP, e-mail).

Determinístico, sem LLM. Usado no check `pii` do /v1/analyze.
Não altera a decisão allow/block — só o texto sanitizado (logs / downstream seguro).
A extração de slots de cotação deve usar o texto ORIGINAL no agente.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Ordem importa: formatados antes de genéricos.
_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_PLACA = re.compile(r"\b[A-Z]{3}-?\d[A-Z0-9]\d{2}\b", re.I)
_PLACA_ANTIGA = re.compile(r"\b[A-Z]{3}-?\d{4}\b", re.I)
_CNH = re.compile(r"\b(?:CNH[:\s-]*)(\d{9,11})\b", re.I)
_EMAIL = re.compile(r"\b[\w.\-+]+@[\w.\-]+\.\w+\b")
_CEP = re.compile(r"\b\d{5}-?\d{3}\b")


@dataclass(frozen=True)
class PiiResult:
    text: str
    types: list[str]  # cpf, placa, cnh, email, cep


def mask_pii(text: str, locale: str = "pt-BR") -> PiiResult:
    """Retorna texto mascarado + tipos encontrados. locale!=pt-BR: no-op."""
    if locale.lower() not in {"pt-br", "pt_br", "br"}:
        return PiiResult(text, [])
    out = text
    found: list[str] = []

    def _sub(pattern: re.Pattern[str], repl: str, label: str) -> None:
        nonlocal out
        if pattern.search(out):
            out = pattern.sub(repl, out)
            if label not in found:
                found.append(label)

    # CNH rotulada antes do CPF genérico (11 dígitos colidem).
    _sub(_EMAIL, "[EMAIL]", "email")
    _sub(_CNH, "CNH [CNH]", "cnh")
    _sub(_CPF, "[CPF]", "cpf")
    _sub(_PLACA, "[PLACA]", "placa")
    _sub(_PLACA_ANTIGA, "[PLACA]", "placa")
    _sub(_CEP, "[CEP]", "cep")
    return PiiResult(out, found)
