from __future__ import annotations

from pathlib import Path

import pytest

from maya.adapters.ollama_adapter import OllamaAdapter
from maya.config import GlobalConfig

from ..conftest import OLLAMA_HOST

SAMPLE_PNG = Path(__file__).parent.parent / "fixtures" / "sample.png"


@pytest.mark.integration
def test_generate_text_only(ollama_models):
    config = GlobalConfig(
        ollama_host=OLLAMA_HOST, model_preferences={"api_reasoning": [ollama_models[0]]}
    )
    adapter = OllamaAdapter(config)

    response = adapter.generate("Say hello in one short word.", task_role="api_reasoning")

    assert response.text.strip() != ""
    assert response.model == ollama_models[0]


@pytest.mark.integration
def test_generate_with_image(ollama_models):
    vision_models = [m for m in ollama_models if "vl" in m.lower() or "vision" in m.lower()]
    if not vision_models:
        pytest.skip("no multimodal model installed locally")

    config = GlobalConfig(
        ollama_host=OLLAMA_HOST, model_preferences={"ui_explore_heal": [vision_models[0]]}
    )
    adapter = OllamaAdapter(config)

    response = adapter.generate(
        "Describe this image in one sentence.",
        images=[SAMPLE_PNG.read_bytes()],
        task_role="ui_explore_heal",
    )

    assert response.text.strip() != ""
