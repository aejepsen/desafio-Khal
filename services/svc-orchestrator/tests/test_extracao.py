"""Testes da extração heurística + LLM (degradação graciosa)."""
from __future__ import annotations

import json

from orch_svc.extracao import extrair_slots, fazer_extrator


class _FakeLlm:
    def __init__(self, payload: dict | str, fail: bool = False) -> None:
        self.payload = payload
        self.fail = fail
        self.calls = 0

    def chat(self, messages, trace: str) -> str:
        self.calls += 1
        if self.fail:
            raise RuntimeError("inference down")
        if isinstance(self.payload, str):
            return self.payload
        return json.dumps(self.payload, ensure_ascii=False)


def test_so_heuristica_sem_llm():
    s = extrair_slots("tenho 35 anos, Corolla 2020, plano completo, cep 01310-100")
    assert s["idade"] == 35
    assert s["veiculo_ano"] == 2020
    assert s["plano_id"] == "completo"
    assert "01310" in s["cep"]


def test_llm_enriquece_veiculo_e_plano():
    fake = _FakeLlm({
        "idade": 42,
        "veiculo_ano": 2019,
        "plano_id": "premium",
        "veiculo_texto": "Civic prata",
    })
    s = extrair_slots("quero o top, meu Civic prata de 2019, tenho 42 anos", fake)
    assert fake.calls == 1
    assert s["plano_id"] == "premium"
    assert s["veiculo_ano"] == 2019
    assert s["idade"] == 42
    assert "Civic" in s["veiculo_texto"]


def test_llm_alucinacao_descartada():
    fake = _FakeLlm({
        "plano_id": "completo",
        "cep": "01310-100",
        "veiculo_texto": "Fusca 1968",
        "data_inicio": "2023-05-01",
        "idade": 42,
        "veiculo_ano": 1968,
    })
    s = extrair_slots("Oi, quero cotar seguro do meu carro", fake)
    assert s == {}


def test_llm_falha_cai_na_heuristica():
    fake = _FakeLlm({}, fail=True)
    s = extrair_slots("tenho 30 anos carro 2021 essencial", fake)
    assert s["idade"] == 30
    assert s["veiculo_ano"] == 2021
    assert s["plano_id"] == "essencial"


def test_llm_lixo_nao_quebra():
    fake = _FakeLlm("desculpe, não entendi")
    s = extrair_slots("idade 28 anos veiculo 2022", fake)
    assert s["idade"] == 28
    assert s["veiculo_ano"] == 2022


def test_fazer_extrator_callable():
    fake = _FakeLlm({"plano_id": "completo", "idade": 33, "veiculo_ano": 2018})
    fn = fazer_extrator(fake)
    s = fn("quero o intermediário, 33 anos, ano 2018")
    assert s["plano_id"] == "completo"
    assert s["idade"] == 33
