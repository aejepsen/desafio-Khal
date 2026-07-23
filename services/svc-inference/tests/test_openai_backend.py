"""OpenAI-compat backend registration."""
from inference.backends import OpenAICompatBackend, build_backend
from inference.config import Settings


def test_build_backend_openai():
    s = Settings(
        backend="openai",
        backend_url="https://api.openai.com/v1",
        backend_api_key="sk-test",
        default_model="gpt-4o-mini",
    )
    b = build_backend(s)
    assert isinstance(b, OpenAICompatBackend)
    assert b.api_key == "sk-test"
