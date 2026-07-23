# STATE — desafio-Khal (handoff resumível)

> Log vivo do projeto. Padrão dos STATEs do portfólio (graphrag-onprem-toolkit).
> Serve para retomar em nova sessão / trocar de LLM sem perder contexto.

## Missão
Solução do **Desafio Técnico FDE / AI Engineer (Namastex)**: um agente que atende
um lead de seguro auto de ponta a ponta — **conversa → qualifica → cota → decide**
(resolve ou escala pro humano, com critério explícito). Repo:
`github.com/aejepsen/desafio-Khal` (PRIVADO durante dev; público na entrega).

## O que o desafio avalia (régua)
1. Funciona ponta a ponta (cota certo no caminho feliz).
2. **O que faz quando `/quote` falha** (20% 500/502/503 + lento 8s) — o que mais separa.
3. Critério de passar pro humano EXPLÍCITO e defensável.
4. Rastreabilidade (cada mensagem/cotação com id + status).
5. Cuidado com dados sensíveis (PII no dataset).
6. Qualidade (outro engenheiro entende as decisões).

## Estratégia de arquitetura (decisões)
**D1 — Reuso dos microsserviços prontos, NÃO cópia do AI-Orchestrator.**
Os 7 `svc-*` do `microservicos-ai-orchestrator` já são a versão desacoplada
(contract-first, OpenAPI /v1/, X-Internal-Key, /health, /metrics, OTel). Reuso o
CÓDIGO dos aderentes por VENDORING LIMPO (sem estado). NÃO copio o monólito
AI-Orchestrator. Serviços aderentes: guardrails (PII), rag (conversas), router
(etapa do lead), inference (LLM), observability (trilha), orchestrator (agente).
svc-evals = offline/opcional.

**D2 — Isolamento de dados (ver docs/isolamento-dados.md).**
Cada serviço reusado sobe com ESTADO DO ZERO. svc-rag populado SÓ do
`conversations.parquet` (coleção `namastex_conversas`). Nada de llm-wiki/spec_kb/
outros projetos vaza pro repo público. Razões: relevância, privacidade,
reprodutibilidade, segurança do repo público.

**D3 — Resiliência do /quote no cliente do orchestrator** (não serviço à parte):
retry + backoff + timeout + circuit breaker. 500/502/503 = OBSERVAÇÃO ao loop, não
exceção. Falha persistente → escala humano (nunca inventa cotação).

**D4 — Código NOVO (a "cola" do desafio, ~3 dias):** lógica de cotação de seguro
(campos veículo/idade/CNH), cliente resiliente do /quote, critério HITL explícito,
decisão sobre mídia sem transcrição.

**D5 — LLM plugável (troca por fim de créditos):** abstrair o provider (svc-inference
ou client) atrás de interface. Ordem de fallback: Claude API → Qwen local (Ollama)
→ outro. Trocar sem tocar na lógica do agente.

## Critério HITL (explícito — a definir/refinar)
Escala pro humano quando: dados insuficientes p/ cotar · mídia sem transcrição
(image/audio/document) · /quote falhou N vezes (circuit aberto) · idade/veículo
fora de faixa cotável · objeção complexa · pedido fora de escopo.

## Estado atual (2026-07-22 noite)
- Vendoring dos 6 `svc-*` + `quote-service` + compose esqueleto: feitos.
- **Domínio determinístico** `domains/seguro_auto/`: feito (monta body `/quote`, não calcula prêmio).
- **quote-api** testado local (`docker compose up --build quote-api`, porta **8000:8000**).
- Docs de regras + Archify do fluxo `/quote`: feitos.
- **RAG:** qdrant + svc-rag no ar; coleção `namastex_conversas` populada (712 conversas `ganho`,
  771 chunks). Script `scripts/ingest_namastex_conversas.py`.
- **PRÓXIMO:** (a) cliente HTTP resiliente do `/quote` no orchestrator;
  (b) wire domínio → agente; (c) wire orchestrator → `POST /v1/search`;
  (d) HITL em código; (e) adaptar prompts; (f) log de execução completa.

## Handoff / troca de LLM
Este STATE + README + docs/isolamento-dados.md + arquitetura.html
+ docs/fluxo-quote.sequence.html + docs/arvore-decisao-planos.html = fonte de verdade.
Ao trocar de LLM: ler este STATE, seguir do "PRÓXIMO". Provider atrás de interface (D5).

## VENDORING EXECUTADO (2026-07-22) — 6 svc-* limpos
`services/`: svc-guardrails/rag/router/inference/observability/orchestrator (5.3G→2.6M;
sem .venv/dados/segredos). Higiene: 0 .env reais, 0 segredos, 0 dados. Removidos
`svc-orchestrator/evals` (domínio antigo financas). **A ADAPTAR ao domínio cotação:**
prompts/config do svc-orchestrator (era financas/rh/estoque/vendas → agora seguro auto:
qualifica veículo/idade/CNH → cota → decide); golden do svc-router (etapas do lead);
config PII-br do svc-guardrails. **PRÓXIMO:** docker-compose funcional + ingestão do
dataset no svc-rag (coleção namastex_conversas) + lógica de cotação + cliente /quote resiliente.

## CONTRATO /quote + REAVALIAÇÃO de serviços (2026-07-22)
**quote-service copiado** (`./quote-service`, fornecido). Contrato:
- `POST /quote` QuoteRequest{plano_id(essencial|completo|premium), idade, veiculo_ano, cep?, data_inicio?}
  → 200 cotação · **422 cotacao_recusada** (regra: idade/veículo fora de faixa) ·
  400 payload_invalido · **500/502/503** instabilidade 20% (+ lento 8s).
- `GET /planos` tabela de regras · `GET /health`.
- Regras (quote_logic): faixa_etaria, idade_veiculo, regiao(cep alto risco), pro_rata 1º mês.
**Domínio determinístico (2026-07-22):** `domains/seguro_auto/` — após o agente marcar
dados como verificados, `build_quote_request(...)` normaliza/valida slots contra
`quote-service/data/plans.json` e devolve o JSON de `/quote` (ou missing/errors/refusals).
LLM não calcula nem monta o body. Prêmio só no quote-service.
**Extração do lead:** idade · veiculo_ano (ou de veiculo_texto) · cep · plano · data_inicio.
422/400 = observação ao loop; 500/502/503 = retry+circuit → escala humano.
**REAVALIAÇÃO (reuso judicioso, D1):** svc-router tem 9 refs do domínio antigo
(multi-domínio financas/rh/estoque/vendas). O fluxo do desafio é LINEAR (qualifica→cota→
decide), não multi-domínio → **svc-router provavelmente DISPENSÁVEL** ou re-proposto p/
classificar INTENÇÃO (qualificar/objeção/pedir-humano). Decisão: avaliar na implementação.
Núcleo confirmado: orchestrator + guardrails + rag + inference + observability.

## SESSÃO 2026-07-22 (noite) — o que foi feito

### quote-api / compose
- Corrigido mapeamento de porta no `docker-compose.yml`: container escuta **8000**
  (`Dockerfile`/`uvicorn --port 8000`); era `8080:8080` (quebrado) → agora `8000:8000`.
- Subido `quote-api` com `docker compose up --build -d quote-api`.
- Testados endpoints: `GET /health`, `GET /planos`, `POST /quote`.
- Snapshots salvos em `data/quote-api-snapshots/`
  (`health.json`, `planos.json`, `openapi.json`, `quote_example_200.json`).
  Nota: pasta `data/` está no `.gitignore` (PII/dataset) — snapshots locais.

### Contrato POST /quote (confirmado no código + OpenAPI)
**Request body** (domínio monta isto):
`{plano_id?, idade, veiculo_ano, cep?, data_inicio?}` —
obrigatórios: `idade`, `veiculo_ano`; default `plano_id=essencial`.
**Response 200:** `plano_id`, `plano_nome`, `premio_mensal`, `franquia`, `coberturas`,
`multiplicadores`, `carencia`, `moeda`, opcional `primeiro_pagamento_pro_rata`.
**422** `cotacao_recusada` · **400** `payload_invalido` · **5xx** instabilidade.
Campo correto: `veiculo_ano` (não `ano_veiculo`).
`plano_id = (payload.get("plano_id") or "essencial").lower()` no `quote_logic` é
**default**, não hardcode — `completo`/`premium` seguem dinâmicos via `plans.json`.

### Domínio determinístico `domains/seguro_auto/`
- Papel: **porteiro** — após `verified=True`, normaliza/valida slots contra
  `quote-service/data/plans.json` e devolve body do POST (ou missing/errors/refusals).
- **Não** chama `quote_logic.py`; **não** calcula prêmio/carência/pro-rata.
- Cálculo fica no servidor: `main.py` → `cotar(req.model_dump())` → `quote_logic`.
- Testes: `domains/seguro_auto/tests/` (30 passed).
- Matriz mock + XML: `domains/seguro_auto/evals/results/domain_quote_cases.xml`
  (colunas input de planos/slots + output do JSON `/quote`).
- Cruzamento domain ↔ quote_logic (recusa/aceitação) alinhado nos casos mockados.

### Documentação visual
- `docs/arvore-decisao-planos.md` + `.html` — árvore de regras de `plans.json`
  (1 box recusa veículo >20; carência 30d roubo/furto como condição sim/não).
- Archify sequence do fluxo: `docs/fluxo-quote.sequence.json` →
  `docs/fluxo-quote.sequence.html` (Archify 2.12) —
  agente → domínio → POST `/quote` → main → cotar → plans.json → resposta.

## SESSÃO 2026-07-22 (noite+) — ingestão svc-rag

### Chaves (portfolio `microservicos-ai-orchestrator`)
- svc-rag usa **`INTERNAL_KEY`** (header `X-Internal-Key`) — fail-closed.
  `.env.example` do portfolio: placeholder `troque-me`. No desafio: `dev-namastex-key`
  (`.env.example` local; `.env` gitignored).
- **`QDRANT_API_KEY`**: opcional; Qdrant local (imagem docker) **sem key**.
  Portfolio tem a variável no `.env` raiz — não necessária aqui.
- **`VOYAGE_API_KEY`**: existe no portfolio; **não** usada pelo svc-rag (SBERT local).
- Compose corrigido: `INTERNAL_KEY` (antes `X_INTERNAL_KEY` errado),
  `ALLOW_LOCAL_STORE=1` (Qdrant em rede docker = IP privado; anti-SSRF),
  porta `8204:8204`, `VECTOR_STORE=qdrant`.

### Ingestão executada
```bash
docker compose up --build -d qdrant svc-rag
INTERNAL_KEY=dev-namastex-key python3 scripts/ingest_namastex_conversas.py --outcome ganho
```
- Health: embedder ok, vector_store ok, graphrag absent.
- Resultado: **712 docs / 771 chunks** na coleção `namastex_conversas`.
- Smoke search OK (`seguro auto corolla idade`, etc.).
- Plano: `docs/plano-ingestao-rag.md`.

## SESSÃO 2026-07-22 (noite++) — cliente resiliente /quote (item PRÓXIMO-a FEITO)
`services/svc-orchestrator/src/orch_svc/quote_client.py`: `ResilientQuoteClient`
(reusa `circuit.py`). 4 desfechos + escalonamento:
- 200 → QUOTED · 422 → REFUSED (observação, NÃO reintenta) · 400 → INVALID (falta dado)
- 5xx/timeout → retry + backoff (2^n) + circuit (3 falhas → OPEN) · esgota/OPEN → UNAVAILABLE + escalate=True (nunca inventa cotação).
- 4xx não conta no breaker (semântica do circuit.py). Sleep injetável p/ teste.
`tests/test_quote_client.py`: **7 passed** (quoted/refused-sem-retry/invalid/retry-sucesso/
timeout/esgota-escala/circuito-aberto-escala).
**PRÓXIMO:** (b) wire domínio seguro_auto → agente (body → quote_client); (c) wire
orchestrator → svc-rag POST /v1/search; (d) critério HITL completo em código
(escalate já cobre /quote; falta: dados insuficientes, mídia sem transcrição, idade/veículo
fora de faixa via REFUSED); (e) adaptar prompts + DISPENSAR svc-router (fluxo linear);
(f) log de execução completa (entregável).

## SESSÃO 2026-07-22 (noite+++) — decisão de cotação: (b)+(c)+(d) integrados
`orch_svc/cotacao_flow.py`: `decidir_cotacao(build_result, quote_client, query, rag)`.
- (b) porteiro seguro_auto (BuildResult) → missing=pedir_dado · refusals=recusar · errors=pedir_correcao.
- (c) RAG few-shot (coleção namastex_conversas) — enriquecimento; falha NÃO bloqueia (degrada gracioso).
- (d) HITL: /quote QUOTED→apresentar · REFUSED→recusar · INVALID→pedir_correcao · UNAVAILABLE→escalar_humano(escalate).
Injeção de dependência (testável sem cross-import). `tests/test_cotacao_flow.py`: 6 passed
(+ 7 do quote_client = 13). **PRÓXIMO:** (e) wire no grafo orchestrator.py (nó de cotação
real chamando cotacao_flow) + adaptar prompts + DISPENSAR svc-router (fluxo linear, remove ~40 refs);
(f) log de execução completa (entregável); ligar rag/quote clients reais no app.
