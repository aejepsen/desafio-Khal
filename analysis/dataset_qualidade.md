# Auditoria de qualidade — dataset/conversations.parquet

Due diligence sobre a base que alimenta RAG/Neo4j (few-shot do LLM) e que
ancorou decisões de arquitetura (`analysis/build_objecao_graph.py`). Gerado por
`analysis/audit_dataset_qualidade.py` — reproduzível, não é assert automático.

## 1. Integridade estrutural (2500 conversas)

| Problema | Ocorrências |
|---|---|
| timestamps fora de ordem (campo não usado pelo código) | 2495 |

`timestamps fora de ordem`: confirmado via grep que o campo `timestamp` **não é lido em nenhum lugar do código** (RAG/Neo4j/extração usam só `message_index`, que é 100% sequencial e correto) — artefato de geração sem efeito prático.

## 2. Qualidade por outcome (dataset inteiro)

| Outcome | Total | Curtas (<2 msg) | Texto quebrado | Veículo vazio | Idade implausível |
|---|---|---|---|---|---|
| em_negociacao | 757 | 0 | 0 | 0 | 0 |
| ganho | 712 | 0 | 0 | 0 | 0 |
| perdido | 538 | 0 | 0 | 0 | 0 |
| sem_resposta | 493 | 0 | 0 | 0 | 0 |

Duplicatas exatas no dataset inteiro: **0** grupos.

## 3. Subconjunto GANHO (o que RAG/Neo4j realmente injetam no LLM)

- Conversas sem sinal textual real de fechamento (falso-positivo de `has_close`): **0**
- Vendedor menciona R$ fora de qualquer faixa plausível dos planos reais (`plans.json`, 0.5x–3x do valor base): **0**

## 4. Re-validação do achado central ('objeção → ~0% ganho')

A heurística que gerou esse achado (`analysis/build_objecao_graph.py`) tinha os mesmos falsos-positivos que foram corrigidos em `orch_svc/objecoes.py` nesta sessão (`azul`/`porto` sem contexto, `preço` solto, `outra` genérico). Comparação:

| Heurística | preço | concorrente | cobertura | ganhos com objeção |
|---|---|---|---|---|
| Original (pré-fix) | 628 | 483 | 226 | **0 / 712 (0.0%)** |
| Corrigida (pós-fix) | 431 | 391 | 226 | **0 / 712 (0.0%)** |

**Conclusão:** a correção da regex reduziu o volume bruto de detecção (menos falso-positivo), mas o número central do insight — zero conversas `ganho` com qualquer objeção detectada — se manteve em 0% nas duas versões. A decisão de arquitetura (reverter objeção com tática antes de escalar) **não está apoiada num artefato da regex antiga** — é um padrão real e robusto no dataset.

## Conclusão geral

Nenhum problema de qualidade encontrado que colocasse em risco o comportamento do agente — nem no subconjunto `ganho` (RAG/Neo4j few-shot) nem no dataset inteiro (que alimenta a análise de objeções). O único achado real (timestamp fora de ordem) não é consumido por nenhum código do sistema.
