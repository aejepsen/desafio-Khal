# Domínio determinístico seguro auto

Monta `QuoteRequest` sem LLM.

```python
from domains.seguro_auto import LeadSlots, build_quote_request

result = build_quote_request(
    LeadSlots(idade=35, veiculo_ano=2020, plano_id="essencial", cep="01310-100"),
    verified=True,
)
if result.ok:
    body = result.payload.to_dict()  # POST /quote
```

Fonte de regras: `quote-service/data/plans.json`. Não calcula prêmio.

## Testes + XML

```bash
python -m pytest domains/seguro_auto/tests/ -v
```

Matriz mockada grava `domains/seguro_auto/evals/results/domain_quote_cases.xml`:

- **input:** slots + metadados de `planos.json` (faixa etária, idade veículo, CEP risco…)
- **output:** campos do JSON de `POST /quote` (+ ok/missing/errors/refusals)
