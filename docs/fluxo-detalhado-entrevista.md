# Fluxo detalhado do agente — do lead ao LLM (material de entrevista)

> **Como este documento foi gerado:** não é uma descrição aproximada — cada dado
> abaixo (scores do RAG, candidatos do Neo4j, o prompt exato, a resposta do LLM)
> foi capturado rodando as **funções reais de produção** contra o stack completo
> no ar (Qdrant + Neo4j + Ollama `qwen2.5:7b` + quote-service reais), pra uma
> mensagem de exemplo. Nada aqui foi inventado ou resumido de memória — é o que
> o sistema faz de verdade.
>
> Mensagem de exemplo: **"tenho 35 anos, Gol 2020, plano essencial, cep
> 01310-100"** (primeiro turno de uma conversa nova, caminho feliz).

## Visão geral — os 17 estágios

```
1. POST /chat chega                         10. Decisão (DecisaoCotacao)
2. Guardrails (sanitize/PII/injection)       11. Grafo de fechamento (rascunho)
3. Pedido de humano? / objeção? / pausa?     12. Persona (estilo por idade)
   3b. Se objeção: tática vem do Neo4j       13. Prompt final (system+user)
       (Objecao-[:TEM_TATICA]->Tatica),      14. Chamada ao LLM (Ollama)
       fallback pro dict se grafo cair       15. Validação anti-alucinação
4. Extração de slots (heurística + LLM)      16. Auditoria (mask PII, SQLite)
5. Porteiro do domínio (valida/normaliza)    17. Resposta final ao lead
6. Coleta ativa (falta dado? pergunta)
7. Busca RAG (Qdrant, vetorial)
8. Busca Neo4j (closes por plano — GraphRAG)
9. Re-rank (RAG+Neo4j → top 3 exemplos)
   → cliente resiliente do /quote (retry+circuit)
```

Cada estágio abaixo tem: **o que faz**, **onde no código**, **o dado real**
capturado neste exemplo, e **por que existe** (a função prática — o que
responder se um entrevistador perguntar "por que você fez assim?").

---

## 1. `POST /chat` chega

`app/main.py:chat()`. Corpo: `{conversation_id, mensagem, idade?, message_type?,
media_url?, media_base64?}`. O agente busca o estado da conversa no
`ThreadStore` (`orch_svc/thread.py`) pelo `conversation_id` — se não existe,
cria um `ThreadState` novo (slots vazios, `estagio="qualificando"`).

**Por quê:** o `/chat` é *stateful por conversa*, não one-shot — o desafio pede
um agente que "conduz" o lead (pergunta só o que falta, lembra o que já foi
dito), não um Q&A avulso.

---

## 2. Guardrails — sanitização, PII, injection

`orch_svc/clients.py:HttpGuardrails.analyze()` → `POST svc-guardrails:8200/v1/analyze`.

**Dado real capturado:**
```json
{
  "decision": "allow",
  "sanitized_text": "tenho 35 anos, Gol 2020, plano essencial, cep [CEP]",
  "pii_types": ["cep"],
  "patterns": []
}
```

O CEP é detectado como PII e mascarado **só na versão usada pra log/audit** — o
texto original (com CEP de verdade) segue pro resto do pipeline, porque o CEP é
necessário pra cotar (regra de região do `/quote`). `decision` só vira `block`
por injection/prompt-injection — PII sozinho não bloqueia, só marca.

**Por quê:** critério explícito da régua ("cuidado com dados sensíveis"). Rodar
guardrails **antes** de qualquer outra lógica garante que nada com injection
chega no LLM, e que todo log subsequente já sabe o que precisa mascarar.

**Se cair:** `run_turno` captura a exceção, loga `guardrails: degraded` e
**segue o turno normalmente** (fail-open) — guardrails fora do ar não pode
travar o agente inteiro; só perde a camada de defesa extra daquele turno.

---

## 3. Pedido de humano? Objeção? Pausa? (checados ANTES de qualificar)

Ordem exata em `orch_svc/thread.py:run_turno`, cada um com **prioridade total**
sobre o resto se disparar:

1. `pedido_humano(mensagem)` — regex dedicado ("falar com atendente/humano/pessoa").
   Se disparar: `escalar_humano` direto, sem passar por nada mais.
2. `detectar_aceite_cotacao` — só se `estagio == "cotado"` (ex.: "pode contratar").
3. `detectar_objecao(mensagem)` — preço/concorrente/cobertura/indeciso.

Nenhum dos três disparou nesta mensagem (é uma mensagem de qualificação normal,
não objeção/pausa/pedido de humano), então o fluxo segue.

**Por quê:** esses três já foram **bugs reais** corrigidos nesta sessão — regex
de objeção sem contexto sequestrava mensagens de qualificação (ex.: "carro
azul" virava objeção de concorrente "Azul Seguros"); pedido de humano caía por
acidente no regex de pausa. Rodar essa checagem **antes** da extração de slots
é o que garante que essas prioridades vencem qualquer outra interpretação.

---

## 3b. Se fosse objeção: de onde vem a tática (grafo Neo4j primeiro)

Não é o caso desta mensagem de exemplo, mas é uma peça importante do pipeline
que merece o mesmo nível de detalhe. Quando `detectar_objecao` dispara (ex.:
"achei muito caro"), `orch_svc/objecoes.py:proxima_acao()` decide **qual
tática usar nesta tentativa** — e a fonte dessa tática não é mais só um dict
Python: é o grafo Neo4j primeiro, com o dict como rede de segurança.

```
(:Objecao {tipo:"preco"}) -[:TEM_TATICA {ordem:0}]-> (:Tatica {texto, framework})
                          -[:TEM_TATICA {ordem:1}]-> (:Tatica {...})
                          -[:TEM_TATICA {ordem:2}]-> (:Tatica {...})
```

**Dado real capturado** (`GET /graph/neo4j/taticas/preco`):
```json
[
  {"texto": "Reconhecer e reancorar: 'entendo — à primeira vista parece; olhando a cobertura por dia, é proteção do seu carro por centavos.'", "framework": "feel-felt-found + ancoragem-valor", "ordem": 0},
  {"texto": "Isolar a objeção: 'além do valor, tem mais algo que te impede de fechar?' Se for só preço, oferecer plano essencial (entrada menor) ou parcelamento.", "framework": "isolamento + alternativa", "ordem": 1},
  {"texto": "Ancorar no risco: comparar a mensalidade com o custo de um sinistro sem seguro (guincho, terceiros, perda total).", "framework": "ancoragem-valor", "ordem": 2}
]
```

`proxima_acao(objecao, tentativas_feitas, taticas_provider=...)` pega a tática
no índice `tentativas_feitas` dessa lista — 1ª objeção usa `ordem=0`
(feel-felt-found), persiste → `ordem=1` (isolamento), persiste de novo →
`ordem=2` (ancoragem no risco), persiste uma 4ª vez → esgotou, `escalar_humano`.

**`taticas_provider` é injeção de dependência** (`app/main.py:_taticas_provider`),
mesmo padrão usado pra `rag`/`quote_client`/`graph_examples` no resto do
pipeline — o `orch_svc` (camada de decisão) nunca importa `Neo4j` diretamente,
só recebe uma função. Se o provider vier vazio ou lançar exceção,
`proxima_acao` cai pro dict `TATICAS` hardcoded no próprio módulo — **mesmo
conteúdo, mas o Neo4j fora do ar nunca impede reverter uma objeção**.

**Por quê materializar no grafo em vez de deixar só no dict:** deixa a
extensão natural pronta — trocar ou adicionar tática vira uma escrita no
grafo, sem precisar de deploy. Testado ao vivo: uma objeção de preço real via
`/chat` devolveu o texto exatamente igual ao lido pelo endpoint acima — prova
de que o runtime lê do grafo de verdade (não é um catálogo espelhado e nunca
consultado, como cheguei a identificar e criticar em outra parte do grafo
antes de implementar este).

---

## 4. Extração de slots — heurística + LLM ancorada (anti-alucinação)

`orch_svc/extracao.py:extrair_slots()`. Dois passos:

1. **Heurística** (regex, sem rede): `idade`, `veiculo_ano`, `cep`, `plano_id`.
2. **LLM opcional** (`svc-inference` → Ollama): pede o mesmo em JSON, mas cada
   campo só é aceito se **aparecer literalmente no texto** do lead
   (`_ancorado_no_texto` — ex.: só aceita `idade=35` se `"35 anos"` estiver na
   mensagem). Isso existe especificamente pra impedir o LLM de "completar"
   dados que o lead não disse.

**Dado real capturado** (heurística e LLM bateram igual, mensagem já clara):
```json
{"idade": 35, "veiculo_ano": 2020, "cep": "01310-100", "plano_id": "essencial"}
```

**Por quê:** a heurística sozinha erra em texto livre ("um Gol branco do ano
passado"); o LLM sozinho alucina. A combinação com ancoragem pega o melhor dos
dois sem inventar dado que vira prêmio errado.

**Se o LLM falhar/timeout:** `extrair_slots` cai de volta pra heurística
(try/except) — degrada, não quebra o turno.

---

## 5. Porteiro do domínio — `domains/seguro_auto/build.py`

`build_quote_request(slots, verified=True)`. Papel: **normalizar e validar**
os slots contra `quote-service/data/plans.json` (idade mínima/máxima aceitável,
plano existe, CEP tem formato válido) e montar o `body` exato do `POST /quote`.
**Não calcula prêmio** — só decide se o pedido está bem formado pra tentar
cotar, e monta o payload.

**Dado real capturado:**
```json
{"missing": [], "errors": [], "refusals": [],
 "payload": {"plano_id": "essencial", "idade": 35, "veiculo_ano": 2020,
             "cep": "01310-100", "data_inicio": "2026-07-24"}}
```

Três saídas possíveis: `missing` (falta dado → `pedir_dado`), `refusals`
(regra local recusa, ex. idade fora de faixa → `recusar`), ou `payload` pronto
(segue pra cotar). Neste caso, tudo ok.

**Por quê:** separar "isso está bem formado pra cotar" (determinístico, no
domínio) de "quanto custa" (determinístico, no `quote-service`) do "LLM decide
algo" — o LLM **nunca** toca em regra de negócio ou cálculo de prêmio.

---

## 6. Coleta ativa

`OBRIGATORIOS = ["idade", "veiculo_ano", "plano_id", "cep"]` em `thread.py`.
Se algum faltar, o agente **pergunta só o que falta** (não usa default
silencioso pro plano) e não avança pro `/quote`. Neste exemplo, os 4 já vieram
na primeira mensagem — segue direto.

**Por quê:** bug corrigido numa sessão anterior — o agente cotava Essencial
"no silêncio" quando o lead não dizia o plano, o que é ruim pro lead
(cotação errada sem ele saber) e pro negócio (subcotação).

---

## 7. Busca RAG — como funciona de verdade

`orch_svc/clients.py:HttpRag.search()` → `POST svc-rag:8204/v1/search`
`{query: mensagem, collection: "namastex_conversas", top_k: 10}`.

Dentro do `svc-rag` (`rag_svc/ingest.py:search_documents`):
1. A **mensagem inteira do lead** vira o embedding de busca — `embedder.encode([query])`,
   modelo `paraphrase-multilingual-MiniLM-L12-v2` (SBERT, roda local, sem custo de API).
2. O vetor é comparado por **cosseno** contra os ~771 chunks da coleção
   `namastex_conversas` (só conversas com `outcome=ganho` do dataset — decisão
   de curadoria: só ensinar o LLM com exemplos de conversa que **fechou**).
3. Volta o `top_k=10` mais similares.

**Dado real capturado** (2 primeiros dos 10, score = similaridade de cosseno):
```
0.5507 — "lead_idade_informada: 31 · veiculo: Fiat Mobi 2020 · [lead] eae,
          tudo bem? to querendo segurar meu carro..."
0.5416 — "lead_idade_informada: 35 · veiculo: Honda Civic 2020 · [lead] eae,
          tudo bem?..."
```

Repare: são conversas **parecidas em texto** (idade+veículo mencionados), mas
o RAG puro não sabe se são do plano certo nem se fecharam com aquele plano
específico — só sabe que o *texto* é parecido. É aí que entra o próximo passo.

**Por quê:** o desafio pede explicitamente usar o dataset ("entender padrões,
few-shot, avaliação"). RAG puro por similaridade de texto é o uso mais direto
— mas sozinho é um sinal fraco (não considera plano nem se a venda fechou).

---

## 8. Busca Neo4j — closes por plano (GraphRAG)

`app/main.py:_graph_examples(plano_id)` → `Neo4jGraph.search_similar_closes()`.
Cypher real executado:
```cypher
MATCH (c:Conversation)-[:HAS_OUTCOME]->(:CorpusAnchor {label: 'ganho'})
MATCH (c)-[:MENTIONS_PLAN]->(:Plano {plano_id: 'essencial'})
WHERE c.has_close = true
RETURN c.id, c.veiculo, c.idade, c.n_msgs
LIMIT 5
```

Diferença chave pro passo 7: aqui a busca é **estruturada** (grafo), não por
texto — filtra exatamente por `plano=essencial` E `has_close=true` (sinal de
fechamento real: "boleto", "apólice" etc. no texto). O RAG do passo 7 não sabe
disso; o Neo4j sabe porque o grafo foi montado com essas arestas explícitas
(`MENTIONS_PLAN`, `HAS_OUTCOME`) no boot do agente.

**Dado real capturado:**
```
outcome=ganho has_close=true plano=essencial conversa=#conv_00534
  veiculo=Hyundai HB20 2019 idade=61 — fechado boleto apólice
outcome=ganho has_close=true plano=essencial conversa=#conv_02482
  veiculo=Chevrolet Onix Plus 2022 idade=41 — fechado boleto apólice
... (5 no total)
```

**Por quê:** complementa o RAG com um sinal que **texto sozinho não capta** —
"este exemplo é do MESMO plano que estou cotando agora e fechou de verdade".
Isso é literalmente a diferença entre RAG puro e GraphRAG: estrutura do grafo
enriquecendo a recuperação por similaridade.

---

## 9. Re-rank — RAG + Neo4j → top 3 exemplos

`orch_svc/rerank.py:rerank()`, chamado por `cotacao_flow._coletar_exemplos()`.
Pega os 10 candidatos do RAG + os 5 do Neo4j (15 no total), e cada um recebe um
**score composto**:

```
score = base (similaridade vetorial, ou 0.55 fixo pros do Neo4j)
       + 0.18 se outcome=ganho aparece no texto
       + 0.22 se o plano bate com o que está sendo cotado
       + 0.16 se tem sinal de fechamento (boleto/apólice/"maravilha")
       + 0.10 se veio do Neo4j (bônus de confiança estrutural)
       + 0.12 × overlap léxico com a mensagem do lead
```

**Dado real capturado** — os 3 vencedores foram **todos do Neo4j**, não do RAG
puro, porque o bônus de plano+close+fonte supera a similaridade textual pura:

| # | score final | fonte | plano_match | close_signal | overlap |
|---|---|---|---|---|---|
| 1 | 1.25 | neo4j | essencial | true | 0.333 |
| 2 | 1.2367 | neo4j | essencial | true | 0.222 |
| 3 | 1.2367 | neo4j | essencial | true | 0.222 |

**Por quê:** isso é o coração do "GraphRAG leve" do projeto — não é
cross-encoder pesado (sem GPU extra pra isso), é uma fórmula simples que
prioriza **exemplos do plano certo que fecharam de verdade** sobre exemplos
"parecidos em texto mas sem garantia de contexto". Os 3 vencedores viram
`exemplos` — vão pro prompt do LLM como referência de tom, não de fato.

---

## 9b. Cliente resiliente do `/quote`

`orch_svc/quote_client.py:ResilientQuoteClient.quote()`.

**Corpo enviado** (montado pelo porteiro no passo 5):
```json
{"plano_id": "essencial", "idade": 35, "veiculo_ano": 2020,
 "cep": "01310-100", "data_inicio": "2026-07-24"}
```

**Resposta real do `/quote`:**
```json
{"plano_id": "essencial", "plano_nome": "Essencial", "premio_mensal": 137.88,
 "franquia": 4500, "coberturas": ["colisao", "roubo", "furto"],
 "multiplicadores": {"faixa_etaria": 1.0, "idade_veiculo": 1.15, "regiao": 1.0},
 "carencia": {"coberturas": ["roubo", "furto"], "dias": 30, "observacao": "..."},
 "primeiro_pagamento_pro_rata": {"dias_no_mes": 31, "dias_cobrados": 8,
                                  "valor_primeiro_pagamento": 35.58}}
```

Mapeamento de status → ação: `200 QUOTED` → apresentar · `422 REFUSED` → recusar
(não reintenta, é regra de negócio) · `400 INVALID` → pedir correção · `5xx/timeout`
→ retry com backoff exponencial (até 3x) → se esgotar, circuito abre (3 falhas
seguidas) → `UNAVAILABLE` → **escalar humano, nunca inventa prêmio**.

**Por quê:** o critério que "mais separa" na régua do desafio é justamente
"o que faz quando `/quote` falha" — o quote-service simula 20% de
instabilidade de propósito. Testado ao vivo forçando `QUOTE_FAILURE_RATE=1`
(ver `docs/curadoria-e2e/relatorio.md`, cenário `quote_indisponivel`): esgota 3
tentativas em ~9.5s e escala com mensagem grau A, sem jargão técnico pro lead.

---

## 10. Decisão — `DecisaoCotacao`

```python
DecisaoCotacao("apresentar_cotacao", quote={...}, exemplos=[...], exemplos_meta=[...])
```

Um dataclass simples que carrega: a ação escolhida, a cotação (se houver), os
3 exemplos re-ranqueados, e metadados de rastreabilidade. É o que atravessa da
camada de decisão pra camada de redação — **a ação já está decidida aqui**,
antes de qualquer LLM ser chamado.

**Por quê:** separar "o que decidir" (determinístico, testável sem LLM) de
"como dizer" (LLM, redação) é o que torna o sistema **auditável e testável**
— dá pra testar a lógica de decisão inteira (130 testes) sem precisar de
Ollama rodando.

---

## 11. Grafo de fechamento — `NoConclusao` → `FECHA_COM` → `FechamentoSpec`

`orch_svc/fechamento_index.py:resolver_fechamento()`. Monta um nó
`NoConclusao{acao, persona, plano, premio, ...}`, percorre a aresta `FECHA_COM`
até o `FechamentoSpec` (o molde de texto certo pra essa combinação
ação+persona+plano), e preenche o template.

**Dado real capturado:**
```json
{
  "no_id": "conclusao:apresentar_cotacao|meia_30_50|essencial",
  "aresta": "conclusao:apresentar_cotacao|meia_30_50|essencial-[FECHA_COM]->apresentar_cotacao|meia_30_50",
  "cta": "Quer que eu detalhe as coberturas ou compare com Completo ou Premium?",
  "rascunho": "Pronto — cotação do plano Essencial: R$ 137,88/mês (franquia R$ 4500). Cobre: colisao, roubo, furto. Quer que eu detalhe as coberturas ou compare com Completo ou Premium?"
}
```

Note que a **CTA já sabe omitir o plano que acabou de ser cotado** (compara só
com Completo/Premium, nunca relista Essencial) — isso é lógica determinística,
não pedido ao LLM.

**Por quê:** o `rascunho` é a resposta **de fallback garantida** — se o LLM
falhar ou inventar algo, o lead recebe isso, não um erro. É a rede de
segurança que faz o sistema nunca ficar mudo.

---

## 12. Persona — estilo por idade

`orch_svc/persona.py:persona_por_idade(35)` → `Faixa.MEIA` (31-50 anos):
tom **"equilibrado e consultivo"**, foco **"cobertura e proteção da família"**.

**Importante (achado anti-Goodhart, validado no dataset antes de fixar):**
idade **não prediz conversão** no dataset (ganho ~28-30% em todas as faixas) —
então persona aqui é **rapport/UX** (falar a língua do público), não uma
alavanca de venda. Só muda a REDAÇÃO, nunca a decisão (cotar/reverter/escalar
continuam iguais pra qualquer idade).

---

## 13. O prompt final — texto literal mandado pro LLM

`orch_svc/resposta.py:_prompt()`. Isto é o que **de fato** chega no Ollama
pra esta conversa — texto exato, sem edição:

**system:**
> Você é um agente de seguro auto no WhatsApp. Reescreva a mensagem ao lead no
> tom indicado, SEM mudar fatos nem a CTA. OBRIGATÓRIO: manter o valor do
> prêmio (número) e o nome do plano se existirem nos FATOS. OBRIGATÓRIO:
> terminar com a mesma intenção da CTA_OBRIGATORIA (detalhar coberturas OU
> comparar com os outros planos listados na CTA). PROIBIDO: perguntar para
> 'ajustar o plano agora' ou sugerir que o plano está errado. PROIBIDO: na
> comparação, relistar o plano que já foi cotado nos FATOS. NÃO invente
> prêmio, plano, franquia nem coberturas. NÃO adicione frases, promessas ou
> garantias que não estejam no RASCUNHO — reescreva só o que já está lá, no
> tom indicado; não acrescente conteúdo novo. Mantenha o valor do prêmio no
> formato R$ 0,00 (vírgula, 2 casas), nunca com ponto. NÃO mude a decisão
> (ação). Resposta curta (2-4 frases), só o texto final.

**user:**
> Estilo (meia_30_50): tom equilibrado e consultivo; foco em cobertura e
> proteção da família. - explicar o que o plano cobre e por quê. - conectar
> com proteção do patrimônio/família.
>
> MENSAGEM DO LEAD: tenho 35 anos, Gol 2020, plano essencial, cep 01310-100
> FATOS: {'conclusao_id': 'conclusao:apresentar_cotacao|meia_30_50|essencial',
> 'acao': 'apresentar_cotacao', 'plano': 'Essencial', 'premio_mensal':
> '137,88', 'franquia': '4500', 'coberturas': 'colisao, roubo, furto',
> 'faltam': [], 'motivos': [], 'escalate': False, 'framework': None,
> 'cta_obrigatoria': 'Quer que eu detalhe as coberturas ou compare com
> Completo ou Premium?'}
> RASCUNHO (molde do grafo FECHA_COM): Pronto — cotação do plano Essencial:
> R$ 137,88/mês (franquia R$ 4500). Cobre: colisao, roubo, furto. Quer que eu
> detalhe as coberturas ou compare com Completo ou Premium?
> CTA_OBRIGATORIA: Quer que eu detalhe as coberturas ou compare com Completo
> ou Premium?
> EXEMPLOS RE-RANKED (tom/estilo; NÃO copie fatos inventados):
> 1. outcome=ganho has_close=true plano=essencial conversa=#conv_02465
>    veiculo=Honda HR-V 2020 idade=81 — fechado boleto apólice
> 2. outcome=ganho has_close=true plano=essencial conversa=#conv_00534
>    veiculo=Hyundai HB20 2019 idade=61 — fechado boleto apólice
> 3. outcome=ganho has_close=true plano=essencial conversa=#conv_02482
>    veiculo=Chevrolet Onix Plus 2022 idade=41 — fechado boleto apólice
> Texto final:

**Ponto crucial pra explicar numa entrevista:** o LLM **não recebe autonomia
sobre o quê dizer** — ele recebe fatos fechados (FATOS), um rascunho já
correto (RASCUNHO), uma CTA obrigatória, e exemplos só de **estilo** (o prompt
avisa explicitamente "NÃO copie fatos inventados"). A única liberdade real do
LLM é a fraseologia — tom, ordem das frases, naturalidade. Isso é o que torna
a validação do passo 15 possível: dá pra checar mecanicamente se ele respeitou
os limites.

---

## 14. Chamada ao LLM

`orch_svc/clients.py:HttpInference.chat()` → `POST svc-inference:8202/v1/chat`
→ Ollama `qwen2.5:7b` (Q4, GPU).

**Resposta real capturada** (24.3s de latência nesta chamada, RTX 3060):
> "Pronto — cotação do plano Essencial: R$ 137,88/mês (franquia R$ 4500). Cobre
> colisão, roubo e furto. Quer que eu detalhe as coberturas ou compare com
> Completo ou Premium?"

Comparando com o RASCUNHO: o LLM manteve o prêmio, o plano, a CTA — só
reescreveu "Cobre: colisao, roubo, furto" (lista crua) pra "Cobre colisão,
roubo e furto" (português natural, acentuado). É exatamente o tipo de
melhoria que o LLM deveria trazer.

**Por quê Ollama local em vez de API paga:** custo zero por chamada, roda na
GPU já dedicada ao Whisper, e não depende de rede externa — mas o client
(`HttpInference`) é uma interface trocável (D5 no STATE.md): trocar pra Claude
API ou outro provider não muda nenhuma linha da lógica de decisão.

---

## 15. Validação anti-alucinação — `validar_fechamento_llm()`

`orch_svc/fechamento_index.py:validar_fechamento_llm()`. Checa
mecanicamente, sem outro LLM (barato e determinístico):
- CTA proibida não apareceu (ex.: "ajustar o plano agora", ou relistar o plano
  já cotado numa comparação)?
- Se `exigir_no_texto` (prêmio/plano) foi definido pra essa ação, o texto
  contém o valor exato (ou uma variação numérica equivalente — `_contem_premio`
  aceita "137,88", "137.88", "137,9" etc.)?

**Resultado real:** `passou=true`, fonte final = `"llm"`.

**Se tivesse falhado:** a resposta cai pro **RASCUNHO determinístico** (passo
11) — `fonte="llm_fallback"`. O lead nunca vê "resposta ruim do LLM"; na pior
das hipóteses, vê a versão sem polimento, mas sempre correta nos fatos.

**Por quê:** essa é a defesa contra alucinação em cima do LLM já restrito pelo
prompt — duas camadas (prompt + validação pós-hoc) em vez de confiar só numa.

---

## 16. Auditoria — mask + SQLite

`app/main.py:chat()` monta `audit_payload` com PII sempre mascarada
(`lead_mascarado`, `cep: "[CEP]"`) e grava em `AuditStore` (SQLite,
`app/audit_store.py`) por `conversation_id` + evento por passo (`step`,
`status`). Consultável em `GET /audit/{conversation_id}`.

**Por quê:** critério explícito da régua ("dá pra rastrear o que aconteceu? —
cada mensagem/cotação, com id e status").

---

## 17. Resposta final ao lead

```json
{"mensagem": "Pronto — cotação do plano Essencial: R$ 137,88/mês...",
 "decisao": {"acao": "apresentar_cotacao", "escalate": false, "quote": {...}},
 "estagio": "cotado", "slots": {...}, "eventos": [...]}
```

O `estagio` vira `"cotado"` — no próximo turno, se o lead aceitar
("pode contratar"), pula direto pra `emitir_apolice` sem recotar.

---

## E se algo falhar? (mapa de degradação por estágio)

| Estágio | Se falhar | O que o lead vê |
|---|---|---|
| Guardrails | fail-open, loga `degraded` | Segue normal |
| Extração LLM | cai pra heurística | Segue normal (menos preciso) |
| RAG | `_coletar_exemplos` ignora, `exemplos=[]` | Resposta sem few-shot, mas correta |
| Neo4j (closes) | `graph_examples` retorna `[]` | Idem |
| `/quote` 5xx/timeout | retry→circuit→`UNAVAILABLE` | HITL grau A, sem jargão, sem prêmio inventado |
| LLM (redação) indisponível | `redigir_resposta` usa `rascunho` direto | Resposta sem polimento, mas correta |
| LLM responde mas viola regra | `validar_fechamento_llm` rejeita → fallback | Idem |
| Mídia sem ASR/OCR configurado | `escalar_humano` (mídia sem transcrição) | Handoff educado |
| Neo4j (táticas de objeção) | `taticas_objecao` retorna `[]` | `proxima_acao` cai pro dict `TATICAS` — mesma tática, sem grafo |

---

## Perguntas prováveis de entrevista (e o gancho de resposta)

- **"Por que RAG E Neo4j, não só um dos dois?"** → RAG pega similaridade de
  texto; Neo4j pega estrutura (plano certo + fechou de verdade) que texto
  sozinho não capta. O re-rank combina os dois com uma fórmula simples (passo 9).
- **"Como você evita que o LLM invente o preço?"** → Duas camadas: o prompt
  proíbe explicitamente e dá o RASCUNHO já pronto; a validação pós-hoc
  (`validar_fechamento_llm`) checa mecanicamente se o número aparece no texto,
  e derruba pro fallback se não.
- **"O que acontece se o `/quote` cair no meio de uma conversa?"** → Retry com
  backoff (até 3x) → circuit breaker abre depois de falhas seguidas →
  `escalar_humano` com mensagem grau A (sem jargão técnico) — nunca inventa
  prêmio. Testado ao vivo forçando 100% de falha (`docs/curadoria-e2e/`).
- **"Por que separar decisão (grafo) de redação (LLM)?"** → Decisão precisa
  ser testável e auditável sem depender de infra de LLM — 130 testes rodam
  sem Ollama. O LLM só entra pra polir tom, nunca pra decidir.
- **"O que é 'GraphRAG' aqui, especificamente?"** → Comunidades detectadas via
  Louvain sobre o grafo Neo4j de conversas (agrupadas por plano+faixa etária),
  servidas como artefato offline pelo `svc-rag`, que anota/reordena/expande os
  resultados do `/v1/search` por coerência de comunidade — ver
  `docs/curadoria-e2e/` e a seção GraphRAG do README pra detalhe.
- **"Vocês usam o Neo4j só pra guardar dado, ou o runtime lê de verdade?"** →
  Os dois — mas com cuidado: o catálogo de fechamento é escrito no boot só pra
  inspeção/Browser (o runtime usa o grafo leve in-process, mais rápido). Já as
  **táticas de objeção** e os **closes por plano** (passo 8) são lidos de
  verdade em toda requisição relevante — validado ao vivo comparando o texto
  devolvido numa conversa real com o que o endpoint de leitura do grafo
  devolve (bateram exato). É uma distinção que vale fazer numa entrevista:
  nem todo nó no grafo tem um consumidor real, e isso foi avaliado caso a
  caso, não assumido.
