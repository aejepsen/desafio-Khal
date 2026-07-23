# desafio-Khal

Solução do **Desafio Técnico FDE / AI Engineer (Namastex)** — um agente que atende
um lead de seguro auto de ponta a ponta: **conversa → qualifica → cota → decide**
(resolve ou escala pro humano, com critério explícito).

> Handoff longo / diário de engenharia: [`STATE.md`](./STATE.md).  
> Log de execução completa (com cotação): [`docs/log-execucao-real.md`](./docs/log-execucao-real.md)  
> · audit SQLite: `GET /audit/{conversation_id}` (ex.: `docs/audit-audit-7b-1784829171.json`).  
> · métricas modelo/agente: [`docs/metricas-modelo.md`](./docs/metricas-modelo.md).

## Arquitetura

Diagrama: [`arquitetura.html`](./arquitetura.html).

Um **agente de cotação** (`app/main.py` + `orch_svc`) integra microsserviços
(`svc-guardrails`, `svc-rag`, `svc-inference`, `svc-observability`) + **ASR/OCR**
+ **quote-service** (API do desafio) + **Ollama** (LLM local) + **Neo4j** (grafo).

| Serviço | Porta | Papel |
|---------|-------|--------|
| **agente** | 8100 | `POST /chat` · `GET /metrics` (KPIs audit) · `GET /audit/{id}` |
| **quote-api** | 8000 | cotação (20% 5xx + lentidão) |
| **svc-guardrails** | 8200 | sanitize + PII + injection |
| **svc-inference** | 8202 | extract/redação via LLM · tokens/latência em `/metrics` |
| **svc-rag** | 8204 | few-shot `namastex_conversas` |
| **svc-observability** | 8205 | scrape + `GET /v1/overview` · `GET /v1/prometheus` |
| **svc-media-asr** | 8210 | Whisper `small` (áudio → texto) |
| **svc-media-ocr** | 8211 | Tesseract (imagem/PDF → texto) |
| **ollama** | 11434 | `qwen2.5:7b` (Q4) |
| **qdrant** | 6333 | vetores |
| **neo4j** | 7474 / 7687 | grafo (Browser + Bolt) |

## Hardware recomendado (stack completa)

Um único `docker compose up` sobe **tudo**. Orçamento típico:

| Peça | Device | VRAM / RAM |
|------|--------|------------|
| Ollama `qwen2.5:7b` (Q4) | GPU | ~**4.5–5.5 GB VRAM** |
| faster-whisper **`small`** | GPU | ~**2–3 GB VRAM** |
| Tesseract OCR | CPU | ~**0.5–1 GB RAM** |
| SBERT (rag + guardrails) | CPU | ~**1–2 GB RAM** |
| Neo4j (heap+pagecache default) | CPU | ~**1–2 GB RAM** |
| Qdrant + APIs + Docker | CPU | ~**2–4 GB RAM** |
| **Total GPU** | | **~8–10 GB VRAM** (cabe na **3060 12 GB**) |
| **Total RAM host** | | **≥16 GB** (confortável **32 GB**) |

**Recomendado:** GPU **NVIDIA ≥ 8 GB VRAM** (ideal **12 GB**) + **≥16 GB RAM** + [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html).

| Cenário | Comando | Notas |
|---------|---------|--------|
| **Completo (GPU)** | `docker compose up --build` | ASR em CUDA |
| Sem NVIDIA | `docker compose -f docker-compose.yml -f docker-compose.cpu.yml up --build` | Whisper em CPU |
| Offline sem LLM | `… -f docker-compose.demo.yml` | `BACKEND=demo`, sem Ollama |

## Como rodar

```bash
cp env.example .env
docker compose up --build
# 1ª vez: pull qwen2.5:7b (~4.7 GB) + build das imagens (pode demorar)
```

O clone já traz `dataset/conversations.parquet` (**sintético** — ver
[`dataset/DICIONARIO.md`](./dataset/DICIONARIO.md)). No `docker compose up`, o corpus
é populado **automaticamente** (paridade com o ambiente de demo):

- **RAG** (`namastex_conversas`, outcome `ganho`) — serviço one-shot `rag-ingest`
- **Neo4j** (catálogo + conversas `ganho`) — boot do agente
  (`NEO4J_INGEST_DATASET_ON_BOOT=1`)

Reingest manual (idempotente):

```bash
python scripts/ingest_namastex_conversas.py
curl -X POST 'http://localhost:8100/graph/neo4j/seed-dataset?outcome=ganho&limit=0'
```

```bash
curl -s http://localhost:8100/health
curl -s -X POST http://localhost:8100/chat -H 'content-type: application/json' \
  -d '{"conversation_id":"c1","mensagem":"tenho 35 anos, Gol 2020, plano essencial, cep 01310100"}'
```

Smokes úteis:

```bash
python scripts/e2e_ciclo_ganho.py      # lead → cota → apólice
python scripts/e2e_escalar_humano.py  # HITL (objeção / mídia / faixa)
python scripts/e2e_ocr_dados.py       # imagem → OCR → cotação
```

Métricas de desempenho (LLM + KPIs do agente):

```bash
KEY="${INTERNAL_KEY:-dev-namastex-key}"
curl -s http://localhost:8100/metrics -H "X-Internal-Key: $KEY"
curl -s -X POST http://localhost:8205/v1/refresh -H "X-Internal-Key: $KEY"
curl -s http://localhost:8205/v1/overview -H "X-Internal-Key: $KEY"
```

Detalhe das taxas (HITL, redação LLM, fechamento) e eval offline:
[`docs/metricas-modelo.md`](./docs/metricas-modelo.md).

Neo4j Browser: http://localhost:7474 (`neo4j` / senha no `.env`).

Áudio (ASR): `message_type=audio` + `media_url`.  
OCR: `message_type=image|document` + `media_url` **ou** `media_base64`.

Falha de ASR/OCR → HITL (`mídia sem transcrição`).  
Falha persistente de `/quote` → retry/circuit → `escalar_humano` (sem inventar prêmio).

## Decisões (e por quê)

| Decisão | Por quê |
|---------|---------|
| **Reusar `svc-*` + domínio novo** (não copiar monólito) | Contrato `/v1/` pronto; o desafio é a cola (agente + `/quote` + HITL). |
| **Resiliência no cliente `/quote`** (retry + backoff + circuit) | A API simula legado (5xx / lentidão). Esgotou → humano; **nunca** inventa prêmio. |
| **HITL explícito** | Mídia sem texto, quote down, objeção esgotada, fora de faixa, max turnos — defensável na régua. |
| **Mensagem HITL grau A (template)** | Lead ouve “instabilidade / atendente”; jargão `503`/circuito fica só no **audit**. |
| **PII só mascarada em log** | CEP/CPF precisamos cotar; mask em audit/SQLite/`[CEP]`/`[CPF]`. |
| **Dataset → RAG + Neo4j + táticas** | Few-shot, closes ganho, padrões de objeção; não treinar modelo do zero. |
| **Ollama `qwen2.5:7b` Q4** | Cabe na 3060 12 GB com Whisper small; redação mais estável que 3B. |
| **OCR `media_base64`** | Lê dados enviados sem depender de URL pública. |
| **Audit SQLite por `conversation_id`** | Rastreabilidade exigida: cada passo com id + status. |
| **Observability raspando agente + inference** | Avaliar modelo (latência/tokens) e funil (HITL/cotação/fechamento) sem dashboard extra. |

Detalhe fino / histórico de sessões: [`STATE.md`](./STATE.md).  
Isolamento de dados: [`docs/isolamento-dados.md`](./docs/isolamento-dados.md).

## Régua do desafio → onde está

| Critério | Evidência |
|----------|-----------|
| Caminho feliz cotando | `scripts/e2e_ciclo_ganho.py` · `docs/log-execucao-real.md` |
| `/quote` falha | cliente resiliente · HITL grau A · eval R2 |
| HITL explícito | `scripts/e2e_escalar_humano.py` · `docs/hitl-dataset-validacao.md` |
| Rastreabilidade | `GET /audit/{conversation_id}` · eventos `step`/`status` |
| Desempenho do modelo | `GET /metrics` · `:8205/v1/overview` · [`docs/metricas-modelo.md`](./docs/metricas-modelo.md) |
| PII | guardrails + mask no audit |
| Dataset | RAG `namastex_conversas` · Neo4j ganho · evals |

## Estrutura

```
desafio-Khal/
  docker-compose.yml       # solução completa
  docker-compose.cpu.yml   # ASR sem GPU
  docker-compose.demo.yml  # sem LLM real
  env.example
  app/                     # agente + audit + neo4j
  services/                # svc-* + media-asr/ocr
  domains/seguro_auto/     # porteiro do body /quote
  scripts/                 # e2e ciclo / HITL / OCR
  docs/                    # logs, evals, fixtures, metricas-modelo.md
```

Desfechos: `apresentar_cotacao` · `emitir_apolice` · `reverter_objecao` · `pedir_dado` · `recusar` · `escalar_humano`.
