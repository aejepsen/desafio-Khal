"""Índice de fechamentos — resolve aresta FECHA_COM do grafo de conclusão.

Runtime: NoConclusao --FECHA_COM--> FechamentoSpec (in-process, sem Neo4j).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from orch_svc.conclusao_graph import (
    ArestaFechamento,
    NoConclusao,
    aresta_fecha_com,
    chave_padrao_fechamento,
    no_conclusao_de,
)
from orch_svc.cotacao_flow import DecisaoCotacao
from orch_svc.persona import Faixa


@dataclass(frozen=True)
class FechamentoSpec:
    key: str
    template: str
    cta: str
    exigir_no_texto: tuple[str, ...] = ()


# CTAs fixas — sem "ajustar o plano agora".
_CTA_COTACAO = (
    "Quer que eu detalhe as coberturas ou compare com outro plano "
    "(Essencial / Completo / Premium)?"
)
_CTA_PEDIR = "Pode me enviar esses dados pra eu cotar?"
_CTA_RECUSAR = "Posso te conectar com um especialista pra avaliar o caso?"
_CTA_HITL = "Um atendente humano vai continuar daqui."
_CTA_OBJECAO = "Faz sentido olharmos isso juntos?"


def _spec_catalog() -> dict[str, FechamentoSpec]:
    """Nós FechamentoSpec do grafo (destino das arestas FECHA_COM)."""
    specs: dict[str, FechamentoSpec] = {}
    for faixa in Faixa:
        key = f"apresentar_cotacao|{faixa.value}"
        specs[key] = FechamentoSpec(
            key=key,
            template="{corpo} " + _CTA_COTACAO,
            cta=_CTA_COTACAO,
        )
    specs["pedir_dado"] = FechamentoSpec(
        key="pedir_dado",
        template="{motivos} " + _CTA_PEDIR,
        cta=_CTA_PEDIR,
    )
    specs["pedir_correcao"] = FechamentoSpec(
        key="pedir_correcao",
        template=(
            "Tem um dado que não bate ({motivos}). "
            "Pode conferir e me mandar de novo?"
        ),
        cta="me mandar de novo",
    )
    specs["recusar"] = FechamentoSpec(
        key="recusar",
        template=(
            "Nesse perfil a cotação automática não fecha: {motivos}. "
            + _CTA_RECUSAR
        ),
        cta=_CTA_RECUSAR,
    )
    specs["reverter_objecao"] = FechamentoSpec(
        key="reverter_objecao",
        template="Entendo sua dúvida{fw}. {motivos} " + _CTA_OBJECAO,
        cta=_CTA_OBJECAO,
    )
    specs["escalar_humano"] = FechamentoSpec(
        key="escalar_humano",
        template=(
            "Vou te conectar com um atendente humano pra continuar com segurança."
            "{extra} " + _CTA_HITL
        ),
        cta=_CTA_HITL,
    )
    specs["fallback"] = FechamentoSpec(
        key="fallback",
        template="{motivos}",
        cta="",
    )
    return specs


_SPECS = _spec_catalog()


@dataclass(frozen=True)
class ResolucaoFechamento:
    no: NoConclusao
    aresta: ArestaFechamento
    spec: FechamentoSpec
    texto: str
    params: dict[str, str]


def lookup_fechamento(
    dec: DecisaoCotacao,
    *,
    idade: int | None,
    framework: str | None = None,
) -> tuple[FechamentoSpec, str, dict[str, str]]:
    """API estável: (spec, texto, params). Preferir `resolver_fechamento` p/ grafo."""
    r = resolver_fechamento(dec, idade=idade, framework=framework)
    return r.spec, r.texto, r.params


def resolver_fechamento(
    dec: DecisaoCotacao,
    *,
    idade: int | None,
    framework: str | None = None,
) -> ResolucaoFechamento:
    """Percorre NoConclusao -FECHA_COM-> FechamentoSpec e preenche o molde."""
    no = no_conclusao_de(dec, idade=idade, framework=framework)
    aresta = aresta_fecha_com(no)
    key = aresta.dst
    base = _SPECS.get(key) or _SPECS["fallback"]
    params = no.params()
    if not params.get("motivos"):
        if no.acao == "pedir_dado":
            faltam = params.get("faltam") or "mais alguns dados"
            params["motivos"] = f"Pra cotar preciso de: {faltam}."
        elif no.acao == "pedir_correcao":
            params["motivos"] = "há um dado inconsistente"
        elif no.acao == "recusar":
            params["motivos"] = "fora da faixa de aceitação"
        elif no.acao == "reverter_objecao":
            params["motivos"] = "vamos olhar juntos o que te travou"
        elif no.acao == "fallback":
            params["motivos"] = "Como posso te ajudar na cotação?"

    params["corpo"] = _corpo_cotacao(no.persona, params)
    params["fw"] = f" ({params['framework']})" if params.get("framework") else ""
    extra = ""
    if no.acao == "escalar_humano" and params.get("motivos"):
        extra = f" Motivo: {params['motivos']}."
    params["extra"] = extra

    exigir = tuple(
        x for x in (params.get("premio"), params.get("plano")) if x
    ) if no.acao == "apresentar_cotacao" else ()

    spec = FechamentoSpec(
        key=base.key,
        template=base.template,
        cta=base.cta,
        exigir_no_texto=exigir,
    )
    texto = _fill(spec.template, params)
    # garantir chave canônica
    assert chave_padrao_fechamento(no) == key or key == "fallback" or key in _SPECS
    return ResolucaoFechamento(
        no=no, aresta=aresta, spec=spec, texto=texto, params=params
    )


def _corpo_cotacao(persona: str, params: dict[str, str]) -> str:
    plano = params.get("plano", "plano")
    premio = params.get("premio", "")
    franquia = params.get("franquia", "")
    cob = params.get("coberturas", "")
    cob_txt = f" Cobre: {cob}." if cob else ""

    if persona == Faixa.JOVEM.value:
        return f"Pronto! {plano}: R$ {premio}/mês (franquia R$ {franquia}).{cob_txt}"
    if persona == Faixa.SENIOR.value:
        return (
            f"Segue a cotação do plano {plano}: R$ {premio}/mês "
            f"(franquia R$ {franquia}).{cob_txt}"
        )
    return (
        f"Pronto — cotação do plano {plano}: R$ {premio}/mês "
        f"(franquia R$ {franquia}).{cob_txt}"
    )


def _fill(template: str, params: dict[str, str]) -> str:
    out = template
    for k, v in params.items():
        out = out.replace("{" + k + "}", v)
    return " ".join(out.split())


_CTA_PROIBIDAS = (
    "ajustar o plano agora",
    "como podemos ajustar",
    "vamos ajustar o plano",
    "ajustar algo no plano",
)


def validar_fechamento_llm(
    texto: str,
    *,
    spec: FechamentoSpec,
    params: dict[str, str],
) -> bool:
    if not (texto or "").strip():
        return False
    low = texto.lower()
    for ban in _CTA_PROIBIDAS:
        if ban in low:
            return False
    for obrig in spec.exigir_no_texto:
        if obrig and obrig == params.get("premio"):
            continue
        if not _contem_fato(texto, obrig):
            return False
    premio = params.get("premio") or ""
    if premio and not _contem_premio(texto, premio):
        return False
    return True


def _contem_fato(texto: str, fato: str) -> bool:
    if not fato:
        return True
    return fato.lower() in texto.lower()


def _contem_premio(texto: str, premio: str) -> bool:
    import re

    try:
        val = float(str(premio).replace(",", "."))
    except ValueError:
        return premio in texto
    candidates = {
        f"{val:.2f}",
        f"{val:.1f}",
        f"{val:g}",
        f"{val:.2f}".replace(".", ","),
        f"{val:.1f}".replace(".", ","),
        f"{val:g}".replace(".", ","),
    }
    if abs(val - round(val, 1)) < 1e-9:
        candidates.add(f"{val:.1f}".replace(".", ","))
    low = texto.replace(" ", "")
    for c in candidates:
        if c and c in texto:
            return True
        if c and c.replace(",", ".") in low.replace(",", "."):
            return True
    digits = re.sub(r"[^\d]", "", f"{val:.2f}")
    return bool(digits) and digits[:3] in re.sub(r"[^\d]", "", texto)
