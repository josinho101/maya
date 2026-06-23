from __future__ import annotations

import json

from maya.config import GlobalConfig, load_global_config


def test_load_global_config_round_trip(tmp_path):
    path = tmp_path / "global_config.json"
    path.write_text(
        json.dumps(
            {
                "ollama_host": "http://example:11434",
                "model_preferences": {"api_reasoning": ["model-a", "model-b"]},
            }
        )
    )

    config = load_global_config(path)

    assert isinstance(config, GlobalConfig)
    assert config.ollama_host == "http://example:11434"
    assert config.model_preferences["api_reasoning"] == ["model-a", "model-b"]


def test_default_ollama_host():
    config = GlobalConfig()
    assert config.ollama_host == "http://localhost:11434"
    assert config.model_preferences == {}
