"""Agente de cotação (fluxo linear) com log rastreável.

conversa → sanitize(PII) → qualifica(extrai slots) → porteiro(monta body) →
decide(cota resiliente + HITL). Cada passo emite um Evento (id + status) para
rastreabilidade — exigência do desafio. PII é mascarada no log.

Injeção de dependência: `build_fn` (porteiro seguro_auto), `quote_client`
(resiliente), `rag` (opcional), `extrair` (LLM ou heurística). Testável e
demonstrável sem serviços no ar.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from orch_svc.cotacao_flow import DecisaoCotacao, decidir_cotacao
from orch_svc.objecoes import AcaoObjecao, detectar_objecao, proxima_acao

_CPF = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}")
_PLACA = re.compile(r"[A-Z]{3}-?\d[A-Z0-9]\d{2}")
_CEP = re.compile(r"\b\d{5}-?\d{3}\b")
_EMAIL = re.compile(r"[\w.\-]+@[\w.\-]+")
_IDADE = re.compile(r"\b(\d{1,2})\s*anos\b", re.I)
_ANO = re.compile(r"\b(19\d{2}|20\d{2})\b")
# plano por keyword (ordem importa: "mais completo" = premium antes de "completo")
_PLANO = [
    ("premium", r"premium|top|melhor plano|mais completo|cobertura total"),
    ("completo", r"\bcompleto\b|intermedi"),
    ("essencial", r"essencial|b[áa]sico|mais barato|simples|em conta|s[óo] o b[áa]sico"),
]


def mascarar_pii(t: str) -> str:
    t = _CPF.sub("[CPF]", t)
    t = _PLACA.sub("[PLACA]", t)
    t = _CEP.sub("[CEP]", t)
    t = _EMAIL.sub("[EMAIL]", t)
    return t


def extrair_slots_heuristica(texto: str) -> dict[str, Any]:
    """Extração de fallback (sem LLM) — idade, veiculo_ano, cep. Demonstração."""
    slots: dict[str, Any] = {}
    m = _IDADE.search(texto)
    if m:
        slots["idade"] = int(m.group(1))
    anos = [int(a) for a in _ANO.findall(texto)]
    if anos:
        slots["veiculo_ano"] = max(anos)          # heurística: ano mais recente citado
    c = _CEP.search(texto)
    if c:
        slots["cep"] = c.group(0)
    low = texto.lower()
    for plano, pat in _PLANO:
        if re.search(pat, low):
            slots["plano_id"] = plano
            break
    return slots


@dataclass
class Evento:
    step: str
    status: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class Execucao:
    conversation_id: str
    eventos: list[Evento]
    decisao: DecisaoCotacao


def run_conversa(mensagens_lead: list[str], build_fn: Callable[..., Any],
                 quote_client: Any, *, rag: Any = None,
                 extrair: Callable[[str], dict] = extrair_slots_heuristica,
                 tentativas_objecao: int = 0,
                 conversation_id: str | None = None) -> Execucao:
    conv = conversation_id or f"conv_{uuid.uuid4().hex[:8]}"
    ev: list[Evento] = []
    texto = " ".join(mensagens_lead)

    ev.append(Evento("ingest", "ok", {"n_mensagens": len(mensagens_lead)}))
    ev.append(Evento("guardrails", "ok", {"texto_mascarado": mascarar_pii(texto)[:140]}))

    slots = extrair(texto)
    ev.append(Evento("qualifica", "ok" if slots else "vazio", {"slots": slots}))

    # tratamento de objeção — NÃO desistir no primeiro "não" (reverte antes de escalar)
    objecao = detectar_objecao(texto)
    if objecao:
        resp = proxima_acao(objecao, tentativas_objecao)
        ev.append(Evento("objecao", resp.acao,
                         {"objecao": objecao, "framework": resp.framework,
                          "tatica": resp.tatica, "tentativa": resp.tentativa}))
        if resp.acao is AcaoObjecao.REVERTER:
            dec = DecisaoCotacao("reverter_objecao", motivos=[resp.tatica or ""])
            ev.append(Evento("decide", dec.acao,
                             {"tatica": resp.tatica, "tentativa": resp.tentativa}))
            return Execucao(conv, ev, dec)
        dec = DecisaoCotacao("escalar_humano", motivos=[resp.motivo or "objeção persistente"],
                             escalate=True)
        ev.append(Evento("decide", dec.acao, {"escalate": True, "motivos": dec.motivos}))
        return Execucao(conv, ev, dec)

    br = build_fn(slots)
    ev.append(Evento("porteiro", "ok",
                     {"missing": list(getattr(br, "missing", [])),
                      "errors": list(getattr(br, "errors", [])),
                      "refusals": list(getattr(br, "refusals", []))}))

    dec = decidir_cotacao(br, quote_client, query=texto, rag=rag, trace=conv)
    ev.append(Evento("decide", dec.acao,
                     {"escalate": dec.escalate, "motivos": dec.motivos,
                      "faltam": dec.faltam,
                      "premio_mensal": (dec.quote or {}).get("premio_mensal")}))
    return Execucao(conv, ev, dec)


def render_log(execs: list[Execucao]) -> str:
    """Renderiza o log de execução em Markdown (entregável)."""
    out = ["# Log de execução — agente de cotação\n"]
    for e in execs:
        out.append(f"## `{e.conversation_id}` → **{e.decisao.acao}**"
                   + ("  ⚠️ escala humano" if e.decisao.escalate else "") + "\n")
        out.append("| # | passo | status | detalhe |")
        out.append("|---|---|---|---|")
        for i, v in enumerate(e.eventos):
            d = ", ".join(f"{k}={val}" for k, val in v.detail.items() if val not in (None, [], {}))
            out.append(f"| {i} | {v.step} | {v.status} | {d[:110]} |")
        out.append("")
    return "\n".join(out)
