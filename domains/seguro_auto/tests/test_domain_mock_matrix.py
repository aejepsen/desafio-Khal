"""Testes unitários com dados mockados + XML de resultados.

Colunas de entrada: slots + metadados derivados de planos.json.
Colunas de saída: campos do JSON de POST /quote (+ ok/missing/errors/refusals).
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from domains.seguro_auto import LeadSlots, build_quote_request  # noqa: E402
from domains.seguro_auto.plans import clear_plans_cache, load_plans  # noqa: E402
from domains.seguro_auto.report_xml import row_from_case, write_results_xml  # noqa: E402

TODAY = date(2026, 7, 22)
RESULTS_XML = Path(__file__).resolve().parents[1] / "evals" / "results" / "domain_quote_cases.xml"

# (case_id, slots_kwargs, verified, expect_ok, expect_out_subset_or_None)
MOCK_CASES: list[tuple[str, dict, bool, bool, dict | None]] = [
    # --- planos (cada id) ---
    (
        "plano_essencial_ok",
        {"idade": 35, "veiculo_ano": 2020, "plano_id": "essencial", "cep": "01310-100", "data_inicio": "2026-07-22"},
        True,
        True,
        {"plano_id": "essencial", "idade": 35, "veiculo_ano": 2020, "cep": "01310-100", "data_inicio": "2026-07-22"},
    ),
    (
        "plano_completo_ok",
        {"idade": 28, "veiculo_ano": 2024, "plano_id": "completo", "cep": "01310-100"},
        True,
        True,
        {"plano_id": "completo", "idade": 28, "veiculo_ano": 2024, "cep": "01310-100"},
    ),
    (
        "plano_premium_ok",
        {"idade": 65, "veiculo_ano": 2018, "plano_id": "premium", "cep": "22041080"},
        True,
        True,
        {"plano_id": "premium", "idade": 65, "veiculo_ano": 2018, "cep": "22041-080"},
    ),
    # --- faixas etárias (amostra por banda de planos.json) ---
    (
        "faixa_18_24",
        {"idade": 22, "veiculo_ano": 2022, "plano_id": "essencial", "cep": "01310-100"},
        True,
        True,
        {"idade": 22, "veiculo_ano": 2022},
    ),
    (
        "faixa_25_29",
        {"idade": 27, "veiculo_ano": 2022, "plano_id": "essencial", "cep": "01310-100"},
        True,
        True,
        {"idade": 27},
    ),
    (
        "faixa_30_59",
        {"idade": 45, "veiculo_ano": 2022, "plano_id": "essencial", "cep": "01310-100"},
        True,
        True,
        {"idade": 45},
    ),
    (
        "faixa_60_75",
        {"idade": 70, "veiculo_ano": 2022, "plano_id": "essencial", "cep": "01310-100"},
        True,
        True,
        {"idade": 70},
    ),
    (
        "faixa_76_recusa",
        {"idade": 76, "veiculo_ano": 2022, "plano_id": "essencial"},
        True,
        False,
        None,
    ),
    (
        "idade_16_fora",
        {"idade": 16, "veiculo_ano": 2022, "plano_id": "essencial"},
        True,
        False,
        None,
    ),
    # --- idade do veículo (bandas planos.json; today=2026) ---
    (
        "veiculo_0_5",
        {"idade": 40, "veiculo_ano": 2023, "plano_id": "completo", "cep": "01310-100"},
        True,
        True,
        {"veiculo_ano": 2023},
    ),
    (
        "veiculo_6_10",
        {"idade": 40, "veiculo_ano": 2018, "plano_id": "completo", "cep": "01310-100"},
        True,
        True,
        {"veiculo_ano": 2018},
    ),
    (
        "veiculo_11_20",
        {"idade": 40, "veiculo_ano": 2010, "plano_id": "completo", "cep": "01310-100"},
        True,
        True,
        {"veiculo_ano": 2010},
    ),
    (
        "veiculo_21_recusa",
        {"idade": 40, "veiculo_ano": 2004, "plano_id": "completo"},
        True,
        False,
        None,
    ),
    # --- CEP alto risco (prefixos planos.json) + normalização ---
    (
        "cep_alto_risco_08",
        {"idade": 33, "veiculo_ano": 2021, "plano_id": "essencial", "cep": "08000-000"},
        True,
        True,
        {"cep": "08000-000"},
    ),
    (
        "cep_invalido",
        {"idade": 33, "veiculo_ano": 2021, "plano_id": "essencial", "cep": "123"},
        True,
        False,
        None,
    ),
    (
        "cep_obrigatorio_faltando",
        {"idade": 33, "veiculo_ano": 2021, "plano_id": "essencial"},
        True,
        False,
        None,
    ),
    # --- extração de texto / aliases ---
    (
        "veiculo_texto_e_alias_plano",
        {"idade": "42 anos", "veiculo_texto": "Gol 1.0 2019", "plano_id": "Básico", "cep": "01310-100"},
        True,
        True,
        {"idade": 42, "veiculo_ano": 2019, "plano_id": "essencial", "cep": "01310-100"},
    ),
    # --- gates ---
    (
        "nao_verificado",
        {"idade": 35, "veiculo_ano": 2020, "plano_id": "essencial"},
        False,
        False,
        None,
    ),
    (
        "faltando_obrigatorios",
        {"plano_id": "premium"},
        True,
        False,
        None,
    ),
    (
        "plano_inexistente",
        {"idade": 30, "veiculo_ano": 2020, "plano_id": "ouro"},
        True,
        False,
        None,
    ),
]


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_plans_cache()
    yield
    clear_plans_cache()


@pytest.mark.parametrize(
    "case_id,slots_kwargs,verified,expect_ok,expect_out",
    MOCK_CASES,
    ids=[c[0] for c in MOCK_CASES],
)
def test_mock_case(case_id, slots_kwargs, verified, expect_ok, expect_out):
    slots = LeadSlots(**slots_kwargs)
    result = build_quote_request(slots, verified=verified, today=TODAY)
    assert result.ok is expect_ok
    if expect_out is not None:
        assert result.payload is not None
        got = result.payload.to_dict()
        for k, v in expect_out.items():
            assert got.get(k) == v, f"{case_id}: {k}={got.get(k)!r} != {v!r}"


def test_write_xml_report_from_all_mocks():
    plans = load_plans()
    rows = []
    for case_id, slots_kwargs, verified, expect_ok, _ in MOCK_CASES:
        slots = LeadSlots(**slots_kwargs)
        result = build_quote_request(slots, verified=verified, today=TODAY)
        assert result.ok is expect_ok
        rows.append(
            row_from_case(
                case_id=case_id,
                slots=slots,
                result=result,
                verified=verified,
                today=TODAY,
                plans=plans,
            )
        )

    path = write_results_xml(rows, RESULTS_XML, today=TODAY)
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "domain_quote_results" in text
    assert "out_plano_id" in text
    assert "faixa_etaria" in text
    assert "plano_essencial_ok" in text
    assert len(rows) == len(MOCK_CASES)
