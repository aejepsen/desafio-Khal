"""svc-media-asr — Whisper small (faster-whisper) atrás de /v1/transcribe.

Combo “sem stress”: modelo small (~2–3 GB VRAM). Tear-free: só sobe com profile media.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

INTERNAL_KEY = os.environ.get("INTERNAL_KEY", "")
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cuda")  # cuda | cpu
WHISPER_COMPUTE = os.environ.get("WHISPER_COMPUTE", "float16")  # float16 | int8

app = FastAPI(title="svc-media-asr", docs_url=None, redoc_url=None)
_model = None


def _auth(x_internal_key: str | None) -> None:
    if INTERNAL_KEY and x_internal_key != INTERNAL_KEY:
        raise HTTPException(401, "unauthorized")


def get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        device = WHISPER_DEVICE
        compute = WHISPER_COMPUTE
        if device == "cuda":
            try:
                _model = WhisperModel(WHISPER_MODEL, device="cuda", compute_type=compute)
            except Exception:
                device, compute = "cpu", "int8"
                _model = WhisperModel(WHISPER_MODEL, device=device, compute_type=compute)
        else:
            _model = WhisperModel(WHISPER_MODEL, device=device, compute_type=compute)
    return _model


class TranscribeOut(BaseModel):
    text: str
    language: str | None = None
    model: str = Field(default_factory=lambda: WHISPER_MODEL)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": WHISPER_MODEL,
        "device": WHISPER_DEVICE,
    }


@app.post("/v1/transcribe", response_model=TranscribeOut)
async def transcribe(
    request: Request,
    x_internal_key: Annotated[str | None, Header()] = None,
):
    _auth(x_internal_key)
    data = await request.json()
    url = str((data or {}).get("url") or "").strip()
    if not url:
        raise HTTPException(422, "url obrigatorio")

    try:
        with httpx.stream("GET", url, timeout=60.0, follow_redirects=True) as r:
            if r.status_code >= 400:
                raise HTTPException(400, f"download failed: {r.status_code}")
            suffix = Path(url.split("?")[0]).suffix or ".ogg"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                for chunk in r.iter_bytes():
                    tmp.write(chunk)
                path = tmp.name
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"download error: {exc}") from exc

    try:
        model = get_model()
        segments, info = model.transcribe(path, language="pt", beam_size=1)
        text = " ".join(s.text.strip() for s in segments).strip()
    except Exception as exc:
        raise HTTPException(503, f"asr failed: {exc}") from exc
    finally:
        Path(path).unlink(missing_ok=True)

    return TranscribeOut(
        text=text,
        language=getattr(info, "language", None),
    )
