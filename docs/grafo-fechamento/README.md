# Grafo de fechamento (seguro auto) — runtime in-process + Graphify

## Propósito

Amarra a **cotação pedida pelo lead** às **conclusões** e ao **fechamento parametrizado**
da resposta. Sem Neo4j no compose (proporcional ao desafio). Graphify (OSS) documenta
e visualiza este grafo.

## Nós

### NoConclusao
Campos: `acao`, `quote` (plano, premio, franquia), `coberturas`, `persona`.
Construído em `orch_svc.conclusao_graph.no_conclusao_de` a partir de `DecisaoCotacao`.

### FechamentoSpec
Molde + CTA fixa (detalhar coberturas OU comparar planos).
Catálogo em `orch_svc.fechamento_index`.

### Plano / Cobertura
Nós de domínio (`plano:essencial|completo|premium`, `cob:*`) no catálogo exportado.

## Arestas

| Rel | De | Para |
|-----|----|------|
| `FECHA_COM` | NoConclusao | FechamentoSpec |
| `PODE_GERAR` | Plano | NoConclusao (padrão cotar) |
| `INCLUI_COBERTURA` | NoConclusao (padrão) | Cobertura |

## Caminho runtime (`/chat`)

```
DecisaoCotacao + idade
  → NoConclusao
  → aresta FECHA_COM
  → FechamentoSpec (template preenchido)
  → LLM estiliza (validação de prêmio/CTA)
  → audit: conclusao_id + aresta
```

## Código

- `services/svc-orchestrator/src/orch_svc/conclusao_graph.py`
- `services/svc-orchestrator/src/orch_svc/fechamento_index.py`
- `services/svc-orchestrator/src/orch_svc/resposta.py`

## Export

- Runtime: `GET /graph/fechamento` → `export_grafo_catalogo()`
- Catálogo: `docs/grafo-fechamento/catalogo.json`
- Graphify OSS (code-only, sem API key): corpus em `docs/grafo-fechamento/src/`
  → saída `docs/grafo-fechamento/graphify-out/` (`graph.json`, `graph.html`, `GRAPH_REPORT.md`)
  God nodes: `resolver_fechamento`, `NoConclusao`, `FechamentoSpec`.
