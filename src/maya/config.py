"""Loader for `framework-data/global_config.json` (plan.md §3.3): Ollama host and the
per-task-role model preference list consumed by `OllamaAdapter` (plan.md §1.2)."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class GlobalConfig(BaseModel):
    ollama_host: str = "http://localhost:11434"
    model_preferences: dict[str, list[str]] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


def load_global_config(path: Path) -> GlobalConfig:
    return GlobalConfig.model_validate_json(Path(path).read_bytes())
