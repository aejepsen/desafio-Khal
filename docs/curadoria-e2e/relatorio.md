# Curadoria E2E — mapeamento de cenários (revisão manual)

Gerado em 2026-07-24 14:33:16 contra o stack real (LLM `qwen2.5:7b` via Ollama, quote-api real, Neo4j/Qdrant populados).

> Não é gate automático — é material pra revisão humana de tom/coerência/qualidade.

## caminho_feliz — Caminho feliz — qualifica → cota → aceita → apólice

Todos os dados de uma vez; aceite explícito depois da cotação.

`conversation_id`: `curadoria-caminho_feliz-1784914274`

**Turno 1** — lead: _tenho 35 anos, Gol 2020, plano essencial, cep 01310-100_

- ação: `apresentar_cotacao` · escalate: `False` · estágio: `cotado` · latência: 42.02s
- **resposta ao lead:** Pronto — cotação do plano Essencial: R$ 137,88/mês (franquia R$ 4500). Cobre colisão, roubo e furto. Quer que eu detalhe as coberturas ou compare com Completo ou Premium?

**Turno 2** — lead: _pode contratar_

- ação: `emitir_apolice` · escalate: `False` · estágio: `contratado` · latência: 12.9s
- **resposta ao lead:** Bem-vindo! Agora que você confirmou, vou gerar o boleto e enviar a apólice do plano Essencial (R$ 137,88/mês), que oferece cobertura para colisão, roubo e furto. Que sua família esteja protegida!
- motivos (internos): `['lead aprovou a cotação (padrão conversas ganho)']`

<details><summary>audit trail (mascarado)</summary>

```json
{
  "conversation_id": "curadoria-caminho_feliz-1784914274",
  "turns": [
    {
      "id": 70,
      "turno": 1,
      "acao": "apresentar_cotacao",
      "escalate": false,
      "premio_mensal": 137.88,
      "fonte_resposta": "llm",
      "created_at": "2026-07-24T17:31:56.588010+00:00",
      "audit": {
        "type": "audit.chat",
        "conversation_id": "curadoria-caminho_feliz-1784914274",
        "turno": 1,
        "estagio": "cotado",
        "persona": "meia_30_50",
        "lead_mascarado": "tenho 35 anos, Gol 2020, plano essencial, cep [CEP]",
        "acao": "apresentar_cotacao",
        "escalate": false,
        "motivos": [],
        "slots": {
          "idade": 35,
          "veiculo_ano": 2020,
          "cep": "[CEP]",
          "plano_id": "essencial",
          "data_inicio": "2026-07-24"
        },
        "premio_mensal": 137.88,
        "rascunho": "Pronto — cotação do plano Essencial: R$ 137,88/mês (franquia R$ 4500). Cobre: colisao, roubo, furto. Quer que eu detalhe as coberturas ou compare com Completo ou Premium?",
        "mensagem_agente": "Pronto — cotação do plano Essencial: R$ 137,88/mês (franquia R$ 4500). Cobre colisão, roubo e furto. Quer que eu detalhe as coberturas ou compare com Completo ou Premium?",
        "fonte_resposta": "llm",
        "index_key": "apresentar_cotacao|meia_30_50",
        "cta": "Quer que eu detalhe as coberturas ou compare com Completo ou Premium?",
        "conclusao_id": "conclusao:apresentar_cotacao|meia_30_50|essencial",
        "aresta": "conclusao:apresentar_cotacao|meia_30_50|essencial-[FECHA_COM]->apresentar_cotacao|meia_30_50",
        "model": "qwen2.5:7b",
        "pii": "masked"
      }
    },
    {
      "id": 71,
      "turno": 2,
      "acao": "emitir_apolice",
      "escalate": false,
      "premio_mensal": 137.88,
      "fonte_resposta": "llm",
      "created_at": "2026-07-24T17:32:09.484393+00:00",
      "audit": {
        "type": "audit.chat",
        "conversation_id": "curadoria-caminho_feliz-1784914274",
        "turno": 2,
        "estagio": "contratado",
        "persona": "meia_30_50",
        "lead_mascarado": "pode contratar",
        "acao": "emitir_apolice",
        "escalate": false,
        "motivos": [
          "lead aprovou a cotação (padrão conversas ganho)"
        ],
        "slots": {
          "idade": 35,
          "veiculo_ano": 2020,
          "cep": "[CEP]",
          "plano_id": "essencial",
          "data_inicio": "2026-07-24"
        },
        "premio_mensal": 137.88,
        "rascunho": "Maravilha! Vou gerar o boleto e te mando a apólice do plano Essencial (R$ 137,88/mês). Bem-vindo!",
        "mensagem_agente": "Bem-vindo! Agora que você confirmou, vou gerar o boleto e enviar a apólice do plano Essencial (R$ 137,88/mês), que oferece cobertura para colisão, roubo e furto. Que sua família esteja protegida!",
        "fonte_resposta": "llm",
        "index_key": "emitir_apolice",
        "cta": "Bem-vindo!",
        "conclusao_id": "conclusao:emitir_apolice|meia_30_50",
        "aresta": "conclusao:emitir_apolice|meia_30_50-[FECHA_COM]->emitir_apolice",
        "model": "qwen2.5:7b",
        "pii": "masked"
      }
    }
  ],
  "eventos": [
    {
      "id": 337,
      "turno": 1,
      "step": "turno",
      "status": "1",
      "detail": {
        "estagio": "qualificando"
      },
      "created_at": "2026-07-24T17:31:56.588010+00:00"
    },
    {
      "id": 338,
      "turno": 1,
      "step": "guardrails",
      "status": "allow",
      "detail": {
        "texto_mascarado": "tenho 35 anos, Gol 2020, plano essencial, cep [CEP]",
        "pii_types": [
          "cep"
        ],
        "patterns": []
      },
      "created_at": "2026-07-24T17:31:56.588010+00:00"
    },
    {
      "id": 339,
      "turno": 1,
      "step": "qualifica",
      "status": "ok",
      "detail": {
        "slots_acumulados": {
          "idade": 35,
          "veiculo_ano": 2020,
          "cep": "[CEP]",
          "plano_id": 
```

</details>

## objecao_escala — Objeção de preço — reverte 3x, escala na 4ª

Mostra as táticas (feel-felt-found/isolamento/ancoragem) e o escalonamento só depois de esgotar tentativas.

`conversation_id`: `curadoria-objecao_escala-1784914329`

**Turno 1** — lead: _tenho 42 anos, Corolla 2019, plano completo, cep 04567-000_

- ação: `apresentar_cotacao` · escalate: `False` · estágio: `cotado` · latência: 32.55s
- **resposta ao lead:** Pronto — cotação do plano Completo: R$ 241,38/mês (franquia R$ 3000). Cobre colisão, roubo, furto, terceiros e danos aos vidros. Quer que eu detalhe as coberturas ou compare com Essencial ou Premium?

**Turno 2** — lead: _achei muito caro_

- ação: `reverter_objecao` · escalate: `False` · estágio: `objecao` · latência: 11.25s
- **resposta ao lead:** Entendo — à primeira vista parece caro. Olhando a cobertura por dia, é proteção do seu carro por centavos. Faz sentido olharmos isso juntos?
- motivos (internos): `["Reconhecer e reancorar: 'entendo — à primeira vista parece; olhando a cobertura por dia, é proteção do seu carro por centavos.'"]`

**Turno 3** — lead: _ainda tá caro_

- ação: `reverter_objecao` · escalate: `False` · estágio: `objecao` · latência: 11.03s
- **resposta ao lead:** Entendo o ponto. Isolando a objeção: 'além do valor, tem mais algo que te impede de fechar?' Faz sentido olharmos isso juntos?
- motivos (internos): `["Isolar a objeção: 'além do valor, tem mais algo que te impede de fechar?' Se for só preço, oferecer plano essencial (entrada menor) ou parcelamento."]`

**Turno 4** — lead: _caro demais_

- ação: `reverter_objecao` · escalate: `False` · estágio: `objecao` · latência: 11.75s
- **resposta ao lead:** Entendo o ponto. Ancorar no risco: comparar a mensalidade com o custo de um sinistro sem seguro (guincho, terceiros, perda total). Faz sentido olharmos isso juntos?
- motivos (internos): `['Ancorar no risco: comparar a mensalidade com o custo de um sinistro sem seguro (guincho, terceiros, perda total).']`

**Turno 5** — lead: _muito caro mesmo_

- ação: `escalar_humano` · escalate: `True` · estágio: `escalado` · latência: 0.01s
- **resposta ao lead:** Quero te atender bem e já tentei alguns caminhos por aqui. Vou te conectar com um atendente humano pra continuar com calma.
- motivos (internos): `["objeção 'preco' persistiu após 3 tentativa(s)"]`

<details><summary>audit trail (mascarado)</summary>

```json
{
  "conversation_id": "curadoria-objecao_escala-1784914329",
  "turns": [
    {
      "id": 72,
      "turno": 1,
      "acao": "apresentar_cotacao",
      "escalate": false,
      "premio_mensal": 241.38,
      "fonte_resposta": "llm",
      "created_at": "2026-07-24T17:32:42.035310+00:00",
      "audit": {
        "type": "audit.chat",
        "conversation_id": "curadoria-objecao_escala-1784914329",
        "turno": 1,
        "estagio": "cotado",
        "persona": "meia_30_50",
        "lead_mascarado": "tenho 42 anos, Corolla 2019, plano completo, cep [CEP]",
        "acao": "apresentar_cotacao",
        "escalate": false,
        "motivos": [],
        "slots": {
          "idade": 42,
          "veiculo_ano": 2019,
          "cep": "[CEP]",
          "plano_id": "completo",
          "data_inicio": "2026-07-24"
        },
        "premio_mensal": 241.38,
        "rascunho": "Pronto — cotação do plano Completo: R$ 241,38/mês (franquia R$ 3000). Cobre: colisao, roubo, furto, terceiros, vidros. Quer que eu detalhe as coberturas ou compare com Essencial ou Premium?",
        "mensagem_agente": "Pronto — cotação do plano Completo: R$ 241,38/mês (franquia R$ 3000). Cobre colisão, roubo, furto, terceiros e danos aos vidros. Quer que eu detalhe as coberturas ou compare com Essencial ou Premium?",
        "fonte_resposta": "llm",
        "index_key": "apresentar_cotacao|meia_30_50",
        "cta": "Quer que eu detalhe as coberturas ou compare com Essencial ou Premium?",
        "conclusao_id": "conclusao:apresentar_cotacao|meia_30_50|completo",
        "aresta": "conclusao:apresentar_cotacao|meia_30_50|completo-[FECHA_COM]->apresentar_cotacao|meia_30_50",
        "model": "qwen2.5:7b",
        "pii": "masked"
      }
    },
    {
      "id": 73,
      "turno": 2,
      "acao": "reverter_objecao",
      "escalate": false,
      "premio_mensal": null,
      "fonte_resposta": "llm",
      "created_at": "2026-07-24T17:32:53.282113+00:00",
      "audit": {
        "type": "audit.chat",
        "conversation_id": "curadoria-objecao_escala-1784914329",
        "turno": 2,
        "estagio": "objecao",
        "persona": "meia_30_50",
        "lead_mascarado": "achei muito caro",
        "acao": "reverter_objecao",
        "escalate": false,
        "motivos": [
          "Reconhecer e reancorar: 'entendo — à primeira vista parece; olhando a cobertura por dia, é proteção do seu carro por centavos.'"
        ],
        "slots": {
          "idade": 42,
          "veiculo_ano": 2019,
          "cep": "[CEP]",
          "plano_id": "completo",
          "data_inicio": "2026-07-24"
        },
        "premio_mensal": null,
        "rascunho": "Entendo o ponto (feel-felt-found + ancoragem-valor). Reconhecer e reancorar: 'entendo — à primeira vista parece; olhando a cobertura por dia, é proteção do seu carro por centavos.' Faz sentido olharmos isso juntos?",
        "mensagem_agente": "Entendo — à primeira vista parece caro. Olhando a cobertura por dia, é proteção do seu carro por centavos. Faz sentido olharmos isso juntos?",
        "fonte_resposta": "llm",
        "index_key": "reverter_objecao",
        "cta": "Faz sentido olharmos isso juntos?",
        "conclusao_id": "conclusao:reverter_objecao|meia_30_50",
        "aresta": "conclusao:reverter_objecao|meia_30_50-[FECHA_COM]->reverter_objecao",
        "model": "qwen2.5:7b",
        "pii": "masked"
      }
    },
    {
      "id": 74,
      "turno": 3,
      "acao": "reverter_objecao",
      "escalate": false,
      "premio_mensal": null,
      "fonte_resposta": "llm",
      "created_at": "2026-07-24T17:33:04.316734+00:00",
      "audit": {
        "type": "audit.chat",
        "conversation_id": "curadoria-objecao_escala-1784914329",
        "turno": 3,
        "estagio": "objecao",
        "persona": "meia_30_50",
        "lead_mascarado": "ainda tá caro",
        "acao": "reverter_objecao",
        "escalate": false,
        "motivos": [
          "Isolar a objeção: 'além do valor,
```

</details>

## quote_indisponivel — Falha do /quote — escala humano (HITL grau A)

QUOTE_FAILURE_RATE forçado a 1.0 no quote-api pra esgotar retry+circuito.

`conversation_id`: `curadoria-quote_indisponivel-1784913054`

**Turno 1** — lead: _tenho 30 anos, HB20 2021, plano essencial, cep 20000-000_

- ação: `escalar_humano` · escalate: `True` · estágio: `qualificando` · latência: 9.52s
- **resposta ao lead:** Tive uma instabilidade no sistema de cotação agora e não consigo te passar um valor com segurança. Vou te conectar com um atendente humano pra continuar. Um atendente humano vai continuar daqui.
- motivos (internos): `['esgotou 3 tentativas (última: 502)']`

<details><summary>audit trail (mascarado)</summary>

```json
{
  "conversation_id": "curadoria-quote_indisponivel-1784913054",
  "turns": [
    {
      "id": 69,
      "turno": 1,
      "acao": "escalar_humano",
      "escalate": true,
      "premio_mensal": null,
      "fonte_resposta": "template",
      "created_at": "2026-07-24T17:11:04.103809+00:00",
      "audit": {
        "type": "audit.chat",
        "conversation_id": "curadoria-quote_indisponivel-1784913054",
        "turno": 1,
        "estagio": "qualificando",
        "persona": "jovem_18_30",
        "lead_mascarado": "tenho 30 anos, HB20 2021, plano essencial, cep [CEP]",
        "acao": "escalar_humano",
        "escalate": true,
        "motivos": [
          "esgotou 3 tentativas (última: 502)"
        ],
        "slots": {
          "idade": 30,
          "veiculo_ano": 2021,
          "cep": "[CEP]",
          "plano_id": "essencial",
          "data_inicio": "2026-07-24"
        },
        "premio_mensal": null,
        "rascunho": "Tive uma instabilidade no sistema de cotação agora e não consigo te passar um valor com segurança. Vou te conectar com um atendente humano pra continuar. Um atendente humano vai continuar daqui.",
        "mensagem_agente": "Tive uma instabilidade no sistema de cotação agora e não consigo te passar um valor com segurança. Vou te conectar com um atendente humano pra continuar. Um atendente humano vai continuar daqui.",
        "fonte_resposta": "template",
        "index_key": "escalar_humano",
        "cta": "Um atendente humano vai continuar daqui.",
        "conclusao_id": "conclusao:escalar_humano|jovem_18_30",
        "aresta": "conclusao:escalar_humano|jovem_18_30-[FECHA_COM]->escalar_humano",
        "model": null,
        "pii": "masked"
      }
    }
  ],
  "eventos": [
    {
      "id": 332,
      "turno": 1,
      "step": "turno",
      "status": "1",
      "detail": {
        "estagio": "qualificando"
      },
      "created_at": "2026-07-24T17:11:04.103809+00:00"
    },
    {
      "id": 333,
      "turno": 1,
      "step": "guardrails",
      "status": "allow",
      "detail": {
        "texto_mascarado": "tenho 30 anos, HB20 2021, plano essencial, cep [CEP]",
        "pii_types": [
          "cep"
        ],
        "patterns": []
      },
      "created_at": "2026-07-24T17:11:04.103809+00:00"
    },
    {
      "id": 334,
      "turno": 1,
      "step": "qualifica",
      "status": "ok",
      "detail": {
        "slots_acumulados": {
          "idade": 30,
          "veiculo_ano": 2021,
          "cep": "[CEP]",
          "plano_id": "essencial"
        }
      },
      "created_at": "2026-07-24T17:11:04.103809+00:00"
    },
    {
      "id": 335,
      "turno": 1,
      "step": "decide",
      "status": "escalar_humano",
      "detail": {
        "faltam": [],
        "premio_mensal": null,
        "escalate": true,
        "exemplos_n": 0,
        "rerank": false
      },
      "created_at": "2026-07-24T17:11:04.103809+00:00"
    },
    {
      "id": 336,
      "turno": 1,
      "step": "resposta",
      "status": "template",
      "detail": {
        "lead_mascarado": "tenho 30 anos, HB20 2021, plano essencial, cep [CEP]",
        "rascunho": "Tive uma instabilidade no sistema de cotação agora e não consigo te passar um valor com segurança. Vou te conectar com um atendente humano pra continuar. Um atendente humano vai continuar daqui.",
        "mensagem": "Tive uma instabilidade no sistema de cotação agora e não consigo te passar um valor com segurança. Vou te conectar com um atendente humano pra continuar. Um atendente humano vai continuar daqui.",
        "fonte": "template",
        "index_key": "escalar_humano",
        "cta": "Um atendente humano vai continuar daqui.",
        "conclusao_id": "conclusao:escalar_humano|jovem_18_30",
        "aresta": "conclusao:escalar_humano|jovem_18_30-[FECHA_COM]->escalar_humano",
        "model": null,
        "pii": "masked"
      },
      "created_at": "2026-07-24T17:11:04.103809+00:00"
    }
  ]
}
```

</details>

## midia_sem_transcricao — Mídia sem transcrição — escala humano

Documento sem media_url/media_base64 (sem OCR possível).

`conversation_id`: `curadoria-midia_sem_transcricao-1784914396`

**Turno 1** — lead: _[documento] CNH.pdf_

- ação: `escalar_humano` · escalate: `True` · estágio: `escalado` · latência: 0.0s
- **resposta ao lead:** Recebi sua mídia, mas não consegui ler o conteúdo com segurança por aqui. Vou te conectar com um atendente humano pra seguir.
- motivos (internos): `['mídia sem transcrição']`

<details><summary>audit trail (mascarado)</summary>

```json
{
  "conversation_id": "curadoria-midia_sem_transcricao-1784914396",
  "turns": [
    {
      "id": 77,
      "turno": 1,
      "acao": "escalar_humano",
      "escalate": true,
      "premio_mensal": null,
      "fonte_resposta": "template",
      "created_at": "2026-07-24T17:33:16.084648+00:00",
      "audit": {
        "type": "audit.chat",
        "conversation_id": "curadoria-midia_sem_transcricao-1784914396",
        "turno": 1,
        "estagio": "escalado",
        "persona": "desconhecida",
        "lead_mascarado": "[documento] CNH.pdf",
        "acao": "escalar_humano",
        "escalate": true,
        "motivos": [
          "mídia sem transcrição"
        ],
        "slots": {},
        "premio_mensal": null,
        "rascunho": "Recebi sua mídia, mas não consegui ler o conteúdo com segurança por aqui. Vou te conectar com um atendente humano pra seguir.",
        "mensagem_agente": "Recebi sua mídia, mas não consegui ler o conteúdo com segurança por aqui. Vou te conectar com um atendente humano pra seguir.",
        "fonte_resposta": "template",
        "index_key": "escalar_humano",
        "cta": "Um atendente humano vai continuar daqui.",
        "conclusao_id": "conclusao:escalar_humano|desconhecida",
        "aresta": "conclusao:escalar_humano|desconhecida-[FECHA_COM]->escalar_humano",
        "model": null,
        "pii": "masked"
      }
    }
  ],
  "eventos": [
    {
      "id": 371,
      "turno": 1,
      "step": "turno",
      "status": "1",
      "detail": {
        "estagio": "qualificando"
      },
      "created_at": "2026-07-24T17:33:16.084648+00:00"
    },
    {
      "id": 372,
      "turno": 1,
      "step": "midia",
      "status": "document",
      "detail": {
        "motivo": "mídia sem transcrição",
        "status": "skip",
        "enricher": true,
        "has_url": false,
        "has_b64": false
      },
      "created_at": "2026-07-24T17:33:16.084648+00:00"
    },
    {
      "id": 373,
      "turno": 1,
      "step": "decide",
      "status": "escalar_humano",
      "detail": {
        "escalate": true,
        "motivo": "mídia sem transcrição"
      },
      "created_at": "2026-07-24T17:33:16.084648+00:00"
    },
    {
      "id": 374,
      "turno": 1,
      "step": "resposta",
      "status": "template",
      "detail": {
        "lead_mascarado": "[documento] CNH.pdf",
        "rascunho": "Recebi sua mídia, mas não consegui ler o conteúdo com segurança por aqui. Vou te conectar com um atendente humano pra seguir.",
        "mensagem": "Recebi sua mídia, mas não consegui ler o conteúdo com segurança por aqui. Vou te conectar com um atendente humano pra seguir.",
        "fonte": "template",
        "index_key": "escalar_humano",
        "cta": "Um atendente humano vai continuar daqui.",
        "conclusao_id": "conclusao:escalar_humano|desconhecida",
        "aresta": "conclusao:escalar_humano|desconhecida-[FECHA_COM]->escalar_humano",
        "model": null,
        "pii": "masked"
      },
      "created_at": "2026-07-24T17:33:16.084648+00:00"
    }
  ]
}
```

</details>

## ocr_dados — OCR de imagem com dados — extrai e segue fluxo normal

Fixture real (docs/fixtures/ocr_dados_cotacao.png) via Tesseract.

`conversation_id`: `curadoria-ocr_dados-1784912914`

**Turno 1** — lead: _[imagem] dados.png_

- ação: `apresentar_cotacao` · escalate: `False` · estágio: `cotado` · latência: 28.03s
- **resposta ao lead:** Pronto — cotação do plano Completo: R$ 241.38/mês (franquia R$ 3000). Cobre colisão, roubo, furto, terceiros e danos aos vidros. Quer que eu detalhe as coberturas ou compare com Essencial ou Premium?

<details><summary>audit trail (mascarado)</summary>

```json
{
  "conversation_id": "curadoria-ocr_dados-1784912914",
  "turns": [
    {
      "id": 63,
      "turno": 1,
      "acao": "apresentar_cotacao",
      "escalate": false,
      "premio_mensal": 241.38,
      "fonte_resposta": "llm",
      "created_at": "2026-07-24T17:09:02.698321+00:00",
      "audit": {
        "type": "audit.chat",
        "conversation_id": "curadoria-ocr_dados-1784912914",
        "turno": 1,
        "estagio": "cotado",
        "persona": "meia_30_50",
        "lead_mascarado": "[imagem] dados.png",
        "acao": "apresentar_cotacao",
        "escalate": false,
        "motivos": [],
        "slots": {
          "idade": 42,
          "veiculo_ano": 2020,
          "cep": "[CEP]",
          "plano_id": "completo",
          "veiculo_texto": "Corolla",
          "data_inicio": "2026-07-24"
        },
        "premio_mensal": 241.38,
        "rascunho": "Pronto — cotação do plano Completo: R$ 241.38/mês (franquia R$ 3000). Cobre: colisao, roubo, furto, terceiros, vidros. Quer que eu detalhe as coberturas ou compare com Essencial ou Premium?",
        "mensagem_agente": "Pronto — cotação do plano Completo: R$ 241.38/mês (franquia R$ 3000). Cobre colisão, roubo, furto, terceiros e danos aos vidros. Quer que eu detalhe as coberturas ou compare com Essencial ou Premium?",
        "fonte_resposta": "llm",
        "index_key": "apresentar_cotacao|meia_30_50",
        "cta": "Quer que eu detalhe as coberturas ou compare com Essencial ou Premium?",
        "conclusao_id": "conclusao:apresentar_cotacao|meia_30_50|completo",
        "aresta": "conclusao:apresentar_cotacao|meia_30_50|completo-[FECHA_COM]->apresentar_cotacao|meia_30_50",
        "model": "qwen2.5:7b",
        "pii": "masked"
      }
    }
  ],
  "eventos": [
    {
      "id": 302,
      "turno": 1,
      "step": "turno",
      "status": "1",
      "detail": {
        "estagio": "qualificando"
      },
      "created_at": "2026-07-24T17:09:02.698321+00:00"
    },
    {
      "id": 303,
      "turno": 1,
      "step": "midia",
      "status": "enriched",
      "detail": {
        "tipo": "image",
        "status": "ok",
        "preview": "PEDIDO DE COTACAO SEGURO AUTO\nidade: 42 anos\n\nveiculo: Corolla 2020\n\nplano: comp",
        "via": "ocr"
      },
      "created_at": "2026-07-24T17:09:02.698321+00:00"
    },
    {
      "id": 304,
      "turno": 1,
      "step": "guardrails",
      "status": "allow",
      "detail": {
        "texto_mascarado": "PEDIDO DE COTACAO SEGURO AUTO\nidade: 42 anos\n\nveiculo: Corolla 2020\n\nplano: completo\n\nCEP: [CEP]",
        "pii_types": [
          "cep"
        ],
        "patterns": []
      },
      "created_at": "2026-07-24T17:09:02.698321+00:00"
    },
    {
      "id": 305,
      "turno": 1,
      "step": "qualifica",
      "status": "ok",
      "detail": {
        "slots_acumulados": {
          "idade": 42,
          "veiculo_ano": 2020,
          "cep": "[CEP]",
          "plano_id": "completo",
          "veiculo_texto": "Corolla"
        }
      },
      "created_at": "2026-07-24T17:09:02.698321+00:00"
    },
    {
      "id": 306,
      "turno": 1,
      "step": "decide",
      "status": "apresentar_cotacao",
      "detail": {
        "faltam": [],
        "premio_mensal": 241.38,
        "escalate": false,
        "exemplos_n": 3,
        "rerank": true
      },
      "created_at": "2026-07-24T17:09:02.698321+00:00"
    },
    {
      "id": 307,
      "turno": 1,
      "step": "resposta",
      "status": "llm",
      "detail": {
        "lead_mascarado": "[imagem] dados.png",
        "rascunho": "Pronto — cotação do plano Completo: R$ 241.38/mês (franquia R$ 3000). Cobre: colisao, roubo, furto, terceiros, vidros. Quer que eu detalhe as coberturas ou compare com Essencial ou Premium?",
        "mensagem": "Pronto — cotação do plano Completo: R$ 241.38/mês (franquia R$ 3000). Cobre colisão, roubo, furto, terceiros e danos aos vidros. Quer que eu detalhe as coberturas ou compare com Essencial ou Premi
```

</details>

## pedido_humano_explicito — Pedido explícito de humano — escala direto

Lead pede atendente ANTES de qualquer dado — não deve virar pausa nem ser ignorado (bug corrigido nesta sessão).

`conversation_id`: `curadoria-pedido_humano_explicito-1784912942`

**Turno 1** — lead: _posso falar com um atendente humano?_

- ação: `escalar_humano` · escalate: `True` · estágio: `escalado` · latência: 0.01s
- **resposta ao lead:** Vou te conectar com um atendente humano pra continuar com segurança. Um atendente humano vai continuar daqui.
- motivos (internos): `['lead pediu explicitamente atendimento humano']`

<details><summary>audit trail (mascarado)</summary>

```json
{
  "conversation_id": "curadoria-pedido_humano_explicito-1784912942",
  "turns": [
    {
      "id": 64,
      "turno": 1,
      "acao": "escalar_humano",
      "escalate": true,
      "premio_mensal": null,
      "fonte_resposta": "template",
      "created_at": "2026-07-24T17:09:02.711752+00:00",
      "audit": {
        "type": "audit.chat",
        "conversation_id": "curadoria-pedido_humano_explicito-1784912942",
        "turno": 1,
        "estagio": "escalado",
        "persona": "desconhecida",
        "lead_mascarado": "posso falar com um atendente humano?",
        "acao": "escalar_humano",
        "escalate": true,
        "motivos": [
          "lead pediu explicitamente atendimento humano"
        ],
        "slots": {},
        "premio_mensal": null,
        "rascunho": "Vou te conectar com um atendente humano pra continuar com segurança. Um atendente humano vai continuar daqui.",
        "mensagem_agente": "Vou te conectar com um atendente humano pra continuar com segurança. Um atendente humano vai continuar daqui.",
        "fonte_resposta": "template",
        "index_key": "escalar_humano",
        "cta": "Um atendente humano vai continuar daqui.",
        "conclusao_id": "conclusao:escalar_humano|desconhecida",
        "aresta": "conclusao:escalar_humano|desconhecida-[FECHA_COM]->escalar_humano",
        "model": null,
        "pii": "masked"
      }
    }
  ],
  "eventos": [
    {
      "id": 308,
      "turno": 1,
      "step": "turno",
      "status": "1",
      "detail": {
        "estagio": "qualificando"
      },
      "created_at": "2026-07-24T17:09:02.711752+00:00"
    },
    {
      "id": 309,
      "turno": 1,
      "step": "guardrails",
      "status": "allow",
      "detail": {
        "texto_mascarado": "posso falar com um atendente humano?",
        "pii_types": [],
        "patterns": []
      },
      "created_at": "2026-07-24T17:09:02.711752+00:00"
    },
    {
      "id": 310,
      "turno": 1,
      "step": "decide",
      "status": "escalar_humano",
      "detail": {
        "escalate": true
      },
      "created_at": "2026-07-24T17:09:02.711752+00:00"
    },
    {
      "id": 311,
      "turno": 1,
      "step": "resposta",
      "status": "template",
      "detail": {
        "lead_mascarado": "posso falar com um atendente humano?",
        "rascunho": "Vou te conectar com um atendente humano pra continuar com segurança. Um atendente humano vai continuar daqui.",
        "mensagem": "Vou te conectar com um atendente humano pra continuar com segurança. Um atendente humano vai continuar daqui.",
        "fonte": "template",
        "index_key": "escalar_humano",
        "cta": "Um atendente humano vai continuar daqui.",
        "conclusao_id": "conclusao:escalar_humano|desconhecida",
        "aresta": "conclusao:escalar_humano|desconhecida-[FECHA_COM]->escalar_humano",
        "model": null,
        "pii": "masked"
      },
      "created_at": "2026-07-24T17:09:02.711752+00:00"
    }
  ]
}
```

</details>

## pausa_respeitosa — Pausa ("vou pensar") — não inventa dúvida

Depois de pedir_dado (falta CEP), lead pede tempo.

`conversation_id`: `curadoria-pausa_respeitosa-1784912942`

**Turno 1** — lead: _tenho 50 anos, Onix 2018, plano completo_

- ação: `pedir_dado` · escalate: `False` · estágio: `qualificando` · latência: 14.69s
- **resposta ao lead:** Pra poder oferecer a melhor proteção para você e sua família, preciso do seu CEP para finalizar o cadastro. Pode me enviar esses dados pra eu cotar?
- motivos (internos): `['Pra cotar seu seguro eu preciso de: seu CEP.']`

**Turno 2** — lead: _vou pensar, depois te falo_

- ação: `adiar_conversa` · escalate: `False` · estágio: `pausado` · latência: 0.02s
- **resposta ao lead:** Sem problema — fica à vontade pra pensar com calma. A cotação fica guardada por aqui. Quando quiser retomar, é só chamar.
- motivos (internos): `['lead pediu tempo para avaliar (pausa) — sem tratar como dúvida específica']`

<details><summary>audit trail (mascarado)</summary>

```json
{
  "conversation_id": "curadoria-pausa_respeitosa-1784912942",
  "turns": [
    {
      "id": 65,
      "turno": 1,
      "acao": "pedir_dado",
      "escalate": false,
      "premio_mensal": null,
      "fonte_resposta": "llm",
      "created_at": "2026-07-24T17:09:17.400968+00:00",
      "audit": {
        "type": "audit.chat",
        "conversation_id": "curadoria-pausa_respeitosa-1784912942",
        "turno": 1,
        "estagio": "qualificando",
        "persona": "meia_30_50",
        "lead_mascarado": "tenho 50 anos, Onix 2018, plano completo",
        "acao": "pedir_dado",
        "escalate": false,
        "motivos": [
          "Pra cotar seu seguro eu preciso de: seu CEP."
        ],
        "slots": {
          "idade": 50,
          "veiculo_ano": 2018,
          "plano_id": "completo",
          "data_inicio": "2026-07-24"
        },
        "premio_mensal": null,
        "rascunho": "Pra cotar seu seguro eu preciso de: seu CEP. Pode me enviar esses dados pra eu cotar?",
        "mensagem_agente": "Pra poder oferecer a melhor proteção para você e sua família, preciso do seu CEP para finalizar o cadastro. Pode me enviar esses dados pra eu cotar?",
        "fonte_resposta": "llm",
        "index_key": "pedir_dado",
        "cta": "Pode me enviar esses dados pra eu cotar?",
        "conclusao_id": "conclusao:pedir_dado|meia_30_50",
        "aresta": "conclusao:pedir_dado|meia_30_50-[FECHA_COM]->pedir_dado",
        "model": "qwen2.5:7b",
        "pii": "masked"
      }
    },
    {
      "id": 66,
      "turno": 2,
      "acao": "adiar_conversa",
      "escalate": false,
      "premio_mensal": null,
      "fonte_resposta": "template",
      "created_at": "2026-07-24T17:09:17.420350+00:00",
      "audit": {
        "type": "audit.chat",
        "conversation_id": "curadoria-pausa_respeitosa-1784912942",
        "turno": 2,
        "estagio": "pausado",
        "persona": "meia_30_50",
        "lead_mascarado": "vou pensar, depois te falo",
        "acao": "adiar_conversa",
        "escalate": false,
        "motivos": [
          "lead pediu tempo para avaliar (pausa) — sem tratar como dúvida específica"
        ],
        "slots": {
          "idade": 50,
          "veiculo_ano": 2018,
          "plano_id": "completo",
          "data_inicio": "2026-07-24"
        },
        "premio_mensal": null,
        "rascunho": "Sem problema — fica à vontade pra pensar com calma. A cotação fica guardada por aqui. Quando quiser retomar, é só chamar.",
        "mensagem_agente": "Sem problema — fica à vontade pra pensar com calma. A cotação fica guardada por aqui. Quando quiser retomar, é só chamar.",
        "fonte_resposta": "template",
        "index_key": "adiar_conversa",
        "cta": "Quando quiser retomar, é só chamar.",
        "conclusao_id": "conclusao:adiar_conversa|meia_30_50",
        "aresta": "conclusao:adiar_conversa|meia_30_50-[FECHA_COM]->adiar_conversa",
        "model": null,
        "pii": "masked"
      }
    }
  ],
  "eventos": [
    {
      "id": 312,
      "turno": 1,
      "step": "turno",
      "status": "1",
      "detail": {
        "estagio": "qualificando"
      },
      "created_at": "2026-07-24T17:09:17.400968+00:00"
    },
    {
      "id": 313,
      "turno": 1,
      "step": "guardrails",
      "status": "allow",
      "detail": {
        "texto_mascarado": "tenho 50 anos, Onix 2018, plano completo",
        "pii_types": [],
        "patterns": []
      },
      "created_at": "2026-07-24T17:09:17.400968+00:00"
    },
    {
      "id": 314,
      "turno": 1,
      "step": "qualifica",
      "status": "ok",
      "detail": {
        "slots_acumulados": {
          "idade": 50,
          "veiculo_ano": 2018,
          "plano_id": "completo"
        }
      },
      "created_at": "2026-07-24T17:09:17.400968+00:00"
    },
    {
      "id": 315,
      "turno": 1,
      "step": "decide",
      "status": "pedir_dado",
      "detail": {
        "faltam": [
          "cep"
        ]
      },
      "c
```

</details>

## fora_de_faixa_recusa — Idade fora de faixa — recusa (não escala)

Regra plans.json: idade > 75 = recusar. Critério local, não é falha de infra.

`conversation_id`: `curadoria-fora_de_faixa_recusa-1784912957`

**Turno 1** — lead: _tenho 80 anos, Civic 2015, plano essencial, cep 30000-000_

- ação: `recusar` · escalate: `False` · estágio: `qualificando` · latência: 18.61s
- **resposta ao lead:** Neste perfil, a cotação não foi possível devido à idade acima do limite de aceitação. Posso te conectar com um especialista para avaliar o caso?
- motivos (internos): `['Idade acima do limite de aceitacao (75 anos).']`

<details><summary>audit trail (mascarado)</summary>

```json
{
  "conversation_id": "curadoria-fora_de_faixa_recusa-1784912957",
  "turns": [
    {
      "id": 67,
      "turno": 1,
      "acao": "recusar",
      "escalate": false,
      "premio_mensal": null,
      "fonte_resposta": "llm",
      "created_at": "2026-07-24T17:09:36.033638+00:00",
      "audit": {
        "type": "audit.chat",
        "conversation_id": "curadoria-fora_de_faixa_recusa-1784912957",
        "turno": 1,
        "estagio": "qualificando",
        "persona": "senior_50+",
        "lead_mascarado": "tenho 80 anos, Civic 2015, plano essencial, cep [CEP]",
        "acao": "recusar",
        "escalate": false,
        "motivos": [
          "Idade acima do limite de aceitacao (75 anos)."
        ],
        "slots": {
          "idade": 80,
          "veiculo_ano": 2015,
          "cep": "[CEP]",
          "plano_id": "essencial",
          "data_inicio": "2026-07-24"
        },
        "premio_mensal": null,
        "rascunho": "Nesse perfil a cotação automática não fecha: Idade acima do limite de aceitacao (75 anos).. Posso te conectar com um especialista pra avaliar o caso?",
        "mensagem_agente": "Neste perfil, a cotação não foi possível devido à idade acima do limite de aceitação. Posso te conectar com um especialista para avaliar o caso?",
        "fonte_resposta": "llm",
        "index_key": "recusar",
        "cta": "Posso te conectar com um especialista pra avaliar o caso?",
        "conclusao_id": "conclusao:recusar|senior_50+",
        "aresta": "conclusao:recusar|senior_50+-[FECHA_COM]->recusar",
        "model": "qwen2.5:7b",
        "pii": "masked"
      }
    }
  ],
  "eventos": [
    {
      "id": 322,
      "turno": 1,
      "step": "turno",
      "status": "1",
      "detail": {
        "estagio": "qualificando"
      },
      "created_at": "2026-07-24T17:09:36.033638+00:00"
    },
    {
      "id": 323,
      "turno": 1,
      "step": "guardrails",
      "status": "allow",
      "detail": {
        "texto_mascarado": "tenho 80 anos, Civic 2015, plano essencial, cep [CEP]",
        "pii_types": [
          "cep"
        ],
        "patterns": []
      },
      "created_at": "2026-07-24T17:09:36.033638+00:00"
    },
    {
      "id": 324,
      "turno": 1,
      "step": "qualifica",
      "status": "ok",
      "detail": {
        "slots_acumulados": {
          "idade": 80,
          "veiculo_ano": 2015,
          "cep": "[CEP]",
          "plano_id": "essencial"
        }
      },
      "created_at": "2026-07-24T17:09:36.033638+00:00"
    },
    {
      "id": 325,
      "turno": 1,
      "step": "decide",
      "status": "recusar",
      "detail": {
        "faltam": [],
        "premio_mensal": null,
        "escalate": false,
        "exemplos_n": 0,
        "rerank": false
      },
      "created_at": "2026-07-24T17:09:36.033638+00:00"
    },
    {
      "id": 326,
      "turno": 1,
      "step": "resposta",
      "status": "llm",
      "detail": {
        "lead_mascarado": "tenho 80 anos, Civic 2015, plano essencial, cep [CEP]",
        "rascunho": "Nesse perfil a cotação automática não fecha: Idade acima do limite de aceitacao (75 anos).. Posso te conectar com um especialista pra avaliar o caso?",
        "mensagem": "Neste perfil, a cotação não foi possível devido à idade acima do limite de aceitação. Posso te conectar com um especialista para avaliar o caso?",
        "fonte": "llm",
        "index_key": "recusar",
        "cta": "Posso te conectar com um especialista pra avaliar o caso?",
        "conclusao_id": "conclusao:recusar|senior_50+",
        "aresta": "conclusao:recusar|senior_50+-[FECHA_COM]->recusar",
        "model": "qwen2.5:7b",
        "pii": "masked"
      },
      "created_at": "2026-07-24T17:09:36.033638+00:00"
    }
  ]
}
```

</details>

## pii_mascarada — PII no texto — mascarada no audit

CPF explícito na mensagem; slots reais seguem pra cotar, mas o audit/log precisa mascarar.

`conversation_id`: `curadoria-pii_mascarada-1784912976`

**Turno 1** — lead: _tenho 33 anos, Fiat Argo 2021, plano essencial, cep 01310-100, meu cpf é 123.456.789-09_

- ação: `apresentar_cotacao` · escalate: `False` · estágio: `cotado` · latência: 27.29s
- **resposta ao lead:** Pronto — cotação do plano Essencial: R$ 119,9/mês (franquia R$ 4500). Cobre colisão, roubo e furto. Quer que eu detalhe as coberturas ou compare com Completo ou Premium?

<details><summary>audit trail (mascarado)</summary>

```json
{
  "conversation_id": "curadoria-pii_mascarada-1784912976",
  "turns": [
    {
      "id": 68,
      "turno": 1,
      "acao": "apresentar_cotacao",
      "escalate": false,
      "premio_mensal": 119.9,
      "fonte_resposta": "llm",
      "created_at": "2026-07-24T17:10:03.324730+00:00",
      "audit": {
        "type": "audit.chat",
        "conversation_id": "curadoria-pii_mascarada-1784912976",
        "turno": 1,
        "estagio": "cotado",
        "persona": "meia_30_50",
        "lead_mascarado": "tenho 33 anos, Fiat Argo 2021, plano essencial, cep [CEP], meu cpf é [CPF]",
        "acao": "apresentar_cotacao",
        "escalate": false,
        "motivos": [],
        "slots": {
          "idade": 33,
          "veiculo_ano": 2021,
          "cep": "[CEP]",
          "plano_id": "essencial",
          "veiculo_texto": "Fiat Argo",
          "data_inicio": "2026-07-24"
        },
        "premio_mensal": 119.9,
        "rascunho": "Pronto — cotação do plano Essencial: R$ 119.9/mês (franquia R$ 4500). Cobre: colisao, roubo, furto. Quer que eu detalhe as coberturas ou compare com Completo ou Premium?",
        "mensagem_agente": "Pronto — cotação do plano Essencial: R$ 119,9/mês (franquia R$ 4500). Cobre colisão, roubo e furto. Quer que eu detalhe as coberturas ou compare com Completo ou Premium?",
        "fonte_resposta": "llm",
        "index_key": "apresentar_cotacao|meia_30_50",
        "cta": "Quer que eu detalhe as coberturas ou compare com Completo ou Premium?",
        "conclusao_id": "conclusao:apresentar_cotacao|meia_30_50|essencial",
        "aresta": "conclusao:apresentar_cotacao|meia_30_50|essencial-[FECHA_COM]->apresentar_cotacao|meia_30_50",
        "model": "qwen2.5:7b",
        "pii": "masked"
      }
    }
  ],
  "eventos": [
    {
      "id": 327,
      "turno": 1,
      "step": "turno",
      "status": "1",
      "detail": {
        "estagio": "qualificando"
      },
      "created_at": "2026-07-24T17:10:03.324730+00:00"
    },
    {
      "id": 328,
      "turno": 1,
      "step": "guardrails",
      "status": "allow",
      "detail": {
        "texto_mascarado": "tenho 33 anos, Fiat Argo 2021, plano essencial, cep [CEP], meu cpf é [CPF]",
        "pii_types": [
          "cpf",
          "cep"
        ],
        "patterns": []
      },
      "created_at": "2026-07-24T17:10:03.324730+00:00"
    },
    {
      "id": 329,
      "turno": 1,
      "step": "qualifica",
      "status": "ok",
      "detail": {
        "slots_acumulados": {
          "idade": 33,
          "veiculo_ano": 2021,
          "cep": "[CEP]",
          "plano_id": "essencial",
          "veiculo_texto": "Fiat Argo"
        }
      },
      "created_at": "2026-07-24T17:10:03.324730+00:00"
    },
    {
      "id": 330,
      "turno": 1,
      "step": "decide",
      "status": "apresentar_cotacao",
      "detail": {
        "faltam": [],
        "premio_mensal": 119.9,
        "escalate": false,
        "exemplos_n": 3,
        "rerank": true
      },
      "created_at": "2026-07-24T17:10:03.324730+00:00"
    },
    {
      "id": 331,
      "turno": 1,
      "step": "resposta",
      "status": "llm",
      "detail": {
        "lead_mascarado": "tenho 33 anos, Fiat Argo 2021, plano essencial, cep [CEP], meu cpf é [CPF]",
        "rascunho": "Pronto — cotação do plano Essencial: R$ 119.9/mês (franquia R$ 4500). Cobre: colisao, roubo, furto. Quer que eu detalhe as coberturas ou compare com Completo ou Premium?",
        "mensagem": "Pronto — cotação do plano Essencial: R$ 119,9/mês (franquia R$ 4500). Cobre colisão, roubo e furto. Quer que eu detalhe as coberturas ou compare com Completo ou Premium?",
        "fonte": "llm",
        "index_key": "apresentar_cotacao|meia_30_50",
        "cta": "Quer que eu detalhe as coberturas ou compare com Completo ou Premium?",
        "conclusao_id": "conclusao:apresentar_cotacao|meia_30_50|essencial",
        "aresta": "conclusao:apresentar_cotacao|meia_30_50|essencial-[FECHA_COM]->apresentar_cotac
```

</details>
