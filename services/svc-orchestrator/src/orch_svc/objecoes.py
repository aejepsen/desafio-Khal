"""Tratamento de objeção — não desistir no primeiro "não".

Análise do dataset (analysis/objecoes_insights.md): objeção de preço/concorrente/
cobertura teve ~0% de ganho — mas porque os vendedores NÃO trataram, não porque
seja irrecuperável. O agente tenta REVERTER com tática (escalando abordagens) e só
escala pro humano quando a objeção PERSISTE após N tentativas.

Simetria com o cliente /quote: como não desistimos na 1ª falha de rede (retry+
backoff), não desistimos na 1ª objeção do lead (rebuttal + limite → escala).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

_OBJ = {
    "preco": r"\bcar[oa]\b|pre[çc]o|desconto|valor.*alto|muito alto|parcel|caro demais",
    "concorrente": r"outra|concorr|porto|azul|cotei|mais barato (em|na|no)|j[áa] tenho",
    "cobertura": r"cobertura|cobre|cobrir|franquia|o que inclui|s[óo] isso",
    "indeciso": r"vou pensar|depois|te aviso|falar com|n[ãa]o sei|talvez",
}

# táticas por objeção — ordenadas: cada tentativa usa uma abordagem diferente
TATICAS: dict[str, list[str]] = {
    "preco": [
        "Reancorar em VALOR: cobertura e tranquilidade por dia, não o total mensal.",
        "Oferecer alternativa: plano essencial (entrada menor) ou parcelamento.",
        "Comparar: custo de um sinistro sem seguro >> a mensalidade.",
    ],
    "concorrente": [
        "Destacar o diferencial: o que este plano cobre que o concorrente não.",
        "Reforçar atendimento/assistência 24h e franquia.",
    ],
    "cobertura": [
        "Esclarecer o que já está incluso no plano atual.",
        "Oferecer upgrade pontual para a cobertura que o lead quer.",
    ],
    "indeciso": [
        "Reduzir fricção: resumir o benefício em 1 frase e propor próximo passo simples.",
    ],
}
MAX_TENTATIVAS = 3


class AcaoObjecao(StrEnum):
    REVERTER = "reverter"
    ESCALAR = "escalar"


@dataclass
class RespostaObjecao:
    acao: AcaoObjecao
    objecao: str
    tatica: str | None = None
    tentativa: int = 0
    motivo: str | None = None


def detectar_objecao(texto: str) -> str | None:
    t = texto.lower()
    for nome, pat in _OBJ.items():
        if re.search(pat, t):
            return nome
    return None


def proxima_acao(objecao: str, tentativas_feitas: int,
                 max_tentativas: int = MAX_TENTATIVAS) -> RespostaObjecao:
    """Dada a objeção e quantas reversões já foram tentadas, decide reverter ou escalar."""
    taticas = TATICAS.get(objecao, [])
    if tentativas_feitas < len(taticas) and tentativas_feitas < max_tentativas:
        return RespostaObjecao(AcaoObjecao.REVERTER, objecao,
                               tatica=taticas[tentativas_feitas],
                               tentativa=tentativas_feitas + 1)
    return RespostaObjecao(AcaoObjecao.ESCALAR, objecao, tentativa=tentativas_feitas,
                           motivo=f"objeção '{objecao}' persistiu após {tentativas_feitas} tentativa(s)")
