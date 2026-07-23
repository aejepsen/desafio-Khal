# Log de execução — agente de cotação

## `caminho_feliz` → **apresentar_cotacao**

| # | passo | status | detalhe |
|---|---|---|---|
| 0 | ingest | ok | n_mensagens=3 |
| 1 | guardrails | ok | texto_mascarado=Oi! Tenho 35 anos quero seguro pro meu Corolla 2020 meu CPF é [CPF], cep [CEP] |
| 2 | qualifica | ok | slots={'idade': 35, 'veiculo_ano': 2020, 'cep': '01310-100'} |
| 3 | porteiro | ok |  |
| 4 | decide | apresentar_cotacao | escalate=False, premio_mensal=142.9 |

## `quote_instavel_escala` → **escalar_humano**  ⚠️ escala humano

| # | passo | status | detalhe |
|---|---|---|---|
| 0 | ingest | ok | n_mensagens=1 |
| 1 | guardrails | ok | texto_mascarado=tenho 40 anos, dirijo um Onix 2019, cep [CEP] |
| 2 | qualifica | ok | slots={'idade': 40, 'veiculo_ano': 2019, 'cep': '20040-002'} |
| 3 | porteiro | ok |  |
| 4 | decide | escalar_humano | escalate=True, motivos=['esgotou 3 tentativas (última: 503)'] |

## `falta_dado` → **pedir_dado**

| # | passo | status | detalhe |
|---|---|---|---|
| 0 | ingest | ok | n_mensagens=1 |
| 1 | guardrails | ok | texto_mascarado=boa tarde, queria cotar um seguro de carro |
| 2 | qualifica | vazio |  |
| 3 | porteiro | ok | missing=['idade', 'veiculo_ano'] |
| 4 | decide | pedir_dado | escalate=False, faltam=['idade', 'veiculo_ano'] |

## `objecao_preco_reverte` → **reverter_objecao**

| # | passo | status | detalhe |
|---|---|---|---|
| 0 | ingest | ok | n_mensagens=2 |
| 1 | guardrails | ok | texto_mascarado=tenho 30 anos, Corolla 2020, cep [CEP] mas achei muito caro, tem desconto? |
| 2 | qualifica | ok | slots={'idade': 30, 'veiculo_ano': 2020, 'cep': '01310-100'} |
| 3 | objecao | reverter | objecao=preco, framework=feel-felt-found + ancoragem-valor, tatica=Reconhecer e reancorar: 'entendo — à primei |
| 4 | decide | reverter_objecao | tatica=Reconhecer e reancorar: 'entendo — à primeira vista parece; olhando a cobertura por dia, é proteção do  |
