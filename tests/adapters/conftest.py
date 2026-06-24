from __future__ import annotations

import httpx
import pytest

OLLAMA_HOST = "http://localhost:11434"


def _list_ollama_models() -> list[str] | None:
    try:
        response = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=2.0)
        response.raise_for_status()
    except httpx.HTTPError:
        return None
    return [m["name"] for m in response.json().get("models", [])]


@pytest.fixture
def ollama_models() -> list[str]:
    models = _list_ollama_models()
    if models is None:
        pytest.skip(f"Ollama not reachable at {OLLAMA_HOST}")
    if not models:
        pytest.skip("Ollama reachable but no models installed")
    return models
