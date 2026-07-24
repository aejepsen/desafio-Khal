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

## Estado atual (2026-07-23)
- Domínio determinístico, quote resiliente, RAG, objeções, persona, thread, `/chat` — feitos.
- PII (mask só em log), CEP obrigatório, HITL explícito (mídia / quote fail / faixa) — feitos.
- Eval amostras 7/7 PASS; smoke feliz Ollama + smoke áudio Whisper GPU — feitos.
- **Compose único = solução completa:** `docker compose up --build` sobe quote + qdrant +
  guardrails + rag + inference + ollama (`qwen2.5:7b` Q4) + asr (Whisper small GPU) +
  ocr (Tesseract) + observability + agente. Sem profiles `ollama`/`media`.
  `MEDIA_ASR_URL`/`MEDIA_OCR_URL` fixos no agente. Overrides: `docker-compose.cpu.yml`,
  `docker-compose.demo.yml`. Removido `docker-compose.media.yml`.
- **Hardware alvo (README):** RTX 3060 12 GB + 32 GB RAM; VRAM tip. ~8–10 GB
  (7b Q4 + whisper small); OCR/SBERT no CPU.
- **Grafo de fechamento:** `NoConclusao` + aresta `FECHA_COM` → `FechamentoSpec`
  (in-process; Graphify em `docs/grafo-fechamento/graphify-out/`). Neo4j no compose
  (`:7474`/`:7687`) com seed + dataset ganho.
- **Re-rank:** `orch_svc/rerank.py` — RAG top_k=10 + closes Neo4j → score
  (vetor + ganho/plano/close) → top 3 em `exemplos`; injetados no prompt de redação.
- **Ciclo E2E ganho:** qualifica → cota → aceite (`fechado`) → `emitir_apolice`
  (`estagio=contratado`). Script `scripts/e2e_ciclo_ganho.py` + log
  `docs/log-execucao-real.md`. Extração LLM ancorada no texto (anti-alucinação).
- **OCR dados enviados:** `/chat` aceita `media_base64` (+ `message_type=image|document`);
  Tesseract lê idade/ano/plano/CEP → fluxo normal. Smoke: `scripts/e2e_ocr_dados.py`.
- **Bootstrap corpus no compose:** `rag-ingest` (712 ganho → 771 chunks) + boot Neo4j
  (`NEO4J_INGEST_DATASET_ON_BOOT`) → clone sobe com o mesmo corpus da demo.
- **Observability ligado ao desempenho do modelo:** `GET /metrics` no agente (KPIs do
  audit: HITL, redação LLM, funil cotação/fechamento) + scrape de `svc-inference`
  (tokens/latência). Compose: `ALLOW_LOCAL_UPSTREAM`, `UPSTREAM_KEY`, `OBS_UPSTREAMS`
  (agente + inference + rag + guardrails). Overview: `POST :8205/v1/refresh` →
  `GET :8205/v1/overview`. Doc: `docs/metricas-modelo.md`. Validado 4/4 upstreams OK
  e KPIs = SQLite audit.
- **UI mínima de teste:** `GET /ui` → `app/static/chat.html` (caixa mensagem + resposta;
  mesma origem, chama `POST /chat`).
- **Aceite pós-cotação ampliado:** `vou contratar` / `aprovo` / `manda o boleto` etc.
  (antes só `quero contratar` → reapresentava cotação).
- **Pausa ≠ dúvida:** `vou pensar` / `depois te falo` → ação `adiar_conversa`
  (template, estágio `pausado`) — sem “Entendo sua dúvida”.
- **PRÓXIMO:** tornar repo público na entrega formal.

## Handoff / troca de LLM
Este STATE + README + docs/isolamento-dados.md + docs/metricas-modelo.md
+ arquitetura.html + docs/fluxo-quote.sequence.html
+ docs/arvore-decisao-planos.html = fonte de verdade.
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
**PRÓXIMO:** resposta redigida (svc-inference persona+tática); README final (decisões);
  opcional: subir svc-inference real e setar INFERENCE_URL.

## SESSÃO 2026-07-23 — EXTRAÇÃO LLM (PRÓXIMO anterior FEITO)
`orch_svc/extracao.py`: heurística + LLM opcional via `HttpInference`.
LLM enriquece plano/veículo/idade; falha → degrada para heurística (não bloqueia).
`app/main.py`: `INFERENCE_URL` / `INFERENCE_MODEL` opcionais; health expõe `inference`.
Body `/quote` nunca envia null (`cotacao_flow._extrair_body` filtra None).
Tests: test_extracao 5 → **38 passed** no pacote orch_svc tests.
**PRÓXIMO:** redigir resposta com persona+tática (svc-inference); README final.

## SESSÃO 2026-07-23 — RESPOSTA REDIGIDA (persona + tática)
`orch_svc/resposta.py`: `redigir_resposta(decisao, idade, …)`.
- Template determinístico por ação (cotação / pedir_dado / objeção / escala…).
- LLM opcional (`INFERENCE_URL`) reescreve no tom da persona sem inventar fatos.
- Objeção: injeta `framework` (LAER / feel-felt-found / …) no prompt/template.
- `/chat` passa a devolver `mensagem` (texto ao lead). Tests: test_resposta 5 → **43 passed**.
Smoke: /chat caminho feliz → mensagem com Essencial R$137.88, persona meia_30_50.
**PRÓXIMO:** README final (decisões / entregável #3).

## SESSÃO 2026-07-23 — PII no svc-guardrails + wire /chat
Check `pii` pt-BR (CPF/placa/CNH/CEP/email) em `guardrails/pii.py`; CNH rotulada antes do CPF genérico.
`/v1/analyze` inclui pii por default; texto mascarado em `sanitized_text` (logs), decisão allow/block só por injection.
Wire: `HttpGuardrails` → sanitize+injection+pii; `run_turno` block→HITL; slots extraídos do texto ORIGINAL (CEP intacto).
`app/main.py`: `GUARDRAILS_URL`. Compose: `8200` + `GUARDRAILS_URL=http://svc-guardrails:8200` (QUOTE/RAG ports alinhados).
Tests: test_pii + test_guardrails_wire; orch suite 45 passed.
**PRÓXIMO:** README final (decisões); opcional smoke com container guardrails.

## SESSÃO 2026-07-23 — CEP obrigatório (mantido)
Antes (`6cd6ca2`): `OPCIONAIS_ATIVOS=[cep]` — pedia 1x e cotava sem se o lead não der.
Agora (decisão confirmada): `cep` em `OBRIGATORIOS` + domain `missing=["cep"]` se ausente.
Sem CEP → `pedir_dado` (não cotar). Payload `/quote` sempre inclui `cep` quando ok.
`QuoteRequestPayload.cep: str` (não mais opcional no body montado pelo domain).
**PRÓXIMO:** README final (decisões).

## SESSÃO 2026-07-23 — svc-inference plug (item 4)
Wire já existia em `app/main.py` (`INFERENCE_URL` → extracao + redigir_resposta).
Fechado o gap operacional:
- `DemoBackend` no svc-inference (`BACKEND=demo`): extract → JSON de slots; polish → ecoa RASCUNHO.
- Compose: porta **8202**, `BACKEND=demo`, `INFERENCE_URL=http://svc-inference:8202`.
- Sem URL / falha → degrada pra heurística/template (não bloqueia).
- Ollama: `BACKEND=ollama` + `BACKEND_URL` + `DEFAULT_MODEL`.
Tests: `test_demo_backend`, `test_inference_plug`.
**PRÓXIMO:** README final (decisões / mapa régua); smoke compose ponta a ponta.

## SESSÃO 2026-07-23 — SMOKE caminho feliz
Stack: quote :8000 · guardrails :8200 · inference :8202 · rag :8204 · agente :8100.
`POST /chat` one-shot com idade+Corolla 2020+essencial+CEP+CPF →
`apresentar_cotacao` Essencial **R$137.88**, persona `meia_30_50`, PII mascarada no log
(`[CEP]`/`cpf` em guardrails), slots completos, `escalate=false`.
Snapshot: `docs/smoke-happy-path.json`.
**PRÓXIMO:** README final (decisões / mapa régua).

## SESSÃO 2026-07-23 — Compose completo + LLM de avaliação
- `docker-compose.yml`: quote + qdrant + guardrails + rag + inference + observability + **agente** (`app/main.py` :8100).
- LLM padrão de avaliação: **Ollama** (`--profile ollama` / `COMPOSE_PROFILES=ollama`) + `qwen2.5:3b` (`ollama-pull`).
- `OpenAICompatBackend` (`BACKEND=openai`) p/ cloud OpenAI-compat.
- Offline: `docker-compose.demo.yml` → `BACKEND=demo`.
- `Dockerfile` do agente · `env.example` · README atualizado.
**PRÓXIMO:** smoke `compose --profile ollama up` (pull do modelo); README decisões.

## SESSÃO 2026-07-23 — SMOKE feliz com Ollama (stack compose)
`docker compose --profile ollama up --build` → agente :8100 + inference `BACKEND=ollama`/`qwen2.5:3b`.
Fix: `plans.json` no Dockerfile do agente (`.dockerignore` excluía `quote-service`).
`POST /chat` → Essencial **R$137.88**, persona `meia_30_50`, PII mascarada; `mensagem` reformulada pelo LLM
(ex.: "R$ 137,88/mês… detalhe as coberturas?"). Snapshot: `docs/smoke-happy-path-ollama.json`.
**PRÓXIMO:** README final (decisões / mapa régua).

## SESSÃO 2026-07-23 — Eval amostras dataset × régua (realtime)
7 casos em `docs/eval-amostras/` (catálogo mascarado + resultados). Rodados 1 a 1 no `/chat`.
**7/7 PASS**: happy · quote fail (sintético rate=1) · objeção→HITL · mídia→pedir_dado · idade fora→recusar · trace · PII.
Gap: mídia ainda não tem `escalar_humano` dedicado (só não cota).

## SESSÃO 2026-07-23 — HITL mídia sem transcrição (gap fechado)
`orch_svc/midia.py` + `run_turno`/`ChatIn.message_type`: placeholder `[documento]|[áudio]|…`
ou `message_type=audio|image|document` → `escalar_humano` motivo **mídia sem transcrição**.
Legenda útil após marcador não escala. Tests: `test_midia` 5.

## SESSÃO 2026-07-23 — Plug ASR/OCR opcional (opção B, tear-free)
`MEDIA_ASR_URL` / `MEDIA_OCR_URL` + `media_url` no `/chat`. Sem URL → HITL (padrão avaliação).
Com URL: tenta `/v1/transcribe` ou `/v1/ocr`; texto útil → fluxo normal; falha → HITL.
README: tabela GPU/RAM (Whisper large ≥10 GB VRAM; stack padrão sem GPU).
Tests: enricher ok + falha→HITL.

## SESSÃO 2026-07-23 — Combo 3 media (whisper small + tesseract)
Profile `media`: `svc-media-asr` (:8210, faster-whisper **small**, GPU) + `svc-media-ocr` (:8211, Tesseract CPU).
`docker-compose.media.yml` seta `MEDIA_*_URL` no agente. Avaliação sem profile = HITL tear-free.
Orçamento: 3b+small ≈ 5–7 GB VRAM / 12 GB.

## SESSÃO 2026-07-23 — Compose único (solução completa) [REGISTRADO]
**Decisão:** a entrega sobe como UM stack — um comando = desafio ponta a ponta
(texto + áudio + cotação + HITL + PII + LLM).

**Mudanças:**
- Removidos profiles `ollama` / `media` e arquivo `docker-compose.media.yml`.
- `docker-compose.yml` sempre sobe: qdrant · quote-api · guardrails · rag ·
  inference · ollama + ollama-pull · svc-media-asr · svc-media-ocr ·
  observability · agente.
- Agente com `MEDIA_ASR_URL` / `MEDIA_OCR_URL` wired (sem opt-in).
- README: seção Hardware (VRAM/RAM) — alvo RTX 3060 12 GB + 32 GB RAM;
  orçamento tip. qwen 3b + whisper small ≈ 5–7 GB VRAM.
- Fallbacks (não são o caminho principal):
  - `docker-compose.cpu.yml` → ASR sem NVIDIA (`gpus: !reset []`)
  - `docker-compose.demo.yml` → omite ollama; `BACKEND=demo`

**Comando canônico:** `docker compose up --build`

**Validado:** `docker compose config --services` lista os 11 serviços do stack.

## SESSÃO 2026-07-23 — Audit log chat↔LLM (governança)
Gap: docker logs só tinham access log HTTP; resposta LLM ficava só no JSON HTTP.
Agora cada `/chat` emite:
1. linha JSON `audit.chat` no stdout do agente (docker logs) com lead_mascarado,
   rascunho, mensagem_agente, fonte, model, acao, slots (mascarados), premio.
2. evento `resposta` no payload (`eventos[]`) — só campos mascarados (`pii: masked`).
`redigir_resposta` → `RedacaoResult{texto,rascunho,fonte}`. Smoke: `docs/eval-amostras/smoke-audit-chat.json`.
**PII sempre ativa nos logs:** sem `lead` cru; CEP/CPF/e-mail/placa → `[CEP]`/`[CPF]`/…;
slots no audit com `cep: "[CEP]"`. API `/chat` ainda devolve slots reais p/ cotar.

## SESSÃO 2026-07-23 — SQLite audit por conversation_id
`app/audit_store.py` + volume `namastex_audit` (`AUDIT_DB_PATH=/data/audit.db`).
Cada `/chat` grava o mesmo payload `audit.chat` (PII masked) em `audit_turn` e
cada passo em `audit_event` (id + step + status). Consulta: `GET /audit/{conversation_id}`.
Smoke: `docs/eval-amostras/smoke-audit-sqlite.json`.
**Esclarecimento:** ao pedir “mostrar o log” antes do SQLite, o que apareceu na
conversa foi o JSON HTTP (`mensagem`/`eventos`) e access log uvicorn — NÃO a
consulta do store; `audit.chat` só existia em stdout do container.

## SESSÃO 2026-07-23 — Índice de fechamento (grafo cotação→CTA)
Problema: LLM (`qwen2.5:3b`) reescrevia e gerava CTA sem nexo (“ajustar o plano agora”),
às vezes omitindo o prêmio.
Solução: `orch_svc/fechamento_index.py` — lookup por `acao|persona` → molde parametrizado
(prêmio/plano/franquia/coberturas) + **CTA fixa** (detalhar coberturas OU comparar planos).
`resposta.py` usa o índice; LLM só estiliza; `validar_fechamento_llm` rejeita CTA proibida
ou ausência de prêmio → `llm_fallback` (template do índice).
Audit/SQLite passam a gravar `index_key` + `cta`.
Tests: `test_fechamento_index.py` + resposta. Smoke: `docs/eval-amostras/smoke-fechamento-index.json`.

## SESSÃO 2026-07-23 — Grafo formal NoConclusao + Graphify (sem Neo4j)
Runtime in-process (proporcional ao desafio; Neo4j evitado de propósito):
- `NoConclusao{acao, quote/coberturas, persona}` + aresta **`FECHA_COM`** → `FechamentoSpec`
- `orch_svc/conclusao_graph.py` · `resolver_fechamento()` · audit grava `conclusao_id` + `aresta`
- `GET /graph/fechamento` devolve catálogo nós/arestas
- Catálogo: `docs/grafo-fechamento/catalogo.json` + README
- **Graphify OSS** no corpus `docs/grafo-fechamento/src/` →
  `docs/grafo-fechamento/graphify-out/` (33 nós, 56 edges, god nodes:
  `resolver_fechamento`, `NoConclusao`, `FechamentoSpec`)
Decisão de produto: Graphify = documentação/visualização; runtime = grafo leve no agente.
Tests: `test_conclusao_graph.py`.

## SESSÃO 2026-07-23 — CTA omite plano já cotado
`cta_cotacao(plano_id)`: Essencial → “compare com Completo ou Premium?”;
Completo → Essencial ou Premium; Premium → Essencial ou Completo.
Validação LLM rejeita lista `(Essencial / Completo / Premium)` e relistar o plano
atual após “compare”. Tests + smoke `/chat` jovem essencial.

## SESSÃO 2026-07-23 — Neo4j no compose (grafo persistente)
Serviço `neo4j:5-community` (:7474 Browser / :7687 Bolt), volume `namastex_neo4j`,
heap default ~1 GB. Agente: `NEO4J_URI=bolt://neo4j:7687`, seed no boot
(`app/neo4j_graph.py`) — catálogo FECHA_COM + âncoras do dataset
(aprovar_cotacao → emitir_apolice → ganho). Endpoints:
`GET /graph/neo4j`, `GET /graph/neo4j/search`, `POST /graph/neo4j/seed`.
svc-rag também recebe NEO4J_* (caminho GraphRAG). Lookup in-process permanece;
Neo4j = pesquisa/persistência do grafo alinhado ao corpus.

## SESSÃO 2026-07-23 — Dataset → Neo4j + ciclo ganho (aprovar→apólice)
Ingest: `POST /graph/neo4j/seed-dataset` / `scripts/neo4j_seed_dataset.py`
(400+ conversas `ganho` → nós Conversation, MENTIONS_PLAN, EXEMPLIFIES emitir_apolice).
Agente: pós-`cotado`, aceite do lead (`fechado`/`pode emitir`/…) → `emitir_apolice`
(mensagem boleto+apólice, espelho dataset). `estagio=contratado`. Tests `test_aceitacao`.

## SESSÃO 2026-07-23 — Observability: métricas de desempenho do modelo
Antes: `svc-observability` no compose mas scrape 0/6 (lista portfolio + sem
`ALLOW_LOCAL_UPSTREAM`/`UPSTREAM_KEY`); trilha real = audit SQLite.
Agora:
- `AuditStore.model_performance_metrics()` + `GET /metrics` no agente (`X-Internal-Key`)
  — contadores/taxas: turns, HITL, `llm_redacao_rate`, `fechamento_sobre_cotacao_rate`, …
- `OBS_UPSTREAMS` no compose: agente · inference · rag · guardrails (override sem
  quebrar gates default do svc via `registry()`).
- Doc `docs/metricas-modelo.md` + link no README.
- Validação ao vivo: refresh 4/4 OK; overview do agente idêntico ao `/metrics`;
  contadores cruzados com SQL do audit (0 divergências). Caveat: p95 < p50 no
  inference com N≈2 amostras (quirk do percentil, não do agregador).
Commit: `55b9110`.

## SESSÃO 2026-07-23 — UI /ui + aceite + pausa respeitosa
- **UI:** `GET /ui` serve `app/static/chat.html` (input + resposta + conversation_id;
  sem visual WhatsApp). README aponta o link.
- **Bug aceite:** lead disse `vou contratar` → detector só tinha `quero contratar` →
  reapresentava cotação. Regex ampliada (`contratar`, `aprovo`, boleto/apólice…).
  Regressão: `test_emitir_apolice_vou_contratar`.
- **Bug pausa:** `vou pensar. depois te falo` caía em `indeciso` + molde
  “Entendo sua dúvida” (inventar dúvida). Agora `adiar_conversa` (template, sem LLM),
  estágio `pausado`, porta aberta. Pattern `depois` solto removido.
  Tests: `test_vou_pensar_adia_sem_inventar_duvida`, `test_detecta_indeciso_pausa`.
Commit: `b12800e`.

## SESSÃO 2026-07-24 — correções de interpretação (objeção/HITL) + GraphRAG real no svc-rag

**Auditoria da camada determinística de objeção** (regex que classifica a mensagem
do lead ANTES do LLM, em `orch_svc/objecoes.py`/`thread.py`) achou 3 falhas de
contexto, todas com teste de regressão:
- Pedido explícito de humano ("posso falar com o atendente?") não tinha handler —
  ou colava por acidente no regex de `indeciso` (virava pausa, o oposto do pedido)
  ou era ignorado. Nova função `pedido_humano()`, prioridade máxima em `run_turno`.
- `azul`/`porto` soltos no regex de `concorrente` confundiam cor de veículo/endereço
  com as seguradoras Azul/Porto Seguro — sequestravam a 1ª mensagem de qualificação.
  Agora exigem `azul seguros`/`porto seguro`.
- `preço`/`parcel` soltos disparavam tática de reversão de objeção pra pergunta
  neutra ("qual o preço do completo?") ANTES de qualquer cotação existir. Agora só
  reclamação real (`caro`, `desconto`, `alto`, `salgado`) é objeção.
Commits: `6dc22fd`, `65680ac`. 130 testes no pacote orch_svc+domínio+app.

**GraphRAG real no `svc-rag` (estava só a metade — auditoria achou):** `docker-compose.yml`
passava `NEO4J_URI/USER/PASSWORD` pro container, mas `config.py` nunca lia essas
env vars — zero linhas conectavam `svc-rag` ao Neo4j. `GET /v1/community/{id}` lia
um `communities.json` que **não existia no repo** (fixture de teste ainda era do
domínio antigo "Finanças", nunca adaptado). `/v1/search` nunca tocava em comunidade.

Implementado de verdade:
- `rag_svc/community_builder.py` (lógica pura, testável): grafo denso por
  `(plano, faixa_etária)` + pontes fracas entre faixas do mesmo plano (clique só
  por plano não se particiona por modularidade — achado ao rodar a 1ª versão: 3
  comunidades = 3 planos, faixa etária nunca aparecia). `louvain_communities`.
- `scripts/build_rag_communities.py`: lê o grafo `Conversation`/`MENTIONS_PLAN`/
  `HAS_OUTCOME` **do Neo4j** (não do parquet direto — usa o grafo que já existe),
  gera `services/svc-rag/models/communities.json` (9 comunidades: 3 planos × 3
  faixas presentes no dataset ganho, 712 conversas).
- `CommunityStore.community_of(doc_id)`: índice reverso membro→comunidade.
- `/v1/search`: anota cada hit com `community_id`/`community_title`; reordena pra
  reforçar a comunidade dominante entre os hits (`score` vetorial não é alterado,
  só a ordem — `_COMMUNITY_BOOST=0.05`). Fail-open: sem artefato/flag ou qualquer
  erro, devolve os hits como vieram.
- Geração é **offline** (script lê Neo4j 1x, artefato é versionado e copiado no
  Dockerfile) — o serviço em runtime não abre conexão Neo4j, evitando round-trip
  bolt em toda busca. `depends_on: neo4j` e env vars mortas removidas do compose;
  `GRAPHRAG_ENABLED` default virou `1`.
- Dockerfile precisou de `!models/communities.json` no `.dockerignore` (mesmo
  gotcha do `plans.json`/quote-service em sessão anterior — pasta inteira ignorada).
- Tests: `test_community_builder.py` (6, lógica pura) + `test_search_graphrag.py`
  (5, anotação/rerank/fail-open) + `test_community_of_membership`. 60/60 no
  `svc-rag` (era 47/54 antes, excluindo o `test_contract.py` que já falhava por
  dependência dev ausente no ambiente local, não relacionado).

**Escopo consciente (revisado — expansão implementada):** a decisão original foi
não fazer live query Neo4j em `/v1/search`. Ao explicar melhor o porquê, separei
duas coisas que a frase original juntava indevidamente: (1) expansão de grafo
(buscar membros da comunidade fora do top_k vetorial) e (2) conexão Neo4j ao
vivo. (1) NÃO precisa de Neo4j — a lista de membros já está em memória, vinda
do artefato; só faltava buscar o TEXTO desses membros por id. Implementado:
- `VectorStore.get_by_ids(collection, doc_ids)` — novo método no Protocol.
  `InMemoryStore`: filtro direto. `QdrantStore`: `points/scroll` com filtro de
  payload em `doc_id` (o id do ponto no Qdrant é uuid5(chunk_id), não doc_id —
  não dá pra usar retrieve-by-point-id direto).
- `_expand_dominant_community` em `app.py`: até 2 membros da comunidade
  dominante que não vieram no vetor, score = `min(scores) - 0.01` (nunca
  outranka similaridade real), `metadata.graphrag_expansion=true`.
- Validado ao vivo contra Qdrant real (não só InMemoryStore dos testes):
  `top_k=3` pedido → 5 hits voltaram (3 vetoriais + 2 expansão), score de
  expansão exatamente `floor - 0.01` como esperado.
(2) Conexão Neo4j ao vivo em `/v1/search` **continua fora de escopo, por
decisão** — o grafo só muda quando o dataset muda, não por requisição; abrir
bolt por busca contradiria o padrão fail-open do resto do projeto (RAG/quote/
guardrails todos degradam sem travar).
Tests: `test_get_by_ids_*` (store), `test_expande_com_membros_*` /
`test_expansao_nao_duplica_*` (app). 65/65 no pacote svc-rag.
