# desafio-Khal

Solução do **Desafio Técnico FDE / AI Engineer (Namastex)** — um agente que atende
um lead de seguro auto de ponta a ponta: **conversa → qualifica → cota → decide**
(resolve ou escala pro humano, com critério explícito).

> 🚧 Em desenvolvimento.

## Arquitetura

O desenho da solução está em [`arquitetura.html`](./arquitetura.html) — diagrama
interativo (abrir no navegador). Resumo:

Agente **FastAPI + LangGraph** com pipeline de 4 estágios:

1. **Sanitize + Guardrails** — mascara PII (CPF/placa/e-mail), injection.
2. **Qualifica** — extrai e normaliza veículo/idade/CNH; trata mídia sem transcrição.
3. **Cota** — chama `/quote` com **retry + backoff + timeout + circuit breaker**.
4. **Decide** — resolve (apresenta plano) ou escala pro humano.

**Princípios de engenharia (o que o desafio avalia):**

- **Resiliência ao `/quote` falhar** (20% 500/502/503 + lentidão): erro é
  **observação ao loop**, não exceção — falha persistente escala pro humano, nunca
  inventa cotação.
- **Critério HITL explícito**: dados insuficientes, mídia sem transcrição, `/quote`
  falhou N vezes, idade/veículo fora de faixa, objeção complexa.
- **PII / dados sensíveis**: mascarados em log e store.
- **Rastreabilidade**: cada mensagem/cotação com `id` e `status`.

## Como rodar

_(a documentar conforme a implementação evolui)_
