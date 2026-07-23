"""Análise do dataset: grafo objeção -> outcome (o desafio convida a "entender
padrões de objeção"). Extrai objeções por heurística (sem LLM), constrói o grafo
e exporta insights que ANCORAM o design do agente e o few-shot dirigido.

Não é banco transacional: é camada de análise offline. Roda uma vez.
  python analysis/build_objecao_graph.py
"""
from __future__ import annotations

import collections
import pathlib
import re

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
PARQUET = ROOT.parent / "namastex-fde-challenge" / "dataset" / "conversations.parquet"
OUT = ROOT / "analysis"

# heurística de objeções (keywords no texto do lead) — barato, transparente
OBJ = {
    "preco": r"\bcar[oa]\b|pre[çc]o|desconto|valor.*alto|muito alto|parcel|cabe no bolso|barat",
    "cobertura": r"cobertura|cobre|cobrir|franquia|prote[çc]|o que inclui|terceiro",
    "prazo": r"prazo|demora|quando.*(sai|fica pronto)|car[êe]ncia|urg[êe]nc",
    "desconfianca": r"golpe|confi|receio|medo|voc[êe]s s[ãa]o|empresa s[ée]ria|real",
    "concorrente": r"outra|concorr|porto|azul|cotei|mais barato (em|na|no)|j[áa] tenho",
    "indeciso": r"vou pensar|depois|te aviso|falar com|n[ãa]o sei|talvez",
}


def objecoes(texto: str) -> list[str]:
    t = texto.lower()
    return [k for k, pat in OBJ.items() if re.search(pat, t)]


def main():
    df = pd.read_parquet(PARQUET)
    lead = df[df["sender_role"] == "lead"]
    convs = lead.groupby("conversation_id").agg(
        texto=("message_body", lambda s: " ".join(str(x) for x in s)),
    )
    outc = df.groupby("conversation_id")["conversation_outcome"].first()
    convs["outcome"] = outc
    convs["objecoes"] = convs["texto"].map(objecoes)

    # agregação objeção -> outcome
    obj_out: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for _, r in convs.iterrows():
        for o in r["objecoes"]:
            obj_out[o][r["outcome"]] += 1

    # insights ordenados por taxa de GANHO (o que converte)
    linhas = []
    for o, cnt in obj_out.items():
        tot = sum(cnt.values())
        ganho = cnt.get("ganho", 0)
        perdido = cnt.get("perdido", 0)
        taxa = round(100 * ganho / tot, 1) if tot else 0.0
        linhas.append((o, tot, taxa, ganho, perdido, dict(cnt)))
    linhas.sort(key=lambda x: -x[2])

    # grafo (graphml, se networkx disponível) + insights md
    try:
        import networkx as nx
        G = nx.DiGraph()
        for o, cnt in obj_out.items():
            for outcome, w in cnt.items():
                G.add_edge(f"objecao:{o}", f"outcome:{outcome}", weight=int(w))
        nx.write_graphml(G, OUT / "objecao_outcome.graphml")
        grafo_nota = f"grafo: {G.number_of_nodes()} nós, {G.number_of_edges()} arestas → `objecao_outcome.graphml`"
    except Exception as e:
        grafo_nota = f"(networkx ausente: {e})"

    md = ["# Padrões de objeção → outcome (análise do dataset)\n",
          f"Conversas analisadas: **{len(convs)}** · {grafo_nota}\n",
          "Objeção detectada por heurística no texto do lead. Ordenado por taxa de ganho.\n",
          "| objeção | conversas | % ganho | ganho | perdido |",
          "|---|---|---|---|---|"]
    for o, tot, taxa, g, p, _ in linhas:
        md.append(f"| {o} | {tot} | **{taxa}%** | {g} | {p} |")
    ganhos_com_obj = sum(1 for _, r in convs.iterrows() if r["objecoes"] and r["outcome"] == "ganho")
    md += ["",
           "## Descoberta central",
           f"- **Objeção de preço/concorrente/cobertura → ~0% de ganho.** Dos ganhos, apenas",
           f"  {ganhos_com_obj} tinham objeção detectada. Ganhos vêm de conversas de qualificação",
           "  limpa; objeção forte = sinal de perda/negociação arrastada.",
           "- ⚠️ **Ressalva (anti-Goodhart)**: dataset é SINTÉTICO (`generate_dataset.py`). O padrão",
           "  pode ser artefato da geração procedural — num cenário real, revalidar antes de decidir.",
           "",
           "## Como isso ancora o agente",
           "- **Design**: não há no histórico tática que CONVERTE objeção de preço → o agente não",
           "  deve prometer o que o dado não sustenta.",
           "- **HITL (critério ancorado em dado)**: objeção de preço/concorrente detectada = candidata",
           "  a **escalar cedo** pro humano — conversão histórica ~0, sem tática vencedora aprendível.",
           "- **Few-shot dirigido**: recuperar do RAG conversas de **ganho** (qualificação limpa) como",
           "  molde do caminho feliz; usar o grafo p/ marcar objeção → rota de escalada, não de few-shot.",
           ""]
    (OUT / "objecoes_insights.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    print(f"\n>> {OUT}/objecoes_insights.md + objecao_outcome.graphml")


if __name__ == "__main__":
    main()
