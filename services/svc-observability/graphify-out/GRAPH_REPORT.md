# Graph Report - svc-observability  (2026-07-10)

## Corpus Check
- 30 files · ~8,919 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 226 nodes · 412 edges · 16 communities (14 shown, 2 thin omitted)
- Extraction: 73% EXTRACTED · 27% INFERRED · 0% AMBIGUOUS · INFERRED: 113 edges (avg confidence: 0.72)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cd497a4d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- FakeScraper
- Metric
- State
- app.py
- SPEC — svc-observability v1.0
- MetricsExport
- DECISIONS — svc-observability
- test_otel_metrics.py
- svc-observability
- init_tracing
- conftest.py
- BACKLOG.md
- svc-observability

## God Nodes (most connected - your core abstractions)
1. `Metric` - 31 edges
2. `FakeScraper` - 30 edges
3. `State` - 25 edges
4. `Aggregator` - 23 edges
5. `create_app()` - 16 edges
6. `SPEC — svc-observability v1.0` - 16 edges
7. `render()` - 15 edges
8. `Settings` - 13 edges
9. `Determinístico para gates: payloads fixos por serviço; pode falhar.` - 11 edges
10. `Scraper` - 10 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `FakeScraper`  [INFERRED]
  svc-observability/evals/bench_latency.py → svc-observability/src/obs_svc/scraper.py
- `ServiceState` --uses--> `Metric`  [INFERRED]
  svc-observability/src/obs_svc/aggregator.py → svc-observability/src/obs_svc/model.py
- `Aggregator` --uses--> `Metric`  [INFERRED]
  svc-observability/src/obs_svc/aggregator.py → svc-observability/src/obs_svc/model.py
- `State` --uses--> `Aggregator`  [INFERRED]
  svc-observability/src/obs_svc/app.py → svc-observability/src/obs_svc/aggregator.py
- `State` --uses--> `FakeScraper`  [INFERRED]
  svc-observability/src/obs_svc/app.py → svc-observability/src/obs_svc/scraper.py

## Import Cycles
- None detected.

## Communities (16 total, 2 thin omitted)

### Community 0 - "FakeScraper"
Cohesion: 0.10
Nodes (30): main(), G2 — agregação: funde upstreams; serviço fora → parcial + stale (determinístico), main(), G3 — rótulo de fonte: live/eval/estimate corretos; ARMADILHA projeção != live., Protocol, Aggregator, Agregador: raspa upstreams (live), guarda cache stale, ingere eval, deriva estim, ServiceState (+22 more)

### Community 1 - "Metric"
Cohesion: 0.11
Nodes (21): main(), G4 — exposição Prometheus: texto parseável (HELP/TYPE/linhas), labels corretos., Raspa todos os upstreams. Retorna (ok, failed). Falha não derruba os outros., Derivados = ESTIMATE por construção (projeção agregada, não medida)., Metric, Modelo de métrica normalizada + fonte., _escape_label(), Exposição em texto Prometheus. Formato: # HELP / # TYPE / name{labels} value.  N (+13 more)

### Community 2 - "State"
Cohesion: 0.15
Nodes (23): BaseModel, main(), create_app(), Any, State, _to_model(), load_settings(), Configuração 12-factor via env. Defaults de segurança fail-closed. (+15 more)

### Community 3 - "app.py"
Cohesion: 0.10
Nodes (19): G8 — overhead do /v1/overview (cache/agregação em memória): P95 < 40 ms., FastAPI, Request, svc-observability — API FastAPI. Swagger off; stack só em log., _env_bool(), client_ip(), add_security_headers(), Any (+11 more)

### Community 4 - "SPEC — svc-observability v1.0"
Cohesion: 0.08
Nodes (24): 0. Metadados, 10. Gates de aceitação, 11. Plano de fases, 12. Regras para o agente, 13. Riscos, 14. Definição de DONE, 1. Contexto e problema, 2. Objetivo (uma frase) (+16 more)

### Community 5 - "MetricsExport"
Cohesion: 0.20
Nodes (9): init_metrics_export(), MetricsExport, Any, D7 — Export OTLP de métricas agregadas (push opt-in para SaaS).  OTLP_METRICS_EN, Registra ObservableGauges por nome de métrica agregada (lazy).      Nomes novos, Encerra o export em background (flush final com timeout curto)., Cria instrumentos para nomes ainda não registrados. Retorna nº de novos., Liga export OTLP de métricas se OTLP_METRICS_ENABLED=1.      `reader` injetável (+1 more)

### Community 6 - "DECISIONS — svc-observability"
Cohesion: 0.20
Nodes (9): D1 — Agregador, nao Collector OTLP, D2 — Scraper adapter + FakeScraper, D3 — Fonte inegociavel; derivados nascem estimate, D4 — Degradacao com cache stale, D5 — Prometheus em texto puro (sem client pesado), D6 — Anti-SSRF nas URLs de upstream, D7 — Export OTLP de metricas para SaaS (opt-in, fail-open), DECISIONS — svc-observability (+1 more)

### Community 7 - "test_otel_metrics.py"
Cohesion: 0.29
Nodes (9): _collect(), G-OTLP — export OTLP de métricas agregadas (D7): opt-in, fiel à fonte, fail-open, G-OTLP-1: sem OTLP_METRICS_ENABLED → no-op absoluto., G-OTLP-2: valores e atributos (service/source/stale) idênticos ao overview., G-OTLP-3: endpoint morto não derruba init, refresh nem API., _settings(), test_desligado_por_default(), test_export_reflete_agregado_com_fonte() (+1 more)

### Community 8 - "svc-observability"
Cohesion: 0.22
Nodes (8): Como rodar, Contrato, Export OTLP para SaaS (opt-in — D7), Gates (medidos), Notas, Regra de fonte (inegociável), svc-observability, Uso

### Community 10 - "init_tracing"
Cohesion: 0.40
Nodes (4): init_tracing(), Any, DS-01 — OTel real: spans OTLP (FastAPI server + httpx client).  OTEL_ENABLED=0 (, Liga traces OTLP se OTEL_ENABLED=1. Retorna True se ativo.

### Community 11 - "conftest.py"
Cohesion: 0.70
Nodes (3): client(), settings(), state()

## Knowledge Gaps
- **38 isolated node(s):** `svc-observability`, `BACKLOG — svc-observability`, `D1 — Agregador, nao Collector OTLP`, `D2 — Scraper adapter + FakeScraper`, `D3 — Fonte inegociavel; derivados nascem estimate` (+33 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Metric` connect `Metric` to `FakeScraper`?**
  _High betweenness centrality (0.122) - this node is a cross-community bridge._
- **Why does `State` connect `State` to `FakeScraper`, `Metric`, `app.py`, `test_otel_metrics.py`, `conftest.py`?**
  _High betweenness centrality (0.111) - this node is a cross-community bridge._
- **Why does `FakeScraper` connect `FakeScraper` to `Metric`, `State`, `app.py`, `test_otel_metrics.py`, `conftest.py`?**
  _High betweenness centrality (0.107) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `Metric` (e.g. with `main()` and `Aggregator`) actually correct?**
  _`Metric` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `FakeScraper` (e.g. with `main()` and `main()`) actually correct?**
  _`FakeScraper` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `State` (e.g. with `main()` and `Aggregator`) actually correct?**
  _`State` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `Aggregator` (e.g. with `main()` and `main()`) actually correct?**
  _`Aggregator` has 15 INFERRED edges - model-reasoned connections that need verification._