"""svc-media-ocr — Tesseract (CPU) atrás de /v1/ocr. Combo sem stress."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

INTERNAL_KEY = os.environ.get("INTERNAL_KEY", "")
OCR_LANG = os.environ.get("OCR_LANG", "por+eng")

app = FastAPI(title="svc-media-ocr", docs_url=None, redoc_url=None)


def _auth(x_internal_key: str | None) -> None:
    if INTERNAL_KEY and x_internal_key != INTERNAL_KEY:
        raise HTTPException(401, "unauthorized")


class OcrOut(BaseModel):
    text: str
    lang: str = OCR_LANG


@app.get("/health")
def health():
    return {"status": "ok", "engine": "tesseract", "lang": OCR_LANG}


@app.post("/v1/ocr", response_model=OcrOut)
async def ocr(
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
            suffix = Path(url.split("?")[0]).suffix or ".png"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                for chunk in r.iter_bytes():
                    tmp.write(chunk)
                path = tmp.name
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"download error: {exc}") from exc

    try:
        from PIL import Image
        import pytesseract

        p = Path(path)
        if p.suffix.lower() == ".pdf":
            try:
                from pdf2image import convert_from_path
                pages = convert_from_path(path, first_page=1, last_page=1)
                img = pages[0]
            except Exception as exc:
                raise HTTPException(422, f"pdf ocr unavailable: {exc}") from exc
        else:
            img = Image.open(path)
        text = pytesseract.image_to_string(img, lang=OCR_LANG).strip()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"ocr failed: {exc}") from exc
    finally:
        Path(path).unlink(missing_ok=True)

    return OcrOut(text=text)
