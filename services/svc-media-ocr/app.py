"""svc-media-ocr — Tesseract (CPU) atrás de /v1/ocr.

Aceita:
  {"url": "http://..."}              — download
  {"image_base64": "...", "filename": "cnh.png"}  — bytes enviados no /chat
"""
from __future__ import annotations

import base64
import binascii
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


def _decode_b64(raw: str) -> bytes:
    s = (raw or "").strip()
    if "," in s and s.lower().startswith("data:"):
        s = s.split(",", 1)[1]
    try:
        return base64.b64decode(s, validate=False)
    except binascii.Error as exc:
        raise HTTPException(422, f"image_base64 invalido: {exc}") from exc


def _ocr_file(path: str) -> str:
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
        # melhora contraste simples p/ CNH/prints
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
    return pytesseract.image_to_string(img, lang=OCR_LANG).strip()


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
    b64 = str((data or {}).get("image_base64") or (data or {}).get("content_base64") or "").strip()
    filename = str((data or {}).get("filename") or "upload.png").strip() or "upload.png"

    if not url and not b64:
        raise HTTPException(422, "informe url ou image_base64")

    path = ""
    try:
        if b64:
            blob = _decode_b64(b64)
            suffix = Path(filename).suffix or ".png"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(blob)
                path = tmp.name
        else:
            with httpx.stream("GET", url, timeout=60.0, follow_redirects=True) as r:
                if r.status_code >= 400:
                    raise HTTPException(400, f"download failed: {r.status_code}")
                suffix = Path(url.split("?")[0]).suffix or ".png"
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    for chunk in r.iter_bytes():
                        tmp.write(chunk)
                    path = tmp.name

        text = _ocr_file(path)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"ocr failed: {exc}") from exc
    finally:
        if path:
            Path(path).unlink(missing_ok=True)

    return OcrOut(text=text)
