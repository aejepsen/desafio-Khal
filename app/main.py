"""Entrypoint do agente de cotação (Namastex FDE).

Amarra o domínio (domains/seguro_auto) + a orquestração (orch_svc) numa API FastAPI.
POST /chat  → run_conversa (sanitize→qualifica→[objeção]→cota resiliente→decide) + log.
GET  /health.

Rodar: uvicorn app.main:app --port 8100   (QUOTE_URL aponta pro quote-service)
"""
from __future__ import annotations

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "domains"))
sys.path.insert(0, str(ROOT / "services/svc-orchestrator/src"))

from fastapi import FastAPI  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from seguro_auto.build import build_quote_request  # noqa: E402
from orch_svc.agente_cotacao import run_conversa  # noqa: E402
from orch_svc.persona import persona_por_idade  # noqa: E402
from orch_svc.quote_client import ResilientQuoteClient  # noqa: E402

QUOTE_URL = os.environ.get("QUOTE_URL", "http://localhost:8000")
RAG_URL = os.environ.get("RAG_URL")
INTERNAL_KEY = os.environ.get("INTERNAL_KEY", "")

app = FastAPI(title="agente-cotacao-namastex", version="1.0.0")


class ChatIn(BaseModel):
    mensagens: list[str]
    idade: int | None = None
    tentativas_objecao: int = 0
    conversation_id: str | None = None


def _build_fn(slots):
    return build_quote_request(slots, verified=True)


def _rag():
    if not RAG_URL:
        return None
    from orch_svc.clients import HttpRag
    return HttpRag(RAG_URL, INTERNAL_KEY, "", 10.0)


@app.get("/health")
def health():
    return {"status": "ok", "quote_url": QUOTE_URL, "rag": bool(RAG_URL)}


@app.post("/chat")
def chat(inp: ChatIn):
    ex = run_conversa(inp.mensagens, _build_fn,
                      ResilientQuoteClient(base_url=QUOTE_URL), rag=_rag(),
                      tentativas_objecao=inp.tentativas_objecao,
                      conversation_id=inp.conversation_id)
    d = ex.decisao
    return {
        "conversation_id": ex.conversation_id,
        "persona": persona_por_idade(inp.idade).faixa,
        "decisao": {"acao": d.acao, "escalate": d.escalate, "motivos": d.motivos,
                    "faltam": d.faltam, "quote": d.quote, "exemplos": d.exemplos},
        "eventos": [{"step": e.step, "status": e.status, "detail": e.detail} for e in ex.eventos],
    }
