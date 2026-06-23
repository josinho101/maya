"""`LLMClient` interface (plan.md §2.1): every agent depends on this Protocol only, never on
Ollama's SDK/REST API directly — the swap point exercised by F23-090's later verification task."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    text: str
    model: str
    raw: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class LLMClient(Protocol):
    def generate(
        self,
        prompt: str,
        images: list[bytes] | None = None,
        tools: list[dict[str, Any]] | None = None,
        task_role: str | None = None,
    ) -> LLMResponse: ...
