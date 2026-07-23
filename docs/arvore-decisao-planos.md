# Árvore de decisão — regras de `planos.json`

Fonte canônica: `quote-service/data/plans.json` (mesma lógica de `quote_logic.cotar`).

**Visualização no browser:** abra [`arvore-decisao-planos.html`](./arvore-decisao-planos.html).

**Archify do fluxo POST /quote:** [`fluxo-quote.sequence.html`](./fluxo-quote.sequence.html) (fonte: [`fluxo-quote.sequence.json`](./fluxo-quote.sequence.json)).

Fluxo: validar plano → faixa etária → idade do veículo → região CEP → prêmio → carência (roubo/furto) → pro-rata.

```mermaid
flowchart TD
  Start([POST /quote<br/>plano_id, idade, veiculo_ano, cep?, data_inicio?]) --> P{plano_id existe<br/>em planos?}

  P -->|não| R1[RECUSAR<br/>Plano inexistente]
  P -->|essencial<br/>base 119.90 / franquia 4500| A
  P -->|completo<br/>base 209.90 / franquia 3000| A
  P -->|premium<br/>base 339.90 / franquia 1500| A

  A{idade} -->|menor que 18<br/>ou sem faixa| R2[RECUSAR<br/>Idade fora das faixas]
  A -->|18–24| M1[m_idade = 1.60]
  A -->|25–29| M2[m_idade = 1.25]
  A -->|30–59| M3[m_idade = 1.00]
  A -->|60–75| M4[m_idade = 1.40]
  A -->|≥ 76| R3[RECUSAR<br/>acima do limite 75 anos]

  M1 --> V
  M2 --> V
  M3 --> V
  M4 --> V

  V{anos = hoje.year − veiculo_ano<br/>> 20?}
  V -->|sim| R4[RECUSAR<br/>veículo > 20 anos]
  V -->|não · 0–5| V1[m_veic = 1.00]
  V -->|não · 6–10| V2[m_veic = 1.15]
  V -->|não · 11–20| V3[m_veic = 1.45]

  V1 --> C
  V2 --> C
  V3 --> C

  C{cep informado e<br/>prefixo 2 dígitos ∈<br/>07, 08, 21, 26, 59?}
  C -->|sim| CR[m_regiao = 1.30]
  C -->|não / sem CEP| CN[m_regiao = 1.00]

  CR --> Calc
  CN --> Calc

  Calc[premio_mensal =<br/>base_mensal × m_idade × m_veic × m_regiao] --> Car

  Car{cobertura inclui<br/>roubo ou furto?<br/>carência 30 dias}
  Car -->|sim| CarYes[aplicar carência 30 dias<br/>a partir de data_inicio]
  Car -->|não| Mid
  CarYes --> Mid

  Mid{data_inicio informada<br/>e dia ≠ 1?}
  Mid -->|sim| Pro[primeiro_pagamento_pro_rata<br/>dias restantes do mês]
  Mid -->|não| Ok
  Pro --> Ok([200 OK — cotação])

  R1 --> End([422 cotacao_recusada])
  R2 --> End
  R3 --> End
  R4 --> End
```

## Planos (folha de preço)

| id | nome | base_mensal | franquia | coberturas |
|---|---|---:|---:|---|
| essencial | Essencial | 119.90 | 4500 | colisao, roubo, furto |
| completo | Completo | 209.90 | 3000 | + terceiros, vidros |
| premium | Premium | 339.90 | 1500 | + carro_reserva, assistencia_24h |

## Multiplicadores

**Faixa etária:** 18–24 ×1.60 · 25–29 ×1.25 · 30–59 ×1.00 · 60–75 ×1.40 · ≥76 recusa  
**Idade veículo:** 0–5 ×1.00 · 6–10 ×1.15 · 11–20 ×1.45 · **> 20 recusa** (um único critério)  
**CEP alto risco** (prefixos `07/08/21/26/59`): ×1.30 · senão ×1.00  
**Carência:** se cobertura inclui roubo/furto → 30 dias a partir de `data_inicio`; senão, sem essa carência
