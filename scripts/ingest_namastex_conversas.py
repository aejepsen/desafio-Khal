#!/usr/bin/env python3
"""Ingere dataset/conversations.parquet no svc-rag (coleção namastex_conversas).

Uso:
  python scripts/ingest_namastex_conversas.py
  python scripts/ingest_namastex_conversas.py --outcome ganho --batch-size 50
  python scripts/ingest_namastex_conversas.py --all --limit 100

Requer: svc-rag + qdrant no ar (docker compose up --build qdrant svc-rag).
Auth: header X-Internal-Key = INTERNAL_KEY (default dev-namastex-key).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PARQUET = ROOT / "dataset" / "conversations.parquet"
DEFAULT_COLLECTION = "namastex_conversas"


def _load_rows(path: Path) -> list[dict]:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit("pyarrow necessário: pip install pyarrow") from exc
    table = pq.read_table(path)
    return table.to_pylist()


def build_documents(
    rows: list[dict],
    *,
    outcomes: set[str] | None,
    limit: int | None,
) -> list[dict]:
    by_conv: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_conv[str(row["conversation_id"])].append(row)

    docs: list[dict] = []
    for conv_id in sorted(by_conv):
        msgs = sorted(by_conv[conv_id], key=lambda r: int(r["message_index"]))
        outcome = str(msgs[0].get("conversation_outcome") or "")
        if outcomes is not None and outcome not in outcomes:
            continue

        idade = msgs[0].get("lead_idade_informada")
        veiculo = str(msgs[0].get("veiculo_texto") or "").strip()
        has_media = any(str(m.get("message_type")) != "text" for m in msgs)

        lines = [
            f"# Conversa {conv_id} · outcome={outcome}",
            f"- lead_idade_informada: {idade}",
            f"- veiculo_texto: {veiculo}",
            "",
        ]
        for m in msgs:
            role = m.get("sender_role")
            body = str(m.get("message_body") or "").strip()
            mtype = m.get("message_type")
            if mtype != "text":
                lines.append(f"[{role}|{mtype}] {body}")
            else:
                lines.append(f"[{role}] {body}")

        docs.append(
            {
                "id": conv_id,
                "text": "\n".join(lines),
                "metadata": {
                    "outcome": outcome,
                    "lead_idade_informada": idade,
                    "veiculo_texto": veiculo,
                    "n_messages": len(msgs),
                    "has_media": has_media,
                    "channel": str(msgs[0].get("channel") or "whatsapp"),
                },
            }
        )
        if limit is not None and len(docs) >= limit:
            break
    return docs


def _request(method: str, url: str, key: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Content-Type": "application/json",
            "X-Internal-Key": key,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(err)
        except json.JSONDecodeError:
            parsed = {"detail": err}
        return exc.code, parsed


def ingest_batches(
    docs: list[dict],
    *,
    base_url: str,
    key: str,
    collection: str,
    batch_size: int,
) -> dict:
    total_docs = 0
    total_chunks = 0
    total_skip = 0
    for i in range(0, len(docs), batch_size):
        batch = docs[i : i + batch_size]
        status, body = _request(
            "POST",
            f"{base_url.rstrip('/')}/v1/ingest",
            key,
            {"collection": collection, "documents": batch},
        )
        if status != 200:
            raise SystemExit(f"ingest falhou HTTP {status}: {body}")
        total_docs += int(body.get("n_documents", 0))
        total_chunks += int(body.get("n_chunks", 0))
        total_skip += int(body.get("n_skipped_idempotent", 0))
        print(
            f"batch {i // batch_size + 1}: docs={body.get('n_documents')} "
            f"chunks={body.get('n_chunks')} skipped={body.get('n_skipped_idempotent')}"
        )
    return {
        "n_documents": total_docs,
        "n_chunks": total_chunks,
        "n_skipped_idempotent": total_skip,
        "collection": collection,
    }


def smoke_search(base_url: str, key: str, collection: str, query: str, top_k: int = 3) -> None:
    status, body = _request(
        "POST",
        f"{base_url.rstrip('/')}/v1/search",
        key,
        {"query": query, "collection": collection, "top_k": top_k},
    )
    print(f"\nsearch {status!r} q={query!r}")
    if status != 200:
        print(body)
        return
    for hit in body.get("hits", []):
        meta = hit.get("metadata") or {}
        print(
            f"  score={hit.get('score'):.3f} doc={hit.get('doc_id')} "
            f"outcome={meta.get('outcome')} veiculo={meta.get('veiculo_texto')!r}"
        )
        preview = str(hit.get("text") or "").replace("\n", " ")[:120]
        print(f"    {preview}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parquet", type=Path, default=DEFAULT_PARQUET)
    parser.add_argument("--base-url", default=os.environ.get("RAG_URL", "http://127.0.0.1:8204"))
    parser.add_argument(
        "--internal-key",
        default=os.environ.get("INTERNAL_KEY", "dev-namastex-key"),
    )
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--batch-size", type=int, default=40)
    parser.add_argument(
        "--outcome",
        action="append",
        default=None,
        help="Filtra outcome (repetível). Default: ganho. Use --all para todos.",
    )
    parser.add_argument("--all", action="store_true", help="Ingere todos os outcomes")
    parser.add_argument("--limit", type=int, default=None, help="Máx. conversas")
    parser.add_argument("--skip-smoke", action="store_true")
    parser.add_argument(
        "--wait-s",
        type=int,
        default=int(os.environ.get("RAG_INGEST_WAIT_S", "0") or "0"),
        help="Espera svc-rag /health ficar ok (compose bootstrap).",
    )
    args = parser.parse_args()

    if not args.parquet.is_file():
        raise SystemExit(f"parquet não encontrado: {args.parquet}")

    outcomes: set[str] | None
    if args.all:
        outcomes = None
    elif args.outcome:
        outcomes = set(args.outcome)
    else:
        outcomes = {"ganho"}

    if args.wait_s > 0:
        import time

        deadline = time.time() + args.wait_s
        health_url = f"{args.base_url.rstrip('/')}/health"
        while True:
            try:
                with urllib.request.urlopen(health_url, timeout=5) as resp:
                    if resp.status == 200:
                        print("svc-rag ready")
                        break
            except Exception as exc:
                if time.time() >= deadline:
                    raise SystemExit(f"timeout esperando svc-rag: {exc}") from exc
                time.sleep(2)

    print(f"lendo {args.parquet} …")
    rows = _load_rows(args.parquet)
    docs = build_documents(rows, outcomes=outcomes, limit=args.limit)
    print(f"documentos a ingerir: {len(docs)} (outcomes={outcomes or 'ALL'})")

    # health
    try:
        with urllib.request.urlopen(f"{args.base_url.rstrip('/')}/health", timeout=30) as resp:
            health = json.loads(resp.read().decode())
            print("health:", health)
    except Exception as exc:
        raise SystemExit(f"svc-rag inacessível em {args.base_url}: {exc}") from exc

    summary = ingest_batches(
        docs,
        base_url=args.base_url,
        key=args.internal_key,
        collection=args.collection,
        batch_size=args.batch_size,
    )
    print("resumo:", summary)

    status, cols = _request("GET", f"{args.base_url.rstrip('/')}/v1/collections", args.internal_key)
    print("collections:", status, cols)

    if not args.skip_smoke:
        smoke_search(args.base_url, args.internal_key, args.collection, "seguro auto corolla idade")
        smoke_search(args.base_url, args.internal_key, args.collection, "cliente enviou documento CNH")


if __name__ == "__main__":
    main()
    sys.exit(0)
