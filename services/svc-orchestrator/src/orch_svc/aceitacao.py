"""Detecção de aceite pós-cotação — alinhada ao dataset (ganho)."""
from __future__ import annotations

import re

# Frases frequentes no parquet + variantes naturais do lead (UI/WhatsApp).
_ACEITE = re.compile(
    r"("
    r"\bfechado\b|\bfechamos\b|\bfechou\b|"
    r"\bpode emitir\b|\bemite\b|\bemitir\b|"
    r"\bvamos nessa\b|\bgostei\b|\bbora\b|"
    r"\baceito\b|\baprovo\b|\baprovado\b|\baprovar\b|\bconfirmo\b|\bconfirmado\b|"
    r"\bcontratar\b|"  # cobre: quero/vou/vamos contratar
    r"\bpode gerar\b|"
    r"\bpode mandar\b|\bmanda(r)?\b.{0,20}\bboleto\b|"
    r"\bquero o boleto\b|\bboleto\b.{0,12}\bap[oó]lice\b|"
    r"\bvamos fechar\b|\bpode fechar\b|\bfechar\b|"
    r"\bpode seguir\b|\bmanda a ap[oó]lice\b|\bquero a ap[oó]lice\b"
    r")",
    re.IGNORECASE,
)


def detectar_aceite_cotacao(mensagem: str) -> bool:
    """True se o lead aprova a cotação (padrão das conversas ganho)."""
    t = (mensagem or "").strip()
    if not t:
        return False
    return bool(_ACEITE.search(t))
