"""Testes do AuditStore SQLite."""
from __future__ import annotations

from app.audit_store import AuditStore


def test_record_and_get(tmp_path):
    db = AuditStore(tmp_path / "audit.db")
    payload = {
        "type": "audit.chat",
        "conversation_id": "c1",
        "turno": 1,
        "acao": "apresentar_cotacao",
        "escalate": False,
        "premio_mensal": 137.88,
        "fonte_resposta": "llm",
        "lead_mascarado": "CEP [CEP]",
        "pii": "masked",
    }
    eventos = [
        {"step": "turno", "status": "1", "detail": {}},
        {"step": "decide", "status": "apresentar_cotacao", "detail": {"premio_mensal": 137.88}},
    ]
    row_id = db.record_turn(
        conversation_id="c1", turno=1, payload=payload, eventos=eventos
    )
    assert row_id >= 1
    got = db.get_conversation("c1")
    assert got["conversation_id"] == "c1"
    assert len(got["turns"]) == 1
    assert got["turns"][0]["audit"]["premio_mensal"] == 137.88
    assert got["eventos"][1]["step"] == "decide"
    assert got["eventos"][1]["status"] == "apresentar_cotacao"
