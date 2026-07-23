from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

# Fonte canônica: mesmo arquivo do quote-service (não duplicar regras).
_DEFAULT_PLANS = (
    Path(__file__).resolve().parents[2] / "quote-service" / "data" / "plans.json"
)


def default_plans_path() -> Path:
    return _DEFAULT_PLANS


@lru_cache(maxsize=4)
def load_plans(path: str | None = None) -> dict[str, Any]:
    p = Path(path) if path else _DEFAULT_PLANS
    return json.loads(p.read_text(encoding="utf-8"))


def plan_ids(plans: dict[str, Any]) -> set[str]:
    return {p["id"] for p in plans["planos"]}


def clear_plans_cache() -> None:
    load_plans.cache_clear()
