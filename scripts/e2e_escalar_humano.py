#!/usr/bin/env python3
"""Valida HITL (escalar_humano / recusar) com casos ancorados no dataset.

Achado do parquet: não há frase explícita 'escalar para humano'.
Padrões usados na régua:
  - perdido + 'achei caro' (ex. conv_00003) → após N táticas, nosso agente escala
  - mídia document/audio/image (ex. conv_00033) → escala se sem ASR/OCR útil
  - idade ≥76 (ex. conv_00008 / conv_00033) → recusa por faixa (domínio)

Uso:
  python scripts/e2e_escalar_humano.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

CHAT_URL = os.environ.get("CHAT_URL", "http://127.0.0.1:8100/chat")
OUT = os.environ.get(
    "E2E_HITL_OUT",
    "/home/aejepsen/Documentos/curriculos/Khal/desafio-Khal/docs/e2e-escalar-humano.json",
)

# Casos derivados do dataset (PII mascarada / sintética).
CASES = [
    {
        "id": "DS_objecao_preco_conv_00003",
        "dataset_cid": "conv_00003",
        "padrao_dataset": "perdido + 'achei caro' / concorrente; vendedor: 'posso te ligar?'",
        "expect_final": {"acao": "escalar_humano", "escalate": True},
        "turns": [
            {
                "mensagem": (
                    "tenho 61 anos, Toyota Corolla 2010, plano essencial, cep 59158-132"
                ),
            },
            {"mensagem": "achei caro pra esse carro... a Porto Seguro me ofereceu menos"},
            {"mensagem": "ainda tá caro"},
            {"mensagem": "caro demais"},
            {"mensagem": "muito caro mesmo"},
        ],
    },
    {
        "id": "DS_media_document_conv_00033",
        "dataset_cid": "conv_00033",
        "padrao_dataset": "lead envia [documento] CNH_frente.pdf sem texto útil",
        "expect_final": {"acao": "escalar_humano", "escalate": True},
        "turns": [
            {
                "mensagem": "[documento] CNH_frente.pdf",
                "message_type": "document",
            },
        ],
    },
    {
        "id": "DS_idade_fora_faixa_conv_00008",
        "dataset_cid": "conv_00008",
        "padrao_dataset": "idade 78 (≥76) — fora das faixas aceitas do domínio",
        "expect_final": {"acao_in": ["recusar", "escalar_humano"]},
        "turns": [
            {
                "mensagem": (
                    "tenho 78 anos, Honda HR-V 2008, plano essencial, cep 01310-100"
                ),
            },
        ],
    },
]


def post_chat(cid: str, mensagem: str, *, message_type: str | None = None) -> dict:
    body: dict = {"conversation_id": cid, "mensagem": mensagem}
    if message_type:
        body["message_type"] = message_type
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        CHAT_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode())


def ok_expect(out: dict, expect: dict) -> bool:
    acao = (out.get("decisao") or {}).get("acao")
    esc = bool((out.get("decisao") or {}).get("escalate"))
    if "acao" in expect and acao != expect["acao"]:
        return False
    if "acao_in" in expect and acao not in expect["acao_in"]:
        return False
    if "escalate" in expect and esc != bool(expect["escalate"]):
        # recusar pode não setar escalate=True — só exige se expect tem escalate
        if "acao" in expect or expect.get("escalate") is True:
            return esc == bool(expect["escalate"])
    return True


def main() -> int:
    stamp = int(time.time())
    results = []
    print(f"# E2E HITL / escalar (dataset)\nURL={CHAT_URL}\n")
    all_pass = True
    for case in CASES:
        cid = f"hitl-{case['id'].lower()}-{stamp}"
        print(f"## {case['id']}  dataset={case['dataset_cid']}")
        print(f"   padrao: {case['padrao_dataset']}")
        last = None
        turns_out = []
        try:
            for i, t in enumerate(case["turns"], 1):
                out = post_chat(
                    cid,
                    t["mensagem"],
                    message_type=t.get("message_type"),
                )
                last = out
                row = {
                    "turno": i,
                    "lead": t["mensagem"][:120],
                    "acao": (out.get("decisao") or {}).get("acao"),
                    "escalate": (out.get("decisao") or {}).get("escalate"),
                    "estagio": out.get("estagio"),
                    "motivos": (out.get("decisao") or {}).get("motivos"),
                    "mensagem": (out.get("mensagem") or "")[:200],
                }
                turns_out.append(row)
                print(
                    f"  T{i} [{row['estagio']}/{row['acao']}] "
                    f"escalate={row['escalate']} → {row['mensagem'][:100]}"
                )
        except urllib.error.URLError as e:
            print(f"  FAIL transport: {e}")
            all_pass = False
            results.append({"id": case["id"], "cid": cid, "pass": False, "error": str(e)})
            continue

        passed = ok_expect(last or {}, case["expect_final"])
        all_pass = all_pass and passed
        print(f"  => {'PASS' if passed else 'FAIL'} expect={case['expect_final']}\n")
        results.append(
            {
                "id": case["id"],
                "dataset_cid": case["dataset_cid"],
                "conversation_id": cid,
                "pass": passed,
                "expect": case["expect_final"],
                "final_acao": (last or {}).get("decisao", {}).get("acao"),
                "final_escalate": (last or {}).get("decisao", {}).get("escalate"),
                "turns": turns_out,
            }
        )

    payload = {
        "nota_dataset": (
            "Parquet não tem 'escalar humano' explícito; 538 convs usam "
            "'posso te ligar?' após objeção de preço (handoff soft)."
        ),
        "pass": all_pass,
        "results": results,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("## veredicto", "PASS" if all_pass else "FAIL")
    print("wrote", OUT)
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
