"""Índice de fechamento parametrizado + validação anti-CTA sem nexo."""
from __future__ import annotations

from orch_svc.cotacao_flow import DecisaoCotacao
from orch_svc.fechamento_index import lookup_fechamento, validar_fechamento_llm
from orch_svc.resposta import redigir_resposta


def test_indice_cotacao_tem_premio_e_cta_comparar():
    d = DecisaoCotacao(
        "apresentar_cotacao",
        quote={
            "plano_nome": "Completo",
            "plano_id": "completo",
            "premio_mensal": 209.9,
            "franquia": 3000,
            "coberturas": ["colisao", "roubo", "furto", "terceiros", "vidros"],
        },
    )
    spec, texto, params = lookup_fechamento(d, idade=42)
    assert spec.key == "apresentar_cotacao|meia_30_50"
    assert "209,90" in texto
    assert "Completo" in texto
    assert "compare" in texto.lower() or "compar" in texto.lower()
    assert "Essencial" in texto and "Premium" in texto
    # não relista o plano já cotado na CTA de comparação
    assert "compare com Completo" not in texto
    assert "Essencial / Completo / Premium" not in texto
    assert "ajustar o plano agora" not in texto.lower()
    assert params["premio"] == "209,90"


def test_cta_omite_plano_cotado_essencial():
    from orch_svc.fechamento_index import cta_cotacao

    assert cta_cotacao(plano_id="essencial") == (
        "Quer que eu detalhe as coberturas ou compare com Completo ou Premium?"
    )
    assert "Essencial" not in cta_cotacao(plano_id="essencial").split("compare")[1]
    assert cta_cotacao(plano_id="premium") == (
        "Quer que eu detalhe as coberturas ou compare com Essencial ou Completo?"
    )


def test_valida_rejeita_cta_sem_nexo():
    d = DecisaoCotacao(
        "apresentar_cotacao",
        quote={"plano_nome": "Completo", "premio_mensal": 209.9, "franquia": 3000},
    )
    spec, _, params = lookup_fechamento(d, idade=42)
    ruim = (
        "Pronto — Plano Completo cobre colisão. "
        "Como podemos ajustar o plano agora?"
    )
    assert not validar_fechamento_llm(ruim, spec=spec, params=params)


def test_valida_rejeita_sem_premio():
    d = DecisaoCotacao(
        "apresentar_cotacao",
        quote={"plano_nome": "Completo", "premio_mensal": 209.9, "franquia": 3000},
    )
    spec, _, params = lookup_fechamento(d, idade=42)
    sem_preco = "Plano Completo é ótimo para sua família. Quer detalhar coberturas?"
    assert not validar_fechamento_llm(sem_preco, spec=spec, params=params)


def test_llm_ruim_cai_no_indice():
    class Fake:
        def chat(self, messages, trace: str) -> str:
            return "Ideal para proteger sua família. Como podemos ajustar o plano agora?"

    d = DecisaoCotacao(
        "apresentar_cotacao",
        quote={"plano_nome": "Completo", "premio_mensal": 209.9, "franquia": 3000},
    )
    red = redigir_resposta(d, idade=42, inference=Fake(), mensagem_lead="quero completo")
    assert red.fonte == "llm_fallback"
    assert "209,90" in red.texto
    assert "ajustar o plano agora" not in red.texto.lower()
    assert red.index_key.startswith("apresentar_cotacao")


def test_llm_bom_mantem_premio():
    class Fake:
        def chat(self, messages, trace: str) -> str:
            return (
                "Pronto — Completo por R$ 209,90/mês (franquia R$ 3000). "
                "Quer que eu detalhe as coberturas ou compare com Essencial ou Premium?"
            )

    d = DecisaoCotacao(
        "apresentar_cotacao",
        quote={
            "plano_id": "completo",
            "plano_nome": "Completo",
            "premio_mensal": 209.9,
            "franquia": 3000,
        },
    )
    red = redigir_resposta(d, idade=42, inference=Fake())
    assert red.fonte == "llm"
    assert "209" in red.texto


def test_llm_relista_plano_atual_cai_fallback():
    class Fake:
        def chat(self, messages, trace: str) -> str:
            return (
                "Essencial por R$ 191.84/mês. "
                "Quer comparar com Essencial / Completo / Premium?"
            )

    d = DecisaoCotacao(
        "apresentar_cotacao",
        quote={
            "plano_id": "essencial",
            "plano_nome": "Essencial",
            "premio_mensal": 191.84,
            "franquia": 4500,
        },
    )
    red = redigir_resposta(d, idade=22, inference=Fake())
    assert red.fonte == "llm_fallback"
    assert "Completo ou Premium" in red.texto
    assert "compare com Essencial" not in red.texto
