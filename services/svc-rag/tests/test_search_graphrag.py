"""Testes do enriquecimento GraphRAG no /v1/search (anotação + re-rank por comunidade)."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from rag_svc.app import State, _annotate_and_rerank_by_community, create_app
from rag_svc.config import Settings
from rag_svc.embedder import FakeEmbedder
from rag_svc.store import Hit as StoreHit
from rag_svc.store import InMemoryStore

ARTIFACT = {
    "communities": [
        {"id": "0", "title": "senior · premium", "summary": "s0", "members": ["a", "b"]},
        {"id": "1", "title": "jovem · essencial", "summary": "s1", "members": ["c"]},
    ]
}

DOCS = {
    "collection": "conv",
    "documents": [
        {"id": "a", "text": "conversa senior premium um"},
        {"id": "b", "text": "conversa senior premium dois"},
        {"id": "c", "text": "conversa jovem essencial"},
    ],
}


def _client(tmp_path: Path, *, graphrag_enabled: bool) -> TestClient:
    (tmp_path / "communities.json").write_text(json.dumps(ARTIFACT))
    settings = Settings(
        internal_key="k", vector_store="memory", rate_limit_per_min=100000,
        models_dir=str(tmp_path), graphrag_enabled=graphrag_enabled,
    )
    state = State(settings, FakeEmbedder(), InMemoryStore())
    return TestClient(create_app(settings=settings, state=state))


def test_hits_anotados_com_comunidade(tmp_path: Path) -> None:
    c = _client(tmp_path, graphrag_enabled=True)
    headers = {"X-Internal-Key": "k"}
    c.post("/v1/ingest", json=DOCS, headers=headers)
    r = c.post(
        "/v1/search",
        json={"query": "conversa", "collection": "conv", "top_k": 3},
        headers=headers,
    )
    hits = {h["doc_id"]: h for h in r.json()["hits"]}
    assert hits["a"]["community_id"] == "0"
    assert hits["a"]["community_title"] == "senior · premium"
    assert hits["c"]["community_id"] == "1"


def test_sem_flag_nao_anota(tmp_path: Path) -> None:
    c = _client(tmp_path, graphrag_enabled=False)
    headers = {"X-Internal-Key": "k"}
    c.post("/v1/ingest", json=DOCS, headers=headers)
    r = c.post(
        "/v1/search", json={"query": "conversa", "collection": "conv"}, headers=headers
    )
    assert all(h["community_id"] is None for h in r.json()["hits"])


def test_health_reporta_graphrag_enabled(tmp_path: Path) -> None:
    c = _client(tmp_path, graphrag_enabled=True)
    assert c.get("/health").json()["deps"]["graphrag"] == "enabled"


def test_rerank_favorece_comunidade_dominante(tmp_path: Path) -> None:
    """Unit direto na função de rerank: score bruto NÃO é sobrescrito, só a ordem
    muda — hit fora da comunidade dominante mas com score maior perde posição
    pro hit da comunidade dominante dentro da margem do boost (0.05)."""
    (tmp_path / "communities.json").write_text(json.dumps(ARTIFACT))
    settings = Settings(
        internal_key="k", vector_store="memory", rate_limit_per_min=100000,
        models_dir=str(tmp_path), graphrag_enabled=True,
    )
    st = State(settings, FakeEmbedder(), InMemoryStore())

    raw_hits = [
        StoreHit(chunk_id="ch1", doc_id="c", text="jovem essencial", score=0.90, metadata={}),
        StoreHit(chunk_id="ch2", doc_id="a", text="senior premium 1", score=0.88, metadata={}),
        StoreHit(chunk_id="ch3", doc_id="b", text="senior premium 2", score=0.87, metadata={}),
    ]
    out = _annotate_and_rerank_by_community(raw_hits, st)

    # comunidade "0" (a, b) é dominante (2 de 3) -> a sobe na frente de c mesmo
    # com score vetorial menor (0.88 + 0.05 = 0.93 > 0.90).
    assert [h.doc_id for h in out] == ["a", "b", "c"]
    # score reportado continua o valor vetorial ORIGINAL, sem boost embutido.
    assert out[0].score == 0.88


def test_rerank_sem_artefato_preserva_ordem_vetorial(tmp_path: Path) -> None:
    settings = Settings(
        internal_key="k", vector_store="memory", rate_limit_per_min=100000,
        models_dir=str(tmp_path), graphrag_enabled=True,  # sem communities.json
    )
    st = State(settings, FakeEmbedder(), InMemoryStore())
    raw_hits = [
        StoreHit(chunk_id="ch1", doc_id="x", text="t", score=0.9, metadata={}),
        StoreHit(chunk_id="ch2", doc_id="y", text="t", score=0.5, metadata={}),
    ]
    out = _annotate_and_rerank_by_community(raw_hits, st)
    assert [h.doc_id for h in out] == ["x", "y"]
    assert all(h.community_id is None for h in out)
