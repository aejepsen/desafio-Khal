"""Store SQLite da trilha audit.chat — consulta por conversation_id.

PII já chega mascarada do /chat. Persistência local (volume Docker).
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuditStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS audit_turn (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  conversation_id TEXT NOT NULL,
                  turno INTEGER NOT NULL,
                  acao TEXT,
                  escalate INTEGER,
                  premio_mensal REAL,
                  fonte_resposta TEXT,
                  created_at TEXT NOT NULL,
                  payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_audit_turn_conv
                  ON audit_turn(conversation_id, turno);

                CREATE TABLE IF NOT EXISTS audit_event (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  conversation_id TEXT NOT NULL,
                  turno INTEGER NOT NULL,
                  step TEXT NOT NULL,
                  status TEXT NOT NULL,
                  detail_json TEXT,
                  created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_audit_event_conv
                  ON audit_event(conversation_id, turno, id);
                """
            )

    def record_turn(
        self,
        *,
        conversation_id: str,
        turno: int,
        payload: dict[str, Any],
        eventos: list[dict[str, Any]],
    ) -> int:
        """Grava o audit.chat + cada evento (step/status). Retorna id do turno."""
        created = _utc_now()
        payload_json = json.dumps(payload, ensure_ascii=False)
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO audit_turn(
                  conversation_id, turno, acao, escalate, premio_mensal,
                  fonte_resposta, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    turno,
                    payload.get("acao"),
                    1 if payload.get("escalate") else 0,
                    payload.get("premio_mensal"),
                    payload.get("fonte_resposta"),
                    created,
                    payload_json,
                ),
            )
            turn_id = int(cur.lastrowid)
            for ev in eventos:
                conn.execute(
                    """
                    INSERT INTO audit_event(
                      conversation_id, turno, step, status, detail_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        conversation_id,
                        turno,
                        ev.get("step"),
                        ev.get("status"),
                        json.dumps(ev.get("detail") or {}, ensure_ascii=False),
                        created,
                    ),
                )
            conn.commit()
        return turn_id

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        with self._lock, self._connect() as conn:
            turns = conn.execute(
                """
                SELECT id, conversation_id, turno, acao, escalate, premio_mensal,
                       fonte_resposta, created_at, payload_json
                FROM audit_turn
                WHERE conversation_id = ?
                ORDER BY turno ASC, id ASC
                """,
                (conversation_id,),
            ).fetchall()
            events = conn.execute(
                """
                SELECT id, conversation_id, turno, step, status, detail_json, created_at
                FROM audit_event
                WHERE conversation_id = ?
                ORDER BY turno ASC, id ASC
                """,
                (conversation_id,),
            ).fetchall()
        return {
            "conversation_id": conversation_id,
            "turns": [
                {
                    "id": r["id"],
                    "turno": r["turno"],
                    "acao": r["acao"],
                    "escalate": bool(r["escalate"]),
                    "premio_mensal": r["premio_mensal"],
                    "fonte_resposta": r["fonte_resposta"],
                    "created_at": r["created_at"],
                    "audit": json.loads(r["payload_json"]),
                }
                for r in turns
            ],
            "eventos": [
                {
                    "id": r["id"],
                    "turno": r["turno"],
                    "step": r["step"],
                    "status": r["status"],
                    "detail": json.loads(r["detail_json"] or "{}"),
                    "created_at": r["created_at"],
                }
                for r in events
            ],
        }
