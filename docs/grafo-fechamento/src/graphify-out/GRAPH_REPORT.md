# Graph Report - docs/grafo-fechamento/src  (2026-07-23)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 33 nodes · 56 edges · 6 communities (5 shown, 1 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 7 edges (avg confidence: 0.63)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6cd6ca2e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- fechamento_index.py
- no_conclusao_de
- resolver_fechamento
- conclusao_graph.py
- NoConclusao
- chave_padrao_fechamento

## God Nodes (most connected - your core abstractions)
1. `resolver_fechamento()` - 11 edges
2. `NoConclusao` - 8 edges
3. `FechamentoSpec` - 7 edges
4. `no_conclusao_de()` - 6 edges
5. `ArestaFechamento` - 5 edges
6. `chave_padrao_fechamento()` - 5 edges
7. `aresta_fecha_com()` - 5 edges
8. `lookup_fechamento()` - 5 edges
9. `ResolucaoFechamento` - 4 edges
10. `validar_fechamento_llm()` - 4 edges

## Surprising Connections (you probably didn't know these)
- `FechamentoSpec` --uses--> `NoConclusao`  [INFERRED]
  fechamento_index.py → conclusao_graph.py
- `FechamentoSpec` --uses--> `ArestaFechamento`  [INFERRED]
  fechamento_index.py → conclusao_graph.py
- `ResolucaoFechamento` --uses--> `ArestaFechamento`  [INFERRED]
  fechamento_index.py → conclusao_graph.py
- `resolver_fechamento()` --calls--> `no_conclusao_de()`  [INFERRED]
  fechamento_index.py → conclusao_graph.py
- `resolver_fechamento()` --calls--> `chave_padrao_fechamento()`  [INFERRED]
  fechamento_index.py → conclusao_graph.py

## Import Cycles
- None detected.

## Communities (6 total, 1 thin omitted)

### Community 0 - "fechamento_index.py"
Cohesion: 0.39
Nodes (7): _contem_fato(), _contem_premio(), FechamentoSpec, Índice de fechamentos — resolve aresta FECHA_COM do grafo de conclusão.  Runtime, Nós FechamentoSpec do grafo (destino das arestas FECHA_COM)., _spec_catalog(), validar_fechamento_llm()

### Community 1 - "no_conclusao_de"
Cohesion: 0.29
Nodes (7): Any, _as_float(), export_grafo_catalogo(), no_conclusao_de(), DecisaoCotacao, Catálogo estático de nós-padrão + arestas (p/ Graphify / docs / auditoria)., Constrói o nó de conclusão a partir da decisão + persona.

### Community 2 - "resolver_fechamento"
Cohesion: 0.33
Nodes (7): _corpo_cotacao(), _fill(), lookup_fechamento(), DecisaoCotacao, API estável: (spec, texto, params). Preferir `resolver_fechamento` p/ grafo., Percorre NoConclusao -FECHA_COM-> FechamentoSpec e preenche o molde., resolver_fechamento()

### Community 3 - "conclusao_graph.py"
Cohesion: 0.50
Nodes (4): aresta_fecha_com(), ArestaFechamento, Grafo formal de fechamento (leve, in-process) — sem Neo4j.  Nós:   NoConclusao{a, Aresta tipada: conclusão → molde de resposta.

### Community 4 - "NoConclusao"
Cohesion: 0.50
Nodes (3): NoConclusao, Nó de conclusão do turno — amarra pedido cotado aos fatos do fechamento., ResolucaoFechamento

## Knowledge Gaps
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `resolver_fechamento()` connect `resolver_fechamento` to `fechamento_index.py`, `no_conclusao_de`, `conclusao_graph.py`, `NoConclusao`, `chave_padrao_fechamento`?**
  _High betweenness centrality (0.348) - this node is a cross-community bridge._
- **Why does `no_conclusao_de()` connect `no_conclusao_de` to `resolver_fechamento`, `conclusao_graph.py`, `NoConclusao`?**
  _High betweenness centrality (0.208) - this node is a cross-community bridge._
- **Why does `NoConclusao` connect `NoConclusao` to `fechamento_index.py`, `no_conclusao_de`, `conclusao_graph.py`, `chave_padrao_fechamento`?**
  _High betweenness centrality (0.195) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `resolver_fechamento()` (e.g. with `aresta_fecha_com()` and `chave_padrao_fechamento()`) actually correct?**
  _`resolver_fechamento()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `NoConclusao` (e.g. with `FechamentoSpec` and `ResolucaoFechamento`) actually correct?**
  _`NoConclusao` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `FechamentoSpec` (e.g. with `ArestaFechamento` and `NoConclusao`) actually correct?**
  _`FechamentoSpec` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `ArestaFechamento` (e.g. with `FechamentoSpec` and `ResolucaoFechamento`) actually correct?**
  _`ArestaFechamento` has 2 INFERRED edges - model-reasoned connections that need verification._