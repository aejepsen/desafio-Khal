"""Redação da resposta — grafo NoConclusao -FECHA_COM-> FechamentoSpec + LLM."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from orch_svc.cotacao_flow import DecisaoCotacao
from orch_svc.fechamento_index import resolver_fechamento, validar_fechamento_llm
from orch_svc.persona import diretriz_de_estilo


class _ChatClient(Protocol):
    def chat(self, messages: list[dict[str, str]], trace: str) -> str: ...


@dataclass(frozen=True)
class RedacaoResult:
    texto: str
    rascunho: str
    fonte: str  # llm | template | llm_fallback
    index_key: str = ""
    cta: str = ""
    conclusao_id: str = ""
    aresta: str = ""


def _prompt(
    dec: DecisaoCotacao,
    *,
    idade: int | None,
    mensagem_lead: str,
    framework: str | None,
    rascunho: str,
    cta: str,
    params: dict[str, str],
    conclusao_id: str,
) -> list[dict[str, str]]:
    estilo = diretriz_de_estilo(idade)
    fatos = {
        "conclusao_id": conclusao_id,
        "acao": dec.acao,
        "plano": params.get("plano"),
        "premio_mensal": params.get("premio"),
        "franquia": params.get("franquia"),
        "coberturas": params.get("coberturas"),
        "faltam": dec.faltam,
        "motivos": dec.motivos,
        "escalate": dec.escalate,
        "framework": framework,
        "cta_obrigatoria": cta,
    }
    system = (
        "Você é um agente de seguro auto no WhatsApp. "
        "Reescreva a mensagem ao lead no tom indicado, SEM mudar fatos nem a CTA. "
        "OBRIGATÓRIO: manter o valor do prêmio (número) e o nome do plano se existirem nos FATOS. "
        "OBRIGATÓRIO: terminar com a mesma intenção da CTA_OBRIGATORIA "
        "(detalhar coberturas OU comparar com os outros planos listados na CTA). "
        "PROIBIDO: perguntar para 'ajustar o plano agora' ou sugerir que o plano está errado. "
        "PROIBIDO: na comparação, relistar o plano que já foi cotado nos FATOS. "
        "NÃO invente prêmio, plano, franquia nem coberturas. "
        "NÃO mude a decisão (ação). Resposta curta (2-4 frases), só o texto final."
    )
    exemplos_bloco = _bloco_exemplos(list(dec.exemplos or []))
    user = (
        f"{estilo}\n\n"
        f"MENSAGEM DO LEAD: {mensagem_lead or '(n/d)'}\n"
        f"FATOS: {fatos}\n"
        f"RASCUNHO (molde do grafo FECHA_COM): {rascunho}\n"
        f"CTA_OBRIGATORIA: {cta}\n"
        f"EXEMPLOS RE-RANKED (tom/estilo; NÃO copie fatos inventados):\n"
        f"{exemplos_bloco}\n"
        "Texto final:"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _bloco_exemplos(exemplos: list[str], *, max_n: int = 3, max_chars: int = 280) -> str:
    if not exemplos:
        return "(nenhum)"
    lines = []
    for i, t in enumerate(exemplos[:max_n], 1):
        snippet = " ".join((t or "").split())[:max_chars]
        lines.append(f"{i}. {snippet}")
    return "\n".join(lines)


def redigir_resposta(
    dec: DecisaoCotacao,
    *,
    idade: int | None,
    mensagem_lead: str = "",
    framework: str | None = None,
    inference: _ChatClient | None = None,
    trace: str = "resposta",
) -> RedacaoResult:
    res = resolver_fechamento(dec, idade=idade, framework=framework)
    rascunho = res.texto
    meta = dict(
        index_key=res.spec.key,
        cta=res.spec.cta,
        conclusao_id=res.no.id,
        aresta=f"{res.aresta.src}-[{res.aresta.rel}]->{res.aresta.dst}",
    )
    # HITL / pausa: texto canônico ao lead (sem LLM) — evita jargão ou "dúvida" inventada.
    if dec.acao in ("escalar_humano", "adiar_conversa"):
        return RedacaoResult(texto=rascunho, rascunho=rascunho, fonte="template", **meta)
    if inference is None:
        return RedacaoResult(texto=rascunho, rascunho=rascunho, fonte="template", **meta)
    try:
        out = inference.chat(
            _prompt(
                dec, idade=idade, mensagem_lead=mensagem_lead,
                framework=framework, rascunho=rascunho,
                cta=res.spec.cta, params=res.params,
                conclusao_id=res.no.id,
            ),
            trace,
        )
    except Exception:
        return RedacaoResult(
            texto=rascunho, rascunho=rascunho, fonte="llm_fallback", **meta
        )
    texto = (out or "").strip()
    if not texto or not validar_fechamento_llm(
        texto, spec=res.spec, params=res.params
    ):
        return RedacaoResult(
            texto=rascunho, rascunho=rascunho, fonte="llm_fallback", **meta
        )
    return RedacaoResult(texto=texto, rascunho=rascunho, fonte="llm", **meta)
