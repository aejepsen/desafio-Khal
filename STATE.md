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

## Estado atual (2026-07-22 noite)
- Vendoring dos 6 `svc-*` + `quote-service` + compose esqueleto: feitos.
- **Domínio determinístico** `domains/seguro_auto/`: feito (monta body `/quote`, não calcula prêmio).
- **quote-api** testado local (`docker compose up --build quote-api`, porta **8000:8000**).
- Docs de regras + Archify do fluxo `/quote`: feitos.
- **RAG:** qdrant + svc-rag no ar; coleção `namastex_conversas` populada (712 conversas `ganho`,
  771 chunks). Script `scripts/ingest_namastex_conversas.py`.
- **PRÓXIMO:** (a) cliente HTTP resiliente do `/quote` no orchestrator;
  (b) wire domínio → agente; (c) wire orchestrator → `POST /v1/search`;
  (d) HITL em código; (e) adaptar prompts; (f) log de execução completa.

## Handoff / troca de LLM
Este STATE + README + docs/isolamento-dados.md + arquitetura.html
+ docs/fluxo-quote.sequence.html + docs/arvore-decisao-planos.html = fonte de verdade.
Ao trocar de LLM: ler este STATE, seguir do "PRÓXIMO". Provider atrás de interface (D5).

## VENDORING EXECUTADO (2026-07-22) — 6 svc-* limpos
`services/`: svc-guardrails/rag/router/inference/observability/orchestrator (5.3G→2.6M;
sem .venv/dados/segredos). Higiene: 0 .env reais, 0 segredos, 0 dados. Removidos
`svc-orchestrator/evals` (domínio antigo financas). **A ADAPTAR ao domínio cotação:**
prompts/config do svc-orchestrator (era financas/rh/estoque/vendas → agora seguro auto:
qualifica veículo/idade/CNH → cota → decide); golden do svc-router (etapas do lead);
config PII-br do svc-guardrails. **PRÓXIMO:** docker-compose funcional + ingestão do
dataset no svc-rag (coleção namastex_conversas) + lógica de cotação + cliente /quote resiliente.

## CONTRATO /quote + REAVALIAÇÃO de serviços (2026-07-22)
**quote-service copiado** (`./quote-service`, fornecido). Contrato:
- `POST /quote` QuoteRequest{plano_id(essencial|completo|premium), idade, veiculo_ano, cep?, data_inicio?}
  → 200 cotação · **422 cotacao_recusada** (regra: idade/veículo fora de faixa) ·
  400 payload_invalido · **500/502/503** instabilidade 20% (+ lento 8s).
- `GET /planos` tabela de regras · `GET /health`.
- Regras (quote_logic): faixa_etaria, idade_veiculo, regiao(cep alto risco), pro_rata 1º mês.
**Domínio determinístico (2026-07-22):** `domains/seguro_auto/` — após o agente marcar
dados como verificados, `build_quote_request(...)` normaliza/valida slots contra
`quote-service/data/plans.json` e devolve o JSON de `/quote` (ou missing/errors/refusals).
LLM não calcula nem monta o body. Prêmio só no quote-service.
**Extração do lead:** idade · veiculo_ano (ou de veiculo_texto) · cep · plano · data_inicio.
422/400 = observação ao loop; 500/502/503 = retry+circuit → escala humano.
**REAVALIAÇÃO (reuso judicioso, D1):** svc-router tem 9 refs do domínio antigo
(multi-domínio financas/rh/estoque/vendas). O fluxo do desafio é LINEAR (qualifica→cota→
decide), não multi-domínio → **svc-router provavelmente DISPENSÁVEL** ou re-proposto p/
classificar INTENÇÃO (qualificar/objeção/pedir-humano). Decisão: avaliar na implementação.
Núcleo confirmado: orchestrator + guardrails + rag + inference + observability.

## SESSÃO 2026-07-22 (noite) — o que foi feito

### quote-api / compose
- Corrigido mapeamento de porta no `docker-compose.yml`: container escuta **8000**
  (`Dockerfile`/`uvicorn --port 8000`); era `8080:8080` (quebrado) → agora `8000:8000`.
- Subido `quote-api` com `docker compose up --build -d quote-api`.
- Testados endpoints: `GET /health`, `GET /planos`, `POST /quote`.
- Snapshots salvos em `data/quote-api-snapshots/`
  (`health.json`, `planos.json`, `openapi.json`, `quote_example_200.json`).
  Nota: pasta `data/` está no `.gitignore` (PII/dataset) — snapshots locais.

### Contrato POST /quote (confirmado no código + OpenAPI)
**Request body** (domínio monta isto):
`{plano_id?, idade, veiculo_ano, cep?, data_inicio?}` —
obrigatórios: `idade`, `veiculo_ano`; default `plano_id=essencial`.
**Response 200:** `plano_id`, `plano_nome`, `premio_mensal`, `franquia`, `coberturas`,
`multiplicadores`, `carencia`, `moeda`, opcional `primeiro_pagamento_pro_rata`.
**422** `cotacao_recusada` · **400** `payload_invalido` · **5xx** instabilidade.
Campo correto: `veiculo_ano` (não `ano_veiculo`).
`plano_id = (payload.get("plano_id") or "essencial").lower()` no `quote_logic` é
**default**, não hardcode — `completo`/`premium` seguem dinâmicos via `plans.json`.

### Domínio determinístico `domains/seguro_auto/`
- Papel: **porteiro** — após `verified=True`, normaliza/valida slots contra
  `quote-service/data/plans.json` e devolve body do POST (ou missing/errors/refusals).
- **Não** chama `quote_logic.py`; **não** calcula prêmio/carência/pro-rata.
- Cálculo fica no servidor: `main.py` → `cotar(req.model_dump())` → `quote_logic`.
- Testes: `domains/seguro_auto/tests/` (30 passed).
- Matriz mock + XML: `domains/seguro_auto/evals/results/domain_quote_cases.xml`
  (colunas input de planos/slots + output do JSON `/quote`).
- Cruzamento domain ↔ quote_logic (recusa/aceitação) alinhado nos casos mockados.

### Documentação visual
- `docs/arvore-decisao-planos.md` + `.html` — árvore de regras de `plans.json`
  (1 box recusa veículo >20; carência 30d roubo/furto como condição sim/não).
- Archify sequence do fluxo: `docs/fluxo-quote.sequence.json` →
  `docs/fluxo-quote.sequence.html` (Archify 2.12) —
  agente → domínio → POST `/quote` → main → cotar → plans.json → resposta.

## SESSÃO 2026-07-22 (noite+) — ingestão svc-rag

### Chaves (portfolio `microservicos-ai-orchestrator`)
- svc-rag usa **`INTERNAL_KEY`** (header `X-Internal-Key`) — fail-closed.
  `.env.example` do portfolio: placeholder `troque-me`. No desafio: `dev-namastex-key`
  (`.env.example` local; `.env` gitignored).
- **`QDRANT_API_KEY`**: opcional; Qdrant local (imagem docker) **sem key**.
  Portfolio tem a variável no `.env` raiz — não necessária aqui.
- **`VOYAGE_API_KEY`**: existe no portfolio; **não** usada pelo svc-rag (SBERT local).
- Compose corrigido: `INTERNAL_KEY` (antes `X_INTERNAL_KEY` errado),
  `ALLOW_LOCAL_STORE=1` (Qdrant em rede docker = IP privado; anti-SSRF),
  porta `8204:8204`, `VECTOR_STORE=qdrant`.

### Ingestão executada
```bash
docker compose up --build -d qdrant svc-rag
INTERNAL_KEY=dev-namastex-key python3 scripts/ingest_namastex_conversas.py --outcome ganho
```
- Health: embedder ok, vector_store ok, graphrag absent.
- Resultado: **712 docs / 771 chunks** na coleção `namastex_conversas`.
- Smoke search OK (`seguro auto corolla idade`, etc.).
- Plano: `docs/plano-ingestao-rag.md`.

## SESSÃO 2026-07-22 (noite++) — cliente resiliente /quote (item PRÓXIMO-a FEITO)
`services/svc-orchestrator/src/orch_svc/quote_client.py`: `ResilientQuoteClient`
(reusa `circuit.py`). 4 desfechos + escalonamento:
- 200 → QUOTED · 422 → REFUSED (observação, NÃO reintenta) · 400 → INVALID (falta dado)
- 5xx/timeout → retry + backoff (2^n) + circuit (3 falhas → OPEN) · esgota/OPEN → UNAVAILABLE + escalate=True (nunca inventa cotação).
- 4xx não conta no breaker (semântica do circuit.py). Sleep injetável p/ teste.
`tests/test_quote_client.py`: **7 passed** (quoted/refused-sem-retry/invalid/retry-sucesso/
timeout/esgota-escala/circuito-aberto-escala).
**PRÓXIMO:** (b) wire domínio seguro_auto → agente (body → quote_client); (c) wire
orchestrator → svc-rag POST /v1/search; (d) critério HITL completo em código
(escalate já cobre /quote; falta: dados insuficientes, mídia sem transcrição, idade/veículo
fora de faixa via REFUSED); (e) adaptar prompts + DISPENSAR svc-router (fluxo linear);
(f) log de execução completa (entregável).

## SESSÃO 2026-07-22 (noite+++) — decisão de cotação: (b)+(c)+(d) integrados
`orch_svc/cotacao_flow.py`: `decidir_cotacao(build_result, quote_client, query, rag)`.
- (b) porteiro seguro_auto (BuildResult) → missing=pedir_dado · refusals=recusar · errors=pedir_correcao.
- (c) RAG few-shot (coleção namastex_conversas) — enriquecimento; falha NÃO bloqueia (degrada gracioso).
- (d) HITL: /quote QUOTED→apresentar · REFUSED→recusar · INVALID→pedir_correcao · UNAVAILABLE→escalar_humano(escalate).
Injeção de dependência (testável sem cross-import). `tests/test_cotacao_flow.py`: 6 passed
(+ 7 do quote_client = 13). **PRÓXIMO:** (e) wire no grafo orchestrator.py (nó de cotação
real chamando cotacao_flow) + adaptar prompts + DISPENSAR svc-router (fluxo linear, remove ~40 refs);
(f) log de execução completa (entregável); ligar rag/quote clients reais no app.

## SESSÃO 2026-07-22 (noite++++) — (e) svc-router dispensado + (f) log de execução
- **(e)** `svc-router` REMOVIDO (multi-domínio, fluxo é linear) — ~40 refs financas foram;
  restam 9 arquivos menores (svc-orchestrator README/tests, svc-guardrails SPEC/test) a adaptar.
  compose limpo (sem svc-router/ROUTER_URL).
- **(f)** `orch_svc/agente_cotacao.py`: runner linear com LOG rastreável (Evento id+status/passo),
  mascara PII, extração heurística de slots (idade/veiculo_ano/cep). `scripts/demo_execucao.py`
  roda 3 cenários → **`docs/log-execucao.md`** (entregável): caminho_feliz (QUOTED) ·
  quote_instavel (UNAVAILABLE→escala humano) · falta_dado (porteiro missing→pedir_dado).
- Testes: 13 passed (quote_client 7 + cotacao_flow 6). cotacao_flow._extrair_body tolera
  BuildResult.payload (o body real vem do porteiro).
**PRÓXIMO:** adaptar 9 refs restantes (financas→seguro); wire clients REAIS no app.py
(guardrails/rag/inference/quote via env URLs); extração de slots via LLM (svc-inference)
substituindo heurística; rodar demo contra quote-api real (docker) p/ log com retry verdadeiro;
adaptar prompts; README final com decisões (entregável #3).

## LIMPEZA DOMÍNIO ANTIGO (2026-07-22) — 0 refs financas
Adaptadas refs (financas→seguro_auto/cotacao) em clients.py/docs; REMOVIDOS os tests do
grafo multi-agente antigo (test_orchestrator/security/app/write_intent/conftest — testavam
o Orchestrator multi-domínio, NÃO a solução de cotação). Tests da solução mantidos:
test_quote_client (7) + test_cotacao_flow (6). **0 refs** de domínio antigo no repo.
Nota: grafo antigo (orchestrator.py/app.py) ainda no código; será substituído no wire do
app.py pelo fluxo de cotação (próximo). Núcleo da solução = quote_client + cotacao_flow + agente_cotacao.

## SESSÃO 2026-07-22 — GRAFO de objeções (decisão: grafo p/ ANÁLISE, não transacional)
Reavaliação: a frase do desafio ("usar dataset p/ entender padrões de objeção") legitima
grafo na CAMADA DE ANÁLISE (não banco transacional — relacional serve pro store).
`analysis/build_objecao_graph.py`: heurística de objeções (sem LLM) → grafo objeção→outcome
(networkx graphml) + `analysis/objecoes_insights.md`.
**DESCOBERTA:** objeção de preço(628)/concorrente(483)/cobertura(226) = **~0% ganho**;
os 712 ganhos vêm de qualificação limpa (0 ganhos com objeção detectada).
**Ressalva (anti-Goodhart):** dataset SINTÉTICO → padrão pode ser artefato de geração.
**Implicação no agente:** objeção de preço/concorrente = critério HITL ancorado em dado
(escalar cedo, sem tática vencedora histórica); few-shot dirigido = conversas de GANHO como
molde do caminho feliz; grafo marca objeção→rota de escalada. svc-rag graphrag segue OFF
(few-shot vetorial + grafo como sinal de escalada, não retrieval).

## SESSÃO 2026-07-22 — tratamento de objeção: NÃO desistir no primeiro "não"
Correção de viés (usuário): objeção não é fim — o dado (0% ganho) mostra que os
VENDEDORES não trataram, não que é irrecuperável = oportunidade do agente.
`orch_svc/objecoes.py`: detectar_objecao + proxima_acao(objecao, tentativas, max=3) →
REVERTER (tática escalonada por tentativa) ou ESCALAR (só após esgotar). TATICAS por
tipo (preco/concorrente/cobertura/indeciso). Simetria com /quote: retry antes de desistir.
Integrado em `agente_cotacao.run_conversa` (intercepta antes de cotar). Demo tem cenário
`objecao_preco_reverte` → reverter_objecao (tática: reancorar em valor). Tests: **25 passed**
(+test_objecoes 6). Critério HITL revisado: escalar = objeção PERSISTENTE (não a 1ª).
**PRÓXIMO:** wire app.py (endpoint→run_conversa); extração via LLM; few-shot de GANHO
(qualificação limpa) do svc-rag; agente aprende com próprias reversões; README final.

## BACKLOG AMANHÃ (2026-07-23) — táticas de objeção + estilo por idade
**1. Táticas de objeção de conteúdo de treinamento de vendas de seguro (fonte externa).**
- Buscar/indexar metodologias reais (SPIN, LAER=Listen-Acknowledge-Explore-Respond,
  feel-felt-found, ancoragem de valor) → EXPANDIR `TATICAS` em `objecoes.py`.
- Opção arquitetural: 2ª fonte de conhecimento (além do dataset de conversas) — indexar
  o conteúdo de vendas num RAG/coleção própria (`namastex_vendas_kb`) para o agente
  RECUPERAR táticas dinamicamente (svc-rag), não só as hardcoded. Grafo opcional:
  objeção→tática→princípio (do material de treinamento).
- Fonte via ctx_fetch_and_index / material que o usuário trouxer. Isolamento: coleção própria.

**2. Estilo de abordagem conforme IDADE (lead_idade_informada).**
- Faixas → modulador de TOM/canal/foco (não muda a lógica, muda a comunicação):
  jovem (18-30): informal, ágil, praticidade/preço · meia-idade (30-50): equilíbrio,
  cobertura/família/proteção · sênior (50+): formal, confiança, clareza, atendimento humano.
- Implementar como `persona.py` (dado idade → estilo) que modula o prompt de resposta;
  combinar com a tática de objeção (ex: sênior + objeção preço = tom formal + reancorar em segurança).
- Validar faixas contra o dataset (idade × outcome) antes de fixar — anti-Goodhart.

## SESSÃO 2026-07-23 — persona por idade (item 2 do backlog)
Validação anti-Goodhart ANTES de fixar: idade × outcome no dataset é PLANO
(jovem/meia/sênior ganho ~28-30%, perdido ~21-22%) → **idade NÃO prediz conversão**.
Decisão honesta: persona = RAPPORT/UX (falar a língua do público), NÃO alavanca de
conversão. `orch_svc/persona.py`: persona_por_idade(idade)→Persona(tom/foco/diretrizes);
diretriz_de_estilo() injeta no PROMPT de redação, não na DECISÃO (cotar/reverter/escalar
inalterados). Faixas: <31 jovem · 31-50 meia · 51+ sênior · None desconhecida (dataset:
idade 18-82, mediana 51). Tests: test_persona 3 + test_objecoes 6. Combina com objecoes
(tom modula como a tática é apresentada). **PRÓXIMO:** item 1 (táticas de treinamento de
vendas → coleção namastex_vendas_kb no svc-rag); wire persona+objeção no prompt de resposta;
wire app.py; README final.

## SESSÃO 2026-07-23 — táticas ancoradas em metodologia (item 1, opção 1)
`objecoes.py` expandido: táticas por objeção agora estruturadas em frameworks REAIS de
vendas — LAER (Listen-Acknowledge-Explore-Respond), feel-felt-found, ancoragem-valor,
isolamento. `Tatica{texto, framework}`; RespostaObjecao carrega `framework` (rastreável/
explicável no log). preço 3 táticas (feel-felt-found→isolamento→risco), concorrente/
cobertura 2, indeciso 1. Escalonamento por tentativa mantido (não desiste no 1º não).
Agente loga o framework usado. **GANCHO item 3 (pendente):** coleção `namastex_vendas_kb`
no svc-rag p/ recuperar táticas de material específico (quando o usuário trouxer).
**PRÓXIMO:** wire persona+objeção no prompt de resposta (svc-inference); wire app.py
(endpoint→run_conversa); README final (entregável #3).

## SESSÃO 2026-07-23 — SERVIÇO NO AR (wire app.py)
`app/main.py` (raiz): FastAPI amarra domains/seguro_auto + orch_svc. POST /chat
{mensagens, idade?, tentativas_objecao?} → run_conversa → {decisao, persona, eventos(log)}.
GET /health. Wire: ResilientQuoteClient(QUOTE_URL) + persona_por_idade + objeção + RAG
opcional (RAG_URL). `requirements.txt`. **TESTADO NO AR**: uvicorn :8100, httpx — health ok;
/chat objeção→reverter_objecao (persona+framework); falta_dado→pedir_dado. README com execução.
**PRÓXIMO:** subir quote-api + /chat caminho feliz real (cotação saindo, log com retry);
wire persona+tática no prompt via svc-inference (redigir a resposta); README final (decisões).

## SESSÃO 2026-07-23 — CAMINHO FELIZ REAL (quote-api no ar)
quote-api subido (docker, :8000). /chat com dados completos → 8/8 apresentar_cotacao;
cotação real saindo (Essencial R$137.88, franquia 4500). Retry absorve os 20% de falha
(transparente; escala só com 3 seguidas ~0.8%). `docs/log-execucao-real.md` gerado
(entregável #4 com dados reais + PII mascarada).
**MELHORIA NOTADA:** extração heurística NÃO capta plano_id (default essencial) nem tudo
de veiculo_texto livre → **extração via LLM (svc-inference)** é o próximo salto de qualidade.
**PRÓXIMO:** extração LLM; wire persona+tática no prompt (redigir resposta); README final (decisões).

## SESSÃO 2026-07-23 — CONVERSA MULTI-TURNO com estado (thread)
`orch_svc/thread.py`: ThreadState (slots acumulados · tentativas_objecao por tipo ·
turnos · estagio · encerrado) + ThreadStore (in-memory; Redis/DB em prod) + run_turno.
Agente CONDUZ: acumula slots entre turnos, pede só o que falta (pedir_faltantes amigável),
objeção persiste tentativas entre turnos, limite MAX_TURNOS=8 = HITL temporal.
`/chat` agora multi-turno: {conversation_id, mensagem, idade?} → estado por conversa.
Demonstrado: T1 só idade→pede veículo; T2 completa→cota R$137.88 (lembrou da idade).
Tests: test_thread 5 (32 total). **PRÓXIMO:** extração LLM (capta plano/veículo livre);
wire resposta redigida (svc-inference com persona+tática); README final (decisões).

## SESSÃO 2026-07-23 — COLETA ATIVA (completude da cotação)
Gap fechado: agente agora capta plano_id do texto (_PLANO: premium/completo/essencial por
keyword, ordem específica) e COLETA ATIVAMENTE os campos que mudam o preço, não usa default
silencioso. thread: OBRIGATORIOS=[idade,veiculo_ano,plano_id] (sempre pergunta) ·
OPCIONAIS_ATIVOS=[cep] (pede 1x, cota sem se lead não der) · data_inicio=hoje (default explícito).
ThreadState.pedidos evita re-perguntar. Demonstrado: lead completo mas sem plano → pergunta o
plano → "premium" → cota Premium R$390.88 (antes cotava Essencial R$137.88 silencioso). 33 testes.
**PRÓXIMO:** extração LLM (plano/veículo de texto livre mais rico); resposta redigida
(svc-inference persona+tática); README final (decisões).
