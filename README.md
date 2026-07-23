# desafio-Khal

Solução do **Desafio Técnico FDE / AI Engineer (Namastex)** — um agente que atende
um lead de seguro auto de ponta a ponta: **conversa → qualifica → cota → decide**
(resolve ou escala pro humano, com critério explícito).

> 🚧 Em desenvolvimento. Ver [`STATE.md`](./STATE.md) para o estado atual e próximos passos.

## Arquitetura

Diagrama interativo em [`arquitetura.html`](./arquitetura.html). Resumo:

Um **agente orquestrador (svc-orchestrator, LangGraph)** conduz o fluxo e integra
**microsserviços plugáveis reusados** do ecossistema `microservicos-ai-orchestrator`
(contract-first, OpenAPI `/v1/`, `X-Internal-Key`, `/health`, `/metrics`, OTel):

| Serviço | Papel no agente |
|---|---|
| **svc-guardrails** | sanitiza + mascara PII (CPF/placa/CNH) + injection |
| **svc-router** | classifica a etapa/intenção do lead |
| **svc-rag** | recupera conversas similares/ganhas (few-shot dinâmico) |
| **svc-inference** | serving do LLM (provider plugável) |
| **svc-observability** | rastreabilidade: id + status + trilha (OTel) |
| **svc-orchestrator** | o agente (fluxo de cotação) |

Fora do ecossistema: **quote-service** (fornecido pelo desafio) como tool externa;
**dataset** de 2500 conversas alimenta o svc-rag; **humano (HITL)** recebe a escalada.

### Por que reuso e não construção do zero
Os microsserviços **já existem** (código, contratos, testes). Reusar demonstra
**visão de plataforma** (desacoplamento/escala) e **velocidade com qualidade** —
exatamente o que o desafio pede. Fragmentar do zero em 3 dias seria over-engineering;
reusar plataforma pronta é senioridade. Detalhe: **não** copio o monólito
AI-Orchestrator — reuso os `svc-*` já desacoplados dele, por vendoring limpo.

## Princípios de engenharia (o que o desafio avalia)

- **Resiliência ao `/quote` falhar** (20% 500/502/503 + lentidão 8s): erro é
  **observação ao loop**, não exceção — `retry + backoff + timeout + circuit breaker`;
  falha persistente **escala pro humano**, nunca inventa cotação.
- **Critério HITL explícito**: dados insuficientes · mídia sem transcrição ·
  `/quote` falhou N vezes · idade/veículo fora de faixa · objeção complexa.
- **Isolamento de dados** — cada serviço reusado sobe com estado **do zero**; o RAG é
  populado só do dataset do desafio; nada de outros projetos vaza pro repo público.
  Ver [`docs/isolamento-dados.md`](./docs/isolamento-dados.md).
- **Rastreabilidade** — cada mensagem/cotação com `id` e `status` (svc-observability).
- **PII / dados sensíveis** — mascarados em log e store; dataset fora do git.

## Como rodar

```bash
docker compose up            # sobe quote-service + serviços do agente + infra (volumes limpos)
# ... pipeline de ingestão do dataset no svc-rag (a documentar)
```

_(instruções completas conforme a implementação evolui — ver STATE.md)_

## Estrutura

```
desafio-Khal/
  arquitetura.html          # diagrama archify da solução
  STATE.md                  # handoff / estado / decisões
  docs/isolamento-dados.md  # política de reuso limpo
  docker-compose.yml        # orquestração (volumes novos, coleção namastex_conversas)
  services/                 # svc-* vendorizados (limpos) + código novo do agente
```

## Rodar o agente (API)

```bash
pip install -r requirements.txt
docker compose up -d quote-api            # sobe o quote-service (porta 8000)
QUOTE_URL=http://localhost:8000 uvicorn app.main:app --port 8100
```

Endpoints: `GET /health` · `POST /chat`.

```bash
# exemplo (via httpx/python — curl também serve)
POST /chat  {"mensagens": ["tenho 45 anos, Onix 2019, cep 20040-002", "tá caro"], "idade": 45}
# -> {"decisao":{"acao":"reverter_objecao",...}, "persona":"meia_30_50",
#     "eventos":[... {"step":"objecao","detail":{"framework":"feel-felt-found + ancoragem-valor"}}]}
```

Desfechos de `/chat`: `apresentar_cotacao` · `reverter_objecao` (não desiste no 1º não) ·
`pedir_dado` · `recusar` · `escalar_humano`. Cada passo é logado (id/status), PII mascarada.
