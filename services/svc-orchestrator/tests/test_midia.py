"""HITL: mídia sem transcrição → escalar_humano; plug ASR/OCR opcional."""
from __future__ import annotations

from orch_svc.midia import FakeMediaEnricher, detectar_midia_sem_transcricao
from orch_svc.quote_client import QuoteOutcome, QuoteStatus
from orch_svc.thread import ThreadState, run_turno


class _Q:
    def quote(self, body, trace):
        return QuoteOutcome(QuoteStatus.QUOTED, quote={"premio_mensal": 1})


def _build(slots):
    from types import SimpleNamespace
    missing = [c for c in ("idade", "veiculo_ano", "cep", "plano_id") if not slots.get(c)]
    return SimpleNamespace(
        payload=None if missing else slots,
        missing=missing, errors=[], refusals=[],
    )


def test_detect_documento_placeholder():
    assert detectar_midia_sem_transcricao("[documento] CNH_frente.pdf") == "document"


def test_detect_audio_type():
    assert detectar_midia_sem_transcricao("", message_type="audio") == "audio"


def test_legenda_util_nao_escala():
    assert detectar_midia_sem_transcricao(
        "[imagem] tenho 35 anos Corolla 2020 plano essencial cep 01310100"
    ) is None


def test_run_turno_midia_escala():
    st = ThreadState("m1")
    ex, st2 = run_turno("[documento] CNH_frente.pdf", st, _build, _Q())
    assert ex.decisao.acao == "escalar_humano"
    assert ex.decisao.escalate
    assert "mídia sem transcrição" in ex.decisao.motivos
    assert st2.encerrado
    assert any(e.step == "midia" for e in ex.eventos)


def test_run_turno_message_type_audio():
    st = ThreadState("m2")
    ex, _ = run_turno("...", st, _build, _Q(), message_type="audio")
    assert ex.decisao.acao == "escalar_humano"
    assert ex.decisao.motivos == ["mídia sem transcrição"]


def test_enricher_converte_midia_em_texto():
    st = ThreadState("m3")
    fake = FakeMediaEnricher()
    ex, st2 = run_turno(
        "[documento] CNH_frente.pdf",
        st,
        _build,
        _Q(),
        message_type="document",
        media_url="http://files/cnh.pdf",
        media_enricher=fake,
        extrair=lambda t: {
            "idade": 35, "veiculo_ano": 2020, "plano_id": "essencial", "cep": "01310-100",
        },
    )
    assert fake.calls
    assert any(e.step == "midia" and e.status == "enriched" for e in ex.eventos)
    assert ex.decisao.acao == "apresentar_cotacao"


def test_enricher_falha_cai_em_hitl():
    st = ThreadState("m4")
    fake = FakeMediaEnricher(text=None)
    ex, _ = run_turno(
        "[áudio]",
        st,
        _build,
        _Q(),
        message_type="audio",
        media_url="http://files/a.ogg",
        media_enricher=fake,
    )
    assert ex.decisao.acao == "escalar_humano"
    assert "mídia sem transcrição" in ex.decisao.motivos
