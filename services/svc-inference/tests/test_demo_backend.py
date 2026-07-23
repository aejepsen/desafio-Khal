"""DemoBackend — plug INFERENCE_URL offline (desafio)."""
from __future__ import annotations

import json

from inference.backends import DemoBackend, build_backend
from inference.config import Settings


def test_demo_extract_json():
    b = DemoBackend()
    out = b.chat(
        "demo-model",
        [
            {"role": "system", "content": "Você extrai dados para cotação. Responda APENAS um JSON válido"},
            {
                "role": "user",
                "content": "tenho 35 anos, Gol 2020, plano premium, cep 01310-100",
            },
        ],
    )
    data = json.loads(out.content)
    assert data["idade"] == 35
    assert data["veiculo_ano"] == 2020
    assert data["plano_id"] == "premium"
    assert "01310" in data["cep"]


def test_demo_polish_eco_rascunho():
    b = DemoBackend()
    out = b.chat(
        "demo-model",
        [
            {"role": "system", "content": "Reescreva a mensagem ao lead no tom indicado."},
            {
                "role": "user",
                "content": "estilo...\nRASCUNHO: Pronto — cotação R$ 100/mês.\nTexto final:",
            },
        ],
    )
    assert "R$ 100" in out.content


def test_build_backend_demo():
    s = Settings(backend="demo", default_model="demo-model", internal_key="x")
    assert isinstance(build_backend(s), DemoBackend)
