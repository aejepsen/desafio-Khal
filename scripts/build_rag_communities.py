#!/usr/bin/env python3
"""Gera services/svc-rag/models/communities.json (GraphRAG) a partir do Neo4j.

Lê o grafo de conversas `ganho` já ingerido no Neo4j (Conversation
-MENTIONS_PLAN-> Plano, has_close, idade — populado por
`scripts/neo4j_seed_dataset.py` / boot do agente), projeta em networkx e
roda detecção de comunidade (Louvain). O artefato gerado é servido pelo
`svc-rag` em `GET /v1/community/{id}` e usado no `/v1/search` (boost por
coerência de comunidade) — ver `rag_svc/community_builder.py` (lógica pura,
testada) e `rag_svc/community.py` (leitura do artefato).

Uso:
  NEO4J_URI=bolt://127.0.0.1:7687 python scripts/build_rag_communities.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/svc-rag/src"))

DEFAULT_OUT = ROOT / "services/svc-rag/models/communities.json"


def _fetch_rows(uri: str, user: str, password: str, outcome: str) -> list:
    from neo4j import GraphDatabase

    from rag_svc.community_builder import ConversaRow

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        driver.verify_connectivity()
        with driver.session() as s:
            result = s.run(
                """
                MATCH (c:Conversation)-[:HAS_OUTCOME]->(:CorpusAnchor {label: $outcome})
                OPTIONAL MATCH (c)-[:MENTIONS_PLAN]->(p:Plano)
                RETURN c.id AS id, c.idade AS idade, c.has_close AS has_close,
                       collect(p.plano_id) AS planos
                """,
                outcome=outcome,
            )
            rows = [
                ConversaRow(
                    id=r["id"],
                    idade=r["idade"],
                    has_close=bool(r["has_close"]),
                    planos=tuple(p for p in (r["planos"] or []) if p),
                )
                for r in result
            ]
    finally:
        driver.close()
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--uri", default=os.environ.get("NEO4J_URI", "bolt://127.0.0.1:7687"))
    ap.add_argument("--user", default=os.environ.get("NEO4J_USER", "neo4j"))
    ap.add_argument("--password", default=os.environ.get("NEO4J_PASSWORD", "namastex-graph"))
    ap.add_argument("--outcome", default="ganho")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    print(f"lendo grafo do Neo4j ({args.uri}) — outcome={args.outcome!r} …")
    rows = _fetch_rows(args.uri, args.user, args.password, args.outcome)
    if not rows:
        raise SystemExit(
            "0 conversas no Neo4j — rode scripts/neo4j_seed_dataset.py primeiro."
        )
    print(f"{len(rows)} conversas carregadas do grafo")

    from rag_svc.community_builder import build_communities_artifact

    artifact = build_communities_artifact(rows, seed=args.seed)
    coms = artifact["communities"]
    print(f"{len(coms)} comunidades detectadas (Louvain):")
    for c in coms:
        st = c["stats"]
        print(f"  [{c['id']}] {c['title']:24s} N={st['size']:<4d} "
              f"has_close={st['pct_has_close']}%")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
    print(f"escrito: {args.out}")


if __name__ == "__main__":
    main()
