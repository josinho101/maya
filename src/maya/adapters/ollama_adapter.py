"""Concrete `LLMClient` backed by a local Ollama install (plan.md §1.3): model-selection policy,
quantization, and `OLLAMA_MAX_LOADED_MODELS` all live behind this adapter — every agent calls
`LLMClient.generate(...)` and never touches Ollama's REST API or model-name strings directly."""

from __future__ import annotations

import base64
import logging
import time
from typing import Any

import httpx

from maya.adapters.llm_client import LLMClient, LLMResponse
from maya.config import GlobalConfig

logger = logging.getLogger("maya.llm")


class OllamaAdapter(LLMClient):
    def __init__(self, config: GlobalConfig, client: httpx.Client | None = None) -> None:
        self._config = config
        self._client = client or httpx.Client(timeout=300.0)

    def select_model(self, task_role: str) -> str:
        preferences = self._config.model_preferences.get(task_role)
        if not preferences:
            raise KeyError(f"no model preferences configured for task_role={task_role!r}")
        return preferences[0]

    def generate(
        self,
        prompt: str,
        images: list[bytes] | None = None,
        tools: list[dict[str, Any]] | None = None,
        task_role: str | None = None,
    ) -> LLMResponse:
        if task_role is None:
            raise ValueError("OllamaAdapter.generate() requires task_role to select a model")
        model = self.select_model(task_role)

        message: dict[str, Any] = {"role": "user", "content": prompt}
        if images:
            message["images"] = [base64.b64encode(b).decode("ascii") for b in images]
        # think=False: reasoning-capable models (e.g. qwen3.x) otherwise spend the whole
        # generation budget on an internal <think> block and return empty `content`.
        payload: dict[str, Any] = {
            "model": model,
            "messages": [message],
            "stream": False,
            "think": False,
        }
        if tools:
            payload["tools"] = tools

        start = time.perf_counter()
        try:
            response = self._client.post(f"{self._config.ollama_host}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "task_role=%s model=%s latency_ms=%.1f prompt_chars=%d outcome=error",
                task_role,
                model,
                latency_ms,
                len(prompt),
                exc_info=True,
            )
            raise

        latency_ms = (time.perf_counter() - start) * 1000
        text = data.get("message", {}).get("content", "")
        logger.info(
            "task_role=%s model=%s latency_ms=%.1f prompt_chars=%d response_chars=%d "
            "outcome=success",
            task_role,
            model,
            latency_ms,
            len(prompt),
            len(text),
        )
        return LLMResponse(text=text, model=model, raw=data)
