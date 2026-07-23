"""Aceite pós-cotação + emitir apólice (padrão dataset ganho)."""
from __future__ import annotations

from orch_svc.aceitacao import detectar_aceite_cotacao
from orch_svc.cotacao_flow import DecisaoCotacao
from orch_svc.fechamento_index import resolver_fechamento
from orch_svc.thread import ThreadState, run_turno


class _FakeQuote:
    def quote(self, body, trace="-"):
        from orch_svc.quote_client import QuoteOutcome, QuoteStatus

        return QuoteOutcome(
            QuoteStatus.QUOTED,
            quote={
                "plano_id": body.get("plano_id", "essencial"),
                "plano_nome": "Essencial",
                "premio_mensal": 137.88,
                "franquia": 4500,
                "coberturas": ["colisao", "roubo", "furto"],
            },
        )


def _build(slots):
    class R:
        ok = True
        missing = []
        refusals = []
        errors = []
        payload = type("P", (), {
            "plano_id": slots.get("plano_id"),
            "idade": slots.get("idade"),
            "veiculo_ano": slots.get("veiculo_ano"),
            "cep": slots.get("cep"),
            "data_inicio": slots.get("data_inicio"),
            "model_dump": lambda self, **k: {
                "plano_id": slots.get("plano_id"),
                "idade": slots.get("idade"),
                "veiculo_ano": slots.get("veiculo_ano"),
                "cep": slots.get("cep"),
                "data_inicio": slots.get("data_inicio"),
            },
        })()
    # simplify - use real build if available
    from seguro_auto.build import build_quote_request
    return build_quote_request(slots, verified=True)


def test_detectar_aceite():
    assert detectar_aceite_cotacao("fechado!")
    assert detectar_aceite_cotacao("pode emitir entao")
    assert detectar_aceite_cotacao("vamos nessa, gostei")
    assert detectar_aceite_cotacao("vou contratar")  # caso UI real
    assert detectar_aceite_cotacao("quero contratar")
    assert detectar_aceite_cotacao("Aprovo a proposta")
    assert detectar_aceite_cotacao("manda o boleto")
    assert not detectar_aceite_cotacao("quanto fica o premium?")
    assert not detectar_aceite_cotacao("detalha as coberturas")


def test_emitir_apolice_apos_cotacao():
    st = ThreadState("t-aceite")
    ex1, st = run_turno(
        "tenho 35 anos corolla 2020 cep 01310-100 plano essencial",
        st,
        _build,
        _FakeQuote(),
    )
    assert ex1.decisao.acao == "apresentar_cotacao"
    assert st.estagio == "cotado"
    assert st.encerrado is False
    assert st.ultima_quote

    ex2, st = run_turno("fechado!", st, _build, _FakeQuote())
    assert ex2.decisao.acao == "emitir_apolice"
    assert st.estagio == "contratado"
    assert st.encerrado is True

    red = resolver_fechamento(ex2.decisao, idade=35)
    assert "apólice" in red.texto.lower() or "apolice" in red.texto.lower()
    assert "boleto" in red.texto.lower()
    assert "137.88" in red.texto


def test_emitir_apolice_vou_contratar():
    """Regressão: 'vou contratar' (sem 'quero') também fecha."""
    st = ThreadState("t-vou-contratar")
    st.estagio = "cotado"
    st.ultima_quote = {
        "plano_id": "essencial",
        "plano_nome": "Essencial",
        "premio_mensal": 137.88,
        "franquia": 4500,
        "coberturas": ["colisao"],
    }
    st.slots = {
        "idade": 35,
        "veiculo_ano": 2020,
        "cep": "01310100",
        "plano_id": "essencial",
        "data_inicio": "2026-07-23",
    }
    ex, st = run_turno("vou contratar", st, _build, _FakeQuote())
    assert ex.decisao.acao == "emitir_apolice"
    assert st.estagio == "contratado"


def test_ciclo_completo_apos_contratado_nao_reabre():
    st = ThreadState("t-ciclo-fim")
    st.slots = {
        "idade": 35,
        "veiculo_ano": 2020,
        "cep": "01310100",
        "plano_id": "essencial",
        "data_inicio": "2026-07-23",
    }
    ex1, st = run_turno("pode cotar", st, _build, _FakeQuote())
    assert ex1.decisao.acao == "apresentar_cotacao"
    ex2, st = run_turno("fechado!", st, _build, _FakeQuote())
    assert st.estagio == "contratado" and st.encerrado
    ex3, st = run_turno("e agora?", st, _build, _FakeQuote())
    assert ex3.decisao.acao == "emitir_apolice"
    assert st.estagio == "contratado"
