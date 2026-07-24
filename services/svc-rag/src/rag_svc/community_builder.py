"""Detecção de comunidade (GraphRAG) — lógica pura, sem I/O.

Constrói um grafo de conversas a partir de linhas já buscadas do Neo4j
(`Conversation` com outcome=ganho, planos mencionados, has_close) e roda
detecção de comunidade (Louvain) sobre ele. O I/O (conexão Neo4j, escrita
do artefato) fica em `scripts/build_rag_communities.py` — este módulo só
faz a parte testável sem depender de rede.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

import networkx as nx

FAIXAS = ("jovem_18_30", "meia_30_50", "senior_50+", "desconhecida")


def faixa_de(idade: int | None) -> str:
    if idade is None:
        return "desconhecida"
    if idade < 31:
        return "jovem_18_30"
    if idade < 51:
        return "meia_30_50"
    return "senior_50+"


@dataclass(frozen=True)
class ConversaRow:
    id: str
    idade: int | None
    has_close: bool
    planos: tuple[str, ...] = ()

    @property
    def plano_dominante(self) -> str:
        return self.planos[0] if self.planos else "sem_plano_mencionado"

    @property
    def faixa(self) -> str:
        return faixa_de(self.idade)


_BRIDGE_SAMPLE = 3  # arestas fracas por par de faixas dentro do mesmo plano


def build_graph(rows: list[ConversaRow]) -> nx.Graph:
    """Clique densa por (plano, faixa) + pontes fracas entre faixas do mesmo plano.

    Conectar TODO par que compartilha só o plano (sem olhar faixa) faz cada
    plano virar um grafo quase-completo — e grafos completos não se dividem
    por modularidade, então o Louvain nunca enxerga a faixa etária (achado
    ao rodar: 3 comunidades = 3 planos, nada mais). O padrão certo pra
    detecção de comunidade de verdade é "denso dentro do grupo, esparso
    entre grupos": clique (peso 1.0) dentro de cada (plano, faixa); só
    algumas arestas de ponte (peso baixo) entre faixas diferentes do mesmo
    plano, pra manter o grafo conectado sem afogar o sinal da faixa.
    """
    g = nx.Graph()
    for r in rows:
        g.add_node(r.id, idade=r.idade, faixa=r.faixa, plano=r.plano_dominante,
                   has_close=r.has_close)

    by_grupo: dict[tuple[str, str], list[ConversaRow]] = {}
    for r in rows:
        by_grupo.setdefault((r.plano_dominante, r.faixa), []).append(r)

    for membros in by_grupo.values():
        for i in range(len(membros)):
            for j in range(i + 1, len(membros)):
                g.add_edge(membros[i].id, membros[j].id, weight=1.0)

    by_plano: dict[str, dict[str, list[ConversaRow]]] = {}
    for (plano, faixa), membros in by_grupo.items():
        by_plano.setdefault(plano, {})[faixa] = membros

    for faixas_do_plano in by_plano.values():
        nomes = list(faixas_do_plano)
        for i in range(len(nomes)):
            for j in range(i + 1, len(nomes)):
                a_list = faixas_do_plano[nomes[i]][:_BRIDGE_SAMPLE]
                b_list = faixas_do_plano[nomes[j]][:_BRIDGE_SAMPLE]
                for a, b in zip(a_list, b_list):
                    g.add_edge(a.id, b.id, weight=0.05)
    return g


def detect_communities(g: nx.Graph, *, seed: int = 42) -> list[set[str]]:
    if g.number_of_nodes() == 0:
        return []
    return list(nx.algorithms.community.louvain_communities(g, weight="weight", seed=seed))


def _moda(valores: list[str]) -> str:
    if not valores:
        return "n/d"
    return Counter(valores).most_common(1)[0][0]


def summarize_community(cid: str, membros: set[str], g: nx.Graph) -> dict[str, Any]:
    nodes = [g.nodes[m] for m in membros]
    planos = [n["plano"] for n in nodes]
    faixas = [n["faixa"] for n in nodes]
    n_close = sum(1 for n in nodes if n.get("has_close"))
    plano_dom = _moda(planos)
    faixa_dom = _moda(faixas)
    pct_close = round(100.0 * n_close / len(nodes), 1) if nodes else 0.0
    title = f"{faixa_dom} · {plano_dom}"
    summary = (
        f"Comunidade de leads {faixa_dom}, predominantemente plano {plano_dom} "
        f"(N={len(nodes)} conversas ganhas). {pct_close}% fecharam com boleto/apólice "
        f"registrados no fluxo (has_close=true)."
    )
    return {
        "id": cid,
        "title": title,
        "summary": summary,
        "members": sorted(membros),
        "stats": {
            "size": len(nodes),
            "plano_dominante": plano_dom,
            "faixa_dominante": faixa_dom,
            "pct_has_close": pct_close,
        },
    }


def build_communities_artifact(rows: list[ConversaRow], *, seed: int = 42) -> dict[str, Any]:
    """Pipeline completo (puro): rows -> grafo -> comunidades -> artefato dict."""
    g = build_graph(rows)
    coms = detect_communities(g, seed=seed)
    # maiores comunidades primeiro — mais úteis pro consumidor do artefato
    coms.sort(key=len, reverse=True)
    communities = [
        summarize_community(str(i), membros, g) for i, membros in enumerate(coms)
    ]
    return {"communities": communities}
