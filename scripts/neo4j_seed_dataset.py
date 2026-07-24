"""Ingere conversations.parquet no Neo4j (grafo do corpus / pesquisa semântica).

  NEO4J_URI=bolt://127.0.0.1:7687 python scripts/neo4j_seed_dataset.py --limit 500
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "services/svc-orchestrator/src"))

DEFAULT_PARQUET = ROOT / "dataset" / "conversations.parquet"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", type=Path, default=DEFAULT_PARQUET)
    ap.add_argument("--outcome", action="append", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--uri", default=os.environ.get("NEO4J_URI", "bolt://127.0.0.1:7687"))
    ap.add_argument("--user", default=os.environ.get("NEO4J_USER", "neo4j"))
    ap.add_argument("--password", default=os.environ.get("NEO4J_PASSWORD", "namastex-graph"))
    args = ap.parse_args()

    from app.dataset_graph import build_conversation_nodes, load_parquet_rows
    from app.neo4j_graph import Neo4jGraph

    outcomes = None if args.all else set(args.outcome or ["ganho"])
    convs = build_conversation_nodes(
        load_parquet_rows(args.parquet), outcomes=outcomes, limit=args.limit
    )
    g = Neo4jGraph(uri=args.uri, user=args.user, password=args.password)
    if not g.connect():
        raise SystemExit("Neo4j offline")
    g.seed_fechamento_catalog()
    g.seed_dataset_anchors()
    tat = g.seed_taticas_objecao()
    n = g.ingest_conversations(convs)
    print(f"OK ingest {n} conversas (filtro={outcomes or 'all'}) → {args.uri}")
    print(f"OK táticas: {tat['objecoes']} objeções, {tat['taticas']} táticas")


if __name__ == "__main__":
    main()
