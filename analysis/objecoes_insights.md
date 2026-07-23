# Padrões de objeção → outcome (análise do dataset)

Conversas analisadas: **2500** · grafo: 5 nós, 6 arestas → `objecao_outcome.graphml`

Objeção detectada por heurística no texto do lead. Ordenado por taxa de ganho.

| objeção | conversas | % ganho | ganho | perdido |
|---|---|---|---|---|
| preco | 628 | **0.0%** | 0 | 263 |
| concorrente | 483 | **0.0%** | 0 | 369 |
| cobertura | 226 | **0.0%** | 0 | 100 |

## Descoberta central
- **Objeção de preço/concorrente/cobertura → ~0% de ganho.** Dos ganhos, apenas
  0 tinham objeção detectada. Ganhos vêm de conversas de qualificação
  limpa; objeção forte = sinal de perda/negociação arrastada.
- ⚠️ **Ressalva (anti-Goodhart)**: dataset é SINTÉTICO (`generate_dataset.py`). O padrão
  pode ser artefato da geração procedural — num cenário real, revalidar antes de decidir.

## Como isso ancora o agente
- **Design**: não há no histórico tática que CONVERTE objeção de preço → o agente não
  deve prometer o que o dado não sustenta.
- **HITL (critério ancorado em dado)**: objeção de preço/concorrente detectada = candidata
  a **escalar cedo** pro humano — conversão histórica ~0, sem tática vencedora aprendível.
- **Few-shot dirigido**: recuperar do RAG conversas de **ganho** (qualificação limpa) como
  molde do caminho feliz; usar o grafo p/ marcar objeção → rota de escalada, não de few-shot.
