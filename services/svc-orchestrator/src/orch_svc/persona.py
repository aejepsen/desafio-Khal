"""Estilo de abordagem por idade — modula o TOM da comunicação, não a lógica.

⚠️ Achado do dataset (validado antes de fixar — anti-Goodhart): idade NÃO prediz
outcome (jovem/meia/sênior têm distribuição de ganho ~igual, 28-30%). Portanto a
persona é RAPPORT/UX (falar a língua do público), NÃO uma alavanca de conversão —
não prometemos o que o dado não sustenta. A decisão (cotar/reverter/escalar) é a
mesma; só muda como a mensagem é redigida.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Faixa(StrEnum):
    JOVEM = "jovem_18_30"
    MEIA = "meia_30_50"
    SENIOR = "senior_50+"
    DESCONHECIDA = "desconhecida"


@dataclass
class Persona:
    faixa: Faixa
    tom: str
    foco: str
    diretrizes: list[str] = field(default_factory=list)


_PERSONAS = {
    Faixa.JOVEM: Persona(Faixa.JOVEM, "informal e ágil", "praticidade, rapidez, preço",
                         ["frases curtas, sem jargão", "resolver rápido, poucos passos",
                          "destacar contratar em minutos pelo WhatsApp"]),
    Faixa.MEIA: Persona(Faixa.MEIA, "equilibrado e consultivo", "cobertura e proteção da família",
                        ["explicar o que o plano cobre e por quê",
                         "conectar com proteção do patrimônio/família"]),
    Faixa.SENIOR: Persona(Faixa.SENIOR, "formal, claro e paciente", "confiança, segurança, atendimento humano",
                          ["tratar por senhor/senhora, sem gírias",
                           "clareza nos termos; reforçar assistência e canal humano disponível"]),
    Faixa.DESCONHECIDA: Persona(Faixa.DESCONHECIDA, "neutro e cordial", "clareza",
                                ["tom profissional padrão até identificar o perfil"]),
}


def persona_por_idade(idade: int | None) -> Persona:
    if idade is None:
        return _PERSONAS[Faixa.DESCONHECIDA]
    if idade < 31:
        return _PERSONAS[Faixa.JOVEM]
    if idade < 51:
        return _PERSONAS[Faixa.MEIA]
    return _PERSONAS[Faixa.SENIOR]


def diretriz_de_estilo(idade: int | None) -> str:
    """String pronta para injetar no prompt de redação da resposta (não na decisão)."""
    p = persona_por_idade(idade)
    return (f"Estilo ({p.faixa}): tom {p.tom}; foco em {p.foco}. "
            + " ".join(f"- {d}." for d in p.diretrizes))
