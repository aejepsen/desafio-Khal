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
    # 3º turno: CEP → cota (aguarda aceite; não encerra ainda)
    ex, st = run_turno("CEP 01310-100", st, _build, FakeQuote())
    assert ex.decisao.acao == "apresentar_cotacao"
    assert st.slots.get("cep") and st.slots.get("data_inicio")
    assert st.estagio == "cotado" and st.encerrado is False


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


def test_vou_pensar_adia_sem_inventar_duvida():
    st = ThreadState(
        "pausa",
        estagio="cotado",
        slots={
            "idade": 35,
            "veiculo_ano": 2020,
            "cep": "01310100",
            "plano_id": "essencial",
            "data_inicio": "2026-07-23",
        },
        ultima_quote={"plano_nome": "Essencial", "premio_mensal": 137.88},
    )
    ex, st = run_turno("vou pensar. depois te falo", st, _build, FakeQuote())
    assert ex.decisao.acao == "adiar_conversa"
    assert st.estagio == "pausado"
    assert st.encerrado is False
    from orch_svc.fechamento_index import resolver_fechamento
    from orch_svc.resposta import redigir_resposta

    red = redigir_resposta(ex.decisao, idade=35, mensagem_lead="vou pensar. depois te falo")
    assert red.fonte == "template"
    low = red.texto.lower()
    assert "dúvida" not in low and "duvida" not in low
    assert "pensar" in low or "quando quiser" in low
    assert "cotação" in low or "cotacao" in low


def test_pedir_faltantes_amigavel():
    msg = pedir_faltantes(["idade", "cep"])
    assert "idade" in msg and "CEP" in msg


def test_limite_turnos_escala():
    st = ThreadState("c3", turnos=8, slots={"idade": 30})
    ex, st = run_turno("oi", st, _build, FakeQuote())
    assert ex.decisao.acao == "escalar_humano" and st.encerrado


def test_pedido_humano_escala_direto():
    # Pedido explícito de humano tem prioridade sobre objeção/qualificação.
    st = ThreadState("ph1")
    ex, st = run_turno("posso falar com o atendente humano?", st, _build, FakeQuote())
    assert ex.decisao.acao == "escalar_humano"
    assert ex.decisao.escalate is True
    assert st.encerrado is True and st.estagio == "escalado"


def test_pergunta_preco_antes_de_cotar_nao_e_objecao():
    # Pergunta neutra de preço (sem cotação ainda) não deve virar tática de
    # reversão de objeção — deve seguir o fluxo normal de qualificação.
    st = ThreadState("preq1")
    ex, st = run_turno(
        "quero saber o preço do plano completo antes de decidir",
        st, _build, FakeQuote(),
    )
    assert ex.decisao.acao != "reverter_objecao"
    assert st.tentativas_objecao == {}


def test_azul_veiculo_nao_e_confundido_com_concorrente():
    # Cor do carro ("azul") não deve sequestrar a 1ª mensagem de qualificação
    # pro fluxo de objeção de concorrente (bug: regex "azul" sem contexto).
    st = ThreadState("qual1")
    ex, st = run_turno(
        "tenho 35 anos, Fiat Uno azul 2020, cep 01310-100, plano completo",
        st, _build, FakeQuote(),
    )
    assert ex.decisao.acao != "reverter_objecao"
    assert st.slots.get("idade") == 35 and st.slots.get("veiculo_ano") == 2020
