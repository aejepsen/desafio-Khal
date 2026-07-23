"""Cópia HITL grau A — o que o lead vê quando escala (sem jargão de infra).

Motivos técnicos (503, circuito, retries) ficam no audit (`dec.motivos`).
A mensagem WhatsApp é sempre humana, honesta e sem prêmio inventado.
"""
from __future__ import annotations

import re
from typing import Iterable

# Texto canônico (grau A) por família de motivo.
_HITL_LEAD: dict[str, str] = {
    "quote_instavel": (
        "Tive uma instabilidade no sistema de cotação agora e não consigo te passar "
        "um valor com segurança. Vou te conectar com um atendente humano pra continuar. "
        "Um atendente humano vai continuar daqui."
    ),
    "midia": (
        "Recebi sua mídia, mas não consegui ler o conteúdo com segurança por aqui. "
        "Vou te conectar com um atendente humano pra seguir. "
        "Um atendente humano vai continuar daqui."
    ),
    "objecao": (
        "Quero te atender bem e já tentei alguns caminhos por aqui. "
        "Vou te conectar com um atendente humano pra continuar com calma. "
        "Um atendente humano vai continuar daqui."
    ),
    "guardrails": (
        "Pra sua segurança, vou te conectar com um atendente humano pra continuar. "
        "Um atendente humano vai continuar daqui."
    ),
    "estagnado": (
        "Pra não te deixar sem resposta, vou te conectar com um atendente humano "
        "pra continuar a cotação. Um atendente humano vai continuar daqui."
    ),
    "generico": (
        "Vou te conectar com um atendente humano pra continuar com segurança. "
        "Um atendente humano vai continuar daqui."
    ),
}

_CTA = "Um atendente humano vai continuar daqui."

# Vazamentos técnicos / venda indevida — proibidos na fala ao lead.
_JARGÃO = re.compile(
    r"\b(503|502|500|504|timeout|circuito|breaker|retry|tentativas|"
    r"unavailable|http|traceback|exception)\b",
    re.I,
)
_PREMIO_INVENTADO = re.compile(r"R\$\s*\d|\d+[.,]\d{2}\s*/\s*m[eê]s", re.I)


def classificar_motivo_hitl(motivos: Iterable[str] | None) -> str:
    blob = " ".join(motivos or ()).lower()
    if any(
        x in blob
        for x in (
            "503", "502", "500", "504", "timeout", "transporte", "circuito",
            "unavailable", "quote", "esgotou", "indispon", "instáv", "instav",
        )
    ):
        return "quote_instavel"
    if any(x in blob for x in ("mídia", "midia", "transcri", "áudio", "audio", "documento")):
        return "midia"
    if any(x in blob for x in ("objeção", "objecao", "preco", "preço")):
        return "objecao"
    if any(x in blob for x in ("guardrail", "injection", "bloquead")):
        return "guardrails"
    if any(x in blob for x in ("turno", "não avançou", "nao avancou")):
        return "estagnado"
    return "generico"


def mensagem_hitl_lead(motivos: Iterable[str] | None) -> str:
    """Mensagem grau A ao lead (WhatsApp)."""
    return _HITL_LEAD[classificar_motivo_hitl(motivos)]


def cta_hitl() -> str:
    return _CTA


def validar_hitl_lead(texto: str) -> bool:
    """True se o texto ao lead está no padrão A (handoff, sem jargão, sem prêmio)."""
    t = (texto or "").strip()
    if not t:
        return False
    low = t.lower()
    if "atendente" not in low and "humano" not in low:
        return False
    if _JARGÃO.search(t):
        return False
    if _PREMIO_INVENTADO.search(t):
        return False
    # não vender cobertura como se tivesse cotado
    if any(x in low for x in ("protege sua família", "cobertura familiar", "seu patrimônio")):
        if "instabilidade" not in low and "não consigo" not in low and "nao consigo" not in low:
            # pitch de venda sem admitir falha → rejeita
            if "conectar" not in low and "atendente" not in low:
                return False
            # se tem atendente mas ainda parece pitch longo de venda, exige handoff claro
            if "vou te conectar" not in low and "conectar com um atendente" not in low:
                return False
    return True
