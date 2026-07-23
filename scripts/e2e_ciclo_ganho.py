#!/usr/bin/env python3
"""E2E ao vivo: lead → qualifica → cota → aceita → emitir_apolice (contratado).

Uso:
  python scripts/e2e_ciclo_ganho.py
  CHAT_URL=http://127.0.0.1:8100/chat python scripts/e2e_ciclo_ganho.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

CHAT_URL = os.environ.get("CHAT_URL", "http://127.0.0.1:8100/chat")
CID = os.environ.get("CID", f"e2e-ciclo-{int(time.time())}")

# Multi-turno espelhando conversa ganho do dataset (coleta progressiva → aceite).
# idade só no texto (não injeta no body) — exercita extração real.
TURNOS = [
    "Oi, quero cotar seguro do meu carro",
    "Tenho 42 anos",
    "É um Corolla 2020",
    "CEP 01310-100, quero o plano completo",
    "fechado! pode emitir",
]


def post_chat(mensagem: str) -> dict:
    body: dict = {"conversation_id": CID, "mensagem": mensagem}
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        CHAT_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def main() -> int:
    print(f"# E2E ciclo ganho\nCID={CID}\nURL={CHAT_URL}\n")
    rows: list[dict] = []
    for i, msg in enumerate(TURNOS, 1):
        try:
            out = post_chat(msg)
        except urllib.error.URLError as e:
            print(f"FALHA turno {i}: {e}", file=sys.stderr)
            return 2
        acao = (out.get("decisao") or {}).get("acao")
        estagio = out.get("estagio")
        premio = (out.get("decisao") or {}).get("quote") or {}
        premio = premio.get("premio_mensal") if isinstance(premio, dict) else None
        exemplos_n = len((out.get("decisao") or {}).get("exemplos") or [])
        slots = {k: out.get("slots", {}).get(k) for k in ("idade", "veiculo_ano", "plano_id", "cep")}
        row = {
            "turno": i,
            "lead": msg,
            "acao": acao,
            "estagio": estagio,
            "premio_mensal": premio,
            "exemplos_n": exemplos_n,
            "slots": slots,
            "mensagem": (out.get("mensagem") or "")[:280],
            "faltam": (out.get("decisao") or {}).get("faltam") or [],
            "motivos": (out.get("decisao") or {}).get("motivos") or [],
        }
        rows.append(row)
        print(
            f"T{i} [{estagio}/{acao}] premio={premio} exemplos={exemplos_n} slots={slots}\n"
            f"  lead: {msg}\n"
            f"  agent: {row['mensagem']}\n"
        )

    last = rows[-1]
    ok = last["acao"] == "emitir_apolice" and last["estagio"] == "contratado"
    cotou = any(r["acao"] == "apresentar_cotacao" for r in rows)
    # não pode inventar plano/cep antes do lead informar
    early = rows[0]["slots"]
    if early.get("plano_id") or early.get("cep"):
        print("FAIL: alucinação de slots no T1", early, file=sys.stderr)
        return 1
    print("## veredicto")
    print(f"cotou={cotou} fechou={ok}")
    if not (cotou and ok):
        print("FAIL: ciclo incompleto", file=sys.stderr)
        return 1
    print("PASS: qualifica → cota → aceite → emitir_apolice")
    out_path = os.environ.get("E2E_OUT", "")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"cid": CID, "rows": rows, "pass": True}, f, ensure_ascii=False, indent=2)
        print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
