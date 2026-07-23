"""Demo: roda conversas de ponta a ponta e gera docs/log-execucao.md.

Liga o porteiro REAL (domains/seguro_auto) ao agente + cliente resiliente (aqui
com desfechos simulados, para demonstrar os 3 caminhos sem subir o quote-service).
Executa: python scripts/demo_execucao.py
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "domains"))
sys.path.insert(0, str(ROOT / "services/svc-orchestrator/src"))

from seguro_auto.build import build_quote_request  # noqa: E402
from orch_svc.agente_cotacao import render_log, run_conversa  # noqa: E402
from orch_svc.quote_client import QuoteOutcome, QuoteStatus  # noqa: E402


class QuoteSimulado:
    def __init__(self, outcome):
        self.outcome = outcome

    def quote(self, body, trace):
        return self.outcome


def build_fn(slots):
    return build_quote_request(slots, verified=True)


CENARIOS = [
    ("caminho_feliz",
     ["Oi! Tenho 35 anos", "quero seguro pro meu Corolla 2020", "meu CPF é 123.456.789-00, cep 01310-100"],
     QuoteSimulado(QuoteOutcome(QuoteStatus.QUOTED,
                                quote={"plano_nome": "Essencial", "premio_mensal": 142.90}))),
    ("quote_instavel_escala",
     ["tenho 40 anos, dirijo um Onix 2019, cep 20040-002"],
     QuoteSimulado(QuoteOutcome(QuoteStatus.UNAVAILABLE,
                                reason="esgotou 3 tentativas (última: 503)", escalate=True))),
    ("falta_dado",
     ["boa tarde, queria cotar um seguro de carro"],
     QuoteSimulado(QuoteOutcome(QuoteStatus.QUOTED))),   # porteiro barra por dados faltantes
]


def main():
    execs = [run_conversa(msgs, build_fn, fq, conversation_id=nome)
             for nome, msgs, fq in CENARIOS]
    log = render_log(execs)
    out = ROOT / "docs" / "log-execucao.md"
    out.write_text(log, encoding="utf-8")
    print(log)
    print(f"\n>> log salvo em {out}")


if __name__ == "__main__":
    main()
