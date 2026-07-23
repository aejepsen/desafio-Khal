"""Estado multi-turno da conversa (thread) — o agente CONDUZ o lead.

Uma conversa não é one-shot: o agente informa o que precisa, o lead manda (pode vir
incompleto), o agente ACUMULA o que já tem e pede só o que falta, até cotar. O estado
por `conversation_id` guarda slots acumulados, tentativas de objeção e estágio.

Store in-memory (simples; produção = Redis/DB por conversation_id). Limite de turnos =
critério HITL temporal (conversa que não avança escala).
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any, Callable

from orch_svc.agente_cotacao import (Evento, Execucao, extrair_slots_heuristica,
                                     mascarar_pii)
from orch_svc.cotacao_flow import DecisaoCotacao, decidir_cotacao
from orch_svc.objecoes import AcaoObjecao, detectar_objecao, proxima_acao

# campos que o /quote precisa (o agente informa isto quando o lead pergunta)
LABELS = {
    "idade": "sua idade",
    "veiculo_ano": "o ano do veículo",
    "cep": "seu CEP",
    "plano_id": "o plano desejado (essencial, completo ou premium)",
}
MAX_TURNOS = 8
# coleta ATIVA — campos que mudam o preço/a escolha, não deixar como default silencioso
OBRIGATORIOS = ["idade", "veiculo_ano", "plano_id"]   # sempre perguntados
OPCIONAIS_ATIVOS = ["cep"]                            # pede 1x; cota sem se o lead não der


@dataclass
class ThreadState:
    conversation_id: str
    slots: dict[str, Any] = field(default_factory=dict)
    tentativas_objecao: dict[str, int] = field(default_factory=dict)
    pedidos: set[str] = field(default_factory=set)     # campos já solicitados (não repetir)
    turnos: int = 0
    estagio: str = "qualificando"      # qualificando | objecao | cotado | escalado
    encerrado: bool = False


class ThreadStore:
    """Estado por conversa. In-memory; troca por Redis/DB em produção."""

    def __init__(self) -> None:
        self._d: dict[str, ThreadState] = {}

    def get(self, cid: str) -> ThreadState:
        return self._d.get(cid) or ThreadState(cid)

    def save(self, st: ThreadState) -> None:
        self._d[st.conversation_id] = st


def pedir_faltantes(faltam: list[str]) -> str:
    itens = ", ".join(LABELS.get(f, f) for f in faltam)
    return f"Pra cotar seu seguro eu preciso de: {itens}."


def _merge(atual: dict, novos: dict) -> None:
    for k, v in novos.items():
        if v is not None and v != "":
            atual[k] = v


def run_turno(mensagem: str, state: ThreadState, build_fn: Callable[..., Any],
              quote_client: Any, *, rag: Any = None,
              extrair: Callable[[str], dict] = extrair_slots_heuristica,
              max_turnos: int = MAX_TURNOS) -> tuple[Execucao, ThreadState]:
    state.turnos += 1
    ev: list[Evento] = [
        Evento("turno", str(state.turnos), {"estagio": state.estagio}),
        Evento("guardrails", "ok", {"texto_mascarado": mascarar_pii(mensagem)[:120]}),
    ]

    # objeção primeiro — não desistir no primeiro "não" (tentativas persistidas)
    obj = detectar_objecao(mensagem)
    if obj:
        feitas = state.tentativas_objecao.get(obj, 0)
        resp = proxima_acao(obj, feitas)
        ev.append(Evento("objecao", resp.acao, {"objecao": obj, "framework": resp.framework,
                                                "tatica": resp.tatica, "tentativa": resp.tentativa}))
        if resp.acao is AcaoObjecao.REVERTER:
            state.tentativas_objecao[obj] = feitas + 1
            state.estagio = "objecao"
            dec = DecisaoCotacao("reverter_objecao", motivos=[resp.tatica or ""])
        else:
            state.encerrado = True
            state.estagio = "escalado"
            dec = DecisaoCotacao("escalar_humano", motivos=[resp.motivo or ""], escalate=True)
        ev.append(Evento("decide", dec.acao, {"escalate": dec.escalate}))
        return Execucao(state.conversation_id, ev, dec), state

    # acumula os slots que vieram neste turno
    _merge(state.slots, extrair(mensagem))
    ev.append(Evento("qualifica", "ok", {"slots_acumulados": dict(state.slots)}))

    # limite de interações — HITL temporal
    if state.turnos > max_turnos:
        state.encerrado = True
        state.estagio = "escalado"
        dec = DecisaoCotacao("escalar_humano", escalate=True,
                             motivos=[f"conversa não avançou em {max_turnos} turnos"])
        ev.append(Evento("decide", dec.acao, {"escalate": True}))
        return Execucao(state.conversation_id, ev, dec), state

    # coleta ATIVA — pede plano/cep/data antes de cotar (não usa default silencioso)
    state.slots.setdefault("data_inicio", _dt.date.today().isoformat())
    faltam = [c for c in OBRIGATORIOS if not state.slots.get(c)]
    for c in OPCIONAIS_ATIVOS:                # pede 1x; se o lead não der, cota sem
        if not state.slots.get(c) and c not in state.pedidos:
            faltam.append(c)
    if faltam:
        state.pedidos.update(faltam)
        state.estagio = "qualificando"
        dec = DecisaoCotacao("pedir_dado", faltam=faltam, motivos=[pedir_faltantes(faltam)])
        ev.append(Evento("decide", dec.acao, {"faltam": faltam}))
        return Execucao(state.conversation_id, ev, dec), state

    # tudo coletado → porteiro + decisão
    br = build_fn(state.slots)
    dec = decidir_cotacao(br, quote_client, query=mensagem, rag=rag, trace=state.conversation_id)
    if dec.acao == "pedir_dado":
        state.estagio = "qualificando"
        dec.motivos = [pedir_faltantes(dec.faltam)]      # mensagem amigável do que falta
    elif dec.acao == "apresentar_cotacao":
        state.estagio = "cotado"
        state.encerrado = True
    ev.append(Evento("decide", dec.acao,
                     {"faltam": dec.faltam, "premio_mensal": (dec.quote or {}).get("premio_mensal"),
                      "escalate": dec.escalate}))
    return Execucao(state.conversation_id, ev, dec), state
