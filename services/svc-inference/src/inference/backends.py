"""Backends de inferência: interface + FakeBackend (gates) + OllamaBackend (real).

Usage é lido NA FONTE (o backend reporta prompt/completion tokens). A fachada
nunca estima. FakeBackend é determinístico para gates 100% offline.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Protocol

from inference.circuit import BackendBusiness, BackendError


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class Completion:
    content: str
    finish_reason: str
    usage: Usage


@dataclass(frozen=True)
class Chunk:
    delta: str
    finish_reason: str | None = None
    usage: Usage | None = None  # presente apenas no último chunk


class Backend(Protocol):
    def chat(self, model: str, messages: list[dict[str, str]], **opts: Any) -> Completion: ...
    def chat_stream(
        self, model: str, messages: list[dict[str, str]], **opts: Any
    ) -> Iterator[Chunk]: ...
    def list_models(self) -> list[str]: ...


def _count_tokens(text: str) -> int:
    """Aproximação simples por palavras — usada SÓ pelo FakeBackend como usage sintético."""
    return len(text.split())


@dataclass
class FakeBackend:
    """Determinístico para gates. Configurável para falhar (resiliência)."""

    reply: str = "resposta determinística do fake backend"
    models: list[str] = field(default_factory=lambda: ["fake-model"])
    fail_transport: bool = False       # simula backend fora (conta p/ circuito)
    fail_business: int = 0             # simula 4xx (NÃO conta p/ circuito)
    n_chunks: int = 3

    def _guard(self) -> None:
        if self.fail_transport:
            raise BackendError("fake: transporte fora")
        if self.fail_business:
            raise BackendBusiness(self.fail_business, "fake: erro de negocio")

    def _usage(self, messages: list[dict[str, str]]) -> Usage:
        prompt = " ".join(m["content"] for m in messages)
        pt = _count_tokens(prompt)
        ct = _count_tokens(self.reply)
        return Usage(pt, ct, pt + ct)

    def chat(self, model: str, messages: list[dict[str, str]], **opts: Any) -> Completion:
        self._guard()
        return Completion(self.reply, "stop", self._usage(messages))

    def chat_stream(
        self, model: str, messages: list[dict[str, str]], **opts: Any
    ) -> Iterator[Chunk]:
        self._guard()
        words = self.reply.split()
        step = max(1, len(words) // self.n_chunks)
        pieces = [" ".join(words[i : i + step]) for i in range(0, len(words), step)]
        for i, piece in enumerate(pieces):
            last = i == len(pieces) - 1
            yield Chunk(
                delta=piece + ("" if last else " "),
                finish_reason="stop" if last else None,
                usage=self._usage(messages) if last else None,
            )

    def list_models(self) -> list[str]:
        self._guard()
        return list(self.models)


@dataclass
class OllamaBackend:
    """Backend real via HTTP Ollama. Usage na fonte (prompt_eval_count/eval_count)."""

    url: str
    timeout_s: float

    def _client(self) -> Any:
        import httpx

        return httpx.Client(timeout=self.timeout_s, base_url=self.url.rstrip("/"))

    @staticmethod
    def _usage(data: dict[str, Any]) -> Usage:
        pt = int(data.get("prompt_eval_count", 0))
        ct = int(data.get("eval_count", 0))
        return Usage(pt, ct, pt + ct)

    def chat(self, model: str, messages: list[dict[str, str]], **opts: Any) -> Completion:
        import httpx

        try:
            with self._client() as c:
                resp = c.post(
                    "/api/chat",
                    json={"model": model, "messages": messages, "stream": False},
                )
        except httpx.HTTPError as exc:
            raise BackendError(str(exc)) from exc
        if resp.status_code >= 500:
            raise BackendError(f"backend 5xx: {resp.status_code}")
        if resp.status_code >= 400:
            raise BackendBusiness(resp.status_code, resp.text[:200])
        data = resp.json()
        return Completion(
            data["message"]["content"], data.get("done_reason", "stop"), self._usage(data)
        )

    def chat_stream(
        self, model: str, messages: list[dict[str, str]], **opts: Any
    ) -> Iterator[Chunk]:
        import json as _json

        import httpx

        try:
            with self._client() as c, c.stream(
                "POST", "/api/chat", json={"model": model, "messages": messages, "stream": True}
            ) as resp:
                if resp.status_code >= 500:
                    raise BackendError(f"backend 5xx: {resp.status_code}")
                if resp.status_code >= 400:
                    raise BackendBusiness(resp.status_code, "erro de negocio")
                for line in resp.iter_lines():
                    if not line:
                        continue
                    data = _json.loads(line)
                    done = data.get("done", False)
                    yield Chunk(
                        delta=data.get("message", {}).get("content", ""),
                        finish_reason=data.get("done_reason", "stop") if done else None,
                        usage=self._usage(data) if done else None,
                    )
        except httpx.HTTPError as exc:
            raise BackendError(str(exc)) from exc

    def list_models(self) -> list[str]:
        import httpx

        try:
            with self._client() as c:
                resp = c.get("/api/tags")
        except httpx.HTTPError as exc:
            raise BackendError(str(exc)) from exc
        if resp.status_code >= 400:
            raise BackendError(f"backend {resp.status_code}")
        return [m["name"] for m in resp.json().get("models", [])]


@dataclass
class DemoBackend:
    """Backend offline útil pro desafio: extrai JSON de slots e ecoa o rascunho na redação.

    Não chama LLM real. Serve para validar o plug INFERENCE_URL ponta a ponta sem Ollama/créditos.
    Produção: BACKEND=ollama (ou outro provider futuro).
    """

    models: list[str] = field(default_factory=lambda: ["demo-model", "default-model"])

    def chat(self, model: str, messages: list[dict[str, str]], **opts: Any) -> Completion:
        system = next((m["content"] for m in messages if m.get("role") == "system"), "")
        user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        if "Responda APENAS um JSON" in system or "extrai dados para cotação" in system.lower():
            reply = _demo_extract_json(user)
        elif "RASCUNHO:" in user or "Reescreva a mensagem" in system:
            reply = _demo_polish(user)
        else:
            reply = "ok"
        prompt = " ".join(m.get("content", "") for m in messages)
        pt, ct = _count_tokens(prompt), _count_tokens(reply)
        return Completion(reply, "stop", Usage(pt, ct, pt + ct))

    def chat_stream(
        self, model: str, messages: list[dict[str, str]], **opts: Any
    ) -> Iterator[Chunk]:
        done = self.chat(model, messages, **opts)
        yield Chunk(delta=done.content, finish_reason="stop", usage=done.usage)

    def list_models(self) -> list[str]:
        return list(self.models)


def _demo_extract_json(texto: str) -> str:
    """Heurística mínima → JSON (espelha o extrator do agente, offline)."""
    import json as _json
    import re as _re

    out: dict[str, Any] = {}
    m = _re.search(r"\b(\d{2})\s*anos?\b", texto, _re.I) or _re.search(
        r"\bidade\s*[:=]?\s*(\d{1,3})\b", texto, _re.I
    )
    if m:
        out["idade"] = int(m.group(1))
    ym = _re.search(r"\b(19|20)\d{2}\b", texto)
    if ym:
        out["veiculo_ano"] = int(ym.group(0))
    low = texto.lower()
    for pid in ("premium", "completo", "essencial"):
        if pid in low:
            out["plano_id"] = pid
            break
    cm = _re.search(r"\b\d{5}-?\d{3}\b", texto)
    if cm:
        out["cep"] = cm.group(0)
    return _json.dumps(out, ensure_ascii=False)


def _demo_polish(user: str) -> str:
    """Devolve o rascunho (prova o plug sem inventar fatos)."""
    marker = "RASCUNHO:"
    if marker in user:
        tail = user.split(marker, 1)[1]
        # corta instrução residual
        line = tail.split("Texto final:")[0].strip()
        return line or "Como posso te ajudar na cotação?"
    return user.strip()[:400] or "ok"


@dataclass
class OpenAICompatBackend:
    """Backend OpenAI-compat (`/v1/chat/completions`) — OpenAI, Groq, vLLM, OpenRouter, etc.

    Usage na fonte quando o provedor devolve `usage`; senão aproxima por palavras.
    """

    url: str
    api_key: str = ""
    timeout_s: float = 60.0

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _client(self) -> Any:
        import httpx

        return httpx.Client(timeout=self.timeout_s, base_url=self.url.rstrip("/"))

    @staticmethod
    def _usage(data: dict[str, Any], messages: list[dict[str, str]], content: str) -> Usage:
        u = data.get("usage") or {}
        if u.get("prompt_tokens") is not None:
            pt = int(u.get("prompt_tokens") or 0)
            ct = int(u.get("completion_tokens") or 0)
            return Usage(pt, ct, int(u.get("total_tokens") or (pt + ct)))
        prompt = " ".join(m.get("content", "") for m in messages)
        pt, ct = _count_tokens(prompt), _count_tokens(content)
        return Usage(pt, ct, pt + ct)

    def chat(self, model: str, messages: list[dict[str, str]], **opts: Any) -> Completion:
        import httpx

        body: dict[str, Any] = {"model": model, "messages": messages, "stream": False}
        if opts.get("temperature") is not None:
            body["temperature"] = opts["temperature"]
        try:
            with self._client() as c:
                resp = c.post("/chat/completions", json=body, headers=self._headers())
        except httpx.HTTPError as exc:
            raise BackendError(str(exc)) from exc
        if resp.status_code >= 500:
            raise BackendError(f"backend 5xx: {resp.status_code}")
        if resp.status_code >= 400:
            raise BackendBusiness(resp.status_code, resp.text[:200])
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        finish = data["choices"][0].get("finish_reason") or "stop"
        return Completion(content, finish, self._usage(data, messages, content))

    def chat_stream(
        self, model: str, messages: list[dict[str, str]], **opts: Any
    ) -> Iterator[Chunk]:
        # Streaming opcional: fallback para chat bloqueante (suficiente pro agente).
        done = self.chat(model, messages, **opts)
        yield Chunk(delta=done.content, finish_reason="stop", usage=done.usage)

    def list_models(self) -> list[str]:
        import httpx

        try:
            with self._client() as c:
                resp = c.get("/models", headers=self._headers())
        except httpx.HTTPError as exc:
            raise BackendError(str(exc)) from exc
        if resp.status_code >= 400:
            raise BackendError(f"backend {resp.status_code}")
        return [m["id"] for m in resp.json().get("data", [])]


def build_backend(settings: Any) -> Backend:
    if settings.backend == "fake":
        return FakeBackend()
    if settings.backend in {"demo", "desafio"}:
        return DemoBackend()
    if settings.backend in {"openai", "openai_compat", "openai-compat"}:
        return OpenAICompatBackend(
            settings.backend_url,
            getattr(settings, "backend_api_key", "") or "",
            settings.backend_timeout_s,
        )
    return OllamaBackend(settings.backend_url, settings.backend_timeout_s)
