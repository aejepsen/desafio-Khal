# desafio-Khal

Solução do **Desafio Técnico FDE / AI Engineer (Namastex)** — um agente que atende
um lead de seguro auto de ponta a ponta: **conversa → qualifica → cota → decide**
(resolve ou escala pro humano, com critério explícito).

> Handoff longo / diário de engenharia: [`STATE.md`](./STATE.md).  
> Log de execução completa (com cotação): [`docs/log-execucao-real.md`](./docs/log-execucao-real.md)  
> · audit SQLite: `GET /audit/{conversation_id}` (ex.: `docs/audit-audit-7b-1784829171.json`).  
> · métricas modelo/agente: [`docs/metricas-modelo.md`](./docs/metricas-modelo.md).  
> · **curadoria E2E (9 cenários, LLM real):** [`docs/curadoria-e2e/relatorio.md`](./docs/curadoria-e2e/relatorio.md)  
> · **fluxo granular (lead → RAG/GraphRAG → prompt exato → LLM):** [`docs/fluxo-detalhado-entrevista.md`](./docs/fluxo-detalhado-entrevista.md).

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
| **svc-rag** | 8204 | few-shot `namastex_conversas` + GraphRAG (comunidades) |
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

UI mínima no browser (caixa de texto + resposta): http://localhost:8100/ui

Smokes úteis:

```bash
python scripts/e2e_ciclo_ganho.py      # lead → cota → apólice
python scripts/e2e_escalar_humano.py  # HITL (objeção / mídia / faixa)
python scripts/e2e_ocr_dados.py       # imagem → OCR → cotação
python scripts/curadoria_e2e.py       # 9 cenários (feliz/objeção/timeout/mídia/
                                       # OCR/pedido humano/pausa/faixa/PII) → relatório
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

### GraphRAG (svc-rag)

O `svc-rag` serve um artefato de **comunidades** (`GET /v1/community/{id}`) detectadas
via Louvain sobre o grafo Neo4j de conversas `ganho` (agrupadas por plano cotado +
faixa etária — grafo denso dentro do grupo, esparso entre grupos, pra dar estrutura
real ao algoritmo de comunidade). O `/v1/search`:
1. anota cada hit com sua comunidade e reordena pra reforçar a comunidade dominante
   entre os resultados (`score` vetorial não é alterado, só a ordem);
2. **expande** com até 2 membros da comunidade dominante que o vetor não trouxe
   (busca por id via `VectorStore.get_by_ids`, sem depender de query) — entram com
   score abaixo do menor hit vetorial real, nunca competindo de igual pra igual com
   similaridade genuína (`metadata.graphrag_expansion=true` sinaliza a origem).

Geração das comunidades é **offline** — o serviço só lê o artefato em runtime, não
abre conexão Neo4j (latência/resiliência, mesmo espírito do `resolver_fechamento`
local); a expansão usa só o vector store (Qdrant/InMemory), sem round-trip ao Neo4j:

```bash
docker compose up -d neo4j
python scripts/neo4j_seed_dataset.py --limit 1000   # popula o grafo (712 ganho)
NEO4J_URI=bolt://127.0.0.1:7687 python scripts/build_rag_communities.py
docker compose up --build svc-rag
curl -s http://localhost:8204/v1/community/0 -H "X-Internal-Key: dev-namastex-key"
```

Artefato versionado em `services/svc-rag/models/communities.json`; regenerar quando
o dataset/grafo mudar. Lógica pura testada em `test_community_builder.py`; re-rank
em `test_search_graphrag.py`.

### Curadoria E2E (revisão manual de qualidade)

`scripts/curadoria_e2e.py` roda 9 tipos de interação lead↔agente↔lead contra o
stack real (LLM `qwen2.5:7b` no loop, não mock) e grava a transcrição completa +
audit trail em [`docs/curadoria-e2e/relatorio.md`](./docs/curadoria-e2e/relatorio.md)
(raw por cenário em `docs/curadoria-e2e/raw/`). Não é gate automático — é material
pra revisão humana de tom/coerência, não só corretude técnica:

caminho feliz · objeção (reverte 3x → escala) · `/quote` indisponível
(`QUOTE_FAILURE_RATE=1` forçado) · mídia sem transcrição · OCR de dados reais ·
pedido explícito de humano · pausa respeitosa · recusa por faixa etária · PII mascarada.

```bash
python scripts/curadoria_e2e.py --skip quote_indisponivel   # cenários normais
QUOTE_FAILURE_RATE=1 docker compose up -d quote-api          # força falha
python scripts/curadoria_e2e.py --only quote_indisponivel
docker compose up -d quote-api                                # restaura 20%
```

Dessa revisão saíram 3 correções de qualidade (não de lógica de decisão — a
ação estava certa nos 9 cenários): formatação de moeda com ponto em vez de
vírgula pt-BR, LLM ocasionalmente inventando frase fora do rascunho, e cópia
HITL repetindo "atendente humano" duas vezes seguidas. Detalhe em `STATE.md`.

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
| **GraphRAG offline (artefato), não Neo4j em runtime no svc-rag** | Comunidades geradas 1x a partir do grafo (Louvain); `/v1/search` só lê o arquivo — evita depender de round-trip Neo4j em toda busca. |
| **Pedido de humano tem handler dedicado, prioridade máxima** | "Falar com atendente" coincidia com o regex de pausa (virava "sem problema, pensa com calma") ou era ignorado — achado ao auditar a camada de objeção. |
| **Regex de objeção exige contexto** (`azul seguros`, não `azul`; reclamação de preço, não pergunta neutra) | Sem isso, cor de veículo/pergunta de qualificação eram lidas como objeção e desviavam a conversa antes de qualquer cotação existir. |
| **Curadoria manual além do teste automatizado** | Assert de pass/fail não pega tom robótico, moeda mal formatada ou LLM inventando frase — só leitura humana da transcrição real pega isso. |
| **Ollama `qwen2.5:7b` Q4** | Cabe na 3060 12 GB com Whisper small; redação mais estável que 3B. |
| **OCR `media_base64`** | Lê dados enviados sem depender de URL pública. |
| **Audit SQLite por `conversation_id`** | Rastreabilidade exigida: cada passo com id + status. |
| **Observability raspando agente + inference** | Avaliar modelo (latência/tokens) e funil (HITL/cotação/fechamento) sem dashboard extra. |

Detalhe fino / histórico de sessões: [`STATE.md`](./STATE.md).  
Isolamento de dados: [`docs/isolamento-dados.md`](./docs/isolamento-dados.md).

## Régua do desafio → onde está

| Critério | Evidência |
|----------|-----------|
| Caminho feliz cotando | `scripts/e2e_ciclo_ganho.py` · `docs/log-execucao-real.md` · curadoria E2E |
| `/quote` falha | cliente resiliente · HITL grau A · eval R2 · curadoria E2E (`quote_indisponivel`, falha forçada) |
| HITL explícito | `scripts/e2e_escalar_humano.py` · `docs/hitl-dataset-validacao.md` · curadoria E2E (objeção/mídia/pedido de humano) |
| Rastreabilidade | `GET /audit/{conversation_id}` · eventos `step`/`status` |
| Desempenho do modelo | `GET /metrics` · `:8205/v1/overview` · [`docs/metricas-modelo.md`](./docs/metricas-modelo.md) |
| PII | guardrails + mask no audit · curadoria E2E (`pii_mascarada`) |
| Dataset | RAG `namastex_conversas` · Neo4j ganho · GraphRAG (comunidades) · evals |
| Qualidade da resposta (não só lógica) | [`docs/curadoria-e2e/relatorio.md`](./docs/curadoria-e2e/relatorio.md) — 9 cenários, revisão manual |

## Estrutura

```
desafio-Khal/
  docker-compose.yml       # solução completa
  docker-compose.cpu.yml   # ASR sem GPU
  docker-compose.demo.yml  # sem LLM real
  env.example
  app/                     # agente + audit + neo4j
  services/                # svc-* + media-asr/ocr (svc-rag/models/communities.json = GraphRAG)
  domains/seguro_auto/     # porteiro do body /quote
  scripts/                 # e2e ciclo/HITL/OCR/curadoria + build_rag_communities/neo4j_seed
  docs/                    # logs, evals, fixtures, metricas-modelo.md, curadoria-e2e/
```

Desfechos: `apresentar_cotacao` · `emitir_apolice` · `adiar_conversa` · `reverter_objecao` · `pedir_dado` · `recusar` · `escalar_humano`.
