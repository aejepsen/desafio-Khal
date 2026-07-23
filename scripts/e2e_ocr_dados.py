#!/usr/bin/env python3
"""Smoke: imagem com dados → OCR → slots → cotação (ou pedir_dado)."""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAT = os.environ.get("CHAT_URL", "http://127.0.0.1:8100/chat")
OCR = os.environ.get("OCR_URL", "http://127.0.0.1:8211/v1/ocr")
KEY = os.environ.get("INTERNAL_KEY", "dev-namastex-key")
IMG = ROOT / "docs/fixtures/ocr_dados_cotacao.png"


def main() -> int:
    b64 = base64.b64encode(IMG.read_bytes()).decode()
    # 1) OCR direto
    req = urllib.request.Request(
        OCR,
        data=json.dumps({"image_base64": b64, "filename": "ocr_dados_cotacao.png"}).encode(),
        headers={"Content-Type": "application/json", "X-Internal-Key": KEY},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        ocr = json.loads(r.read().decode())
    text = (ocr.get("text") or "").strip()
    print("OCR text:", repr(text[:300]))
    if len(text) < 8:
        print("FAIL: OCR vazio")
        return 1

    cid = f"ocr-dados-{int(time.time())}"
    body = {
        "conversation_id": cid,
        "mensagem": "[imagem] ocr_dados_cotacao.png",
        "message_type": "image",
        "media_base64": b64,
        "media_filename": "ocr_dados_cotacao.png",
    }
    req2 = urllib.request.Request(
        CHAT,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req2, timeout=300) as r:
        out = json.loads(r.read().decode())
    acao = (out.get("decisao") or {}).get("acao")
    slots = out.get("slots") or {}
    print("CID", cid)
    print("acao", acao, "estagio", out.get("estagio"))
    print("slots", {k: slots.get(k) for k in ("idade", "veiculo_ano", "plano_id", "cep")})
    print("mensagem", (out.get("mensagem") or "")[:220])
    evs = [e for e in (out.get("eventos") or []) if e.get("step") == "midia"]
    print("midia_events", evs)

    ok = acao in ("apresentar_cotacao", "pedir_dado") and any(
        e.get("status") == "enriched" for e in evs
    )
    # preferir ter lido idade/ano do OCR
    if slots.get("idade") == 42 or slots.get("veiculo_ano") == 2020:
        print("PASS: OCR enriqueceu e slots parciais/completos")
        return 0
    if ok:
        print("PASS parcial: midia enriched (slots podem depender do OCR/heurística)")
        return 0
    print("FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
