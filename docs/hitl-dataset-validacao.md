# HITL / escalar humano — validação com dataset

## Achado no parquet
O dataset **não** tem mensagens explícitas “escalar para humano” / “transferir”.

Padrão mais próximo (538 conversas): após objeção de preço, o vendedor diz
**“Entendo! Consigo rever, posso te ligar?”** — handoff soft para canal humano.
Exemplos: `conv_00003`, `conv_00033`, `conv_00121` (outcome `perdido`).

## Mapeamento → nosso critério HITL

| Caso dataset | Nosso critério | Resultado live |
|--------------|----------------|----------------|
| `conv_00003` preço persistente | após 3 táticas → `escalar_humano` | **PASS** |
| `conv_00033` `[documento]` | mídia sem transcrição → `escalar_humano` | **PASS** |
| `conv_00008` idade 78 | faixa ≥76 → `recusar` | **PASS** |

Script: `scripts/e2e_escalar_humano.py`  
JSON: `docs/e2e-escalar-humano.json`

## Grau A (mensagem ao lead quando `/quote` falha)

- **Audit** guarda motivo técnico (`503`, circuito, retries).
- **Lead** recebe só cópia humana (`orch_svc/hitl_copy.py`): admitir instabilidade,
  conectar atendente, **nunca** inventar prêmio / jargão HTTP.
- `redigir_resposta` em `escalar_humano` usa **template** (não LLM) para garantir grau A.
- Testes: `tests/test_hitl_grau_a.py`.
