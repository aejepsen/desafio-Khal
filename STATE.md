# STATE — desafio-Khal (handoff resumível)

> Log vivo do projeto. Padrão dos STATEs do portfólio (graphrag-onprem-toolkit).
> Serve para retomar em nova sessão / trocar de LLM sem perder contexto.

## Missão
Solução do **Desafio Técnico FDE / AI Engineer (Namastex)**: um agente que atende
um lead de seguro auto de ponta a ponta — **conversa → qualifica → cota → decide**
(resolve ou escala pro humano, com critério explícito). Repo:
`github.com/aejepsen/desafio-Khal` (PRIVADO durante dev; público na entrega).

## O que o desafio avalia (régua)
1. Funciona ponta a ponta (cota certo no caminho feliz).
2. **O que faz quando `/quote` falha** (20% 500/502/503 + lento 8s) — o que mais separa.
3. Critério de passar pro humano EXPLÍCITO e defensável.
4. Rastreabilidade (cada mensagem/cotação com id + status).
5. Cuidado com dados sensíveis (PII no dataset).
6. Qualidade (outro engenheiro entende as decisões).

## Estratégia de arquitetura (decisões)
**D1 — Reuso dos microsserviços prontos, NÃO cópia do AI-Orchestrator.**
Os 7 `svc-*` do `microservicos-ai-orchestrator` já são a versão desacoplada
(contract-first, OpenAPI /v1/, X-Internal-Key, /health, /metrics, OTel). Reuso o
CÓDIGO dos aderentes por VENDORING LIMPO (sem estado). NÃO copio o monólito
AI-Orchestrator. Serviços aderentes: guardrails (PII), rag (conversas), router
(etapa do lead), inference (LLM), observability (trilha), orchestrator (agente).
svc-evals = offline/opcional.

**D2 — Isolamento de dados (ver docs/isolamento-dados.md).**
Cada serviço reusado sobe com ESTADO DO ZERO. svc-rag populado SÓ do
`conversations.parquet` (coleção `namastex_conversas`). Nada de llm-wiki/spec_kb/
outros projetos vaza pro repo público. Razões: relevância, privacidade,
reprodutibilidade, segurança do repo público.

**D3 — Resiliência do /quote no cliente do orchestrator** (não serviço à parte):
retry + backoff + timeout + circuit breaker. 500/502/503 = OBSERVAÇÃO ao loop, não
exceção. Falha persistente → escala humano (nunca inventa cotação).

**D4 — Código NOVO (a "cola" do desafio, ~3 dias):** lógica de cotação de seguro
(campos veículo/idade/CNH), cliente resiliente do /quote, critério HITL explícito,
decisão sobre mídia sem transcrição.

**D5 — LLM plugável (troca por fim de créditos):** abstrair o provider (svc-inference
ou client) atrás de interface. Ordem de fallback: Claude API → Qwen local (Ollama)
→ outro. Trocar sem tocar na lógica do agente.

## Critério HITL (explícito — a definir/refinar)
Escala pro humano quando: dados insuficientes p/ cotar · mídia sem transcrição
(image/audio/document) · /quote falhou N vezes (circuit aberto) · idade/veículo
fora de faixa cotável · objeção complexa · pedido fora de escopo.

## Estado atual
- Repo criado (privado), branch master. README + arquitetura.html + .gitignore.
- Arquitetura desenhada (archify). Política de isolamento documentada.
- **PRÓXIMO:** (a) vendoring limpo dos svc-* aderentes; (b) docker-compose do desafio
  (volumes novos, coleção namastex_conversas); (c) pipeline de ingestão do dataset
  no svc-rag; (d) lógica de cotação + cliente resiliente do /quote; (e) critério HITL
  em código; (f) log de execução completa (entregável).

## Handoff / troca de LLM
Este STATE + README + docs/isolamento-dados.md + arquitetura.html = fonte de verdade.
Ao trocar de LLM: ler este STATE, seguir do "PRÓXIMO". Provider atrás de interface (D5).

## VENDORING EXECUTADO (2026-07-22) — 6 svc-* limpos
`services/`: svc-guardrails/rag/router/inference/observability/orchestrator (5.3G→2.6M;
sem .venv/dados/segredos). Higiene: 0 .env reais, 0 segredos, 0 dados. Removidos
`svc-orchestrator/evals` (domínio antigo financas). **A ADAPTAR ao domínio cotação:**
prompts/config do svc-orchestrator (era financas/rh/estoque/vendas → agora seguro auto:
qualifica veículo/idade/CNH → cota → decide); golden do svc-router (etapas do lead);
config PII-br do svc-guardrails. **PRÓXIMO:** docker-compose funcional + ingestão do
dataset no svc-rag (coleção namastex_conversas) + lógica de cotação + cliente /quote resiliente.
