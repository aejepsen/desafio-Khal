"""Mídia: detecção HITL + plug opcional ASR/OCR (tear-free).

Default (sem URLs): mídia sem texto útil → escalar_humano ("mídia sem transcrição").
Com MEDIA_ASR_URL / MEDIA_OCR_URL: tenta enriquecer; falha → mesmo HITL.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

# Placeholders típicos do dataset / WhatsApp quando não há ASR/OCR.
_MEDIA_TYPES = frozenset({"audio", "image", "document", "video", "sticker", "ptt"})

_MARKER = re.compile(
    r"(?is)^\s*\[(?P<kind>documento|document|áudio|audio|imagem|image|foto|"
    r"vídeo|video|sticker|mídia|midia|arquivo)\]\s*(?P<rest>.*)$"
)

_FILENAME_ONLY = re.compile(
    r"(?is)^\s*[\w.\- ]+\.(pdf|jpe?g|png|gif|webp|ogg|mp3|m4a|wav|mp4|mov|opus)\s*$"
)

_KIND_MAP = {
    "áudio": "audio",
    "audio": "audio",
    "imagem": "image",
    "image": "image",
    "foto": "image",
    "documento": "document",
    "document": "document",
    "arquivo": "document",
    "vídeo": "video",
    "video": "video",
    "sticker": "sticker",
    "mídia": "media",
    "midia": "media",
}


def detectar_midia_sem_transcricao(
    mensagem: str,
    message_type: str | None = None,
) -> str | None:
    """Retorna o tipo de mídia se NÃO há texto útil para cotar; senão None."""
    mt = (message_type or "").strip().lower()
    text = (mensagem or "").strip()

    if mt in _MEDIA_TYPES:
        if not text or _MARKER.match(text) or _FILENAME_ONLY.match(text):
            return mt
        if len(text) < 12 and not any(ch.isalpha() for ch in text):
            return mt

    m = _MARKER.match(text)
    if m:
        kind = m.group("kind").lower()
        rest = (m.group("rest") or "").strip()
        if not rest or _FILENAME_ONLY.match(rest) or len(rest) < 8:
            return _KIND_MAP.get(kind, kind)
        return None

    if _FILENAME_ONLY.match(text):
        return "document"

    return None


def texto_util_para_cotacao(texto: str) -> bool:
    t = (texto or "").strip()
    if len(t) < 8:
        return False
    if detectar_midia_sem_transcricao(t) is not None:
        return False
    return any(ch.isalpha() for ch in t)


class MediaEnricher(Protocol):
    """ASR (áudio) / OCR (imagem|documento). Retorna texto ou None."""

    def enrich(
        self,
        *,
        media_type: str,
        media_url: str | None,
        placeholder: str,
        trace: str,
        media_base64: str | None = None,
        filename: str | None = None,
    ) -> str | None: ...


@dataclass
class HttpMediaEnricher:
    """Cliente HTTP opcional.

    Contratos:
      POST {asr}/v1/transcribe  {"url": "..."} -> {"text": "..."}
      POST {ocr}/v1/ocr         {"url"| "image_base64"} -> {"text": "..."}
    """

    asr_url: str | None = None
    ocr_url: str | None = None
    key: str = ""
    timeout_s: float = 60.0

    def enrich(
        self,
        *,
        media_type: str,
        media_url: str | None,
        placeholder: str,
        trace: str,
        media_base64: str | None = None,
        filename: str | None = None,
    ) -> str | None:
        mt = media_type.lower()
        if mt in {"audio", "ptt", "video"}:
            base = self.asr_url
            path = "/v1/transcribe"
            if not media_url:
                return None
            body: dict[str, Any] = {
                "url": media_url,
                "media_type": mt,
                "placeholder": placeholder,
            }
        elif mt in {"image", "document", "sticker"}:
            base = self.ocr_url
            path = "/v1/ocr"
            if not media_url and not media_base64:
                return None
            body = {
                "media_type": mt,
                "placeholder": placeholder,
                "filename": filename or "upload.png",
            }
            if media_base64:
                body["image_base64"] = media_base64
            if media_url:
                body["url"] = media_url
        else:
            return None
        if not base:
            return None
        import httpx

        headers = {"traceparent": trace}
        if self.key:
            headers["X-Internal-Key"] = self.key
        try:
            resp = httpx.post(
                f"{base.rstrip('/')}{path}",
                json=body,
                headers=headers,
                timeout=self.timeout_s,
            )
        except httpx.HTTPError:
            return None
        if resp.status_code >= 400:
            return None
        try:
            text = str((resp.json() or {}).get("text") or "").strip()
        except Exception:
            return None
        return text or None


@dataclass
class FakeMediaEnricher:
    """Gates / testes — devolve texto fixo ou None."""

    text: str | None = "tenho 35 anos, Gol 2020, plano essencial, cep 01310-100"
    calls: list = field(default_factory=list)

    def enrich(
        self,
        *,
        media_type: str,
        media_url: str | None,
        placeholder: str,
        trace: str,
        media_base64: str | None = None,
        filename: str | None = None,
    ) -> str | None:
        self.calls.append({"trace": trace, "b64": bool(media_base64), "url": media_url})
        return self.text


def tentar_enriquecer_midia(
    mensagem: str,
    tipo_midia: str,
    *,
    enricher: MediaEnricher | None,
    media_url: str | None,
    trace: str,
    media_base64: str | None = None,
    filename: str | None = None,
) -> tuple[str | None, str]:
    """Tenta ASR/OCR. Retorna (texto_ou_None, status: ok|skip|fail)."""
    if enricher is None:
        return None, "skip"
    if not media_url and not media_base64:
        return None, "skip"
    try:
        out = enricher.enrich(
            media_type=tipo_midia,
            media_url=media_url,
            placeholder=mensagem,
            trace=trace,
            media_base64=media_base64,
            filename=filename,
        )
    except Exception:
        return None, "fail"
    if out and texto_util_para_cotacao(out):
        return out, "ok"
    return None, "fail"
