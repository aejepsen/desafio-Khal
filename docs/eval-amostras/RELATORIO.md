# Eval amostras × régua Namastex (realtime)

Fonte: `dataset/conversations.parquet` + 1 caso sintético (`R2`, falha `/quote`).
Catálogo mascarado: `catalogo.json` · resultados: `resultados-realtime.json`.

| ID | Régua | Origem | Expectativa | Resultado |
|----|-------|--------|-------------|-----------|
| R1_happy_path | 1 e2e | conv ganho | `apresentar_cotacao` + quote | **PASS** |
| R2_quote_falha | 2 resiliência | sintético (`QUOTE_FAILURE_RATE=1`) | `escalar_humano`, sem inventar prêmio | **PASS** |
| R3_objecao_hitl | 3 HITL | conv perdido/preço | esgota táticas → escala | **PASS** |
| R3_media_sem_transcricao | 3 HITL | mídia no dataset | `escalar_humano` + motivo *mídia sem transcrição* | **PASS** (após fix) |
| R3_idade_fora_faixa | 3 HITL | idade ≥76 | `recusar` | **PASS** |
| R4_rastreabilidade | 4 trace | mesmo happy | eventos com `step`+`status` | **PASS** (4 eventos) |
| R5_pii | 5 PII | conv com PII | mask no log (`[CPF]`/`cep`) | **PASS** |

**Item 6 (qualidade/decisões):** não é amostra de dataset — coberto por README/STATE/código.

### Mídia (HITL dedicado + plug ASR/OCR)
- Default: placeholder `[documento]|[áudio]|…` / `message_type` → `escalar_humano`
  motivo **mídia sem transcrição**.
- Opt-in tear-free: `MEDIA_ASR_URL` / `MEDIA_OCR_URL` + `media_url` no `/chat`.
  Sucesso → segue cotação; falha → mesmo HITL.
- Hardware: ver README (Whisper large ≈ ≥10 GB VRAM; stack padrão **sem GPU**).
