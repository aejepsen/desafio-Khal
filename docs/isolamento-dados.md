# Isolamento de dados — reuso limpo dos microsserviços

> Princípio: **reuso a plataforma, não o passado dela.** Os microsserviços
> (`svc-*`) são reusados pelo CÓDIGO; cada um sobe no desafio com **estado do zero**.

## Por que (4 razões)
1. **Relevância** — svc-rag com embeddings de outros domínios recuperaria docs de
   spec/código no meio de uma conversa de seguro. Contamina o retrieval.
2. **Privacidade / vazamento** — o repo **vira público na entrega**. Dado residual de
   outro projeto (golden sets, traces, PII de outros contextos) seria exposto.
3. **Reprodutibilidade** — o desafio é autocontido: `docker compose up` + ingestão
   popula tudo do dataset do desafio, sem depender de estado pré-existente.
4. **Segurança** — não trazer dados de fora que não deveriam sair dos outros projetos.

## O que zerar, por serviço
| Serviço | Estado | Política no desafio |
|---|---|---|
| **svc-rag** | coleção Qdrant + embeddings | coleção **nova** `namastex_conversas`, volume limpo, populada só do `conversations.parquet` |
| **svc-router** | golden set de roteamento | do domínio do desafio (etapas do lead) ou vazio; não o do AI-Orchestrator |
| **svc-guardrails** | listas/config PII+injection | config **própria** (regex CPF/placa/CNH/CEP br) |
| **svc-observability** | traces / métricas | começa vazio; telemetria só deste sistema |
| **svc-inference** | serving (stateless) | ok; conferir cache/config; provider plugável |
| **svc-orchestrator** | configs de rota/prompt | próprias do fluxo de cotação |
| **svc-evals** | dataset de avaliação | o do desafio (offline/opcional) |

## Como garantir (checklist)
- [ ] **Vendoring sem estado** — copiar código dos `svc-*`, excluir `.venv/`,
      `__pycache__/`, `.pytest_cache/`, volumes, `.env` real, dumps de dados.
- [ ] **Volumes/DBs novos** no docker-compose do desafio (não montar volumes de
      outros projetos).
- [ ] **Namespaces próprios** — coleções/índices com prefixo `namastex_`.
- [ ] **.env próprio** — chaves e configs do desafio; nunca herdar.
- [ ] **Pipeline de ingestão dedicado** — script que popula svc-rag só do dataset.
- [ ] **Verificação pré-subida** — confirmar volumes vazios / coleções ausentes.
- [ ] **`.gitignore`** — `*.parquet`, `dataset/`, `data/`, `.env` fora do repo.

## Fronteira
Reuso = **código + contratos + lógica**. Isolamento = **dados + estado + segredos**.
O primeiro atravessa projetos; o segundo, nunca.
