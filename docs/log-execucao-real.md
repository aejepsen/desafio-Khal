# Log de execução REAL — ciclo E2E (lead → contratado)

> Gerado por `scripts/e2e_ciclo_ganho.py` contra `/chat` no compose.
> CID: `e2e-ciclo-1784828321` · 2026-07-23

## Fluxo

`qualificar` → `cotado` → `contratado` (`emitir_apolice`)

| # | estágio / ação | lead | agente (resumo) |
|---|---|---|---|
| 1 | qualificando / pedir_dado | Oi, quero cotar seguro do meu carro | pede idade, ano, plano, CEP |
| 2 | qualificando / pedir_dado | Tenho 42 anos | slots: idade=42; pede ano/plano/CEP |
| 3 | qualificando / pedir_dado | É um Corolla 2020 | slots: +veiculo_ano=2020; pede plano/CEP |
| 4 | cotado / apresentar_cotacao | CEP 01310-100, quero o plano completo | Completo **R$ 241.38/mês** · rerank `exemplos_n=3` |
| 5 | contratado / emitir_apolice | fechado! pode emitir | boleto + apólice Completo R$ 241.38 |

## Veredicto

**PASS** — coleta progressiva sem alucinação de slots → cotação → aceite → apólice.

JSON bruto: `docs/e2e-ciclo-ganho.json`

## `execucao_real_01` (histórico — one-shot até cotar)

| # | passo | status | detalhe |
|---|---|---|---|
| 0 | ingest | ok | n_mensagens=3 |
| 1 | guardrails | ok | PII mascarada |
| 2 | qualifica | ok | idade/ano/cep |
| 3 | porteiro | ok |  |
| 4 | decide | apresentar_cotacao | premio_mensal=137.88 |
