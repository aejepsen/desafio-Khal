from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from domains.seguro_auto import LeadSlots, build_quote_request  # noqa: E402
from domains.seguro_auto.plans import clear_plans_cache, default_plans_path  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_plans_cache()
    yield
    clear_plans_cache()


def test_plans_path_exists():
    assert default_plans_path().is_file()


def test_happy_path_builds_quote_json():
    r = build_quote_request(
        LeadSlots(
            idade=35,
            veiculo_ano=2020,
            plano_id="essencial",
            cep="01310100",
            data_inicio="2026-07-22",
        ),
        verified=True,
        today=date(2026, 7, 22),
    )
    assert r.ok
    assert r.payload is not None
    assert r.payload.to_dict() == {
        "plano_id": "essencial",
        "idade": 35,
        "veiculo_ano": 2020,
        "cep": "01310-100",
        "data_inicio": "2026-07-22",
    }


def test_requires_verification_gate():
    r = build_quote_request(
        LeadSlots(idade=35, veiculo_ano=2020),
        verified=False,
    )
    assert not r.ok
    assert "dados_nao_verificados" in r.errors


def test_missing_required_fields():
    r = build_quote_request(LeadSlots(plano_id="completo"), verified=True)
    assert not r.ok
    assert set(r.missing) == {"idade", "veiculo_ano", "cep"}


def test_extract_year_from_veiculo_texto():
    r = build_quote_request(
        LeadSlots(
            idade="42",
            veiculo_texto="Civic LX 2019 prata",
            plano_id="Completo",
            cep="01310-100",
        ),
        verified=True,
        today=date(2026, 7, 22),
    )
    assert r.ok
    assert r.payload is not None
    assert r.payload.veiculo_ano == 2019
    assert r.payload.plano_id == "completo"


def test_refuse_idade_acima_75():
    r = build_quote_request(
        LeadSlots(idade=80, veiculo_ano=2022, plano_id="essencial"),
        verified=True,
        today=date(2026, 7, 22),
    )
    assert not r.ok
    assert any("75" in m for m in r.refusals)


def test_refuse_veiculo_mais_de_20_anos():
    r = build_quote_request(
        LeadSlots(idade=40, veiculo_ano=2000, plano_id="essencial"),
        verified=True,
        today=date(2026, 7, 22),
    )
    assert not r.ok
    assert any("20 anos" in m for m in r.refusals)


def test_plano_inexistente():
    r = build_quote_request(
        LeadSlots(idade=30, veiculo_ano=2021, plano_id="ouro"),
        verified=True,
    )
    assert not r.ok
    assert any("inexistente" in e for e in r.errors)


def test_cep_invalido():
    r = build_quote_request(
        LeadSlots(idade=30, veiculo_ano=2021, cep="123"),
        verified=True,
    )
    assert not r.ok
    assert "cep_invalido" in r.errors


def test_idade_abaixo_18_recusada_por_faixa():
    r = build_quote_request(
        LeadSlots(idade=16, veiculo_ano=2022),
        verified=True,
        today=date(2026, 7, 22),
    )
    assert not r.ok
    assert any("faixas" in m.lower() or "fora" in m.lower() for m in r.refusals)
