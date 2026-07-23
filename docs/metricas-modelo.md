# Métricas de desempenho do modelo / agente

Duas camadas, agregadas no **svc-observability** (`:8205`):

| Camada | Fonte | O que mede |
|--------|--------|------------|
| **LLM (infra)** | `svc-inference` `/metrics` | `requests_total`, tokens in/out, `latency_ms_p50/p95`, `ttft_ms_*` |
| **Agente (negócio)** | `agente` `/metrics` (audit SQLite) | taxas HITL, redação LLM, cotação apresentada, fechamento |

## Como ler

```bash
KEY="${INTERNAL_KEY:-dev-namastex-key}"

# 1) raspa upstreams agora (agente + inference + rag + guardrails)
curl -s -X POST http://localhost:8205/v1/refresh \
  -H "X-Internal-Key: $KEY"

# 2) visão unificada (cada métrica com source=live|eval|estimate)
curl -s http://localhost:8205/v1/overview \
  -H "X-Internal-Key: $KEY" | python -m json.tool

# 3) texto Prometheus (scraping externo / Grafana)
curl -s http://localhost:8205/v1/prometheus \
  -H "X-Internal-Key: $KEY"
```

Direto no agente (sem agregar):

```bash
curl -s http://localhost:8100/metrics -H "X-Internal-Key: $KEY" | python -m json.tool
```

## KPIs do agente (audit)

| Métrica | Interpretação |
|---------|----------------|
| `llm_redacao_rate` | fração de turnos com resposta via LLM (sucesso) |
| `llm_fallback_rate` | fração com fallback (LLM falhou → template) |
| `hitl_rate` / `escala_sobre_turnos_rate` | pressão de escalação humana |
| `cotacao_apresentada_rate` | turnos que chegaram a cotação |
| `fechamento_sobre_cotacao_rate` | emitir_apolice / apresentar_cotacao |
| `resposta_llm_total` | volume absoluto de redação pelo modelo |

## Eval offline (source=eval)

Após um script e2e, dá para empurrar scores nomeados:

```bash
curl -s -X POST http://localhost:8205/v1/eval-results \
  -H "X-Internal-Key: $KEY" -H 'content-type: application/json' \
  -d '{"service":"agente","dataset_date":"2026-07-23","metrics":[
        {"name":"e2e_ciclo_ganho_pass","value":1},
        {"name":"e2e_hitl_pass","value":1}
      ]}'
```

Esses entram no overview com `source=eval` (não misturam com live).
