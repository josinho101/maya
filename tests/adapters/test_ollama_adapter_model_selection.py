from __future__ import annotations

import pytest

from maya.adapters.ollama_adapter import OllamaAdapter
from maya.config import GlobalConfig


def test_select_model_returns_first_preference():
    config = GlobalConfig(model_preferences={"ui_explore_heal": ["qwen2.5vl:7b", "qwen2.5vl:3b"]})
    adapter = OllamaAdapter(config)

    assert adapter.select_model("ui_explore_heal") == "qwen2.5vl:7b"


def test_select_model_missing_role_raises():
    config = GlobalConfig(model_preferences={})
    adapter = OllamaAdapter(config)

    with pytest.raises(KeyError):
        adapter.select_model("unknown_role")


def test_generate_without_task_role_raises():
    config = GlobalConfig(model_preferences={"api_reasoning": ["m"]})
    adapter = OllamaAdapter(config)

    with pytest.raises(ValueError):
        adapter.generate("hello")
