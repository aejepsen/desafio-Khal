"""Detecção de aceite pós-cotação — alinhada ao dataset (ganho)."""
from __future__ import annotations

import re

# Frases frequentes no parquet em conversas ganho (lead / fechamento).
_ACEITE = re.compile(
    r"\b("
    r"fechado|fechamos|pode emitir|vamos nessa|vamos nessa,? gostei|"
    r"gostei|quero contratar|aceito|bora|pode gerar|emite|emitir|"
    r"fechou|pode mandar o boleto|quero o boleto"
    r")\b",
    re.IGNORECASE,
)


def detectar_aceite_cotacao(mensagem: str) -> bool:
    """True se o lead aprova a cotação (padrão das conversas ganho)."""
    t = (mensagem or "").strip()
    if not t:
        return False
    return bool(_ACEITE.search(t))
