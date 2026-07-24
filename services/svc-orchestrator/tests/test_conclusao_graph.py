"""Grafo formal NoConclusao + aresta FECHA_COM."""
from __future__ import annotations

from orch_svc.conclusao_graph import (
    aresta_fecha_com,
    export_grafo_catalogo,
    no_conclusao_de,
)
from orch_svc.cotacao_flow import DecisaoCotacao
from orch_svc.fechamento_index import resolver_fechamento
from orch_svc.resposta import redigir_resposta


def test_no_conclusao_e_aresta():
    d = DecisaoCotacao(
        "apresentar_cotacao",
        quote={
            "plano_id": "completo",
            "plano_nome": "Completo",
            "premio_mensal": 209.9,
            "franquia": 3000,
            "coberturas": ["colisao", "roubo", "furto"],
        },
    )
    no = no_conclusao_de(d, idade=42)
    assert no.acao == "apresentar_cotacao"
    assert no.persona == "meia_30_50"
    assert no.premio_mensal == 209.9
    assert "roubo" in no.coberturas
    e = aresta_fecha_com(no)
    assert e.rel == "FECHA_COM"
    assert e.dst == "apresentar_cotacao|meia_30_50"
    assert e.src == no.id


def test_resolver_usa_grafo():
    d = DecisaoCotacao(
        "apresentar_cotacao",
        quote={
            "plano_id": "completo",
            "plano_nome": "Completo",
            "premio_mensal": 209.9,
            "franquia": 3000,
            "coberturas": ["colisao", "vidros"],
        },
    )
    r = resolver_fechamento(d, idade=42)
    assert r.aresta.rel == "FECHA_COM"
    assert r.no.id.startswith("conclusao:")
    assert "209,90" in r.texto
    assert "compare" in r.texto.lower() or "compar" in r.texto.lower()


def test_redacao_expoe_conclusao_id():
    d = DecisaoCotacao(
        "apresentar_cotacao",
        quote={"plano_nome": "Essencial", "premio_mensal": 137.88, "franquia": 4500},
    )
    red = redigir_resposta(d, idade=35)
    assert red.conclusao_id
    assert "FECHA_COM" in red.aresta


def test_catalogo_exportavel():
    g = export_grafo_catalogo()
    assert g["engine"] == "in-process"
    assert any(n["label"] == "NoConclusao" for n in g["nodes"])
    assert any(e["rel"] == "FECHA_COM" for e in g["edges"])
