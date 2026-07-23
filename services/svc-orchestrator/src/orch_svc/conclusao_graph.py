"""Grafo formal de fechamento (leve, in-process) — sem Neo4j.

Nós:
  NoConclusao{acao, quote, coberturas, persona}
  FechamentoSpec{key, template, cta, ...}   (em fechamento_index)

Aresta:
  NoConclusao --FECHA_COM--> FechamentoSpec

Graphify (OSS) documenta/visualiza este módulo; o runtime do /chat consulta
`resolver_fechamento()` aqui — não um servidor de grafo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from orch_svc.cotacao_flow import DecisaoCotacao
from orch_svc.persona import Faixa, persona_por_idade


@dataclass(frozen=True)
class NoConclusao:
    """Nó de conclusão do turno — amarra pedido cotado aos fatos do fechamento."""

    id: str
    acao: str
    persona: str
    plano_id: str | None = None
    plano_nome: str | None = None
    premio_mensal: float | None = None
    franquia: float | int | None = None
    coberturas: tuple[str, ...] = ()
    faltam: tuple[str, ...] = ()
    motivos: tuple[str, ...] = ()
    framework: str | None = None
    escalate: bool = False

    def params(self) -> dict[str, str]:
        cob = ", ".join(self.coberturas)
        return {
            "premio": "" if self.premio_mensal is None else str(self.premio_mensal),
            "plano": str(self.plano_nome or self.plano_id or ""),
            "franquia": "" if self.franquia is None else str(self.franquia),
            "coberturas": cob,
            "faltam": ", ".join(self.faltam),
            "motivos": "; ".join(self.motivos),
            "framework": self.framework or "",
        }


@dataclass(frozen=True)
class ArestaFechamento:
    """Aresta tipada: conclusão → molde de resposta."""

    src: str  # NoConclusao.id (ou padrão acao|persona)
    rel: str  # FECHA_COM
    dst: str  # FechamentoSpec.key
    props: dict[str, Any] = field(default_factory=dict)


def no_conclusao_de(
    dec: DecisaoCotacao,
    *,
    idade: int | None,
    framework: str | None = None,
) -> NoConclusao:
    """Constrói o nó de conclusão a partir da decisão + persona."""
    persona = persona_por_idade(idade)
    q = dec.quote or {}
    cob = tuple(str(x) for x in (q.get("coberturas") or []))
    plano_id = q.get("plano_id")
    plano_nome = q.get("plano_nome")
    if dec.acao == "apresentar_cotacao" and q:
        nid = f"conclusao:{dec.acao}|{persona.faixa}|{plano_id or plano_nome or 'plano'}"
    else:
        nid = f"conclusao:{dec.acao}|{persona.faixa}"
    return NoConclusao(
        id=nid,
        acao=dec.acao,
        persona=str(persona.faixa),
        plano_id=None if plano_id is None else str(plano_id),
        plano_nome=None if plano_nome is None else str(plano_nome),
        premio_mensal=_as_float(q.get("premio_mensal")),
        franquia=q.get("franquia"),
        coberturas=cob,
        faltam=tuple(dec.faltam or ()),
        motivos=tuple(dec.motivos or ()),
        framework=framework,
        escalate=bool(dec.escalate),
    )


def chave_padrao_fechamento(no: NoConclusao) -> str:
    """Chave do FechamentoSpec alvo da aresta FECHA_COM."""
    if no.acao == "apresentar_cotacao":
        return f"apresentar_cotacao|{no.persona}"
    if no.acao in (
        "pedir_dado",
        "pedir_correcao",
        "recusar",
        "reverter_objecao",
        "escalar_humano",
        "emitir_apolice",
    ):
        return no.acao
    return "fallback"


def aresta_fecha_com(no: NoConclusao) -> ArestaFechamento:
    dst = chave_padrao_fechamento(no)
    return ArestaFechamento(
        src=no.id,
        rel="FECHA_COM",
        dst=dst,
        props={
            "persona": no.persona,
            "acao": no.acao,
            "plano_id": no.plano_id,
            "n_coberturas": len(no.coberturas),
        },
    )


def export_grafo_catalogo() -> dict[str, Any]:
    """Catálogo estático de nós-padrão + arestas (p/ Graphify / docs / auditoria)."""
    acoes = [
        "apresentar_cotacao",
        "pedir_dado",
        "pedir_correcao",
        "recusar",
        "reverter_objecao",
        "escalar_humano",
        "emitir_apolice",
        "fallback",
    ]
    personas = [f.value for f in Faixa]
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    for acao in acoes:
        if acao == "apresentar_cotacao":
            for p in personas:
                cid = f"padrao:{acao}|{p}"
                fid = f"{acao}|{p}"
                nodes.append(
                    {"id": cid, "label": "NoConclusao", "acao": acao, "persona": p}
                )
                nodes.append(
                    {"id": fid, "label": "FechamentoSpec", "key": fid}
                )
                edges.append(
                    {"source": cid, "rel": "FECHA_COM", "target": fid}
                )
        else:
            cid = f"padrao:{acao}"
            nodes.append({"id": cid, "label": "NoConclusao", "acao": acao})
            nodes.append({"id": acao, "label": "FechamentoSpec", "key": acao})
            edges.append({"source": cid, "rel": "FECHA_COM", "target": acao})

    # coberturas / planos como nós de domínio ligados à ação de cotar
    for plano in ("essencial", "completo", "premium"):
        nodes.append({"id": f"plano:{plano}", "label": "Plano", "plano_id": plano})
        edges.append(
            {
                "source": f"plano:{plano}",
                "rel": "PODE_GERAR",
                "target": "padrao:apresentar_cotacao|meia_30_50",
            }
        )
    for cob in ("colisao", "roubo", "furto", "terceiros", "vidros",
                "carro_reserva", "assistencia_24h"):
        nodes.append({"id": f"cob:{cob}", "label": "Cobertura", "nome": cob})
        edges.append(
            {
                "source": "padrao:apresentar_cotacao|meia_30_50",
                "rel": "INCLUI_COBERTURA",
                "target": f"cob:{cob}",
            }
        )

    return {
        "name": "grafo-fechamento-seguro-auto",
        "engine": "in-process",
        "note": "Runtime sem Neo4j; Graphify documenta este catálogo.",
        "nodes": nodes,
        "edges": edges,
    }


def _as_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
