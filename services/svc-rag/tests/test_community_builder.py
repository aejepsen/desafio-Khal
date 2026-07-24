"""Testes da detecção de comunidade (GraphRAG) — lógica pura, sem Neo4j."""
from __future__ import annotations

from rag_svc.community_builder import (
    ConversaRow,
    build_communities_artifact,
    build_graph,
    detect_communities,
    faixa_de,
)


def test_faixa_de():
    assert faixa_de(None) == "desconhecida"
    assert faixa_de(25) == "jovem_18_30"
    assert faixa_de(40) == "meia_30_50"
    assert faixa_de(60) == "senior_50+"
    # limites
    assert faixa_de(30) == "jovem_18_30" and faixa_de(31) == "meia_30_50"
    assert faixa_de(50) == "meia_30_50" and faixa_de(51) == "senior_50+"


def _rows() -> list[ConversaRow]:
    # 2 grupos bem separados: jovem+essencial (4) e senior+premium (4)
    return [
        ConversaRow("c1", 22, True, ("essencial",)),
        ConversaRow("c2", 24, True, ("essencial",)),
        ConversaRow("c3", 26, False, ("essencial",)),
        ConversaRow("c4", 28, True, ("essencial",)),
        ConversaRow("c5", 60, True, ("premium",)),
        ConversaRow("c6", 62, True, ("premium",)),
        ConversaRow("c7", 65, False, ("premium",)),
        ConversaRow("c8", 68, True, ("premium",)),
    ]


def test_build_graph_dense_dentro_do_grupo_esparsa_entre_grupos():
    g = build_graph(_rows())
    # clique completa dentro do grupo (plano, faixa): C(4,2) = 6 arestas peso 1.0
    assert g["c1"]["c2"]["weight"] == 1.0
    assert g.number_of_edges() >= 6 * 2  # 2 grupos densos
    # não há aresta entre grupos totalmente diferentes de plano E faixa
    assert not g.has_edge("c1", "c5")


def test_detect_communities_separa_plano_e_faixa():
    g = build_graph(_rows())
    coms = detect_communities(g)
    assert len(coms) == 2
    ids = {frozenset(c) for c in coms}
    assert frozenset({"c1", "c2", "c3", "c4"}) in ids
    assert frozenset({"c5", "c6", "c7", "c8"}) in ids


def test_build_communities_artifact_shape():
    artifact = build_communities_artifact(_rows())
    coms = artifact["communities"]
    assert len(coms) == 2
    for c in coms:
        assert set(c) >= {"id", "title", "summary", "members", "stats"}
        assert c["stats"]["size"] == 4
        assert c["stats"]["pct_has_close"] == 75.0  # 3 de 4 com has_close=True
    # maior/igual primeiro (ambos N=4 aqui, mas o contrato é size desc)
    assert coms[0]["stats"]["size"] >= coms[1]["stats"]["size"]


def test_plano_ausente_vira_grupo_proprio():
    rows = [ConversaRow("c1", 25, True, ()), ConversaRow("c2", 27, True, ())]
    artifact = build_communities_artifact(rows)
    assert len(artifact["communities"]) == 1
    assert artifact["communities"][0]["stats"]["plano_dominante"] == "sem_plano_mencionado"


def test_grafo_vazio_nao_quebra():
    assert detect_communities(build_graph([])) == []
    assert build_communities_artifact([])["communities"] == []
