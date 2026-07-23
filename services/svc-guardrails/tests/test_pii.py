from __future__ import annotations

from guardrails.pii import mask_pii


def test_mask_cpf_placa_email_cep() -> None:
    text = "CPF 529.982.247-25 placa ABC1D23 email a@b.com cep 01310-100"
    r = mask_pii(text)
    assert "[CPF]" in r.text
    assert "[PLACA]" in r.text
    assert "[EMAIL]" in r.text
    assert "[CEP]" in r.text
    assert "529.982.247-25" not in r.text
    assert set(r.types) >= {"cpf", "placa", "email", "cep"}


def test_mask_cnh() -> None:
    r = mask_pii("minha CNH 12345678901")
    assert "[CNH]" in r.text
    assert "cnh" in r.types


def test_no_pii_unchanged() -> None:
    t = "quero seguro do Gol 2020, tenho 35 anos"
    r = mask_pii(t)
    assert r.text == t
    assert r.types == []


def test_locale_other_noop() -> None:
    t = "CPF 529.982.247-25"
    r = mask_pii(t, locale="en-US")
    assert r.text == t
    assert r.types == []


def test_analyze_endpoint_pii(client, auth_headers) -> None:
    r = client.post(
        "/v1/analyze",
        headers=auth_headers,
        json={
            "text": "Meu CPF é 529.982.247-25 e placa ABC1D23",
            "checks": ["sanitize", "pii"],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] == "allow"
    assert "[CPF]" in body["sanitized_text"]
    assert "[PLACA]" in body["sanitized_text"]
    assert body["verdicts"]["pii"]["flagged"] is True
    assert "cpf" in body["verdicts"]["pii"]["types"]
