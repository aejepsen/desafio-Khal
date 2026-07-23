"""Tratamento de objeção — não desistir no primeiro "não".

Análise do dataset (analysis/objecoes_insights.md): objeção de preço/concorrente/
cobertura teve ~0% de ganho — porque os vendedores NÃO trataram, não porque seja
irrecuperável. O agente REVERTE com tática (abordagens escalonadas) e só escala pro
humano quando a objeção PERSISTE após N tentativas. Simetria com o /quote: retry
antes de desistir.

Táticas ancoradas em metodologias consolidadas de vendas (não no histórico falho):
- **LAER**  Listen → Acknowledge → Explore → Respond (macro-framework de toda resposta).
- **feel-felt-found**  "entendo como se sente · outros sentiram o mesmo · descobriram que…".
- **ancoragem-valor**  reancorar preço em valor/benefício (custo/dia, risco evitado).
- **isolamento**  "além disso, há mais algo que impede?" — separa a objeção real.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

_OBJ = {
    "preco": r"\bcar[oa]\b|pre[çc]o|desconto|valor.*alto|muito alto|parcel|caro demais",
    "concorrente": r"outra|concorr|porto|azul|cotei|mais barato (em|na|no)|j[áa] tenho",
    "cobertura": r"cobertura|cobre|cobrir|franquia|o que inclui|s[óo] isso|terceiro",
    # Pausa / adiamento — NÃO é dúvida específica (evita "entendo sua dúvida").
    "indeciso": (
        r"vou pensar|preciso (pensar|avaliar|ver com calma)|"
        r"depois te (falo|aviso|retorno|respondo)|te aviso|"
        r"falar com (minha|meu|a |o )|"
        r"n[ãa]o sei ainda|talvez depois|mais tarde|"
        r"deixa eu (pensar|ver|avaliar)|vou analisar"
    ),
}


@dataclass
class Tatica:
    texto: str
    framework: str


# táticas por objeção — cada tentativa usa uma abordagem/framework diferente
TATICAS: dict[str, list[Tatica]] = {
    "preco": [
        Tatica("Reconhecer e reancorar: 'entendo — à primeira vista parece; olhando a "
               "cobertura por dia, é proteção do seu carro por centavos.'", "feel-felt-found + ancoragem-valor"),
        Tatica("Isolar a objeção: 'além do valor, tem mais algo que te impede de fechar?' "
               "Se for só preço, oferecer plano essencial (entrada menor) ou parcelamento.", "isolamento + alternativa"),
        Tatica("Ancorar no risco: comparar a mensalidade com o custo de um sinistro sem "
               "seguro (guincho, terceiros, perda total).", "ancoragem-valor"),
    ],
    "concorrente": [
        Tatica("Explorar antes de responder: 'o que você mais valorizou na proposta deles?' "
               "— e então destacar o diferencial que importa pra esse ponto.", "LAER (explore→respond)"),
        Tatica("'Vários clientes vieram de lá e descobriram que a assistência 24h e a "
               "franquia daqui compensam.' Comparar valor, não só preço.", "feel-felt-found"),
    ],
    "cobertura": [
        Tatica("Explorar a preocupação exata ('o que te preocupa não estar coberto?') e "
               "esclarecer o que já está incluso no plano.", "LAER (explore→respond)"),
        Tatica("Oferecer upgrade pontual para a cobertura específica que o lead quer.", "ancoragem-valor"),
    ],
    "indeciso": [
        Tatica(
            "Respeitar o tempo: não inventar 'dúvida'. Porta aberta, cotação guardada, "
            "sem pressão — o lead pediu espaço pra avaliar ou encerrar com educação.",
            "pausa-respeitosa",
        ),
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
    framework: str | None = None
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
        t = taticas[tentativas_feitas]
        return RespostaObjecao(AcaoObjecao.REVERTER, objecao, tatica=t.texto,
                               framework=t.framework, tentativa=tentativas_feitas + 1)
    return RespostaObjecao(AcaoObjecao.ESCALAR, objecao, tentativa=tentativas_feitas,
                           motivo=f"objeção '{objecao}' persistiu após {tentativas_feitas} tentativa(s)")
