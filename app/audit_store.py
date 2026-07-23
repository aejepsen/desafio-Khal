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

    def model_performance_metrics(self) -> dict[str, Any]:
        """KPIs numéricos p/ scrape do svc-observability (desempenho agente/modelo).

        Contadores + taxas 0–1 derivados do audit SQLite (sem PII).
        """
        with self._lock, self._connect() as conn:
            turns_total = int(
                conn.execute("SELECT COUNT(*) FROM audit_turn").fetchone()[0]
            )
            conversations_total = int(
                conn.execute(
                    "SELECT COUNT(DISTINCT conversation_id) FROM audit_turn"
                ).fetchone()[0]
            )
            escalate_turns = int(
                conn.execute(
                    "SELECT COUNT(*) FROM audit_turn WHERE escalate = 1"
                ).fetchone()[0]
            )
            by_acao = {
                str(r["acao"] or "unknown"): int(r["n"])
                for r in conn.execute(
                    """
                    SELECT acao, COUNT(*) AS n FROM audit_turn
                    GROUP BY acao
                    """
                ).fetchall()
            }
            by_fonte = {
                str(r["fonte_resposta"] or "unknown"): int(r["n"])
                for r in conn.execute(
                    """
                    SELECT fonte_resposta, COUNT(*) AS n FROM audit_turn
                    GROUP BY fonte_resposta
                    """
                ).fetchall()
            }
            midia_enriched = int(
                conn.execute(
                    """
                    SELECT COUNT(*) FROM audit_event
                    WHERE step = 'midia' AND status = 'enriched'
                    """
                ).fetchone()[0]
            )
            resposta_llm = int(by_fonte.get("llm", 0))
            resposta_fallback = int(by_fonte.get("llm_fallback", 0))
            apresentar = int(by_acao.get("apresentar_cotacao", 0))
            emitir = int(by_acao.get("emitir_apolice", 0))
            escalar = int(by_acao.get("escalar_humano", 0))

        def _rate(num: int, den: int) -> float:
            return round(num / den, 4) if den else 0.0

        return {
            "source": "live",
            "turns_total": turns_total,
            "conversations_total": conversations_total,
            "escalate_turns_total": escalate_turns,
            "acao_apresentar_cotacao_total": apresentar,
            "acao_emitir_apolice_total": emitir,
            "acao_escalar_humano_total": escalar,
            "acao_pedir_dado_total": int(by_acao.get("pedir_dado", 0)),
            "resposta_llm_total": resposta_llm,
            "resposta_llm_fallback_total": resposta_fallback,
            "resposta_template_total": int(by_fonte.get("template", 0)),
            "midia_enriched_total": midia_enriched,
            "hitl_rate": _rate(escalate_turns, turns_total),
            "llm_redacao_rate": _rate(resposta_llm, turns_total),
            "llm_fallback_rate": _rate(resposta_fallback, turns_total),
            "cotacao_apresentada_rate": _rate(apresentar, turns_total),
            "fechamento_sobre_cotacao_rate": _rate(emitir, apresentar),
            "escala_sobre_turnos_rate": _rate(escalar, turns_total),
        }
