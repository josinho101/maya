from __future__ import annotations

from typing import Any

from maya.adapters.llm_client import LLMClient, LLMResponse


class StubLLMClient:
    def generate(
        self,
        prompt: str,
        images: list[bytes] | None = None,
        tools: list[dict[str, Any]] | None = None,
        task_role: str | None = None,
    ) -> LLMResponse:
        return LLMResponse(text="stub", model="stub-model")


def test_stub_satisfies_llm_client_protocol():
    assert isinstance(StubLLMClient(), LLMClient)


def test_non_conforming_object_does_not_satisfy_protocol():
    assert not isinstance(object(), LLMClient)
