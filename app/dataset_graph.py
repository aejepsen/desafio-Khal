"""Helpers para graphificar conversations.parquet → Neo4j."""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

_PLANO = re.compile(r"\b(essencial|completo|premium)\b", re.I)
_CLOSE = re.compile(
    r"\b(fechado|boleto|apolice|apólice|pode emitir|vamos nessa|maravilha)\b",
    re.I,
)


def load_parquet_rows(path: Path) -> list[dict]:
    import pyarrow.parquet as pq

    return pq.read_table(path).to_pylist()


def build_conversation_nodes(
    rows: list[dict],
    *,
    outcomes: set[str] | None,
    limit: int | None,
) -> list[dict[str, Any]]:
    by: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by[str(r["conversation_id"])].append(r)

    out: list[dict[str, Any]] = []
    for cid in sorted(by):
        msgs = sorted(by[cid], key=lambda m: int(m["message_index"]))
        outcome = str(msgs[0].get("conversation_outcome") or "")
        if outcomes is not None and outcome not in outcomes:
            continue
        body = " ".join(str(m.get("message_body") or "") for m in msgs)
        planos = sorted({m.group(1).lower() for m in _PLANO.finditer(body)})
        out.append(
            {
                "id": cid,
                "outcome": outcome,
                "idade": msgs[0].get("lead_idade_informada"),
                "veiculo": str(msgs[0].get("veiculo_texto") or ""),
                "n_msgs": len(msgs),
                "planos": planos,
                "has_close": bool(_CLOSE.search(body)),
                "has_media": any(str(m.get("message_type")) != "text" for m in msgs),
            }
        )
        if limit is not None and len(out) >= limit:
            break
    return out
