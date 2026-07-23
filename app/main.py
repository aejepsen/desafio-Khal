"""Entrypoint do agente de cotação (Namastex FDE).

Amarra o domínio (domains/seguro_auto) + a orquestração (orch_svc) numa API FastAPI.
POST /chat  → run_turno + redação LLM + audit log (lead ↔ resposta).
GET  /health.

Rodar: uvicorn app.main:app --port 8100   (QUOTE_URL aponta pro quote-service)
"""
from __future__ import annotations

import json
import logging
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "domains"))
sys.path.insert(0, str(ROOT / "services/svc-orchestrator/src"))

from fastapi import FastAPI  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402

from seguro_auto.build import build_quote_request  # noqa: E402
from orch_svc.persona import persona_por_idade  # noqa: E402
from orch_svc.quote_client import ResilientQuoteClient  # noqa: E402
from orch_svc.thread import ThreadStore, run_turno  # noqa: E402

STORE = ThreadStore()  # estado por conversa (in-memory; Redis/DB em produção)

QUOTE_URL = os.environ.get("QUOTE_URL", "http://localhost:8000")
RAG_URL = os.environ.get("RAG_URL")
INFERENCE_URL = os.environ.get("INFERENCE_URL")
GUARDRAILS_URL = os.environ.get("GUARDRAILS_URL")
MEDIA_ASR_URL = os.environ.get("MEDIA_ASR_URL")   # opcional — Whisper etc.
MEDIA_OCR_URL = os.environ.get("MEDIA_OCR_URL")   # opcional — Tesseract/Paddle etc.
INTERNAL_KEY = os.environ.get("INTERNAL_KEY", "")
INFERENCE_MODEL = os.environ.get("INFERENCE_MODEL", "default-model")
AUDIT_DB_PATH = os.environ.get("AUDIT_DB_PATH", str(ROOT / "data" / "audit.db"))

# Auditoria / governança / curadoria — JSON em stdout + SQLite por conversation_id.
logging.basicConfig(level=logging.INFO, format="%(message)s")
AUDIT = logging.getLogger("audit.chat")
AUDIT.setLevel(logging.INFO)

from app.audit_store import AuditStore  # noqa: E402
from app.neo4j_graph import boot_neo4j, get_neo4j  # noqa: E402

AUDIT_STORE = AuditStore(AUDIT_DB_PATH)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    boot = boot_neo4j()
    logging.getLogger("neo4j.graph").info("boot neo4j: %s", boot)
    yield
    get_neo4j().close()


app = FastAPI(title="agente-cotacao-namastex", version="1.0.0", lifespan=_lifespan)


class ChatIn(BaseModel):
    conversation_id: str          # mantém o estado da conversa entre turnos
    mensagem: str                 # a mensagem do lead NESTE turno
    idade: int | None = None
    message_type: str | None = None  # text|audio|image|document
    media_url: str | None = None     # URL do arquivo p/ ASR/OCR (se MEDIA_*_URL setado)


def _build_fn(slots):
    return build_quote_request(slots, verified=True)


def _rag():
    if not RAG_URL:
        return None
    from orch_svc.clients import HttpRag
    return HttpRag(RAG_URL, INTERNAL_KEY, "", 10.0)


def _guardrails():
    if not GUARDRAILS_URL:
        return None
    from orch_svc.clients import HttpGuardrails
    return HttpGuardrails(GUARDRAILS_URL, INTERNAL_KEY, "", 10.0)


def _extrair():
    """Heurística + LLM opcional (INFERENCE_URL). Falha de LLM degrada gracioso."""
    from orch_svc.extracao import fazer_extrator
    if not INFERENCE_URL:
        return fazer_extrator(None)
    from orch_svc.clients import HttpInference
    return fazer_extrator(HttpInference(INFERENCE_URL, INTERNAL_KEY, INFERENCE_MODEL, 30.0))


def _inference():
    if not INFERENCE_URL:
        return None
    from orch_svc.clients import HttpInference
    return HttpInference(INFERENCE_URL, INTERNAL_KEY, INFERENCE_MODEL, 30.0)


def _framework_dos_eventos(eventos) -> str | None:
    for e in eventos:
        if e.step == "objecao":
            return (e.detail or {}).get("framework")
    return None


def _media_enricher():
    """Plug tear-free: só instancia se MEDIA_ASR_URL e/ou MEDIA_OCR_URL existirem."""
    if not (MEDIA_ASR_URL or MEDIA_OCR_URL):
        return None
    from orch_svc.midia import HttpMediaEnricher
    return HttpMediaEnricher(
        asr_url=MEDIA_ASR_URL,
        ocr_url=MEDIA_OCR_URL,
        key=INTERNAL_KEY,
        timeout_s=60.0,
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "quote_url": QUOTE_URL,
        "rag": bool(RAG_URL),
        "inference": bool(INFERENCE_URL),
        "guardrails": bool(GUARDRAILS_URL),
        "media_asr": bool(MEDIA_ASR_URL),
        "media_ocr": bool(MEDIA_OCR_URL),
        "audit_db": str(AUDIT_STORE.path),
        "neo4j": get_neo4j().health(),
    }


@app.get("/audit/{conversation_id}")
def audit_by_conversation(conversation_id: str):
    """Trilha persistida (SQLite) — o que foi gravado em audit.chat, por id."""
    return AUDIT_STORE.get_conversation(conversation_id)


@app.get("/graph/fechamento")
def graph_fechamento():
    """Catálogo do grafo de conclusão (nós/arestas) — também materializado no Neo4j."""
    from orch_svc.conclusao_graph import export_grafo_catalogo
    return export_grafo_catalogo()


@app.get("/graph/neo4j")
def graph_neo4j_status():
    return get_neo4j().health()


@app.get("/graph/neo4j/search")
def graph_neo4j_search(q: str = "apresentar_cotacao", limit: int = 5):
    """Pesquisa semântica leve no grafo (caminhos a partir de id/ação)."""
    return {"query": q, "paths": get_neo4j().path_fechamento(q, limit=limit)}


@app.post("/graph/neo4j/seed")
def graph_neo4j_seed():
    g = get_neo4j()
    if not g.connect():
        return {"status": "down"}
    return {
        "status": "ok",
        "seed": g.seed_fechamento_catalog(),
        "anchors": g.seed_dataset_anchors(),
    }


@app.post("/graph/neo4j/seed-dataset")
def graph_neo4j_seed_dataset(
    outcome: str = "ganho",
    limit: int = 500,
    all_outcomes: bool = False,
):
    """Popula Neo4j a partir de dataset/conversations.parquet (pesquisa semântica)."""
    from pathlib import Path

    from app.dataset_graph import build_conversation_nodes, load_parquet_rows

    g = get_neo4j()
    if not g.connect():
        return {"status": "down"}
    path = Path("/app/dataset/conversations.parquet")
    if not path.exists():
        path = ROOT / "dataset" / "conversations.parquet"
    if not path.exists():
        return {"status": "error", "detail": "parquet não encontrado"}
    rows = load_parquet_rows(path)
    outcomes = None if all_outcomes else {outcome}
    convs = build_conversation_nodes(rows, outcomes=outcomes, limit=limit)
    g.seed_fechamento_catalog()
    g.seed_dataset_anchors()
    n = g.ingest_conversations(convs)
    return {
        "status": "ok",
        "ingested": n,
        "outcomes": list(outcomes) if outcomes else "all",
        "neo4j": g.health(),
    }


@app.get("/graph/neo4j/closes")
def graph_neo4j_closes(plano: str | None = None, limit: int = 5):
    """Conversas ganho com fechamento (boleto/apólice) — espelho do dataset."""
    return {
        "plano": plano,
        "closes": get_neo4j().search_similar_closes(plano_id=plano, limit=limit),
    }


def _graph_examples(plano_id: str | None) -> list[str]:
    """Candidatos Neo4j para o re-rank (closes ganho + plano)."""
    closes = get_neo4j().search_similar_closes(plano_id=plano_id, limit=5)
    out: list[str] = []
    for c in closes:
        out.append(
            "outcome=ganho has_close=true "
            f"plano={plano_id or 'n/d'} "
            f"conversa=#{c.get('id')} veiculo={c.get('veiculo')} "
            f"idade={c.get('idade')} — fechado boleto apólice"
        )
    return out


@app.post("/chat")
def chat(inp: ChatIn):
    from orch_svc.agente_cotacao import mascarar_pii
    from orch_svc.resposta import redigir_resposta

    state = STORE.get(inp.conversation_id)
    if inp.idade is not None:
        state.slots.setdefault("idade", inp.idade)
    ex, state = run_turno(
        inp.mensagem,
        state,
        _build_fn,
        ResilientQuoteClient(base_url=QUOTE_URL),
        rag=_rag(),
        extrair=_extrair(),
        guardrails=_guardrails(),
        message_type=inp.message_type,
        media_url=inp.media_url,
        media_enricher=_media_enricher(),
        graph_examples=_graph_examples,
    )
    STORE.save(state)
    d = ex.decisao
    idade = state.slots.get("idade") or inp.idade
    red = redigir_resposta(
        d,
        idade=idade,
        mensagem_lead=inp.mensagem,
        framework=_framework_dos_eventos(ex.eventos),
        inference=_inference(),
        trace=ex.conversation_id,
    )
    # PII SEMPRE ativa em qualquer registro de log / trilha de auditoria.
    lead_mascarado = mascarar_pii(inp.mensagem)
    rascunho_log = mascarar_pii(red.rascunho)
    mensagem_log = mascarar_pii(red.texto)
    slots_log = _slots_para_log(state.slots)
    eventos = [{"step": e.step, "status": e.status, "detail": e.detail} for e in ex.eventos]
    eventos.append({
        "step": "resposta",
        "status": red.fonte,
        "detail": {
            "lead_mascarado": lead_mascarado,
            "rascunho": rascunho_log,
            "mensagem": mensagem_log,
            "fonte": red.fonte,
            "index_key": red.index_key,
            "cta": red.cta,
            "conclusao_id": red.conclusao_id,
            "aresta": red.aresta,
            "model": INFERENCE_MODEL if red.fonte == "llm" else None,
            "pii": "masked",
        },
    })
    audit_payload = {
        "type": "audit.chat",
        "conversation_id": ex.conversation_id,
        "turno": state.turnos,
        "estagio": state.estagio,
        "persona": persona_por_idade(idade).faixa,
        "lead_mascarado": lead_mascarado,
        "acao": d.acao,
        "escalate": d.escalate,
        "motivos": d.motivos,
        "slots": slots_log,
        "premio_mensal": (d.quote or {}).get("premio_mensal") if d.quote else None,
        "rascunho": rascunho_log,
        "mensagem_agente": mensagem_log,
        "fonte_resposta": red.fonte,
        "index_key": red.index_key,
        "cta": red.cta,
        "conclusao_id": red.conclusao_id,
        "aresta": red.aresta,
        "model": INFERENCE_MODEL if red.fonte == "llm" else None,
        "pii": "masked",
    }
    AUDIT.info(json.dumps(audit_payload, ensure_ascii=False))
    # Persistência consultável (mesmo conteúdo do audit.chat + eventos mascarados).
    eventos_log = _eventos_para_log(eventos)
    turn_row_id = AUDIT_STORE.record_turn(
        conversation_id=ex.conversation_id,
        turno=state.turnos,
        payload=audit_payload,
        eventos=eventos_log,
    )
    audit_payload["audit_turn_id"] = turn_row_id
    return {
        "conversation_id": ex.conversation_id,
        "turno": state.turnos,
        "estagio": state.estagio,
        "persona": persona_por_idade(idade).faixa,
        "mensagem": red.texto,
        "slots": state.slots,
        "decisao": {"acao": d.acao, "escalate": d.escalate, "motivos": d.motivos,
                    "faltam": d.faltam, "quote": d.quote, "exemplos": d.exemplos},
        "eventos": eventos,
        "audit_turn_id": turn_row_id,
    }


def _slots_para_log(slots: dict) -> dict:
    """Cópia dos slots com PII mascarada (CEP/CPF/e-mail/placa) — só p/ log."""
    from orch_svc.agente_cotacao import mascarar_pii

    out: dict = {}
    for k, v in (slots or {}).items():
        if k == "cep" and v not in (None, ""):
            out[k] = "[CEP]"
        elif isinstance(v, str):
            out[k] = mascarar_pii(v)
        else:
            out[k] = v
    return out


def _eventos_para_log(eventos: list[dict]) -> list[dict]:
    """Cópia dos eventos com PII mascarada antes de gravar no SQLite."""
    from orch_svc.agente_cotacao import mascarar_pii

    out: list[dict] = []
    for e in eventos:
        detail = dict(e.get("detail") or {})
        for key in ("slots", "slots_acumulados"):
            if isinstance(detail.get(key), dict):
                detail[key] = _slots_para_log(detail[key])
        for key, val in list(detail.items()):
            if isinstance(val, str):
                detail[key] = mascarar_pii(val)
        out.append({
            "step": e.get("step"),
            "status": e.get("status"),
            "detail": detail,
        })
    return out
