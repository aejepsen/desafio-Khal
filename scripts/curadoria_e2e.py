#!/usr/bin/env python3
"""Mapeamento E2E multi-cenário pra curadoria manual (não é gate automático).

Roda uma bateria de conversas reais contra o agente no ar (LLM de verdade via
Ollama), captura cada turno (mensagem do lead, decisão, texto final redigido)
+ o audit trail (`GET /audit/{conversation_id}`), e escreve:
  - docs/curadoria-e2e/raw/<cenario>.json  (transcript bruto, por cenário)
  - docs/curadoria-e2e/relatorio.md         (consolidado, pra revisão humana)

Não faz assert de pass/fail — o objetivo é dar material real pra um humano
avaliar tom/coerência/qualidade das respostas, não só corretude técnica.

Uso:
  docker compose up -d   # stack completa já no ar
  python scripts/curadoria_e2e.py
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAT_URL = os.environ.get("CHAT_URL", "http://127.0.0.1:8100/chat")
AUDIT_URL = os.environ.get("AUDIT_URL", "http://127.0.0.1:8100/audit")
OUT_DIR = ROOT / "docs/curadoria-e2e"
RAW_DIR = OUT_DIR / "raw"


def _post(url: str, body: dict, timeout: int = 180) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _get(url: str, timeout: int = 30) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())


@dataclass
class Turno:
    mensagem: str
    message_type: str | None = None
    media_url: str | None = None
    media_base64: str | None = None
    media_filename: str | None = None
    idade: int | None = None


@dataclass
class Cenario:
    id: str
    titulo: str
    descricao: str
    turnos: list[Turno] = field(default_factory=list)


def _fixture_ocr_b64() -> str:
    return base64.b64encode((ROOT / "docs/fixtures/ocr_dados_cotacao.png").read_bytes()).decode()


def cenarios() -> list[Cenario]:
    return [
        Cenario(
            "caminho_feliz", "Caminho feliz — qualifica → cota → aceita → apólice",
            "Todos os dados de uma vez; aceite explícito depois da cotação.",
            [
                Turno("tenho 35 anos, Gol 2020, plano essencial, cep 01310-100"),
                Turno("pode contratar"),
            ],
        ),
        Cenario(
            "objecao_escala", "Objeção de preço — reverte 3x, escala na 4ª",
            "Mostra as táticas (feel-felt-found/isolamento/ancoragem) e o "
            "escalonamento só depois de esgotar tentativas.",
            [
                Turno("tenho 42 anos, Corolla 2019, plano completo, cep 04567-000"),
                Turno("achei muito caro"),
                Turno("ainda tá caro"),
                Turno("caro demais"),
                Turno("muito caro mesmo"),
            ],
        ),
        Cenario(
            "quote_indisponivel", "Falha do /quote — escala humano (HITL grau A)",
            "QUOTE_FAILURE_RATE forçado a 1.0 no quote-api pra esgotar retry+circuito.",
            [Turno("tenho 30 anos, HB20 2021, plano essencial, cep 20000-000")],
        ),
        Cenario(
            "midia_sem_transcricao", "Mídia sem transcrição — escala humano",
            "Documento sem media_url/media_base64 (sem OCR possível).",
            [Turno("[documento] CNH.pdf", message_type="document")],
        ),
        Cenario(
            "ocr_dados", "OCR de imagem com dados — extrai e segue fluxo normal",
            "Fixture real (docs/fixtures/ocr_dados_cotacao.png) via Tesseract.",
            [Turno("[imagem] dados.png", message_type="image",
                   media_base64=_fixture_ocr_b64(), media_filename="dados.png")],
        ),
        Cenario(
            "pedido_humano_explicito", "Pedido explícito de humano — escala direto",
            "Lead pede atendente ANTES de qualquer dado — não deve virar pausa "
            "nem ser ignorado (bug corrigido nesta sessão).",
            [Turno("posso falar com um atendente humano?")],
        ),
        Cenario(
            "pausa_respeitosa", "Pausa (\"vou pensar\") — não inventa dúvida",
            "Depois de pedir_dado (falta CEP), lead pede tempo.",
            [
                Turno("tenho 50 anos, Onix 2018, plano completo"),
                Turno("vou pensar, depois te falo"),
            ],
        ),
        Cenario(
            "fora_de_faixa_recusa", "Idade fora de faixa — recusa (não escala)",
            "Regra plans.json: idade > 75 = recusar. Critério local, não é falha de infra.",
            [Turno("tenho 80 anos, Civic 2015, plano essencial, cep 30000-000")],
        ),
        Cenario(
            "pii_mascarada", "PII no texto — mascarada no audit",
            "CPF explícito na mensagem; slots reais seguem pra cotar, mas o "
            "audit/log precisa mascarar.",
            [Turno("tenho 33 anos, Fiat Argo 2021, plano essencial, cep 01310-100, "
                   "meu cpf é 123.456.789-09")],
        ),
    ]


def run_cenario(cen: Cenario) -> dict:
    conversation_id = f"curadoria-{cen.id}-{int(time.time())}"
    turnos_out = []
    for t in cen.turnos:
        body: dict = {"conversation_id": conversation_id, "mensagem": t.mensagem}
        if t.message_type:
            body["message_type"] = t.message_type
        if t.media_url:
            body["media_url"] = t.media_url
        if t.media_base64:
            body["media_base64"] = t.media_base64
        if t.media_filename:
            body["media_filename"] = t.media_filename
        if t.idade is not None:
            body["idade"] = t.idade
        t0 = time.time()
        try:
            resp = _post(CHAT_URL, body)
            err = None
        except urllib.error.HTTPError as e:
            resp = {"http_error": e.code, "body": e.read().decode(errors="replace")}
            err = str(e)
        except Exception as e:  # noqa: BLE001
            resp = {}
            err = str(e)
        dt = round(time.time() - t0, 2)
        turnos_out.append({
            "lead": t.mensagem, "message_type": t.message_type,
            "latencia_s": dt, "erro": err, "resposta": resp,
        })
        print(f"  [{cen.id}] turno {len(turnos_out)} ({dt}s): "
              f"acao={((resp.get('decisao') or {}).get('acao'))} "
              f"mensagem={(resp.get('mensagem') or '')[:80]!r}")

    audit = None
    try:
        audit = _get(f"{AUDIT_URL}/{conversation_id}")
    except Exception as e:  # noqa: BLE001
        audit = {"erro": str(e)}

    return {
        "id": cen.id, "titulo": cen.titulo, "descricao": cen.descricao,
        "conversation_id": conversation_id, "turnos": turnos_out, "audit": audit,
    }


def to_markdown(resultados: list[dict]) -> str:
    lines = [
        "# Curadoria E2E — mapeamento de cenários (revisão manual)",
        "",
        f"Gerado em {time.strftime('%Y-%m-%d %H:%M:%S')} contra o stack real "
        "(LLM `qwen2.5:7b` via Ollama, quote-api real, Neo4j/Qdrant populados).",
        "",
        "> Não é gate automático — é material pra revisão humana de tom/coerência/qualidade.",
        "",
    ]
    for r in resultados:
        lines += [
            f"## {r['id']} — {r['titulo']}",
            "",
            r["descricao"],
            "",
            f"`conversation_id`: `{r['conversation_id']}`",
            "",
        ]
        for i, t in enumerate(r["turnos"], 1):
            resp = t["resposta"] or {}
            dec = resp.get("decisao") or {}
            lines += [
                f"**Turno {i}** — lead: _{t['lead']}_",
                "",
                f"- ação: `{dec.get('acao')}` · escalate: `{dec.get('escalate')}` "
                f"· estágio: `{resp.get('estagio')}` · latência: {t['latencia_s']}s",
                f"- **resposta ao lead:** {resp.get('mensagem') or '(sem mensagem — ver erro)'}",
            ]
            if t["erro"]:
                lines.append(f"- ⚠️ erro: `{t['erro']}`")
            if dec.get("motivos"):
                lines.append(f"- motivos (internos): `{dec.get('motivos')}`")
            lines.append("")
        audit = r.get("audit") or {}
        lines += ["<details><summary>audit trail (mascarado)</summary>", "",
                   "```json", json.dumps(audit, ensure_ascii=False, indent=2)[:4000],
                   "```", "", "</details>", ""]
    return "\n".join(lines)


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", default=None, help="ids separados por vírgula (roda só esses)")
    ap.add_argument("--skip", default=None, help="ids separados por vírgula (pula esses)")
    args = ap.parse_args()

    only = set(args.only.split(",")) if args.only else None
    skip = set(args.skip.split(",")) if args.skip else set()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    selecionados = [
        c for c in cenarios()
        if (only is None or c.id in only) and c.id not in skip
    ]
    for cen in selecionados:
        print(f"=== {cen.id}: {cen.titulo} ===")
        try:
            r = run_cenario(cen)
        except Exception as e:  # noqa: BLE001
            print(f"  FALHOU: {e}")
            r = {"id": cen.id, "titulo": cen.titulo, "descricao": cen.descricao,
                 "conversation_id": "-", "turnos": [], "audit": {"erro": str(e)}}
        (RAW_DIR / f"{cen.id}.json").write_text(
            json.dumps(r, ensure_ascii=False, indent=2)
        )

    # relatório consolidado sempre a partir de TODOS os raw/*.json já gerados
    # (permite rodar em passadas separadas, ex.: /quote forçado a falhar à parte).
    ordem = {c.id: i for i, c in enumerate(cenarios())}
    resultados = [
        json.loads(p.read_text())
        for p in sorted(RAW_DIR.glob("*.json"), key=lambda p: ordem.get(p.stem, 99))
    ]
    (OUT_DIR / "relatorio.md").write_text(to_markdown(resultados))
    print(f"\nrelatório: {OUT_DIR / 'relatorio.md'} ({len(resultados)} cenários)")
    print(f"raw: {RAW_DIR}/*.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
