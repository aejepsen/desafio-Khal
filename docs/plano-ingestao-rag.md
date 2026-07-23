# Plano — ingestão do dataset no svc-rag

> Coleção: `namastex_conversas` · Fonte: `dataset/conversations.parquet`  
> Princípio: isolamento (`docs/isolamento-dados.md`) — estado do zero, só dataset do desafio.

## O que entendi (objetivo)

Usar **`services/svc-rag`** para indexar as conversas do desafio e o agente recuperar
**few-shot / conversas similares** (ex.: ganhas) na qualificação/cotação — **sem**
contaminar com corpora de outros projetos.

O `svc-rag` **não** gera resposta LLM: só `POST /v1/ingest` + `POST /v1/search`.
A síntese fica no orchestrator.

## Análise dos dados (`dataset/`)

| Artefato | Papel |
|---|---|
| `conversations.parquet` | Fonte canônica (~447 KB) |
| `sample.jsonl` | Amostra legível (mesmo schema) |
| `DICIONARIO.md` | Schema + aviso: dados **sintéticos** com PII plausível |

**Escala:** 2 500 conversas · 26 470 mensagens (1 linha = 1 mensagem).

**Colunas:** `conversation_id`, `message_index`, `timestamp`, `sender_role`
(`lead`/`vendedor`), `sender_name`, `message_type` (`text`/`image`/`audio`/`document`),
`message_body`, `channel` (whatsapp), `conversation_outcome`
(`ganho` / `perdido` / `em_negociacao` / `sem_resposta`), `lead_idade_informada`,
`veiculo_texto`.

**Implicações para RAG**
- Documento útil = **conversa reconstruída** (agrupar por `conversation_id`, ordenar
  `message_index`) — não ingerir mensagem a mensagem como doc isolado (context curto demais).
- Mídia (~7%): só marcadores (`[documento] …`) — sem transcrição → útil como sinal HITL,
  pouco valor semântico; pode filtrar ou manter com metadata `has_media=true`.
- PII sintética no texto → preferir passar por **svc-guardrails** (máscara) **antes**
  de persistir no Qdrant, ou metadata sem nomes/CPF no payload quando possível.
- `veiculo_texto` / idade / outcome são ótimos em **metadata** para filtro futuro e debug.
- Prioridade de qualidade: conversas **`ganho`** (e talvez `em_negociacao`) como few-shot;
  `perdido`/`sem_resposta` opcional (objeções / abandono).

## Contrato svc-rag (o que vamos usar)

```
POST /v1/ingest  { collection, documents: [{ id, text, metadata }] }
POST /v1/search  { query, collection, top_k }
GET  /v1/collections
```

Compose do desafio já prevê: `RAG_COLLECTION=namastex_conversas`, Qdrant volume limpo
`namastex_qdrant`, auth `X-Internal-Key`.

## Plano de implementação (fases)

### Fase 0 — Infra mínima
1. Subir `qdrant` + `svc-rag` no `docker-compose` (volumes novos).
2. Confirmar `GET /health` e coleção ausente / vazia.
3. Script só lê `dataset/` local (não commitado — já no `.gitignore`).

### Fase 1 — Transformação parquet → Document[]
Script dedicado (ex.: `scripts/ingest_namastex_conversas.py`):

1. Ler `conversations.parquet` (pandas/pyarrow).
2. Agrupar por `conversation_id`; ordenar por `message_index`.
3. Montar `text` Markdown legível, ex.:

```text
# Conversa conv_00042 · outcome=ganho
- lead (35) · veiculo: Toyota Corolla 2008

[lead] Oi, queria fazer um seguro...
[vendedor] Qual o modelo e ano...
...
```

4. `id` = `conversation_id` (idempotência do svc-rag por id+hash).
5. `metadata` sugerido:
   - `outcome`, `lead_idade_informada`, `veiculo_texto`
   - `n_messages`, `has_media`, `channel`
6. **Filtro v1 (recomendado):** só `outcome == ganho` (melhor few-shot); flag `--all`
   para corpus completo depois.
7. Batch de ingest (ex. 50–100 docs/request) → `POST /v1/ingest` com
   `collection=namastex_conversas`.
8. Opcional: sanitizar `text` via guardrails antes do ingest (PII).

### Fase 2 — Validação da ingestão
1. `GET /v1/collections` → chunks > 0 em `namastex_conversas`.
2. Smoke searches:
   - “seguro corolla idade 35”
   - “cliente enviou CNH documento”
   - “recusou por preço” (se incluir perdidos)
3. Conferir que hits trazem `metadata.outcome` coerente.
4. Re-rodar script → `n_skipped_idempotent` sobe (sem duplicar).

### Fase 3 — Uso no agente (svc-orchestrator)
1. Antes/durante qualificação: `POST /v1/search` com trecho da conversa atual
   (`collection=namastex_conversas`, `top_k=3`).
2. Injetar hits como few-shot no prompt (não como “fonte de prêmio”).
3. Cotação continua: domínio determinístico → `POST /quote` (RAG **não** calcula prêmio).

### Fase 4 — Hardening (depois do E2E mínimo)
- Eval Recall simples (queries douradas do domínio seguro).
- Decidir se indexa `perdido` para objeções.
- Política PII: máscara obrigatória pré-ingest vs. só em logs.
- GraphRAG: **fora** do caminho crítico do desafio (opt-in; não bloquear entrega).

## Fora de escopo deste plano
- Treinar/fine-tune embedder.
- Ingerir `plans.json` no RAG (regras já estão no domínio + quote-service).
- Subir dataset no git.

## Critério de pronto
- [x] Qdrant + svc-rag no ar com volume limpo
- [x] Script `scripts/ingest_namastex_conversas.py`
- [x] Coleção `namastex_conversas` populada (712 `ganho` / 771 chunks — 2026-07-22)
- [x] Smoke searches OK
- [ ] Orchestrator consegue chamar `/v1/search` (mesmo que prompt ainda provisório)

## Ordem sugerida de execução
**Fase 0 → 1 → 2** agora; **Fase 3** junto do wire do agente; **Fase 4** se sobrar tempo.
