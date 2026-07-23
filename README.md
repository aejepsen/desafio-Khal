# desafio-Khal

Solução do **Desafio Técnico FDE / AI Engineer (Namastex)** — um agente que atende
um lead de seguro auto de ponta a ponta: **conversa → qualifica → cota → decide**
(resolve ou escala pro humano, com critério explícito).

> Ver [`STATE.md`](./STATE.md) para handoff / decisões de engenharia.

## Arquitetura

Diagrama: [`arquitetura.html`](./arquitetura.html).

Um **agente de cotação** (`app/main.py` + `orch_svc`) integra microsserviços
(`svc-guardrails`, `svc-rag`, `svc-inference`, `svc-observability`) + **ASR/OCR**
+ **quote-service** (API do desafio) + **Ollama** (LLM local).

| Serviço | Porta | Papel |
|---------|-------|--------|
| **agente** | 8100 | `POST /chat` multi-turno |
| **quote-api** | 8000 | cotação (20% 5xx + lentidão) |
| **svc-guardrails** | 8200 | sanitize + PII + injection |
| **svc-inference** | 8202 | extract/redação via LLM |
| **svc-rag** | 8204 | few-shot `namastex_conversas` |
| **svc-observability** | 8205 | métricas / trilha |
| **svc-media-asr** | 8210 | Whisper `small` (áudio → texto) |
| **svc-media-ocr** | 8211 | Tesseract (imagem/PDF → texto) |
| **ollama** | 11434 | `qwen2.5:7b` (Q4) |
| **qdrant** | 6333 | vetores |
| **neo4j** | 7474 / 7687 | grafo (Browser + Bolt) |

## Hardware recomendado (stack completa)

Um único `docker compose up` sobe **tudo**. Orçamento típico (combo sem stress):

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

**Recomendado para a solução completa:** GPU **NVIDIA ≥ 8 GB VRAM** (ideal **12 GB**, ex. RTX 3060) + **≥16 GB RAM** + [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html).

| Cenário | Comando | Notas |
|---------|---------|--------|
| **Completo (GPU)** | `docker compose up --build` | ASR em CUDA |
| Sem NVIDIA | `docker compose -f docker-compose.yml -f docker-compose.cpu.yml up --build` | Whisper em CPU (lento) |
| Offline sem LLM | `… -f docker-compose.demo.yml` | `BACKEND=demo`, sem Ollama |

Sem GPU e sem o override `cpu.yml`, o serviço ASR pode falhar ao reservar `gpus: all`.

## Como rodar

```bash
cp env.example .env
docker compose up --build
# 1ª vez: pull qwen2.5:3b + build das imagens (pode demorar)
```

```bash
curl -s http://localhost:8100/health
curl -s -X POST http://localhost:8100/chat -H 'content-type: application/json' \
  -d '{"conversation_id":"c1","mensagem":"tenho 35 anos, Gol 2020, plano essencial, cep 01310100"}'
```

Neo4j (Browser http://localhost:7474 — user `neo4j` / senha `.env`):
```bash
curl -s http://localhost:8100/graph/neo4j
curl -s 'http://localhost:8100/graph/neo4j/search?q=apresentar_cotacao'
```

Áudio (ASR integrado):
```bash
curl -s -X POST http://localhost:8100/chat -H 'content-type: application/json' \
  -d '{"conversation_id":"a1","mensagem":"[áudio]","message_type":"audio","media_url":"http://<host-acessivel-do-container>/voz.mp3"}'
```

OCR de dados enviados (imagem/PDF em base64 — sem URL externa):
```bash
# ver scripts/e2e_ocr_dados.py — fixture docs/fixtures/ocr_dados_cotacao.png
python scripts/e2e_ocr_dados.py
```

Falha de ASR/OCR → HITL (`mídia sem transcrição`). Falha de `/quote` → retry/circuit → HITL (nunca inventa prêmio).

## Princípios (régua do desafio)

- Resiliência ao `/quote` (20% 5xx + 8s)
- HITL explícito (mídia, objeção, faixa etária, quote down, turnos)
- Rastreabilidade (`eventos` com step/status)
- PII mascarada em log (guardrails)
- Isolamento de dados — [`docs/isolamento-dados.md`](./docs/isolamento-dados.md)

## Estrutura

```
desafio-Khal/
  docker-compose.yml       # solução completa (tudo integrado)
  docker-compose.cpu.yml   # ASR sem GPU
  docker-compose.demo.yml  # sem LLM real
  env.example
  app/                     # agente
  services/                # svc-* + media-asr/ocr
  domains/seguro_auto/     # porteiro do body /quote
```

Desfechos: `apresentar_cotacao` · `reverter_objecao` · `pedir_dado` · `recusar` · `escalar_humano`.  
Detalhes: [`STATE.md`](./STATE.md).
