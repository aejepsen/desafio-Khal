"""Testes da conversa multi-turno com estado (thread)."""
from types import SimpleNamespace

from orch_svc.quote_client import QuoteOutcome, QuoteStatus
from orch_svc.thread import ThreadState, pedir_faltantes, run_turno


def _build(slots):
    missing = [c for c in ("idade", "veiculo_ano", "cep") if c not in slots]
    return SimpleNamespace(payload=slots if not missing else None,
                           missing=missing, errors=[], refusals=[])


class FakeQuote:
    def quote(self, body, trace):
        return QuoteOutcome(QuoteStatus.QUOTED, quote={"premio_mensal": 100})


def test_acumula_slots_entre_turnos():
    st = ThreadState("c1")
    ex, st = run_turno("tenho 30 anos", st, _build, FakeQuote())
    # coleta ativa: pede veículo, plano e CEP
    assert ex.decisao.acao == "pedir_dado"
    assert "veiculo_ano" in ex.decisao.faltam and "plano_id" in ex.decisao.faltam
    assert "cep" in ex.decisao.faltam
    assert st.slots["idade"] == 30 and st.turnos == 1
    # 2º turno: veículo + plano — ainda falta CEP
    ex, st = run_turno("é um Corolla 2020, quero o completo", st, _build, FakeQuote())
    assert ex.decisao.acao == "pedir_dado"
    assert ex.decisao.faltam == ["cep"]
    assert st.slots["veiculo_ano"] == 2020 and st.slots["plano_id"] == "completo"
    # 3º turno: CEP → cota
    ex, st = run_turno("CEP 01310-100", st, _build, FakeQuote())
    assert ex.decisao.acao == "apresentar_cotacao"
    assert st.slots.get("cep") and st.slots.get("data_inicio") and st.encerrado


def test_coleta_ativa_plano_nao_cota_sem_plano():
    st = ThreadState("cp", slots={"idade": 30, "veiculo_ano": 2020, "cep": "01310-100"})
    ex, st = run_turno("qual o valor?", st, _build, FakeQuote())
    assert ex.decisao.acao == "pedir_dado" and "plano_id" in ex.decisao.faltam


def test_nao_cota_sem_cep():
    st = ThreadState("nc", slots={
        "idade": 30, "veiculo_ano": 2020, "plano_id": "essencial",
    })
    ex, st = run_turno("pode cotar", st, _build, FakeQuote())
    assert ex.decisao.acao == "pedir_dado" and "cep" in ex.decisao.faltam


def test_objecao_persistida_entre_turnos():
    st = ThreadState("c2", slots={"idade": 40, "veiculo_ano": 2019})
    ex, st = run_turno("achei caro", st, _build, FakeQuote())
    assert ex.decisao.acao == "reverter_objecao" and st.tentativas_objecao["preco"] == 1
    ex, st = run_turno("ainda tá caro", st, _build, FakeQuote())
    assert st.tentativas_objecao["preco"] == 2
    ex, st = run_turno("caro demais", st, _build, FakeQuote())
    ex, st = run_turno("muito caro mesmo", st, _build, FakeQuote())
    assert ex.decisao.acao == "escalar_humano" and st.encerrado


def test_pedir_faltantes_amigavel():
    msg = pedir_faltantes(["idade", "cep"])
    assert "idade" in msg and "CEP" in msg


def test_limite_turnos_escala():
    st = ThreadState("c3", turnos=8, slots={"idade": 30})
    ex, st = run_turno("oi", st, _build, FakeQuote())
    assert ex.decisao.acao == "escalar_humano" and st.encerrado
