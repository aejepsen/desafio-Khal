# Log de execução REAL — /chat contra quote-service no ar

## `execucao_real_01` → **apresentar_cotacao** · persona: meia_30_50

| # | passo | status | detalhe |
|---|---|---|---|
| 0 | ingest | ok | n_mensagens=3 |
| 1 | guardrails | ok | texto_mascarado=Oi, tenho 35 anos quero seguro pro Corolla 2020 meu CPF [CPF], cep [CEP] |
| 2 | qualifica | ok | slots={'idade': 35, 'veiculo_ano': 2020, 'cep': '01310-100'} |
| 3 | porteiro | ok |  |
| 4 | decide | apresentar_cotacao | escalate=False, premio_mensal=137.88 |

**Cotação retornada:** plano=Essencial · prêmio mensal=R$ 137.88 · franquia=4500 · moeda=BRL

> Retry+circuit absorvem os 20% de falha do quote-service; PII mascarada no log.