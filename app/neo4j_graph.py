"""Cliente Neo4j — grafo de fechamento + âncoras do corpus (pesquisa semântica).

Sobe com o compose (`bolt://neo4j:7687`). Seed idempotente no boot do agente.
O lookup in-process (`conclusao_graph`) continua; Neo4j é a base persistente
consultável (Browser :7474) e caminho para GraphRAG sobre o dataset.
"""
from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger("neo4j.graph")

_NEO4J_URI = os.environ.get("NEO4J_URI", "")
_NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
_NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "namastex-graph")


class Neo4jGraph:
    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        self.uri = uri if uri is not None else _NEO4J_URI
        self.user = user if user is not None else _NEO4J_USER
        self.password = password if password is not None else _NEO4J_PASSWORD
        self._driver = None

    @property
    def enabled(self) -> bool:
        return bool(self.uri)

    def connect(self) -> bool:
        if not self.enabled:
            return False
        try:
            from neo4j import GraphDatabase

            self._driver = GraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
            self._driver.verify_connectivity()
            return True
        except Exception as exc:
            log.warning("Neo4j indisponível: %s", exc)
            self._driver = None
            return False

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def health(self) -> dict[str, Any]:
        if not self.enabled:
            return {"status": "disabled"}
        if self._driver is None and not self.connect():
            return {"status": "down", "uri": self.uri}
        try:
            with self._driver.session() as s:
                n = s.run("MATCH (n) RETURN count(n) AS c").single()["c"]
            return {"status": "ok", "uri": self.uri, "nodes": int(n)}
        except Exception as exc:
            return {"status": "error", "detail": str(exc), "uri": self.uri}

    def seed_fechamento_catalog(self) -> dict[str, int]:
        """Materializa catálogo NoConclusao/FECHA_COM/Plano/Cobertura no Neo4j."""
        from orch_svc.conclusao_graph import export_grafo_catalogo

        if self._driver is None and not self.connect():
            raise RuntimeError("Neo4j offline — seed abortado")

        cat = export_grafo_catalogo()
        created_n = created_e = 0
        with self._driver.session() as s:
            s.run(
                "CREATE CONSTRAINT fechamento_id IF NOT EXISTS "
                "FOR (n:GraphNode) REQUIRE n.id IS UNIQUE"
            )
            for node in cat["nodes"]:
                lab = node.get("label") or "GraphNode"
                props = {k: v for k, v in node.items() if k != "label"}
                s.run(
                    f"""
                    MERGE (n:GraphNode:{lab} {{id: $id}})
                    SET n += $props, n.label = $lab
                    """,
                    id=node["id"],
                    props=props,
                    lab=lab,
                )
                created_n += 1
            for e in cat["edges"]:
                s.run(
                    """
                    MATCH (a:GraphNode {id: $src})
                    MATCH (b:GraphNode {id: $dst})
                    MERGE (a)-[r:REL {type: $rel}]->(b)
                    SET r.rel = $rel
                    """,
                    src=e["source"],
                    dst=e["target"],
                    rel=e["rel"],
                )
                created_e += 1
            # âncoras de domínio seguro-auto (pesquisa)
            s.run(
                """
                MERGE (d:Domain {id: 'seguro_auto'})
                SET d.name = 'seguro auto namastex'
                """
            )
            for pid, nome in (
                ("essencial", "Essencial"),
                ("completo", "Completo"),
                ("premium", "Premium"),
            ):
                s.run(
                    """
                    MATCH (p:Plano {id: $id})
                    MATCH (d:Domain {id: 'seguro_auto'})
                    MERGE (d)-[:HAS_PLAN]->(p)
                    SET p.nome = $nome
                    """,
                    id=f"plano:{pid}",
                    nome=nome,
                )
        log.info("Neo4j seed: %s nós, %s arestas", created_n, created_e)
        return {"nodes_upserted": created_n, "edges_upserted": created_e}

    def seed_dataset_anchors(self, outcomes: list[dict[str, Any]] | None = None) -> int:
        """Âncoras leves do corpus (outcome/plano) — base para GraphRAG incremental."""
        if self._driver is None and not self.connect():
            return 0
        samples = outcomes or [
            {"id": "outcome:ganho", "label": "ganho"},
            {"id": "outcome:perdido", "label": "perdido"},
            {"id": "outcome:em_negociacao", "label": "em_negociacao"},
            {"id": "etapa:aprovar_cotacao", "label": "aprovar_cotacao"},
            {"id": "etapa:emitir_apolice", "label": "emitir_apolice"},
        ]
        n = 0
        with self._driver.session() as s:
            # search_similar_closes filtra CorpusAnchor por `label` (não `id`) —
            # sem isso, essa busca (roda em toda cotação) faz label scan.
            s.run(
                "CREATE INDEX corpus_anchor_label IF NOT EXISTS "
                "FOR (x:CorpusAnchor) ON (x.label)"
            )
            for o in samples:
                s.run(
                    """
                    MERGE (x:CorpusAnchor {id: $id})
                    SET x.label = $label, x.source = 'dataset'
                    WITH x
                    MATCH (d:Domain {id: 'seguro_auto'})
                    MERGE (d)-[:HAS_ANCHOR]->(x)
                    """,
                    id=o["id"],
                    label=o["label"],
                )
                n += 1
            # ciclo feliz do dataset: cotar → aprovar → apólice
            s.run(
                """
                MATCH (a:CorpusAnchor {id: 'etapa:aprovar_cotacao'})
                MATCH (b:CorpusAnchor {id: 'etapa:emitir_apolice'})
                MATCH (g:CorpusAnchor {id: 'outcome:ganho'})
                MERGE (a)-[:NEXT]->(b)
                MERGE (b)-[:LEADS_TO]->(g)
                """
            )
            s.run(
                """
                MATCH (c:GraphNode {id: 'padrao:apresentar_cotacao|meia_30_50'})
                MATCH (a:CorpusAnchor {id: 'etapa:aprovar_cotacao'})
                MERGE (c)-[:THEN]->(a)
                """
            )
        return n

    def seed_taticas_objecao(self) -> dict[str, int]:
        """Materializa objecoes.TATICAS no grafo: Objecao -[:TEM_TATICA {ordem}]-> Tatica.

        Fonte de conteúdo continua sendo o dict Python (curado, ancorado em
        frameworks reais de vendas) — o grafo é a camada CONSULTÁVEL/persistente
        em cima dele, não uma duplicata cega: `orch_svc.objecoes.proxima_acao`
        lê de volta via `taticas_objecao()` em runtime (fallback pro dict se o
        Neo4j estiver fora — ver app/main.py `_taticas_provider`).
        """
        from orch_svc.objecoes import TATICAS

        if self._driver is None and not self.connect():
            raise RuntimeError("Neo4j offline — seed abortado")
        n_obj = n_tat = 0
        with self._driver.session() as s:
            s.run(
                "CREATE CONSTRAINT tatica_id IF NOT EXISTS "
                "FOR (t:Tatica) REQUIRE t.id IS UNIQUE"
            )
            # taticas_objecao() filtra Objecao por `tipo` a cada objeção — sem
            # constraint/índice, faz label scan (barato hoje com 4 nós, mas
            # errado de deixar sem, dado que tipo já é 1 nó por valor).
            s.run(
                "CREATE CONSTRAINT objecao_tipo IF NOT EXISTS "
                "FOR (o:Objecao) REQUIRE o.tipo IS UNIQUE"
            )
            for tipo, taticas in TATICAS.items():
                s.run("MERGE (o:Objecao {tipo: $tipo})", tipo=tipo)
                n_obj += 1
                for ordem, t in enumerate(taticas):
                    s.run(
                        """
                        MATCH (o:Objecao {tipo: $tipo})
                        MERGE (t:Tatica {id: $tid})
                        SET t.texto = $texto, t.framework = $framework, t.ordem = $ordem
                        MERGE (o)-[r:TEM_TATICA]->(t)
                        SET r.ordem = $ordem
                        """,
                        tipo=tipo,
                        tid=f"{tipo}:{ordem}",
                        texto=t.texto,
                        framework=t.framework,
                        ordem=ordem,
                    )
                    n_tat += 1
        log.info("Neo4j seed táticas: %s objeções, %s táticas", n_obj, n_tat)
        return {"objecoes": n_obj, "taticas": n_tat}

    def taticas_objecao(self, tipo: str) -> list[dict[str, Any]]:
        """Lê táticas do grafo pra uma objeção, ordenadas — usado em runtime.

        Retorna [] (não lança) se o Neo4j estiver fora/sem dado — o chamador
        (`orch_svc.objecoes.proxima_acao`) cai pro dict TATICAS hardcoded.
        """
        if self._driver is None and not self.connect():
            return []
        try:
            with self._driver.session() as s:
                rows = s.run(
                    """
                    MATCH (:Objecao {tipo: $tipo})-[r:TEM_TATICA]->(t:Tatica)
                    RETURN t.texto AS texto, t.framework AS framework, r.ordem AS ordem
                    ORDER BY r.ordem
                    """,
                    tipo=tipo,
                )
                return [dict(row) for row in rows]
        except Exception as exc:
            log.warning("taticas_objecao(%s) falhou: %s", tipo, exc)
            return []

    def ingest_conversations(self, convs: list[dict[str, Any]]) -> int:
        """Upsert nós Conversation + arestas OUTCOME / MENTIONS_PLAN / HAS_CLOSE."""
        if self._driver is None and not self.connect():
            raise RuntimeError("Neo4j offline")
        n = 0
        with self._driver.session() as s:
            s.run(
                "CREATE CONSTRAINT conversation_id IF NOT EXISTS "
                "FOR (c:Conversation) REQUIRE c.id IS UNIQUE"
            )
            # search_similar_closes filtra Plano por `plano_id` (não `id`, que já
            # tem índice via a constraint fechamento_id em :GraphNode) — sem isso,
            # essa busca (roda em toda cotação) faz label scan.
            s.run(
                "CREATE INDEX plano_plano_id IF NOT EXISTS "
                "FOR (p:Plano) ON (p.plano_id)"
            )
            for c in convs:
                s.run(
                    """
                    MERGE (c:Conversation {id: $id})
                    SET c.outcome = $outcome,
                        c.idade = $idade,
                        c.veiculo = $veiculo,
                        c.n_msgs = $n_msgs,
                        c.has_close = $has_close,
                        c.has_media = $has_media,
                        c.source = 'conversations.parquet'
                    WITH c
                    MERGE (o:CorpusAnchor {id: $oid})
                    SET o.label = $outcome, o.source = 'dataset'
                    MERGE (c)-[:HAS_OUTCOME]->(o)
                    """,
                    id=c["id"],
                    outcome=c.get("outcome") or "",
                    idade=c.get("idade"),
                    veiculo=c.get("veiculo") or "",
                    n_msgs=int(c.get("n_msgs") or 0),
                    has_close=bool(c.get("has_close")),
                    has_media=bool(c.get("has_media")),
                    oid=f"outcome:{c.get('outcome') or 'desconhecido'}",
                )
                for plano in c.get("planos") or []:
                    s.run(
                        """
                        MATCH (c:Conversation {id: $cid})
                        MERGE (p:GraphNode:Plano {id: $pid})
                        SET p.plano_id = $plano, p.label = 'Plano'
                        MERGE (c)-[:MENTIONS_PLAN]->(p)
                        """,
                        cid=c["id"],
                        pid=f"plano:{plano}",
                        plano=plano,
                    )
                if c.get("has_close"):
                    s.run(
                        """
                        MATCH (c:Conversation {id: $cid})
                        MATCH (a:CorpusAnchor {id: 'etapa:emitir_apolice'})
                        MERGE (c)-[:EXEMPLIFIES]->(a)
                        """,
                        cid=c["id"],
                    )
                n += 1
        log.info("Neo4j ingest conversations: %s", n)
        return n

    def search_similar_closes(self, plano_id: str | None = None, limit: int = 5) -> list[dict]:
        """Conversas ganho com sinal de fechamento (boleto/apólice), opcionalmente por plano."""
        if self._driver is None and not self.connect():
            return []
        with self._driver.session() as s:
            if plano_id:
                rows = s.run(
                    """
                    MATCH (c:Conversation)-[:HAS_OUTCOME]->(:CorpusAnchor {label: 'ganho'})
                    MATCH (c)-[:MENTIONS_PLAN]->(:Plano {plano_id: $plano})
                    WHERE c.has_close = true
                    RETURN c.id AS id, c.veiculo AS veiculo, c.idade AS idade, c.n_msgs AS n_msgs
                    LIMIT $limit
                    """,
                    plano=plano_id,
                    limit=limit,
                )
            else:
                rows = s.run(
                    """
                    MATCH (c:Conversation)-[:HAS_OUTCOME]->(:CorpusAnchor {label: 'ganho'})
                    WHERE c.has_close = true
                    RETURN c.id AS id, c.veiculo AS veiculo, c.idade AS idade, c.n_msgs AS n_msgs
                    LIMIT $limit
                    """,
                    limit=limit,
                )
            return [dict(r) for r in rows]

    def path_fechamento(self, conclusao_like: str, limit: int = 5) -> list[dict[str, Any]]:
        """Pesquisa caminhos FECHA_COM / THEN a partir de um id parcial."""
        if self._driver is None and not self.connect():
            return []
        with self._driver.session() as s:
            rows = s.run(
                """
                MATCH (n:GraphNode)
                WHERE n.id CONTAINS $q OR coalesce(n.acao,'') CONTAINS $q
                OPTIONAL MATCH path = (n)-[:REL|THEN*1..3]->(m)
                RETURN n.id AS start, [x IN nodes(path) | x.id] AS nodes,
                       [r IN relationships(path) | coalesce(r.rel, r.type, type(r))] AS rels
                LIMIT $limit
                """,
                q=conclusao_like,
                limit=limit,
            )
            return [dict(r) for r in rows]


_STORE: Neo4jGraph | None = None


def get_neo4j() -> Neo4jGraph:
    global _STORE
    if _STORE is None:
        _STORE = Neo4jGraph()
    return _STORE


def boot_neo4j() -> dict[str, Any]:
    """Conecta + seed + ingest dataset (paridade clone ↔ ambiente de demo)."""
    g = get_neo4j()
    if not g.enabled:
        return {"status": "disabled"}
    if not g.connect():
        return {"status": "down"}
    out: dict[str, Any] = {"status": "ok", "uri": g.uri}
    if os.environ.get("NEO4J_SEED_ON_BOOT", "1") in ("1", "true", "True"):
        try:
            out["seed"] = g.seed_fechamento_catalog()
            out["anchors"] = g.seed_dataset_anchors()
            out["taticas"] = g.seed_taticas_objecao()
        except Exception as exc:
            out["seed_error"] = str(exc)
    # Ingest conversas ganho do parquet (idempotente MERGE) — mesmo corpus do RAG.
    if os.environ.get("NEO4J_INGEST_DATASET_ON_BOOT", "1") in ("1", "true", "True"):
        try:
            from pathlib import Path

            from app.dataset_graph import build_conversation_nodes, load_parquet_rows

            path = Path("/app/dataset/conversations.parquet")
            if not path.exists():
                root = Path(__file__).resolve().parents[1]
                path = root / "dataset" / "conversations.parquet"
            if not path.exists():
                out["ingest_error"] = "parquet não encontrado"
            else:
                limit = int(os.environ.get("NEO4J_INGEST_LIMIT", "0") or "0") or None
                rows = load_parquet_rows(path)
                convs = build_conversation_nodes(
                    rows, outcomes={"ganho"}, limit=limit
                )
                out["ingest_conversations"] = g.ingest_conversations(convs)
                out["ingest_limit"] = limit or "all_ganho"
        except Exception as exc:
            out["ingest_error"] = str(exc)
    return out
