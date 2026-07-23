"""Domínio determinístico de seguro auto.

Monta o payload de POST /quote a partir dos slots do lead, validando contra
planos.json. Não calcula prêmio — isso é responsabilidade do quote-service.
"""

from .build import build_quote_request
from .models import BuildResult, LeadSlots, QuoteRequestPayload

__all__ = [
    "LeadSlots",
    "QuoteRequestPayload",
    "BuildResult",
    "build_quote_request",
]
